from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.paths import LOG_DIR, ensure_directories


def configure_logging() -> None:
    ensure_directories()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    file_handler = RotatingFileHandler(
        LOG_DIR / "investment-engine.log",
        maxBytes=10_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(file_handler)

    # PyInstaller --windowed may set stderr/stdout to None. Do not create a
    # broken StreamHandler in the installed GUI/service binary.
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)
