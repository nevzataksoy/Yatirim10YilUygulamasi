from __future__ import annotations

import inspect
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.paths import LOG_DIR

_POOL_STAT_KEYS = (
    "pool_min",
    "pool_max",
    "pool_size",
    "pool_available",
    "requests_waiting",
    "usage_ms",
    "requests_num",
    "requests_queued",
    "requests_wait_ms",
    "requests_errors",
    "returns_bad",
    "connections_num",
    "connections_ms",
    "connections_errors",
    "connections_lost",
)

_POOL_HEALTH_COUNTERS = (
    "requests_queued",
    "requests_errors",
    "returns_bad",
    "connections_errors",
    "connections_lost",
)


def compact_pool_stats(stats: dict[str, Any] | None) -> dict[str, int]:
    """Normalize psycopg pool counters without depending on optional zero-valued keys."""
    raw = stats or {}
    result: dict[str, int] = {}
    for key in _POOL_STAT_KEYS:
        try:
            result[key] = int(raw.get(key, 0) or 0)
        except (TypeError, ValueError):
            result[key] = 0
    return result


def pool_counter_deltas(previous: dict[str, int] | None, current: dict[str, int]) -> dict[str, int]:
    """Return only positive changes in counters relevant to pool pressure/health."""
    if previous is None:
        return {}
    deltas: dict[str, int] = {}
    for key in _POOL_HEALTH_COUNTERS:
        delta = int(current.get(key, 0)) - int(previous.get(key, 0))
        if delta > 0:
            deltas[key] = delta
    return deltas


def application_module_from_filename(filename: str) -> str | None:
    """Resolve an app module from source or PyInstaller frozen co_filename forms."""
    normalized = str(filename or "").replace("\\", "/")
    if "/app/" in normalized:
        relative = normalized.split("/app/", 1)[1]
    elif normalized.startswith("app/"):
        relative = normalized[len("app/") :]
    else:
        return None

    if relative.endswith(".py"):
        relative = relative[:-3]
    module = relative.replace("/", ".").strip(".")
    return module or None


class PoolTelemetryRecorder:
    """Best-effort local JSONL recorder for connection-pool RCA.

    Telemetry never writes back to PostgreSQL, so it cannot consume a pool
    connection or amplify a pool outage. Each process writes to its own file to
    avoid Windows file-sharing/rotation conflicts between the service and CLI.
    """

    def __init__(
        self,
        log_dir: Path = LOG_DIR,
        *,
        sample_interval_seconds: float = 60.0,
        max_bytes: int = 5_000_000,
        backups: int = 3,
    ) -> None:
        self.path = Path(log_dir) / f"connection-pool-telemetry-{os.getpid()}.jsonl"
        self.sample_interval_seconds = float(sample_interval_seconds)
        self.max_bytes = int(max_bytes)
        self.backups = int(backups)
        self._lock = threading.Lock()
        self._last_sample_monotonic = 0.0
        self._last_health_counters: dict[str, int] | None = None

    def observe_counter_deltas(self, stats: dict[str, int]) -> dict[str, int]:
        with self._lock:
            deltas = pool_counter_deltas(self._last_health_counters, stats)
            self._last_health_counters = dict(stats)
            return deltas

    def sample_due(self) -> bool:
        now = time.monotonic()
        with self._lock:
            if now - self._last_sample_monotonic < self.sample_interval_seconds:
                return False
            self._last_sample_monotonic = now
            return True

    @staticmethod
    def infer_callsite() -> str:
        """Find the nearest application caller without expensive inspect.stack()."""
        frame = inspect.currentframe()
        try:
            frame = frame.f_back if frame is not None else None
            while frame is not None:
                module = application_module_from_filename(frame.f_code.co_filename)
                if module and module not in {"database.db", "database.pool_telemetry"}:
                    return f"{module}.{frame.f_code.co_name}"
                frame = frame.f_back
        finally:
            del frame
        return "unknown"

    def record(self, event: str, **fields: Any) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "pid": os.getpid(),
            **fields,
        }
        try:
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate_if_needed(len(encoded) + 1)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(encoded + "\n")
        except Exception:
            # RCA telemetry must never change engine/database behavior.
            return

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        if self.max_bytes <= 0 or self.backups <= 0:
            return
        try:
            current_size = self.path.stat().st_size if self.path.exists() else 0
        except OSError:
            return
        if current_size + incoming_bytes <= self.max_bytes:
            return
        try:
            oldest = Path(f"{self.path}.{self.backups}")
            if oldest.exists():
                oldest.unlink()
            for index in range(self.backups - 1, 0, -1):
                source = Path(f"{self.path}.{index}")
                if source.exists():
                    source.replace(Path(f"{self.path}.{index + 1}"))
            if self.path.exists():
                self.path.replace(Path(f"{self.path}.1"))
        except OSError:
            # If rotation fails, the append attempt may still succeed.
            return
