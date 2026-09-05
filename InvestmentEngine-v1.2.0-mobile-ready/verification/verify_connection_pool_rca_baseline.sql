-- Post-Shadow P0 / Gate C — Connection-pool RCA baseline
-- READ ONLY: every block is SELECT-only.
--
-- Purpose:
--   1. Locate real pool-acquisition timeout failures.
--   2. Show jobs overlapping those failures.
--   3. Quantify job duration tails before changing pool sizing.
--   4. Preserve scheduler/run provenance in every diagnostic row.
--
-- Do NOT change max_size, timeout, retries, thresholds, weights or scheduler
-- behavior based on these queries alone.

-- ============================================================
-- BLOCK A — Pool-acquisition timeout rows, last 30 days
-- ============================================================
select
  id,
  job_name,
  run_kind,
  status,
  started_at,
  finished_at,
  round(extract(epoch from (finished_at - started_at))::numeric, 3) as duration_seconds,
  shadow_epoch_id,
  details->>'root_job_name' as root_job_name,
  message
from system.job_runs
where started_at >= now() - interval '30 days'
  and (
    message ilike '%couldn''t get a connection%'
    or message ilike '%pooltimeout%'
    or message ilike '%pool timeout%'
    or message ilike '%connection after 10%'
  )
order by started_at desc;

-- ============================================================
-- BLOCK B — All ERROR rows, last 30 days
-- Keeps non-pool errors visible instead of forcing every failure into the
-- connection-pool hypothesis.
-- ============================================================
select
  id,
  job_name,
  run_kind,
  started_at,
  finished_at,
  round(extract(epoch from (finished_at - started_at))::numeric, 3) as duration_seconds,
  shadow_epoch_id,
  details->>'root_job_name' as root_job_name,
  message
from system.job_runs
where started_at >= now() - interval '30 days'
  and status = 'ERROR'
order by started_at desc;

-- ============================================================
-- BLOCK C — Jobs overlapping each pool timeout
-- Includes a two-minute context margin around the failed run so nearby
-- scheduler collisions remain visible even if timestamps are slightly offset.
-- ============================================================
with pool_errors as (
  select
    id,
    job_name,
    started_at,
    coalesce(finished_at, started_at) as finished_at,
    message
  from system.job_runs
  where started_at >= now() - interval '30 days'
    and (
      message ilike '%couldn''t get a connection%'
      or message ilike '%pooltimeout%'
      or message ilike '%pool timeout%'
      or message ilike '%connection after 10%'
    )
)
select
  e.id as error_id,
  e.job_name as error_job,
  e.started_at as error_started_at,
  e.finished_at as error_finished_at,
  j.id as nearby_job_id,
  j.job_name as nearby_job,
  j.run_kind as nearby_run_kind,
  j.status as nearby_status,
  j.started_at as nearby_started_at,
  j.finished_at as nearby_finished_at,
  round(extract(epoch from (j.finished_at - j.started_at))::numeric, 3) as nearby_duration_seconds,
  j.shadow_epoch_id,
  j.details->>'root_job_name' as nearby_root_job_name,
  j.message as nearby_message
from pool_errors e
join system.job_runs j
  on j.started_at <= e.finished_at + interval '2 minutes'
 and coalesce(j.finished_at, j.started_at) >= e.started_at - interval '2 minutes'
order by e.started_at desc, j.started_at;

-- ============================================================
-- BLOCK D — Duration distribution by job/run-kind/status
-- Long p95/max durations are evidence to inspect; they are not proof that the
-- pool size itself is wrong.
-- ============================================================
select
  job_name,
  run_kind,
  status,
  count(*) as runs,
  round(avg(extract(epoch from (finished_at - started_at)))::numeric, 3) as avg_seconds,
  round(percentile_cont(0.50) within group (
    order by extract(epoch from (finished_at - started_at))
  )::numeric, 3) as p50_seconds,
  round(percentile_cont(0.95) within group (
    order by extract(epoch from (finished_at - started_at))
  )::numeric, 3) as p95_seconds,
  round(max(extract(epoch from (finished_at - started_at)))::numeric, 3) as max_seconds
from system.job_runs
where started_at >= now() - interval '30 days'
  and finished_at is not null
group by job_name, run_kind, status
order by p95_seconds desc nulls last, job_name, run_kind, status;

-- ============================================================
-- BLOCK E — Highest observed job concurrency from recorded run intervals
-- This uses job_runs intervals, so nested maintenance/dependency rows remain
-- visible. It does not infer DB connections held; that requires runtime pool
-- instrumentation in the next RCA sub-gate.
-- ============================================================
with intervals as (
  select id, started_at, finished_at
  from system.job_runs
  where started_at >= now() - interval '30 days'
    and finished_at is not null
    and finished_at >= started_at
), events as (
  select started_at as event_at, 1 as delta from intervals
  union all
  select finished_at as event_at, -1 as delta from intervals
), collapsed as (
  select event_at, sum(delta) as delta
  from events
  group by event_at
), concurrency as (
  select
    event_at,
    sum(delta) over (order by event_at rows unbounded preceding) as concurrent_runs
  from collapsed
)
select event_at, concurrent_runs
from concurrency
order by concurrent_runs desc, event_at desc
limit 30;

-- ============================================================
-- BLOCK F — Runs active around the top concurrency timestamps
-- Run this after BLOCK E only if a timestamp needs deeper inspection.
-- Replace the timestamp literal with one BLOCK E event_at value.
-- ============================================================
-- select
--   id, job_name, run_kind, status, started_at, finished_at,
--   shadow_epoch_id, details->>'root_job_name' as root_job_name, message
-- from system.job_runs
-- where started_at <= timestamptz '2026-09-04 00:00:00+00'
--   and finished_at >= timestamptz '2026-09-04 00:00:00+00'
-- order by started_at;
