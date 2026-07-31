from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EngineMode = Literal["shadow", "live", "maintenance"]
DerivativesProvider = Literal["auto", "deribit", "okx"]


class SettingsValidationError(ValueError):
    pass


@dataclass(slots=True)
class AppSettings:
    # Windows engine uses a direct/Supavisor PostgreSQL connection. Supabase URL
    # and public/publishable keys belong to the future Quasar mobile app, not to
    # the engine service.
    supabase_host: str = ""
    supabase_port: int = 5432
    supabase_database: str = "postgres"
    supabase_user: str = ""
    supabase_password: str = ""
    supabase_sslmode: str = "require"

    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    sec_user_agent: str = "RosaInvestmentEngine/1.2.0 admin@example.com"

    engine_mode: EngineMode = "shadow"
    timezone: str = "Europe/Istanbul"
    crypto_primary: str = "coinbase"
    crypto_fallback: str = "bitstamp"
    derivatives_provider: DerivativesProvider = "auto"
    realtime_execution_enabled: bool = False
    realtime_execution_minutes: int = 30
    min_data_quality: float = 80.0
    min_action_edge: float = 70.0
    min_action_confidence: float = 70.0
    strong_action_edge: float = 80.0
    strong_action_confidence: float = 80.0
    regime_reset_edge: float = 45.0
    regime_reset_days: int = 5
    base_tranche_pct: float = 0.25
    max_regime_pct: float = 0.50
    max_late_entry_cross_age_days: int = 5
    ura_holdings_csv_url: str = ""

    def validate(self) -> None:
        required = {
            "Supabase host": self.supabase_host,
            "Supabase kullanıcı": self.supabase_user,
            "Supabase parola": self.supabase_password,
            "Alpha Vantage API key": self.alpha_vantage_api_key,
            "FRED API key": self.fred_api_key,
            "Telegram bot token": self.telegram_bot_token,
            "Telegram chat id": self.telegram_chat_id,
            "SEC User-Agent": self.sec_user_agent,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise SettingsValidationError("Eksik ayarlar: " + ", ".join(missing))
        if not (1 <= int(self.supabase_port) <= 65535):
            raise SettingsValidationError("Supabase portu geçersiz.")
        if self.supabase_sslmode not in {"require", "verify-full", "prefer"}:
            raise SettingsValidationError("Supabase SSL mode geçersiz.")
        if self.engine_mode not in {"shadow", "live", "maintenance"}:
            raise SettingsValidationError("Engine mode geçersiz.")
        if self.derivatives_provider not in {"auto", "deribit", "okx"}:
            raise SettingsValidationError("Derivatives provider geçersiz.")
        if not 0 <= self.min_data_quality <= 100:
            raise SettingsValidationError("Minimum data quality 0-100 olmalıdır.")
        if not 0 <= self.min_action_edge <= 100:
            raise SettingsValidationError("Minimum edge 0-100 olmalıdır.")
        if not 0 <= self.min_action_confidence <= 100:
            raise SettingsValidationError("Minimum confidence 0-100 olmalıdır.")
        if not self.min_action_edge <= self.strong_action_edge <= 100:
            raise SettingsValidationError("Güçlü edge eşiği minimum edge'den küçük olamaz.")
        if not self.min_action_confidence <= self.strong_action_confidence <= 100:
            raise SettingsValidationError("Güçlü confidence eşiği minimum confidence'dan küçük olamaz.")
        if not 0 <= self.regime_reset_edge <= self.min_action_edge:
            raise SettingsValidationError("Rejim reset edge eşiği geçersiz.")
        if not 1 <= int(self.regime_reset_days) <= 30:
            raise SettingsValidationError("Rejim reset gün sayısı 1-30 olmalıdır.")
        if not 0 < self.base_tranche_pct <= self.max_regime_pct <= 1:
            raise SettingsValidationError("Dönüşüm yüzdeleri geçersiz.")
        if self.realtime_execution_minutes < 5 or self.realtime_execution_minutes > 120:
            raise SettingsValidationError("Execution penceresi 5-120 dakika olmalıdır.")
        if "@" not in self.sec_user_agent:
            raise SettingsValidationError("SEC User-Agent içinde iletişim e-postası bulunmalıdır.")

    @property
    def postgres_dsn(self) -> str:
        from urllib.parse import quote_plus

        user = quote_plus(self.supabase_user)
        password = quote_plus(self.supabase_password)
        host = self.supabase_host.strip()
        db = quote_plus(self.supabase_database)
        return (
            f"postgresql://{user}:{password}@{host}:{self.supabase_port}/{db}"
            f"?sslmode={self.supabase_sslmode}"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        obj = cls(**{k: v for k, v in data.items() if k in allowed})
        obj.validate()
        return obj


@dataclass(slots=True)
class PriceBar:
    provider: str
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class FactorScore:
    code: str
    score: float
    quality: float = 100.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Decision:
    system: str
    as_of: str
    direction: str
    regime: str
    edge_score: float
    confidence: float
    uncertainty: float
    data_quality: float
    risk_score: float
    recommended_size: float
    late_entry: bool
    event_veto: bool
    status: str
    execution_required: bool
    factors: dict[str, FactorScore]
    rationale: dict[str, Any] = field(default_factory=dict)
    action_event: bool = False
    action_stage: int = 0
    action_size: float = 0.0
    regime_cumulative_size: float = 0.0
