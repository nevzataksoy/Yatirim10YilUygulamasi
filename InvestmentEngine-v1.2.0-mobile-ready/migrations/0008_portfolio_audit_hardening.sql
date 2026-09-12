begin;

-- Quasar/Supabase contract alignment. This migration only changes the
-- authenticated portfolio surface; market.*, macro.*, model.* and engine
-- snapshot write paths used by the running Python service are untouched.

alter table public.user_investment_settings
  add column if not exists start_date date not null default date '2026-07-25',
  add column if not exists btc_eth_conversion_pct numeric(8,6) not null default 0.5,
  add column if not exists ura_usd_conversion_pct numeric(8,6) not null default 0.5;

alter table public.user_investment_settings
  drop constraint if exists user_investment_settings_btc_eth_conversion_pct_check,
  drop constraint if exists user_investment_settings_ura_usd_conversion_pct_check;

alter table public.user_investment_settings
  add constraint user_investment_settings_btc_eth_conversion_pct_check
    check (btc_eth_conversion_pct between 0 and 1),
  add constraint user_investment_settings_ura_usd_conversion_pct_check
    check (ura_usd_conversion_pct between 0 and 1);

-- A transaction may have only one direct successor. This prevents concurrent
-- edits from forking a revision chain while preserving every historical row.
create unique index if not exists ux_portfolio_transactions_single_successor
  on public.portfolio_transactions ((metadata ->> 'supersedes_transaction_id'))
  where nullif(metadata ->> 'supersedes_transaction_id', '') is not null;

create or replace function public.validate_portfolio_revision_reference()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
declare
  referenced_transaction public.portfolio_transactions%rowtype;
  referenced_id text := nullif(new.metadata ->> 'supersedes_transaction_id', '');
begin
  if referenced_id is null then
    return new;
  end if;

  select * into referenced_transaction
  from public.portfolio_transactions
  where id::text = referenced_id;

  if not found then
    raise exception 'Superseded transaction % does not exist.', referenced_id;
  end if;
  if referenced_transaction.user_id <> new.user_id
     or referenced_transaction.account_id <> new.account_id then
    raise exception 'A revision must stay in the same user and investment account.';
  end if;
  if referenced_transaction.metadata ? 'cancelled_at' then
    raise exception 'A cancellation marker cannot be revised.';
  end if;
  if new.metadata ? 'cancelled_at'
     and (new.source_quantity is not null or new.target_quantity is not null
          or coalesce(new.gross_usd, 0) <> 0 or new.fee_usd <> 0) then
    raise exception 'A cancellation marker cannot contain effective quantities or value.';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_validate_portfolio_revision_reference on public.portfolio_transactions;
create trigger trg_validate_portfolio_revision_reference
before insert on public.portfolio_transactions
for each row execute function public.validate_portfolio_revision_reference();

-- Reports and balance reads use only the tip of each revision chain. A
-- cancellation row supersedes the prior transaction but has no effective leg.
create or replace view public.portfolio_positions
with (security_invoker = true)
as
with effective_transactions as (
  select tx.*
  from public.portfolio_transactions tx
  where not (tx.metadata ? 'cancelled_at')
    and not exists (
      select 1
      from public.portfolio_transactions successor
      where successor.user_id = tx.user_id
        and successor.account_id = tx.account_id
        and successor.metadata ->> 'supersedes_transaction_id' = tx.id::text
    )
),
legs as (
  select user_id, account_id, target_asset as asset, target_quantity as quantity
  from effective_transactions
  where target_asset is not null and target_quantity is not null
  union all
  select user_id, account_id, source_asset as asset, -source_quantity as quantity
  from effective_transactions
  where source_asset is not null and source_quantity is not null
)
select user_id, account_id, asset, sum(quantity)::numeric(38,12) as quantity
from legs
group by user_id, account_id, asset;

-- Authenticated clients are append-only. Service-role/database administrators
-- retain maintenance authority for an explicitly approved test-data purge.
drop policy if exists "transactions_update_own" on public.portfolio_transactions;
drop policy if exists "transactions_delete_own" on public.portfolio_transactions;
revoke update, delete on public.portfolio_transactions from authenticated;

-- Deleting an account would cascade-delete its audit rows, so client-side
-- account removal becomes soft deactivation through is_active instead.
drop policy if exists "accounts_delete_own" on public.investment_accounts;
revoke delete on public.investment_accounts from authenticated;

-- Supports users created before the profiles trigger was installed.
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
for insert to authenticated with check (auth.uid() = user_id);
grant insert on public.profiles to authenticated;

grant select, insert on public.portfolio_transactions to authenticated;
grant select on public.portfolio_positions to authenticated;

comment on view public.portfolio_positions is
  'Effective account balances; superseded revisions and append-only cancellation markers are excluded.';

commit;
