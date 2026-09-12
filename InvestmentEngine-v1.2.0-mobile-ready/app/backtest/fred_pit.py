from __future__ import annotations

from bisect import bisect_right
from datetime import date

from app.backtest.validation import ReplayPoint, _aligned_crypto
from app.engines.decision import DecisionEngine
from app.engines.factors import (
    neutral,
    score_flow,
    score_macro,
    score_momentum,
    score_trend,
    score_value,
    score_volatility,
)
from app.engines.regime import detect_regime
from app.features.builders import crypto_features
from app.models import AppSettings, FactorScore, PriceBar


PreparedRealtimeHistory = dict[
    str,
    tuple[
        list[date],
        list[tuple[list[date], list[dict]]],
    ],
]


def _as_date(value) -> date | None:
    if value in (None, "", "."):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def prepare_realtime_history(rows: dict[str, list[dict]]) -> PreparedRealtimeHistory:
    """Index ALFRED real-time-period rows for efficient historical lookup."""
    prepared: PreparedRealtimeHistory = {}

    for series_id, items in rows.items():
        by_observation: dict[date, list[dict]] = {}
        for item in items:
            obs = _as_date(item.get("observation_date") or item.get("date"))
            realtime_start = _as_date(item.get("realtime_start"))
            if obs is None or realtime_start is None or item.get("value") is None:
                continue
            normalized = {
                "series_id": series_id,
                "observation_date": obs,
                "value": float(item["value"]),
                "realtime_start": realtime_start,
                "realtime_end": _as_date(item.get("realtime_end")),
            }
            by_observation.setdefault(obs, []).append(normalized)

        observation_dates = sorted(by_observation)
        revision_groups: list[tuple[list[date], list[dict]]] = []
        for obs in observation_dates:
            revisions = sorted(
                by_observation[obs],
                key=lambda row: row["realtime_start"],
            )
            revision_groups.append(
                ([row["realtime_start"] for row in revisions], revisions)
            )
        prepared[series_id] = (observation_dates, revision_groups)

    return prepared


def strict_macro_asof(
    prepared: PreparedRealtimeHistory,
    as_of: str | date,
) -> dict[str, dict]:
    """Return only macro values that were public on the requested historical date.

    Both conditions are enforced:

    - observation_date <= as_of
    - realtime_start <= as_of <= realtime_end (or open-ended current interval)

    Among valid rows the latest observation date is selected. If an observation
    has multiple historical revisions, the revision whose validity interval
    contains the historical date is used.
    """
    target = as_of if isinstance(as_of, date) else date.fromisoformat(str(as_of)[:10])
    out: dict[str, dict] = {}

    for series_id, (observation_dates, revision_groups) in prepared.items():
        obs_idx = bisect_right(observation_dates, target) - 1
        while obs_idx >= 0:
            starts, revisions = revision_groups[obs_idx]
            rev_idx = bisect_right(starts, target) - 1
            while rev_idx >= 0:
                row = revisions[rev_idx]
                realtime_end = row.get("realtime_end")
                if realtime_end is None or target <= realtime_end:
                    out[series_id] = row
                    break
                rev_idx -= 1
            if series_id in out:
                break
            obs_idx -= 1

    return out


def strict_macro_coverage(
    prepared: PreparedRealtimeHistory,
    as_of_dates: list[str],
    expected_series: list[str],
) -> dict:
    complete_dates = 0
    missing_counts = {series_id: 0 for series_id in expected_series}
    first_complete = None
    last_complete = None

    for as_of in as_of_dates:
        selected = strict_macro_asof(prepared, as_of)
        missing = [series_id for series_id in expected_series if series_id not in selected]
        for series_id in missing:
            missing_counts[series_id] += 1
        if not missing:
            complete_dates += 1
            first_complete = first_complete or as_of
            last_complete = as_of

    return {
        "dates": len(as_of_dates),
        "complete_dates": complete_dates,
        "complete_ratio": complete_dates / len(as_of_dates) if as_of_dates else 0.0,
        "first_complete_date": first_complete,
        "last_complete_date": last_complete,
        "missing_date_counts": missing_counts,
    }


def replay_ethbtc_core_strict_macro_pit(
    btc: list[PriceBar],
    eth: list[PriceBar],
    fred_realtime_history: dict[str, list[dict]],
    settings: AppSettings,
    decision_engine: DecisionEngine,
    *,
    min_history_sessions: int = 1120,
) -> list[ReplayPoint]:
    """Replay the ETH/BTC directional core using strict historical FRED vintages.

    Technical/value/flow inputs remain historical price-prefix calculations.
    Derivatives and event factors remain neutral because trustworthy PIT history
    for those factors is still unavailable. This is therefore a macro-PIT
    directional-core verification, not a production ACTION backtest.
    """
    dates, bmap, emap = _aligned_crypto(btc, eth)
    if len(dates) < min_history_sessions + 1:
        return []

    macro_prepared = prepare_realtime_history(fred_realtime_history)
    points: list[ReplayPoint] = []

    for i in range(min_history_sessions - 1, len(dates)):
        current_dates = dates[: i + 1]
        bprefix = [bmap[d] for d in current_dates]
        eprefix = [emap[d] for d in current_dates]
        try:
            features = crypto_features(bprefix, eprefix)
        except ValueError:
            continue

        as_of = str(features["as_of"]["value"])
        macro = score_macro(strict_macro_asof(macro_prepared, as_of), as_of)
        regime, _, _ = detect_regime(features, macro.score)
        factors: dict[str, FactorScore] = {
            "value": score_value(features),
            "trend": score_trend(features),
            "momentum": score_momentum(features),
            "volatility": score_volatility(features),
            "derivatives": neutral(
                "derivatives",
                0,
                "Point-in-time derivatives history unavailable.",
            ),
            "flow": score_flow(features),
            "macro": macro,
            "event": neutral(
                "event",
                0,
                "Point-in-time event history unavailable.",
            ),
        }
        decision, _ = decision_engine.build(
            "ETH/BTC",
            as_of,
            regime,
            features,
            factors,
            event_veto=False,
        )
        points.append(
            ReplayPoint(
                as_of=as_of,
                edge_signed=float(decision.rationale.get("edge_signed") or 0.0),
                edge=float(decision.edge_score),
                confidence=float(decision.confidence),
                data_quality=float(decision.data_quality),
                late_entry=bool(decision.late_entry),
                regime=regime,
                ratio=float(features["ratio"]["value"]),
            )
        )

    return points
