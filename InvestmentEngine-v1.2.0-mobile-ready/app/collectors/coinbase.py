from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.http import build_session
from app.models import PriceBar


class CoinbaseCollector:
    BASE = "https://api.exchange.coinbase.com"

    def __init__(self) -> None:
        self.session = build_session()

    def fetch_daily(self, product_id: str, days: int = 1300) -> list[PriceBar]:
        end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=days)
        cursor = start
        out: dict[str, PriceBar] = {}
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=280), end)
            params = {
                "granularity": 86400,
                "start": cursor.isoformat().replace("+00:00", "Z"),
                "end": chunk_end.isoformat().replace("+00:00", "Z"),
            }
            r = self.session.get(f"{self.BASE}/products/{product_id}/candles", params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise RuntimeError(f"Coinbase {product_id} candle yanıtı geçersiz.")
            for row in data:
                if not isinstance(row, list) or len(row) < 6:
                    continue
                ts, low, high, open_, close, volume = row[:6]
                dt = datetime.fromtimestamp(float(ts), timezone.utc)
                if dt >= end:
                    continue
                key = dt.date().isoformat()
                out[key] = PriceBar("coinbase", product_id, key, float(open_), float(high), float(low), float(close), float(volume))
            cursor = chunk_end
        rows = sorted(out.values(), key=lambda x: x.date)
        minimum = 1100 if days >= 1100 else max(60, min(days, int(days * 0.85)))
        if len(rows) < minimum:
            raise RuntimeError(f"Coinbase {product_id} için yeterli günlük veri alınamadı: {len(rows)}")
        return rows

    def fetch_level2_book(self, product_id: str) -> dict:
        r = self.session.get(f"{self.BASE}/products/{product_id}/book", params={"level": 2}, timeout=10)
        r.raise_for_status()
        return r.json()
