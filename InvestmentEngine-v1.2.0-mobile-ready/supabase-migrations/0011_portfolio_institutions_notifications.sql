begin;

-- =============================================================================
-- Portfolio institution dictionary + mobile notification management foundation.
-- This migration is additive. Existing portfolio/platform data is preserved and
-- Python market/macro/model collection tables are not changed.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Financial institution dictionary
-- -----------------------------------------------------------------------------
create table if not exists public.financial_institutions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  institution_type text not null default 'OTHER'
    check (institution_type in ('BANK','EXCHANGE','BROKER','CUSTODIAN','FUND_PLATFORM','OTHER')),
  country_code text,
  website text,
  note text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(name)) between 2 and 120),
  unique(user_id, name)
);

create table if not exists public.investment_account_institutions (
  user_id uuid not null references auth.users(id) on delete cascade,
  account_id uuid not null references public.investment_accounts(id) on delete cascade,
  institution_id uuid not null references public.financial_institutions(id) on delete cascade,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(account_id, institution_id)
);

alter table public.portfolio_transactions
  add column if not exists institution_id uuid references public.financial_institutions(id) on delete set null;
create index if not exists idx_portfolio_transactions_institution_time
  on public.portfolio_transactions(institution_id, transaction_at desc);

-- Convert existing free-text platform values into the user dictionary without
-- changing the original platform snapshot.
insert into public.financial_institutions(user_id, name, institution_type)
select distinct user_id, btrim(platform), 'OTHER'
from public.portfolio_transactions
where nullif(btrim(platform), '') is not null
on conflict(user_id, name) do nothing;

insert into public.investment_account_institutions(user_id, account_id, institution_id)
select distinct tx.user_id, tx.account_id, fi.id
from public.portfolio_transactions tx
join public.financial_institutions fi
  on fi.user_id=tx.user_id and fi.name=btrim(tx.platform)
where nullif(btrim(tx.platform), '') is not null
on conflict(account_id, institution_id) do nothing;

update public.portfolio_transactions tx
set institution_id=fi.id
from public.financial_institutions fi
where tx.institution_id is null
  and fi.user_id=tx.user_id
  and fi.name=btrim(tx.platform)
  and nullif(btrim(tx.platform), '') is not null;

create or replace function public.normalize_transaction_institution()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  institution_row public.financial_institutions%rowtype;
begin
  -- New clients may send the normalized id. Keep platform as a historical name
  -- snapshot so exports remain readable if the dictionary entry is renamed later.
  if new.institution_id is not null then
    select * into institution_row
    from public.financial_institutions
    where id=new.institution_id and user_id=new.user_id;

    if not found then
      raise exception 'Institution does not belong to the transaction user.' using errcode='42501';
    end if;
    if not exists (
      select 1 from public.investment_account_institutions map
      where map.user_id=new.user_id
        and map.account_id=new.account_id
        and map.institution_id=new.institution_id
        and map.is_active=true
    ) then
      raise exception 'Institution is not active for this investment account.' using errcode='42501';
    end if;
    new.platform := institution_row.name;
    return new;
  end if;

  -- Backward compatibility for older Quasar/APK clients that still submit only
  -- the platform text. If the name exists in the dictionary, attach its id.
  if nullif(btrim(new.platform), '') is not null then
    select fi.* into institution_row
    from public.financial_institutions fi
    join public.investment_account_institutions map
      on map.institution_id=fi.id and map.account_id=new.account_id and map.is_active=true
    where fi.user_id=new.user_id and fi.name=btrim(new.platform)
    limit 1;
    if found then
      new.institution_id := institution_row.id;
      new.platform := institution_row.name;
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_normalize_transaction_institution on public.portfolio_transactions;
create trigger trg_normalize_transaction_institution
before insert on public.portfolio_transactions
for each row execute function public.normalize_transaction_institution();

create or replace function public.validate_account_institution_mapping()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if not exists (
    select 1 from public.investment_accounts a
    where a.id=new.account_id and a.user_id=new.user_id
  ) then
    raise exception 'Investment account does not belong to the mapping user.' using errcode='42501';
  end if;
  if not exists (
    select 1 from public.financial_institutions fi
    where fi.id=new.institution_id and fi.user_id=new.user_id
  ) then
    raise exception 'Institution does not belong to the mapping user.' using errcode='42501';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_validate_account_institution_mapping on public.investment_account_institutions;
create trigger trg_validate_account_institution_mapping
before insert or update on public.investment_account_institutions
for each row execute function public.validate_account_institution_mapping();

-- One effective OPENING chain per account + asset. A correction is a revision
-- that explicitly supersedes the current OPENING row; a missing asset may still
-- be added later as its own initial OPENING chain.
create or replace function public.validate_opening_chain()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  supersedes_id text := nullif(new.metadata ->> 'supersedes_transaction_id','');
  predecessor public.portfolio_transactions%rowtype;
begin
  if new.transaction_type <> 'OPENING' then
    return new;
  end if;
  -- Existing append-only cancellation rows intentionally have no effective
  -- quantity/value legs; let the 0008 revision validator handle them.
  if new.metadata ? 'cancelled_at' then
    return new;
  end if;
  if new.target_asset is null or new.target_quantity is null then
    raise exception 'OPENING transaction requires target asset and quantity.';
  end if;

  if supersedes_id is not null then
    select * into predecessor
    from public.portfolio_transactions
    where id::text=supersedes_id
      and user_id=new.user_id
      and account_id=new.account_id;
    if not found or predecessor.transaction_type <> 'OPENING' then
      raise exception 'OPENING correction must supersede an OPENING transaction.';
    end if;
    if predecessor.target_asset is distinct from new.target_asset then
      raise exception 'OPENING correction cannot change the asset; add the miss