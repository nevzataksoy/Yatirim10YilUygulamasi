from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from math import sqrt
from statistics import median
from typing import Iterable

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
from app.version import MODEL_VERSION


@dataclass(slots=True)
class ReplayPoint:
    as_of: str
    edge_signed: float
    edge: float
    confidence: float
    data_quality: float
    late_entry: bool
    regime: str
    ratio: float


@dataclass(slots=True)
class HorizonMetrics:
    horizon_sessions: int
    signals: int
    hit_rate: float
    avg_signed_return: float
    median_signed_return: float


def _aligned_crypto(btc: list[PriceBar], eth: list[PriceBar]) -> tuple[list[str], dict[str, PriceBar], dict[str, PriceBar]]:
    bmap = {x.date: x for x in btc}
    emap = {x.date: x for x in eth}
    dates = sorted(set(bmap).intersection(emap))
    return dates, bmap, emap


def _prepare_macro_history(rows: dict[str, list[dict]]) -> dict[str, tuple[list[date], list[dict]]]:
    out: dict[str, tuple[list[date], list[dict]]] = {}
    for series_id, items in rows.items():
        parsed = sorted(
            [
                (
                    x["observation_date"]
                    if isinstance(x["observation_date"], date)
                    else date.fromisoformat(str(x["observation_date"])[:10]),
                    x,
                )
                for x in items
            ],
            key=lambda item: item[0],
        )
        out[series_id] = ([x[0] for x in parsed], [x[1] for x in parsed])
    return out


def _macro_asof(prepared: dict[str, tuple[list[date], list[dict]]], as_of: str) -> dict[str, dict]:
    target = date.fromisoformat(as_of[:10])
    out: dict[str, dict] = {}
    for series_id, (dates, rows) in prepared.items():
        idx = bisect_right(dates, target) - 1
        if idx >= 0:
            out[series_id] = rows[idx]
    return out


def replay_ethbtc_core(
    btc: list[PriceBar],
    eth: list[PriceBar],
    macro_history: dict[str, list[dict]],
    settings: AppSettings,
    decision_engine: DecisionEngine,
    *,
    min_history_sessions: int = 1120,
    max_horizon_sessions: int = 60,
) -> list[ReplayPoint]:
    """Rebuild the historical directional core without future information.

    This intentionally excludes derivatives and event/sentiment because a
    trustworthy point-in-time history for those sources is not available yet.
    The returned edge therefore validates the technical/value/flow/macro core;
    it must not be presented as a historical production ACTION backtest.
    """
    dates, bmap, emap = _aligned_crypto(btc, eth)
    if len(dates) < min_history_sessions + 1:
        return []

    macro_prepared = _prepare_macro_history(macro_history)
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
        macro = score_macro(_macro_asof(macro_prepared, as_of), as_of)
        regime, _, _ = detect_regime(features, macro.score)
        factors: dict[str, FactorScore] = {
            "value": score_value(features),
            "trend": score_trend(features),
            "momentum": score_momentum(features),
            "volatility": score_volatility(features),
            "derivatives": neutral("derivatives", 0, "Point-in-time derivatives history unavailable."),
            "flow": score_flow(features),
            "macro": macro,
            "event": neutral("event", 0, "Point-in-time event history unavailable."),
        }
        decision, _ = decision_engine.build(
            "ETH/BTC", as_of, regime, features, factors, event_veto=False
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


def _select_signal_indices(
    points: list[ReplayPoint],
    edge_threshold: float,
    *,
    cooldown_sessions: int = 5,
    start: int = 0,
    end: int | None = None,
) -> list[int]:
    end = len(points) if end is None else min(end, len(points))
    selected: list[int] = []
    last_idx = -10_000
    last_sign = 0
    armed = True

    for i in range(max(0, start), end):
        p = points[i]
        sign = 1 if p.edge_signed > 0 else -1 if p.edge_signed < 0 else 0
        qualified = p.edge >= edge_threshold and not p.late_entry and sign != 0
        if not qualified:
            armed = True
            continue

        direction_changed = bool(last_sign and sign != last_sign)
        if (armed or direction_changed) and i - last_idx >= cooldown_sessions:
            selected.append(i)
            last_idx = i
            last_sign = sign
            armed = False
    return selected


def _signed_forward_returns(
    points: list[ReplayPoint], indices: Iterable[int], horizon: int
) -> list[float]:
    out: list[float] = []
    for i in indices:
        if i + horizon >= len(points):
            continue
        base = points[i].ratio
        future = points[i + horizon].ratio
        if base <= 0:
            continue
        raw = future / base - 1.0
        out.append(raw if points[i].edge_signed > 0 else -raw)
    return out


def _metrics(points: list[ReplayPoint], indices: list[int], horizon: int) -> HorizonMetrics:
    returns = _signed_forward_returns(points, indices, horizon)
    return HorizonMetrics(
        horizon_sessions=horizon,
        signals=len(returns),
        hit_rate=(sum(x > 0 for x in returns) / len(returns)) if returns else 0.0,
        avg_signed_return=(sum(returns) / len(returns)) if returns else 0.0,
        median_signed_return=median(returns) if returns else 0.0,
    )


def calibrate_edge_thresholds(
    points: list[ReplayPoint],
    *,
    thresholds: tuple[int, ...] = (50, 55, 60, 65, 70, 75, 80),
    primary_horizon: int = 20,
    train_fraction: float = 0.70,
) -> dict:
    """Exploratory walk-forward threshold report; never mutates settings."""
    if len(points) < 80:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "reason": "Core replay için en az 80 değerlendirme noktası gerekir.",
            "candidates": [],
        }

    split = max(1, min(len(points) - 1, int(len(points) * train_fraction)))
    candidates: list[dict] = []
    for threshold in thresholds:
        train_idx = _select_signal_indices(points, threshold, start=0, end=split)
        test_idx = _select_signal_indices(points, threshold, start=split, end=len(points))
        train = _metrics(points, train_idx, primary_horizon)
        test = _metrics(points, test_idx, primary_horizon)
        ranking_score = (
            train.avg_signed_return * sqrt(max(train.signals, 1))
            + max(0.0, train.hit_rate - 0.5) * 0.02
        )
        candidates.append(
            {
                "edge_threshold": threshold,
                "train": asdict(train),
                "holdout": asdict(test),
                "ranking_score": ranking_score,
            }
        )
    candidates.sort(key=lambda x: x["ranking_score"], reverse=True)
    eligible = [
        x
        for x in candidates
        if x["train"]["signals"] >= 8 and x["holdout"]["signals"] >= 3
    ]
    return {
        "status": "OK" if eligible else "LIMITED_SIGNAL_COUNT",
        "train_fraction": train_fraction,
        "primary_horizon_sessions": primary_horizon,
        "best_candidate": eligible[0] if eligible else None,
        "candidates": candidates,
        "note": (
            "Exploratory only. Derivatives/event point-in-time history eksik olduğu için "
            "bu rapor production threshold'u otomatik değiştirmez."
        ),
    }


