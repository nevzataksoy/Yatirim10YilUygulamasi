-- Post-Shadow P2.6 — system.job_runs evidence-aware retention policy dry-run
-- READ-ONLY verification only.
--
-- Bu sorgu hiçbir DELETE / UPDATE / INSERT / DDL / VACUUM çalıştırmaz.
-- Amaç: P2.5 production baseline sonrasında, gelecekteki job_runs büyümesini
-- evidence kaybetmeden sınırlayabilecek en dar aday sınıfı dry-run ile ölçmek.
--
-- Proposed conservative contract:
--   * Son 90 gün full-fidelity korunur.
--   * ERROR / unknown status evidence her yaşta korunur.
--   * manual/test/backfill/development/maintenance/dependency/legacy korunur.
--   * shadow_epoch_id NULL provenance boşlukları korunur.
--   * release/audit/milestone job'ları korunur.
--   * status veya message değişim sınırları korunur.
--   * Europe/Istanbul operasyon gününde her job/run_kind/status/root için
--     ilk ve son satır korunur.
--   * Ancak bunların dışında kalan, eski scheduled/scheduled_legacy
--     OK/DEGRADED/SKIPPED intra-day tekrarlar COMPACTION_CANDIDATE olabilir.
--
-- ÖNEMLİ:
--   COMPACTION_CANDIDATE != DELETE AUTHORIZED
--   Bu sorgu yalnız classifier güvenliğini ve aday hacmini ölçer.
--
-- Model/LIVE contract:
--   Model 1.2.0
--   SHADOW / READY / LIVE NO-GO

