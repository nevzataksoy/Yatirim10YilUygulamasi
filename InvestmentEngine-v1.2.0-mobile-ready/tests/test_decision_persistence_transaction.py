from __future__ import annotations

import copy
from contextlib import contextmanager

import pytest

from app.database.decision_persistence import persist_decision_outcome
from app.engines.signal_state import apply_signal_state
from app.models import AppSettings, Decision


def _settings() -> AppSettings:
    return AppSettings(
        regime_reset_edge=45.0,
        regime_reset_days=5,
        strong_action_edge=80.0,
        strong_action_confidence=80.0,
        base_tranche_pct=0.25,
        max_regime_pct=0.50,
    )


def _decision(
    as_of: str = "2026-09-08",
    *,
    status: str = "ACTION",
    edge: float = 85.0,
    confidence: float = 85.0,
) -> Decision:
    return Decision(
        system="URA/USD",
        as_of=as_of,
        direction="USD→URA",
        regime="RISK_ON_TREND",
        edge_score=edge,
        confidence=confidence,
        uncertainty=15.0,
        data_quality=90.0,
        risk_score=20.0,
        recommended_size=0.25,
        late_entry=False,
        event_veto=False,
        status=status,
        execution_required=False,
        factors={},
    )


def _normalize(sql: str) -> str:
    return " ".join(sql.lower().split())


class _FakeCursor:
    def __init__(self, conn: "_FakeConnection") -> None:
        self.conn = conn
        self._row = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        query = _normalize(sql)
        self.conn.sql.append(query)

        if query.startswith("insert into model.signal_state"):
            system = params[0]
            self.conn.working_state.setdefault(
                system,
                {
                    "system": system,
                    "active_direction": None,
                    "stage": 0,
                    "cumulative_size": 0.0,
                    "last_action_date": None,
                    "reset_counter": 0,
                    "last_evaluated_as_of": None,
                },
            )
            return

        if query.startswith("select * from model.signal_state"):
            system = params[0]
            self.conn.lock_observed = "for update" in query
            self._row = copy.deepcopy(self.conn.working_state.get(system))
            return

        if query.startswith("update model.signal_state"):
            active, stage, cumulative, last_action, reset_counter, system = params
            self.conn.working_state[system].update(
                active_direction=active,
                stage=stage,
                cumulative_size=cumulative,
                last_action_date=last_action,
                reset_counter=reset_counter,
            )
            return

        if query.startswith("insert into model.decisions"):
            if self.conn.fail_on == "decision":
                raise RuntimeError("injected decision failure")
            as_of, system = params[0], params[1]
            self.conn.next_id += 1
            decision_id = self.conn.next_id
            self.conn.working_decisions.append(
                {"id": decision_id, "as_of": as_of, "system": system}
            )
            # Migration 0013 AFTER INSERT trigger is represented in the fake
            # transaction so rollback semantics include the marker too.
            self.conn.working_state[system]["last_evaluated_as_of"] = as_of
            self._row = {"id": decision_id}
            return

        if query.startswith("insert into public.decision_history"):
            if self.conn.fail_on == "history":
                raise RuntimeError("injected history failure")
            self.conn.working_history.append({"decision_id": params[0]})
            return

        if query.startswith("insert into public.decision_snapshot"):
            if self.conn.fail_on == "snapshot":
                raise RuntimeError("injected snapshot failure")
            self.conn.working_snapshot[params[0]] = {"as_of": params[1]}
            return

        raise AssertionError(f"Beklenmeyen SQL: {query}")

    def fetchone(self):
        row, self._row = self._row, None
        return row


