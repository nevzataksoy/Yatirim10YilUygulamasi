from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.models import AppSettings


class DatabaseError(RuntimeError):
    pass


class DatabaseService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.pool: ConnectionPool | None = None

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

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        if self.pool is None:
            self.open()
        assert self.pool is not None
        with self.pool.connection() as conn:
            yield conn
