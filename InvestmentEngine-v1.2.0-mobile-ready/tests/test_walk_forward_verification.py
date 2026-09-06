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
