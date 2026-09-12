from __future__ import annotations

from app.engines.signal_state import apply_signal_state
from app.models import AppSettings, Decision


def _settings() -> AppSettings:
    return AppSettings(
        regime_reset_edge=45.0,
        regime_reset_days=5,
        strong_action_edge=80.0,
        strong_action_confidence=80.0,
        base_tranche_pct=0.10,
        max_regime_pct=0.20,
    )


def _decision(
    as_of: str,
    *,
    direction: str = "USD→URA",
    status: str = "WAIT",
    edge: float = 30.0,
    confidence: float = 70.0,
) -> Decision:
    return Decision(
        system="URA/USD",
        as_of=as_of,
        direction=direction,
        regime="RISK_ON_TREND",
        edge_score=edge,
        confidence=confidence,
        uncertainty=30.0,
        data_quality=90.0,
        risk_score=25.0,
        recommended_size=0.10,
        late_entry=False,
        event_veto=False,
        status=status,
        execution_required=False,
        factors={},
    )


def _active_state(*, reset_counter: int, last_evaluated_as_of: str) -> dict:
    return {
        "active_direction": "USD→URA",
        "stage": 1,
        "cumulative_size": 0.10,
        "last_action_date": "2026-09-01",
        "reset_counter": reset_counter,
        "last_evaluated_as_of": last_evaluated_as_of,
    }


def test_reset_counter_advances_once_per_market_as_of() -> None:
    settings = _settings()
    state = _active_state(reset_counter=1, last_evaluated_as_of="2026-09-04")

    first = _decision("2026-09-05", status="WAIT", edge=30.0)
    state = apply_signal_state(first, state, settings)
    assert state["reset_counter"] == 2
    assert state["last_evaluated_as_of"] == "2026-09-05"

    repeated = _decision("2026-09-05", status="WAIT", edge=20.0)
    state = apply_signal_state(repeated, state, settings)
    assert state["reset_counter"] == 2
    assert repeated.rationale["signal_state"]["last_evaluated_as_of"] == "2026-09-05"

    next_market_day = _decision("2026-09-06", status="WAIT", edge=25.0)
    state = apply_signal_state(next_market_day, state, settings)
    assert state["reset_counter"] == 3
    assert state["last_evaluated_as_of"] == "2026-09-06"


def test_same_asof_strong_active_direction_can_clear_reset_counter() -> None:
    settings = _settings()
    state = _active_state(reset_counter=3, last_evaluated_as_of="2026-09-05")

    corrected_same_day = _decision("2026-09-05", status="WAIT", edge=50.0)
    state = apply_signal_state(corrected_same_day, state, settings)

    assert state["reset_counter"] == 0
    assert state["active_direction"] == "USD→URA"
    assert state["stage"] == 1


def test_second_stage_action_remains_blocked_on_same_action_date() -> None:
    settings = _settings()
    state = {
        "active_direction": "USD→URA",
        "stage": 1,
        "cumulative_size": 0.10,
        "last_action_date": "2026-09-05",
        "reset_counter": 0,
        "last_evaluated_as_of": "2026-09-05",
    }

    repeated_action = _decision(
        "2026-09-05",
        status="ACTION",
        edge=85.0,
        confidence=85.0,
    )
    state = apply_signal_state(repeated_action, state, settings)

    assert repeated_action.action_event is False
    assert repeated_action.action_stage == 1
    assert repeated_action.action_size == 0.0
    assert state["cumulative_size"] == 0.10
    assert state["last_action_date"] == "2026-09-05"
