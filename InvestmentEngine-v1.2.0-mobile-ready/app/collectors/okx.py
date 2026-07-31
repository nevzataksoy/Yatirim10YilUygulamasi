from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.http import build_session


class OkxCollector:
    """Public OKX derivatives market-data collector.

    The engine uses linear BTC-USDT-SWAP / ETH-USDT-SWAP instruments and keeps
    BTC+ETH on the same venue.  No API credentials are required for these
    public endpoints.
    """

    BASE = "https://www.okx.com"

    def __init__(self) -> None:
        self.session = build_session(
            total_retries=1,
            connect_retries=1,
            read_retries=1,
            backoff_factor=0.4,
        )

    def _get(self, path: str, **params: Any) -> list[dict[str, Any]]:
        response = self.session.get(
            f"{self.BASE}{path}", params=params, timeout=(8, 20)
        )
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("code", "")) != "0":
            raise RuntimeError(
                f"OKX: code={payload.get('code')} msg={payload.get('msg', '')}"
            )
        data = payload.get("data") or []
        if not isinstance(data, list):
            raise RuntimeError("OKX: data alanı liste değil.")
        return data

    def _one(self, path: str, **params: Any) -> dict[str, Any]:
        rows = self._get(path, **params)
        if not rows:
            raise RuntimeError(f"OKX: {path} boş sonuç döndürdü.")
        return rows[0]

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        if value in (None, ""):
            return default
        return float(value)

    @staticmethod
    def _iso_from_ms(*values: Any) -> str:
        timestamps: list[int] = []
        for value in values:
            try:
                if value not in (None, ""):
                    timestamps.append(int(value))
            except (TypeError, ValueError):
                pass
        if not timestamps:
            return datetime.now(timezone.utc).isoformat()
        return datetime.fromtimestamp(max(timestamps) / 1000, timezone.utc).isoformat()

    @staticmethod
    def _normalize_funding_8h(row: dict[str, Any]) -> float:
        rate = OkxCollector._float(row.get("fundingRate"))
        try:
            funding_time = int(row.get("fundingTime") or 0)
            next_time = int(row.get("nextFundingTime") or 0)
            hours = (next_time - funding_time) / 3_600_000
            if hours > 0:
                return rate * (8.0 / hours)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        return rate

    def fetch_snapshot(self, currency: str) -> dict[str, Any]:
        currency = currency.upper().strip()
        if currency not in {"BTC", "ETH"}:
            raise ValueError("OKX collector yalnız BTC ve ETH destekler.")

        instrument = f"{currency}-USDT-SWAP"
        index_instrument = f"{currency}-USDT"

        oi = self._one(
            "/api/v5/public/open-interest",
            instType="SWAP",
            instId=instrument,
        )
        funding = self._one(
            "/api/v5/public/funding-rate",
            instId=instrument,
        )
        ticker = self._one("/api/v5/market/ticker", instId=instrument)

        # Mark and index are public endpoints.  If either endpoint changes or is
        # temporarily unavailable, fall back to last/premium without failing the
        # complete provider pair.
        mark: dict[str, Any] = {}
        index: dict[str, Any] = {}
        try:
            mark = self._one(
                "/api/v5/public/mark-price",
                instType="SWAP",
                instId=instrument,
            )
        except Exception:
            mark = {}
        try:
            index = self._one(
                "/api/v5/market/index-tickers",
                instId=index_instrument,
            )
        except Exception:
            index = {}

        mark_price = self._float(mark.get("markPx"), self._float(ticker.get("last")))
        index_price = self._float(index.get("idxPx"))
        premium = self._float(funding.get("premium"))
        if not index_price and mark_price and abs(1.0 + premium) > 1e-12:
            index_price = mark_price / (1.0 + premium)
        basis_pct = (
            ((mark_price / index_price) - 1.0) * 100.0
            if mark_price and index_price
            else premium * 100.0
        )

        oi_usd = self._float(oi.get("oiUsd"))
        if not oi_usd:
            # oiCcy is base-currency exposure.  This is only a fallback for an
            # unexpected response without oiUsd.
            oi_usd = self._float(oi.get("oiCcy")) * (index_price or mark_price)

        return {
            "venue": "okx",
            "ts": self._iso_from_ms(
                oi.get("ts"), funding.get("ts"), ticker.get("ts"), mark.get("ts"), index.get("ts")
            ),
            "currency": currency,
            "instrument": instrument,
            "open_interest": oi_usd,
            "mark_price": mark_price,
            "index_price": index_price,
            "basis_pct": basis_pct,
            "funding_8h": self._normalize_funding_8h(funding),
            "current_funding": self._float(funding.get("fundingRate")),
            "best_bid": self._float(ticker.get("bidPx")),
            "best_ask": self._float(ticker.get("askPx")),
            "option_open_interest": None,
            "option_volume_24h": None,
            "option_mark_iv_mean": None,
            "provider_details": {
                "contract": "linear_usdt_swap",
                "oi_source": "oiUsd",
                "premium": premium,
                "funding_time": funding.get("fundingTime"),
                "next_funding_time": funding.get("nextFundingTime"),
            },
        }
