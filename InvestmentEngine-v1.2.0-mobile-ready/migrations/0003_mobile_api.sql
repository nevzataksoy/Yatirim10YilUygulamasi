begin;

-- ---------------------------------------------------------------------------
-- Authenticated mobile surface for the future Quasar/Capacitor application
-- package id: tr.rosayazilim.yatirimdashboard
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  first_name text,
  middle_name text,
  last_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.investment_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'Ana Portföy',
  base_currency text not null default 'USD' check(base_currency in ('USD','TRY')),
  is_default boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, name)
);
create index if not exists idx_investment_accounts_user on public.investment_accounts(user_id, created_at);

create table if not exists public.portfolio_transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  account_id uuid not null references public.investment_accounts(id) on delete cascade,
  decision_id bigint references model.decisions(id) on delete set null,
  transaction_at timestamptz not null,
  transaction_type text not null check(transaction_type in (
    'OPENING','BUY','SELL','CONVERSION','EXIT','CASH_IN','CASH_OUT'
  )),
  source_asset text,
  target_asset text,
  source_quantity numeric(38,12) check(source_quantity is null or source_quantity >= 0),
  target_quantity numeric(38,12) check(target_quantity is null or target_quantity >= 0),
  price_currency text check(price_currency is null or price_currency in ('USD','TRY')),
  source_unit_price numeric(28,10) check(source_unit_price is null or source_unit_price >= 0),
  target_unit_price numeric(28,10) check(target_unit_price is null or target_unit_price >= 0),
  usd_try numeric(18,8) check(usd_try is null or usd_try > 0),
  gross_usd numeric(28,8) check(gross_usd is null or gross_usd >= 0),
  fee_usd numeric(28,8) not null default 0 check(fee_usd >= 0),
  net_usd numeric(28,8),
  platform text,
  external_ref text,
  note text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(source_asset is not null or target_asset is not null),
  check(source_asset is null or target_asset is null or source_asset <> target_asset)
);
create index if not exists idx_portfolio_transactions_user_time on public.portfolio_transactions(user_id, transaction_at desc);
create index if not exists idx_portfolio_transactions_account_time on public.portfolio_transactions(account_id, transaction_at desc);
create unique index if not exists ux_portfolio_transactions_external_ref
  on public.portfolio_transactions(user_id, external_ref)
  where external_ref is not null and external_ref <> '';

create table if not exists public.user_investment_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  monthly_budget_usd numeric(18,2) not null default 200 check(monthly_budget_usd >= 0),
  btc_target_pct numeric(8,6) not null default 0.375 check(btc_target_pct between 0 and 1),
  eth_target_pct numeric(8,6) not null default 0.375 check(eth_target_pct between 0 and 1),
  ura_target_pct numeric(8,6) not null default 0.25 check(ura_target_pct between 0 and 1),
  dca_day smallint not null default 25 check(dca_day between 1 and 28),
  telegram_notifications boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(abs((btc_target_pct + eth_target_pct + ura_target_pct) - 1.0) < 0.000001)
);

-- Latest engine outputs. Windows service writes through the PostgreSQL service
-- connection. Mobile users can only SELECT after Supabase Auth login.
create table if not exists public.decision_snapshot (
  system text primary key,
  generated_at timestamptz not null default now(),
  as_of date not null,
  direction text not null,
  status text not null,
  regime_code text not null,
  edge_score numeric(8,3) not null,
  confidence numeric(8,3) not null,
  uncertainty numeric(8,3) not null,
  data_quality numeric(8,3) not null,
  risk_score numeric(8,3) not null,
  recommended_size numeric(12,8) not null default 0,
  late_entry boolean not null default false,
  event_veto boolean not null default false,
  execution_required boolean not null default false,
  action_event boolean not null default false,
  action_stage smallint not null default 0 check(action_stage between 0 and 2),
  action_size numeric(12,8) not null default 0 check(action_size between 0 and 1),
  regime_cumulative_size numeric(12,8) not null default 0 check(regime_cumulative_size between 0 and 1),
  provider text,
  factors jsonb not null default '{}'::jsonb,
  rationale jsonb not null default '{}'::jsonb
);

