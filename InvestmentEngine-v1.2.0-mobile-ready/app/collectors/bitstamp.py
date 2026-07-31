from __future__ import annotations

from datetime import datetime, timezone

from app.http import build_session
from app.models import PriceBar


class BitstampCollector:
    BASE = "https://www.bitstamp.net/api/v2/ohlc"

    def __init__(self) -> None:
        self.session = build_session()

    def fetch_daily(self, market_symbol: str, days: int = 1300) -> list[PriceBar]:
        today_start = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        end = today_start - 1
        out: dict[str, PriceBar] = {}
        loops = 0
        while len(out) < days and loops < 5:
            loops += 1
            limit = min(1000, days - len(out) + 30)
            params = {"step": 86400, "limit": limit, "end": end, "exclude_current_candle": "true"}
            r = self.session.get(f"{self.BASE}/{market_symbol}/", params=params, timeout=20)
            r.raise_for_status()
            rows = r.json().get("data", {}).get("ohlc", [])
            if not rows:
                break
            earliest = None
            for row in rows:
                ts = int(row["timestamp"])
                if ts >= today_start:
                    continue
                dt = datetime.fromtimestamp(ts, timezone.utc)
                key = dt.date().isoformat()
                out[key] = PriceBar(
                    "bitstamp", market_symbol.upper(), key,
                    float(row["open"]), float(row["high"]), float(row["low"]),
                    float(row["close"]), float(row.get("volume", 0.0)),
                )
                earliest = ts if earliest is None else min(earliest, ts)
            if earliest is None:
                break
            end = earliest - 1
        rows = sorted(out.values(), key=lambda x: x.date)[-days:]
        minimum = 1100 if days >= 1100 else max(60, min(days, int(days * 0.85)))
        if len(rows) < minimum:
            raise RuntimeError(f"Bitstamp {market_symbol} için yeterli veri alınamadı: {len(rows)}")
        return rows
