from __future__ import annotations


def risk_and_size(features: dict[str,dict], confidence: float, base_pct: float, max_pct: float) -> tuple[float,float,dict]:
    rv20=float(features.get("rv20",{}).get("value",0.6) or 0.6); rv60=float(features.get("rv60",{}).get("value",0.6) or 0.6)
    vol_ratio=rv20/max(rv60,1e-9)
    risk=max(0,min(100,50+(vol_ratio-1)*50))
    confidence_factor=max(0.4,min(1.0,confidence/90))
    vol_factor=max(0.35,min(1.0,1/max(vol_ratio,0.7)))
    size=min(max_pct,base_pct*confidence_factor*vol_factor)
    return risk,size,{"vol_ratio":vol_ratio,"confidence_factor":confidence_factor,"vol_factor":vol_factor}