class _FakeConnection:
    def __init__(self, db: "_FakeDb") -> None:
        self.db = db
        self.fail_on = db.fail_on
        self.next_id = db.next_id
        self.sql: list[str] = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.lock_observed = False
        self.working_state = copy.deepcopy(db.state)
        self.working_decisions = copy.deepcopy(db.decisions)
        self.working_history = copy.deepcopy(db.history)
        self.working_snapshot = copy.deepcopy(db.snapshot)

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commit_calls += 1
        self.db.state = copy.deepcopy(self.working_state)
        self.db.decisions = copy.deepcopy(self.working_decisions)
        self.db.history = copy.deepcopy(self.working_history)
        self.db.snapshot = copy.deepcopy(self.working_snapshot)
        self.db.next_id = self.next_id

    def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeDb:
    def __init__(self, state: dict | None = None, fail_on: str | None = None) -> None:
        self.state = copy.deepcopy(state or {})
        self.decisions: list[dict] = []
        self.history: list[dict] = []
        self.snapshot: dict[str, dict] = {}
        self.next_id = 0
        self.fail_on = fail_on
        self.connection_calls = 0
        self.last_conn: _FakeConnection | None = None

    @contextmanager
    def connection(self):
        self.connection_calls += 1
        conn = _FakeConnection(self)
        self.last_conn = conn
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise


def _persist(db: _FakeDb, decision: Decision) -> int:
    settings = _settings()
    return persist_decision_outcome(
        db,
        decision,
        "alpha_vantage",
        lambda raw_state: apply_signal_state(decision, raw_state, settings),
    )


def test_success_uses_one_connection_one_commit_and_locked_state() -> None:
    db = _FakeDb()
    decision = _decision()

    decision_id = _persist(db, decision)

    assert decision_id == 1
    assert db.connection_calls == 1
    assert db.last_conn is not None
    assert db.last_conn.commit_calls == 1
    assert db.last_conn.rollback_calls == 0
    assert db.last_conn.lock_observed is True
    assert decision.action_event is True
    assert decision.action_stage == 1
    assert db.state["URA/USD"]["stage"] == 1
    assert db.state["URA/USD"]["cumulative_size"] == 0.25
    assert db.state["URA/USD"]["last_evaluated_as_of"] == "2026-09-08"
    assert len(db.decisions) == 1
    assert len(db.history) == 1
    assert db.snapshot["URA/USD"]["as_of"] == "2026-09-08"


@pytest.mark.parametrize("fail_on", ["decision", "history", "snapshot"])
def test_any_persistence_failure_rolls_back_entire_outcome(fail_on: str) -> None:
    db = _FakeDb(fail_on=fail_on)
    decision = _decision()

    with pytest.raises(RuntimeError):
        _persist(db, decision)

    assert db.connection_calls == 1
    assert db.last_conn is not None
    assert db.last_conn.commit_calls == 0
    assert db.last_conn.rollback_calls == 1
    assert db.state == {}
    assert db.decisions == []
    assert db.history == []
    assert db.snapshot == {}


def test_failed_k1_does_not_consume_state_and_retry_can_emit_k1() -> None:
    db = _FakeDb(fail_on="decision")

    with pytest.raises(RuntimeError):
        _persist(db, _decision())

    assert db.state == {}

    db.fail_on = None
    retry = _decision()
    decision_id = _persist(db, retry)

    assert decision_id == 1
    assert retry.action_event is True
    assert retry.action_stage == 1
    assert db.state["URA/USD"]["stage"] == 1
    assert db.state["URA/USD"]["cumulative_size"] == 0.25


def test_failed_reset_transition_preserves_previous_committed_state() -> None:
    original_state = {
        "URA/USD": {
            "system": "URA/USD",
            "active_direction": "USD→URA",
            "stage": 1,
            "cumulative_size": 0.25,
            "last_action_date": "2026-09-01",
            "reset_counter": 4,
            "last_evaluated_as_of": "2026-09-07",
        }
    }
    db = _FakeDb(original_state, fail_on="decision")
    weak_wait = _decision(status="WAIT", edge=20.0, confidence=50.0)

    with pytest.raises(RuntimeError):
        _persist(db, weak_wait)

    assert db.state == original_state
