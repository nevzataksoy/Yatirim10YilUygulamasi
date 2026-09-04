from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.database.pool_telemetry import PoolTelemetryRecorder, compact_pool_stats, pool_counter_deltas


class PoolTelemetryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
