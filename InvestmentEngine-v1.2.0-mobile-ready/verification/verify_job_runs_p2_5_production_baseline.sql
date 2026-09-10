-- Post-Shadow P2.5 — system.job_runs production baseline
-- READ-ONLY verification only.
--
-- Bu sorgu:
--   * DELETE / UPDATE / INSERT yapmaz,
--   * migration / DDL çalıştırmaz,
--   * VACUUM / VACUUM FULL çalıştırmaz,
--   * scheduler veya model davranışını değiştirmez.
--
-- Amaç: P2.6 evidence-aware retention tasarımından önce system.job_runs tablosunun
-- gerçek production büyüklüğünü, provenance dağılımını, readiness bağımlılığını,
-- incident/RCA kanıt sınıflarını ve fiziksel durumunu ölçmek.
--
-- Önemli güvenlik ilkesi:
--   old / routine / current-readiness tarafından doğrudan kullanılmıyor
--   !=
--   safe-to-delete
--
-- Expected runtime contract:
--   Model 1.2.0
--   SHADOW / READY / LIVE NO-GO

with
params as (
  select now() as checked_at
),
base as (
  select
    j.id,
    j.job_name,
    j.started_at,
    j.finished_at,
    j.status,
    j.message,
    j.details,
    j.run_kind,
    j.shadow_epoch_id,
    nullif(j.details ->> 'root_job_name', '') as root_job_name,
    case
      when j.finished_at is not null and j.finished_at >= j.started_at
      then extract(epoch from (j.finished_at - j.started_at))::numeric
      else null
    end as duration_seconds,
    octet_length(coalesce(j.message, ''))::bigint as message_bytes,
    pg_column_size(coalesce(j.details, '{}'::jsonb))::bigint as details_bytes,
    (
      octet_length(coalesce(j.message, ''))
      + pg_column_size(coalesce(j.details, '{}'::jsonb))
    )::bigint as payload_bytes,
    case
      when j.status = 'OK' then 'ROUTINE_OK'
      when j.status = 'DEGRADED' then 'DEGRADED_EVIDENCE'
      when j.status = 'SKIPPED' then 'SKIPPED_EVIDENCE'
      else 'ERROR_OR_OTHER_EVIDENCE'
    end as evidence_class,
    case
      when j.started_at >= p.checked_at - interval '7 days' then '00_0_7d'
      when j.started_at >= p.checked_at - interval '30 days' then '01_8_30d'
      when j.started_at >= p.checked_at - interval '90 days' then '02_31_90d'
      when j.started_at >= p.checked_at - interval '180 days' then '03_91_180d'
      when j.started_at >= p.checked_at - interval '365 days' then '04_181_365d'
      else '05_gt_365d'
    end as age_bucket
  from system.job_runs j
  cross join params p
),
overall as (
  select
    count(*)::bigint as total_rows,
    min(started_at) as oldest_started_at,
    max(started_at) as latest_started_at,
    min(finished_at) filter (where finished_at is not null) as oldest_finished_at,
    max(finished_at) filter (where finished_at is not null) as latest_finished_at,
    count(*) filter (where finished_at is null)::bigint as unfinished_rows,
    count(*) filter (
      where finished_at is not null and finished_at < started_at
    )::bigint as invalid_negative_duration_rows,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '1 day'
    )::bigint as rows_last_1d,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '7 days'
    )::bigint as rows_last_7d,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '30 days'
    )::bigint as rows_last_30d,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '90 days'
    )::bigint as rows_last_90d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '7 days'
    )::bigint as rows_older_than_7d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '30 days'
    )::bigint as rows_older_than_30d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '90 days'
    )::bigint as rows_older_than_90d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '365 days'
    )::bigint as rows_older_than_365d,
    count(distinct job_name)::bigint as distinct_job_names,
    count(distinct status)::bigint as distinct_statuses,
    count(distinct run_kind)::bigint as distinct_run_kinds,
    count(distinct shadow_epoch_id) filter (where shadow_epoch_id is not null)::bigint
      as distinct_shadow_epochs,
    count(*) filter (where shadow_epoch_id is null)::bigint as rows_without_shadow_epoch,
    count(*) filter (where root_job_name is not null)::bigint as rows_with_root_job_name,
    count(*) filter (where root_job_name is null)::bigint as rows_without_root_job_name,
    round(avg(duration_seconds), 3) as avg_duration_seconds,
    round(percentile_cont(0.50) within group (order by duration_seconds)::numeric, 3)
      as p50_duration_seconds,
    round(percentile_cont(0.95) within group (order by duration_seconds)::numeric, 3)
      as p95_duration_seconds,
    round(max(duration_seconds), 3) as max_duration_seconds,
    sum(message_bytes)::bigint as total_message_bytes,
    sum(details_bytes)::bigint as total_details_bytes,
    sum(payload_bytes)::bigint as total_payload_bytes,
    round(avg(payload_bytes), 2) as avg_payload_bytes,
    round(percentile_cont(0.95) within group (order by payload_bytes)::numeric, 2)
      as p95_payload_bytes,
    max(payload_bytes)::bigint as max_payload_bytes
  from base
),
status_distribution as (
  select
    status,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '7 days'
    )::bigint as rows_last_7d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '90 days'
    )::bigint as rows_older_than_90d,
    sum(payload_bytes)::bigint as payload_bytes
  from base
  group by status
),
evidence_distribution as (
  select
    evidence_class,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '7 days'
    )::bigint as rows_older_than_7d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '30 days'
    )::bigint as rows_older_than_30d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '90 days'
    )::bigint as rows_older_than_90d,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '365 days'
    )::bigint as rows_older_than_365d
  from base
  group by evidence_class
),
run_kind_distribution as (
  select
    run_kind,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '90 days'
    )::bigint as rows_older_than_90d
  from base
  group by run_kind
),
job_distribution as (
  select
    job_name,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows,
    count(*) filter (
      where run_kind in ('manual', 'test', 'backfill', 'development')
    )::bigint as explicit_non_scheduler_rows,
    count(*) filter (
      where run_kind in ('scheduled', 'scheduled_legacy')
    )::bigint as scheduler_rows,
    count(*) filter (
      where run_kind in ('dependency', 'maintenance')
    )::bigint as child_or_maintenance_rows,
    count(*) filter (
      where run_kind = 'legacy'
    )::bigint as unresolved_legacy_rows,
    sum(payload_bytes)::bigint as payload_bytes,
    round(avg(payload_bytes), 2) as avg_payload_bytes,
    max(payload_bytes)::bigint as max_payload_bytes
  from base
  group by job_name
),
job_kind_distribution as (
  select
    job_name,
    run_kind,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows
  from base
  group by job_name, run_kind
),
age_distribution as (
  select
    age_bucket,
    count(*)::bigint as rows,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows,
    count(*) filter (
      where run_kind in ('manual', 'test', 'backfill', 'development')
    )::bigint as explicit_non_scheduler_rows,
    count(*) filter (
      where run_kind in ('scheduled', 'scheduled_legacy')
    )::bigint as scheduler_rows,
    count(*) filter (
      where run_kind in ('dependency', 'maintenance')
    )::bigint as child_or_maintenance_rows,
    sum(payload_bytes)::bigint as payload_bytes
  from base
  group by age_bucket
),
daily_growth as (
  select
    started_at::date as run_date,
    count(*)::bigint as rows,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows,
    sum(payload_bytes)::bigint as payload_bytes
  from base
  where started_at >= (select checked_at from params) - interval '45 days'
  group by started_at::date
),
monthly_growth as (
  select
    date_trunc('month', started_at)::date as run_month,
    count(*)::bigint as rows,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (where status = 'SKIPPED')::bigint as skipped_rows,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows,
    sum(payload_bytes)::bigint as payload_bytes
  from base
  group by date_trunc('month', started_at)::date
),
payload_by_job as (
  select
    job_name,
    count(*)::bigint as rows,
    sum(message_bytes)::bigint as message_bytes,
    sum(details_bytes)::bigint as details_bytes,
    sum(payload_bytes)::bigint as total_payload_bytes,
    round(avg(payload_bytes), 2) as avg_payload_bytes,
    round(percentile_cont(0.95) within group (order by payload_bytes)::numeric, 2)
      as p95_payload_bytes,
    max(payload_bytes)::bigint as max_payload_bytes
  from base
  group by job_name
),
largest_payload_rows as (
  select
    id,
    job_name,
    started_at,
    status,
    run_kind,
    shadow_epoch_id,
    root_job_name,
    message_bytes,
    details_bytes,
    payload_bytes
  from base
  order by payload_bytes desc, id desc
  limit 20
),
readiness_window as (
  select
    count(*)::bigint as jobs,
    count(*) filter (
      where status in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as successful_by_current_contract,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as unsuccessful_by_current_contract,
    min(started_at) as oldest_row_in_window,
    max(started_at) as latest_row_in_window,
    round(
      case
        when count(*) = 0 then 0
        else count(*) filter (
          where status in ('OK', 'DEGRADED', 'SKIPPED')
        )::numeric / count(*)::numeric
      end,
      6
    ) as success_rate
  from base
  where started_at >= (select checked_at from params) - interval '7 days'
    and job_name <> 'realtime_test'
),
readiness_window_by_kind as (
  select
    run_kind,
    count(*)::bigint as rows,
    count(*) filter (
      where status in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as successful_by_current_contract,
    count(*) filter (
      where status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as unsuccessful_by_current_contract
  from base
  where started_at >= (select checked_at from params) - interval '7 days'
    and job_name <> 'realtime_test'
  group by run_kind
),
realtime_test_state as (
  select
    count(*)::bigint as total_rows,
    min(started_at) as first_started_at,
    max(started_at) as latest_started_at,
    max(finished_at) filter (where status = 'OK') as latest_ok_finished_at,
    count(*) filter (where status = 'OK')::bigint as ok_rows,
    count(*) filter (where status <> 'OK')::bigint as non_ok_rows
  from base
  where job_name = 'realtime_test'
),
epoch_distribution as (
  select
    b.shadow_epoch_id,
    e.epoch_key,
    e.model_version,
    e.status as epoch_status,
    e.started_at as epoch_started_at,
    e.ended_at as epoch_ended_at,
    count(*)::bigint as rows,
    min(b.started_at) as first_job_started_at,
    max(b.started_at) as last_job_started_at,
    count(*) filter (where b.status = 'OK')::bigint as ok_rows,
    count(*) filter (where b.status = 'DEGRADED')::bigint as degraded_rows,
    count(*) filter (
      where b.status not in ('OK', 'DEGRADED', 'SKIPPED')
    )::bigint as error_or_other_rows
  from base b
  left join model.shadow_epochs e on e.id = b.shadow_epoch_id
  group by
    b.shadow_epoch_id,
    e.epoch_key,
    e.model_version,
    e.status,
    e.started_at,
    e.ended_at
),
root_job_distribution as (
  select
    coalesce(root_job_name, '(none)') as root_job_name,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (
      where run_kind in ('dependency', 'maintenance')
    )::bigint as dependency_or_maintenance_rows
  from base
  group by coalesce(root_job_name, '(none)')
),
physical_relation as (
  select
    pg_relation_size('system.job_runs'::regclass)::bigint as heap_bytes,
    pg_indexes_size('system.job_runs'::regclass)::bigint as indexes_bytes,
    pg_total_relation_size('system.job_runs'::regclass)::bigint as total_bytes,
    pg_size_pretty(pg_relation_size('system.job_runs'::regclass)) as heap_size,
    pg_size_pretty(pg_indexes_size('system.job_runs'::regclass)) as indexes_size,
    pg_size_pretty(pg_total_relation_size('system.job_runs'::regclass)) as total_size
),
table_stats as (
  select
    coalesce(s.n_live_tup, 0)::bigint as n_live_tup,
    coalesce(s.n_dead_tup, 0)::bigint as n_dead_tup,
    coalesce(s.n_tup_ins, 0)::bigint as n_tup_ins,
    coalesce(s.n_tup_upd, 0)::bigint as n_tup_upd,
    coalesce(s.n_tup_del, 0)::bigint as n_tup_del,
    coalesce(s.n_mod_since_analyze, 0)::bigint as n_mod_since_analyze,
    coalesce(s.n_ins_since_vacuum, 0)::bigint as n_ins_since_vacuum,
    s.last_vacuum,
    s.last_autovacuum,
    s.last_analyze,
    s.last_autoanalyze,
    coalesce(s.vacuum_count, 0)::bigint as vacuum_count,
    coalesce(s.autovacuum_count, 0)::bigint as autovacuum_count,
    coalesce(s.analyze_count, 0)::bigint as analyze_count,
    coalesce(s.autoanalyze_count, 0)::bigint as autoanalyze_count
  from pg_stat_user_tables s
  where s.schemaname = 'system'
    and s.relname = 'job_runs'
),
index_stats as (
  select
    i.indexrelname as index_name,
    pg_relation_size(i.indexrelid)::bigint as index_bytes,
    pg_size_pretty(pg_relation_size(i.indexrelid)) as index_size,
    coalesce(i.idx_scan, 0)::bigint as idx_scan,
    coalesce(i.idx_tup_read, 0)::bigint as idx_tup_read,
    coalesce(i.idx_tup_fetch, 0)::bigint as idx_tup_fetch
  from pg_stat_user_indexes i
  where i.schemaname = 'system'
    and i.relname = 'job_runs'
),
schema_contract as (
  select
    to_regclass('system.job_runs') is not null as table_present,
    exists (
      select 1
      from information_schema.columns
      where table_schema = 'system'
        and table_name = 'job_runs'
        and column_name = 'run_kind'
    ) as run_kind_column_present,
    exists (
      select 1
      from information_schema.columns
      where table_schema = 'system'
        and table_name = 'job_runs'
        and column_name = 'shadow_epoch_id'
    ) as shadow_epoch_id_column_present,
    exists (
      select 1
      from pg_indexes
      where schemaname = 'system'
        and tablename = 'job_runs'
        and indexname = 'idx_job_runs_name_time'
    ) as name_time_index_present,
    exists (
      select 1
      from pg_indexes
      where schemaname = 'system'
        and tablename = 'job_runs'
        and indexname = 'idx_job_runs_kind_time'
    ) as kind_time_index_present,
    exists (
      select 1
      from pg_indexes
      where schemaname = 'system'
        and tablename = 'job_runs'
        and indexname = 'idx_job_runs_epoch_name_time'
    ) as epoch_name_time_index_present,
    exists (
      select 1
      from pg_trigger t
      join pg_class c on c.oid = t.tgrelid
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'system'
        and c.relname = 'job_runs'
        and t.tgname = 'trg_job_runs_provenance'
        and not t.tgisinternal
    ) as provenance_trigger_present
),
explicit_non_scheduler_evidence as (
  select
    count(*)::bigint as rows,
    count(*) filter (where run_kind = 'manual')::bigint as manual_rows,
    count(*) filter (where run_kind = 'test')::bigint as test_rows,
    count(*) filter (where run_kind = 'backfill')::bigint as backfill_rows,
    count(*) filter (where run_kind = 'development')::bigint as development_rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    count(*) filter (
      where started_at < (select checked_at from params) - interval '90 days'
    )::bigint as rows_older_than_90d
  from base
  where run_kind in ('manual', 'test', 'backfill', 'development')
),
provenance_quality as (
  select
    count(*) filter (where run_kind = 'legacy')::bigint as unresolved_legacy_rows,
    count(*) filter (where run_kind = 'scheduled_legacy')::bigint as scheduled_legacy_rows,
    count(*) filter (where run_kind = 'scheduled')::bigint as scheduled_rows,
    count(*) filter (where run_kind = 'dependency')::bigint as dependency_rows,
    count(*) filter (where run_kind = 'maintenance')::bigint as maintenance_rows,
    count(*) filter (
      where run_kind in ('dependency', 'maintenance') and root_job_name is null
    )::bigint as child_rows_without_root_job_name,
    count(*) filter (
      where run_kind in ('dependency', 'maintenance') and root_job_name is not null
    )::bigint as child_rows_with_root_job_name
  from base
)
select jsonb_build_object(
  'job_runs_p2_5_production_baseline',
  jsonb_build_object(
    'checked_at', (select checked_at from params),
    'model_version', '1.2.0',
    'mode_contract', 'SHADOW / READY / LIVE NO-GO',
    'mutation_performed', false,
    'retention_delete_authorized', false,
    'vacuum_full_authorized', false,
    'baseline_purpose',
      'Read-only production evidence for P2.6 evidence-aware system.job_runs retention design.',
    'current_readiness_contract',
      'shadow_readiness_stats reads the last 7 days excluding realtime_test and counts OK/DEGRADED/SKIPPED as successful.',
    'retention_safety_contract',
      'Old, routine, or not directly used by current readiness does not imply safe-to-delete; incident/RCA, manual/backfill/test, release/shadow milestone and provenance evidence must be classified first.',
    'schema_contract', (select to_jsonb(s) from schema_contract s),
    'overall', (select to_jsonb(o) from overall o),
    'status_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.rows desc, x.status)
        from status_distribution x
      ),
      '[]'::jsonb
    ),
    'evidence_class_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.evidence_class)
        from evidence_distribution x
      ),
      '[]'::jsonb
    ),
    'run_kind_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.rows desc, x.run_kind)
        from run_kind_distribution x
      ),
      '[]'::jsonb
    ),
    'job_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.rows desc, x.job_name)
        from job_distribution x
      ),
      '[]'::jsonb
    ),
    'job_kind_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.job_name, x.run_kind)
        from job_kind_distribution x
      ),
      '[]'::jsonb
    ),
    'age_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.age_bucket)
        from age_distribution x
      ),
      '[]'::jsonb
    ),
    'daily_growth_last_45d', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.run_date)
        from daily_growth x
      ),
      '[]'::jsonb
    ),
    'monthly_growth', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.run_month)
        from monthly_growth x
      ),
      '[]'::jsonb
    ),
    'payload_by_job', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.total_payload_bytes desc, x.job_name)
        from payload_by_job x
      ),
      '[]'::jsonb
    ),
    'largest_payload_rows', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.payload_bytes desc, x.id desc)
        from largest_payload_rows x
      ),
      '[]'::jsonb
    ),
    'current_readiness_window_7d', jsonb_build_object(
      'overall', (select to_jsonb(r) from readiness_window r),
      'by_run_kind', coalesce(
        (
          select jsonb_agg(to_jsonb(x) order by x.run_kind)
          from readiness_window_by_kind x
        ),
        '[]'::jsonb
      )
    ),
    'realtime_test_state', (select to_jsonb(r) from realtime_test_state r),
    'shadow_epoch_distribution', coalesce(
      (
        select jsonb_agg(
          to_jsonb(x)
          order by x.shadow_epoch_id nulls first
        )
        from epoch_distribution x
      ),
      '[]'::jsonb
    ),
    'root_job_distribution', coalesce(
      (
        select jsonb_agg(to_jsonb(x) order by x.rows desc, x.root_job_name)
        from root_job_distribution x
      ),
      '[]'::jsonb
    ),
    'explicit_non_scheduler_evidence',
      (select to_jsonb(x) from explicit_non_scheduler_evidence x),
    'provenance_quality', (select to_jsonb(x) from provenance_quality x),
    'physical_maintenance', jsonb_build_object(
      'relation_sizes', (select to_jsonb(x) from physical_relation x),
      'table_stats', (select to_jsonb(x) from table_stats x),
      'indexes', coalesce(
        (
          select jsonb_agg(to_jsonb(x) order by x.index_bytes desc, x.index_name)
          from index_stats x
        ),
        '[]'::jsonb
      ),
      'vacuum_full_authorized', false
    ),
    'baseline_complete',
      (
        select
          s.table_present
          and s.run_kind_column_present
          and s.shadow_epoch_id_column_present
          and s.name_time_index_present
          and s.kind_time_index_present
          and s.epoch_name_time_index_present
          and s.provenance_trigger_present
        from schema_contract s
      ),
    'next_step',
      'Interpret this baseline first. P2.6 may classify evidence-aware retention candidates; this query itself authorizes no DELETE, VACUUM FULL, migration, or scheduler change.'
  )
) as job_runs_p2_5_production_baseline;
