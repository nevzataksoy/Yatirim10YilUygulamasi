from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "InvestmentEngine"
COMPANY_NAME = "Rosa"


def application_dir() -> Path:
    """Writable application directory.

    Frozen one-file builds deliberately use the directory containing the EXE.
    This is where settings, rosalock, logs and runtime state live.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_dir() -> Path:
    """Read-only bundled resources directory.

    PyInstaller one-file extracts bundled resources to sys._MEIPASS. Source runs
    simply use the project root.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[1]


APP_DIR = application_dir()
BUNDLE_DIR = resource_dir()
CONFIG_DIR = APP_DIR
LOG_DIR = APP_DIR / "logs"
RUNTIME_DIR = APP_DIR / "runtime"
SETTINGS_PATH = APP_DIR / "settings"
LOCK_PATH = APP_DIR / "rosalock"
SPOOL_PATH = RUNTIME_DIR / "spool.db"
PID_PATH = RUNTIME_DIR / "engine.pid"

# Compatibility alias for older modules/docs.
APP_DATA_DIR = APP_DIR


def ensure_directories() -> None:
    # The installer runs elevated and the Windows service runs as LocalSystem.
    # Normal non-elevated users should not need write access to the install dir.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
