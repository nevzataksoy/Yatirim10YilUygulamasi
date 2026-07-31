from __future__ import annotations

from datetime import date, timedelta
from xml.etree import ElementTree

from app.http import build_session


class TcmbCollector:
    BASE = "https://www.tcmb.gov.tr/kurlar"

    def __init__(self) -> None:
        self.session = build_session()

    def latest_usd_selling(self, ref_date: date | None = None) -> dict:
        ref = ref_date or date.today()
        for back in range(0, 11):
            d = ref - timedelta(days=back)
            url = f"{self.BASE}/{d:%Y%m}/{d:%d%m%Y}.xml"
            r = self.session.get(url, timeout=15)
            if r.status_code != 200:
                continue
            root = ElementTree.fromstring(r.content)
            for node in root.findall("Currency"):
                if node.attrib.get("CurrencyCode") == "USD":
                    value = node.findtext("ForexSelling")
                    if value:
                        return {"date": d.isoformat(), "rate": float(value), "source": url}
        raise RuntimeError("TCMB USD Döviz Satış bulunamadı.")
