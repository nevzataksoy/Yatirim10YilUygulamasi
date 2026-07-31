begin;
create extension if not exists pgcrypto;

create schema if not exists market;
create schema if not exists macro;
create schema if not exists fundamentals;
create schema if not exists events;
create schema if not exists model;
create schema if not exists system;

create table if not exists market.daily_prices (
  id bigint generated always as identity primary key,
  provider text not null,
  asset_class text not null,
  symbol text not null,
  price_date date not null,
  open numeric(28,10) not null,
  high numeric(28,10) not null,
  low numeric(28,10) not null,
  close numeric(28,10) not null,
  volume numeric(38,10) not null default 0,
  fetched_at timestamptz not null default now(),
  unique(provider, symbol, price_date)
);
create index if not exists idx_daily_prices_symbol_date on market.daily_prices(symbol, price_date desc);

create table if not exists market.derivatives_snapshots (
  id bigint generated always as identity primary key,
  observed_at timestamptz not null,
  venue text not null,
  underlying text not null,
  instrument_name text not null,
  open_interest numeric(38,10),
  mark_price numeric(28,10),
  index_price numeric(28,10),
  basis_pct numeric(18,8),
  funding_8h numeric(18,10),
  current_funding numeric(18,10),
  best_bid numeric(28,10),
  best_ask numeric(28,10),
  option_open_interest numeric(38,10),
  option_volume_24h numeric(38,10),
  option_mark_iv_mean numeric(18,8),
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_deriv_underlying_time on market.derivatives_snapshots(underlying, observed_at desc);

create table if not exists market.execution_snapshots (
  id bigint generated always as identity primary key,
  decision_id bigint,
  observed_at timestamptz not null,
  product text not null,
  spread_bps numeric(18,8),
  bid_depth_usd numeric(28,4),
  ask_depth_usd numeric(28,4),
  imbalance numeric(18,8),
  microprice numeric(28,10),
  created_at timestamptz not null default now()
);
create index if not exists idx_execution_decision_time on market.execution_snapshots(decision_id, observed_at);

create table if not exists macro.observations (
  id bigint generated always as identity primary key,
  series_id text not null,
  observation_date date not null,
  value numeric(28,10) not null,
  realtime_start date not null,
  realtime_end date,
  fetched_at timestamptz not null default now(),
  unique(series_id, observation_date, realtime_start)
);
create index if not exists idx_macro_series_date on macro.observations(series_id, observation_date desc);

create table if not exists fundamentals.ura_holdings (
  holding_date date not null,
  ticker text not null,
  name text,
  weight numeric(18,8),
  shares numeric(28,8),
  market_value numeric(28,2),
  source_url text,
  fetched_at timestamptz not null default now(),
  primary key(holding_date, ticker)
);

create table if not exists fundamentals.ura_breadth (
  breadth_date date primary key,
  pct_above_20dma numeric(18,8),
  pct_above_50dma numeric(18,8),
  pct_above_200dma numeric(18,8),
  pct_positive_day numeric(18,8),
  new_20d_high_pct numeric(18,8),
  quality numeric(8,4),
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists events.events (
  id bigint generated always as identity primary key,
  source text not null,
  entity text,
  asset text not null default 'ALL',
  event_type text not null,
  occurred_at timestamptz not null,
  title text not null,
  url text not null default '',
  severity numeric(8,3) not null default 0 check(severity between -100 and 100),
  surprise numeric(8,3) not null default 0 check(surprise between -100 and 100),
  credibility numeric(8,3) not null default 100 check(credibility between 0 and 100),
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create unique index if not exists ux_events_source_url on events.events(source, url) where url <> '';
create index if not exists idx_events_asset_time on events.events(asset, occurred_at desc);

create table if not exists model.features (
  id bigint generated always as identity primary key,
  as_of date not null,
  system text not null,
  feature_code text not null,
  value numeric(38,12),
  z_score numeric(18,8),
  quality numeric(8,3) not null default 100 check(quality between 0 and 100),
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(as_of, system, feature_code)
);

create table if not exists model.regimes (
  id bigint generated always as identity primary key,
  as_of date not null,
  system text not null,
  primary_regime text not null,
  probabilities jsonb not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(as_of, system)
);

create table if not exists model.factor_scores (
  id bigint generated always as identity primary key,
  as_of date not null,
  system text not null,
  regime_code text not null,
  factor_code text not null,
  score numeric(8,3) not null check(score between -100 and 100),
  quality numeric(8,3) not null check(quality between 0 and 100),
  weight numeric(10,6) not null default 0,
  weighted_score numeric(12,6) not null default 0,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(as_of, system, factor_code)
);

create table if not exists model.decisions (
  id bigint generated always as identity primary key,
  as_of date not null,
  system text not null,
  direction text not null,
  regime_code text not null,
  edge_score numeric(8,3) not null check(edge_score between 0 and 100),
  confidence numeric(8,3) not null check(confidence between 0 and 100),
  uncertainty numeric(8,3) not null check(uncertainty between 0 and 100),
  data_quality numeric(8,3) not null check(data_quality between 0 and 100),
  risk_score numeric(8,3) not null check(risk_score between 0 and 100),
  recommended_size numeric(12,8) not null default 0 check(recommended_size between 0 and 1),
  late_entry boolean not null default false,
  event_veto boolean not null default false,
  status text not null,
  execution_required boolean not null default false,
  action_event boolean not null default false,
  action_stage smallint not null default 0 check(action_stage between 0 and 2),
  action_size numeric(12,8) not null default 0 check(action_size between 0 and 1),
  regime_cumulative_size numeric(12,8) not null default 0 check(regime_cumulative_size between 0 and 1),
  factors jsonb not null default '{}'::jsonb,
  rationale jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_decisions_system_time on model.decisions(system, created_at desc);

create table if not exists model.signal_state (
  system text primary key,
  active_direction text,
  stage smallint not null default 0 check(stage between 0 and 2),
  cumulative_size numeric(12,8) not null default 0 check(cumulative_size between 0 and 1),
  last_action_date date,
  reset_counter integer not null default 0 check(reset_counter >= 0),
  updated_at timestamptz not null default now()
);

alter table market.execution_snapshots
  drop constraint if exists fk_execution_decision;
alter table market.execution_snapshots
  add constraint fk_execution_decision foreign key(decision_id) references model.decisions(id) on delete cascade;

create table if not exists model.performance (
  id bigint generated always as identity primary key,
  system text not null,
  decision_id bigint references model.decisions(id) on delete cascade,
  horizon_days integer not null,
  relative_return numeric(18,8),
  hit boolean,
  evaluated_at timestamptz,
  unique(decision_id, horizon_days)
);

create table if not exists model.parameters (
  system text not null,
  parameter_key text not null,
  value_numeric numeric(18,8),
  value_text text,
  description text,
  updated_at timestamptz not null default now(),
  primary key(system, parameter_key)
);

create table if not exists model.factor_weights (
  system text not null,
  regime_code text not null,
  factor_code text not null,
  weight numeric(10,6) not null check(weight >= 0 and weight <= 1),
  description text,
  primary key(system, regime_code, factor_code)
);

create table if not exists system.job_runs (
  id bigint generated always as identity primary key,
  job_name text not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,
  message text,
  details jsonb not null default '{}'::jsonb
);
create index if not exists idx_job_runs_name_time on system.job_runs(job_name, started_at desc);

create table if not exists system.data_sources (
  code text primary key,
  category text not null,
  source_url text not null,
  expected_interval_seconds integer,
  stale_after_seconds integer,
  required boolean not null default true,
  enabled boolean not null default true,
  notes text
);

commit;