create table if not exists public.decision_history (
  decision_id bigint primary key references model.decisions(id) on delete cascade,
  generated_at timestamptz not null default now(),
  as_of date not null,
  system text not null,
  direction text not null,
  status text not null,
  regime_code text not null,
  edge_score numeric(8,3) not null,
  confidence numeric(8,3) not null,
  uncertainty numeric(8,3) not null,
  data_quality numeric(8,3) not null,
  risk_score numeric(8,3) not null,
  recommended_size numeric(12,8) not null default 0,
  late_entry boolean not null default false,
  event_veto boolean not null default false,
  execution_required boolean not null default false,
  action_event boolean not null default false,
  action_stage smallint not null default 0 check(action_stage between 0 and 2),
  action_size numeric(12,8) not null default 0 check(action_size between 0 and 1),
  regime_cumulative_size numeric(12,8) not null default 0 check(regime_cumulative_size between 0 and 1),
  provider text,
  factors jsonb not null default '{}'::jsonb,
  rationale jsonb not null default '{}'::jsonb
);
create index if not exists idx_decision_history_system_time on public.decision_history(system, generated_at desc);

create table if not exists public.market_snapshot (
  symbol text primary key,
  value numeric(38,12) not null,
  unit text not null,
  provider text not null,
  data_date date not null,
  generated_at timestamptz not null default now(),
  details jsonb not null default '{}'::jsonb
);

create table if not exists public.engine_health_snapshot (
  component text primary key,
  status text not null,
  message text,
  checked_at timestamptz not null default now(),
  details jsonb not null default '{}'::jsonb
);

