from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _require_markers(path: str, markers: list[str], label: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise SystemExit(f"{label} eksik: {marker}")


def main() -> int:
    required = [
        "build.bat",
        "investmentengine_setup.iss",
        "InvestmentEngineCLI.cmd",
        "InvestmentEngineCLI.ps1",
        "requirements.txt",
        "migrations/0001_schema.sql",
        "migrations/0002_seed.sql",
        "migrations/0003_mobile_api.sql",
        "migrations/0004_v1_1_hardening.sql",
        "migrations/0005_v1_1_2_macro_derivatives.sql",
        "migrations/0006_v1_1_3_hardening_realtime_ura.sql",
        "migrations/0007_v1_2_model_validation.sql",
        "migrations/0008_portfolio_audit_hardening.sql",
        "migrations/0009_portfolio_self_service_reset.sql",
        "app/collectors/globalx_ura.py",
        "app/collectors/sec.py",
        "app/engines/ura.py",
        "app/realtime/coinbase_orderbook.py",
        "app/backtest/validation.py",
        "app/version.py",
        "docs/SUPABASE_SETUP.md",
        "docs/TELEGRAM_SETUP.md",
        "docs/MOBILE_APP_BACKEND_CONTRACT.md",
        "docs/HOTFIX_1_1_3.md",
        "docs/TEST_PLAN_V1_1_3.md",
        "docs/OPEN_ITEMS_AFTER_V1_1_3.md",
        "docs/MODEL_VALIDATION_AND_SHADOW.md",
        "docs/TEST_PLAN_V1_2_0.md",
        "docs/HOTFIX_1_2_0.md",
    ]
    missing = [x for x in required if not (ROOT / x).is_file()]
    if missing:
        raise SystemExit("Eksik release dosyaları: " + ", ".join(missing))

    forbidden = ["Google-Sheets-v8.xlsx", "AppsScript-v8.gs", "settings", "rosalock"]
    present = [x for x in forbidden if (ROOT / x).exists()]
    if present:
        raise SystemExit("Release kaynak ağacında olmaması gereken dosyalar: " + ", ".join(present))

    if (ROOT / "VERSION").read_text(encoding="utf-8").strip() != "1.2.0":
        raise SystemExit("VERSION 1.2.0 değil.")

    defaults = json.loads((ROOT / "config/defaults.json").read_text(encoding="utf-8"))
    for system, regimes in defaults["factor_weights"].items():
        for regime, weights in regimes.items():
            total = sum(float(v) for v in weights.values())
            if abs(total - 1.0) > 1e-9:
                raise SystemExit(f"Factor weight toplamı 1 değil: {system}/{regime}={total}")
            if "volatility" in weights and float(weights["volatility"]) != 0:
                raise SystemExit(f"Volatility directional edge'e dahil edilmiş: {system}/{regime}")

    _require_markers(
        "migrations/0003_mobile_api.sql",
        [
            "public.portfolio_transactions",
            "auth.uid() = user_id",
            "public.decision_snapshot",
            "public.market_snapshot",
            "to authenticated",
        ],
        "Mobil backend sözleşmesi",
    )

    _require_markers(
        "app/collectors/fred.py",
        ['"sort_order": "desc"'],
        "FRED latest-first",
    )
    if not (ROOT / "app/collectors/okx.py").is_file():
        raise SystemExit("OKX derivatives fallback collector eksik.")
    _require_markers(
        "app/collectors/derivatives.py",
        ["deribit", "okx", "fetch_pair"],
        "Derivatives provider abstraction",
    )

    engine = (ROOT / "app/engine.py").read_text(encoding="utf-8")
    for forbidden_marker in ['neutral("event",50', 'neutral("event", 50']:
        if forbidden_marker in engine:
            raise SystemExit("Eksik crypto event verisine sentetik quality=50 veriliyor.")
    for marker in [
        "score_ura_holdings_fundamentals",
        "score_ura_breadth",
        "score_event_monitor",
        "def sec_event_job",
        "def realtime_smoke_test",
        '"market_data_date"',
        '"decision_evaluated_at"',
    ]:
        if marker not in engine:
            raise SystemExit(f"v1.2.0 engine hardening eksik: {marker}")

    _require_markers(
        "app/realtime/coinbase_orderbook.py",
        ["level2_batch", "matches", "ofi", "trade_imbalance", "trade_notional_usd", "trade_gap_count"],
        "Realtime metrics",
    )
    _require_markers(
        "run.py",
        ["--test-realtime", "--validate-model", "--backfill-crypto", '"events"', "_attach_parent_console", "investment-engine-cli.log"],
        "CLI hardening",
    )
    _require_markers(
        "app/engines/decision.py",
        ["if f.score > 1e-9", "elif f.score < -1e-9"],
        "Neutral agreement semantics",
    )
    _require_markers(
        "app/engines/regime.py",
        ["market_regime", "trend_regime", "STRONG_DOWNTREND", "STRONG_UPTREND"],
        "Regime axes",
    )
    _require_markers(
        "app/database/repository.py",
        [
            "calculate_and_upsert_ura_breadth",
            "evaluate_mature_decisions",
            "trade_imbalance",
            "quality / 100.0",
        ],
        "Repository hardening",
    )
    _require_markers(
        "investmentengine_setup.iss",
        [
            '#define MyAppVersion "1.2.0"',
            'Source: "dist\\InvestmentEngine\\{#MyAppExeName}"',
            'Source: "dist\\InvestmentEngine\\_internal\\*"',
            'DestDir: "{app}\\_internal"',
            'Source: "InvestmentEngineCLI.cmd"',
            'Source: "InvestmentEngineCLI.ps1"',
        ],
        "Installer v1.2.0",
    )
    _require_markers(
        "migrations/0007_v1_2_model_validation.sql",
        ["model.validation_runs", "public.model_validation_snapshot", "shadow_min_calendar_days"],
        "Model validation migration",
    )
    _require_markers(
        "migrations/0008_portfolio_audit_hardening.sql",
        [
            "ux_portfolio_transactions_single_successor",
            "validate_portfolio_revision_reference",
            "revoke update, delete on public.portfolio_transactions",
            "btc_eth_conversion_pct",
        ],
        "Portföy audit hardening migration",
    )
    _require_markers(
        "migrations/0009_portfolio_self_service_reset.sql",
        [
            "reset_portfolio_transaction_history",
            "authenticated_user_id uuid := auth.uid()",
            "transaction_row.user_id = authenticated_user_id",
            "grant execute on function",
        ],
        "Kullanıcı portföy sıfırlama migration",
    )
    _require_markers(
        "app/backtest/validation.py",
        ["replay_ethbtc_core", "calibrate_edge_thresholds", "classify_shadow_readiness"],
        "Point-in-time validation",
    )

    build_text = (ROOT / "build.bat").read_text(encoding="utf-8")
    for marker in [
        "--onedir",
        '--contents-directory "_internal"',
        "--noupx",
        "dist\\InvestmentEngine\\InvestmentEngine.exe",
        "dist\\InvestmentEngine\\_internal",
    ]:
        if marker not in build_text:
            raise SystemExit(f"Windows Service OneDir build sözleşmesi eksik: {marker}")
    if "--onefile" in build_text:
        raise SystemExit("Windows Service build tekrar --onefile kullanıyor; SCM startup timeout riski geri geldi.")

    cmd_text=(ROOT / "InvestmentEngineCLI.cmd").read_text(encoding="utf-8")
    ps1_text=(ROOT / "InvestmentEngineCLI.ps1").read_text(encoding="utf-8")
    if "\\n" in cmd_text or "\\n" in ps1_text:
        raise SystemExit("CLI wrapper dosyalarında literal \\n bulundu.")
    if "%*" not in cmd_text or "ValueFromRemainingArguments" not in ps1_text:
        raise SystemExit("CLI wrapper argüman aktarımı eksik.")

    print("Release check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
