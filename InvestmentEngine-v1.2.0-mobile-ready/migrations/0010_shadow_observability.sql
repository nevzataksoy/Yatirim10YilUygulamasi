begin;

create table if not exists model.shadow_epochs (
  id bigint generated always as identity primary key,
  epoch_key text not null unique,
  model_version text not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  status text not null default 'ACTIVE' check(status in ('ACTIVE','CLOSED')),
  reason text not null default '',
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(ended_at is null or ended_at >= started_at)
);

create unique index if not exists ux_shadow_epochs_active_model
  on model.shadow_epochs(model_version)
  where status='ACTIVE';

-- Recover the already-running v1.2.0 Shadow epoch from real decision evidence.
-- No synthetic start date is created when no v1.2.0 decision exists.
insert into model.shadow_epochs(epoch_key,model_version,started_at,status,reason,details)
select
  'shadow-1.2.0-initial',
  '1.2.0',
  min(created_at),
  'ACTIVE',
  'Initial production Shadow epoch recovered from first v1.2.0 decision.',
  jsonb_build_object('source','model.decisions','recovered_by','0010_shadow_observability')
from model.decisions
where model_version='1.2.0'
having min(created_at) is not null
on conflict(epoch_key) do nothing;

alter table system.job_runs
  add column if not exists run_kind text not null default 'legacy',
  add column if not exists shadow_epoch_id bigint;

alter table system.job_runs
  drop constraint if exists ck_job_runs_run_kind;
alter table system.job_runs
  add constraint ck_job_runs_run_kind
  check(run_kind in ('scheduled','scheduled_legacy','manual','test','backfill','dependency','maintenance','development','legacy'));

alter table system.job_runs
  drop constraint if exists fk_job_runs_shadow_epoch;
alter table system.job_runs
  add constraint fk_job_runs_shadow_epoch
  foreign key(shadow_epoch_id) references model.shadow_epochs(id) on delete set null;

-- Known top-level non-scheduler operations can be classified deterministically.
update system.job_runs set run_kind='test'
where run_kind='legacy' and job_name='realtime_test';
update system.job_runs set run_kind='manual'
where run_kind='legacy' and job_name='model_validation_job';
update system.job_runs set run_kind='backfill'
where run_kind='legacy' and job_name='crypto_history_backfill';

-- Child jobs invoked inside a scheduled parent are not additional scheduler fires.
update system.job_runs child
set run_kind='maintenance'
where child.run_kind='legacy'
  and child.job_name in ('macro_job','sec_event_job')
  and exists (
    select 1 from system.job_runs parent
    where parent.job_name='weekly_job'
      and child.started_at >= parent.started_at
      and child.started_at <= coalesce(parent.finished_at,parent.started_at + interval '30 minutes')
  );

update system.job_runs child
set run_kind='dependency'
where child.run_kind='legacy'
  and child.job_name='hourly_job'
  and exists (
    select 1 from system.job_runs parent
    where parent.job_name='daily_crypto_job'
      and child.started_at >= parent.started_at
      and child.started_at <= coalesce(parent.finished_at,parent.started_at + interval '30 minutes')
  );

update system.job_runs child
set run_kind='dependency'
where child.run_kind='legacy'
  and child.job_name='sec_event_job'
  and exists (
    select 1 from system.job_runs parent
    where parent.job_name='daily_ura_job'
      and child.started_at >= parent.started_at
      and child.started_at <= coalesce(parent.finished_at,parent.started_at + interval '30 minutes')
  );

-- Remaining known scheduler jobs in the recovered epoch are historical scheduler candidates.
-- They remain explicitly 'scheduled_legacy' instead of pretending perfect provenance.
update system.job_runs
set run_kind='scheduled_legacy'
where run_kind='legacy'
  and job_name in (
    'hourly_job','macro_job','sec_event_job','daily_crypto_job','daily_ura_job',
    'daily_fx_job','weekly_job','monthly_audit_job'
  );

update system.job_runs j
set shadow_epoch_id=e.id
from model.shadow_epochs e
where j.shadow_epoch_id is null
  and e.status='ACTIVE'
  and j.started_at >= e.started_at
  and (e.ended_at is null or j.started_at <= e.ended_at);

create index if not exists idx_job_runs_kind_time
  on system.job_runs(run_kind,started_at desc);
create index if not exists idx_job_runs_epoch_name_time
  on system.job_runs(shadow_epoch_id,job_name,started_at desc);

create or replace function system.annotate_job_run_provenance()
returns trigger
language plpgsql
as $$
declare
  root_job text := nullif(current_setting('rosa.root_job_name', true),'');
  root_kind text := nullif(current_setting('rosa.run_kind', true),'');
  active_epoch_id bigint;
begin
  if root_kind is not null then
    if root_kind='scheduled' and root_job=NEW.job_name then
      NEW.run_kind := 'scheduled';
    elsif root_job='weekly_job' and NEW.job_name in ('macro_job','sec_event_job') then
      NEW.run_kind := 'maintenance';
    elsif (root_job='daily_crypto_job' and NEW.job_name='hourly_job')
       or (root_job='daily_ura_job' and NEW.job_name='sec_event_job') then
      NEW.run_kind := 'dependency';
    elsif root_job=NEW.job_name and root_kind in ('manual','test','backfill','development') then
      NEW.run_kind := root_kind;
    elsif root_job is not null and root_job<>NEW.job_name then
      NEW.run_kind := 'dependency';
    else
      NEW.run_kind := root_kind;
    end if;
  end if;

  if NEW.shadow_epoch_id is null then
    select id into active_epoch_id
    from model.shadow_epochs
    where status='ACTIVE'
      and started_at <= NEW.started_at
      and (ended_at is null or ended_at >= NEW.started_at)
    order by started_at desc
    limit 1;
    NEW.shadow_epoch_id := active_epoch_id;
  end if;

  NEW.details := coalesce(NEW.details,'{}'::jsonb)
    || jsonb_build_object('run_kind',NEW.run_kind)
    || case when root_job is not null then jsonb_build_object('root_job_name',root_job) else '{}'::jsonb end;
  return NEW;
end;
$$;

drop trigger if exists trg_job_runs_provenance on system.job_runs;
create trigger trg_job_runs_provenance
before insert on system.job_runs
for each row execute function system.annotate_job_run_provenance();

commit;