create or replace view public.portfolio_positions
with (security_invoker = true)
as
with legs as (
  select user_id, account_id, target_asset as asset, target_quantity as quantity
  from public.portfolio_transactions
  where target_asset is not null and target_quantity is not null
  union all
  select user_id, account_id, source_asset as asset, -source_quantity as quantity
  from public.portfolio_transactions
  where source_asset is not null and source_quantity is not null
)
select user_id, account_id, asset, sum(quantity)::numeric(38,12) as quantity
from legs
group by user_id, account_id, asset;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles(user_id, first_name, last_name)
  values (
    new.id,
    nullif(new.raw_user_meta_data ->> 'first_name', ''),
    nullif(new.raw_user_meta_data ->> 'last_name', '')
  )
  on conflict(user_id) do nothing;

  insert into public.investment_accounts(user_id, name, base_currency, is_default)
  values (new.id, 'Ana Portföy', 'USD', true)
  on conflict(user_id, name) do nothing;

  insert into public.user_investment_settings(user_id)
  values (new.id)
  on conflict(user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- updated_at triggers
drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists trg_investment_accounts_updated_at on public.investment_accounts;
create trigger trg_investment_accounts_updated_at before update on public.investment_accounts
for each row execute function public.set_updated_at();

drop trigger if exists trg_portfolio_transactions_updated_at on public.portfolio_transactions;
create trigger trg_portfolio_transactions_updated_at before update on public.portfolio_transactions
for each row execute function public.set_updated_at();

drop trigger if exists trg_user_investment_settings_updated_at on public.user_investment_settings;
create trigger trg_user_investment_settings_updated_at before update on public.user_investment_settings
for each row execute function public.set_updated_at();

-- RLS
alter table public.profiles enable row level security;
alter table public.investment_accounts enable row level security;
alter table public.portfolio_transactions enable row level security;
alter table public.user_investment_settings enable row level security;
alter table public.decision_snapshot enable row level security;
alter table public.decision_history enable row level security;
alter table public.market_snapshot enable row level security;
alter table public.engine_health_snapshot enable row level security;

-- Make reruns deterministic in development.
drop policy if exists "profiles_select_own" on public.profiles;
drop policy if exists "profiles_update_own" on public.profiles;
drop policy if exists "accounts_select_own" on public.investment_accounts;
drop policy if exists "accounts_insert_own" on public.investment_accounts;
drop policy if exists "accounts_update_own" on public.investment_accounts;
drop policy if exists "accounts_delete_own" on public.investment_accounts;
drop policy if exists "transactions_select_own" on public.portfolio_transactions;
drop policy if exists "transactions_insert_own" on public.portfolio_transactions;
drop policy if exists "transactions_update_own" on public.portfolio_transactions;
drop policy if exists "transactions_delete_own" on public.portfolio_transactions;
drop policy if exists "investment_settings_select_own" on public.user_investment_settings;
drop policy if exists "investment_settings_insert_own" on public.user_investment_settings;
drop policy if exists "investment_settings_update_own" on public.user_investment_settings;
drop policy if exists "decision_authenticated_read" on public.decision_snapshot;
drop policy if exists "decision_history_authenticated_read" on public.decision_history;
drop policy if exists "market_authenticated_read" on public.market_snapshot;
drop policy if exists "health_authenticated_read" on public.engine_health_snapshot;

create policy "profiles_select_own" on public.profiles
for select to authenticated using (auth.uid() = user_id);
create policy "profiles_update_own" on public.profiles
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "accounts_select_own" on public.investment_accounts
for select to authenticated using (auth.uid() = user_id);
create policy "accounts_insert_own" on public.investment_accounts
for insert to authenticated with check (auth.uid() = user_id);
create policy "accounts_update_own" on public.investment_accounts
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "accounts_delete_own" on public.investment_accounts
for delete to authenticated using (auth.uid() = user_id);

create policy "transactions_select_own" on public.portfolio_transactions
for select to authenticated using (auth.uid() = user_id);
create policy "transactions_insert_own" on public.portfolio_transactions
for insert to authenticated with check (
  auth.uid() = user_id and exists (
    select 1 from public.investment_accounts a
    where a.id = account_id and a.user_id = auth.uid()
  )
);
create policy "transactions_update_own" on public.portfolio_transactions
for update to authenticated using (auth.uid() = user_id) with check (
  auth.uid() = user_id and exists (
    select 1 from public.investment_accounts a
    where a.id = account_id and a.user_id = auth.uid()
  )
);
create policy "transactions_delete_own" on public.portfolio_transactions
for delete to authenticated using (auth.uid() = user_id);

create policy "investment_settings_select_own" on public.user_investment_settings
for select to authenticated using (auth.uid() = user_id);
create policy "investment_settings_insert_own" on public.user_investment_settings
for insert to authenticated with check (auth.uid() = user_id);
create policy "investment_settings_update_own" on public.user_investment_settings
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "decision_authenticated_read" on public.decision_snapshot
for select to authenticated using (true);
create policy "decision_history_authenticated_read" on public.decision_history
for select to authenticated using (true);
create policy "market_authenticated_read" on public.market_snapshot
for select to authenticated using (true);
create policy "health_authenticated_read" on public.engine_health_snapshot
for select to authenticated using (true);

revoke all on public.decision_snapshot from anon;
revoke all on public.decision_history from anon;
revoke all on public.market_snapshot from anon;
revoke all on public.engine_health_snapshot from anon;
revoke all on public.profiles from anon;
revoke all on public.investment_accounts from anon;
revoke all on public.portfolio_transactions from anon;
revoke all on public.user_investment_settings from anon;

-- Base table grants are still constrained by RLS.
grant select, update on public.profiles to authenticated;
grant select, insert, update, delete on public.investment_accounts to authenticated;
grant select, insert, update, delete on public.portfolio_transactions to authenticated;
grant select, insert, update on public.user_investment_settings to authenticated;
grant select on public.decision_snapshot to authenticated;
grant select on public.decision_history to authenticated;
grant select on public.market_snapshot to authenticated;
grant select on public.engine_health_snapshot to authenticated;
grant select on public.portfolio_positions to authenticated;

commit;
