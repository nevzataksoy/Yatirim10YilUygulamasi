-- Post-Shadow P1 — repeated market as_of production detail
-- READ-ONLY diagnostic. No table, model setting, signal state or snapshot is changed.
--
-- Amaç:
--   1) aynı system + market as_of için tekrar üretilen decision satırlarını zaman sırasıyla açmak,
--   2) tekrarlar arasında hangi factor payload'larının değiştiğini göstermek,
--   3) direction/edge/confidence/data_quality/status değişimini ayırmak,
--   4) provenance alanlarının yalnız mevcut olmasını değil, gerçek değerlerini de göstermek,
--   5) production-vs-replay parity için aynı market günündeki evaluation-time drift'i sınıflandırmak.
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
        d.rationale -> 'provenance' as provenance
    from model.decisions d
    where d.model_version = '1.2.0'
),
repeated_keys as (
    select system, as_of
    from base
    group by system, as_of
    having count(*) > 1
),
repeated as (
    select b.*
    from base b
    join repeated_keys k using (system, as_of)
),
ordered as (
    select
        r.*,
        lag(r.id) over w as prev_id,
        lag(r.created_at) over w as prev_created_at,
        lag(r.direction) over w as prev_direction,
        lag(r.regime_code) over w as prev_regime_code,
        lag(r.edge_score) over w as prev_edge_score,
        lag(r.confidence) over w as prev_confidence,
        lag(r.data_quality) over w as prev_data_quality,
        lag(r.status) over w as prev_status,
        lag(r.factors) over w as prev_factors,
        lag(r.signal_state) over w as prev_signal_state
    from repeated r
    window w as (
        partition by r.system, r.as_of
        order by r.created_at, r.id
    )
),
detail as (
    select
        o.system,
        o.as_of,
        o.id,
        o.created_at,
        o.prev_id,
        o.prev_created_at,
        o.direction,
        o.regime_code,
        o.edge_score,
        o.confidence,
        o.data_quality,
        o.status,
        o.late_entry,
        o.event_veto,
        o.execution_required,
        o.action_event,
        o.action_stage,
        o.action_size,
        o.regime_cumulative_size,
        o.signal_state,
        o.provenance ->> 'decision_evaluated_at' as decision_evaluated_at,
        o.provenance ->> 'price_provider' as price_provider,
        o.provenance -> 'macro_observation_dates' as macro_observation_dates,
        o.provenance -> 'derivatives_observed_at' as derivatives_observed_at,
        case when o.prev_id is null then null else o.direction is distinct from o.prev_direction end as direction_changed,
        case when o.prev_id is null then null else o.regime_code is distinct from o.prev_regime_code end as regime_changed,
        case when o.prev_id is null then null else o.edge_score is distinct from o.prev_edge_score end as edge_changed,
        case when o.prev_id is null then null else o.confidence is distinct from o.prev_confidence end as confidence_changed,
        case when o.prev_id is null then null else o.data_quality is distinct from o.prev_data_quality end as data_quality_changed,
        case when o.prev_id is null then null else o.status is distinct from o.prev_status end as status_changed,
        case when o.prev_id is null then null else o.signal_state is distinct from o.prev_signal_state end as signal_state_changed,
        case
            when o.prev_id is null then '[]'::jsonb
            else coalesce((
                select jsonb_agg(k.factor_code order by k.factor_code)
                from jsonb_object_keys(
                    coalesce(o.prev_factors, '{}'::jsonb) || coalesce(o.factors, '{}'::jsonb)
                ) as k(factor_code)
                where o.factors -> k.factor_code is distinct from o.prev_factors -> k.factor_code
            ), '[]'::jsonb)
        end as changed_factors,
        case
            when o.prev_id is null then '{}'::jsonb
            else coalesce((
                select jsonb_object_agg(
                    k.factor_code,
                    jsonb_build_object(
                        'previous', o.prev_factors -> k.factor_code,
                        'current', o.factors -> k.factor_code
                    )
                    order by k.factor_code
                )
                from jsonb_object_keys(
                    coalesce(o.prev_factors, '{}'::jsonb) || coalesce(o.factors, '{}'::jsonb)
                ) as k(factor_code)
                where o.factors -> k.factor_code is distinct from o.prev_factors -> k.factor_code
            ), '{}'::jsonb)
        end as changed_factor_payloads
    from ordered o
),
coverage as (
    select
        system,
        count(*)::int as repeated_decision_rows,
        count(distinct as_of)::int as repeated_market_dates,
        count(*) filter (
            where provenance ->> 'decision_evaluated_at' is not null
        )::int as rows_with_decision_evaluated_at,
        count(*) filter (
            where jsonb_typeof(provenance -> 'macro_observation_dates') = 'object'
              and provenance -> 'macro_observation_dates' <> '{}'::jsonb
        )::int as rows_with_nonempty_macro_observation_dates,
        count(*) filter (
            where provenance #>> '{derivatives_observed_at,btc}' is not null
              and provenance #>> '{derivatives_observed_at,eth}' is not null
        )::int as rows_with_nonnull_derivatives_pair
    from repeated
    group by system
)
select jsonb_build_object(
    'generated_at', now(),
    'scope', jsonb_build_object(
        'model_version', '1.2.0',
        'read_only', true,
        'purpose', 'Classify repeated market-as_of input/output drift before production-vs-replay parity decisions.'
    ),
    'coverage', coalesce((
        select jsonb_agg(to_jsonb(c) order by c.system)
        from coverage c
    ), '[]'::jsonb),
    'repeated_asof_detail', coalesce((
        select jsonb_agg(to_jsonb(d) order by d.system, d.as_of, d.created_at, d.id)
        from detail d
    ), '[]'::jsonb),
    'interpretation_hints', jsonb_build_object(
        'changed_factors',
            'A non-empty list means the persisted decision factor payload changed while market as_of stayed the same.',
        'signal_state_changed',
            'True would mean persistent post-state moved on a repeated market as_of; classify separately from decision-input drift.',
        'event_time_semantics',
            'URA event/veto runtime queries are evaluation-time windows; a repeated market as_of can therefore see different event inputs.',
        'derivatives_coverage',
            'The baseline only checked whether derivatives_observed_at existed. This query counts BTC+ETH timestamps only when both are actually non-null.'
    )
) as production_replay_repeated_asof_detail;