with
params as (
  select
    now() as checked_at,
    90::integer as proposed_full_fidelity_days
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
    (j.started_at at time zone 'Europe/Istanbul')::date as run_day_trt,
    md5(coalesce(j.status,'') || '|' || coalesce(j.message,'')) as status_message_signature,
    octet_length(coalesce(j.message,''))::bigint
      + pg_column_size(coalesce(j.details,'{}'::jsonb))::bigint as payload_bytes
  from system.job_runs j
),
ordered as (
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
      partition by run_day_trt, job_name, run_kind, status, coalesce(root_job_name,'')
      order by started_at, id
    ) as day_first_rn,
    row_number() over (
      partition by run_day_trt, job_name, run_kind, status, coalesce(root_job_name,'')
      order by started_at desc, id desc
    ) as day_last_rn
  from base b
),
classified as (
  select
    o.*,
    (status not in ('OK','DEGRADED','SKIPPED')) as is_incident_or_unknown,
    (run_kind not in ('scheduled','scheduled_legacy')) as is_non_scheduler_evidence,
    (run_kind='legacy' or shadow_epoch_id is null) as is_provenance_gap,
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
    (day_first_rn=1 or day_last_rn=1) as is_daily_anchor,
    (
      started_at >= (select checked_at from params)
                    - make_interval(days => (select proposed_full_fidelity_days from params))
    ) as is_in_proposed_hot_window
  from ordered o
),
policy_classified as (
  select
    c.*,
    case
      when is_incident_or_unknown then 'PROTECT_INCIDENT_OR_UNKNOWN_STATUS'
      when is_non_scheduler_evidence then 'PROTECT_NON_SCHEDULER_EVIDENCE'
      when is_provenance_gap then 'PROTECT_PROVENANCE_GAP'
      when is_milestone_job then 'PROTECT_MILESTONE_JOB'
      when is_in_proposed_hot_window then 'PROTECT_FULL_FIDELITY_90D'
      when is_status_message_boundary then 'PROTECT_STATUS_MESSAGE_BOUNDARY'
      when is_daily_anchor then 'PROTECT_DAILY_FIRST_LAST_ANCHOR'
      else 'COMPACTION_CANDIDATE_90D'
    end as proposed_policy_class
  from classified c
),
scenarios(cutoff_days) as (
  values (30),(60),(90),(180)
),
scenario_eval as (
  select
    s.cutoff_days,
    c.*,
    (
      c.started_at < (select checked_at from params) - make_interval(days => s.cutoff_days)
      and not c.is_incident_or_unknown
      and not c.is_non_scheduler_evidence
      and not c.is_provenance_gap
      and not c.is_milestone_job
      and not c.is_status_message_boundary
      and not c.is_daily_anchor
    ) as is_compaction_candidate
  from scenarios s
  cross join classified c
),
scenario_summary as (
  select
    cutoff_days,
    count(*) filter (
      where started_at < (select checked_at from params) - make_interval(days => cutoff_days)
    )::bigint as rows_older_than_cutoff,
    count(*) filter (where is_compaction_candidate)::bigint as candidate_rows,
    count(*) filter (
      where started_at < (select checked_at from params) - make_interval(days => cutoff_days)
        and not is_compaction_candidate
    )::bigint as protected_rows_older_than_cutoff,
    count(*) filter (
      where is_compaction_candidate and status='OK'
    )::bigint as candidate_ok_rows,
    count(*) filter (
      where is_compaction_candidate and status='DEGRADED'
    )::bigint as candidate_degraded_rows,
    count(*) filter (
      where is_compaction_candidate and status='SKIPPED'
    )::bigint as candidate_skipped_rows,
    count(*) filter (
      where is_compaction_candidate and run_kind='scheduled'
    )::bigint as candidate_scheduled_rows,
    count(*) filter (
      where is_compaction_candidate and run_kind='scheduled_legacy'
    )::bigint as candidate_scheduled_legacy_rows,
    sum(payload_bytes) filter (where is_compaction_candidate)::bigint as candidate_payload_bytes
  from scenario_eval
  group by cutoff_days
),
policy_distribution as (
  select
    proposed_policy_class,
    count(*)::bigint as rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at,
    sum(payload_bytes)::bigint as payload_bytes
  from policy_classified
  group by proposed_policy_class
),
job_policy_distribution as (
  select
    job_name,
    proposed_policy_class,
    count(*)::bigint as rows,
    count(*) filter(where status='OK')::bigint as ok_rows,
    count(*) filter(where status='DEGRADED')::bigint as degraded_rows,
    count(*) filter(where status='SKIPPED')::bigint as skipped_rows,
    count(*) filter(where status not in ('OK','DEGRADED','SKIPPED'))::bigint as error_or_other_rows,
    min(started_at) as first_started_at,
    max(started_at) as last_started_at
  from policy_classified
  group by job_name, proposed_policy_class
),
protected_reason_sim30 as (
  select
    case
      when is_incident_or_unknown then 'PROTECT_INCIDENT_OR_UNKNOWN_STATUS'
      when is_non_scheduler_evidence then 'PROTECT_NON_SCHEDULER_EVIDENCE'
      when is_provenance_gap then 'PROTECT_PROVENANCE_GAP'
      when is_milestone_job then 'PROTECT_MILESTONE_JOB'
      when is_status_message_boundary then 'PROTECT_STATUS_MESSAGE_BOUNDARY'
      when is_daily_anchor then 'PROTECT_DAILY_FIRST_LAST_ANCHOR'
      else 'COMPACTION_CANDIDATE'
    end as class,
    count(*)::bigint as rows
  from classified
  where started_at < (select checked_at from params) - interval '30 days'
  group by 1
),
candidate_sample_sim30 as (
  select
    id,
    job_name,
    run_kind,
    status,
    started_at,
    run_day_trt,
    root_job_name,
    message,
    payload_bytes
  from scenario_eval
  where cutoff_days=30 and is_compaction_candidate
  order by started_at, id
  limit 40
),
retained_anchor_check_sim30 as (
  select
    run_day_trt,
    job_name,
    run_kind,
    status,
    coalesce(root_job_name,'') as root_job_name_key,
    count(*)::bigint as old_rows,
    count(*) filter(where is_daily_anchor)::bigint as daily_anchor_rows,
    count(*) filter(where is_status_message_boundary)::bigint as boundary_rows
  from classified
  where started_at < (select checked_at from params) - interval '30 days'
    and run_kind in ('scheduled','scheduled_legacy')
    and status in ('OK','DEGRADED','SKIPPED')
    and shadow_epoch_id is not null
  group by run_day_trt,job_name,run_kind,status,coalesce(root_job_name,'')
),
safety_checks as (
  select
    -- 30-day simulation deliberately stresses the classifier because production
    -- does not yet contain >90d rows.
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and status not in ('OK','DEGRADED','SKIPPED')
    ) = 0 as sim30_incident_rows_never_candidate,
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and run_kind not in ('scheduled','scheduled_legacy')
    ) = 0 as sim30_non_scheduler_rows_never_candidate,
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and (run_kind='legacy' or shadow_epoch_id is null)
    ) = 0 as sim30_provenance_gaps_never_candidate,
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and job_name in (
          'monthly_audit_job','model_validation_job','realtime_test',
          'shadow_observability','crypto_history_backfill'
        )
    ) = 0 as sim30_milestone_jobs_never_candidate,
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and is_status_message_boundary
    ) = 0 as sim30_status_message_boundaries_never_candidate,
    count(*) filter (
      where cutoff_days=30 and is_compaction_candidate
        and is_daily_anchor
    ) = 0 as sim30_daily_anchors_never_candidate,
    count(*) filter (
      where cutoff_days=90 and is_compaction_candidate
        and started_at >= (select checked_at from params)-interval '7 days'
    ) = 0 as proposed_policy_never_touches_current_readiness_window
  from scenario_eval
),
anchor_safety as (
  select
    count(*)::bigint as groups_checked,
    count(*) filter(where daily_anchor_rows=0)::bigint as groups_missing_anchor,
    bool_and(daily_anchor_rows >= 1) as every_group_retains_daily_anchor
  from retained_anchor_check_sim30
),
projection_inputs as (
  select
    count(*) filter (
      where started_at >= (select checked_at from params)-interval '30 days'
    )::numeric / 30.0 as recent_rows_per_day,
    coalesce(sum(payload_bytes) filter (
      where started_at >= (select checked_at from params)-interval '30 days'
    ),0)::numeric / 30.0 as recent_payload_bytes_per_day
  from classified
),
projection as (
  select
    round(recent_rows_per_day,2) as recent_rows_per_day,
    round(recent_payload_bytes_per_day,2) as recent_payload_bytes_per_day,
    round(recent_rows_per_day * 3650,0)::bigint as ten_year_rows_without_retention_estimate,
    round(recent_payload_bytes_per_day * 3650,0)::bigint as ten_year_payload_bytes_without_retention_estimate
  from projection_inputs
),
final_checks as (
  select
    s.*,
    a.groups_checked,
    a.groups_missing_anchor,
    a.every_group_retains_daily_anchor,
    (
      s.sim30_incident_rows_never_candidate
      and s.sim30_non_scheduler_rows_never_candidate
      and s.sim30_provenance_gaps_never_candidate
      and s.sim30_milestone_jobs_never_candidate
      and s.sim30_status_message_boundaries_never_candidate
      and s.sim30_daily_anchors_never_candidate
      and s.proposed_policy_never_touches_current_readiness_window
      and coalesce(a.every_group_retains_daily_anchor,true)
    ) as classifier_safety_complete
  from safety_checks s
  cross join anchor_safety a
)
select jsonb_build_object(
  'job_runs_p2_6_retention_policy_dry_run', jsonb_build_object(
    'checked_at', (select checked_at from params),
    'model_version', '1.2.0',
    'mode_contract', 'SHADOW / READY / LIVE NO-GO',
    'mutation_performed', false,
    'retention_delete_authorized', false,
    'proposed_full_fidelity_days', (select proposed_full_fidelity_days from params),
    'proposed_contract', jsonb_build_object(
      'full_fidelity_window', '90 days',
      'candidate_scope', 'Only old intra-day scheduled/scheduled_legacy OK/DEGRADED/SKIPPED telemetry after all evidence protections.',
      'protect_incident_or_unknown_status', true,
      'protect_non_scheduler_evidence', true,
      'protect_provenance_gaps', true,
      'protect_milestone_jobs', true,
      'protect_status_message_boundaries', true,
      'protect_daily_first_last_anchors_trt', true,
      'candidate_does_not_mean_delete_authorized', true
    ),
    'scenario_summary', coalesce((
      select jsonb_agg(to_jsonb(x) order by cutoff_days)
      from scenario_summary x
    ),'[]'::jsonb),
    'proposed_90d_policy_distribution', coalesce((
      select jsonb_agg(to_jsonb(x) order by proposed_policy_class)
      from policy_distribution x
    ),'[]'::jsonb),
    'job_policy_distribution', coalesce((
      select jsonb_agg(to_jsonb(x) order by job_name, proposed_policy_class)
      from job_policy_distribution x
    ),'[]'::jsonb),
    'sim30_protected_reason_distribution', coalesce((
      select jsonb_agg(to_jsonb(x) order by class)
      from protected_reason_sim30 x
    ),'[]'::jsonb),
    'sim30_candidate_sample', coalesce((
      select jsonb_agg(to_jsonb(x) order by started_at,id)
      from candidate_sample_sim30 x
    ),'[]'::jsonb),
    'safety_checks', (select to_jsonb(x) from final_checks x),
    'ten_year_unbounded_projection', (select to_jsonb(x) from projection x),
    'policy_ready_for_interpretation', (select classifier_safety_complete from final_checks),
    'next_step', 'Interpret classifier and scenario evidence. Do not implement DELETE/migration/scheduler maintenance until P2.6 contract is accepted from evidence.'
  )
) as job_runs_p2_6_retention_policy_dry_run;
