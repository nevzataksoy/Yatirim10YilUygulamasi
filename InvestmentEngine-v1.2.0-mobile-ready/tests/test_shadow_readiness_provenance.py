from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.schedule_contract import expected_run_counts


ROOT = Path(__file__).resolve().parents[1]


def _shadow_readiness_method_source() -> str:
    text = (ROOT / "app" / "database" / "repository.py").read_text(encoding="utf-8")
    return text.split("    def shadow_readiness_stats(self) -> dict:", 1)[1].split(
        "    def insert_validation_run(", 1
    )[0]


def test_shadow_readiness_expected_fire_baseline_matches_production_rca() -> None:
    start = datetime(2026, 9, 3, 19, 49, 26, 322356, tzinfo=timezone.utc)
    end = datetime(2026, 9, 10, 19, 49, 26, 322356, tzinfo=timezone.utc)

    counts = expected_run_counts(start, end, "Europe/Istanbul")

    assert counts == {
        "hourly_job": 168,
        "macro_job": 28,
        "sec_event_job": 168,
        "daily_crypto_job": 7,
        "daily_ura_job": 7,
        "daily_fx_job": 5,
        "weekly_job": 1,
        "monthly_audit_job": 0,
    }
    assert sum(counts.values()) == 384


def test_shadow_readiness_job_health_uses_scheduler_provenance_contract() -> None:
    method = " ".join(_shadow_readiness_method_source().split())

    assert "from model.shadow_epochs" in method
    assert "where status='ACTIVE' and model_version=%s" in method
    assert "shadow_epoch_id=%s" in method
    assert "started_at >= %s and started_at <= %s" in method
    assert "run_kind = any(%s)" in method
    assert "scheduled" in method
    assert "scheduled_legacy" in method
    assert "expected_run_counts(" in method
    assert "job_name not in ('realtime_test')" not in method


def test_shadow_readiness_keeps_released_success_status_semantics() -> None:
    method = " ".join(_shadow_readiness_method_source().split())
    assert '{"OK", "DEGRADED", "SKIPPED"}' in method
