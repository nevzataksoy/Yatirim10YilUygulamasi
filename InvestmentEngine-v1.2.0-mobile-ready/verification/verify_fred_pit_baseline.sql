-- Post-Shadow P1 — FRED strict point-in-time baseline
-- Read-only diagnostic. It does not mutate macro data, model settings, or validation rows.
--
-- Purpose:
--   1) measure how macro.observations currently uses realtime_start/realtime_end,
--   2) quantify duplicate/revised observation dates,
--   3) expose ambiguity at the latest observation date,
--   4) test whether the local table alone can answer historical strict-PIT cutoffs.
--
-- Run in the Supabase SQL editor and return the single JSON result row.

with configured(series_id) as (
    values
      ('DGS2'::text),
      ('DGS10'::text),
      ('DFII10'::text),
      ('VIXCLS'::text),
      ('STLFSI4'::text),
      ('DTWEXBGS'::text),
      ('NASDAQCOM'::text),
      ('SP500'::text)
),
obs_stats as (
    select
        m.series_id,
        m.observation_date,
        count(*)::int as rows_for_observation,
        count(distinct m.value)::int as distinct_values,
        min(m.realtime_start) as min_realtime_start,
        max(m.realtime_start) as max_realtime_start
    from macro.observations m
    join configured c using(series_id)
    group by m.series_id, m.observation_date
),
series_stats as (
    select
        c.series_id,
        count(m.id)::int as rows,
        count(distinct m.observation_date)::int as observation_dates,
        count(distinct m.realtime_start)::int as realtime_start_dates,
        min(m.observation_date) as min_observation_date,
        max(m.observation_date) as max_observation_date,
        min(m.realtime_start) as min_realtime_start,
        max(m.realtime_start) as max_realtime_start,
        count(*) filter (
            where m.id is not null
              and m.realtime_end = m.realtime_start
        )::int as same_day_realtime_rows,
        count(*) filter (
            where m.id is not null
              and m.realtime_end is not null
              and m.realtime_end > m.realtime_start
        )::int as interval_realtime_rows,
        count(*) filter (
            where m.id is not null
              and m.realtime_end is null
        )::int as open_ended_realtime_rows,
        coalesce(sum((o.rows_for_observation > 1)::int), 0)::int
            as observation_dates_with_multiple_rows,
        coalesce(sum((o.distinct_values > 1)::int), 0)::int
            as observation_dates_with_value_revisions,
        coalesce(max(o.rows_for_observation), 0)::int
            as max_rows_per_observation_date,
        coalesce(max(o.distinct_values), 0)::int
            as max_distinct_values_per_observation_date
    from configured c
    left join macro.observations m using(series_id)
    left join obs_stats o
      on o.series_id = c.series_id
     and o.observation_date = m.observation_date
    group by c.series_id
),
-- Re-aggregate duplicate/revision counts without row multiplication from the join above.
series_obs_summary as (
    select
        c.series_id,
        count(*) filter (where o.rows_for_observation > 1)::int
            as observation_dates_with_multiple_rows,
        count(*) filter (where o.distinct_values > 1)::int
            as observation_dates_with_value_revisions,
        coalesce(max(o.rows_for_observation), 0)::int
            as max_rows_per_observation_date,
        coalesce(max(o.distinct_values), 0)::int
            as max_distinct_values_per_observation_date
    from configured c
    left join obs_stats o using(series_id)
    group by c.series_id
),
coverage as (
    select
        s.series_id,
        s.rows,
        s.observation_dates,
        s.realtime_start_dates,
        s.min_observation_date,
        s.max_observation_date,
        s.min_realtime_start,
        s.max_realtime_start,
        s.same_day_realtime_rows,
        s.interval_realtime_rows,
        s.open_ended_realtime_rows,
        o.observation_dates_with_multiple_rows,
        o.observation_dates_with_value_revisions,
        o.max_rows_per_observation_date,
        o.max_distinct_values_per_observation_date
    from series_stats s
    join series_obs_summary o using(series_id)
),
latest_dates as (
    select
        c.series_id,
        max(m.observation_date) as observation_date
    from configured c
    left join macro.observations m using(series_id)
    group by c.series_id
),
latest_ambiguity as (
    select
        d.series_id,
        d.observation_date,
        count(m.id)::int as rows_at_latest_observation,
        count(distinct m.value)::int as distinct_values_at_latest_observation,
        min(m.realtime_start) as min_realtime_start,
        max(m.realtime_start) as max_realtime_start,
        array_agg(distinct m.value order by m.value)
            filter (where m.value is not null) as distinct_values
    from latest_dates d
    left join macro.observations m
      on m.series_id = d.series_id
     and m.observation_date = d.observation_date
    group by d.series_id, d.observation_date
),
cutoffs(cutoff) as (
    values
      ('2022-10-18'::date),
      ('2023-10-17'::date),
      ('2024-10-11'::date),
      ('2025-10-06'::date),
      ('2026-07-03'::date),
      (current_date)
),
pit_rows as (
    select
        k.cutoff,
        c.series_id,
        p.observation_date,
        p.value,
        p.realtime_start,
        p.realtime_end,
        (p.series_id is not null) as strict_pit_available
    from cutoffs k
    cross join configured c
    left join lateral (
        select
            m.series_id,
            m.observation_date,
            m.value,
            m.realtime_start,
            m.realtime_end
        from macro.observations m
        where m.series_id = c.series_id
          and m.observation_date <= k.cutoff
          and m.realtime_start <= k.cutoff
          and coalesce(m.realtime_end, '9999-12-31'::date) >= k.cutoff
        order by
            m.observation_date desc,
            m.realtime_start desc,
            m.fetched_at desc,
            m.id desc
        limit 1
    ) p on true
),
pit_summary as (
    select
        cutoff,
        count(*) filter (where strict_pit_available)::int as available_series,
        count(*)::int as configured_series,
        array_agg(series_id order by series_id)
            filter (where not strict_pit_available) as missing_series
    from pit_rows
    group by cutoff
),
revision_examples as (
    select
        m.series_id,
        m.observation_date,
        count(*)::int as rows,
        count(distinct m.value)::int as distinct_values,
        min(m.realtime_start) as min_realtime_start,
        max(m.realtime_start) as max_realtime_start,
        array_agg(distinct m.value order by m.value) as values
    from macro.observations m
    join configured c using(series_id)
    group by m.series_id, m.observation_date
    having count(distinct m.value) > 1
    order by m.observation_date desc, m.series_id
    limit 25
)
select jsonb_build_object(
    'generated_at', now(),
    'series_coverage', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.series_id)
        from coverage x
    ), '[]'::jsonb),
    'latest_observation_ambiguity', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.series_id)
        from latest_ambiguity x
    ), '[]'::jsonb),
    'strict_pit_cutoff_coverage', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.cutoff)
        from pit_summary x
    ), '[]'::jsonb),
    'strict_pit_cutoff_rows', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.cutoff, x.series_id)
        from pit_rows x
    ), '[]'::jsonb),
    'revision_examples', coalesce((
        select jsonb_agg(to_jsonb(x))
        from revision_examples x
    ), '[]'::jsonb),
    'interpretation_hints', jsonb_build_object(
        'same_day_realtime_rows',
            'High counts indicate fetch-day/FRED-current snapshots rather than full ALFRED validity intervals.',
        'value_revisions',
            'Any observation_dates_with_value_revisions > 0 proves observation_date-only replay can select different historical values.',
        'strict_pit_cutoff_coverage',
            'A cutoff is locally reconstructable only when a row validity interval contains that historical cutoff.',
        'latest_observation_ambiguity',
            'rows_at_latest_observation > 1 means production ordering by observation_date alone has a tie; distinct value count shows whether the tie can change the factor value.'
    )
) as fred_pit_baseline;
