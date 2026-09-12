-- Post-Shadow P2.3 — macro.observations post-migration verification
-- READ-ONLY. Run after migration 0015 and the hardened runtime deployment.

with
ordered as (
    select
        o.id,
        o.series_id,
        o.observation_date,
        o.value,
        o.realtime_start,
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
remaining_duplicates as (
    select count(*)::bigint as n
    from ordered
    where seq_no > 1
      and value is not distinct from previous_value
),
group_stats as (
    select
        series_id,
        observation_date,
        count(*)::bigint as transition_rows,
        count(distinct value)::bigint as distinct_values
    from macro.observations
    group by series_id, observation_date
),
transition_summary as (
    select
        count(*)::bigint as observation_date_groups,
        count(*) filter (where distinct_values > 1)::bigint as revision_groups,
        count(*) filter (where transition_rows > distinct_values)::bigint as value_reversion_groups
    from group_stats
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
        (select count(*)::bigint from macro.observations) as total_rows,
        (select n from remaining_duplicates) as consecutive_same_value_rows,
        ts.observation_date_groups,
        ts.revision_groups,
        ts.value_reversion_groups,
        dp.refs_checked as decision_refs_checked,
        dp.refs_preserved as decision_refs_preserved,
        (dp.refs_checked - dp.refs_preserved) as decision_refs_lost,
        lc.present as legacy_unique_constraint_present,
        vi.present as version_index_present
    from transition_summary ts
    cross join decision_preservation dp
    cross join legacy_constraint lc
    cross join version_index vi
)
select jsonb_build_object(
    'checked_at', now(),
    'total_rows', total_rows,
    'consecutive_same_value_rows', consecutive_same_value_rows,
    'observation_date_groups', observation_date_groups,
    'revision_groups', revision_groups,
    'value_reversion_groups', value_reversion_groups,
    'decision_refs_checked', decision_refs_checked,
    'decision_refs_preserved', decision_refs_preserved,
    'decision_refs_lost', decision_refs_lost,
    'legacy_unique_constraint_present', legacy_unique_constraint_present,
    'version_index_present', version_index_present,
    'safe_cleanup_complete',
        consecutive_same_value_rows = 0
        and decision_refs_lost = 0
        and legacy_unique_constraint_present = false
        and version_index_present = true
) as macro_observations_p2_3_post_migration
from summary;
