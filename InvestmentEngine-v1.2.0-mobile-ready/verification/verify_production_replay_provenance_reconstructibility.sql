-- Post-Shadow P1 — production/replay provenance reconstructibility
-- READ-ONLY diagnostic. No table, signal state, model parameter or snapshot is changed.
--
-- Amaç:
--   1) model.decisions içindeki audit payload'ından hangi factor girdilerinin yeniden
--      hesaplanabilir olduğunu ölçmek,
--   2) market as_of ile gerçek evaluation-time source provenance arasındaki boşlukları
--      sistem bazında nicelleştirmek,
--   3) özellikle URA breadth/event ve ETH/BTC derivatives provenance kapsamını ayırmak,
--   4) full production-vs-replay parity için hangi veri saklama boşluklarının kaldığını
--      kanıtla sınıflandırmak.
--
-- Scope: model_version = 1.2.0 only.

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
        d.action_event,
        d.action_stage,
        d.factors,
        d.rationale,
        d.rationale -> 'provenance' as provenance,
        d.rationale -> 'signal_state' as signal_state
    from model.decisions d
    where d.model_version = '1.2.0'
),
flags as (
    select
        b.*,

        -- Decision/evaluation identity.
        (b.provenance ->> 'decision_evaluated_at') is not null
            as has_decision_evaluated_at,
        jsonb_typeof(b.signal_state) = 'object'
            and b.signal_state <> '{}'::jsonb
            as has_embedded_signal_state,

        -- Technical factor details needed to recompute the persisted factor score.
        coalesce((b.factors -> 'value' -> 'details') ?& array['percentile','zscore'], false)
            as value_inputs_complete,
        coalesce((b.factors -> 'trend' -> 'details') ?& array['ema_gap_pct','slope_5d_pct'], false)
            as trend_inputs_complete,
        coalesce((b.factors -> 'momentum' -> 'details') ?& array['rsi','macd_hist'], false)
            as momentum_inputs_complete,
        coalesce((b.factors -> 'volatility' -> 'details') ?& array['rv20','rv60','ratio'], false)
            as volatility_inputs_complete,

        -- Macro factor stores values + observation dates inside factor details.
        jsonb_typeof(b.factors #> '{macro,details,latest}') = 'object'
            and coalesce(b.factors #> '{macro,details,latest}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_values,
        jsonb_typeof(b.factors #> '{macro,details,observation_dates}') = 'object'
            and coalesce(b.factors #> '{macro,details,observation_dates}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_observation_dates,
        jsonb_typeof(b.factors #> '{macro,details,freshness_quality}') = 'object'
            and coalesce(b.factors #> '{macro,details,freshness_quality}', '{}'::jsonb) <> '{}'::jsonb
            as has_macro_freshness_quality,

        -- ETH/BTC flow + derivatives scoring inputs.
        coalesce((b.factors -> 'flow' -> 'details') ? 'relative_rvol_eth_btc', false)
            as has_crypto_flow_input,
        coalesce((b.factors -> 'derivatives' -> 'details') ?&
            array['provider','funding_diff_bps','basis_diff_pct','btc_oi_usd','eth_oi_usd','oi_usd_ratio'], false)
            as has_derivatives_scoring_inputs,
        (b.provenance #>> '{derivatives_observed_at,btc}') is not null
            and (b.provenance #>> '{derivatives_observed_at,eth}') is not null
            as has_derivatives_observed_pair,

        -- URA fundamentals audit payload. Only require directional fields when
        -- the factor itself had positive quality; q0/missing is classified separately.
        case
            when b.system <> 'URA/USD' then null
            when coalesce((b.factors #>> '{fundamentals,quality}')::numeric, 0) <= 0 then null
            else coalesce((b.factors -> 'fundamentals' -> 'details') ?&
                array['current_date','previous_date','flow_proxy_pct','days_between','weight_coverage'], false)
        end as ura_fundamentals_directional_inputs_complete,

        -- The current score_ura_breadth implementation consumes these numeric
        -- components, but its returned details historically contain metadata rather
        -- than these values. Measure rather than assume their presence.
        case
            when b.system <> 'URA/USD' then null
            when coalesce((b.factors #>> '{breadth,quality}')::numeric, 0) <= 0 then null
            else coalesce((b.factors -> 'breadth' -> 'details') ?&
                array['pct_above_20dma','pct_above_50dma','pct_above_200dma','pct_positive_day','new_20d_high_pct'], false)
        end as ura_breadth_numeric_inputs_complete,

        -- Exact event-set provenance would need identities/timestamps (or an
        -- equivalent persisted snapshot reference), not only counts.
        case
            when b.system <> 'URA/USD' then null
            else (
                jsonb_typeof(b.factors #> '{event,details,events}') = 'array'
                or jsonb_typeof(b.factors #> '{event,details,event_ids}') = 'array'
                or jsonb_typeof(b.factors #> '{event,details,event_refs}') = 'array'
            )
        end as ura_event_set_identity_present,

        -- Source fetch/evaluation timestamps for URA sub-sources. Holding date /
        -- breadth date are market/source dates, not fetch-time identities.
        case
            when b.system <> 'URA/USD' then null
            else (
                (b.factors #>> '{fundamentals,details,fetched_at}') is not null
                or (b.factors #>> '{fundamentals,details,snapshot_fetched_at}') is not null
            )
        end as ura_holdings_fetch_time_present,
        case
            when b.system <> 'URA/USD' then null
            else (
                (b.factors #>> '{breadth,details,created_at}') is not null
                or (b.factors #>> '{breadth,details,calculated_at}') is not null
            )
        end as ura_breadth_compute_time_present,
        case
            when b.system <> 'URA/USD' then null
            else (
                (b.factors #>> '{event,details,checked_at}') is not null
                or (b.factors #>> '{event,details,health_checked_at}') is not null
            )
        end as ura_event_health_time_present
    from base b
),
system_summary as (
    select
        system,
        count(*)::int as decision_rows,
        count(*) filter (where has_decision_evaluated_at)::int as rows_with_decision_evaluated_at,
        count(*) filter (where has_embedded_signal_state)::int as rows_with_embedded_signal_state,
        count(*) filter (
            where value_inputs_complete
              and trend_inputs_complete
              and momentum_inputs_complete
              and volatility_inputs_complete
        )::int as rows_with_core_technical_factor_inputs,
        count(*) filter (where has_macro_values)::int as rows_with_macro_values,
        count(*) filter (where has_macro_observation_dates)::int as rows_with_macro_observation_dates,
        count(*) filter (where has_macro_freshness_quality)::int as rows_with_macro_freshness_quality,
        count(*) filter (where has_crypto_flow_input)::int as rows_with_crypto_flow_input,
        count(*) filter (where has_derivatives_scoring_inputs)::int as rows_with_derivatives_scoring_inputs,
        count(*) filter (where has_derivatives_observed_pair)::int as rows_with_derivatives_observed_pair,
        count(*) filter (where ura_fundamentals_directional_inputs_complete is not null)::int
            as ura_rows_with_directional_fundamentals_quality,
        count(*) filter (where ura_fundamentals_directional_inputs_complete is true)::int
            as ura_rows_with_directional_fundamentals_inputs,
        count(*) filter (where ura_breadth_numeric_inputs_complete is not null)::int
            as ura_rows_with_positive_breadth_quality,
        count(*) filter (where ura_breadth_numeric_inputs_complete is true)::int
            as ura_rows_with_breadth_numeric_inputs,
        count(*) filter (where ura_event_set_identity_present is true)::int
            as ura_rows_with_event_set_identity,
        count(*) filter (where ura_holdings_fetch_time_present is true)::int
            as ura_rows_with_holdings_fetch_time,
        count(*) filter (where ura_breadth_compute_time_present is true)::int
            as ura_rows_with_breadth_compute_time,
        count(*) filter (where ura_event_health_time_present is true)::int
            as ura_rows_with_event_health_time
    from flags
    group by system
),
repeated_keys as (
    select system, as_of
    from base
    group by system, as_of
    having count(*) > 1
),
repeated_collision_summary as (
    select
        b.system,
        count(*)::int as repeated_decision_rows,
        count(distinct b.as_of)::int as repeated_market_dates,
        count(*) filter (
            where exists (
                select 1
                from base x
                where x.system = b.system
                  and x.as_of = b.as_of
                  and x.id <> b.id
                  and x.factors is distinct from b.factors
            )
        )::int as repeated_rows_with_factor_payload_peer_difference,
        count(*) filter (
            where exists (
                select 1
                from base x
                where x.system = b.system
                  and x.as_of = b.as_of
                  and x.id <> b.id
                  and x.regime_code is distinct from b.regime_code
            )
        )::int as repeated_rows_with_regime_peer_difference
    from base b
    join repeated_keys k using (system, as_of)
    group by b.system
),
ura_gap_examples as (
    select
        id,
        as_of,
        created_at,
        direction,
        status,
        edge_score,
        confidence,
        data_quality,
        (factors #>> '{fundamentals,quality}')::numeric as fundamentals_quality,
        ura_fundamentals_directional_inputs_complete,
        (factors #>> '{breadth,quality}')::numeric as breadth_quality,
        ura_breadth_numeric_inputs_complete,
        (factors #>> '{event,quality}')::numeric as event_quality,
        ura_event_set_identity_present,
        ura_holdings_fetch_time_present,
        ura_breadth_compute_time_present,
        ura_event_health_time_present
    from flags
    where system = 'URA/USD'
      and (
          ura_breadth_numeric_inputs_complete is false
          or ura_event_set_identity_present is false
          or ura_holdings_fetch_time_present is false
          or ura_breadth_compute_time_present is false
          or ura_event_health_time_present is false
      )
    order by created_at desc, id desc
    limit 20
)
select jsonb_build_object(
    'generated_at', now(),
    'scope', jsonb_build_object(
        'model_version', '1.2.0',
        'read_only', true,
        'purpose', 'Measure whether persisted production decisions contain enough evaluation-time provenance to reconstruct factor inputs and source snapshots.'
    ),
    'system_summary', coalesce((
        select jsonb_agg(to_jsonb(s) order by s.system)
        from system_summary s
    ), '[]'::jsonb),
    'repeated_collision_summary', coalesce((
        select jsonb_agg(to_jsonb(r) order by r.system)
        from repeated_collision_summary r
    ), '[]'::jsonb),
    'ura_gap_examples', coalesce((
        select jsonb_agg(to_jsonb(u) order by u.created_at desc, u.id desc)
        from ura_gap_examples u
    ), '[]'::jsonb),
    'interpretation', jsonb_build_object(
        'decision_audit_vs_source_replay',
            'Persisted factor score/quality/output can be audited even when the exact raw source snapshot cannot be recreated. Do not treat these as the same guarantee.',
        'macro',
            'Macro factor details persist values, observation dates and freshness qualities; top-level provenance alone understates macro auditability.',
        'derivatives',
            'ETH/BTC needs both scoring inputs and BTC/ETH observed_at timestamps for evaluation-time source reconstruction.',
        'ura_fundamentals',
            'Directional fundamentals details can preserve calculation inputs, but holding/source fetch-time identity is measured separately.',
        'ura_breadth',
            'Exact breadth factor recomputation requires the numeric breadth components used by score_ura_breadth; metadata-only details are insufficient.',
        'ura_event',
            'Event counts/quality alone do not identify the exact event set seen by a production evaluation.',
        'next_decision_rule',
            'Do not implement a broad production-parity replay until these coverage results separate reproducible inputs from source-history gaps.'
    )
) as production_replay_provenance_reconstructibility;
