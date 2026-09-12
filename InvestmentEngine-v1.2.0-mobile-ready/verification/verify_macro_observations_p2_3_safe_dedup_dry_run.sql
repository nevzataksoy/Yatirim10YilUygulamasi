-- Post-Shadow P2.3 — macro.observations safe dedup dry-run
-- READ-ONLY. Bu sorgu hiçbir production satırını değiştirmez veya silmez.
--
-- Accepted P2.2 contract:
--   * FRED production current-view realtime_start/realtime_end default olarak query real-time date'i taşır.
--   * realtime_start/end değişimi tek başına value revision değildir.
--   * revision lineage value transition zinciridir.
--   * A -> B -> A gibi geri dönüşler korunmalıdır.
--   * yalnız ardışık same-value current-view refetch row'ları dedup adayıdır.
--
-- Bu sorgu:
--   1. her series/date zincirini realtime_start,id sırasına koyar,
--   2. first row + her value transition row'unu RETAINED sayar,
--   3. yalnız previous value ile aynı olan row'ları CANDIDATE_DELETE sayar,
--   4. persisted 1.2.0 decision series/date/value refs retained set'te korunuyor mu kontrol eder,
--   5. her group ve current-series latest value before/after parity kontrol eder,
--   6. candidate hacmini seri/yaş/revision group bazında ölçer.

