-- Post-Shadow P2.3 — macro.observations natural scheduler forward verification
-- READ-ONLY.
-- Run only after at least one natural scheduled macro_job completed after the
-- production migration/post-check boundary below.

with
params as (
    select
        timestamptz '2026-09-10 00:55:41.210674+00' as boundary_at,
        20433::bigint as baseline_total_rows
),
latest_macro_job as (
    select
        j.id,
        j.started_at,
        j.finished_at,
        j.status,
        j.run_kind,
        j.message
    from system.job_runs j
    cross join params p
    where j.job_name = 'macro_job'
      and j.started_at > p.boundary_at
      and coalesce(j.run_kind, 'scheduled') = 'scheduled'
    order by j.started_at desc, j.id desc
    limit 1
),
ordered as (
    select
        o.id,
        o.series_id,
        o.observation_date,
        o.value,
        o.realtime_start,
        o.realtime_end,
        o.fetched_at,
        row_number() over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start asc, o.fetched_at asc, o.id asc
        ) as seq_no,
        lag(o.value) over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start asc, o.fetched_at asc, o.id asc
        ) as previous_value
    from macro.observations o
),
post_boundary_rows as (
    select o.*
    from ordered o
    cross join params p
    where o.fetched_at > p.boundary_at
),
post_boundary_summary as (
    select
        count(*)::bigint as new_rows,
        count(*) filter (
            where seq_no = 1
        )::bigint as new_observation_rows,
        count(*) filter (
            where seq_no > 1
              and value is distinct from previous_value
        )::bigint as value_transition_rows,
        count(*) filter (
            where seq_no > 1
              and value is not distinct from previous_value
        )::bigint as duplicate_same_value_rows
    from post_boundary_rows
),
remaining_duplicates as (
    select count(*)::bigint as n
    from ordered
    where seq_no > 1
      and value is not distinct from previous_value
),
decisions as (
    select d.id, d.system, d.factors
    from model.decisions d
    where d.model_version = '1.2.0'
),
decision_refs as (
    select
        d.id as decision_id,
        d.system,
        od.key as series_id,
        case
            when od.value ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                then od.value::date
            else null
        end as observation_date,
        case
            when lv.value ~ '^-?[0-9]+([.][0-9]+)?$'
                then lv.value::numeric
            else null
        end as persisted_value
    from decisions d
    cross join lateral jsonb_each_text(
        case
            when jsonb_typeof(d.factors #> '{macro,details,observation_dates}') = 'object'
                then d.factors #> '{macro,details,observation_dates}'
            else '{}'::jsonb
        end
    ) od
    left join lateral jsonb_each_text(
        case
            when jsonb_typeof(d.factors #> '{macro,details,latest}') = 'object'
                then d.factors #> '{macro,details,latest}'
            else '{}'::jsonb
        end
    ) lv on lv.key = od.key
),
decision_preservation as (
    select
        count(*)::bigint as refs_checked,
        count(*) filter (
            where exists (
                select 1
                from macro.observations o
                where o.series_id = r.series_id
                  and o.observation_date = r.observation_date
                  and o.value = r.persisted_value
            )
        )::bigint as refs_preserved
    from decision_refs r
    where r.observation_date is not null
      and r.persisted_value is not null
),
legacy_constraint as (
    select exists (
        select 1
        from pg_constraint c
        join pg_class t on t.oid = c.conrelid
        join pg_namespace n on n.oid = t.relnamespace
        where n.nspname = 'macro'
          and t.relname = 'observations'
          and c.contype = 'u'
          and c.conname = 'observations_series_id_observation_date_realtime_start_key'
    ) as present
),
version_index as (
    select exists (
        select 1
        from pg_indexes
        where schemaname = 'macro'
          and tablename = 'observations'
          and indexname = 'idx_macro_series_observation_version'
    ) as present
),
summary as (
    select
        p.boundary_at,
        p.baseline_total_rows,
        (select count(*)::bigint from macro.observations) as total_rows,
        (select count(*)::bigint from macro.observations) - p.baseline_total_rows as total_row_delta,
        pbs.new_rows,
        pbs.new_observation_rows,
        pbs.value_transition_rows,
        pbs.duplicate_same_value_rows,
        rd.n as consecutive_same_value_rows,
        dp.refs_checked as decision_refs_checked,
        dp.refs_preserved as decision_refs_preserved,
        (dp.refs_checked - dp.refs_preserved) as decision_refs_lost,
        lc.present as legacy_unique_constraint_present,
        vi.present as version_index_present,
        lmj.id as latest_macro_job_id,
        lmj.started_at as latest_macro_job_started_at,
        lmj.finished_at as latest_macro_job_finished_at,
        lmj.status as latest_macro_job_status,
        lmj.run_kind as latest_macro_job_run_kind,
        lmj.message as latest_macro_job_message
    from params p
    cross join post_boundary_summary pbs
    cross join remaining_duplicates rd
    cross join decision_preservation dp
    cross join legacy_constraint lc
    cross join version_index vi
    left join latest_macro_job lmj on true
)
select jsonb_build_object(
    'checked_at', now(),
    'boundary_at', boundary_at,
    'baseline_total_rows', baseline_total_rows,
    'total_rows', total_rows,
    'total_row_delta', total_row_delta,
    'post_boundary_rows', jsonb_build_object(
        'new_rows', new_rows,
        'new_observation_rows', new_observation_rows,
        'value_transition_rows', value_transition_rows,
        'duplicate_same_value_rows', duplicate_same_value_rows
    ),
    'latest_natural_macro_job', jsonb_build_object(
        'id', latest_macro_job_id,
        'started_at', latest_macro_job_started_at,
        'finished_at', latest_macro_job_finished_at,
        'status', latest_macro_job_status,
        'run_kind', latest_macro_job_run_kind,
        'message', latest_macro_job_message
    ),
    'consecutive_same_value_rows', consecutive_same_value_rows,
    'decision_refs_checked', decision_refs_checked,
    'decision_refs_preserved', decision_refs_preserved,
    'decision_refs_lost', decision_refs_lost,
    'legacy_unique_constraint_present', legacy_unique_constraint_present,
    'version_index_present', version_index_present,
    'forward_contract_complete',
        latest_macro_job_id is not null
        and latest_macro_job_finished_at is not null
        and latest_macro_job_status = 'OK'
        and coalesce(latest_macro_job_run_kind, 'scheduled') = 'scheduled'
        and duplicate_same_value_rows = 0
        and consecutive_same_value_rows = 0
        and decision_refs_lost = 0
        and legacy_unique_constraint_present = false
        and version_index_present = true
) as macro_observations_p2_3_forward
from summary;
