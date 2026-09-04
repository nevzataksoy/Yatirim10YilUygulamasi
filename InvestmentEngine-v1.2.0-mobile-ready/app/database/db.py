from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.database.pool_telemetry import PoolTelemetryRecorder, compact_pool_stats
from app.models import AppSettings
from app.run_context import current_job_context


class DatabaseError(RuntimeError):
    pass


class DatabaseService:
    _SLOW_CHECKOUT_MS = 250.0
    _SLOW_HOLD_MS = 2_000.0

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.pool: ConnectionPool | None = None
        self._pool_telemetry = PoolTelemetryRecorder()

    def test_connection(self) -> None:
        try:
            with psycopg.connect(self.settings.postgres_dsn, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    cur.execute("select current_database(), now()")
                    cur.fetchone()
        except Exception as exc:
            raise DatabaseError(f"Supabase PostgreSQL bağlantısı başarısız: {exc}") from exc

    def open(self) -> None:
        if self.pool is not None:
            return
        self.pool = ConnectionPool(
            conninfo=self.settings.postgres_dsn,
            min_size=1,
            max_size=6,
            timeout=10,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            self.pool = None

    def _pool_stats(self) -> dict[str, int]:
        if self.pool is None:
            return compact_pool_stats({})
        try:
            return compact_pool_stats(self.pool.get_stats())
        except Exception:
            return compact_pool_stats({})

    def _telemetry_context(self) -> dict:
        root_job_name, run_kind = current_job_context()
        return {
            "root_job_name": root_job_name,
            "run_kind": run_kind,
            "callsite": self._pool_telemetry.infer_callsite(),
            "thread": threading.current_thread().name,
        }

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        if self.pool is None:
            self.open()
        assert self.pool is not None

        context = self._telemetry_context()
        checkout_started = time.perf_counter()
        acquired_at: float | None = None
        wait_ms: float | None = None
        hold_ms: float | None = None
        stats_before = self._pool_stats()

        try:
            with self.pool.connection() as conn:
                acquired_at = time.perf_counter()
                wait_ms = (acquired_at - checkout_started) * 1000.0
                stats_acquired = self._pool_stats()

                if wait_ms >= self._SLOW_CHECKOUT_MS or stats_acquired.get("requests_waiting", 0) > 0:
                    self._pool_telemetry.record(
                        "checkout_pressure",
                        **context,
                        wait_ms=round(wait_ms, 3),
                        stats_before=stats_before,
                        stats_acquired=stats_acquired,
                    )

                root_job_name, run_kind = current_job_context()
                # Local GUCs are consumed by migration 0010's job-run provenance trigger.
                # They are observability metadata only; model/decision semantics are untouched.
                with conn.cursor() as cur:
                    cur.execute(
                        "select set_config('rosa.root_job_name', %s, true), "
                        "set_config('rosa.run_kind', %s, true)",
                        (root_job_name, run_kind),
                    )
                try:
                    yield conn
                finally:
                    hold_ms = (time.perf_counter() - acquired_at) * 1000.0

        except PoolTimeout as exc:
            timeout_ms = (time.perf_counter() - checkout_started) * 1000.0
            stats_timeout = self._pool_stats()
            deltas = self._pool_telemetry.observe_counter_deltas(stats_timeout)
            self._pool_telemetry.record(
                "checkout_timeout",
                **context,
                wait_ms=round(timeout_ms, 3),
                error=str(exc)[:500],
                stats_before=stats_before,
                stats_timeout=stats_timeout,
                counter_deltas=deltas,
            )
            raise
        finally:
            if acquired_at is not None:
                stats_after = self._pool_stats()
                deltas = self._pool_telemetry.observe_counter_deltas(stats_after)

                if hold_ms is not None and hold_ms >= self._SLOW_HOLD_MS:
                    self._pool_telemetry.record(
                        "hold_slow",
                        **context,
                        wait_ms=round(wait_ms or 0.0, 3),
                        hold_ms=round(hold_ms, 3),
                        stats_after=stats_after,
                    )

                if deltas:
                    self._pool_telemetry.record(
                        "counter_delta",
                        **context,
                        wait_ms=round(wait_ms or 0.0, 3),
                        hold_ms=round(hold_ms or 0.0, 3),
                        deltas=deltas,
                        stats=stats_after,
                    )

                if self._pool_telemetry.sample_due():
                    self._pool_telemetry.record(
                        "sample",
                        **context,
                        wait_ms=round(wait_ms or 0.0, 3),
                        hold_ms=round(hold_ms or 0.0, 3),
                        stats=stats_after,
                    )
