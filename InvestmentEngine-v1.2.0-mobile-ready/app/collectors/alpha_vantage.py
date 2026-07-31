from __future__ import annotations

import threading
import time

from app.http import build_session
from app.models import PriceBar


class AlphaVantageCollector:
    BASE = "https://www.alphavantage.co/query"
    # Free keys currently ask clients to keep burst rate to roughly one request
    # per second. Use a little margin so daily/weekly/monthly calls do not race.
    MIN_REQUEST_INTERVAL_SECONDS = 1.25

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = build_session()
        self._rate_lock = threading.Lock()
        self._last_request_at = 0.0

    def _wait_for_slot(self) -> None:
        with self._rate_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait = self.MIN_REQUEST_INTERVAL_SECONDS - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def _request_once(self, function: str, symbol: str) -> dict:
        self._wait_for_slot()
        params = {"function": function, "symbol": symbol, "apikey": self.api_key}
        r = self.session.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _request(self, function: str, symbol: str) -> dict:
        data = self._request_once(function, symbol)
        for key in ("Error Message", "Note", "Information"):
            if key not in data:
                continue
            message = str(data[key])
            # Alpha Vantage may reject a burst even though the daily quota is
            # still available. Retry once after an additional pause. If the
            # daily quota is exhausted the second response will still fail and
            # be surfaced instead of looping indefinitely.
            if "1 request per second" in message.lower():
                time.sleep(1.5)
                data = self._request_once(function, symbol)
                if not any(k in data for k in ("Error Message", "Note", "Information")):
                    return data
                message = str(next(data[k] for k in ("Error Message", "Note", "Information") if k in data))
            raise RuntimeError(f"Alpha Vantage: {message}")
        return data

    def fetch_daily(self, symbol: str = "URA") -> list[PriceBar]:
        data = self._request("TIME_SERIES_DAILY", symbol)
        series = data.get("Time Series (Daily)")
        if not isinstance(series, dict):
            raise RuntimeError("Alpha Vantage günlük seri bulunamadı.")
        out = []
        for date, row in series.items():
            out.append(PriceBar(
                "alpha_vantage", symbol, date,
                float(row["1. open"]), float(row["2. high"]), float(row["3. low"]),
                float(row["4. close"]), float(row["5. volume"]),
            ))
        return sorted(out, key=lambda x: x.date)

    def fetch_weekly(self, symbol: str = "URA") -> list[PriceBar]:
        return self._parse_ohlcv(self._request("TIME_SERIES_WEEKLY", symbol), "Weekly Time Series", symbol)

    def fetch_monthly(self, symbol: str = "URA") -> list[PriceBar]:
        return self._parse_ohlcv(self._request("TIME_SERIES_MONTHLY", symbol), "Monthly Time Series", symbol)

    @staticmethod
    def _parse_ohlcv(data: dict, key: str, symbol: str) -> list[PriceBar]:
        series = data.get(key)
        if not isinstance(series, dict):
            raise RuntimeError(f"Alpha Vantage {key} bulunamadı.")
        out = []
        for date, row in series.items():
            out.append(PriceBar(
                "alpha_vantage", symbol, date,
                float(row["1. open"]), float(row["2. high"]), float(row["3. low"]),
                float(row["4. close"]), float(row.get("5. volume", 0.0)),
            ))
        return sorted(out, key=lambda x: x.date)
