from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.features.technical import ema, macd, percentile_rank, rsi


@dataclass(slots=True)
class BacktestResult:
    observations: int
    signals: int
    hit_rate: float
    avg_forward_relative_return: float


def ethbtc_baseline(dates: list[str], ratios: list[float], horizon: int = 20) -> BacktestResult:
    """Leakage-resistant baseline using only data available at each point.

    This is intentionally not presented as the production engine backtest because
    derivatives/macro/event histories require point-in-time datasets. It is a
    sanity check for the technical/value core.
    """
    e10=ema(ratios,10); e21=ema(ratios,21); ml,ms,_=macd(ratios); rr=rsi(ratios)
    hits=[]; returns=[]; signals=0
    for i in range(80,len(ratios)-horizon):
        history=ratios[max(0,i-36*30):i+1]
        p=percentile_rank(history,ratios[i])
        bull=e10[i]>e21[i] and ml[i]>ms[i] and rr[i]>=45 and p<=0.35
        bear=e10[i]<e21[i] and ml[i]<ms[i] and rr[i]<=55 and p>=0.65
        if not (bull or bear): continue
        signals+=1; forward=ratios[i+horizon]/ratios[i]-1
        signed=forward if bull else -forward
        returns.append(signed); hits.append(signed>0)
    return BacktestResult(len(ratios),signals,(sum(hits)/len(hits) if hits else 0.0),(mean(returns) if returns else 0.0))
