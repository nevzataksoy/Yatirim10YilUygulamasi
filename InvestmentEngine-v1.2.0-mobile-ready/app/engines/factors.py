from __future__ import annotations

import math
from app.models import FactorScore


def _clip(x: float) -> float: return max(-100.0,min(100.0,float(x)))


def score_value(f: dict) -> FactorScore:
    p=float(f["percentile_36m"]["value"]); z=float(f["zscore_52w"]["value"])
    score=(0.5-p)*160 + (-z)*20
    return FactorScore("value",_clip(score),100,{"percentile":p,"zscore":z})


def score_trend(f: dict) -> FactorScore:
    e10=float(f["ema10"]["value"]); e21=float(f["ema21"]["value"]); slope=float(f["ema21_slope_5d"]["value"])
    ratio=(e10/e21-1)*100 if e21 else 0
    score=ratio*350 + slope*12
    return FactorScore("trend",_clip(score),100,{"ema_gap_pct":ratio,"slope_5d_pct":slope})


def score_momentum(f: dict) -> FactorScore:
    r=float(f["rsi14"]["value"]); h=float(f["macd_hist"]["value"]); base=50
    rscore=(r-50)*2.3; scale=max(abs(float(f.get("ratio",f.get("price",{"value":1}))["value"]))*0.001,1e-8)
    hscore=max(-50,min(50,h/scale))
    return FactorScore("momentum",_clip(rscore+hscore),100,{"rsi":r,"macd_hist":h})


def score_volatility(f: dict) -> FactorScore:
    rv20=float(f["rv20"]["value"]); rv60=float(f["rv60"]["value"]); ratio=rv20/max(rv60,1e-9)
    # Direction-neutral risk factor: positive = healthy/moderate, negative = unstable.
    score=60-(ratio-1)*100
    return FactorScore("volatility",_clip(score),100,{"rv20":rv20,"rv60":rv60,"ratio":ratio})


def score_flow(f: dict) -> FactorScore:
    if "relative_rvol_eth_btc" in f:
        v=float(f["relative_rvol_eth_btc"]["value"]); score=math.log(max(v,1e-9))*40
        return FactorScore("flow",_clip(score),80,{
            "relative_rvol_eth_btc":v,
            "btc_notional_rvol20":float(f.get("btc_notional_rvol20",{}).get("value",1)),
            "eth_notional_rvol20":float(f.get("eth_notional_rvol20",{}).get("value",1)),
            "note":"Aynı provider'da USD notional bazlı ETH/BTC relatif hacim proxy'si.",
        })
    rvol=float(f.get("volume_rvol20",{}).get("value",1)); return FactorScore("flow",_clip((rvol-1)*40),70,{"rvol20":rvol})


def score_derivatives(btc: dict | None, eth: dict | None) -> FactorScore:
    if not btc or not eth:
        return FactorScore("derivatives",0,0,{"missing":True})
    btc_venue=str(btc.get("venue") or "")
    eth_venue=str(eth.get("venue") or "")
    if not btc_venue or btc_venue != eth_venue:
        return FactorScore("derivatives",0,0,{
            "missing":True,
            "reason":"BTC ve ETH derivatives snapshot aynı provider'dan değil.",
            "btc_provider":btc_venue,
            "eth_provider":eth_venue,
        })
    funding_diff=(float(eth.get("funding_8h") or 0)-float(btc.get("funding_8h") or 0))*10000
    basis_diff=float(eth.get("basis_pct") or 0)-float(btc.get("basis_pct") or 0)
    # Both collectors normalize open_interest to USD notional before persistence:
    # Deribit inverse perpetuals already report USD amount units; OKX uses oiUsd.
    btc_oi_usd=float(btc.get("open_interest") or 0)
    eth_oi_usd=float(eth.get("open_interest") or 0)
    oi_ratio=eth_oi_usd/max(btc_oi_usd,1e-9)
    crowd_penalty=max(0,funding_diff-1.5)*20
    score=basis_diff*20 + math.log(max(oi_ratio,1e-9))*8 - crowd_penalty
    return FactorScore("derivatives",_clip(score),90,{
        "provider":btc_venue,
        "funding_diff_bps":funding_diff,"basis_diff_pct":basis_diff,
        "btc_oi_usd":btc_oi_usd,"eth_oi_usd":eth_oi_usd,"oi_usd_ratio":oi_ratio,
    })


