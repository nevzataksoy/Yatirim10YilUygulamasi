-- Post-Shadow P2.1 — macro.observations production baseline / duplicate classification
-- READ-ONLY. Bu sorgu hiçbir production satırını değiştirmez veya silmez.
--
-- Amaç:
--   * logical row/version dağılımını ölçmek,
--   * aynı observation date için gerçek value revision ile aynı-value refetch
--     version adaylarını ayırmak,
--   * physical size + PostgreSQL update/dead-tuple churn kanıtını görmek,
--   * released 1.2.0 decision macro references ve validation input tarih aralığını
--     retention/dedup tasarımından önce sabitlemek.
--
-- Bu sorgunun çıktısı tek başına DELETE/UNIQUE/retention kararı değildir.

with
configured_series(series_id) as (
    values
        ('DGS2'),
        ('DGS10'),
        ('DFII10'),
        ('VIXCLS'),
        ('STLFSI4'),
        ('DTWEXBGS'),
        ('NASDAQCOM'),
        ('SP500')
),
base as (
    select
        o.id,
        o.series_id,
        o.observation_date,
        o.value,
        o.realtime_start,
        o.realtime_end,
        o.fetched_at
    from macro.observations o
),
version_groups as (
    select
        series_id,
        observation_date,
        count(*)::bigint as version_count,
        count(distinct value)::bigint as distinct_value_count,
        count(distinct realtime_start)::bigint as distinct_realtime_start_count,
        min(realtime_start) as first_realtime_start,
        max(realtime_start) as last_realtime_start,
        min(fetched_at) as first_fetched_at,
        max(fetched_at) as last_fetched_at
    from base
    group by series_id, observation_date
),
classified as (
    select
        vg.*,
        case
            when version_count = 1 then 'SINGLE OBSERVATION'
            when version_count > 1 and distinct_value_count = 1
                then 'IDENTICAL CURRENT-VIEW REFETCH VERSION'
            when version_count > 1 and distinct_value_count > 1
                then 'ACTUAL VALUE REVISION'
            else 'UNRESOLVED'
        end as classification,
        case
            when version_count > 1 and distinct_value_count = 1
                then version_count - 1
            else 0
        end::bigint as candidate_redundant_rows
    from version_groups vg
),
series_summary as (
    select
        c.series_id,
        sum(c.version_count)::bigint as row_count,
        count(*)::bigint as observation_date_count,
        min(c.observation_date) as min_observation_date,
        max(c.observation_date) as max_observation_date,
        min(c.first_realtime_start) as min_realtime_start,
        max(c.last_realtime_start) as max_realtime_start,
        min(c.first_fetched_at) as min_fetched_at,
        max(c.last_fetched_at) as max_fetched_at,
        max(c.version_count)::bigint as max_versions_per_observation_date,
        count(*) filter (where c.version_count > 1)::bigint as multi_version_date_count,
        count(*) filter (
            where c.classification = 'IDENTICAL CURRENT-VIEW REFETCH VERSION'
        )::bigint as identical_refetch_date_count,
        count(*) filter (
            where c.classification = 'ACTUAL VALUE REVISION'
        )::bigint as actual_revision_date_count,
        sum(c.candidate_redundant_rows)::bigint as identical_refetch_candidate_redundant_rows
    from classified c
    group by c.series_id
),
classification_summary as (
    select
        classification,
        count(*)::bigint as observation_date_groups,
        sum(version_count)::bigint as rows_in_groups,
        sum(candidate_redundant_rows)::bigint as candidate_redundant_rows
    from classified
    group by classification
),
latest_decisions as (
    select distinct on (d.system)
        d.id,
        d.system,
        d.as_of,
        d.created_at,
        d.status,
        d.factors
    from model.decisions d
    where d.model_version = '1.2.0'
    order by d.system, d.created_at desc, d.id desc
),
decision_ref_rows as (
    select
        d.id as decision_id,
        d.system,
        d.as_of as decision_as_of,
        d.created_at as decision_created_at,
        kv.key as series_id,
        case
            when kv.value ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                then kv.value::date
            else null
        end as observation_date
    from model.decisions d
    cross join lateral jsonb_each_text(
        case
            when jsonb_typeof(d.factors #> '{macro,details,observation_dates}') = 'object'
                then d.factors #> '{macro,details,observation_dates}'
            else '{}'::jsonb
        end
    ) kv
    where d.model_version = '1.2.0'
),
decision_ref_coverage as (
    select
        series_id,
        count(*) filter (where observation_date is not null)::bigint as reference_count,
        min(observation_date) as min_referenced_observation_date,
        max(observation_date) as max_referenced_observation_date,
        min(decision_created_at) filter (where observation_date is not null) as first_decision_reference_at,
        max(decision_created_at) filter (where observation_date is not null) as last_decision_reference_at
    from decision_ref_rows
    group by series_id
),
decision_ref_ambiguity as (
    select
        count(*) filter (where r.observation_date is not null)::bigint as valid_decision_macro_refs,
        count(*) filter (
            where r.observation_date is not null and c.version_count is not null
        )::bigint as refs_resolved_to_macro_date_group,
        count(*) filter (
            where r.observation_date is not null and c.version_count > 1
        )::bigint as refs_pointing_to_multi_version_date,
        count(*) filter (
            where r.observation_date is not null
              and c.classification = 'IDENTICAL CURRENT-VIEW REFETCH VERSION'
        )::bigint as refs_pointing_to_identical_refetch_date,
        count(*) filter (
            where r.observation_date is not null
              and c.classification = 'ACTUAL VALUE REVISION'
        )::bigint as refs_pointing_to_actual_revision_date
    from decision_ref_rows r
    left join classified c
      on c.series_id = r.series_id
     and c.observation_date = r.observation_date
),
btc_dates as (
    select distinct price_date
    from market.daily_prices
    where symbol = 'BTC-USD'
),
eth_dates as (
    select distinct price_date
    from market.daily_prices
    where symbol = 'ETH-USD'
),
crypto_common_history as (
    select
        min(b.price_date) as first_common_price_date,
        max(b.price_date) as last_common_price_date,
        count(*)::bigint as common_price_days
    from btc_dates b
    join eth_dates e using (price_date)
)
select jsonb_build_object(
    'checked_at', now(),

    'configured_series',
    (
        select jsonb_agg(series_id order by series_id)
        from configured_series
    ),

    'table_summary',
    (
        select jsonb_build_object(
            'total_rows', count(*),
            'series_count', count(distinct series_id),
            'series_observation_date_groups', count(distinct (series_id, observation_date)),
            'min_observation_date', min(observation_date),
            'max_observation_date', max(observation_date),
            'min_fetched_at', min(fetched_at),
            'max_fetched_at', max(fetched_at),
            'realtime_start_equals_current_fetched_date_rows',
                count(*) filter (where realtime_start = fetched_at::date),
            'realtime_start_differs_from_current_fetched_date_rows',
                count(*) filter (where realtime_start <> fetched_at::date)
        )
        from base
    ),

    'physical_size',
    jsonb_build_object(
        'heap_bytes', pg_relation_size('macro.observations'::regclass),
        'heap_pretty', pg_size_pretty(pg_relation_size('macro.observations'::regclass)),
        'indexes_bytes', pg_indexes_size('macro.observations'::regclass),
        'indexes_pretty', pg_size_pretty(pg_indexes_size('macro.observations'::regclass)),
        'total_bytes', pg_total_relation_size('macro.observations'::regclass),
        'total_pretty', pg_size_pretty(pg_total_relation_size('macro.observations'::regclass))
    ),

    'postgres_activity',
    (
        select jsonb_build_object(
            'stats_reset',
                (select stats_reset from pg_stat_database where datname = current_database()),
            'n_live_tup', s.n_live_tup,
            'n_dead_tup', s.n_dead_tup,
            'n_tup_ins', s.n_tup_ins,
            'n_tup_upd', s.n_tup_upd,
            'n_tup_del', s.n_tup_del,
            'n_tup_hot_upd', s.n_tup_hot_upd,
            'last_vacuum', s.last_vacuum,
            'last_autovacuum', s.last_autovacuum,
            'vacuum_count', s.vacuum_count,
            'autovacuum_count', s.autovacuum_count,
            'last_analyze', s.last_analyze,
            'last_autoanalyze', s.last_autoanalyze
        )
        from pg_stat_user_tables s
        where s.schemaname = 'macro'
          and s.relname = 'observations'
    ),

    'index_activity',
    (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'index_name', i.indexrelname,
                    'index_size_bytes', pg_relation_size(i.indexrelid),
                    'index_size_pretty', pg_size_pretty(pg_relation_size(i.indexrelid)),
                    'idx_scan', i.idx_scan,
                    'idx_tup_read', i.idx_tup_read,
                    'idx_tup_fetch', i.idx_tup_fetch
                )
                order by i.indexrelname
            ),
            '[]'::jsonb
        )
        from pg_stat_user_indexes i
        where i.schemaname = 'macro'
          and i.relname = 'observations'
    ),

    'classification_summary',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.classification),
            '[]'::jsonb
        )
        from classification_summary x
    ),

    'series_summary',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.series_id),
            '[]'::jsonb
        )
        from series_summary x
    ),

    'configured_series_missing_from_table',
    (
        select coalesce(jsonb_agg(x.series_id order by x.series_id), '[]'::jsonb)
        from (
            select cs.series_id
            from configured_series cs
            where not exists (
                select 1
                from base b
                where b.series_id = cs.series_id
            )
        ) x
    ),

    'unexpected_series_in_table',
    (
        select coalesce(jsonb_agg(x.series_id order by x.series_id), '[]'::jsonb)
        from (
            select distinct b.series_id
            from base b
            where not exists (
                select 1
                from configured_series cs
                where cs.series_id = b.series_id
            )
        ) x
    ),

    'age_distribution',
    (
        select jsonb_build_object(
            'fetched_older_than_7d_rows',
                count(*) filter (where fetched_at < now() - interval '7 days'),
            'fetched_older_than_30d_rows',
                count(*) filter (where fetched_at < now() - interval '30 days'),
            'fetched_older_than_90d_rows',
                count(*) filter (where fetched_at < now() - interval '90 days'),
            'fetched_older_than_180d_rows',
                count(*) filter (where fetched_at < now() - interval '180 days'),
            'observation_older_than_1y_rows',
                count(*) filter (where observation_date < current_date - interval '1 year'),
            'observation_older_than_3y_rows',
                count(*) filter (where observation_date < current_date - interval '3 years'),
            'observation_older_than_5y_rows',
                count(*) filter (where observation_date < current_date - interval '5 years'),
            'observation_older_than_10y_rows',
                count(*) filter (where observation_date < current_date - interval '10 years')
        )
        from base
    ),

    'top_multi_version_groups',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x)),
            '[]'::jsonb
        )
        from (
            select
                series_id,
                observation_date,
                version_count,
                distinct_value_count,
                distinct_realtime_start_count,
                classification,
                candidate_redundant_rows,
                first_realtime_start,
                last_realtime_start,
                first_fetched_at,
                last_fetched_at
            from classified
            where version_count > 1
            order by version_count desc, observation_date desc, series_id
            limit 50
        ) x
    ),

    'latest_decision_macro_refs',
    (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'system', d.system,
                    'decision_id', d.id,
                    'as_of', d.as_of,
                    'created_at', d.created_at,
                    'status', d.status,
                    'observation_dates',
                        case
                            when jsonb_typeof(d.factors #> '{macro,details,observation_dates}') = 'object'
                                then d.factors #> '{macro,details,observation_dates}'
                            else '{}'::jsonb
                        end
                )
                order by d.system
            ),
            '[]'::jsonb
        )
        from latest_decisions d
    ),

    'decision_macro_ref_coverage',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.series_id),
            '[]'::jsonb
        )
        from decision_ref_coverage x
    ),

    'decision_macro_ref_version_ambiguity',
    (
        select to_jsonb(x)
        from decision_ref_ambiguity x
    ),

    'validation_market_history_boundary',
    (
        select to_jsonb(x)
        from crypto_common_history x
    )
) as macro_observations_p2_1_baseline;
