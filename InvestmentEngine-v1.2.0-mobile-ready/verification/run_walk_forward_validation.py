from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backtest.validation import replay_ethbtc_core, walk_forward_edge_thresholds
from app.engine import InvestmentEngine
from app.security.settings_store import SettingsStore, SettingsStoreError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Post-Shadow P1 expanding walk-forward validation against the "
            "configured Supabase history. Dry-run by default."
        )
    )
    parser.add_argument("--persist", action="store_true", help="Write WALK_FORWARD_CORE validation rows/snapshot.")
    parser.add_argument(
        "--settings-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing encrypted settings and rosalock. Source runs "
            "first check the repo directory, then the standard Windows OneDir "
            "installation under Program Files\\Rosa\\InvestmentEngine."
        ),
    )
    parser.add_argument("--min-train", type=int, default=365, help="Expanding training window minimum sessions.")
    parser.add_argument("--test-sessions", type=int, default=90, help="Holdout sessions per fold.")
    parser.add_argument("--step-sessions", type=int, default=90, help="Fold step in sessions.")
    parser.add_argument("--horizon", type=int, default=20, help="Primary forward-return horizon in sessions.")
    parser.add_argument("--min-train-signals", type=int, default=8, help="Minimum train signals before candidate selection.")
    parser.add_argument(
        "--min-oos-signals",
        type=int,
        default=8,
        help=(
            "Minimum aggregate selected-candidate holdout signals before the report "
            "is classified as EVIDENCE_AVAILABLE. Validation-only; never changes production settings."
        ),
    )
    return parser


def _settings_dirs(explicit_dir: Path | None) -> list[Path]:
    if explicit_dir is not None:
        return [Path(explicit_dir).expanduser().resolve()]

    candidates: list[Path] = [ROOT]
    if sys.platform == "win32":
        for env_name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env_name)
            if base:
                candidates.append(Path(base) / "Rosa" / "InvestmentEngine")
        candidates.append(Path(r"C:\Program Files\Rosa\InvestmentEngine"))

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _load_settings(explicit_dir: Path | None):
    searched: list[Path] = []
    load_errors: list[str] = []

    for settings_dir in _settings_dirs(explicit_dir):
        searched.append(settings_dir)
        store = SettingsStore(
            settings_path=settings_dir / "settings",
            lock_path=settings_dir / "rosalock",
        )
        if not store.is_configured:
            continue
        try:
            settings = store.load()
        except SettingsStoreError as exc:
            load_errors.append(f"{settings_dir}: {exc}")
            continue
        if settings is not None:
            return settings, settings_dir, searched, load_errors

    return None, None, searched, load_errors


def _aggregate_selected_oos(result: dict) -> dict:
    signals = 0
    weighted_hits = 0.0
    weighted_return = 0.0
    folds_with_signals = 0

    for fold in result.get("folds") or []:
        candidate = fold.get("selected_candidate") or {}
        holdout = candidate.get("holdout") or {}
        count = int(holdout.get("signals") or 0)
        if count <= 0:
            continue
        folds_with_signals += 1
        signals += count
        weighted_hits += float(holdout.get("hit_rate") or 0.0) * count
        weighted_return += float(holdout.get("avg_signed_return") or 0.0) * count

    return {
        "signals": signals,
        "folds_with_signals": folds_with_signals,
        "hit_rate": (weighted_hits / signals) if signals else 0.0,
        "avg_signed_return": (weighted_return / signals) if signals else 0.0,
    }


def _classify_evidence(result: dict, min_oos_signals: int) -> str:
    if min_oos_signals <= 0:
        raise ValueError("min_oos_signals pozitif olmalıdır.")
    if int(result.get("selected_candidate_folds") or 0) <= 0:
        return "LIMITED_TRAIN_SIGNAL_COUNT"
    summary = _aggregate_selected_oos(result)
    if int(summary["signals"]) < min_oos_signals:
        return "LIMITED_OOS_SIGNAL_COUNT"
    return "EVIDENCE_AVAILABLE"


def main() -> int:
    args = _parser().parse_args()
    settings, settings_dir, searched, load_errors = _load_settings(args.settings_dir)
    if settings is None:
        if load_errors:
            print(
                "ERROR: Investment Engine settings bulundu ancak okunamadı. "
                + " | ".join(load_errors),
                file=sys.stderr,
            )
        else:
            searched_text = ", ".join(str(path) for path in searched)
            print(
                "ERROR: Investment Engine settings configured değil. "
                f"Denenen dizinler: {searched_text}",
                file=sys.stderr,
            )
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

        result["selection_status"] = str(result.get("status") or "UNKNOWN")
        result["selected_candidate_oos_summary"] = _aggregate_selected_oos(result)
        result["min_oos_signals"] = args.min_oos_signals
        result["status"] = _classify_evidence(result, args.min_oos_signals)
        result["settings_dir"] = str(settings_dir)
        result["persistence"] = {"persisted": False}

        if args.persist:
            status = str(result.get("status") or "UNKNOWN")
            observations = int(result.get("observations") or 0)
            signals = int(result.get("configured_holdout_signals") or 0)
            details = {
                "auto_apply": False,
                "method": result.get("method"),
                "selection_status": result.get("selection_status"),
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
            result["persistence"] = {
                "persisted": True,
                "validation_run_id": run_id,
            }
            engine.repo.publish_validation_snapshot(
                validation_type="WALK_FORWARD_CORE",
                system="ETH/BTC",
                status=status,
                start_date=result.get("start_date"),
                end_date=result.get("end_date"),
                metrics=result,
                details={**details, "validation_run_id": run_id},
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        engine.db.close()


if __name__ == "__main__":
    raise SystemExit(main())
