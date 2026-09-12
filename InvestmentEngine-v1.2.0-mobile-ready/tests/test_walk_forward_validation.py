from __future__ import annotations

from app.backtest.validation import (
    ReplayPoint,
    _metrics,
    walk_forward_edge_thresholds,
)


def _point(
    i: int,
    *,
    edge: float = 0.0,
    edge_signed: float = 1.0,
    ratio: float | None = None,
) -> ReplayPoint:
    return ReplayPoint(
        as_of=f"D{i:03d}",
        edge_signed=edge_signed,
        edge=edge,
        confidence=80.0,
        data_quality=90.0,
        late_entry=False,
        regime="NEUTRAL",
        ratio=float(i + 1 if ratio is None else ratio),
    )


def test_train_metrics_do_not_cross_holdout_boundary() -> None:
    points = [_point(i) for i in range(12)]
    points[7] = _point(7, edge=80.0, ratio=8.0)
    points[9] = _point(9, ratio=100.0)

    unrestricted = _metrics(points, [7], 2)
    train_only = _metrics(points, [7], 2, max_index_exclusive=8)

    assert unrestricted.signals == 1
    assert train_only.signals == 0


def test_expanding_walk_forward_builds_past_only_folds() -> None:
    points = [
        _point(i, edge=80.0 if i % 2 == 0 else 0.0, ratio=100.0 + i)
        for i in range(30)
    ]

    result = walk_forward_edge_thresholds(
        points,
        configured_edge=70,
        thresholds=(50, 70),
        primary_horizon=1,
        min_train_sessions=10,
        test_sessions=5,
        step_sessions=5,
        min_train_signals=1,
    )

    assert result["method"] == "EXPANDING_WINDOW"
    assert result["fold_count"] == 4
    assert result["auto_apply"] is False

    folds = result["folds"]
    assert [fold["train_observations"] for fold in folds] == [10, 15, 20, 25]
    assert [fold["test_observations"] for fold in folds] == [5, 5, 5, 5]
    assert folds[0]["train_end"] == "D009"
    assert folds[0]["test_start"] == "D010"
    assert folds[-1]["train_end"] == "D024"
    assert folds[-1]["test_end"] == "D029"

    for fold in folds:
        candidate = fold["selected_candidate"]
        assert candidate is not None
        assert candidate["train"]["signals"] >= 1
        assert candidate["holdout"] is not None


def test_expanding_walk_forward_reports_insufficient_history() -> None:
    points = [_point(i, edge=80.0) for i in range(20)]

    result = walk_forward_edge_thresholds(
        points,
        configured_edge=70,
        primary_horizon=2,
        min_train_sessions=15,
        test_sessions=6,
        step_sessions=6,
        min_train_signals=1,
    )

    assert result["status"] == "INSUFFICIENT_HISTORY"
    assert result["observations"] == 20
    assert result["folds"] == []
    assert result["auto_apply"] is False
