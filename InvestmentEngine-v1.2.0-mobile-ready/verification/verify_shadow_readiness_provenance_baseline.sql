-- Shadow Readiness provenance baseline — production READ-ONLY
--
-- Amaç:
--   Released SHADOW_READINESS job-health hesabının son 7 günlük geniş kapsamını,
--   scheduler provenance kapsamlarıyla 7 ve 30 günlük pencerelerde yan yana ölçmek.
--
-- Bu sorgu:
--   * yalnızca SELECT / CTE kullanır,
--   * INSERT / UPDATE / DELETE yapmaz,
--   * migration / DDL çalıştırmaz,
--   * VACUUM / VACUUM FULL çalıştırmaz,
--   * scheduler cadence, readiness threshold, model kararı veya LIVE durumunu değiştirmez.
--
-- Karşılaştırılan scope'lar:
--   CURRENT
--     Released Repository.shadow_readiness_stats() job sorgusunun provenance semantiği:
--     realtime_test hariç, pencere içindeki tüm run_kind / epoch kayıtları.
--   SCHEDULED_ONLY
--     CURRENT kapsamına yalnız run_kind='scheduled' filtresi eklenmiş karşı-olgusal görünüm.
--   ACTIVE_EPOCH_SCHEDULED
--     Aktif Model 1.2.0 Shadow Epoch + run_kind='scheduled' + checked_at üst sınırı.
--   ACTIVE_EPOCH_SCHEDULED_LEGACY
--     Aktif Model 1.2.0 Shadow Epoch + run_kind in ('scheduled','scheduled_legacy')
--     + checked_at üst sınırı; mevcut SHADOW_OBSERVABILITY provenance kapsamına denktir.
--
-- Başarı semantiği released classifier ile aynıdır:
--   status in ('OK','DEGRADED','SKIPPED') => successful
--
-- Not:
--   Bu baseline scheduler'ın beklenen fire sayısını yeniden üretmez. Cadence için tek kaynak
--   app/schedule_contract.py olarak kalır. Bu sorgu yalnızca kaydedilmiş system.job_runs
--   provenance farkını ölçer.

