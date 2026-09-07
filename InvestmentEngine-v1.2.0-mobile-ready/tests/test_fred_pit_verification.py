from __future__ import annotations

from app.backtest.validation import ReplayPoint
from app.collectors.fred import FredRealtimeHistoryUnavailable
from verification.run_fred_strict_pit_validation import (
    _fetch_realtime_histories,
    _point_comparison,
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
