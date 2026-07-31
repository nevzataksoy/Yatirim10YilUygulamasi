begin;

-- v1.2.0: model-version provenance, point-in-time validation reports and
-- explicit Shadow -> LIVE readiness gate.

alter table model.decisions
  add column if not exists model_version text not null default 'legacy-pre-1.2.0';

alter table public.decision_snapshot
  add column if not exists model_version text not null default 'legacy-pre-1.2.0';

alter table public.decision_history
  add column if not exists model_version text not null default 'legacy-pre-1.2.0';

create table if not exists model.validation_runs (
  id bigint generated always as identity primary key,
  validation_type text not null,
  system text not null,
  model_version text not null,
  status text not null,
  started_at timestamptz not null,
  finished_at timestamptz not null default now(),
  start_date date,
  end_date date,
  observations integer,
  signals integer,
  metrics jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb
);
create index if not exists idx_validation_runs_type_system_time
  on model.validation_runs(validation_type, system, finished_at desc);

create table if not exists public.model_validation_snapshot (
  validation_type text not null,
  system text not null,
  generated_at timestamptz not null default now(),
  model_version text not null,
  status text not null,
  start_date date,
  end_date date,
  metrics jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  primary key(validation_type, system)
);

alter table public.model_validation_snapshot enable row level security;
drop policy if exists "model_validation_authenticated_read" on public.model_validation_snapshot;
create policy "model_validation_authenticated_read" on public.model_validation_snapshot
for select to authenticated using (true);

revoke all on public.model_validation_snapshot from anon;
grant select on public.model_validation_snapshot to authenticated;

insert into model.parameters(system, parameter_key, value_numeric, description)
values
('ALL','shadow_min_calendar_days',30,'LIVE değerlendirmesi öncesi minimum Shadow takvim günü'),
('ETH/BTC','shadow_min_decision_days',25,'ETH/BTC için minimum farklı karar günü'),
('URA/USD','shadow_min_decision_days',20,'URA/USD için minimum farklı karar günü'),
('ALL','shadow_min_median_data_quality',80,'Shadow kararlarında minimum median data quality'),
('ALL','shadow_min_job_success_rate',0.98,'Son 7 günlük minimum job başarı oranı'),
('ALL','shadow_realtime_max_age_days',7,'Başarılı realtime smoke test için maksimum yaş'),
('URA/USD','shadow_min_holdings_dates',2,'URA directional holdings proxy için minimum snapshot günü'),
('URA/USD','shadow_min_breadth_dates',20,'URA breadth doğrulaması için minimum tarih sayısı')
on conflict(system,parameter_key) do update set
  value_numeric=excluded.value_numeric,
  description=excluded.description,
  updated_at=now();

commit;
