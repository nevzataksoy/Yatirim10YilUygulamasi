from __future__ import annotations

from app.http import build_session


class FredCollector:
    BASE = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = build_session()

    def fetch_series(self, series_id: str, limit: int = 1500) -> list[dict]:
        """Fetch the latest observations and return them oldest -> newest.

        FRED defaults to ascending order.  Using ascending order together with a
        finite limit can silently return the *oldest* observations of long-lived
        daily series.  We request descending data so the limit always applies to
        the most recent history, then sort locally for deterministic persistence.
        """
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": min(max(int(limit), 1), 100000),
        }
        response = self.session.get(self.BASE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        out = []
        for row in data.get("observations", []):
            value = row.get("value")
            if value in (None, "."):
                continue
            out.append({
                "series_id": series_id,
                "date": row["date"],
                "value": float(value),
                "realtime_start": row.get("realtime_start"),
                "realtime_end": row.get("realtime_end"),
            })
        out.sort(key=lambda item: item["date"])
        return out
