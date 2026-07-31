from __future__ import annotations

from typing import Any

from app.models import AppSettings, Decision


def apply_signal_state(
    decision: Decision,
    raw_state: dict[str, Any] | None,
    settings: AppSettings,
) -> dict[str, Any]:
    """Apply persistent two-stage hysteresis to a daily decision.

    Direction/edge may remain ACTION for several closes. ``action_event`` is only
    true when a new executable tranche is created. This prevents repeated daily
    Telegram alerts and execution workers for the same active regime.
    """
    raw = raw_state or {}
    active = raw.get("active_direction")
    stage = int(raw.get("stage") or 0)
    cumulative = float(raw.get("cumulative_size") or 0)
    last_action = str(raw.get("last_action_date") or "") or None
    reset_counter = int(raw.get("reset_counter") or 0)

    if active:
        same_direction = decision.direction == active
        if same_direction and decision.edge_score >= settings.regime_reset_edge:
            reset_counter = 0
        elif decision.status != "ACTION":
            reset_counter += 1
        else:
            reset_counter = 0

        if reset_counter >= settings.regime_reset_days:
            active = None
            stage = 0
            cumulative = 0.0
            last_action = None
            reset_counter = 0

    action_event = False
    action_stage = stage
    action_size = 0.0

    if decision.status == "ACTION":
        # A qualified opposite direction starts a new regime immediately.
        if active != decision.direction:
            active = decision.direction
            stage = 0
            cumulative = 0.0
            last_action = None
            reset_counter = 0

        remaining = max(0.0, settings.max_regime_pct - cumulative)
        if stage == 0 and remaining > 0:
            action_event = True
            action_stage = 1
            action_size = min(
                decision.recommended_size,
                settings.base_tranche_pct,
                remaining,
            )
        elif (
            stage == 1
            and remaining > 0
            and decision.as_of != last_action
            and decision.edge_score >= settings.strong_action_edge
            and decision.confidence >= settings.strong_action_confidence
        ):
            action_event = True
            action_stage = 2
            action_size = min(
                decision.recommended_size,
                settings.base_tranche_pct,
                remaining,
            )

        if action_event and action_size > 0:
            stage = action_stage
            cumulative = min(settings.max_regime_pct, cumulative + action_size)
            last_action = decision.as_of
        else:
            action_event = False
            action_size = 0.0

    decision.action_event = action_event
    decision.action_stage = stage
    decision.action_size = round(action_size, 4)
    decision.regime_cumulative_size = round(cumulative, 4)
    decision.execution_required = bool(decision.execution_required and action_event)
    decision.rationale["signal_state"] = {
        "active_direction": active,
        "stage": stage,
        "cumulative_size": cumulative,
        "last_action_date": last_action,
        "reset_counter": reset_counter,
        "new_action": action_event,
    }

    return {
        "active_direction": active,
        "stage": stage,
        "cumulative_size": cumulative,
        "last_action_date": last_action,
        "reset_counter": reset_counter,
    }
