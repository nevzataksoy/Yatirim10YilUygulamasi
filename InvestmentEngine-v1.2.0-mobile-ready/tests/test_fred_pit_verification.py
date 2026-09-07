from __future__ import annotations

from app.backtest.fred_pit import prepare_realtime_history
from app.backtest.validation import ReplayPoint
from app.collectors.fred import FredRealtimeHistoryUnavailable
from verification.run_fred_strict_pit_validation import (
    _fetch_realtime_histories,
    _filter_points,
    _macro_coverage_partition,
    _point_comparison,
    _walk_forward_summary,
)


def _point(
    as_of: str,
    *,
    edge_signed: float,
    edge: float,
    regime: str = "NEUTRAL",
    late_entry: bool = False,
) -> ReplayPoint:
    return ReplayPoint(
        as_of=as_of,
        edge_signed=edge_signed,
        edge=edge,
        confidence=80.0,
        data_quality=90.0,
        late_entry=late_entry,
        regime=regime,
        ratio=0.05,
    )


class _FredStub:
    def fetch_realtime_history(self, series_id: str, **_kwargs):
        if series_id == "SP500":
            raise FredRealtimeHistoryUnavailable(
                "FRED SP500 isteği başarısız (HTTP 400): series does not exist in ALFRED"
            )
        return [
            {
                "series_id": series_id,
                "date": "2024-01-01",
                "value": 1.0,
                "realtime_start": "2024-01-02",
                "realtime_end": None,
            }
        ]


def test_point_comparison_reports_regime_direction_and_qualification_changes():
    current = [
        _point("2024-01-01", edge_signed=71.0, edge=71.0, regime="RISK_ON_TREND"),
        _point("2024-01-02", edge_signed=40.0, edge=40.0),
    ]
    strict = [
        _point("2024-01-01", edge_signed=-65.0, edge=65.0, regime="RISK_OFF"),
        _point("2024-01-02", edge_signed=42.0, edge=42.0),
    ]

    result = _point_comparison(current, strict, 70.0)

    assert result["common_dates"] == 2
    assert result["regime_change_dates"] == 1
    assert result["direction_change_dates"] == 1
    assert result["configured_qualification_change_dates"] == 1
    assert result["max_abs_edge_delta"] == 6.0
    assert result["largest_changes"][0]["as_of"] == "2024-01-01"


def test_point_comparison_reports_non_overlapping_dates():
    current = [_point("2024-01-01", edge_signed=1.0, edge=1.0)]
    strict = [_point("2024-01-02", edge_signed=1.0, edge=1.0)]

    result = _point_comparison(current, strict, 70.0)

    assert result["common_dates"] == 0
    assert result["current_only_dates"] == 1
    assert result["strict_only_dates"] == 1
    assert result["largest_changes"] == []


def test_realtime_history_fetch_continues_when_one_series_has_no_alfred_history():
    histories, unavailable = _fetch_realtime_histories(
        _FredStub(),
        ["DGS2", "SP500", "VIXCLS"],
        observation_start="2024-01-01",
        observation_end="2024-01-31",
    )

    assert len(histories["DGS2"]) == 1
    assert histories["SP500"] == []
    assert len(histories["VIXCLS"]) == 1
    assert list(unavailable) == ["SP500"]
    assert "does not exist in ALFRED" in unavailable["SP500"]


def test_complete_coverage_partition_separates_missing_dates_before_vintage_comparison():
    prepared = prepare_realtime_history(
        {
            "A": [
                {
                    "date": "2024-01-01",
                    "value": 1.0,
                    "realtime_start": "2024-01-02",
                    "realtime_end": None,
                }
            ],
            "B": [
                {
                    "date": "2024-01-01",
                    "value": 2.0,
                    "realtime_start": "2024-01-03",
                    "realtime_end": None,
                }
            ],
        }
    )

    complete, incomplete = _macro_coverage_partition(
        prepared,
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        ["A", "B"],
    )

    assert complete == {"2024-01-03", "2024-01-04"}
    assert incomplete == [
        {"as_of": "2024-01-02", "missing_series": ["B"]}
    ]

    points = [
        _point("2024-01-02", edge_signed=1.0, edge=1.0),
        _point("2024-01-03", edge_signed=2.0, edge=2.0),
        _point("2024-01-04", edge_signed=3.0, edge=3.0),
    ]
    filtered = _filter_points(points, complete)
    assert [point.as_of for point in filtered] == ["2024-01-03", "2024-01-04"]


def test_walk_forward_summary_does_not_treat_selection_ok_as_sufficient_evidence():
    raw_result = {
        "status": "OK",
        "observations": 1397,
        "fold_count": 11,
        "configured_edge_threshold": 70.0,
        "configured_holdout_signals": 0,
        "selected_candidate_folds": 2,
        "selected_candidate_holdout_signals": 3,
        "folds": [
            {
                "fold": 1,
                "selected_candidate": {
                    "edge_threshold": 55.0,
                    "holdout": {
                        "signals": 2,
                        "hit_rate": 0.5,
                        "avg_signed_return": 0.01,
                    },
                },
            },
            {
                "fold": 2,
                "selected_candidate": {
                    "edge_threshold": 50.0,
                    "holdout": {
                        "signals": 1,
                        "hit_rate": 0.0,
                        "avg_signed_return": -0.02,
                    },
                },
            },
        ],
    }

    summary = _walk_forward_summary(raw_result, min_oos_signals=8)

    assert summary["selection_status"] == "OK"
    assert summary["status"] == "LIMITED_OOS_SIGNAL_COUNT"
    assert summary["evidence_status"] == "LIMITED_OOS_SIGNAL_COUNT"
    assert summary["configured_holdout_signals"] == 0
    assert summary["selected_candidate_oos_summary"]["signals"] == 3
