from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import quote

from app.http import build_session


class SecCollector:
    BASE = "https://data.sec.gov/submissions"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

    def __init__(self, user_agent: str) -> None:
        self.session = build_session(user_agent, total_retries=3, backoff_factor=0.8)
        self.session.headers.update({"Accept-Encoding": "gzip, deflate", "Accept": "application/json"})

    def fetch_ticker_map(self) -> dict[str, dict]:
        response = self.session.get(self.TICKERS_URL, timeout=30)
        response.raise_for_status()
        payload = response.json()
        out: dict[str, dict] = {}
        for item in payload.values():
            ticker = str(item.get("ticker") or "").upper().strip()
            cik = item.get("cik_str")
            if not ticker or cik is None:
                continue
            out[ticker] = {
                "ticker": ticker,
                "cik": str(cik).zfill(10),
                "title": str(item.get("title") or "").strip(),
            }
        return out

    def fetch_recent_filings(self, cik: str, forms: set[str] | None = None) -> list[dict]:
        normalized = str(cik).zfill(10)
        response = self.session.get(f"{self.BASE}/CIK{normalized}.json", timeout=30)
        response.raise_for_status()
        recent = response.json().get("filings", {}).get("recent", {})
        out = []
        count = len(recent.get("accessionNumber", []))
        for i in range(count):
            form = recent.get("form", [""] * count)[i]
            if forms and form not in forms:
                continue
            accession = recent.get("accessionNumber", [""] * count)[i]
            accession_compact = str(accession).replace("-", "")
            primary_document = recent.get("primaryDocument", [None] * count)[i]
            cik_compact = str(int(normalized))
            filing_url = (
                f"{self.ARCHIVES_BASE}/{quote(cik_compact)}/{quote(accession_compact)}/{quote(str(primary_document))}"
                if accession and primary_document
                else ""
            )
            accepted = recent.get("acceptanceDateTime", [None] * count)[i]
            filing_date = recent.get("filingDate", [None] * count)[i]
            occurred_at = accepted or (f"{filing_date}T00:00:00Z" if filing_date else None)
            out.append({
                "cik": normalized,
                "accession": accession,
                "filing_date": filing_date,
                "report_date": recent.get("reportDate", [None] * count)[i],
                "accepted_at": accepted,
                "occurred_at": occurred_at,
                "form": form,
                "primary_document": primary_document,
                "url": filing_url,
            })
        return out

    @staticmethod
    def is_recent(filing: dict, days: int, reference: date | None = None) -> bool:
        raw = filing.get("filing_date")
        if not raw:
            return False
        try:
            filing_date = date.fromisoformat(str(raw)[:10])
        except ValueError:
            return False
        ref = reference or datetime.now(timezone.utc).date()
        age = (ref - filing_date).days
        return 0 <= age <= days
