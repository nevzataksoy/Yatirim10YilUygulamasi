-- Post-Shadow P2.7 — bounded lifecycle observability production verification
-- READ-ONLY ONLY.
--
-- Bu sorgu app/database/data_lifecycle.py içindeki production SELECT kontratını
-- Supabase üzerinde deployment öncesi doğrular. DELETE / UPDATE / INSERT / DDL /
-- VACUUM çalıştırmaz. COMPACTION_CANDIDATE hiçbir zaman DELETE yetkisi değildir.
--
-- Contract:
--   * macro: P2.3 same-value refetch regression = 0 beklenir.
--   * job_runs: son 90 gün full fidelity.
--   * 90 günden eski yalnız güvenli scheduled tekrarlar candidate olabilir.
--   * ERROR/unknown, non-scheduler, provenance gap, milestone, boundary ve
--     daily first/last anchor satırları korunur.
--   * Europe/Istanbul operasyon günü kullanılır.
--   * mutation_performed=false / delete_authorized=false.

with
params as (
  select
    now() as checked_at,
    90::integer as full_fidelity_days,
    'Europe/Istanbul'::text as timezone_name
),
job_base as (
  select
    j.id,
    j.job_name,
    j.started_at,
    j.status,
    j.message,
    j.details,
    j.run_kind,
    j.shadow_epoch_id,
    nullif(j.details ->> 'root_job_name', '') as root_job_name,
    timezone((select timezone_name from params), j.started_at)::date as run_day_local,
    md5(coalesce(j.status,'') || '|' || coalesce(j.message,'')) as status_message_signature,
    (
      octet_length(coalesce(j.message,''))
      + pg_column_size(coalesce(j.details,'{}'::jsonb))
    )::bigint as payload_bytes
  from system.job_runs j
),
job_ordered as (
  select
    b.*,
    lag(status_message_signature) over (
      partition by job_name, run_kind, coalesce(root_job_name,'')
      order by started_at, id
    ) as prev_status_message_signature,
    lead(status_message_signature) over (
      partition by job_name, run_kind, coalesce(root_job_name,'')
      order by started_at, id
    ) as next_status_message_signature,
    row_number() over (
      partition by run_day_local, job_name, run_kind, status, coalesce(root_job_name,'')
      order by started_at, id
    ) as day_first_rn,
    row_number() over (
      partition by run_day_local, job_name, run_kind, status, coalesce(root_job_name,'')
      order by started_at desc, id desc
    ) as day_last_rn
  from job_base b
),
job_classified as (
  select
    o.*,
    (coalesce(status,'') not in ('OK','DEGRADED','SKIPPED')) as is_incident_or_unknown,
    (coalesce(run_kind,'') not in ('scheduled','scheduled_legacy')) as is_non_scheduler_evidence,
    (coalesce(run_kind,'')='legacy' or shadow_epoch_id is null) as is_provenance_gap,
    (
      job_name in (
        'monthly_audit_job',
        'model_validation_job',
        'realtime_test',
        'shadow_observability',
        'crypto_history_backfill'
      )
    ) as is_milestone_job,
    (
      prev_status_message_signature is null
      or prev_status_message_signature is distinct from status_message_signature
      or next_status_message_signature is null
      or next_status_message_signature is distinct from status_message_signature
    ) as is_status_message_boundary,
    (day_first_rn=1 or day_last_rn=1) as is_daily_anchor
  from job_ordered o
),
job_summary as (
  select
    count(*)::bigint as total_rows,
    count(*) filter (
      where started_at >= (select checked_at from params) - interval '7 days'
    )::bigint as rows_last_7d,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
    )::bigint as rows_older_than_full_fidelity,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and not is_incident_or_unknown
        and not is_non_scheduler_evidence
        and not is_provenance_gap
        and not is_milestone_job
        and not is_status_message_boundary
        and not is_daily_anchor
    )::bigint as compaction_candidate_rows,
    coalesce(sum(payload_bytes) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and not is_incident_or_unknown
        and not is_non_scheduler_evidence
        and not is_provenance_gap
        and not is_milestone_job
        and not is_status_message_boundary
        and not is_daily_anchor
    ),0)::bigint as compaction_candidate_payload_bytes,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_incident_or_unknown
    )::bigint as old_incident_or_unknown_rows,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_non_scheduler_evidence
    )::bigint as old_non_scheduler_evidence_rows,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_provenance_gap
    )::bigint as old_provenance_gap_rows,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_milestone_job
    )::bigint as old_milestone_rows,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_status_message_boundary
    )::bigint as old_status_message_boundary_rows,
    count(*) filter (
      where started_at < (select checked_at from params)
        - make_interval(days => (select full_fidelity_days from params))
        and is_daily_anchor
    )::bigint as old_daily_anchor_rows
  from job_classified
),
macro_ordered as (
  select
    value,
    row_number() over (
      partition by series_id, observation_date
      order by realtime_start, fetched_at, id
    ) as version_rn,
    lag(value) over (
      partition by series_id, observation_date
      order by realtime_start, fetched_at, id
    ) as previous_value
  from macro.observations
),
macro_summary as (
  select
    count(*)::bigint as total_rows,
    count(*) filter (
      where version_rn > 1 and value is not distinct from previous_value
    )::bigint as consecutive_same_value_rows
  from macro_ordered
),
physical as (
  select
    pg_total_relation_size('macro.observations'::regclass)::bigint as macro_total_bytes,
    coalesce((
      select n_dead_tup::bigint
      from pg_stat_user_tables
      where schemaname='macro' and relname='observations'
    ),0)::bigint as macro_dead_tuples,
    pg_total_relation_size('system.job_runs'::regclass)::bigint as job_runs_total_bytes,
    coalesce((
      select n_dead_tup::bigint
      from pg_stat_user_tables
      where schemaname='system' and relname='job_runs'
    ),0)::bigint as job_runs_dead_tuples
)
select jsonb_build_object(
  'check', 'data_lifecycle_p2_7_production_readonly',
  'checked_at', p.checked_at,
  'model_version', '1.2.0',
  'mode', 'SHADOW',
  'live', 'NO-GO',
  'timezone', p.timezone_name,
  'full_fidelity_days', p.full_fidelity_days,
  'maintenance_action', case
    when j.compaction_candidate_rows=0 then 'NO_OP'
    else 'OBSERVE_CANDIDATES_ONLY'
  end,
  'mutation_performed', false,
  'delete_authorized', false,
  'macro', jsonb_build_object(
    'rows', m.total_rows,
    'consecutive_same_value_rows', m.consecutive_same_value_rows,
    'total_bytes', x.macro_total_bytes,
    'dead_tuples', x.macro_dead_tuples,
    'p2_3_regression_free', m.consecutive_same_value_rows=0
  ),
  'job_runs', jsonb_build_object(
    'rows', j.total_rows,
    'rows_last_7d', j.rows_last_7d,
    'rows_older_than_full_fidelity', j.rows_older_than_full_fidelity,
    'protected_rows_older_than_full_fidelity', greatest(
      0::bigint,
      j.rows_older_than_full_fidelity - j.compaction_candidate_rows
    ),
    'compaction_candidate_rows', j.compaction_candidate_rows,
    'compaction_candidate_payload_bytes', j.compaction_candidate_payload_bytes,
    'old_incident_or_unknown_rows', j.old_incident_or_unknown_rows,
    'old_non_scheduler_evidence_rows', j.old_non_scheduler_evidence_rows,
    'old_provenance_gap_rows', j.old_provenance_gap_rows,
    'old_milestone_rows', j.old_milestone_rows,
    'old_status_message_boundary_rows', j.old_status_message_boundary_rows,
    'old_daily_anchor_rows', j.old_daily_anchor_rows,
    'total_bytes', x.job_runs_total_bytes,
    'dead_tuples', x.job_runs_dead_tuples
  ),
  'contract', jsonb_build_object(
    'macro_delete_policy', 'NONE_PROVEN',
    'job_runs_candidate_is_delete_authorized', false,
    'observability_only', true,
    'current_noop', j.compaction_candidate_rows=0,
    'production_query_contract_complete', (
      m.consecutive_same_value_rows=0
      and p.full_fidelity_days=90
      and p.timezone_name='Europe/Istanbul'
    )
  )
) as data_lifecycle_p2_7_production_readonly
from params p
cross join macro_summary m
cross join job_summary j
cross join physical x;
