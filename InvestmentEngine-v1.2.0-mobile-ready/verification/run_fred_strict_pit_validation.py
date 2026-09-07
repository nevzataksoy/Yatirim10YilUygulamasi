from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backtest.fred_pit import (
    prepare_realtime_history,
    replay_ethbtc_core_strict_macro_pit,
    strict_macro_coverage,
)
from app.backtest.validation import replay_ethbtc_core, walk_forward_edge_thresholds
from app.engine import InvestmentEngine
from verification.run_walk_forward_validation import _load_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the existing FRED-current historical replay with a strict "
            "ALFRED real-time-period macro replay. Read-only verification."
        )
    )
    parser.add_argument(
        "--settings-dir",
        type=Path,
        default=None,
        help="Directory containing encrypted Investment Engine settings and rosalock.",
    )
    parser.add_argument("--min-train", type=int, default=365)
    parser.add_argument("--test-sessions", type=int, default=90)
    parser.add_argument("--step-sessions", type=int, default=90)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--min-train-signals", type=int, default=8)
    parser.add_argument(
        "--macro-lookback-days",
        type=int,
        default=120,
        help="Observation history fetched before the first replay date.",
    )
    return parser


def _qualified(point, edge_threshold: float) -> bool:
    sign = 1 if point.edge_signed > 0 else -1 if point.edge_signed < 0 else 0
    return bool(point.edge >= edge_threshold and not point.late_entry and sign != 0)


def _point_comparison(current_points, strict_points, edge_threshold: float) -> dict:
    current = {point.as_of: point for point in current_points}
    strict = {point.as_of: point for point in strict_points}
    common_dates = sorted(set(current).intersection(strict))

    edge_deltas: list[float] = []
    signed_edge_deltas: list[float] = []
    regime_changes = 0
    direction_changes = 0
    qualification_changes = 0
    changed_rows: list[dict] = []

    for as_of in common_dates:
        left = current[as_of]
        right = strict[as_of]
        edge_delta = float(right.edge - left.edge)
        signed_delta = float(right.edge_signed - left.edge_signed)
        edge_deltas.append(abs(edge_delta))
        signed_edge_deltas.append(abs(signed_delta))

        regime_changed = left.regime != right.regime
        left_sign = 1 if left.edge_signed > 0 else -1 if left.edge_signed < 0 else 0
        right_sign = 1 if right.edge_signed > 0 else -1 if right.edge_signed < 0 else 0
        direction_changed = left_sign != right_sign
        qualification_changed = _qualified(left, edge_threshold) != _qualified(right, edge_threshold)

        regime_changes += int(regime_changed)
        direction_changes += int(direction_changed)
        qualification_changes += int(qualification_changed)

        if regime_changed or direction_changed or qualification_changed or abs(edge_delta) >= 1.0:
            changed_rows.append(
                {
                    "as_of": as_of,
                    "current_edge": left.edge,
                    "strict_edge": right.edge,
                    "edge_delta": edge_delta,
                    "current_signed_edge": left.edge_signed,
                    "strict_signed_edge": right.edge_signed,
                    "current_regime": left.regime,
                    "strict_regime": right.regime,
                    "current_qualified": _qualified(left, edge_threshold),
                    "strict_qualified": _qualified(right, edge_threshold),
                }
            )

    changed_rows.sort(key=lambda row: abs(float(row["edge_delta"])), reverse=True)
    n = len(common_dates)
    return {
        "common_dates": n,
        "current_only_dates": len(set(current) - set(strict)),
        "strict_only_dates": len(set(strict) - set(current)),
        "mean_abs_edge_delta": sum(edge_deltas) / n if n else 0.0,
        "max_abs_edge_delta": max(edge_deltas) if edge_deltas else 0.0,
        "mean_abs_signed_edge_delta": sum(signed_edge_deltas) / n if n else 0.0,
        "max_abs_signed_edge_delta": max(signed_edge_deltas) if signed_edge_deltas else 0.0,
        "regime_change_dates": regime_changes,
        "direction_change_dates": direction_changes,
        "configured_qualification_change_dates": qualification_changes,
        "largest_changes": changed_rows[:20],
    }


def _walk_forward_summary(result: dict) -> dict:
    return {
        "status": result.get("status"),
        "observations": result.get("observations"),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "fold_count": result.get("fold_count"),
        "configured_edge_threshold": result.get("configured_edge_threshold"),
        "configured_holdout_signals": result.get("configured_holdout_signals"),
        "selected_candidate_folds": result.get("selected_candidate_folds"),
        "selected_candidate_holdout_signals": result.get("selected_candidate_holdout_signals"),
        "folds": [
            {
                "fold": fold.get("fold"),
                "train_end": fold.get("train_end"),
                "test_start": fold.get("test_start"),
                "test_end": fold.get("test_end"),
                "configured_holdout_signals": (fold.get("configured_holdout") or {}).get("signals"),
                "selected_edge": (fold.get("selected_candidate") or {}).get("edge_threshold"),
                "selected_holdout_signals": ((fold.get("selected_candidate") or {}).get("holdout") or {}).get("signals"),
            }
            for fold in result.get("folds") or []
        ],
    }


