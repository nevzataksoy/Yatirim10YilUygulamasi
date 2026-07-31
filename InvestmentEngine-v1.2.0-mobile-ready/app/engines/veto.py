from __future__ import annotations


def evaluate_late_entry(features: dict[str,dict], bullish: bool, max_age: int = 5) -> tuple[bool,list[str]]:
    reasons=[]
    age_key="ema_cross_age_bull" if bullish else "ema_cross_age_bear"
    raw_age=features.get(age_key,{}).get("value",999)
    age=int(raw_age if raw_age is not None else 999)
    rsi=float(features.get("rsi14",{}).get("value",50) or 50)
    pb=float(features.get("bb_percent_b",{}).get("value",0.5) or 0.5)
    p=float(features.get("percentile_36m",{}).get("value",0.5) or 0.5)
    if age>max_age: reasons.append(f"EMA dönüş yaşı {age if age<999 else 'yok'}")
    if bullish and rsi>=68: reasons.append(f"RSI {rsi:.1f} ≥ 68")
    if not bullish and rsi<=32: reasons.append(f"RSI {rsi:.1f} ≤ 32")
    if bullish and pb>0.85: reasons.append(f"%B {pb:.2f} > 0.85")
    if not bullish and pb<0.15: reasons.append(f"%B {pb:.2f} < 0.15")
    if bullish and p>0.45: reasons.append(f"Percentile %{p*100:.1f} > %45")
    if not bullish and p<0.55: reasons.append(f"Percentile %{p*100:.1f} < %55")
    return bool(reasons),reasons
