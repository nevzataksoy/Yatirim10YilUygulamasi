from __future__ import annotations

import math
from statistics import fmean, pstdev
from typing import Sequence

import numpy as np


def _arr(values: Sequence[float]) -> np.ndarray:
    a = np.asarray(values, dtype=float)
    if a.size == 0 or np.isnan(a).all():
        raise ValueError("Gösterge için veri yok.")
    return a


def ema(values: Sequence[float], period: int) -> np.ndarray:
    a = _arr(values); out = np.empty_like(a); alpha = 2.0 / (period + 1.0); out[0] = a[0]
    for i in range(1, len(a)): out[i] = alpha * a[i] + (1-alpha) * out[i-1]
    return out


def macd(values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    line = ema(values, fast) - ema(values, slow); sig = ema(line, signal); return line, sig, line-sig


def rsi(values: Sequence[float], period: int = 14) -> np.ndarray:
    a = _arr(values); out = np.full_like(a, np.nan)
    if len(a) <= period: return out
    diff = np.diff(a); gains = np.maximum(diff, 0); losses = np.maximum(-diff, 0)
    avg_gain = gains[:period].mean(); avg_loss = losses[:period].mean()
    out[period] = 100 if avg_loss == 0 else 100 - 100/(1 + avg_gain/avg_loss)
    for i in range(period+1, len(a)):
        avg_gain = (avg_gain*(period-1)+gains[i-1])/period
        avg_loss = (avg_loss*(period-1)+losses[i-1])/period
        out[i] = 100 if avg_loss == 0 else 100 - 100/(1 + avg_gain/avg_loss)
    return out


def atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int = 14) -> np.ndarray:
    h,l,c = _arr(high),_arr(low),_arr(close); tr = np.empty_like(c); tr[0] = h[0]-l[0]
    for i in range(1,len(c)): tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    return ema(tr, period)


def bollinger(values: Sequence[float], period: int = 20, mult: float = 2.0) -> dict[str,np.ndarray]:
    a = _arr(values); mid=np.full_like(a,np.nan); upper=np.full_like(a,np.nan); lower=np.full_like(a,np.nan)
    pb=np.full_like(a,np.nan); width=np.full_like(a,np.nan)
    for i in range(period-1,len(a)):
        w=a[i-period+1:i+1]; m=float(w.mean()); s=float(w.std()); u=m+mult*s; lo=m-mult*s
        mid[i]=m; upper[i]=u; lower[i]=lo; pb[i]=0.5 if u==lo else (a[i]-lo)/(u-lo); width[i]=0 if m==0 else (u-lo)/m
    return {"mid":mid,"upper":upper,"lower":lower,"percent_b":pb,"width":width}


def realized_vol(values: Sequence[float], period: int = 20, annualization: int = 365) -> float:
    a=_arr(values)
    if len(a)<period+1: return float("nan")
    returns=np.diff(np.log(a[-(period+1):])); return float(returns.std()*math.sqrt(annualization))


def percentile_rank(values: Sequence[float], current: float) -> float:
    a=[float(x) for x in values if math.isfinite(float(x))]
    if not a: return 0.5
    return sum(x <= current for x in a)/len(a)


def zscore(values: Sequence[float], current: float) -> float:
    a=[float(x) for x in values if math.isfinite(float(x))]
    if len(a)<2: return 0.0
    s=pstdev(a); return 0.0 if s==0 else (current-fmean(a))/s


def cross_age(a: Sequence[float], b: Sequence[float], bullish: bool, max_lookback: int = 30) -> int:
    aa,bb=_arr(a),_arr(b); i=min(len(aa),len(bb))-1
    for age in range(max_lookback+1):
        j=i-age
        if j-1<0: break
        if bullish and aa[j]>bb[j] and aa[j-1]<=bb[j-1]: return age
        if not bullish and aa[j]<bb[j] and aa[j-1]>=bb[j-1]: return age
    return 999


def slope_pct(values: Sequence[float], bars: int = 5) -> float:
    a=_arr(values)
    if len(a)<=bars or a[-bars-1]==0: return 0.0
    return float((a[-1]/a[-bars-1]-1)*100)
