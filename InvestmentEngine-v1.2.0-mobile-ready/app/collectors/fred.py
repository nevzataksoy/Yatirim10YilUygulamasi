from __future__ import annotations

from app.http import build_session


class FredCollector:
    BASE = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = build_session()

    @staticmethod
    def _normalize_rows(series_id: str, rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        for row in rows:
            value = row.get("value")
            if value in (None, "."):
                continue
            realtime_end = row.get("realtime_end")
            if realtime_end in (None, ".", ""):
                realtime_end = None
            out.append(
                {
                    "series_id": series_id,
                    "date": row["date"],
                    "value": float(value),
                    "realtime_start": row.get("realtime_start"),
                    "realtime_end": realtime_end,
                }
            )
        return out

    def fetch_series(self, series_id: str, limit: int = 1500) -> list[dict]:
        """Fetch the latest observations and return them oldest -> newest.

        FRED defaults to ascending order. Using ascending order together with a
        finite limit can silently return the *oldest* observations of long-lived
        daily series. We request descending data so the limit always applies to
        the most recent history, then sort locally for deterministic persistence.

        This method intentionally keeps the released production behavior: with
        no real-time period supplied, FRED returns the current real-time view.
        Strict historical validation uses ``fetch_realtime_history`` instead.
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
        out = self._normalize_rows(series_id, data.get("observations", []))
        out.sort(key=lambda item: item["date"])
        return out

    def fetch_realtime_history(
        self,
        series_id: str,
        *,
        observation_start: str,
        observation_end: str,
    ) -> list[dict]:
        """Fetch complete ALFRED real-time intervals for a validation window.

        FRED ``output_type=1`` returns observations by real-time period. Using
        the complete real-time bounds exposes the historical validity interval
        for every revision instead of returning only today's FRED view.

        The production macro job does not call this method. It exists for
        Post-Shadow PIT verification and performs no database writes.
        """
        limit = 100000
        offset = 0
        raw_rows: list[dict] = []

        while True:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "realtime_start": "1776-07-04",
                "realtime_end": "9999-12-31",
                "observation_start": observation_start,
                "observation_end": observation_end,
                "output_type": 1,
                "sort_order": "asc",
                "limit": limit,
                "offset": offset,
            }
            response = self.session.get(self.BASE, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            page = list(data.get("observations", []))
            raw_rows.extend(page)

            count = int(data.get("count") or len(raw_rows))
            offset += len(page)
            if not page or offset >= count:
                break

        out = self._normalize_rows(series_id, raw_rows)
        out.sort(
            key=lambda item: (
                item["date"],
                item.get("realtime_start") or "",
                item.get("realtime_end") or "9999-12-31",
            )
        )
        return out