DAILY_MACRO_SERIES = {"DGS2", "DGS10", "DFII10", "VIXCLS", "DTWEXBGS", "NASDAQCOM", "SP500"}
WEEKLY_MACRO_SERIES = {"STLFSI4"}


def _macro_age_quality(series_id: str, age_days: int) -> float:
    if age_days < 0:
        return 0.0
    if series_id in WEEKLY_MACRO_SERIES:
        if age_days <= 10:
            return 100.0
        if age_days <= 17:
            return 70.0
        if age_days <= 24:
            return 40.0
        return 0.0
    if age_days <= 4:
        return 100.0
    if age_days <= 8:
        return 80.0
    if age_days <= 14:
        return 40.0
    return 0.0


def score_macro(latest: dict, reference_date=None) -> FactorScore:
    """Score macro conditions while explicitly accounting for observation age.

    ``latest`` may be the legacy ``{series_id: value}`` mapping or the richer
    repository mapping ``{series_id: {value, observation_date}}``.  Production
    decisions use the richer form, preventing decades-old observations from
    receiving 100% quality merely because the API request itself succeeded.
    """
    if not latest:
        return FactorScore("macro", 0, 0, {"missing": True})

    from datetime import date, datetime, timezone

    if reference_date is None:
        ref = datetime.now(timezone.utc).date()
    elif isinstance(reference_date, datetime):
        ref = reference_date.date()
    elif isinstance(reference_date, date):
        ref = reference_date
    else:
        ref = date.fromisoformat(str(reference_date)[:10])

    values: dict[str, float] = {}
    dates: dict[str, str | None] = {}
    qualities: dict[str, float] = {}
    expected = sorted(DAILY_MACRO_SERIES | WEEKLY_MACRO_SERIES)

    for series_id in expected:
        item = latest.get(series_id)
        if item is None:
            qualities[series_id] = 0.0
            dates[series_id] = None
            continue
        if isinstance(item, dict):
            raw_value = item.get("value")
            raw_date = item.get("observation_date") or item.get("date")
            if raw_value is None or raw_date is None:
                qualities[series_id] = 0.0
                dates[series_id] = str(raw_date) if raw_date else None
                continue
            obs_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date)[:10])
            age_days = (ref - obs_date).days
            qualities[series_id] = _macro_age_quality(series_id, age_days)
            dates[series_id] = obs_date.isoformat()
            if qualities[series_id] > 0:
                values[series_id] = float(raw_value)
        else:
            # Backward-compatible path used by small unit tests/backtest helpers.
            values[series_id] = float(item)
            dates[series_id] = None
            qualities[series_id] = 100.0

    score = 0.0
    used_components: list[str] = []
    vix = values.get("VIXCLS")
    stress = values.get("STLFSI4")
    real = values.get("DFII10")
    if vix is not None:
        score += max(-40, min(40, (22 - vix) * 2))
        used_components.append("VIXCLS")
    if stress is not None:
        score += max(-30, min(30, -stress * 20))
        used_components.append("STLFSI4")
    if real is not None:
        score += max(-20, min(20, (1.5 - real) * 8))
        used_components.append("DFII10")

    quality = sum(qualities.values()) / len(expected) if expected else 0.0
    stale = [key for key, q in qualities.items() if q <= 0]
    degraded = [key for key, q in qualities.items() if 0 < q < 100]
    return FactorScore(
        "macro",
        _clip(score),
        round(quality, 2),
        {
            "latest": values,
            "observation_dates": dates,
            "freshness_quality": qualities,
            "stale_or_missing": stale,
            "degraded": degraded,
            "used_components": used_components,
            "reference_date": ref.isoformat(),
        },
    )


def neutral(code: str, quality: float, note: str) -> FactorScore:
    return FactorScore(code,0,quality,{"note":note})
