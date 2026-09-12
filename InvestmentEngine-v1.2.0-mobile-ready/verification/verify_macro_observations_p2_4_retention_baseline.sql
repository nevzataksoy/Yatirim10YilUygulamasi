-- Post-Shadow P2.4 — macro.observations retention / maintenance production baseline
-- READ-ONLY. This query performs no DELETE/UPDATE/INSERT, no VACUUM, no DDL,
-- and does not change scheduler or model behavior.
--
-- Goal:
--   1) measure the retained P2.3 transition history by age/series,
--   2) identify decision + current replay evidence dependencies,
--   3) measure revision/reversion lineage and source-audit metadata,
--   4) measure physical table/index + vacuum/dead-tuple state,
--   5) expose consumer-unreferenced rows without declaring them safe to delete.
--
-- Current contract:
--   model v1.2.0 / SHADOW / READY / LIVE NO-GO
--   blind age-based retention is NOT authorized.
--
-- Expected result: one JSONB object named macro_observations_p2_4_retention_baseline.

with
params as (
    select
        '1.2.0'::text as model_version,
        1120::integer as replay_min_history_sessions,
        current_date as checked_date
),
configured_series(series_id) as (
    values
        ('DFII10'),
        ('DGS10'),
        ('DGS2'),
        ('DTWEXBGS'),
        ('NASDAQCOM'),
        ('SP500'),
        ('STLFSI4'),
        ('VIXCLS')
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
classified as (
    select
        o.*,
        case
            when o.seq_no = 1 then 'BASE_OBSERVATION'
            when o.value is distinct from o.previous_value then 'VALUE_TRANSITION'
            else 'SAME_VALUE_REPEAT'
        end as row_class
    from ordered o
),
group_stats as (
    select
        c.series_id,
        c.observation_date,
        count(*)::bigint as retained_rows,
        count(distinct c.value)::bigint as distinct_values,
        count(*) filter (where c.row_class = 'VALUE_TRANSITION')::bigint as transition_rows,
        count(*) filter (where c.row_class = 'SAME_VALUE_REPEAT')::bigint as same_value_repeat_rows
    from classified c
    group by c.series_id, c.observation_date
),
series_summary as (
    select
        s.series_id,
        count(c.id)::bigint as retained_rows,
        count(distinct c.observation_date)::bigint as observation_dates,
        min(c.observation_date) as min_observation_date,
        max(c.observation_date) as max_observation_date,
        min(c.fetched_at) as min_fetched_at,
        max(c.fetched_at) as max_fetched_at,
        count(*) filter (where c.row_class = 'BASE_OBSERVATION')::bigint as base_observation_rows,
        count(*) filter (where c.row_class = 'VALUE_TRANSITION')::bigint as value_transition_rows,
        count(*) filter (where c.row_class = 'SAME_VALUE_REPEAT')::bigint as same_value_repeat_rows,
        count(distinct c.observation_date) filter (
            where g.retained_rows > 1
        )::bigint as revision_groups,
        count(distinct c.observation_date) filter (
            where g.retained_rows > g.distinct_values
              and g.same_value_repeat_rows = 0
        )::bigint as value_reversion_groups
    from configured_series s
    left join classified c on c.series_id = s.series_id
    left join group_stats g
      on g.series_id = c.series_id
     and g.observation_date = c.observation_date
    group by s.series_id
),
observation_age_rows as (
    select
        c.series_id,
        case
            when c.observation_date >= current_date - interval '90 days'
                then '00_0_90d'
            when c.observation_date >= current_date - interval '1 year'
                then '01_91d_1y'
            when c.observation_date >= current_date - interval '3 years'
                then '02_1_3y'
            when c.observation_date >= current_date - interval '5 years'
                then '03_3_5y'
            when c.observation_date >= current_date - interval '10 years'
                then '04_5_10y'
            else '05_gt_10y'
        end as age_bucket,
        c.row_class
    from classified c
),
observation_age_by_series as (
    select
        a.series_id,
        a.age_bucket,
        count(*)::bigint as retained_rows,
        count(*) filter (where a.row_class = 'VALUE_TRANSITION')::bigint as value_transition_rows
    from observation_age_rows a
    group by a.series_id, a.age_bucket
),
fetched_age_rows as (
    select
        c.series_id,
        case
            when c.fetched_at >= now() - interval '7 days'
                then '00_0_7d'
            when c.fetched_at >= now() - interval '30 days'
                then '01_8_30d'
            when c.fetched_at >= now() - interval '90 days'
                then '02_31_90d'
            else '03_gt_90d'
        end as age_bucket,
        c.row_class
    from classified c
),
fetched_age_by_series as (
    select
        a.series_id,
        a.age_bucket,
        count(*)::bigint as retained_rows,
        count(*) filter (where a.row_class = 'VALUE_TRANSITION')::bigint as value_transition_rows
    from fetched_age_rows a
    group by a.series_id, a.age_bucket
),
released_decisions as (
    select d.id, d.system, d.as_of, d.created_at, d.factors
    from model.decisions d
    cross join params p
    where d.model_version = p.model_version
),
decision_refs as (
    select
        d.id as decision_id,
        d.system,
        d.as_of as decision_as_of,
        d.created_at as decision_created_at,
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
    from released_decisions d
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
valid_decision_refs as (
    select *
    from decision_refs
    where observation_date is not null
      and persisted_value is not null
),
decision_ref_match_counts as (
    select
        r.decision_id,
        r.system,
        r.series_id,
        r.observation_date,
        r.persisted_value,
        count(o.id)::bigint as matching_rows
    from valid_decision_refs r
    left join macro.observations o
      on o.series_id = r.series_id
     and o.observation_date = r.observation_date
     and o.value = r.persisted_value
    group by
        r.decision_id,
        r.system,
        r.series_id,
        r.observation_date,
        r.persisted_value
),
decision_protected_rows as (
    select distinct o.id
    from valid_decision_refs r
    join macro.observations o
      on o.series_id = r.series_id
     and o.observation_date = r.observation_date
     and o.value = r.persisted_value
),
decision_series_summary as (
    select
        r.series_id,
        count(*)::bigint as refs,
        count(distinct r.decision_id)::bigint as decisions,
        min(r.observation_date) as min_observation_date,
        max(r.observation_date) as max_observation_date,
        count(*) filter (where m.matching_rows > 0)::bigint as refs_preserved,
        count(*) filter (where m.matching_rows = 0)::bigint as refs_lost,
        count(*) filter (where m.matching_rows > 1)::bigint as refs_with_multiple_matching_rows
    from valid_decision_refs r
    join decision_ref_match_counts m
      on m.decision_id = r.decision_id
     and m.series_id = r.series_id
     and m.observation_date = r.observation_date
     and m.persisted_value = r.persisted_value
    group by r.series_id
),
common_price_dates as (
    select p.price_date
    from market.daily_prices p
    where p.symbol in ('BTC-USD', 'ETH-USD')
    group by p.price_date
    having count(distinct p.symbol) = 2
),
numbered_common_dates as (
    select
        d.price_date,
        row_number() over (order by d.price_date) as session_no,
        count(*) over () as total_sessions
    from common_price_dates d
),
replay_eval_dates as (
    select n.price_date as evaluation_date
    from numbered_common_dates n
    cross join params p
    where n.session_no >= p.replay_min_history_sessions
),
replay_selected as (
    select
        e.evaluation_date,
        s.series_id,
        x.id,
        x.observation_date,
        x.value,
        x.realtime_start,
        x.fetched_at
    from replay_eval_dates e
    cross join configured_series s
    left join lateral (
        select
            o.id,
            o.observation_date,
            o.value,
            o.realtime_start,
            o.fetched_at
        from macro.observations o
        where o.series_id = s.series_id
          and o.observation_date <= e.evaluation_date
        order by
            o.observation_date desc,
            o.realtime_start desc,
            o.fetched_at desc,
            o.id desc
        limit 1
    ) x on true
),
replay_protected_rows as (
    select distinct id
    from replay_selected
    where id is not null
),
replay_series_summary as (
    select
        r.series_id,
        count(*)::bigint as evaluation_dates,
        count(*) filter (where r.id is not null)::bigint as resolved_evaluations,
        count(*) filter (where r.id is null)::bigint as unresolved_evaluations,
        count(distinct r.id) filter (where r.id is not null)::bigint as distinct_rows_selected,
        min(r.observation_date) filter (where r.id is not null) as min_selected_observation_date,
        max(r.observation_date) filter (where r.id is not null) as max_selected_observation_date
    from replay_selected r
    group by r.series_id
),
validation_run_summary as (
    select
        count(*) filter (
            where v.validation_type = 'PIT_CORE_REPLAY'
        )::bigint as pit_core_replay_runs,
        min(v.start_date) filter (
            where v.validation_type = 'PIT_CORE_REPLAY'
        ) as earliest_recorded_replay_start,
        max(v.end_date) filter (
            where v.validation_type = 'PIT_CORE_REPLAY'
        ) as latest_recorded_replay_end,
        max(v.finished_at) filter (
            where v.validation_type = 'PIT_CORE_REPLAY'
        ) as latest_recorded_replay_finished_at
    from model.validation_runs v
    cross join params p
    where v.model_version = p.model_version
),
consumer_protected_rows as (
    select id from decision_protected_rows
    union
    select id from replay_protected_rows
),
consumer_reference_summary as (
    select
        count(*)::bigint as total_retained_rows,
        count(*) filter (
            where p.id is not null
        )::bigint as directly_referenced_rows,
        count(*) filter (
            where p.id is null
        )::bigint as consumer_unreferenced_rows,
        count(*) filter (
            where p.id is null
              and c.row_class = 'BASE_OBSERVATION'
        )::bigint as unreferenced_base_rows,
        count(*) filter (
            where p.id is null
              and c.row_class = 'VALUE_TRANSITION'
        )::bigint as unreferenced_value_transition_rows,
        count(*) filter (
            where p.id is null
              and c.row_class = 'SAME_VALUE_REPEAT'
        )::bigint as unreferenced_same_value_repeat_rows,
        count(*) filter (
            where p.id is null
              and c.observation_date < current_date - interval '1 year'
        )::bigint as unreferenced_observation_older_than_1y,
        count(*) filter (
            where p.id is null
              and c.observation_date < current_date - interval '3 years'
        )::bigint as unreferenced_observation_older_than_3y,
        count(*) filter (
            where p.id is null
              and c.observation_date < current_date - interval '5 years'
        )::bigint as unreferenced_observation_older_than_5y,
        count(*) filter (
            where p.id is null
              and c.observation_date < current_date - interval '10 years'
        )::bigint as unreferenced_observation_older_than_10y
    from classified c
    left join consumer_protected_rows p on p.id = c.id
),
lineage_summary as (
    select
        count(*)::bigint as retained_rows,
        count(distinct (series_id, observation_date))::bigint as observation_date_groups,
        count(*) filter (where row_class = 'BASE_OBSERVATION')::bigint as base_observation_rows,
        count(*) filter (where row_class = 'VALUE_TRANSITION')::bigint as legitimate_value_transition_rows,
        count(*) filter (where row_class = 'SAME_VALUE_REPEAT')::bigint as non_lineage_same_value_repeat_rows,
        count(*) filter (where realtime_start is null)::bigint as rows_missing_realtime_start,
        count(*) filter (where fetched_at is null)::bigint as rows_missing_fetched_at
    from classified
),
decision_overall as (
    select
        count(*)::bigint as refs_checked,
        count(*) filter (where matching_rows > 0)::bigint as refs_preserved,
        count(*) filter (where matching_rows = 0)::bigint as refs_lost,
        count(*) filter (where matching_rows > 1)::bigint as refs_with_multiple_matching_rows
    from decision_ref_match_counts
),
replay_overall as (
    select
        (select count(*)::bigint from common_price_dates) as common_price_sessions,
        (select min(price_date) from common_price_dates) as first_common_price_date,
        (select max(price_date) from common_price_dates) as last_common_price_date,
        (select min(evaluation_date) from replay_eval_dates) as first_replay_evaluation_date,
        (select count(*)::bigint from replay_eval_dates) as replay_evaluation_dates,
        (select count(distinct id)::bigint from replay_protected_rows) as distinct_replay_rows,
        (select count(*)::bigint from replay_selected where id is null) as unresolved_series_evaluations
),
relation_sizes as (
    select
        pg_relation_size('macro.observations'::regclass)::bigint as heap_bytes,
        pg_indexes_size('macro.observations'::regclass)::bigint as indexes_bytes,
        pg_total_relation_size('macro.observations'::regclass)::bigint as total_bytes
),
table_stats as (
    select
        s.n_live_tup::bigint as n_live_tup,
        s.n_dead_tup::bigint as n_dead_tup,
        s.n_tup_ins::bigint as n_tup_ins,
        s.n_tup_upd::bigint as n_tup_upd,
        s.n_tup_del::bigint as n_tup_del,
        s.n_mod_since_analyze::bigint as n_mod_since_analyze,
        s.n_ins_since_vacuum::bigint as n_ins_since_vacuum,
        s.vacuum_count::bigint as vacuum_count,
        s.autovacuum_count::bigint as autovacuum_count,
        s.analyze_count::bigint as analyze_count,
        s.autoanalyze_count::bigint as autoanalyze_count,
        s.last_vacuum,
        s.last_autovacuum,
        s.last_analyze,
        s.last_autoanalyze
    from pg_stat_user_tables s
    where s.schemaname = 'macro'
      and s.relname = 'observations'
),
index_stats as (
    select
        i.indexrelname as index_name,
        pg_relation_size(i.indexrelid)::bigint as index_bytes,
        pg_size_pretty(pg_relation_size(i.indexrelid)) as index_size,
        i.idx_scan::bigint as idx_scan,
        i.idx_tup_read::bigint as idx_tup_read,
        i.idx_tup_fetch::bigint as idx_tup_fetch
    from pg_stat_user_indexes i
    where i.schemaname = 'macro'
      and i.relname = 'observations'
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
)
select jsonb_build_object(
    'checked_at', now(),
    'model_version', (select model_version from params),
    'mode_contract', 'SHADOW / READY / LIVE NO-GO',
    'mutation_performed', false,

    'lineage_contract', (
        select jsonb_build_object(
            'retained_rows', l.retained_rows,
            'observation_date_groups', l.observation_date_groups,
            'base_observation_rows', l.base_observation_rows,
            'legitimate_value_transition_rows', l.legitimate_value_transition_rows,
            'non_lineage_same_value_repeat_rows', l.non_lineage_same_value_repeat_rows,
            'rows_missing_realtime_start', l.rows_missing_realtime_start,
            'rows_missing_fetched_at', l.rows_missing_fetched_at,
            'p2_3_same_value_contract_intact', l.non_lineage_same_value_repeat_rows = 0
        )
        from lineage_summary l
    ),

    'series_summary', coalesce((
        select jsonb_agg(
            jsonb_build_object(
                'series_id', s.series_id,
                'retained_rows', s.retained_rows,
                'observation_dates', s.observation_dates,
                'min_observation_date', s.min_observation_date,
                'max_observation_date', s.max_observation_date,
                'min_fetched_at', s.min_fetched_at,
                'max_fetched_at', s.max_fetched_at,
                'base_observation_rows', s.base_observation_rows,
                'value_transition_rows', s.value_transition_rows,
                'same_value_repeat_rows', s.same_value_repeat_rows,
                'revision_groups', s.revision_groups,
                'value_reversion_groups', s.value_reversion_groups
            )
            order by s.series_id
        )
        from series_summary s
    ), '[]'::jsonb),

    'observation_age_by_series', coalesce((
        select jsonb_agg(
            jsonb_build_object(
                'series_id', a.series_id,
                'age_bucket', a.age_bucket,
                'retained_rows', a.retained_rows,
                'value_transition_rows', a.value_transition_rows
            )
            order by a.series_id, a.age_bucket
        )
        from observation_age_by_series a
    ), '[]'::jsonb),

    'fetched_age_by_series', coalesce((
        select jsonb_agg(
            jsonb_build_object(
                'series_id', a.series_id,
                'age_bucket', a.age_bucket,
                'retained_rows', a.retained_rows,
                'value_transition_rows', a.value_transition_rows
            )
            order by a.series_id, a.age_bucket
        )
        from fetched_age_by_series a
    ), '[]'::jsonb),

    'released_decision_evidence', jsonb_build_object(
        'overall', (
            select jsonb_build_object(
                'refs_checked', d.refs_checked,
                'refs_preserved', d.refs_preserved,
                'refs_lost', d.refs_lost,
                'refs_with_multiple_matching_rows', d.refs_with_multiple_matching_rows,
                'distinct_protected_rows', (select count(*)::bigint from decision_protected_rows)
            )
            from decision_overall d
        ),
        'by_series', coalesce((
            select jsonb_agg(
                jsonb_build_object(
                    'series_id', s.series_id,
                    'refs', s.refs,
                    'decisions', s.decisions,
                    'min_observation_date', s.min_observation_date,
                    'max_observation_date', s.max_observation_date,
                    'refs_preserved', s.refs_preserved,
                    'refs_lost', s.refs_lost,
                    'refs_with_multiple_matching_rows', s.refs_with_multiple_matching_rows
                )
                order by s.series_id
            )
            from decision_series_summary s
        ), '[]'::jsonb)
    ),

    'current_model_replay_dependency', jsonb_build_object(
        'replay_contract', 'BTC/ETH common sessions; first evaluation at session 1120; deterministic latest macro row <= evaluation date',
        'overall', (
            select jsonb_build_object(
                'common_price_sessions', r.common_price_sessions,
                'first_common_price_date', r.first_common_price_date,
                'last_common_price_date', r.last_common_price_date,
                'first_replay_evaluation_date', r.first_replay_evaluation_date,
                'replay_evaluation_dates', r.replay_evaluation_dates,
                'distinct_replay_rows', r.distinct_replay_rows,
                'unresolved_series_evaluations', r.unresolved_series_evaluations
            )
            from replay_overall r
        ),
        'by_series', coalesce((
            select jsonb_agg(
                jsonb_build_object(
                    'series_id', s.series_id,
                    'evaluation_dates', s.evaluation_dates,
                    'resolved_evaluations', s.resolved_evaluations,
                    'unresolved_evaluations', s.unresolved_evaluations,
                    'distinct_rows_selected', s.distinct_rows_selected,
                    'min_selected_observation_date', s.min_selected_observation_date,
                    'max_selected_observation_date', s.max_selected_observation_date
                )
                order by s.series_id
            )
            from replay_series_summary s
        ), '[]'::jsonb),
        'recorded_validation_runs', (
            select jsonb_build_object(
                'pit_core_replay_runs', v.pit_core_replay_runs,
                'earliest_recorded_replay_start', v.earliest_recorded_replay_start,
                'latest_recorded_replay_end', v.latest_recorded_replay_end,
                'latest_recorded_replay_finished_at', v.latest_recorded_replay_finished_at
            )
            from validation_run_summary v
        )
    ),

    'consumer_reference_classification', (
        select jsonb_build_object(
            'total_retained_rows', c.total_retained_rows,
            'directly_referenced_rows', c.directly_referenced_rows,
            'consumer_unreferenced_rows', c.consumer_unreferenced_rows,
            'unreferenced_base_rows', c.unreferenced_base_rows,
            'unreferenced_value_transition_rows', c.unreferenced_value_transition_rows,
            'unreferenced_same_value_repeat_rows', c.unreferenced_same_value_repeat_rows,
            'unreferenced_observation_older_than_1y', c.unreferenced_observation_older_than_1y,
            'unreferenced_observation_older_than_3y', c.unreferenced_observation_older_than_3y,
            'unreferenced_observation_older_than_5y', c.unreferenced_observation_older_than_5y,
            'unreferenced_observation_older_than_10y', c.unreferenced_observation_older_than_10y,
            'classification_only', true,
            'delete_authorized', false,
            'note', 'Consumer-unreferenced does not mean safe-to-delete; revision lineage, source audit and future validation coverage remain protection constraints.'
        )
        from consumer_reference_summary c
    ),

    'source_revision_audit', jsonb_build_object(
        'production_store_semantics', 'FRED current-view value-transition history after P2.3; realtime_start/end alone are not economic revision identity.',
        'strict_pit_semantics', 'Strict FRED/ALFRED realtime history is fetched through the separate DB-write-free verification path.',
        'retention_implication', 'Do not remove legitimate value transitions/reversions merely because current decisions or replay do not directly select them.'
    ),

    'physical_maintenance', jsonb_build_object(
        'relation_sizes', (
            select jsonb_build_object(
                'heap_bytes', r.heap_bytes,
                'heap_size', pg_size_pretty(r.heap_bytes),
                'indexes_bytes', r.indexes_bytes,
                'indexes_size', pg_size_pretty(r.indexes_bytes),
                'total_bytes', r.total_bytes,
                'total_size', pg_size_pretty(r.total_bytes)
            )
            from relation_sizes r
        ),
        'table_stats', coalesce((
            select jsonb_build_object(
                'n_live_tup', s.n_live_tup,
                'n_dead_tup', s.n_dead_tup,
                'n_tup_ins', s.n_tup_ins,
                'n_tup_upd', s.n_tup_upd,
                'n_tup_del', s.n_tup_del,
                'n_mod_since_analyze', s.n_mod_since_analyze,
                'n_ins_since_vacuum', s.n_ins_since_vacuum,
                'vacuum_count', s.vacuum_count,
                'autovacuum_count', s.autovacuum_count,
                'analyze_count', s.analyze_count,
                'autoanalyze_count', s.autoanalyze_count,
                'last_vacuum', s.last_vacuum,
                'last_autovacuum', s.last_autovacuum,
                'last_analyze', s.last_analyze,
                'last_autoanalyze', s.last_autoanalyze
            )
            from table_stats s
        ), '{}'::jsonb),
        'indexes', coalesce((
            select jsonb_agg(
                jsonb_build_object(
                    'index_name', i.index_name,
                    'index_bytes', i.index_bytes,
                    'index_size', i.index_size,
                    'idx_scan', i.idx_scan,
                    'idx_tup_read', i.idx_tup_read,
                    'idx_tup_fetch', i.idx_tup_fetch
                )
                order by i.index_name
            )
            from index_stats i
        ), '[]'::jsonb),
        'legacy_unique_constraint_present', (select present from legacy_constraint),
        'deterministic_version_index_present', (select present from version_index),
        'vacuum_full_authorized', false
    ),

    'baseline_complete',
        (select non_lineage_same_value_repeat_rows = 0 from lineage_summary)
        and (select refs_lost = 0 from decision_overall)
        and (select common_price_sessions >= replay_min_history_sessions
             from replay_overall cross join params)
        and (select first_replay_evaluation_date is not null from replay_overall)
        and (select unresolved_series_evaluations = 0 from replay_overall)
        and (select count(*) = 8 from series_summary where retained_rows > 0)
        and (select present = false from legacy_constraint)
        and (select present = true from version_index)
) as macro_observations_p2_4_retention_baseline;
