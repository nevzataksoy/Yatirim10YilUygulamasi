from __future__ import annotations

from collections import defaultdict
from statistics import fmean

from app.features.technical import atr, bollinger, cross_age, ema, macd, percentile_rank, realized_vol, rsi, slope_pct, zscore
from app.models import PriceBar


def _common_ratio(btc: list[PriceBar], eth: list[PriceBar]) -> tuple[list[str], list[float], list[float], list[float]]:
    emap={x.date:x for x in eth}; dates=[]; ratio=[]; btc_close=[]; eth_close=[]
    for b in btc:
        e=emap.get(b.date)
        if e:
            dates.append(b.date); ratio.append(e.close/b.close); btc_close.append(b.close); eth_close.append(e.close)
    return dates, ratio, btc_close, eth_close


def _monthly(values: list[tuple[str,float]]) -> list[float]:
    groups=defaultdict(list)
    for d,v in values: groups[d[:7]].append((d,v))
    return [sorted(rows)[-1][1] for _,rows in sorted(groups.items())][:-1]


def crypto_features(btc: list[PriceBar], eth: list[PriceBar]) -> dict[str, dict]:
    dates, ratio, bc, ec = _common_ratio(btc,eth)
    if len(ratio)<80: raise ValueError("ETH/BTC feature için veri yetersiz.")
    e10,e21=ema(ratio,10),ema(ratio,21); ml,ms,mh=macd(ratio); rr=rsi(ratio); bb=bollinger(ratio)
    monthly=_monthly(list(zip(dates,ratio))); weekly=[ratio[i] for i in range(6,len(ratio),7)]
    if len(monthly) < 36 or len(weekly) < 52:
        raise ValueError(f"ETH/BTC uzun dönem feature verisi yetersiz: monthly={len(monthly)}, weekly={len(weekly)}")
    btc_atr=atr([x.high for x in btc[-80:]],[x.low for x in btc[-80:]],[x.close for x in btc[-80:]])[-1]/btc[-1].close
    eth_atr=atr([x.high for x in eth[-80:]],[x.low for x in eth[-80:]],[x.close for x in eth[-80:]])[-1]/eth[-1].close
    bmap={x.date:x for x in btc}; emap={x.date:x for x in eth}
    common=[d for d in dates if d in bmap and d in emap]
    recent=common[-20:]
    if len(recent) < 20:
        raise ValueError("ETH/BTC relative volume için 20 ortak gün bulunamadı.")
    btc_notional=[bmap[d].volume*bmap[d].close for d in recent]
    eth_notional=[emap[d].volume*emap[d].close for d in recent]
    btc_rvol=btc_notional[-1]/max(fmean(btc_notional),1e-9)
    eth_rvol=eth_notional[-1]/max(fmean(eth_notional),1e-9)
    relative_rvol=eth_rvol/max(btc_rvol,1e-9)
    return {
        "ratio": {"value":ratio[-1],"quality":100},
        "percentile_36m":{"value":percentile_rank(monthly[-36:],ratio[-1]),"quality":100},
        "zscore_52w":{"value":zscore(weekly[-52:],ratio[-1]),"quality":100},
        "ema10":{"value":float(e10[-1]),"quality":100}, "ema21":{"value":float(e21[-1]),"quality":100},
        "ema_cross_age_bull":{"value":cross_age(e10,e21,True),"quality":100},
        "ema_cross_age_bear":{"value":cross_age(e10,e21,False),"quality":100},
        "ema21_slope_5d":{"value":slope_pct(e21,5),"quality":100},
        "macd":{"value":float(ml[-1]),"quality":100}, "macd_signal":{"value":float(ms[-1]),"quality":100},
        "macd_hist":{"value":float(mh[-1]),"quality":100},
        "macd_cross_age_bull":{"value":cross_age(ml,ms,True),"quality":100},
        "macd_cross_age_bear":{"value":cross_age(ml,ms,False),"quality":100},
        "rsi14":{"value":float(rr[-1]),"quality":100},
        "bb_percent_b":{"value":float(bb['percent_b'][-1]),"quality":100}, "bb_width":{"value":float(bb['width'][-1]),"quality":100},
        "rv20":{"value":realized_vol(ratio,20),"quality":100}, "rv60":{"value":realized_vol(ratio,60),"quality":100},
        "btc_atr_pct":{"value":float(btc_atr),"quality":100}, "eth_atr_pct":{"value":float(eth_atr),"quality":100},
        "btc_notional_rvol20":{"value":float(btc_rvol),"quality":85},
        "eth_notional_rvol20":{"value":float(eth_rvol),"quality":85},
        "relative_rvol_eth_btc":{"value":float(relative_rvol),"quality":85},
        "as_of":{"value":dates[-1],"quality":100},
    }


def ura_features(daily: list[PriceBar], weekly: list[PriceBar], monthly: list[PriceBar]) -> dict[str,dict]:
    if len(daily)<60: raise ValueError("URA günlük veri yetersiz.")
    if len(weekly)<52 or len(monthly)<36:
        raise ValueError(f"URA uzun dönem veri yetersiz: weekly={len(weekly)}, monthly={len(monthly)}")
    c=[x.close for x in daily]; e10,e21=ema(c,10),ema(c,21); ml,ms,mh=macd(c); rr=rsi(c); bb=bollinger(c)
    a=atr([x.high for x in daily],[x.low for x in daily],c)[-1]/c[-1]
    return {
        "price":{"value":c[-1],"quality":100},
        "percentile_36m":{"value":percentile_rank([x.close for x in monthly[-36:]],c[-1]),"quality":100},
        "zscore_52w":{"value":zscore([x.close for x in weekly[-52:]],c[-1]),"quality":100},
        "ema10":{"value":float(e10[-1]),"quality":100}, "ema21":{"value":float(e21[-1]),"quality":100},
        "ema_cross_age_bull":{"value":cross_age(e10,e21,True),"quality":100}, "ema_cross_age_bear":{"value":cross_age(e10,e21,False),"quality":100},
        "ema21_slope_5d":{"value":slope_pct(e21,5),"quality":100},
        "macd":{"value":float(ml[-1]),"quality":100}, "macd_signal":{"value":float(ms[-1]),"quality":100}, "macd_hist":{"value":float(mh[-1]),"quality":100},
        "rsi14":{"value":float(rr[-1]),"quality":100}, "bb_percent_b":{"value":float(bb['percent_b'][-1]),"quality":100}, "bb_width":{"value":float(bb['width'][-1]),"quality":100},
        "atr_pct":{"value":float(a),"quality":100}, "rv20":{"value":realized_vol(c,20,252),"quality":100}, "rv60":{"value":realized_vol(c,60,252),"quality":100},
        "volume_rvol20":{"value":daily[-1].volume/max(fmean([x.volume for x in daily[-20:]]),1e-9),"quality":100},
        "as_of":{"value":daily[-1].date,"quality":100},
    }