def main() -> int:
    args = _parser().parse_args()
    if args.macro_lookback_days <= 0:
        print("ERROR: --macro-lookback-days pozitif olmalıdır.", file=sys.stderr)
        return 2

    settings, settings_dir, searched, load_errors = _load_settings(args.settings_dir)
    if settings is None:
        if load_errors:
            print(
                "ERROR: Investment Engine settings bulundu ancak okunamadı. "
                + " | ".join(load_errors),
                file=sys.stderr,
            )
        else:
            print(
                "ERROR: Investment Engine settings configured değil. Denenen dizinler: "
                + ", ".join(str(path) for path in searched),
                file=sys.stderr,
            )
        return 2

    engine = InvestmentEngine(settings, ROOT)
    engine.db.open()
    try:
        btc = engine.repo.get_price_bars("BTC-USD")
        eth = engine.repo.get_price_bars("ETH-USD")
        current_macro_history = engine.repo.get_macro_history(engine.fred_series)
        current_points = replay_ethbtc_core(
            btc,
            eth,
            current_macro_history,
            settings,
            engine.decision_engine,
        )
        if not current_points:
            print("ERROR: Current core replay point üretmedi.", file=sys.stderr)
            return 3

        first_replay = date.fromisoformat(current_points[0].as_of[:10])
        last_replay = date.fromisoformat(current_points[-1].as_of[:10])
        observation_start = (first_replay - timedelta(days=args.macro_lookback_days)).isoformat()
        observation_end = last_replay.isoformat()

        realtime_history: dict[str, list[dict]] = {}
        for series_id in engine.fred_series:
            realtime_history[series_id] = engine.fred.fetch_realtime_history(
                series_id,
                observation_start=observation_start,
                observation_end=observation_end,
            )

        strict_points = replay_ethbtc_core_strict_macro_pit(
            btc,
            eth,
            realtime_history,
            settings,
            engine.decision_engine,
        )

        prepared = prepare_realtime_history(realtime_history)
        coverage_dates = [point.as_of for point in strict_points]
        coverage = strict_macro_coverage(prepared, coverage_dates, list(engine.fred_series))

        current_walk = walk_forward_edge_thresholds(
            current_points,
            configured_edge=settings.min_action_edge,
            primary_horizon=args.horizon,
            min_train_sessions=args.min_train,
            test_sessions=args.test_sessions,
            step_sessions=args.step_sessions,
            min_train_signals=args.min_train_signals,
        )
        strict_walk = walk_forward_edge_thresholds(
            strict_points,
            configured_edge=settings.min_action_edge,
            primary_horizon=args.horizon,
            min_train_sessions=args.min_train,
            test_sessions=args.test_sessions,
            step_sessions=args.step_sessions,
            min_train_signals=args.min_train_signals,
        )

        result = {
            "status": "VERIFICATION_COMPLETE",
            "method": "FRED_STRICT_MACRO_PIT_COMPARISON",
            "model_version": "1.2.0",
            "settings_dir": str(settings_dir),
            "configured_series": list(engine.fred_series),
            "observation_window": {
                "start": observation_start,
                "end": observation_end,
                "macro_lookback_days": args.macro_lookback_days,
            },
            "alfred_rows_by_series": {
                series_id: len(rows)
                for series_id, rows in realtime_history.items()
            },
            "strict_macro_coverage": coverage,
            "current_replay": {
                "observations": len(current_points),
                "start_date": current_points[0].as_of,
                "end_date": current_points[-1].as_of,
            },
            "strict_replay": {
                "observations": len(strict_points),
                "start_date": strict_points[0].as_of if strict_points else None,
                "end_date": strict_points[-1].as_of if strict_points else None,
            },
            "point_comparison": _point_comparison(
                current_points,
                strict_points,
                settings.min_action_edge,
            ),
            "current_walk_forward": _walk_forward_summary(current_walk),
            "strict_walk_forward": _walk_forward_summary(strict_walk),
            "persistence": {"persisted": False},
            "auto_apply": False,
            "limitations": [
                "Strict PIT applies to FRED macro only.",
                "Derivatives and event PIT histories remain unavailable and neutral in core replay.",
                "This is not a production ACTION/state-machine backtest.",
                "No threshold, factor weight, mode or signal-state parameter is changed.",
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        engine.db.close()


if __name__ == "__main__":
    raise SystemExit(main())
