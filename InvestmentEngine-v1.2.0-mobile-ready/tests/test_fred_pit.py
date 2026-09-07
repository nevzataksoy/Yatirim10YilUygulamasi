from __future__ import annotations

from app.backtest.fred_pit import (
    prepare_realtime_history,
    strict_macro_asof,
    strict_macro_coverage,
)
from app.collectors.fred import FredCollector


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class _PagedSession:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get(self, _url, *, params, timeout):
        self.calls.append({"params": dict(params), "timeout": timeout})
        if int(params["offset"]) == 0:
            return _Response(
                {
                    "count": 100001,
                    "observations": [
                        {
                            "date": "2024-01-01",
                            "value": "1.5",
                            "realtime_start": "2024-01-03",
                            "realtime_end": "2024-01-09",
                        },
                        {
                            "date": "2024-01-02",
                            "value": ".",
                            "realtime_start": "2024-01-03",
                            "realtime_end": "2024-01-09",
                        },
                    ],
                }
            )
        return _Response(
            {
                "count": 100001,
                "observations": [
                    {
                        "date": "2024-01-01",
                        "value": "1.7",
                        "realtime_start": "2024-01-10",
                        "realtime_end": ".",
                    }
                ],
            }
        )


def test_strict_macro_selector_respects_release_and_revision_intervals():
    prepared = prepare_realtime_history(
        {
            "SERIES": [
                {
                    "date": "2024-01-01",
                    "value": 1.0,
                    "realtime_start": "2024-01-03",
                    "realtime_end": "2024-01-09",
                },
                {
                    "date": "2024-01-01",
                    "value": 2.0,
                    "realtime_start": "2024-01-10",
                    "realtime_end": None,
                },
                {
                    "date": "2024-01-08",
                    "value": 8.0,
                    "realtime_start": "2024-01-12",
                    "realtime_end": None,
                },
            ]
        }
    )

    assert strict_macro_asof(prepared, "2024-01-02") == {}
    assert strict_macro_asof(prepared, "2024-01-05")["SERIES"]["value"] == 1.0
    assert strict_macro_asof(prepared, "2024-01-10")["SERIES"]["value"] == 2.0
    assert strict_macro_asof(prepared, "2024-01-11")["SERIES"]["value"] == 2.0
    assert strict_macro_asof(prepared, "2024-01-12")["SERIES"]["value"] == 8.0


def test_strict_macro_coverage_reports_missing_series_by_date():
    prepared = prepare_realtime_history(
        {
            "A": [
                {
                    "date": "2024-01-01",
                    "value": 1,
                    "realtime_start": "2024-01-02",
                    "realtime_end": None,
                }
            ],
            "B": [
                {
                    "date": "2024-01-01",
                    "value": 2,
                    "realtime_start": "2024-01-03",
                    "realtime_end": None,
                }
            ],
        }
    )

    result = strict_macro_coverage(
        prepared,
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        ["A", "B"],
    )

    assert result["dates"] == 3
    assert result["complete_dates"] == 2
    assert result["complete_ratio"] == 2 / 3
    assert result["first_complete_date"] == "2024-01-03"
    assert result["last_complete_date"] == "2024-01-04"
    assert result["missing_date_counts"] == {"A": 0, "B": 1}


def test_fred_realtime_history_requests_complete_period_and_normalizes_rows():
    collector = FredCollector("test-api-key")
    session = _PagedSession()
    collector.session = session

    rows = collector.fetch_realtime_history(
        "SERIES",
        observation_start="2024-01-01",
        observation_end="2024-01-31",
    )

    assert len(session.calls) == 2
    first = session.calls[0]["params"]
    assert first["realtime_start"] == "1776-07-04"
    assert first["realtime_end"] == "9999-12-31"
    assert first["output_type"] == 1
    assert first["observation_start"] == "2024-01-01"
    assert first["observation_end"] == "2024-01-31"
    assert session.calls[1]["params"]["offset"] == 2

    assert rows == [
        {
            "series_id": "SERIES",
            "date": "2024-01-01",
            "value": 1.5,
            "realtime_start": "2024-01-03",
            "realtime_end": "2024-01-09",
        },
        {
            "series_id": "SERIES",
            "date": "2024-01-01",
            "value": 1.7,
            "realtime_start": "2024-01-10",
            "realtime_end": None,
        },
    ]
