from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.engines.ura import score_event_monitor, score_ura_breadth


def test_breadth_audit_details_preserve_scoring_inputs_without_changing_score() -> None:
    row = {
        "breadth_date": date(2026, 9, 4),
        "created_at": datetime(2026, 9, 5, 1, 2, 3, tzinfo=timezone.utc),
        "quality": 80.0,
        "pct_above_20dma": 0.60,
        "pct_above_50dma": 0.55,
        "pct_above_200dma": None,
        "pct_positive_day": 0.52,
        "new_20d_high_pct": 0.15,
        "details": {"source": "Global X test fixture"},
    }

    factor = score_ura_breadth(row, "2026-09-04")

    # Existing scoring semantics: (14 + 7 + 2.8 + 8) / 4 = 7.95.
    assert factor.score == pytest.approx(7.95)
    assert factor.quality == pytest.approx(80.0)
    assert factor.details["pct_above_20dma"] == pytest.approx(0.60)
    assert factor.details["pct_above_50dma"] == pytest.approx(0.55)
    assert factor.details["pct_above_200dma"] is None
    assert factor.details["pct_positive_day"] == pytest.approx(0.52)
    assert factor.details["new_20d_high_pct"] == pytest.approx(0.15)
    assert factor.details["created_at"] == "2026-09-05T01:02:03+00:00"
    assert factor.details["source"] == "Global X test fixture"


def test_event_audit_details_persist_health_time_and_exact_quiet_event_set() -> None:
    health = {
        "status": "DEGRADED",
        "checked_at": datetime(2026, 9, 7, 20, 5, tzinfo=timezone.utc),
        "details": {"quality": 19.37},
    }
    recent_events = [
        {
            "source": "sec",
            "entity": "Example Corp",
            "asset": "URA",
            "event_type": "10-Q",
            "url": "https://example.test/filing/1",
            "occurred_at": datetime(2026, 9, 7, 18, 0, tzinfo=timezone.utc),
            "severity": 0,
            "surprise": 0,
            "credibility": 100,
        }
    ]

    factor = score_event_monitor(health, recent_events)

    assert factor.score == 0
    assert factor.quality == pytest.approx(19.37)
    assert factor.details["directional_events"] == 0
    assert factor.details["health_checked_at"] == "2026-09-07T20:05:00+00:00"
    assert factor.details["health_status"] == "DEGRADED"
    assert factor.details["recent_events"] == 1
    assert factor.details["event_refs"] == [
        {
            "source": "sec",
            "entity": "Example Corp",
            "asset": "URA",
            "event_type": "10-Q",
            "url": "https://example.test/filing/1",
            "occurred_at": "2026-09-07T18:00:00+00:00",
            "severity": 0.0,
            "surprise": 0.0,
            "credibility": 100.0,
        }
    ]


def test_event_audit_metadata_does_not_change_directional_weighting() -> None:
    health = {
        "status": "OK",
        "checked_at": "2026-09-07T20:05:00+00:00",
        "details": {"quality": 70.0},
    }
    recent_events = [
        {
            "source": "test",
            "entity": "A",
            "asset": "URA",
            "event_type": "negative",
            "url": "negative",
            "occurred_at": "2026-09-07T18:00:00+00:00",
            "severity": -50,
            "surprise": 0,
            "credibility": 80,
        },
        {
            "source": "test",
            "entity": "B",
            "asset": "URA",
            "event_type": "positive",
            "url": "positive",
            "occurred_at": "2026-09-07T19:00:00+00:00",
            "severity": 20,
            "surprise": 0,
            "credibility": 40,
        },
    ]

    factor = score_event_monitor(health, recent_events)

    # Existing weighting semantics: (-50*0.8 + 20*0.4) / (0.8+0.4).
    assert factor.score == pytest.approx(-26.6666666667)
    assert factor.quality == pytest.approx(70.0)
    assert factor.details["directional_events"] == 2
    assert len(factor.details["event_refs"]) == 2