with
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
ordered as (
    select
        b.*,
        row_number() over (
            partition by b.series_id, b.observation_date
            order by b.realtime_start asc, b.id asc
        ) as seq_no,
        lag(b.value) over (
            partition by b.series_id, b.observation_date
            order by b.realtime_start asc, b.id asc
        ) as previous_value
    from base b
),
classified as (
    select
        o.*,
        case
            when o.seq_no = 1 then true
            when o.value is distinct from o.previous_value then true
            else false
        end as retain,
        case
            when o.seq_no = 1 then 'FIRST_VERSION'
            when o.value is distinct from o.previous_value then 'VALUE_TRANSITION'
            else 'IDENTICAL_CURRENT_VIEW_REFETCH'
        end as row_class
    from ordered o
),
retained as (
    select *
    from classified
    where retain
),
candidates as (
    select *
    from classified
    where not retain
),
group_stats as (
    select
        c.series_id,
        c.observation_date,
        count(*)::bigint as total_rows,
        count(distinct c.value)::bigint as distinct_value_count,
        count(*) filter (where c.retain)::bigint as retained_rows,
        count(*) filter (where not c.retain)::bigint as candidate_delete_rows,
        min(c.realtime_start) as first_realtime_start,
        max(c.realtime_start) as last_realtime_start
    from classified c
    group by c.series_id, c.observation_date
),
pre_group_latest as (
    select distinct on (b.series_id, b.observation_date)
        b.series_id,
        b.observation_date,
        b.id,
        b.value,
        b.realtime_start,
        b.fetched_at
    from base b
    order by b.series_id, b.observation_date, b.realtime_start desc, b.id desc
),
post_group_latest as (
    select distinct on (r.series_id, r.observation_date)
        r.series_id,
        r.observation_date,
        r.id,
        r.value,
        r.realtime_start,
        r.fetched_at
    from retained r
    order by r.series_id, r.observation_date, r.realtime_start desc, r.id desc
),
group_parity as (
    select
        p.series_id,
        p.observation_date,
        p.id as pre_latest_id,
        q.id as post_latest_id,
        p.value as pre_latest_value,
        q.value as post_latest_value,
        p.realtime_start as pre_latest_realtime_start,
        q.realtime_start as post_latest_realtime_start,
        (p.value = q.value) as value_equal
    from pre_group_latest p
    join post_group_latest q
      on q.series_id = p.series_id
     and q.observation_date = p.observation_date
),
pre_series_latest as (
    select distinct on (b.series_id)
        b.series_id,
        b.observation_date,
        b.value,
        b.realtime_start,
        b.id
    from base b
    order by
        b.series_id,
        b.observation_date desc,
        b.realtime_start desc,
        b.id desc
),
post_series_latest as (
    select distinct on (r.series_id)
        r.series_id,
        r.observation_date,
        r.value,
        r.realtime_start,
        r.id
    from retained r
    order by
        r.series_id,
        r.observation_date desc,
        r.realtime_start desc,
        r.id desc
),
series_latest_parity as (
    select
        p.series_id,
        p.observation_date as pre_observation_date,
        q.observation_date as post_observation_date,
        p.value as pre_value,
        q.value as post_value,
        p.realtime_start as pre_realtime_start,
        q.realtime_start as post_realtime_start,
        (
            p.observation_date = q.observation_date
            and p.value = q.value
        ) as value_date_equal
    from pre_series_latest p
    join post_series_latest q using (series_id)
),
decisions as (
    select
        d.id as decision_id,
        d.system,
        d.as_of,
        d.created_at,
        d.factors
    from model.decisions d
    where d.model_version = '1.2.0'
),
decision_refs as (
    select
        d.decision_id,
        d.system,
        d.as_of,
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
        r.*,
        exists (
            select 1
            from base b
            where b.series_id = r.series_id
              and b.observation_date = r.observation_date
              and b.value = r.persisted_value
        ) as exists_before,
        exists (
            select 1
            from retained k
            where k.series_id = r.series_id
              and k.observation_date = r.observation_date
              and k.value = r.persisted_value
        ) as exists_after
    from decision_refs r
    where r.observation_date is not null
      and r.persisted_value is not null
),
series_summary as (
    select
        c.series_id,
        count(*)::bigint as total_rows,
        count(*) filter (where c.retain)::bigint as retained_rows,
        count(*) filter (where not c.retain)::bigint as candidate_delete_rows,
        count(distinct c.observation_date)::bigint as observation_date_groups,
        count(distinct c.observation_date) filter (
            where gs.distinct_value_count > 1
        )::bigint as revision_groups,
        count(*) filter (
            where not c.retain and gs.distinct_value_count > 1
        )::bigint as candidate_rows_inside_revision_groups,
        count(*) filter (
            where not c.retain and gs.distinct_value_count = 1
        )::bigint as candidate_rows_inside_identical_only_groups
    from classified c
    join group_stats gs
      on gs.series_id = c.series_id
     and gs.observation_date = c.observation_date
    group by c.series_id
),
revision_transition_stats as (
    select
        gs.series_id,
        gs.observation_date,
        gs.total_rows,
        gs.distinct_value_count,
        gs.retained_rows,
        gs.candidate_delete_rows,
        (gs.retained_rows > gs.distinct_value_count) as contains_value_reversion,
        gs.first_realtime_start,
        gs.last_realtime_start
    from group_stats gs
    where gs.distinct_value_count > 1
),
summary as (
    select
        (select count(*) from base)::bigint as total_rows,
        (select count(*) from retained)::bigint as retained_rows,
        (select count(*) from candidates)::bigint as candidate_delete_rows,
        (select count(*) from group_stats)::bigint as observation_date_groups,
        (select count(*) from group_stats where distinct_value_count > 1)::bigint as revision_groups,
        (select count(*) from revision_transition_stats where contains_value_reversion)::bigint as revision_groups_with_value_reversion,
        (select count(*) from group_stats where retained_rows = 0)::bigint as groups_without_retained_row,
        (select count(*) from group_parity where value_equal is not true)::bigint as group_latest_value_mismatches,
        (select count(*) from series_latest_parity where value_date_equal is not true)::bigint as series_latest_value_date_mismatches,
        (select count(*) from decision_preservation)::bigint as decision_refs_checked,
        (select count(*) from decision_preservation where exists_before)::bigint as decision_refs_present_before,
        (select count(*) from decision_preservation where exists_after)::bigint as decision_refs_preserved_after,
        (select count(*) from decision_preservation where exists_before and not exists_after)::bigint as decision_refs_lost_by_candidate_cleanup
)
select jsonb_build_object(
    'checked_at', now(),

    'dry_run_summary',
    (
        select jsonb_build_object(
            'total_rows', s.total_rows,
            'retained_rows', s.retained_rows,
            'candidate_delete_rows', s.candidate_delete_rows,
            'candidate_delete_pct',
                round(100.0 * s.candidate_delete_rows / nullif(s.total_rows, 0), 4),
            'observation_date_groups', s.observation_date_groups,
            'revision_groups', s.revision_groups,
            'revision_groups_with_value_reversion', s.revision_groups_with_value_reversion,
            'groups_without_retained_row', s.groups_without_retained_row,
            'group_latest_value_mismatches', s.group_latest_value_mismatches,
            'series_latest_value_date_mismatches', s.series_latest_value_date_mismatches,
            'decision_refs_checked', s.decision_refs_checked,
            'decision_refs_present_before', s.decision_refs_present_before,
            'decision_refs_preserved_after', s.decision_refs_preserved_after,
            'decision_refs_lost_by_candidate_cleanup', s.decision_refs_lost_by_candidate_cleanup,
            'safe_dedup_contract_complete',
                (
                    s.groups_without_retained_row = 0
                    and s.group_latest_value_mismatches = 0
                    and s.series_latest_value_date_mismatches = 0
                    and s.decision_refs_lost_by_candidate_cleanup = 0
                    and s.decision_refs_checked = s.decision_refs_preserved_after
                )
        )
        from summary s
    ),

    'series_summary',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.series_id),
            '[]'::jsonb
        )
        from series_summary x
    ),

    'candidate_age_distribution',
    (
        select jsonb_build_object(
            'total_candidates', count(*),
            'fetched_older_than_7d', count(*) filter (
                where fetched_at < now() - interval '7 days'
            ),
            'fetched_older_than_30d', count(*) filter (
                where fetched_at < now() - interval '30 days'
            ),
            'observation_older_than_1y', count(*) filter (
                where observation_date < current_date - interval '1 year'
            ),
            'observation_older_than_3y', count(*) filter (
                where observation_date < current_date - interval '3 years'
            ),
            'observation_older_than_5y', count(*) filter (
                where observation_date < current_date - interval '5 years'
            ),
            'observation_older_than_10y', count(*) filter (
                where observation_date < current_date - interval '10 years'
            )
        )
        from candidates
    ),

    'revision_transition_summary',
    (
        select jsonb_build_object(
            'revision_groups', count(*),
            'version_rows', coalesce(sum(total_rows), 0),
            'retained_transition_rows', coalesce(sum(retained_rows), 0),
            'candidate_delete_rows_inside_revision_groups', coalesce(sum(candidate_delete_rows), 0),
            'groups_with_value_reversion', count(*) filter (where contains_value_reversion),
            'max_versions_in_group', coalesce(max(total_rows), 0),
            'max_retained_transitions_in_group', coalesce(max(retained_rows), 0)
        )
        from revision_transition_stats
    ),

    'revision_groups_with_value_reversion_examples',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select
                series_id,
                observation_date,
                total_rows,
                distinct_value_count,
                retained_rows,
                candidate_delete_rows,
                first_realtime_start,
                last_realtime_start
            from revision_transition_stats
            where contains_value_reversion
            order by retained_rows desc, observation_date desc, series_id
            limit 30
        ) x
    ),

    'top_candidate_groups',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select
                series_id,
                observation_date,
                total_rows,
                distinct_value_count,
                retained_rows,
                candidate_delete_rows,
                first_realtime_start,
                last_realtime_start
            from group_stats
            where candidate_delete_rows > 0
            order by candidate_delete_rows desc, observation_date desc, series_id
            limit 50
        ) x
    ),

    'decision_ref_loss_examples',
    (
        select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb)
        from (
            select
                decision_id,
                system,
                as_of,
                series_id,
                observation_date,
                persisted_value,
                exists_before,
                exists_after
            from decision_preservation
            where exists_before and not exists_after
            order by decision_id, series_id
            limit 50
        ) x
    ),

    'series_latest_parity',
    (
        select coalesce(
            jsonb_agg(to_jsonb(x) order by x.series_id),
            '[]'::jsonb
        )
        from series_latest_parity x
    )
) as macro_observations_p2_3_safe_dedup_dry_run;
