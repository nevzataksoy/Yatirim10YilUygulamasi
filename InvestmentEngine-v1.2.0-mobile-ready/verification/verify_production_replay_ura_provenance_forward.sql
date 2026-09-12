-- Post-Shadow P1 — URA provenance hardening forward verification
-- READ-ONLY. No table, decision, state, snapshot or model parameter is changed.
--
-- Purpose:
--   Verify that a NEW production URA/USD decision produced by the hardened
--   runtime carries enough evaluation-time audit metadata for breadth/event
--   reconstruction while keeping the released model contract unchanged.
--
-- Run this only AFTER the hardened build has been deployed and at least one
-- fresh URA/USD decision has been persisted by that runtime.

with latest as (
    select
        d.id,
        d.created_at,
        d.as_of,
        d.system,
        d.model_version,
        d.direction,
        d.regime_code,
        d.edge_score,
        d.confidence,
        d.data_quality,
        d.status,
        d.action_event,
        d.action_stage,
        d.action_size,
        d.regime_cumulative_size,
        d.factors,
        d.rationale,
        d.rationale -> 'provenance' as provenance,
        d.rationale -> 'signal_state' as signal_state
    from model.decisions d
    where d.system = 'URA/USD'
      and d.model_version = '1.2.0'
    order by d.created_at desc, d.id desc
    limit 1
),
flags as (
    select
        l.*,
        (l.provenance ->> 'decision_evaluated_at') is not null
            as has_decision_evaluated_at,
        jsonb_typeof(l.signal_state) = 'object'
            and l.signal_state <> '{}'::jsonb
            as has_embedded_signal_state,

        coalesce((l.factors -> 'breadth' -> 'details') ?& array[
            'pct_above_20dma',
            'pct_above_50dma',
            'pct_above_200dma',
            'pct_positive_day',
            'new_20d_high_pct'
        ], false) as has_breadth_numeric_keys,
        (l.factors #>> '{breadth,details,created_at}') is not null
            as has_breadth_created_at,
        (l.factors #>> '{breadth,details,breadth_date}') is not null
            as has_breadth_date,

        jsonb_typeof(l.factors #> '{event,details,event_refs}') = 'array'
            as has_event_refs_array,
        (l.factors #>> '{event,details,health_checked_at}') is not null
            as has_event_health_checked_at,
        (l.factors #>> '{event,details,health_status}') is not null
            as has_event_health_status,
        (l.factors #>> '{event,details,recent_events}') is not null
            as has_event_count,

        case
            when coalesce((l.factors #>> '{fundamentals,quality}')::numeric, 0) <= 0
                then null
            else coalesce((l.factors -> 'fundamentals' -> 'details') ?& array[
                'current_date',
                'previous_date',
                'flow_proxy_pct',
                'days_between',
                'weight_coverage'
            ], false)
        end as fundamentals_directional_inputs_complete,

        jsonb_typeof(l.factors #> '{macro,details,latest}') = 'object'
            and coalesce(l.factors #> '{macro,details,latest}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_values,
        jsonb_typeof(l.factors #> '{macro,details,observation_dates}') = 'object'
            and coalesce(l.factors #> '{macro,details,observation_dates}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_observation_dates,
        jsonb_typeof(l.factors #> '{macro,details,freshness_quality}') = 'object'
            and coalesce(l.factors #> '{macro,details,freshness_quality}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_freshness_quality
    from latest l
),
result as (
    select
        f.*,
        (
            f.has_decision_evaluated_at
            and f.has_embedded_signal_state
            and f.has_breadth_numeric_keys
            and f.has_breadth_created_at
            and f.has_breadth_date
            and f.has_event_refs_array
            and f.has_event_health_checked_at
            and f.has_event_health_status
            and f.has_event_count
            and f.has_macro_values
            and f.has_macro_observation_dates
            and f.has_macro_freshness_quality
            and coalesce(f.fundamentals_directional_inputs_complete, true)
        ) as hardened_audit_payload_complete
    from flags f
)
select jsonb_build_object(
    'generated_at', now(),
    'scope', jsonb_build_object(
        'read_only', true,
        'system', 'URA/USD',
        'model_version', '1.2.0',
        'purpose', 'Forward verification of URA breadth/event provenance hardening after runtime deployment.'
    ),
    'latest_decision', coalesce((
        select jsonb_build_object(
            'id', r.id,
            'created_at', r.created_at,
            'as_of', r.as_of,
            'direction', r.direction,
            'regime_code', r.regime_code,
            'edge_score', r.edge_score,
            'confidence', r.confidence,
            'data_quality', r.data_quality,
            'status', r.status,
            'action_event', r.action_event,
            'action_stage', r.action_stage,
            'action_size', r.action_size,
            'regime_cumulative_size', r.regime_cumulative_size,
            'decision_evaluated_at', r.provenance ->> 'decision_evaluated_at',
            'breadth_quality', (r.factors #>> '{breadth,quality}')::numeric,
            'breadth_details', r.factors #> '{breadth,details}',
            'event_quality', (r.factors #>> '{event,quality}')::numeric,
            'event_details', r.factors #> '{event,details}',
            'fundamentals_quality', (r.factors #>> '{fundamentals,quality}')::numeric,
            'fundamentals_details', r.factors #> '{fundamentals,details}',
            'signal_state', r.signal_state
        )
        from result r
    ), '{}'::jsonb),
    'checks', coalesce((
        select jsonb_build_object(
            'has_decision_evaluated_at', r.has_decision_evaluated_at,
            'has_embedded_signal_state', r.has_embedded_signal_state,
            'has_breadth_numeric_keys', r.has_breadth_numeric_keys,
            'has_breadth_created_at', r.has_breadth_created_at,
            'has_breadth_date', r.has_breadth_date,
            'has_event_refs_array', r.has_event_refs_array,
            'has_event_health_checked_at', r.has_event_health_checked_at,
            'has_event_health_status', r.has_event_health_status,
            'has_event_count', r.has_event_count,
            'fundamentals_directional_inputs_complete', r.fundamentals_directional_inputs_complete,
            'has_macro_values', r.has_macro_values,
            'has_macro_observation_dates', r.has_macro_observation_dates,
            'has_macro_freshness_quality', r.has_macro_freshness_quality,
            'hardened_audit_payload_complete', r.hardened_audit_payload_complete
        )
        from result r
    ), '{}'::jsonb),
    'interpretation', jsonb_build_object(
        'pass_condition',
            'hardened_audit_payload_complete=true on a decision created by the deployed hardened runtime.',
        'event_refs',
            'An empty event_refs array is valid when the evaluated 168-hour window contained no events; the array itself identifies the exact evaluated set.',
        'breadth_null_values',
            'Some numeric breadth values may legitimately be null when history has not matured. Presence of all keys plus created_at/breadth_date is the audit requirement.',
        'holdings_limit',
            'This does not make raw Global X holdings snapshots versioned. Historical raw holdings fetch identity remains a separate data-lifecycle limitation.',
        'model_contract',
            'This verification does not justify threshold, weights, K1/K2, sizing, SHADOW/LIVE or model-version changes.'
    )
) as production_replay_ura_provenance_forward;