with
params as (
  select
    now() as checked_at,
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
windows as (
  select 7::int as window_days,
         (select checked_at from params) - interval '7 days' as window_start
  union all
  select 30::int,
         (select checked_at from params) - interval '30 days'
),
scope_defs as (
  select *
  from (
    values
      (1, 'CURRENT'::text),
      (2, 'SCHEDULED_ONLY'::text),
      (3, 'ACTIVE_EPOCH_SCHEDULED'::text),
      (4, 'ACTIVE_EPOCH_SCHEDULED_LEGACY'::text)
  ) as v(scope_order, scope)
),
base_30d as (
  select
    j.id,
    j.job_name,
    j.started_at,
    j.finished_at,
    j.status,
    j.run_kind,
    j.shadow_epoch_id,
    nullif(j.details ->> 'root_job_name', '') as root_job_name,
    j.message
  from system.job_runs j
  cross join params p
  where j.started_at >= p.checked_at - interval '30 days'
    and j.job_name <> 'realtime_test'
),
scope_rows as (
  select
    w.window_days,
    'CURRENT'::text as scope,
    b.*
  from windows w
  join base_30d b on b.started_at >= w.window_start

  union all

  select
    w.window_days,
    'SCHEDULED_ONLY'::text as scope,
    b.*
  from windows w
  join base_30d b on b.started_at >= w.window_start
  where b.run_kind = 'scheduled'

  union all

  select
    w.window_days,
    'ACTIVE_EPOCH_SCHEDULED'::text as scope,
    b.*
  from windows w
  join base_30d b on b.started_at >= w.window_start
  where b.started_at <= (select checked_at from params)
    and b.run_kind = 'scheduled'
    and b.shadow_epoch_id = (select id from active_epoch)

  union all

  select
    w.window_days,
    'ACTIVE_EPOCH_SCHEDULED_LEGACY'::text as scope,
    b.*
  from windows w
  join base_30d b on b.started_at >= w.window_start
  where b.started_at <= (select checked_at from params)
    and b.run_kind in ('scheduled', 'scheduled_legacy')
    and b.shadow_epoch_id = (select id from active_epoch)
),
scope_comparison_raw as (
  select
    window_days,
    scope,
    count(*)::bigint as rows,
    count(*) filter (
      where status in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as successful_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED') or status is null
    )::bigint as unsuccessful_rows,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (where status = 'ERROR')::bigint as error_rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    round(
      case
        when count(*) = 0 then 0::numeric
        else count(*) filter (
          where status in ('OK', 'DEGRADED', 'SKIPPED')
        )::numeric / count(*)::numeric
      end,
      6
    ) as success_rate
  from scope_rows
  group by window_days, scope
),
scope_comparison as (
  select
    w.window_days,
    d.scope_order,
    d.scope,
    coalesce(r.rows, 0)::bigint as rows,
    coalesce(r.successful_rows, 0)::bigint as successful_rows,
    coalesce(r.unsuccessful_rows, 0)::bigint as unsuccessful_rows,
    coalesce(r.ok_rows, 0)::bigint as ok_rows,
    coalesce(r.degraded_rows, 0)::bigint as degraded_rows,
    coalesce(r.skipped_rows, 0)::bigint as skipped_rows,
    coalesce(r.error_rows, 0)::bigint as error_rows,
    r.first_started_at,
    r.last_started_at,
    coalesce(r.success_rate, 0::numeric) as success_rate
  from windows w
  cross join scope_defs d
  left join scope_comparison_raw r
    on r.window_days = w.window_days
   and r.scope = d.scope
),
provenance_breakdown as (
  select
    w.window_days,
    b.run_kind,
    b.status,
    b.shadow_epoch_id,
    count(*)::bigint as rows,
    min(b.started_at) as first_started_at,
    max(b.started_at) as last_started_at
  from windows w
  join base_30d b on b.started_at >= w.window_start
  group by
    w.window_days,
    b.run_kind,
    b.status,
    b.shadow_epoch_id
),
job_root_breakdown as (
  select
    w.window_days,
    b.job_name,
    b.root_job_name,
    b.run_kind,
    b.status,
    b.shadow_epoch_id,
    count(*)::bigint as rows,
    min(b.started_at) as first_started_at,
    max(b.started_at) as last_started_at
  from windows w
  join base_30d b on b.started_at >= w.window_start
  group by
    w.window_days,
    b.job_name,
    b.root_job_name,
    b.run_kind,
    b.status,
    b.shadow_epoch_id
),
provenance_gaps as (
  select
    w.window_days,
    count(*)::bigint as current_rows,
    count(*) filter (
      where b.started_at > (select checked_at from params)
    )::bigint as future_started_rows,
    count(*) filter (where b.run_kind is null)::bigint as null_run_kind_rows,
    count(*) filter (where b.shadow_epoch_id is null)::bigint as null_shadow_epoch_rows,
    count(*) filter (
      where b.run_kind is null
         or b.run_kind not in ('scheduled', 'scheduled_legacy')
    )::bigint as non_scheduler_or_unknown_rows,
    count(*) filter (
      where b.run_kind in ('manual', 'test', 'backfill', 'development')
    )::bigint as explicit_manual_test_backfill_development_rows,
    count(*) filter (
      where b.run_kind in ('dependency', 'maintenance')
    )::bigint as dependency_or_maintenance_rows,
    count(*) filter (
      where b.run_kind in ('dependency', 'maintenance')
        and b.root_job_name is null
    )::bigint as dependency_or_maintenance_without_root_rows,
    count(*) filter (
      where b.run_kind in ('scheduled', 'scheduled_legacy')
        and (
          (select id from active_epoch) is null
          or b.shadow_epoch_id is distinct from (select id from active_epoch)
        )
    )::bigint as scheduler_rows_outside_active_epoch,
    count(*) filter (
      where b.run_kind = 'scheduled_legacy'
    )::bigint as scheduled_legacy_rows
  from windows w
  join base_30d b on b.started_at >= w.window_start
  group by w.window_days
),
excluded_from_active_epoch_scheduler as (
  select
    case
      when b.started_at > (select checked_at from params) then 'FUTURE_STARTED_AT'
      when b.run_kind is null then 'MISSING_RUN_KIND'
      when b.run_kind not in ('scheduled', 'scheduled_legacy') then 'NON_SCHEDULER_RUN_KIND'
      when (select id from active_epoch) is null then 'ACTIVE_EPOCH_NOT_FOUND'
      when b.shadow_epoch_id is null then 'MISSING_SHADOW_EPOCH'
      when b.shadow_epoch_id is distinct from (select id from active_epoch) then 'DIFFERENT_SHADOW_EPOCH'
      else 'OTHER'
    end as excluded_reason,
    b.job_name,
    b.root_job_name,
    b.run_kind,
    b.status,
    b.shadow_epoch_id,
    count(*)::bigint as rows,
    array_agg(b.id order by b.id) as job_run_ids,
    min(b.started_at) as first_started_at,
    max(b.started_at) as last_started_at
  from base_30d b
  where
    b.started_at > (select checked_at from params)
    or b.run_kind is null
    or (select id from active_epoch) is null
    or b.run_kind not in ('scheduled', 'scheduled_legacy')
    or b.shadow_epoch_id is distinct from (select id from active_epoch)
  group by
    excluded_reason,
    b.job_name,
    b.root_job_name,
    b.run_kind,
    b.status,
    b.shadow_epoch_id
),
scheduled_legacy_profile as (
  select
    j.job_name,
    nullif(j.details ->> 'root_job_name', '') as root_job_name,
    j.status,
    j.shadow_epoch_id,
    count(*)::bigint as total_rows,
    count(*) filter (
      where j.started_at >= (select checked_at from params) - interval '7 days'
    )::bigint as rows_last_7d,
    count(*) filter (
      where j.started_at >= (select checked_at from params) - interval '30 days'
    )::bigint as rows_last_30d,
    min(j.started_at) as first_started_at,
    max(j.started_at) as last_started_at
  from system.job_runs j
  where j.run_kind = 'scheduled_legacy'
    and j.job_name <> 'realtime_test'
  group by
    j.job_name,
    nullif(j.details ->> 'root_job_name', ''),
    j.status,
    j.shadow_epoch_id
),
result_rows as (
  select
    10::int as section_order,
    0::int as item_order,
    'METADATA'::text as section,
    jsonb_build_object(
      'checked_at', p.checked_at,
      'model_version', p.model_version,
      'active_epoch_found', (select count(*) = 1 from active_epoch),
      'active_epoch_id', (select id from active_epoch),
      'active_epoch_key', (select epoch_key from active_epoch),
      'active_epoch_model_version', (select model_version from active_epoch),
      'active_epoch_started_at', (select started_at from active_epoch),
      'active_epoch_ended_at', (select ended_at from active_epoch),
      'active_epoch_status', (select status from active_epoch),
      'success_statuses', jsonb_build_array('OK', 'DEGRADED', 'SKIPPED'),
      'realtime_test_excluded', true
    ) as payload
  from params p

  union all

  select
    20,
    s.scope_order,
    'SCOPE_COMPARISON',
    jsonb_build_object(
      'window_days', s.window_days,
      'scope', s.scope,
      'rows', s.rows,
      'successful_rows', s.successful_rows,
      'unsuccessful_rows', s.unsuccessful_rows,
      'ok_rows', s.ok_rows,
      'degraded_rows', s.degraded_rows,
      'skipped_rows', s.skipped_rows,
      'error_rows', s.error_rows,
      'success_rate', s.success_rate,
      'first_started_at', s.first_started_at,
      'last_started_at', s.last_started_at
    )
  from scope_comparison s

  union all

  select
    30,
    0,
    'PROVENANCE_GAPS',
    jsonb_build_object(
      'window_days', g.window_days,
      'current_rows', g.current_rows,
      'future_started_rows', g.future_started_rows,
      'null_run_kind_rows', g.null_run_kind_rows,
      'null_shadow_epoch_rows', g.null_shadow_epoch_rows,
      'non_scheduler_or_unknown_rows', g.non_scheduler_or_unknown_rows,
      'explicit_manual_test_backfill_development_rows', g.explicit_manual_test_backfill_development_rows,
      'dependency_or_maintenance_rows', g.dependency_or_maintenance_rows,
      'dependency_or_maintenance_without_root_rows', g.dependency_or_maintenance_without_root_rows,
      'scheduler_rows_outside_active_epoch', g.scheduler_rows_outside_active_epoch,
      'scheduled_legacy_rows', g.scheduled_legacy_rows
    )
  from provenance_gaps g

  union all

  select
    40,
    0,
    'PROVENANCE_BREAKDOWN',
    jsonb_build_object(
      'window_days', p.window_days,
      'run_kind', p.run_kind,
      'status', p.status,
      'shadow_epoch_id', p.shadow_epoch_id,
      'rows', p.rows,
      'first_started_at', p.first_started_at,
      'last_started_at', p.last_started_at
    )
  from provenance_breakdown p

  union all

  select
    50,
    0,
    'JOB_ROOT_BREAKDOWN',
    jsonb_build_object(
      'window_days', j.window_days,
      'job_name', j.job_name,
      'root_job_name', j.root_job_name,
      'run_kind', j.run_kind,
      'status', j.status,
      'shadow_epoch_id', j.shadow_epoch_id,
      'rows', j.rows,
      'first_started_at', j.first_started_at,
      'last_started_at', j.last_started_at
    )
  from job_root_breakdown j

  union all

  select
    60,
    0,
    'CURRENT_EXCLUDED_FROM_ACTIVE_EPOCH_SCHEDULER_30D',
    jsonb_build_object(
      'excluded_reason', e.excluded_reason,
      'job_name', e.job_name,
      'root_job_name', e.root_job_name,
      'run_kind', e.run_kind,
      'status', e.status,
      'shadow_epoch_id', e.shadow_epoch_id,
      'rows', e.rows,
      'job_run_ids', to_jsonb(e.job_run_ids),
      'first_started_at', e.first_started_at,
      'last_started_at', e.last_started_at
    )
  from excluded_from_active_epoch_scheduler e

  union all

  select
    70,
    0,
    'SCHEDULED_LEGACY_PROFILE',
    jsonb_build_object(
      'job_name', l.job_name,
      'root_job_name', l.root_job_name,
      'status', l.status,
      'shadow_epoch_id', l.shadow_epoch_id,
      'total_rows', l.total_rows,
      'rows_last_7d', l.rows_last_7d,
      'rows_last_30d', l.rows_last_30d,
      'first_started_at', l.first_started_at,
      'last_started_at', l.last_started_at
    )
  from scheduled_legacy_profile l
)
select
  section,
  payload
from result_rows
order by
  section_order,
  coalesce((payload ->> 'window_days')::int, 0),
  item_order,
  coalesce(payload ->> 'job_name', ''),
  coalesce(payload ->> 'run_kind', ''),
  coalesce(payload ->> 'status', ''),
  coalesce(payload ->> 'excluded_reason', '');
