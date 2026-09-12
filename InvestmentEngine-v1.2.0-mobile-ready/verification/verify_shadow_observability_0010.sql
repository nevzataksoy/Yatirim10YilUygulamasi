-- Post-Shadow P0.1 — Runtime / Observability Deployment Verification
-- Model: 1.2.0
-- Mode must remain SHADOW. Realtime Execution must remain OFF.
-- This file is READ-ONLY: it contains SELECT statements only.
--
-- Run BLOCK A first in Supabase SQL Editor.
-- If every *_ok column is true, run BLOCK B-D.
-- If any BLOCK A result is false, stop there and return that result before applying migration 0010.

-- ============================================================
-- BLOCK A — Migration 0010 schema/object presence
-- Safe even when migration 0010 has not been applied.
-- ============================================================
select
  to_regclass('model.shadow_epochs') is not null as shadow_epochs_table_ok,
  exists (
    select 1
    from information_schema.columns
    where table_schema='system'
      and table_name='job_runs'
      and column_name='run_kind'
  ) as job_runs_run_kind_ok,
  exists (
    select 1
    from information_schema.columns
    where table_schema='system'
      and table_name='job_runs'
      and column_name='shadow_epoch_id'
  ) as job_runs_shadow_epoch_id_ok,
  exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='system'
      and p.proname='annotate_job_run_provenance'
  ) as provenance_function_ok,
  exists (
    select 1
    from pg_trigger t
    join pg_class c on c.oid=t.tgrelid
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='system'
      and c.relname='job_runs'
      and t.tgname='trg_job_runs_provenance'
      and not t.tgisinternal
  ) as provenance_trigger_ok;

-- ============================================================
-- BLOCK B — Shadow epoch state
-- Run only if BLOCK A is fully true.
-- Expected: one ACTIVE v1.2.0 epoch recovered from real decisions.
-- ============================================================
select
  id,
  epoch_key,
  model_version,
  started_at,
  ended_at,
  status,
  reason,
  details
from model.shadow_epochs
order by started_at desc;

-- ============================================================
-- BLOCK C — Recent run-kind/status accounting
-- Run only if BLOCK A is fully true.
-- New deployed scheduler roots should eventually appear as run_kind='scheduled'.
-- Historical scheduler rows migrated by 0010 may remain 'scheduled_legacy'.
-- ============================================================
select
  run_kind,
  job_name,
  status,
  count(*) as run_count,
  min(started_at) as first_started_at,
  max(started_at) as last_started_at
from system.job_runs
where started_at >= now() - interval '7 days'
group by run_kind, job_name, status
order by run_kind, job_name, status;

-- ============================================================
-- BLOCK D — Latest provenance-bearing rows
-- root_job_name is written by the new runtime through PostgreSQL local GUCs.
-- This is the key source-vs-deployed-runtime check.
-- ============================================================
select
  id,
  started_at,
  finished_at,
  job_name,
  run_kind,
  status,
  shadow_epoch_id,
  details->>'root_job_name' as root_job_name,
  message
from system.job_runs
order by started_at desc
limit 50;

-- ============================================================
-- BLOCK E — Focused consistency diagnostics
-- These queries do not change any rows.
-- ============================================================

-- New-style scheduled roots with runtime provenance.
select
  count(*) as scheduled_with_matching_root_job
from system.job_runs
where run_kind='scheduled'
  and details->>'root_job_name'=job_name;

-- Nested weekly maintenance rows must not be counted as scheduler roots.
select
  job_name,
  count(*) as maintenance_rows
from system.job_runs
where run_kind='maintenance'
  and job_name in ('macro_job','sec_event_job')
group by job_name
order by job_name;

-- Known dependency rows must stay separate from scheduler roots.
select
  job_name,
  count(*) as dependency_rows
from system.job_runs
where run_kind='dependency'
  and job_name in ('hourly_job','sec_event_job')
group by job_name
order by job_name;

-- Preserve real scheduler ERROR evidence for root-cause work.
select
  id,
  started_at,
  job_name,
  run_kind,
  status,
  message,
  details->>'root_job_name' as root_job_name,
  shadow_epoch_id
from system.job_runs
where status='ERROR'
  and started_at >= now() - interval '30 days'
order by started_at desc;

-- ============================================================
-- BLOCK F — Runtime observability persistence / released readiness separation
-- Run after deploying the new binary and executing --shadow-observability.
-- Expected: SHADOW_OBSERVABILITY exists in both validation_runs and snapshot.
-- Existing SHADOW_READINESS snapshot remains a separate row/type.
-- ============================================================

select
  id,
  validation_type,
  system,
  model_version,
  status,
  started_at,
  finished_at,
  details
from model.validation_runs
where validation_type in ('SHADOW_OBSERVABILITY','SHADOW_READINESS')
order by started_at desc
limit 20;

select
  validation_type,
  system,
  generated_at,
  model_version,
  status,
  details
from public.model_validation_snapshot
where validation_type in ('SHADOW_OBSERVABILITY','SHADOW_READINESS')
order by validation_type, system;

-- Runtime CLI provenance row: this should appear as manual and carry root_job_name.
select
  id,
  started_at,
  job_name,
  run_kind,
  status,
  shadow_epoch_id,
  details->>'root_job_name' as root_job_name,
  message
from system.job_runs
where job_name='shadow_observability'
order by started_at desc
limit 10;
