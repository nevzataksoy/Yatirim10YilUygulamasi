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
      raise exception 'OPENING correction cannot change the asset; add the missing asset separately.';
    end if;
    return new;
  end if;

  if exists (
    select 1
    from public.portfolio_transactions current_opening
    where current_opening.user_id=new.user_id
      and current_opening.account_id=new.account_id
      and current_opening.transaction_type='OPENING'
      and current_opening.target_asset=new.target_asset
      and not (current_opening.metadata ? 'cancelled_at')
      and not exists (
        select 1 from public.portfolio_transactions successor
        where successor.user_id=current_opening.user_id
          and successor.account_id=current_opening.account_id
          and successor.metadata ->> 'supersedes_transaction_id' = current_opening.id::text
      )
  ) then
    raise exception 'This asset already has an active OPENING row. Revise the existing opening instead of adding another.'
      using errcode='23505';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_validate_opening_chain on public.portfolio_transactions;
create trigger trg_validate_opening_chain
before insert on public.portfolio_transactions
for each row execute function public.validate_opening_chain();

-- Opening balance remains an auditable ledger event. Corrections are made by
-- the existing append-only revision chain; full reset is only for intentional
-- re-entry of the complete account history. No new transaction type is needed.

-- -----------------------------------------------------------------------------
-- Notification provider/device/template/inbox/log/outbox
-- -----------------------------------------------------------------------------
create table if not exists public.push_provider_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  provider text not null default 'FCM' check(provider='FCM'),
  enabled boolean not null default false,
  firebase_project_id text,
  sender_id text,
  android_package_name text not null default 'tr.rosayazilim.yatirimdashboard',
  web_vapid_key text,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.push_provider_settings is
  'Non-secret Firebase/FCM metadata only. Service-account private keys must remain on the Python server.';

create table if not exists public.notification_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  installation_id text not null,
  device_name text,
  platform text not null default 'unknown',
  operating_system text,
  os_version text,
  app_version text,
  target_kind text not null default 'TOKEN' check(target_kind in ('TOKEN','FID')),
  push_target text,
  permission_status text not null default 'UNKNOWN'
    check(permission_status in ('UNKNOWN','PROMPT','GRANTED','DENIED')),
  is_active boolean not null default true,
  last_seen_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, installation_id)
);
create index if not exists idx_notification_devices_user_active
  on public.notification_devices(user_id, is_active, last_seen_at desc);

create table if not exists public.notification_templates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  account_id uuid references public.investment_accounts(id) on delete cascade,
  name text not null,
  event_type text not null check(event_type in ('PORTFOLIO_DAILY','SIGNAL_CREATED')),
  enabled boolean not null default true,
  timezone text not null default 'Europe/Istanbul',
  schedule_time time,
  days_of_week smallint[] not null default array[1,2,3,4,5,6,7]::smallint[],
  display_currency text not null default 'USD' check(display_currency in ('USD','TRY','BTC','ETH')),
  title_template text not null,
  body_template text not null,
  payload jsonb not null default '{}'::jsonb,
  last_enqueued_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(event_type <> 'PORTFOLIO_DAILY' or (account_id is not null and schedule_time is not null)),
  check(event_type <> 'SIGNAL_CREATED' or schedule_time is null)
);
create index if not exists idx_notification_templates_user_event
  on public.notification_templates(user_id, enabled, event_type);

create table if not exists public.notification_outbox (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  template_id uuid references public.notification_templates(id) on delete set null,
  event_type text not null,
  event_key text not null,
  source_id text,
  context jsonb not null default '{}'::jsonb,
  status text not null default 'PENDING' check(status in ('PENDING','PROCESSING','SENT','FAILED','SKIPPED')),
  attempts integer not null default 0,
  available_at timestamptz not null default now(),
  locked_at timestamptz,
  processed_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  unique(template_id, event_key)
);
create index if not exists idx_notification_outbox_pending
  on public.notification_outbox(status, available_at, id);

create table if not exists public.notification_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  template_id uuid references public.notification_templates(id) on delete set null,
  outbox_id bigint references public.notification_outbox(id) on delete set null,
  event_type text not null,
  title text not null,
  body text not null,
  payload jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists idx_notification_messages_user_time
  on public.notification_messages(user_id, created_at desc);
create unique index if not exists ux_notification_messages_outbox
  on public.notification_messages(outbox_id) where outbox_id is not null;

