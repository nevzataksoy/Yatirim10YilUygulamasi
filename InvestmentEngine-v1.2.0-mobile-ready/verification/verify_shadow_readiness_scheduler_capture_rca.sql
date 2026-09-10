-- Shadow Readiness scheduler capture RCA — production READ-ONLY
--
-- Amaç:
--   verify_shadow_readiness_provenance_baseline.sql çıktısında görülen scheduler
--   sayım farkını, released cadence ile aynı 7 günlük sabit pencere üzerinde
--   dakika/fire bazında açıklamak.
--
-- Bu sorgu:
--   * yalnızca SELECT / CTE kullanır,
--   * INSERT / UPDATE / DELETE yapmaz,
--   * migration / DDL çalıştırmaz,
--   * scheduler, readiness threshold, model kararı veya LIVE durumunu değiştirmez.
--
-- Sabit baseline penceresi:
--   checked_at = 2026-09-10 19:49:26.322356+00
--   window_start = checked_at - 7 days
--
-- Cadence doğrulama kopyası yalnız bu READ-ONLY RCA sorgusuna aittir.
-- Runtime source-of-truth app/schedule_contract.py olarak kalır.
-- Europe/Istanbul yerel saat sözleşmesi:
--   hourly_job        her saat :05
--   macro_job         00:15, 06:15, 12:15, 18:15
--   sec_event_job     her saat :35
--   daily_crypto_job  05:20
--   daily_ura_job     02:40
--   daily_fx_job      Pzt-Cum 16:30
--   weekly_job        Cumartesi 08:00
--   monthly_audit_job ayın 1'i 09:00
--
-- Success semantiği değişmez:
--   OK / DEGRADED / SKIPPED = completed/successful

