from __future__ import annotations

import math
from datetime import date

from app.models import FactorScore


def _clip(value: float) -> float:
    return max(-100.0, min(100.0, float(value)))


def score_ura_holdings_fundamentals(summary: dict | None) -> FactorScore:
    """Score the ETF holdings/flow proxy without pretending it is uranium spot fundamentals.

    A single holdings snapshot only proves that the source is reachable; it has
    no directional information.  Directional quality starts once a prior
    snapshot exists and we can estimate asset growth net of URA price movement.
    """
    if not summary:
        return FactorScore("fundamentals", 0, 0, {"missing": True, "reason": "URA holdings snapshot yok."})

    current_date = summary.get("current_date")
    previous_date = summary.get("previous_date")
    coverage = float(summary.get("weight_coverage") or 0)
    if not previous_date:
        return FactorScore(
            "fundamentals",
            0,
            0,
            {
                "missing": True,
                "reason": "Directional holdings/flow için en az iki farklı gün snapshot gerekir.",
                "current_date": current_date,
                "weight_coverage": coverage,
                "constituents": summary.get("constituents", 0),
            },
        )

    flow_proxy_pct = float(summary.get("flow_proxy_pct") or 0)
    days = max(1, int(summary.get("days_between") or 1))
    snapshot_age = max(0, int(summary.get("snapshot_age_days") or 0))
    # A few percent of price-adjusted AUM change is already meaningful.  Scale
    # conservatively and reduce quality for stale comparison windows/coverage.
    score = _clip(flow_proxy_pct * 12.0)
    comparison_quality = 100.0 if days <= 7 else (75.0 if days <= 14 else 40.0 if days <= 31 else 0.0)
    freshness_quality = 100.0 if snapshot_age <= 3 else (80.0 if snapshot_age <= 7 else 40.0 if snapshot_age <= 14 else 0.0)
    quality = min(100.0, max(0.0, coverage * 100.0)) * comparison_quality / 100.0 * freshness_quality / 100.0
    return FactorScore(
        "fundamentals",
        score,
        round(quality, 2),
        {
            "proxy": "Global X URA holdings price-adjusted AUM flow",
            "note": "Bu uranium spot arz-talep verisi değildir; ETF holdings/flow proxy'sidir.",
            **summary,
        },
    )


def score_ura_breadth(row: dict | None, reference_date: str | None = None) -> FactorScore:
    if not row:
        return FactorScore("breadth", 0, 0, {"missing": True, "reason": "URA constituent breadth henüz üretilemedi."})
    quality = float(row.get("quality") or 0)
    if reference_date and row.get("breadth_date"):
        ref = date.fromisoformat(str(reference_date)[:10])
        breadth_date = row["breadth_date"] if isinstance(row["breadth_date"], date) else date.fromisoformat(str(row["breadth_date"])[:10])
        age = max(0, (ref - breadth_date).days)
        freshness = 100.0 if age <= 3 else (80.0 if age <= 7 else 40.0 if age <= 14 else 0.0)
        quality = quality * freshness / 100.0
    if quality <= 0:
        return FactorScore("breadth", 0, 0, {"missing": True, "reason": "Breadth history yetersiz.", **(row.get("details") or {})})

    components: list[float] = []
    for key in ("pct_above_20dma", "pct_above_50dma", "pct_above_200dma", "pct_positive_day", "new_20d_high_pct"):
        value = row.get(key)
        if value is None:
            continue
        # Values are stored as 0..1 fractions.  50% is neutral for most breadth
        # measures; new highs gets a gentler scaling because its baseline is low.
        v = float(value)
        if key == "new_20d_high_pct":
            components.append(_clip((v - 0.10) * 160.0))
        else:
            components.append(_clip((v - 0.50) * 140.0))
    score = sum(components) / len(components) if components else 0.0
    return FactorScore("breadth", _clip(score), round(quality, 2), {"breadth_date": str(row.get("breadth_date")), **(row.get("details") or {})})



def sec_monitor_quality_from_weight(matched_weight: float, scope_cap: float = 70.0) -> float:
    """Quality credit for SEC-only monitoring based on actual fund weight coverage.

    `matched_weight` is the sum of URA portfolio weights whose ticker can be
    mapped exactly to an SEC entity. SEC filings are only one event source, so
    even perfect holdings coverage is capped below 100 until broader official
    event/news sources are implemented.
    """
    coverage_pct = max(0.0, min(100.0, float(matched_weight) * 100.0))
    return round(min(float(scope_cap), coverage_pct), 2)

def score_event_monitor(health: dict | None, recent_events: list[dict]) -> FactorScore:
    """Differentiate 'checked and quiet' from 'not monitored'.

    SEC filing ingestion currently records filings as neutral events.  A future
    semantic classifier may populate severity/surprise.  Until then, successful
    monitoring deserves data quality but never invents directional edge.
    """
    if not health or str(health.get("status") or "").upper() not in {"OK", "DEGRADED"}:
        return FactorScore("event", 0, 0, {"missing": True, "reason": "Event collector freshness doğrulanamadı."})

    details = health.get("details") or {}
    raw_quality = details.get("quality")
    quality = float(raw_quality) if raw_quality is not None else (90.0 if str(health.get("status")).upper() == "OK" else 60.0)
    quality = max(0.0, min(100.0, quality))
    if quality <= 0:
        return FactorScore("event", 0, 0, {"missing": True, "reason": "Event collector çalıştı ancak doğrulanmış entity coverage yok."})
    scored = [e for e in recent_events if float(e.get("severity") or 0) != 0]
    if not scored:
        return FactorScore("event", 0, quality, {"monitored": True, "recent_events": len(recent_events), "directional_events": 0})

    weighted = 0.0
    weight = 0.0
    for event in scored:
        cred = max(0.0, min(100.0, float(event.get("credibility") or 0))) / 100.0
        weighted += float(event.get("severity") or 0) * cred
        weight += cred
    return FactorScore("event", _clip(weighted / max(weight, 1e-9)), quality, {"monitored": True, "recent_events": len(recent_events), "directional_events": len(scored)})
