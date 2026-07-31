from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean

from app.http import build_session


class DeribitCollector:
    BASE = "https://www.deribit.com/api/v2"

    def __init__(self) -> None:
        self.session = build_session(total_retries=0, connect_retries=0, read_retries=0, backoff_factor=0.0)

    def _get(self, method: str, **params) -> dict:
        r = self.session.get(f"{self.BASE}/{method}", params=params, timeout=(5, 15))
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Deribit: {data['error']}")
        return data.get("result")

    def fetch_snapshot(self, currency: str) -> dict:
        perp = self._get("public/ticker", instrument_name=f"{currency}-PERPETUAL")
        options = self._get("public/get_book_summary_by_currency", currency=currency, kind="option") or []
        option_oi = sum(float(x.get("open_interest") or 0) for x in options)
        option_volume = sum(float(x.get("volume") or 0) for x in options)
        ivs = [float(x["mark_iv"]) for x in options if x.get("mark_iv") is not None]
        index_price = float(perp.get("index_price") or 0)
        mark_price = float(perp.get("mark_price") or 0)
        basis_pct = ((mark_price / index_price) - 1) * 100 if index_price else 0.0
        return {
            "venue": "deribit",
            "ts": datetime.now(timezone.utc).isoformat(),
            "currency": currency,
            "instrument": f"{currency}-PERPETUAL",
            "open_interest": float(perp.get("open_interest") or 0),
            "mark_price": mark_price,
            "index_price": index_price,
            "basis_pct": basis_pct,
            "funding_8h": float(perp.get("funding_8h") or 0),
            "current_funding": float(perp.get("current_funding") or 0),
            "best_bid": float(perp.get("best_bid_price") or 0),
            "best_ask": float(perp.get("best_ask_price") or 0),
            "option_open_interest": option_oi,
            "option_volume_24h": option_volume,
            "option_mark_iv_mean": fmean(ivs) if ivs else None,
        }