def summarize_core_replay(points: list[ReplayPoint], configured_edge: float) -> dict:
    if not points:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "model_version": MODEL_VERSION,
            "observations": 0,
        }
    idx = _select_signal_indices(points, configured_edge)
    horizons = {
        str(h): asdict(_metrics(points, idx, h))
        for h in (5, 20, 60)
    }
    replay_status = "OK" if len(points) >= 365 else "LIMITED_HISTORY"
    return {
        "status": replay_status,
        "model_version": MODEL_VERSION,
        "start_date": points[0].as_of,
        "end_date": points[-1].as_of,
        "observations": len(points),
        "configured_edge_threshold": configured_edge,
        "configured_threshold_metrics": horizons,
        "median_replay_data_quality": median(p.data_quality for p in points),
        "limitations": [
            "Historical derivatives factor excluded: trustworthy point-in-time history unavailable.",
            "Historical event/sentiment factor excluded: trustworthy point-in-time history unavailable.",
            "This validates directional core, not historical production ACTION decisions.",
        ],
    }


def classify_shadow_readiness(stats: dict, criteria: dict | None = None) -> dict:
    criteria = criteria or {
        "min_calendar_days": 30,
        "min_crypto_decision_days": 25,
        "min_ura_decision_days": 20,
        "min_median_data_quality": 80.0,
        "min_job_success_rate": 0.98,
        "realtime_max_age_days": 7,
        "min_ura_holdings_dates": 2,
        "min_ura_breadth_dates": 20,
    }

    waiting: list[str] = []
    blockers: list[str] = []

    if int(stats.get("calendar_days") or 0) < criteria["min_calendar_days"]:
        waiting.append(
            f"Shadow gözlem süresi {stats.get('calendar_days', 0)}/{criteria['min_calendar_days']} gün."
        )
    if int(stats.get("crypto_decision_days") or 0) < criteria["min_crypto_decision_days"]:
        waiting.append(
            f"ETH/BTC karar günü {stats.get('crypto_decision_days', 0)}/{criteria['min_crypto_decision_days']}."
        )
    if int(stats.get("ura_decision_days") or 0) < criteria["min_ura_decision_days"]:
        waiting.append(
            f"URA/USD karar günü {stats.get('ura_decision_days', 0)}/{criteria['min_ura_decision_days']}."
        )

    for system, key in (("ETH/BTC", "crypto_median_quality"), ("URA/USD", "ura_median_quality")):
        value = stats.get(key)
        if value is not None and float(value) < criteria["min_median_data_quality"]:
            blockers.append(
                f"{system} median data quality {float(value):.1f} < {criteria['min_median_data_quality']:.1f}."
            )

    success_rate = float(stats.get("job_success_rate") or 0.0)
    if int(stats.get("job_count") or 0) > 0 and success_rate < criteria["min_job_success_rate"]:
        blockers.append(
            f"Son 7 günlük job başarı oranı {success_rate:.1%} < {criteria['min_job_success_rate']:.1%}."
        )

    rt_age = stats.get("realtime_test_age_days")
    if rt_age is None:
        blockers.append("Başarılı realtime smoke test kaydı yok.")
    elif float(rt_age) > criteria["realtime_max_age_days"]:
        blockers.append(
            f"Realtime smoke test {float(rt_age):.1f} günlük; maksimum {criteria['realtime_max_age_days']} gün."
        )

    if int(stats.get("ura_holdings_dates") or 0) < criteria["min_ura_holdings_dates"]:
        waiting.append(
            f"URA holdings snapshot günü {stats.get('ura_holdings_dates', 0)}/{criteria['min_ura_holdings_dates']}."
        )
    if int(stats.get("ura_breadth_dates") or 0) < criteria["min_ura_breadth_dates"]:
        waiting.append(
            f"URA breadth history {stats.get('ura_breadth_dates', 0)}/{criteria['min_ura_breadth_dates']} gün."
        )

    if waiting:
        status = "NOT_READY"
    elif blockers:
        status = "BLOCKED"
    else:
        status = "READY"

    return {
        "status": status,
        "criteria": criteria,
        "waiting_reasons": waiting,
        "blockers": blockers,
        "stats": stats,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "note": "READY yalnız manuel LIVE değerlendirmesine izin veren bir gate'tir; mode otomatik değiştirilmez.",
    }
