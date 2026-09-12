from __future__ import annotations

from pathlib import Path

import verification.run_walk_forward_validation as walk_forward_cli


def test_explicit_settings_dir_is_the_only_candidate(tmp_path: Path) -> None:
    explicit = tmp_path / "installed-engine"

    candidates = walk_forward_cli._settings_dirs(explicit)

    assert candidates == [explicit.resolve()]


def test_windows_standard_install_is_a_settings_candidate(monkeypatch, tmp_path: Path) -> None:
    program_files = tmp_path / "Program Files"
    monkeypatch.setattr(walk_forward_cli.sys, "platform", "win32")
    monkeypatch.setenv("ProgramW6432", str(program_files))
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)

    candidates = walk_forward_cli._settings_dirs(None)

    assert walk_forward_cli.ROOT in candidates
    assert program_files / "Rosa" / "InvestmentEngine" in candidates


def test_evidence_status_distinguishes_train_and_oos_scarcity() -> None:
    no_candidate = {
        "selected_candidate_folds": 0,
        "folds": [],
    }
    assert (
        walk_forward_cli._classify_evidence(no_candidate, min_oos_signals=8)
        == "LIMITED_TRAIN_SIGNAL_COUNT"
    )

    sparse_oos = {
        "selected_candidate_folds": 2,
        "folds": [
            {
                "selected_candidate": {
                    "holdout": {
                        "signals": 1,
                        "hit_rate": 0.0,
                        "avg_signed_return": -0.08,
                    }
                }
            },
            {
                "selected_candidate": {
                    "holdout": {
                        "signals": 3,
                        "hit_rate": 1 / 3,
                        "avg_signed_return": -0.02,
                    }
                }
            },
        ],
    }
    assert (
        walk_forward_cli._classify_evidence(sparse_oos, min_oos_signals=8)
        == "LIMITED_OOS_SIGNAL_COUNT"
    )

    summary = walk_forward_cli._aggregate_selected_oos(sparse_oos)
    assert summary["signals"] == 4
    assert summary["folds_with_signals"] == 2
    assert summary["hit_rate"] == 0.25
    assert round(summary["avg_signed_return"], 6) == -0.035


def test_evidence_status_requires_explicit_oos_floor() -> None:
    enough_oos = {
        "selected_candidate_folds": 1,
        "folds": [
            {
                "selected_candidate": {
                    "holdout": {
                        "signals": 8,
                        "hit_rate": 0.5,
                        "avg_signed_return": 0.0,
                    }
                }
            }
        ],
    }

    assert (
        walk_forward_cli._classify_evidence(enough_oos, min_oos_signals=8)
        == "EVIDENCE_AVAILABLE"
    )
