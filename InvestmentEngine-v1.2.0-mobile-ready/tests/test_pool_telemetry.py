from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from psycopg_pool import PoolTimeout

from app.database.db import DatabaseService
from app.database.pool_telemetry import (
    PoolTelemetryRecorder,
    application_module_from_filename,
    compact_pool_stats,
    connection_lifecycle_snapshot,
    pool_counter_deltas,
)


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs) -> None:
        return None


class _FakeInfo:
    backend_pid = 4242


class _FakeConnection:
    def __init__(self) -> None:
        self.info = _FakeInfo()
        self._created_at = 40.0
        self._expire_at = 90.0

    def cursor(self) -> _FakeCursor:
        return _FakeCursor()


class _FakeConnectionContext:
    def __init__(self, enter_error: Exception | None = None) -> None:
        self.enter_error = enter_error
        self.connection = _FakeConnection()

    def __enter__(self):
        if self.enter_error is not None:
            raise self.enter_error
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, enter_error: Exception | None = None) -> None:
        self.enter_error = enter_error

    def connection(self) -> _FakeConnectionContext:
        return _FakeConnectionContext(self.enter_error)

    def get_stats(self) -> dict[str, int]:
        return {
            "pool_min": 1,
            "pool_max": 6,
            "pool_size": 1,
            "pool_available": 1,
            "requests_waiting": 0,
        }


class _RecordingTelemetry:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def infer_callsite(self) -> str:
        return "tests.fake_callsite"

    def observe_counter_deltas(self, _stats: dict[str, int]) -> dict[str, int]:
        return {}

    def sample_due(self) -> bool:
        return False

    def record(self, event: str, **fields) -> None:
        self.events.append({"event": event, **fields})


class PoolTelemetryTests(unittest.TestCase):
    def _database_service(self, pool: _FakePool) -> tuple[DatabaseService, _RecordingTelemetry]:
        service = DatabaseService.__new__(DatabaseService)
        service.settings = None
        service.pool = pool
        telemetry = _RecordingTelemetry()
        service._pool_telemetry = telemetry
        return service, telemetry

    def test_compact_pool_stats_fills_optional_zero_keys(self) -> None:
        stats = compact_pool_stats({"pool_min": 1, "pool_max": 6, "requests_num": 4})
        self.assertEqual(stats["pool_min"], 1)
        self.assertEqual(stats["pool_max"], 6)
        self.assertEqual(stats["requests_num"], 4)
        self.assertEqual(stats["requests_waiting"], 0)
        self.assertEqual(stats["connections_lost"], 0)

    def test_counter_deltas_only_report_positive_health_changes(self) -> None:
        previous = {
            "requests_queued": 2,
            "requests_errors": 1,
            "returns_bad": 0,
            "connections_errors": 3,
            "connections_lost": 1,
        }
        current = {
            "requests_queued": 4,
            "requests_errors": 1,
            "returns_bad": 1,
            "connections_errors": 2,
            "connections_lost": 3,
        }
        self.assertEqual(
            pool_counter_deltas(previous, current),
            {"requests_queued": 2, "returns_bad": 1, "connections_lost": 2},
        )
        self.assertEqual(pool_counter_deltas(None, current), {})

    def test_connection_lifecycle_snapshot_reports_expiry_without_mutation(self) -> None:
        conn = _FakeConnection()
        snapshot = connection_lifecycle_snapshot(conn, now_monotonic=100.0)
        self.assertEqual(snapshot["backend_pid"], 4242)
        self.assertEqual(snapshot["age_ms"], 60_000.0)
        self.assertEqual(snapshot["expires_in_ms"], -10_000.0)
        self.assertTrue(snapshot["expired"])
        self.assertEqual(conn._created_at, 40.0)
        self.assertEqual(conn._expire_at, 90.0)

    def test_application_module_from_filename_supports_source_and_frozen_paths(self) -> None:
        self.assertEqual(
            application_module_from_filename(r"D:\repo\InvestmentEngine\app\database\repository.py"),
            "database.repository",
        )
        self.assertEqual(
            application_module_from_filename(r"app\notifications\dispatcher.py"),
            "notifications.dispatcher",
        )
        self.assertIsNone(application_module_from_filename(r"contextlib.py"))

    def test_recorder_writes_process_local_jsonl_and_throttles_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = PoolTelemetryRecorder(Path(temp_dir), sample_interval_seconds=60)
            self.assertTrue(recorder.sample_due())
            self.assertFalse(recorder.sample_due())

            recorder.record("sample", root_job_name="hourly_job", stats={"pool_size": 1})

            expected = Path(temp_dir) / f"connection-pool-telemetry-{os.getpid()}.jsonl"
            self.assertTrue(expected.exists())
            payload = json.loads(expected.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["event"], "sample")
            self.assertEqual(payload["root_job_name"], "hourly_job")
            self.assertEqual(payload["pid"], os.getpid())

    def test_database_service_lifecycle_callbacks_record_creation_and_expiry(self) -> None:
        service, telemetry = self._database_service(_FakePool())
        conn = _FakeConnection()

        service._configure_pool_connection(conn)
        conn._expire_at = 0.0
        service._reset_pool_connection(conn)

        self.assertEqual(
            [event["event"] for event in telemetry.events],
            ["connection_created", "connection_expired_on_return"],
        )
        self.assertEqual(telemetry.events[0]["backend_pid"], 4242)
        self.assertTrue(telemetry.events[1]["expired"])

    def test_database_service_records_checkout_timeout_only_before_acquisition(self) -> None:
        service, telemetry = self._database_service(_FakePool(PoolTimeout("pool checkout timeout")))
        with self.assertRaises(PoolTimeout):
            with service.connection():
                pass
        self.assertEqual([event["event"] for event in telemetry.events], ["checkout_timeout"])

    def test_nested_pool_timeout_is_not_misclassified_as_outer_checkout_timeout(self) -> None:
        service, telemetry = self._database_service(_FakePool())
        with self.assertRaises(PoolTimeout):
            with service.connection():
                raise PoolTimeout("nested timeout")
        self.assertNotIn("checkout_timeout", [event["event"] for event in telemetry.events])

    def test_hold_timing_is_recorded_after_pool_context_exit(self) -> None:
        service, telemetry = self._database_service(_FakePool())
        service._SLOW_HOLD_MS = -1.0
        with service.connection():
            pass
        events = [event for event in telemetry.events if event["event"] == "hold_slow"]
        self.assertEqual(len(events), 1)
        self.assertGreaterEqual(float(events[0]["hold_ms"]), 0.0)


if __name__ == "__main__":
    unittest.main()