with
params as (
  select
    timestamptz '2026-09-10 19:49:26.322356+00' as checked_at,
    timestamptz '2026-09-10 19:49:26.322356+00' - interval '7 days' as window_start,
    'Europe/Istanbul'::text as timezone_name,
    '1.2.0'::text as model_version
),
active_epoch as (
  select
    e.id,
    e.epoch_key,
    e.model_version,
    e.started_at,
    e.ended_at,
    e.status
  from model.shadow_epochs e
  cross join params p
  where e.status = 'ACTIVE'
    and e.model_version = p.model_version
  order by e.started_at desc
  limit 1
),
minute_grid as (
  select
    gs as minute_utc,
    gs at time zone p.timezone_name as local_minute
  from params p
  cross join lateral generate_series(
    date_trunc('minute', p.window_start),
    date_trunc('minute', p.checked_at),
    interval '1 minute'
  ) as gs
  where gs >= p.window_start
    and gs <= p.checked_at
),
expected_fires as (
  select minute_utc as expected_at_utc, local_minute, 'hourly_job'::text as job_name
  from minute_grid
  where extract(minute from local_minute) = 5

  union all

  select minute_utc, local_minute, 'macro_job'
  from minute_grid
  where extract(minute from local_minute) = 15
    and extract(hour from local_minute) in (0, 6, 12, 18)

  union all

  select minute_utc, local_minute, 'sec_event_job'
  from minute_grid
  where extract(minute from local_minute) = 35

  union all

  select minute_utc, local_minute, 'daily_crypto_job'
  from minute_grid
  where extract(hour from local_minute) = 5
    and extract(minute from local_minute) = 20

  union all

  select minute_utc, local_minute, 'daily_ura_job'
  from minute_grid
  where extract(hour from local_minute) = 2
    and extract(minute from local_minute) = 40

  union all

  select minute_utc, local_minute, 'daily_fx_job'
  from minute_grid
  where extract(isodow from local_minute) between 1 and 5
    and extract(hour from local_minute) = 16
    and extract(minute from local_minute) = 30

  union all

  select minute_utc, local_minute, 'weekly_job'
  from minute_grid
  where extract(isodow from local_minute) = 6
    and extract(hour from local_minute) = 8
    and extract(minute from local_minute) = 0

  union all

  select minute_utc, local_minute, 'monthly_audit_job'
  from minute_grid
  where extract(day from local_minute) = 1
    and extract(hour from local_minute) = 9
    and extract(minute from local_minute) = 0
),
actual_scheduler as (
  select
    j.id,
    j.job_name,
    j.started_at,
    j.finished_at,
    j.status,
    j.run_kind,
    j.shadow_epoch_id,
    nullif(j.details ->> 'root_job_name', '') as root_job_name,
    date_trunc('minute', j.started_at) as fire_minute_utc
  from system.job_runs j
  cross join params p
  where j.started_at >= p.window_start
    and j.started_at <= p.checked_at
    and j.shadow_epoch_id = (select id from active_epoch)
    and j.run_kind in ('scheduled', 'scheduled_legacy')
    and j.job_name in (
      'hourly_job',
      'macro_job',
      'sec_event_job',
      'daily_crypto_job',
      'daily_ura_job',
      'daily_fx_job',
      'weekly_job',
      'monthly_audit_job'
    )
),
actual_per_fire as (
  select
    a.job_name,
    a.fire_minute_utc,
    count(*)::bigint as actual_rows,
    count(*) filter (
      where a.status in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as successful_rows,
    count(*) filter (where a.status = 'ERROR')::bigint as error_rows,
    min(a.started_at) as first_started_at,
    max(a.started_at) as last_started_at,
    array_agg(a.id order by a.id) as job_run_ids,
    array_agg(a.run_kind order by a.id) as run_kinds,
    array_agg(a.status order by a.id) as statuses
  from actual_scheduler a
  group by a.job_name, a.fire_minute_utc
),
fire_comparison as (
  select
    e.job_name,
    e.expected_at_utc,
    e.local_minute as expected_at_local,
    coalesce(a.actual_rows, 0)::bigint as actual_rows,
    coalesce(a.successful_rows, 0)::bigint as successful_rows,
    coalesce(a.error_rows, 0)::bigint as error_rows,
    a.first_started_at,
    a.last_started_at,
    a.job_run_ids,
    a.run_kinds,
    a.statuses
  from expected_fires e
  left join actual_per_fire a
    on a.job_name = e.job_name
   and a.fire_minute_utc = e.expected_at_utc
),
job_summary as (
  select
    f.job_name,
    count(*)::bigint as expected_fires,
    count(*) filter (where f.actual_rows > 0)::bigint as captured_fires,
    count(*) filter (where f.successful_rows > 0)::bigint as completed_fires,
    count(*) filter (where f.actual_rows = 0)::bigint as missing_fires,
    count(*) filter (
      where f.actual_rows > 0 and f.successful_rows = 0
    )::bigint as captured_but_unsuccessful_fires,
    coalesce(sum(f.actual_rows), 0)::bigint as actual_rows,
    coalesce(sum(f.successful_rows), 0)::bigint as successful_rows,
    coalesce(sum(greatest(f.actual_rows - 1, 0)), 0)::bigint as duplicate_extra_rows,
    round(
      count(*) filter (where f.actual_rows > 0)::numeric / nullif(count(*), 0)::numeric,
      6
    ) as fire_capture_rate,
    round(
      count(*) filter (where f.successful_rows > 0)::numeric / nullif(count(*), 0)::numeric,
      6
    ) as fire_completed_rate,
    round(
      coalesce(sum(f.successful_rows), 0)::numeric / nullif(count(*), 0)::numeric,
      6
    ) as row_based_completed_rate
  from fire_comparison f
  group by f.job_name
),
overall_summary as (
  select
    '__TOTAL__'::text as job_name,
    sum(expected_fires)::bigint as expected_fires,
    sum(captured_fires)::bigint as captured_fires,
    sum(completed_fires)::bigint as completed_fires,
    sum(missing_fires)::bigint as missing_fires,
    sum(captured_but_unsuccessful_fires)::bigint as captured_but_unsuccessful_fires,
    sum(actual_rows)::bigint as actual_rows,
    sum(successful_rows)::bigint as successful_rows,
    sum(duplicate_extra_rows)::bigint as duplicate_extra_rows,
    round(sum(captured_fires)::numeric / nullif(sum(expected_fires), 0)::numeric, 6) as fire_capture_rate,
    round(sum(completed_fires)::numeric / nullif(sum(expected_fires), 0)::numeric, 6) as fire_completed_rate,
    round(sum(successful_rows)::numeric / nullif(sum(expected_fires), 0)::numeric, 6) as row_based_completed_rate
  from job_summary
),
all_summary as (
  select 0::int as item_order, o.* from overall_summary o
  union all
  select
    row_number() over (order by j.job_name)::int,
    j.*
  from job_summary j
),
incomplete_fires as (
  select
    f.*,
    case
      when f.actual_rows = 0 then 'MISSING_JOB_RUN_ROW'
      when f.successful_rows = 0 then 'CAPTURED_WITHOUT_SUCCESS_STATUS'
      else 'OTHER'
    end as reason,
    (
      select max(a.started_at)
      from actual_scheduler a
      where a.job_name = f.job_name
        and a.started_at < f.expected_at_utc
    ) as previous_actual_started_at,
    (
      select min(a.started_at)
      from actual_scheduler a
      where a.job_name = f.job_name
        and a.started_at > f.expected_at_utc
    ) as next_actual_started_at
  from fire_comparison f
  where f.actual_rows = 0
     or f.successful_rows = 0
),
duplicate_fire_rows as (
  select *
  from actual_per_fire
  where actual_rows > 1
),
off_cadence_rows as (
  select
    a.*,
    a.started_at at time zone (select timezone_name from params) as started_at_local
  from actual_scheduler a
  left join expected_fires e
    on e.job_name = a.job_name
   and e.expected_at_utc = a.fire_minute_utc
  where e.job_name is null
),
result_rows as (
  select
    10::int as section_order,
    0::int as item_order,
    'METADATA'::text as section,
    jsonb_build_object(
      'checked_at', p.checked_at,
      'window_start', p.window_start,
      'window_days', 7,
      'timezone', p.timezone_name,
      'model_version', p.model_version,
      'active_epoch_found', (select count(*) = 1 from active_epoch),
      'active_epoch_id', (select id from active_epoch),
      'active_epoch_key', (select epoch_key from active_epoch),
      'active_epoch_started_at', (select started_at from active_epoch),
      'success_statuses', jsonb_build_array('OK', 'DEGRADED', 'SKIPPED'),
      'run_kinds', jsonb_build_array('scheduled', 'scheduled_legacy'),
      'runtime_schedule_source', 'app/schedule_contract.py'
    ) as payload
  from params p

  union all

  select
    20,
    s.item_order,
    'EXPECTED_VS_ACTUAL_BY_JOB',
    jsonb_build_object(
      'job_name', s.job_name,
      'expected_fires', s.expected_fires,
      'captured_fires', s.captured_fires,
      'completed_fires', s.completed_fires,
      'missing_fires', s.missing_fires,
      'captured_but_unsuccessful_fires', s.captured_but_unsuccessful_fires,
      'actual_rows', s.actual_rows,
      'successful_rows', s.successful_rows,
      'duplicate_extra_rows', s.duplicate_extra_rows,
      'fire_capture_rate', s.fire_capture_rate,
      'fire_completed_rate', s.fire_completed_rate,
      'row_based_completed_rate', s.row_based_completed_rate
    )
  from all_summary s

  union all

  select
    30,
    row_number() over (order by i.expected_at_utc, i.job_name)::int,
    'INCOMPLETE_EXPECTED_FIRES',
    jsonb_build_object(
      'job_name', i.job_name,
      'reason', i.reason,
      'expected_at_utc', i.expected_at_utc,
      'expected_at_local', i.expected_at_local,
      'actual_rows', i.actual_rows,
      'successful_rows', i.successful_rows,
      'error_rows', i.error_rows,
      'job_run_ids', i.job_run_ids,
      'run_kinds', i.run_kinds,
      'statuses', i.statuses,
      'previous_actual_started_at', i.previous_actual_started_at,
      'next_actual_started_at', i.next_actual_started_at
    )
  from incomplete_fires i

  union all

  select
    40,
    row_number() over (order by d.fire_minute_utc, d.job_name)::int,
    'DUPLICATE_SCHEDULER_FIRE_ROWS',
    jsonb_build_object(
      'job_name', d.job_name,
      'fire_minute_utc', d.fire_minute_utc,
      'actual_rows', d.actual_rows,
      'successful_rows', d.successful_rows,
      'error_rows', d.error_rows,
      'first_started_at', d.first_started_at,
      'last_started_at', d.last_started_at,
      'job_run_ids', d.job_run_ids,
      'run_kinds', d.run_kinds,
      'statuses', d.statuses
    )
  from duplicate_fire_rows d

  union all

  select
    50,
    row_number() over (order by o.started_at, o.id)::int,
    'OFF_CADENCE_SCHEDULER_ROWS',
    jsonb_build_object(
      'id', o.id,
      'job_name', o.job_name,
      'started_at', o.started_at,
      'started_at_local', o.started_at_local,
      'status', o.status,
      'run_kind', o.run_kind,
      'shadow_epoch_id', o.shadow_epoch_id,
      'root_job_name', o.root_job_name,
      'fire_minute_utc', o.fire_minute_utc
    )
  from off_cadence_rows o
)
select section, payload
from result_rows
order by section_order, item_order;
