from __future__ import annotations

from datetime import datetime

from app.database.db import DatabaseService

JOB_RUNS_FULL_FIDELITY_DAYS = 90


def read_data_lifecycle_snapshot(
    db: DatabaseService,
    *,
    full_fidelity_days: int = JOB_RUNS_FULL_FIDELITY_DAYS,
    timezone_name: str = "Europe/Istanbul",
) -> dict:
    """Return bounded read-only lifecycle observability for macro/job_runs.

    This function deliberately has no mutation path.  P2.4 authorizes no macro
    retention delete, while P2.6 only defines old job-run compaction candidates;
    a candidate is evidence for future review, not permission to delete it.
    """
    days = int(full_fidelity_days)
    timezone_name = str(timezone_name or "").strip()
    if days < 7 or days > 3650:
        raise ValueError("job_runs full-fidelity window must be between 7 and 3650 days")
    if not timezone_name:
        raise ValueError("lifecycle observability timezone cannot be empty")

    sql = """
    with
    params as (
      select now() as checked_at, %s::integer as full_fidelity_days
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
        timezone(%s, j.started_at)::date as run_day_local,
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
    )
    select
      p.checked_at,
      p.full_fidelity_days,
      m.total_rows as macro_rows,
      m.consecutive_same_value_rows as macro_consecutive_same_value_rows,
      pg_total_relation_size('macro.observations'::regclass)::bigint as macro_total_bytes,
      coalesce((
        select n_dead_tup::bigint
        from pg_stat_user_tables
        where schemaname='macro' and relname='observations'
      ),0)::bigint as macro_dead_tuples,
      j.total_rows as job_runs_rows,
      j.rows_last_7d as job_runs_rows_last_7d,
      j.rows_older_than_full_fidelity as job_runs_rows_older_than_full_fidelity,
      j.compaction_candidate_rows as job_runs_compaction_candidate_rows,
      j.compaction_candidate_payload_bytes as job_runs_compaction_candidate_payload_bytes,
      j.old_incident_or_unknown_rows,
      j.old_non_scheduler_evidence_rows,
      j.old_provenance_gap_rows,
      j.old_milestone_rows,
      j.old_status_message_boundary_rows,
      j.old_daily_anchor_rows,
      pg_total_relation_size('system.job_runs'::regclass)::bigint as job_runs_total_bytes,
      coalesce((
        select n_dead_tup::bigint
        from pg_stat_user_tables
        where schemaname='system' and relname='job_runs'
      ),0)::bigint as job_runs_dead_tuples
    from params p
    cross join macro_summary m
    cross join job_summary j
    """

    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (days, timezone_name))
        row = cur.fetchone() or {}

    checked_at = row.get("checked_at")
    candidate_rows = int(row.get("job_runs_compaction_candidate_rows") or 0)
    old_rows = int(row.get("job_runs_rows_older_than_full_fidelity") or 0)
    return {
        "status": "OK",
        "checked_at": checked_at.isoformat() if isinstance(checked_at, datetime) else str(checked_at or ""),
        "timezone": timezone_name,
        "full_fidelity_days": days,
        "maintenance_action": "NO_OP" if candidate_rows == 0 else "OBSERVE_CANDIDATES_ONLY",
        "mutation_performed": False,
        "delete_authorized": False,
        "macro": {
            "rows": int(row.get("macro_rows") or 0),
            "consecutive_same_value_rows": int(row.get("macro_consecutive_same_value_rows") or 0),
            "total_bytes": int(row.get("macro_total_bytes") or 0),
            "dead_tuples": int(row.get("macro_dead_tuples") or 0),
        },
        "job_runs": {
            "rows": int(row.get("job_runs_rows") or 0),
            "rows_last_7d": int(row.get("job_runs_rows_last_7d") or 0),
            "rows_older_than_full_fidelity": old_rows,
            "protected_rows_older_than_full_fidelity": max(0, old_rows - candidate_rows),
            "compaction_candidate_rows": candidate_rows,
            "compaction_candidate_payload_bytes": int(row.get("job_runs_compaction_candidate_payload_bytes") or 0),
            "old_incident_or_unknown_rows": int(row.get("old_incident_or_unknown_rows") or 0),
            "old_non_scheduler_evidence_rows": int(row.get("old_non_scheduler_evidence_rows") or 0),
            "old_provenance_gap_rows": int(row.get("old_provenance_gap_rows") or 0),
            "old_milestone_rows": int(row.get("old_milestone_rows") or 0),
            "old_status_message_boundary_rows": int(row.get("old_status_message_boundary_rows") or 0),
            "old_daily_anchor_rows": int(row.get("old_daily_anchor_rows") or 0),
            "total_bytes": int(row.get("job_runs_total_bytes") or 0),
            "dead_tuples": int(row.get("job_runs_dead_tuples") or 0),
        },
        "contract": {
            "macro_delete_policy": "NONE_PROVEN",
            "job_runs_candidate_is_delete_authorized": False,
            "observability_only": True,
        },
    }
