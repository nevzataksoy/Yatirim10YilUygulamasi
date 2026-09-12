from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.database.db import DatabaseService
from app.models import Decision
from app.version import MODEL_VERSION

SignalStateApplier = Callable[[dict[str, Any] | None], dict[str, Any]]


def persist_decision_outcome(
    db: DatabaseService,
    decision: Decision,
    provider: str,
    apply_state: SignalStateApplier,
) -> int:
    """Persist signal state and the published decision as one DB transaction.

    The state row is locked before the state machine is applied so concurrent
    evaluations of the same system cannot both advance from the same stale
    persistent state.  External side effects (Telegram/execution workers) must
    run only after this function returns successfully.
    """
    factors_json = {
        code: {"score": factor.score, "quality": factor.quality, "details": factor.details}
        for code, factor in decision.factors.items()
    }
    public_factors = {
        code: {"score": factor.score, "quality": factor.quality}
        for code, factor in decision.factors.items()
    }

    with db.connection() as conn:
        with conn.cursor() as cur:
            # Ensure a row exists even for a system's first persisted decision.
            # ON CONFLICT also participates in PostgreSQL's unique-key locking,
            # after which FOR UPDATE serializes the state transition itself.
            cur.execute(
                """
                insert into model.signal_state(system)
                values (%s)
                on conflict(system) do nothing
                """,
                (decision.system,),
            )
            cur.execute(
                "select * from model.signal_state where system=%s for update",
                (decision.system,),
            )
            raw_state = cur.fetchone()
            if raw_state is None:
                raise RuntimeError(f"signal_state satırı kilitlenemedi: {decision.system}")

            state = apply_state(raw_state)
            cur.execute(
                """
                update model.signal_state
                set active_direction=%s,
                    stage=%s,
                    cumulative_size=%s,
                    last_action_date=%s,
                    reset_counter=%s,
                    updated_at=now()
                where system=%s
                """,
                (
                    state["active_direction"],
                    state["stage"],
                    state["cumulative_size"],
                    state["last_action_date"],
                    state["reset_counter"],
                    decision.system,
                ),
            )

            cur.execute(
                """
                insert into model.decisions
                  (as_of, system, direction, regime_code, edge_score, confidence, uncertainty,
                   data_quality, risk_score, recommended_size, late_entry, event_veto,
                   status, execution_required, action_event, action_stage, action_size, regime_cumulative_size,
                   model_version, factors, rationale)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                returning id
                """,
                (
                    decision.as_of,
                    decision.system,
                    decision.direction,
                    decision.regime,
                    decision.edge_score,
                    decision.confidence,
                    decision.uncertainty,
                    decision.data_quality,
                    decision.risk_score,
                    decision.recommended_size,
                    decision.late_entry,
                    decision.event_veto,
                    decision.status,
                    decision.execution_required,
                    decision.action_event,
                    decision.action_stage,
                    decision.action_size,
                    decision.regime_cumulative_size,
                    MODEL_VERSION,
                    json.dumps(factors_json),
                    json.dumps(decision.rationale),
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Decision insert id döndürmedi.")
            decision_id = int(row["id"])

            cur.execute(
                """
                insert into public.decision_history
                  (decision_id, generated_at, as_of, system, direction, status, regime_code,
                   edge_score, confidence, uncertainty, data_quality, risk_score, recommended_size,
                   late_entry, event_veto, execution_required, action_event, action_stage, action_size,
                   regime_cumulative_size, provider, model_version, factors, rationale)
                values (%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(decision_id) do nothing
                """,
                (
                    decision_id,
                    decision.as_of,
                    decision.system,
                    decision.direction,
                    decision.status,
                    decision.regime,
                    decision.edge_score,
                    decision.confidence,
                    decision.uncertainty,
                    decision.data_quality,
                    decision.risk_score,
                    decision.recommended_size,
                    decision.late_entry,
                    decision.event_veto,
                    decision.execution_required,
                    decision.action_event,
                    decision.action_stage,
                    decision.action_size,
                    decision.regime_cumulative_size,
                    provider,
                    MODEL_VERSION,
                    json.dumps(public_factors),
                    json.dumps(decision.rationale),
                ),
            )

            cur.execute(
                """
                insert into public.decision_snapshot
                  (system, generated_at, as_of, direction, status, regime_code, edge_score,
                   confidence, uncertainty, data_quality, risk_score, recommended_size,
                   late_entry, event_veto, execution_required, action_event, action_stage, action_size,
                   regime_cumulative_size, provider, model_version, factors, rationale)
                values (%s,now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                on conflict(system) do update set
                  generated_at=now(), as_of=excluded.as_of, direction=excluded.direction,
                  status=excluded.status, regime_code=excluded.regime_code,
                  edge_score=excluded.edge_score, confidence=excluded.confidence,
                  uncertainty=excluded.uncertainty, data_quality=excluded.data_quality,
                  risk_score=excluded.risk_score, recommended_size=excluded.recommended_size,
                  late_entry=excluded.late_entry, event_veto=excluded.event_veto,
                  execution_required=excluded.execution_required, action_event=excluded.action_event,
                  action_stage=excluded.action_stage, action_size=excluded.action_size,
                  regime_cumulative_size=excluded.regime_cumulative_size, provider=excluded.provider,
                  model_version=excluded.model_version, factors=excluded.factors, rationale=excluded.rationale
                """,
                (
                    decision.system,
                    decision.as_of,
                    decision.direction,
                    decision.status,
                    decision.regime,
                    decision.edge_score,
                    decision.confidence,
                    decision.uncertainty,
                    decision.data_quality,
                    decision.risk_score,
                    decision.recommended_size,
                    decision.late_entry,
                    decision.event_veto,
                    decision.execution_required,
                    decision.action_event,
                    decision.action_stage,
                    decision.action_size,
                    decision.regime_cumulative_size,
                    provider,
                    MODEL_VERSION,
                    json.dumps(public_factors),
                    json.dumps(decision.rationale),
                ),
            )
        conn.commit()
        return decision_id
