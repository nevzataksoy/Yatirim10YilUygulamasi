from __future__ import annotations

from app.http import build_session


class FredRealtimeHistoryUnavailable(RuntimeError):
    """Raised when a FRED series has no historical ALFRED representation."""


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

    @staticmethod
    def _raise_for_status_safe(
        response,
        series_id: str,
        *,
        realtime_history: bool = False,
    ) -> None:
        """Raise an error without exposing the API key embedded in request URLs."""
        try:
            response.raise_for_status()
        except Exception:
            message = ""
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = str(
                        payload.get("error_message")
                        or payload.get("message")
                        or ""
                    ).strip()
            except Exception:
                message = ""
            status = getattr(response, "status_code", None)
            prefix = f"HTTP {status}" if status is not None else "HTTP request"
            detail = f": {message}" if message else ""
            safe_message = f"FRED {series_id} isteği başarısız ({prefix}){detail}"
            if (
                realtime_history
                and status == 400
                and "does not exist in ALFRED" in message
            ):
                raise FredRealtimeHistoryUnavailable(safe_message) from None
            raise RuntimeError(safe_message) from None

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
        self._raise_for_status_safe(response, series_id)
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
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> list[dict]:
        """Fetch ALFRED real-time intervals needed by a validation window.

        FRED ``output_type=1`` returns observations by real-time period. For
        strict historical validation we only need the revisions that could have
        been visible during the replay window. Requesting the entire FRED
        real-time history from 1776 to 9999 can exceed FRED's JSON vintage-date
        limits for long-lived daily series, so the real-time period defaults to
        the requested observation window.

        The returned validity intervals may therefore be clipped to the requested
        real-time boundaries, which is sufficient for replay dates inside those
        same boundaries.

        Some FRED series have no ALFRED historical representation. That case is
        reported with ``FredRealtimeHistoryUnavailable`` so verification can mark
        the series as historically unprovable instead of substituting today's
        value into the past.

        The production macro job does not call this method. It exists for
        Post-Shadow PIT verification and performs no database writes.
        """
        limit = 100000
        offset = 0
        raw_rows: list[dict] = []
        rt_start = realtime_start or observation_start
        rt_end = realtime_end or observation_end

        while True:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "realtime_start": rt_start,
                "realtime_end": rt_end,
                "observation_start": observation_start,
                "observation_end": observation_end,
                "output_type": 1,
                "sort_order": "asc",
                "limit": limit,
                "offset": offset,
            }
            response = self.session.get(self.BASE, params=params, timeout=30)
            self._raise_for_status_safe(
                response,
                series_id,
                realtime_history=True,
            )
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
