from __future__ import annotations


def detect_regime(technical: dict[str,dict], macro_score: float = 0.0) -> tuple[str,dict,dict]:
    slope=float(technical.get("ema21_slope_5d",{}).get("value",0) or 0)
    rv20=float(technical.get("rv20",{}).get("value",0) or 0)
    rv60=float(technical.get("rv60",{}).get("value",0) or 0)
    trend_strength=min(100,abs(slope)*25)
    vol_ratio=rv20/max(rv60,1e-6)

    # Keep the legacy primary regime codes because factor-weight tables use them,
    # but also persist two explicit axes so a strong downtrend in a risk-on macro
    # environment is not mislabeled in dashboards.
    if macro_score < -35 or vol_ratio > 1.6:
        market_regime="RISK_OFF"
    elif macro_score >= -10:
        market_regime="RISK_ON"
    else:
        market_regime="NEUTRAL"

    if trend_strength > 35:
        trend_regime="STRONG_UPTREND" if slope > 0 else "STRONG_DOWNTREND"
    elif trend_strength < 15:
        trend_regime="FLAT"
    else:
        trend_regime="TRANSITION"

    if market_regime == "RISK_OFF":
        regime="RISK_OFF"
    elif trend_strength > 35 and macro_score >= -10:
        regime="RISK_ON_TREND"
    elif trend_strength < 15 and vol_ratio < 1.15:
        regime="MEAN_REVERSION"
    else:
        regime="NEUTRAL"
    probs={"RISK_ON_TREND":0.1,"MEAN_REVERSION":0.1,"RISK_OFF":0.1,"NEUTRAL":0.1}
    probs[regime]=0.7
    return regime,probs,{"trend_strength":trend_strength,"vol_ratio":vol_ratio,"macro_score":macro_score,"market_regime":market_regime,"trend_regime":trend_regime,"ema21_slope_5d":slope}
