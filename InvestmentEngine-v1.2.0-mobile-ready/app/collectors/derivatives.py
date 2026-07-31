from __future__ import annotations

from dataclasses import dataclass

from app.collectors.deribit import DeribitCollector
from app.collectors.okx import OkxCollector


@dataclass(slots=True)
class DerivativesPair:
    provider: str
    btc: dict
    eth: dict
    fallback_used: bool
    errors: dict[str, str]


class DerivativesCollector:
    """Fetch BTC and ETH derivatives atomically from one venue."""

    def __init__(
        self,
        deribit: DeribitCollector | None = None,
        okx: OkxCollector | None = None,
    ) -> None:
        self.providers = {
            "deribit": deribit or DeribitCollector(),
            "okx": okx or OkxCollector(),
        }

    def fetch_pair(self, mode: str = "auto") -> DerivativesPair:
        mode = (mode or "auto").strip().lower()
        if mode not in {"auto", "deribit", "okx"}:
            raise ValueError(f"Derivatives provider geçersiz: {mode}")

        order = ["deribit", "okx"] if mode == "auto" else [mode]
        errors: dict[str, str] = {}
        for index, provider in enumerate(order):
            collector = self.providers[provider]
            try:
                btc = collector.fetch_snapshot("BTC")
                eth = collector.fetch_snapshot("ETH")
                if btc.get("venue") != provider or eth.get("venue") != provider:
                    raise RuntimeError("Provider etiketi beklenen değerle eşleşmiyor.")
                return DerivativesPair(
                    provider=provider,
                    btc=btc,
                    eth=eth,
                    fallback_used=index > 0,
                    errors=errors,
                )
            except Exception as exc:
                errors[provider] = str(exc)

        message = "; ".join(f"{key}: {value}" for key, value in errors.items())
        raise RuntimeError(f"Derivatives provider kullanılamıyor — {message}")
