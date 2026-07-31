from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime

from app.http import build_session


@dataclass(slots=True)
class UraHolding:
    holding_date: str
    ticker: str
    name: str
    weight: float
    shares: float
    market_value: float
    market_price: float
    source_url: str


@dataclass(slots=True)
class UraHoldingsSnapshot:
    holding_date: str
    source_url: str
    holdings: list[UraHolding]


class GlobalXUraHoldingsCollector:
    """Fetch the official Global X URA full-holdings CSV.

    The fund page exposes a dated CSV link.  We discover that link on every
    refresh instead of hard-coding an address that becomes stale the next day.
    A user supplied CSV URL can still override discovery for troubleshooting.
    """

    FUND_PAGE = "https://www.globalxetfs.com/funds/ura"
    CSV_RE = re.compile(
        r"https://assets\.globalxetfs\.com/funds/holdings/ura_full-holdings_\d{8}\.csv",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.session = build_session("RosaInvestmentEngine/1.1.4")
        self.session.headers.update({"Accept": "text/csv,text/html;q=0.9,*/*;q=0.8"})

    def discover_csv_url(self) -> str:
        response = self.session.get(self.FUND_PAGE, timeout=30)
        response.raise_for_status()
        match = self.CSV_RE.search(response.text)
        if not match:
            # Some frontend builds escape slashes in embedded JSON.
            normalized = response.text.replace("\\/", "/")
            match = self.CSV_RE.search(normalized)
        if not match:
            raise RuntimeError("Global X URA full-holdings CSV bağlantısı bulunamadı.")
        return match.group(0)

    def fetch(self, override_url: str = "") -> UraHoldingsSnapshot:
        url = override_url.strip() or self.discover_csv_url()
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return self.parse_csv(response.text, url)

    @staticmethod
    def _number(value: str | None) -> float:
        text = (value or "").strip().replace(",", "")
        if not text:
            return 0.0
        return float(text)

    @classmethod
    def parse_csv(cls, text: str, source_url: str = "") -> UraHoldingsSnapshot:
        lines = text.replace("\ufeff", "").splitlines()
        if len(lines) < 3:
            raise RuntimeError("Global X URA holdings CSV beklenen yapıda değil.")
        date_match = re.search(r"as of\s+(\d{1,2}/\d{1,2}/\d{4})", lines[1], re.IGNORECASE)
        if not date_match:
            raise RuntimeError("Global X URA holdings tarihi bulunamadı.")
        holding_date = datetime.strptime(date_match.group(1), "%m/%d/%Y").date().isoformat()

        reader = csv.DictReader(io.StringIO("\n".join(lines[2:])))
        holdings: list[UraHolding] = []
        for row in reader:
            ticker = (row.get("Ticker") or "").strip()
            name = (row.get("Name") or "").strip()
            # Cash/currency rows have no ticker and are not constituents.
            if not ticker:
                continue
            weight_pct = cls._number(row.get("% of Net Assets"))
            shares = cls._number(row.get("Shares Held"))
            market_value = cls._number(row.get("Market Value ($)"))
            market_price = cls._number(row.get("Market Price ($)"))
            holdings.append(
                UraHolding(
                    holding_date=holding_date,
                    ticker=ticker,
                    name=name,
                    weight=weight_pct / 100.0,
                    shares=shares,
                    market_value=market_value,
                    market_price=market_price,
                    source_url=source_url,
                )
            )
        if not holdings:
            raise RuntimeError("Global X URA holdings CSV içinde constituent bulunamadı.")
        return UraHoldingsSnapshot(holding_date, source_url, holdings)
