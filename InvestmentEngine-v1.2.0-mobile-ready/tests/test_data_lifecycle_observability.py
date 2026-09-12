from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.database.data_lifecycle import read_data_lifecycle_snapshot
from app.engine import InvestmentEngine


class _FakeCursor:
    def __init__(self, row: dict) -> None:
        self.row = row
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, params=None) -> None:
        self.sql = sql
        self.params = params

    def fetchone(self) -> dict:
        return self.row


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        raise AssertionError("read_data_lifecycle_snapshot must never commit")


class _FakeDb:
    def __init__(self, row: dict) -> None:
        self.cursor = _FakeCursor(row)
        self.connection_obj = _FakeConnection(self.cursor)

    def connection(self) -> _FakeConnection:
        return self.connection_obj


class _AuditRepo:
    def __init__(self) -> None:
        self.health: dict | None = None
        self.job: dict | None = None

    def evaluate_mature_decisions(self, horizons) -> dict:
        return {"evaluated": 2, "skipped": 1, "horizons": list(horizons)}

    def publish_health(self, component, status, message="", details=None) -> None:
        self.health = {
            "component": component,
            "status": status,
            "message": message,
            "details": details,
        }

    def log_job(self, job_name, status, started_at, message="", details=None) -> None:
        self.job = {
            "job_name": job_name,
            "status": status,
            "started_at": started_at,
            "message": message,
            "details": details,
        }


class DataLifecycleObservabilityTests(unittest.TestCase):
    def _row(self, *, candidates: int = 0) -> dict:
        return {
            "checked_at": datetime(2026, 9, 10, 14, 0, tzinfo=timezone.utc),
            "full_fidelity_days": 90,
            "macro_rows": 20435,
            "macro_consecutive_same_value_rows": 0,
            "macro_total_bytes": 60_000_000,
            "macro_dead_tuples": 0,
            "job_runs_rows": 2327,
            "job_runs_rows_last_7d": 386,
            "job_runs_rows_older_than_full_fidelity": candidates + 4,
            "job_runs_compaction_candidate_rows": candidates,
            "job_runs_compaction_candidate_payload_bytes": candidates * 440,
            "old_incident_or_unknown_rows": 1,
            "old_non_scheduler_evidence_rows": 1,
            "old_provenance_gap_rows": 1,
            "old_milestone_rows": 1,
            "old_status_message_boundary_rows": 2,
            "old_daily_anchor_rows": 2,
            "job_runs_total_bytes": 4_200_000,
            "job_runs_dead_tuples": 0,
        }

    def test_snapshot_query_is_read_only_and_preserves_policy_contract(self) -> None:
        db = _FakeDb(self._row(candidates=5))

        result = read_data_lifecycle_snapshot(
            db,
            full_fidelity_days=90,
            timezone_name="Europe/Istanbul",
        )

        normalized = re.sub(r"\s+", " ", db.cursor.sql.lower())
        self.assertNotIn("delete from", normalized)
        self.assertNotIn("insert into", normalized)
        self.assertNotRegex(normalized, r"\bupdate\s+[a-z_]")
        self.assertNotIn("vacuum ", normalized)
        self.assertEqual(db.cursor.params, (90, "Europe/Istanbul"))
        self.assertFalse(result["mutation_performed"])
        self.assertFalse(result["delete_authorized"])
        self.assertEqual(result["maintenance_action"], "OBSERVE_CANDIDATES_ONLY")
        self.assertEqual(result["job_runs"]["compaction_candidate_rows"], 5)
        self.assertEqual(result["job_runs"]["protected_rows_older_than_full_fidelity"], 4)
        self.assertEqual(result["macro"]["consecutive_same_value_rows"], 0)

    def test_snapshot_rejects_unsafe_window(self) -> None:
        with self.assertRaises(ValueError):
            read_data_lifecycle_snapshot(_FakeDb(self._row()), full_fidelity_days=6)

    def _engine(self) -> tuple[InvestmentEngine, _AuditRepo]:
        engine = InvestmentEngine.__new__(InvestmentEngine)
        repo = _AuditRepo()
        engine.repo = repo
        engine.db = object()
        engine.settings = SimpleNamespace(timezone="Europe/Istanbul")
        engine.model_validation_job = lambda *, log_job=True: {
            "shadow_readiness": {"status": "READY"},
            "weights_changed": False,
            "thresholds_changed": False,
        }
        return engine, repo

    def test_monthly_audit_embeds_lifecycle_snapshot_without_changing_audit_status(self) -> None:
        engine, repo = self._engine()
        lifecycle = {
            "status": "OK",
            "maintenance_action": "NO_OP",
            "mutation_performed": False,
            "delete_authorized": False,
        }
        with patch("app.engine.read_data_lifecycle_snapshot", return_value=lifecycle) as reader:
            engine.monthly_audit_job()

        reader.assert_called_once_with(
            engine.db,
            full_fidelity_days=90,
            timezone_name="Europe/Istanbul",
        )
        self.assertEqual(repo.health["status"], "OK")
        self.assertEqual(repo.job["status"], "OK")
        self.assertEqual(repo.job["job_name"], "monthly_audit_job")
        self.assertEqual(repo.job["details"]["data_lifecycle"], lifecycle)
        self.assertFalse(repo.job["details"]["weights_changed"])

    def test_lifecycle_observability_failure_is_best_effort_for_monthly_audit(self) -> None:
        engine, repo = self._engine()
        with patch(
            "app.engine.read_data_lifecycle_snapshot",
            side_effect=RuntimeError("read-only lifecycle probe failed"),
        ):
            engine.monthly_audit_job()

        lifecycle = repo.job["details"]["data_lifecycle"]
        self.assertEqual(repo.job["status"], "OK")
        self.assertEqual(repo.health["status"], "OK")
        self.assertEqual(lifecycle["status"], "DEGRADED")
        self.assertEqual(lifecycle["maintenance_action"], "OBSERVABILITY_FAILED_NO_MUTATION")
        self.assertFalse(lifecycle["mutation_performed"])
        self.assertFalse(lifecycle["delete_authorized"])


if __name__ == "__main__":
    unittest.main()
