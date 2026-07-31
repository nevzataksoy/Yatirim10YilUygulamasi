from __future__ import annotations

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from app.backtest.baseline import ethbtc_baseline
from app.collectors.crypto import CryptoCollector

bundle=CryptoCollector().fetch(1600)
emap={x.date:x for x in bundle.eth}; dates=[]; ratios=[]
for b in bundle.btc:
    e=emap.get(b.date)
    if e: dates.append(b.date); ratios.append(e.close/b.close)
r=ethbtc_baseline(dates,ratios)
print(f"Observations: {r.observations}")
print(f"Signals: {r.signals}")
print(f"Hit rate: {r.hit_rate:.2%}")
print(f"Avg 20D signed relative return: {r.avg_forward_relative_return:.2%}")
print("NOT: Bu yalnız teknik/value baseline sanity check'tir; full production feature backtest değildir.")
