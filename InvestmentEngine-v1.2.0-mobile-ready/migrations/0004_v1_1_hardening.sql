begin;

-- v1.0 -> v1.1 mobile-ready / staged-signal upgrade.
-- Safe to run on a fresh schema because all operations are IF NOT EXISTS.

alter table model.decisions add column if not exists action_event boolean not null default false;
alter table model.decisions add column if not exists action_stage smallint not null default 0;
alter table model.decisions add column if not exists action_size numeric(12,8) not null default 0;
alter table model.decisions add column if not exists regime_cumulative_size numeric(12,8) not null default 0;

create table if not exists model.signal_state (
  system text primary key,
  active_direction text,
  stage smallint not null default 0 check(stage between 0 and 2),
  cumulative_size numeric(12,8) not null default 0 check(cumulative_size between 0 and 1),
  last_action_date date,
  reset_counter integer not null default 0 check(reset_counter >= 0),
  updated_at timestamptz not null default now()
);

alter table public.portfolio_transactions
  add column if not exists decision_id bigint references model.decisions(id) on delete set null;

alter table public.decision_snapshot add column if not exists action_event boolean not null default false;
alter table public.decision_snapshot add column if not exists action_stage smallint not null default 0;
alter table public.decision_snapshot add column if not exists action_size numeric(12,8) not null default 0;
alter table public.decision_snapshot add column if not exists regime_cumulative_size numeric(12,8) not null default 0;

alter table public.decision_history add column if not exists action_event boolean not null default false;
alter table public.decision_history add column if not exists action_stage smallint not null default 0;
alter table public.decision_history add column if not exists action_size numeric(12,8) not null default 0;
alter table public.decision_history add column if not exists regime_cumulative_size numeric(12,8) not null default 0;

insert into model.parameters(system,parameter_key,value_numeric,description) values
('ALL','strong_action_edge',80,'Kademe 2 için güçlü edge'),
('ALL','strong_action_confidence',80,'Kademe 2 için güçlü confidence'),
('ALL','regime_reset_edge',45,'Aktif rejimin zayıf kabul edildiği edge'),
('ALL','regime_reset_days',5,'Rejim reset için ardışık zayıf gün')
on conflict(system,parameter_key) do update set
  value_numeric=excluded.value_numeric,
  description=excluded.description,
  updated_at=now();

commit;