create table if not exists public.notification_logs (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  message_id uuid references public.notification_messages(id) on delete set null,
  template_id uuid references public.notification_templates(id) on delete set null,
  device_id uuid references public.notification_devices(id) on delete set null,
  provider text not null default 'FCM',
  status text not null check(status in ('SENT','FAILED','SKIPPED','OPENED')),
  provider_message_id text,
  error_message text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_notification_logs_user_time
  on public.notification_logs(user_id, created_at desc);

-- Current portfolio valuation used by scheduled notification templates.
create or replace function public.notification_portfolio_value(
  p_account_id uuid,
  p_display_currency text default 'USD'
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  owner_id uuid;
  usd_try numeric;
  btc_usd numeric;
  eth_usd numeric;
  ura_usd numeric;
  total_usd numeric := 0;
  converted numeric := 0;
begin
  select user_id into owner_id from public.investment_accounts where id=p_account_id;
  if owner_id is null then raise exception 'Investment account not found.'; end if;

  select value into usd_try from public.market_snapshot where symbol='USD/TRY';
  select value into btc_usd from public.market_snapshot where symbol='BTC/USD';
  select value into eth_usd from public.market_snapshot where symbol='ETH/USD';
  select value into ura_usd from public.market_snapshot where symbol='URA/USD';

  select coalesce(sum(case p.asset
    when 'USD' then p.quantity
    when 'TRY' then case when coalesce(usd_try,0)>0 then p.quantity/usd_try else 0 end
    when 'BTC' then p.quantity*coalesce(btc_usd,0)
    when 'ETH' then p.quantity*coalesce(eth_usd,0)
    when 'URA' then p.quantity*coalesce(ura_usd,0)
    else 0 end),0)
  into total_usd
  from public.portfolio_positions p
  where p.account_id=p_account_id;

  converted := case upper(p_display_currency)
    when 'TRY' then total_usd*coalesce(usd_try,0)
    when 'BTC' then case when coalesce(btc_usd,0)>0 then total_usd/btc_usd else 0 end
    when 'ETH' then case when coalesce(eth_usd,0)>0 then total_usd/eth_usd else 0 end
    else total_usd end;

  return jsonb_build_object(
    'account_id',p_account_id,
    'user_id',owner_id,
    'display_currency',upper(p_display_currency),
    'value',converted,
    'value_usd',total_usd,
    'usd_try',usd_try,
    'calculated_at',now()
  );
end;
$$;

-- Enqueue due daily templates. ISO day numbers: Monday=1 ... Sunday=7.
create or replace function public.enqueue_due_portfolio_notifications(p_now timestamptz default now())
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  inserted_count integer := 0;
begin
  insert into public.notification_outbox(user_id,template_id,event_type,event_key,context)
  select
    t.user_id,
    t.id,
    t.event_type,
    'PORTFOLIO_DAILY:' || (p_now at time zone t.timezone)::date::text,
    jsonb_build_object('account_id',t.account_id,'display_currency',t.display_currency)
  from public.notification_templates t
  where t.enabled=true
    and t.event_type='PORTFOLIO_DAILY'
    and extract(isodow from (p_now at time zone t.timezone))::smallint = any(t.days_of_week)
    and (p_now at time zone t.timezone)::time >= t.schedule_time
    and (p_now at time zone t.timezone)::time < t.schedule_time + interval '5 minutes'
  on conflict(template_id,event_key) do nothing;
  get diagnostics inserted_count = row_count;
  return inserted_count;
end;
$$;

create or replace function public.validate_notification_template_owner()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if new.account_id is not null and not exists (
    select 1 from public.investment_accounts a
    where a.id=new.account_id and a.user_id=new.user_id and a.is_active=true
  ) then
    raise exception 'Notification template account does not belong to the user.' using errcode='42501';
  end if;
  if exists (select 1 from unnest(new.days_of_week) as dow(day_no) where day_no < 1 or day_no > 7) then
    raise exception 'days_of_week values must be ISO weekday numbers 1..7.';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_validate_notification_template_owner on public.notification_templates;
create trigger trg_validate_notification_template_owner
before insert or update on public.notification_templates
for each row execute function public.validate_notification_template_owner();

-- New actionable engine signals are mirrored to enabled Quasar push templates.
create or replace function public.enqueue_signal_notification()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce(new.action_event,false) is not true then return new; end if;

  insert into public.notification_outbox(user_id,template_id,event_type,event_key,source_id,context)
  select
    t.user_id,
    t.id,
    'SIGNAL_CREATED',
    'SIGNAL_CREATED:' || new.decision_id::text,
    new.decision_id::text,
    jsonb_build_object(
      'decision_id',new.decision_id,
      'system',new.system,
      'direction',new.direction,
      'edge',new.edge_score,
      'confidence',new.confidence,
      'data_quality',new.data_quality,
      'regime',new.regime_code,
      'action_stage',new.action_stage,
      'action_size',new.action_size,
      'generated_at',new.generated_at
    )
  from public.notification_templates t
  where t.enabled=true and t.event_type='SIGNAL_CREATED'
  on conflict(template_id,event_key) do nothing;
  return new;
end;
$$;

drop trigger if exists trg_enqueue_signal_notification on public.decision_history;
create trigger trg_enqueue_signal_notification
after insert on public.decision_history
for each row execute function public.enqueue_signal_notification();

-- Keep mutable user-managed rows timestamped with the shared 0003 helper.
drop trigger if exists trg_financial_institutions_updated_at on public.financial_institutions;
create trigger trg_financial_institutions_updated_at before update on public.financial_institutions
for each row execute function public.set_updated_at();
drop trigger if exists trg_account_institutions_updated_at on public.investment_account_institutions;
create trigger trg_account_institutions_updated_at before update on public.investment_account_institutions
for each row execute function public.set_updated_at();
drop trigger if exists trg_push_provider_settings_updated_at on public.push_provider_settings;
create trigger trg_push_provider_settings_updated_at before update on public.push_provider_settings
for each row execute function public.set_updated_at();
drop trigger if exists trg_notification_devices_updated_at on public.notification_devices;
create trigger trg_notification_devices_updated_at before update on public.notification_devices
for each row execute function public.set_updated_at();
drop trigger if exists trg_notification_templates_updated_at on public.notification_templates;
create trigger trg_notification_templates_updated_at before update on public.notification_templates
for each row execute function public.set_updated_at();

-- Queue creation is server-side only; authenticated clients manage templates,
-- not outbox rows or direct enqueue functions.
revoke all on function public.enqueue_due_portfolio_notifications(timestamptz) from public, anon, authenticated;
revoke all on function public.enqueue_signal_notification() from public, anon, authenticated;

-- -----------------------------------------------------------------------------
-- RLS / grants
-- -----------------------------------------------------------------------------
alter table public.financial_institutions enable row level security;
alter table public.investment_account_institutions enable row level security;
alter table public.push_provider_settings enable row level security;
alter table public.notification_devices enable row level security;
alter table public.notification_templates enable row level security;
alter table public.notification_outbox enable row level security;
alter table public.notification_messages enable row level security;
alter table public.notification_logs enable row level security;

drop policy if exists "financial_institutions_own_all" on public.financial_institutions;
drop policy if exists "account_institutions_own_all" on public.investment_account_institutions;
drop policy if exists "push_provider_settings_own_all" on public.push_provider_settings;
drop policy if exists "notification_devices_own_all" on public.notification_devices;
drop policy if exists "notification_templates_own_all" on public.notification_templates;
drop policy if exists "notification_messages_own_select" on public.notification_messages;
drop policy if exists "notification_messages_own_update" on public.notification_messages;
drop policy if exists "notification_logs_own_select" on public.notification_logs;

create policy "financial_institutions_own_all" on public.financial_institutions
for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "account_institutions_own_all" on public.investment_account_institutions
for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "push_provider_settings_own_all" on public.push_provider_settings
for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "notification_devices_own_all" on public.notification_devices
for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "notification_templates_own_all" on public.notification_templates
for all to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "notification_messages_own_select" on public.notification_messages
for select to authenticated using(auth.uid()=user_id);
create policy "notification_messages_own_update" on public.notification_messages
for update to authenticated using(auth.uid()=user_id) with check(auth.uid()=user_id);
create policy "notification_logs_own_select" on public.notification_logs
for select to authenticated using(auth.uid()=user_id);
-- notification_outbox is intentionally backend-only.

revoke all on public.notification_outbox from anon, authenticated;
revoke all on public.notification_messages from anon, authenticated;
revoke all on public.notification_logs from anon, authenticated;

grant select,insert,update on public.financial_institutions to authenticated;
grant select,insert,update on public.investment_account_institutions to authenticated;
grant select,insert,update on public.push_provider_settings to authenticated;
grant select,insert,update on public.notification_devices to authenticated;
grant select,insert,update,delete on public.notification_templates to authenticated;
grant select on public.notification_messages to authenticated;
grant update(read_at) on public.notification_messages to authenticated;
grant select on public.notification_logs to authenticated;
grant execute on function public.notification_portfolio_value(uuid,text) to authenticated;

commit;
