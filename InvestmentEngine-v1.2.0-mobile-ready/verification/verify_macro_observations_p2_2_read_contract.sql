-- Post-Shadow P2.2 — macro.observations deterministic read/version contract verification
-- READ-ONLY. Bu sorgu hiçbir production satırını değiştirmez veya silmez.
--
-- Amaç:
--   1. persisted 1.2.0 decision macro value/date referanslarını aynı date içindeki
--      production current-view version'larla karşılaştırmak,
--   2. gerçek revision date'lerinde hangi deterministic seçim kuralının persisted
--      decision value ile uyumlu olduğunu ölçmek,
--   3. mutable fetched_at nedeniyle exact intraday reconstruction açığını nicelleştirmek,
--   4. revision sequence korunarak consecutive identical refetch satırlarının ne kadarının
--      ileride safe-dedup adayı olabileceğini ölçmek.
--
-- Bu sorgu P2.3 DELETE/migration değildir. Yalnız read-contract evidence üretir.

with
decisions as (
    select
        d.id as decision_id,
        d.system,
        d.as_of as decision_as_of,
        d.created_at as decision_created_at,
        d.status,
        d.factors,
        d.rationale,
        coalesce(
            nullif(d.rationale #>> '{provenance,decision_evaluated_at}', '')::timestamptz,
            d.created_at
        ) as decision_evaluated_at
    from model.decisions d
    where d.model_version = '1.2.0'
),
decision_macro_refs as (
    select
        d.decision_id,
        d.system,
        d.decision_as_of,
        d.decision_created_at,
        d.decision_evaluated_at,
        d.status,
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
version_groups as (
    select
        o.series_id,
        o.observation_date,
        count(*)::bigint as version_count,
        count(distinct o.value)::bigint as distinct_value_count,
        min(o.realtime_start) as first_realtime_start,
        max(o.realtime_start) as last_realtime_start,
        min(o.fetched_at) as min_current_fetched_at,
        max(o.fetched_at) as max_current_fetched_at
    from macro.observations o
    group by o.series_id, o.observation_date
),
ref_candidates as (
    select
        r.*,
        vg.version_count,
        vg.distinct_value_count,

        current_latest.id as current_latest_id,
        current_latest.value as current_latest_value,
        current_latest.realtime_start as current_latest_realtime_start,
        current_latest.fetched_at as current_latest_fetched_at,

        eval_date_latest.id as eval_date_latest_id,
        eval_date_latest.value as eval_date_latest_value,
        eval_date_latest.realtime_start as eval_date_latest_realtime_start,
        eval_date_latest.fetched_at as eval_date_latest_fetched_at,

        eval_timestamp_latest.id as eval_timestamp_latest_id,
        eval_timestamp_latest.value as eval_timestamp_latest_value,
        eval_timestamp_latest.realtime_start as eval_timestamp_latest_realtime_start,
        eval_timestamp_latest.fetched_at as eval_timestamp_latest_fetched_at,

        eval_date_earliest.id as eval_date_earliest_id,
        eval_date_earliest.value as eval_date_earliest_value,
        eval_date_earliest.realtime_start as eval_date_earliest_realtime_start,

        persisted_matches.matching_version_count,
        persisted_matches.first_matching_realtime_start,
        persisted_matches.last_matching_realtime_start,
        persisted_matches.matching_versions_with_current_fetched_at_before_eval,

        case
            when r.persisted_value is null or current_latest.value is null then null
            else r.persisted_value = current_latest.value
        end as persisted_matches_current_latest,
        case
            when r.persisted_value is null or eval_date_latest.value is null then null
            else r.persisted_value = eval_date_latest.value
        end as persisted_matches_eval_date_latest,
        case
            when r.persisted_value is null or eval_timestamp_latest.value is null then null
            else r.persisted_value = eval_timestamp_latest.value
        end as persisted_matches_eval_timestamp_latest,
        case
            when r.persisted_value is null or eval_date_earliest.value is null then null
            else r.persisted_value = eval_date_earliest.value
        end as persisted_matches_eval_date_earliest
    from decision_macro_refs r
    left join version_groups vg
      on vg.series_id = r.series_id
     and vg.observation_date = r.observation_date

    left join lateral (
        select o.*
        from macro.observations o
        where o.series_id = r.series_id
          and o.observation_date = r.observation_date
        order by o.realtime_start desc, o.fetched_at desc, o.id desc
        limit 1
    ) current_latest on true

    -- Coarse production-availability candidate.
    -- realtime_start is a DATE and survives later fetched_at overwrites.
    left join lateral (
        select o.*
        from macro.observations o
        where o.series_id = r.series_id
          and o.observation_date = r.observation_date
          and o.realtime_start <= r.decision_evaluated_at::date
        order by o.realtime_start desc, o.id desc
        limit 1
    ) eval_date_latest on true

    -- Strict timestamp candidate. This is intentionally measured separately because
    -- current persistence mutates fetched_at on conflict, so historical first-seen
    -- time is not guaranteed to remain reconstructible.
    left join lateral (
        select o.*
        from macro.observations o
        where o.series_id = r.series_id
          and o.observation_date = r.observation_date
          and o.fetched_at <= r.decision_evaluated_at
        order by o.realtime_start desc, o.fetched_at desc, o.id desc
        limit 1
    ) eval_timestamp_latest on true

    left join lateral (
        select o.*
        from macro.observations o
        where o.series_id = r.series_id
          and o.observation_date = r.observation_date
          and o.realtime_start <= r.decision_evaluated_at::date
        order by o.realtime_start asc, o.id asc
        limit 1
    ) eval_date_earliest on true

    left join lateral (
        select
            count(*)::bigint as matching_version_count,
            min(o.realtime_start) as first_matching_realtime_start,
            max(o.realtime_start) as last_matching_realtime_start,
            count(*) filter (
                where o.fetched_at <= r.decision_evaluated_at
            )::bigint as matching_versions_with_current_fetched_at_before_eval
        from macro.observations o
        where o.series_id = r.series_id
          and o.observation_date = r.observation_date
          and r.persisted_value is not null
          and o.value = r.persisted_value
    ) persisted_matches on true
),
ref_summary as (
    select
        count(*)::bigint as total_refs,
        count(*) filter (
            where observation_date is not null and persisted_value is not null
        )::bigint as refs_with_date_and_value,
        count(*) filter (where version_count > 1)::bigint as multi_version_refs,
        count(*) filter (where distinct_value_count > 1)::bigint as actual_revision_refs,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_date_latest is true
        )::bigint as revision_refs_matching_eval_date_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_date_latest is false
        )::bigint as revision_refs_not_matching_eval_date_latest,
        count(*) filter (
            where distinct_value_count > 1
              and eval_date_latest_id is null
        )::bigint as revision_refs_without_eval_date_candidate,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_timestamp_latest is true
        )::bigint as revision_refs_matching_eval_timestamp_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_timestamp_latest is false
        )::bigint as revision_refs_not_matching_eval_timestamp_latest,
        count(*) filter (
            where distinct_value_count > 1
              and eval_timestamp_latest_id is null
        )::bigint as revision_refs_without_eval_timestamp_candidate,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_current_latest is true
        )::bigint as revision_refs_still_matching_current_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_current_latest is false
        )::bigint as revision_refs_drifted_from_current_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_date_earliest is true
        )::bigint as revision_refs_matching_eval_date_earliest,
        count(*) filter (
            where persisted_value is not null
              and coalesce(matching_version_count, 0) = 0
        )::bigint as persisted_values_not_found_in_current_table,
        count(*) filter (
            where matching_version_count > 1
        )::bigint as refs_whose_persisted_value_exists_in_multiple_versions
    from ref_candidates
),
series_ref_summary as (
    select
        series_id,
        count(*)::bigint as total_refs,
        count(*) filter (where version_count > 1)::bigint as multi_version_refs,
        count(*) filter (where distinct_value_count > 1)::bigint as actual_revision_refs,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_date_latest is true
        )::bigint as revision_match_eval_date_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_eval_date_latest is false
        )::bigint as revision_mismatch_eval_date_latest,
        count(*) filter (
            where distinct_value_count > 1
              and persisted_matches_current_latest is false
        )::bigint as revision_drift_from_current_latest,
        count(*) filter (
            where distinct_value_count > 1
              and eval_timestamp_latest_id is null
        )::bigint as revision_without_strict_timestamp_candidate
    from ref_candidates
    group by series_id
),
ordered_versions as (
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
            order by o.realtime_start, o.id
        ) as seq_no,
        lag(o.value) over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start, o.id
        ) as previous_value,
        lag(o.realtime_end) over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start, o.id
        ) as previous_realtime_end
    from macro.observations o
),
transition_flags as (
    select
        ov.*,
        case
            when seq_no = 1 then 1
            when value is distinct from previous_value then 1
            when realtime_end is distinct from previous_realtime_end then 1
            else 0
        end as keep_for_transition_lineage
    from ordered_versions ov
),
transition_series_summary as (
    select
        series_id,
        count(*)::bigint as total_rows,
        sum(keep_for_transition_lineage)::bigint as transition_lineage_keep_rows,
        (count(*) - sum(keep_for_transition_lineage))::bigint as consecutive_identical_repeat_rows,
        count(distinct (series_id, observation_date))::bigint as observation_date_groups,
        count(distinct (series_id, observation_date)) filter (
            where keep_for_transition_lineage = 1
        )::bigint as groups_with_kept_version
    from transition_flags
    group by series_id
),
revision_transition_groups as (
    select
        tf.series_id,
        tf.observation_date,
        count(*)::bigint as version_count,
        count(distinct tf.value)::bigint as distinct_value_count,
        sum(tf.keep_for_transition_lineage)::bigint as transition_keep_count,
        (count(*) - sum(tf.keep_for_transition_lineage))::bigint as consecutive_identical_repeat_rows,
        min(tf.realtime_start) as first_realtime_start,
        max(tf.realtime_start) as last_realtime_start
    from transition_flags tf
    group by tf.series_id, tf.observation_date
    having count(distinct tf.value) > 1
),
fetched_at_mutation_summary as (
    select
        count(*)::bigint as total_rows,
        count(*) filter (
            where fetched_at::date = realtime_start
        )::bigint as fetched_date_equals_realtime_start,
        count(*) filter (
            where fetched_at::date > realtime_start
        )::bigint as fetched_date_after_realtime_start,
        count(*) filter (
            where fetched_at::date < realtime_start
        )::bigint as fetched_date_before_realtime_start,
        max((fetched_at::date - realtime_start)) as max_fetch_date_lag_days
    from macro.observations
)
select jsonb_build_object(
    'checked_at', now(),

    'decision_ref_contract_summary',
    (select to_jsonb(x) from ref_summary x),

    'series_decision_ref_summary',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.series_id),
            '[]'::jsonb
        )
        from series_ref_summary x
    ),

    'fetched_at_mutation_evidence',
    (select to_jsonb(x) from fetched_at_mutation_summary x),

    'transition_lineage_summary',
    jsonb_build_object(
        'all_series',
        (
            select jsonb_build_object(
                'total_rows', sum(total_rows),
                'transition_lineage_keep_rows', sum(transition_lineage_keep_rows),
                'consecutive_identical_repeat_rows', sum(consecutive_identical_repeat_rows)
            )
            from transition_series_summary
        ),
        'by_series',
        (
            select coalesce(
                jsonb_agg(to_jsonb(x) order by x.series_id),
                '[]'::jsonb
            )
            from transition_series_summary x
        )
    ),

    'revision_transition_distribution',
    (
        select jsonb_build_object(
            'revision_groups', count(*),
            'version_rows_in_revision_groups', sum(version_count),
            'distinct_value_instances_sum', sum(distinct_value_count),
            'transition_keep_rows', sum(transition_keep_count),
            'consecutive_identical_repeat_rows', sum(consecutive_identical_repeat_rows),
            'max_versions_in_group', max(version_count),
            'max_transitions_in_group', max(transition_keep_count)
        )
        from revision_transition_groups
    ),

    'revision_group_examples',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select *
            from revision_transition_groups
            order by consecutive_identical_repeat_rows desc,
                     version_count desc,
                     observation_date desc,
                     series_id
            limit 30
        ) x
    ),

    'revision_decision_mismatch_examples',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select
                decision_id,
                system,
                decision_as_of,
                decision_evaluated_at,
                series_id,
                observation_date,
                persisted_value,
                version_count,
                distinct_value_count,
                eval_date_latest_id,
                eval_date_latest_value,
                eval_date_latest_realtime_start,
                eval_date_latest_fetched_at,
                persisted_matches_eval_date_latest,
                eval_timestamp_latest_id,
                eval_timestamp_latest_value,
                eval_timestamp_latest_realtime_start,
                eval_timestamp_latest_fetched_at,
                persisted_matches_eval_timestamp_latest,
                current_latest_id,
                current_latest_value,
                current_latest_realtime_start,
                persisted_matches_current_latest,
                matching_version_count,
                first_matching_realtime_start,
                last_matching_realtime_start,
                matching_versions_with_current_fetched_at_before_eval
            from ref_candidates
            where distinct_value_count > 1
              and (
                  persisted_matches_eval_date_latest is false
                  or persisted_matches_eval_date_latest is null
                  or persisted_matches_current_latest is false
                  or eval_timestamp_latest_id is null
              )
            order by decision_evaluated_at, decision_id, series_id
            limit 100
        ) x
    ),

    'latest_revision_decision_refs',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select
                decision_id,
                system,
                decision_as_of,
                decision_evaluated_at,
                series_id,
                observation_date,
                persisted_value,
                version_count,
                distinct_value_count,
                eval_date_latest_value,
                eval_date_latest_realtime_start,
                persisted_matches_eval_date_latest,
                current_latest_value,
                current_latest_realtime_start,
                persisted_matches_current_latest
            from ref_candidates
            where distinct_value_count > 1
            order by decision_evaluated_at desc, decision_id desc, series_id
            limit 30
        ) x
    )
) as macro_observations_p2_2_read_contract;
