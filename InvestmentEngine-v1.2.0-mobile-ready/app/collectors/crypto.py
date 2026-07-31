from __future__ import annotations

from dataclasses import dataclass

from app.collectors.bitstamp import BitstampCollector
from app.collectors.coinbase import CoinbaseCollector
from app.models import PriceBar


@dataclass(slots=True)
class CryptoBundle:
    provider: str
    btc: list[PriceBar]
    eth: list[PriceBar]
    fallback_reason: str = ""


class CryptoCollector:
    def __init__(self) -> None:
        self.coinbase = CoinbaseCollector()
        self.bitstamp = BitstampCollector()

    @staticmethod
    def _validate_common_history(btc: list[PriceBar], eth: list[PriceBar], days: int) -> None:
        common=len({x.date for x in btc} & {x.date for x in eth})
        minimum=1100 if days >= 1100 else max(60, min(days, int(days * 0.85)))
        if common < minimum:
            raise RuntimeError(f"BTC/ETH ortak günlük veri yetersiz: {common} < {minimum}")

    def fetch(self, days: int = 1300) -> CryptoBundle:
        try:
            btc = self.coinbase.fetch_daily("BTC-USD", days)
            eth = self.coinbase.fetch_daily("ETH-USD", days)
            self._validate_common_history(btc,eth,days)
            return CryptoBundle("coinbase", btc, eth)
        except Exception as exc:
            reason = str(exc)
            btc = self.bitstamp.fetch_daily("btcusd", days)
            eth = self.bitstamp.fetch_daily("ethusd", days)
            self._validate_common_history(btc,eth,days)
            return CryptoBundle("bitstamp", btc, eth, fallback_reason=reason)
