from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backtest.validation import replay_ethbtc_core, walk_forward_edge_thresholds
from app.engine import InvestmentEngine
from app.security.settings_store import SettingsStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Post-Shadow P1 expanding walk-forward validation against the "
            "configured Supabase history. Dry-run by default."
        )
    )
    parser.add_argument("--persist", action="store_true", help="Write WALK_FORWARD_CORE validation rows/snapshot.")
    parser.add_argument("--min-train", type=int, default=365, help="Expanding training window minimum sessions.")
    parser.add_argument("--test-sessions", type=int, default=90, help="Holdout sessions per fold.")
    parser.add_argument("--step-sessions", type=int, default=90, help="Fold step in sessions.")
    parser.add_argument("--horizon", type=int, default=20, help="Primary forward-return horizon in sessions.")
    parser.add_argument("--min-train-signals", type=int, default=8, help="Minimum train signals before candidate selection.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    store = SettingsStore()
    if not store.is_configured:
        print("ERROR: Investment Engine settings configured değil.", file=sys.stderr)
        return 2

    settings = store.load()
    if settings is None:
        print("ERROR: Investment Engine settings yüklenemedi.", file=sys.stderr)
        return 2

    engine = InvestmentEngine(settings, ROOT)
    started = datetime.now(timezone.utc)
    engine.db.open()
    try:
        btc = engine.repo.get_price_bars("BTC-USD")
        eth = engine.repo.get_price_bars("ETH-USD")
        macro_history = engine.repo.get_macro_history(engine.fred_series)
        points = replay_ethbtc_core(
            btc,
            eth,
            macro_history,
            settings,
            engine.decision_engine,
        )
        result = walk_forward_edge_thresholds(
            points,
            configured_edge=settings.min_action_edge,
            primary_horizon=args.horizon,
            min_train_sessions=args.min_train,
            test_sessions=args.test_sessions,
            step_sessions=args.step_sessions,
            min_train_signals=args.min_train_signals,
        )

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if args.persist:
            status = str(result.get("status") or "UNKNOWN")
            observations = int(result.get("observations") or 0)
            signals = int(result.get("configured_holdout_signals") or 0)
            details = {
                "auto_apply": False,
                "method": result.get("method"),
                "source": "verification/run_walk_forward_validation.py",
            }
            run_id = engine.repo.insert_validation_run(
                validation_type="WALK_FORWARD_CORE",
                system="ETH/BTC",
                status=status,
                started_at=started,
                start_date=result.get("start_date"),
                end_date=result.get("end_date"),
                observations=observations,
                signals=signals,
                metrics=result,
                details=details,
            )
            engine.repo.publish_validation_snapshot(
                validation_type="WALK_FORWARD_CORE",
                system="ETH/BTC",
                status=status,
                start_date=result.get("start_date"),
                end_date=result.get("end_date"),
                metrics=result,
                details={**details, "validation_run_id": run_id},
            )
            print(f"PERSISTED validation_run_id={run_id}", file=sys.stderr)
        else:
            print("DRY-RUN: Supabase validation tablolarına yazılmadı.", file=sys.stderr)

        return 0
    finally:
        engine.db.close()


if __name__ == "__main__":
    raise SystemExit(main())
