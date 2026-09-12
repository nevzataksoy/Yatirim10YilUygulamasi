from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.run_context import current_job_context, job_run_context
from app.schedule_contract import expected_run_counts


class ShadowObservabilityTests(unittest.TestCase):
    def test_task4_seven_day_expected_schedule(self) -> None:
        start = datetime(2026, 7, 31, 12, 33, tzinfo=timezone.utc)
        end = datetime(2026, 8, 7, 12, 33, tzinfo=timezone.utc)
        counts = expected_run_counts(start, end, "Europe/Istanbul")
        self.assertEqual(counts["hourly_job"], 168)
        self.assertEqual(counts["macro_job"], 28)
        self.assertEqual(counts["sec_event_job"], 168)
        self.assertEqual(counts["daily_crypto_job"], 7)
        self.assertEqual(counts["daily_ura_job"], 7)
        self.assertEqual(counts["daily_fx_job"], 5)
        self.assertEqual(counts["weekly_job"], 1)
        self.assertEqual(counts["monthly_audit_job"], 1)
        self.assertEqual(sum(counts.values()), 385)

    def test_job_context_restores_previous_values(self) -> None:
        self.assertEqual(current_job_context(), ("", "legacy"))
        with job_run_context("weekly_job", "scheduled"):
            self.assertEqual(current_job_context(), ("weekly_job", "scheduled"))
        self.assertEqual(current_job_context(), ("", "legacy"))


if __name__ == "__main__":
    unittest.main()
