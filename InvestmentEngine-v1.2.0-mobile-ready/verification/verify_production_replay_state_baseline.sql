-- Post-Shadow P1 — production vs replay / signal-state baseline
-- READ-ONLY diagnostic. No table, model setting, signal state or snapshot is changed.
--
-- Sorun:
--   Historical directional replay produces one market-day point, while production
--   applies persistent signal state every time a decision row is persisted.
--   Re-running the same market as_of may therefore matter even when the market
--   candle has not changed.
--
-- Amaç:
--   1) quantify repeated decisions for the same system + market as_of,
--   2) see whether edge/factor/state results changed across those repeats,
--   3) detect same-as_of reset/stage/cumulative state movement,
--   4) inventory ACTION/action_event evidence,
--   5) verify whether decision rows contain enough post-state/provenance history
--      for the next production-vs-replay parity step.
--
-- Scope:
--   model_version = 1.2.0 only.
--   This query does NOT claim a parity failure by itself; it only measures the
--   stored production history needed to design the replay comparison safely.
--
-- Run in Supabase SQL Editor and return the single JSON result row.

with base as (
    select
        d.id,
        d.created_at,
        d.as_of,
        d.system,
        d.direction,
        d.regime_code,
        d.edge_score,
        d.confidence,
        d.data_quality,
        d.status,
        d.late_entry,
        d.event_veto,
        d.execution_required,
        d.action_event,
        d.action_stage,
        d.action_size,
        d.regime_cumulative_size,
        d.factors,
        d.rationale,
        d.rationale -> 'signal_state' as signal_state,
        d.rationale -> 'provenance' as provenance,
        nullif(d.rationale #>> '{signal_state,active_direction}', '') as state_active_direction,
        nullif(d.rationale #>> '{signal_state,stage}', '')::int as state_stage,
        nullif(d.rationale #>> '{signal_state,cumulative_size}', '')::numeric as state_cumulative_size,
        nullif(d.rationale #>> '{signal_state,last_action_date}', '')::date as state_last_action_date,
        nullif(d.rationale #>> '{signal_state,reset_counter}', '')::int as state_reset_counter
    from model.decisions d
    where d.model_version = '1.2.0'
),
ordered as (
    select
        b.*,
        lag(b.id) over w as prev_id,
        lag(b.created_at) over w as prev_created_at,
        lag(b.as_of) over w as prev_as_of,
        lag(b.status) over w as prev_status,
        lag(b.direction) over w as prev_direction,
        lag(b.regime_code) over w as prev_regime_code,
        lag(b.edge_score) over w as prev_edge_score,
        lag(b.state_active_direction) over w as prev_state_active_direction,
        lag(b.state_stage) over w as prev_state_stage,
        lag(b.state_cumulative_size) over w as prev_state_cumulative_size,
        lag(b.state_last_action_date) over w as prev_state_last_action_date,
        lag(b.state_reset_counter) over w as prev_state_reset_counter
    from base b
    window w as (partition by b.system order by b.created_at, b.id)
),
per_day as (
    select
        system,
        as_of,
        count(*)::int as decision_rows,
        min(created_at) as first_created_at,
        max(created_at) as last_created_at,
        count(distinct edge_score)::int as distinct_edges,
        count(distinct confidence)::int as distinct_confidences,
        count(distinct data_quality)::int as distinct_data_qualities,
        count(distinct regime_code)::int as distinct_regimes,
        count(distinct direction)::int as distinct_directions,
        count(distinct status)::int as distinct_statuses,
        count(distinct factors::text)::int as distinct_factor_payloads,
        count(*) filter (where action_event)::int as action_events,
        count(distinct action_stage)::int as distinct_action_stages,
        count(distinct regime_cumulative_size)::int as distinct_cumulative_sizes,
        array_agg(distinct status order by status) as statuses,
        array_agg(distinct direction order by direction) as directions,
        array_agg(distinct regime_code order by regime_code) as regimes
    from base
    group by system, as_of
),
system_summary as (
    select
        b.system,
        count(*)::int as decision_rows,
        count(distinct b.as_of)::int as market_dates,
        min(b.as_of) as first_market_date,
        max(b.as_of) as last_market_date,
        min(b.created_at) as first_created_at,
        max(b.created_at) as last_created_at,
        count(*) filter (where b.signal_state is null)::int as rows_missing_signal_state,
        count(*) filter (where b.provenance is null)::int as rows_missing_provenance,
        count(*) filter (where b.action_event)::int as action_event_rows,
        count(*) filter (where b.status = 'ACTION')::int as action_status_rows,
        count(*) filter (where b.status = 'WATCH')::int as watch_rows,
        count(*) filter (where b.status = 'WAIT')::int as wait_rows,
        count(*) filter (where b.status = 'NO_ACTION_DATA')::int as no_action_data_rows,
        coalesce((
            select count(*)::int
            from per_day p
            where p.system = b.system and p.decision_rows > 1
        ), 0) as repeated_market_dates,
        coalesce((
            select max(p.decision_rows)::int
            from per_day p
            where p.system = b.system
        ), 0) as max_decisions_on_one_market_date
    from base b
    group by b.system
),
repeated_days as (
    select *
    from per_day
    where decision_rows > 1
    order by as_of desc, system
),
same_asof_state_moves as (
    select
        system,
        as_of,
        prev_id,
        id,
        prev_created_at,
        created_at,
        prev_status,
        status,
        prev_direction,
        direction,
        prev_regime_code,
        regime_code,
        prev_edge_score,
        edge_score,
        prev_state_active_direction,
        state_active_direction,
        prev_state_stage,
        state_stage,
        prev_state_cumulative_size,
        state_cumulative_size,
        prev_state_last_action_date,
        state_last_action_date,
        prev_state_reset_counter,
        state_reset_counter,
        action_event,
        action_stage,
        action_size
    from ordered
    where prev_as_of = as_of
      and (
          state_active_direction is distinct from prev_state_active_direction
          or state_stage is distinct from prev_state_stage
          or state_cumulative_size is distinct from prev_state_cumulative_size
          or state_last_action_date is distinct from prev_state_last_action_date
          or state_reset_counter is distinct from prev_state_reset_counter
      )
    order by created_at, id
),
same_asof_reset_advances as (
    select *
    from same_asof_state_moves
    where state_reset_counter > coalesce(prev_state_reset_counter, -1)
    order by created_at, id
),
same_asof_multiple_action_events as (
    select
        system,
        as_of,
        count(*) filter (where action_event)::int as action_events,
        array_agg(id order by created_at, id) filter (where action_event) as decision_ids
    from base
    group by system, as_of
    having count(*) filter (where action_event) > 1
),
first_last_state as (
    select
        s.system,
        (
            select jsonb_build_object(
                'id', x.id,
                'as_of', x.as_of,
                'created_at', x.created_at,
                'status', x.status,
                'action_event', x.action_event,
                'signal_state', x.signal_state
            )
            from base x
            where x.system = s.system
            order by x.created_at, x.id
            limit 1
        ) as first_decision,
        (
            select jsonb_build_object(
                'id', x.id,
                'as_of', x.as_of,
                'created_at', x.created_at,
                'status', x.status,
                'action_event', x.action_event,
                'signal_state', x.signal_state
            )
            from base x
            where x.system = s.system
            order by x.created_at desc, x.id desc
            limit 1
        ) as last_decision
    from (select distinct system from base) s
),
current_state as (
    select
        system,
        active_direction,
        stage,
        cumulative_size,
        last_action_date,
        reset_counter,
        updated_at
    from model.signal_state
),
provenance_summary as (
    select
        system,
        count(*)::int as decision_rows,
        count(*) filter (
            where rationale #>> '{provenance,decision_evaluated_at}' is not null
        )::int as rows_with_decision_evaluated_at,
        count(*) filter (
            where rationale #> '{provenance,macro_observation_dates}' is not null
        )::int as rows_with_macro_observation_dates,
        count(*) filter (
            where rationale #> '{provenance,derivatives_observed_at}' is not null
        )::int as rows_with_derivatives_observed_at,
        count(distinct as_of)::int as market_dates
    from base
    group by system
)
select jsonb_build_object(
    'generated_at', now(),
    'scope', jsonb_build_object(
        'model_version', '1.2.0',
        'read_only', true,
        'purpose', 'Production-vs-replay signal-state baseline; no model behavior is changed.'
    ),
    'system_summary', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.system)
        from system_summary x
    ), '[]'::jsonb),
    'repeated_market_dates', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.as_of desc, x.system)
        from (select * from repeated_days limit 100) x
    ), '[]'::jsonb),
    'same_asof_state_moves', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.created_at, x.id)
        from (select * from same_asof_state_moves limit 100) x
    ), '[]'::jsonb),
    'same_asof_reset_advances', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.created_at, x.id)
        from (select * from same_asof_reset_advances limit 100) x
    ), '[]'::jsonb),
    'same_asof_multiple_action_events', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.as_of, x.system)
        from same_asof_multiple_action_events x
    ), '[]'::jsonb),
    'first_last_decision_state', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.system)
        from first_last_state x
    ), '[]'::jsonb),
    'current_signal_state', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.system)
        from current_state x
    ), '[]'::jsonb),
    'provenance_summary', coalesce((
        select jsonb_agg(to_jsonb(x) order by x.system)
        from provenance_summary x
    ), '[]'::jsonb),
    'interpretation_hints', jsonb_build_object(
        'repeated_market_dates',
            'The production decisions table permits multiple rows for one market as_of. Repeats are not automatically independent market days.',
        'same_asof_state_moves',
            'Any row here proves persistent signal state changed between two consecutive decisions sharing the same market as_of; the cause must then be classified.',
        'same_asof_reset_advances',
            'Rows here are especially important because reset_days is intended as a market-day/state rule, while repeated processing of one as_of could otherwise advance the counter more than once.',
        'multiple_action_events',
            'More than one action_event on one system+as_of would require immediate RCA; ACTION status alone is not an action_event.',
        'provenance',
            'High coverage is required before production inputs can be compared fairly with replay inputs.'
    )
) as production_replay_state_baseline;
