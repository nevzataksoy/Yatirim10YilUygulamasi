from __future__ import annotations

from contextlib import contextmanager

from app.database.repository import Repository


def _normalize(sql: str) -> str:
    return " ".join(sql.lower().split())


class _FakeCursor:
    def __init__(self, db: "_FakeDb") -> None:
        self.db = db

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        self.db.executed.append((_normalize(sql), params))

    def executemany(self, sql: str, rows) -> None:
        self.db.executemany_calls.append((_normalize(sql), list(rows)))

    def fetchone(self):
        if not self.db.fetchone_rows:
            return None
        return self.db.fetchone_rows.pop(0)

    def fetchall(self):
        return list(self.db.fetchall_rows)


class _FakeConnection:
    def __init__(self, db: "_FakeDb") -> None:
        self.db = db

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.db)

    def commit(self) -> None:
        self.db.commit_calls += 1


class _FakeDb:
    def __init__(self) -> None:
        self.connection_calls = 0
        self.commit_calls = 0
        self.executed: list[tuple[str, object]] = []
        self.executemany_calls: list[tuple[str, list[tuple]]] = []
        self.fetchone_rows: list[dict] = []
        self.fetchall_rows: list[dict] = []

    @contextmanager
    def connection(self):
        self.connection_calls += 1
        yield _FakeConnection(self)


def test_upsert_macro_skips_same_value_refetches_in_sql_contract() -> None:
    db = _FakeDb()
    repo = Repository(db)

    repo.upsert_macro(
        [
            {
                "series_id": "SP500",
                "date": "2026-09-08",
                "value": 7673.52,
                "realtime_start": "2026-09-10",
                "realtime_end": "2026-09-10",
            },
            {
                "series_id": "STLFSI4",
                "date": "2026-09-04",
                "value": -0.7884,
                "realtime_start": "2026-09-10",
                "realtime_end": "2026-09-10",
            },
        ]
    )

    assert db.connection_calls == 1
    assert db.commit_calls == 1
    assert len(db.executemany_calls) == 1

    lock_calls = [
        (sql, params)
        for sql, params in db.executed
        if "pg_advisory_xact_lock" in sql
    ]
    assert [params[0] for _, params in lock_calls] == [
        "macro.observations:SP500",
        "macro.observations:STLFSI4",
    ]

    sql, rows = db.executemany_calls[0]
    assert "select m.value from macro.observations m" in sql
    assert "order by m.realtime_start desc, m.fetched_at desc, m.id desc" in sql
    assert ") is distinct from %s" in sql
    assert "on conflict do nothing" in sql
    assert "do update" not in sql
    assert "fetched_at=now" not in sql
    assert len(rows) == 2
    assert all(len(row) == 8 for row in rows)
    assert rows[0][0:5] == (
        "SP500",
        "2026-09-08",
        7673.52,
        "2026-09-10",
        "2026-09-10",
    )
    assert rows[0][5:] == ("SP500", "2026-09-08", 7673.52)


def test_upsert_macro_empty_input_does_not_open_connection() -> None:
    db = _FakeDb()
    Repository(db).upsert_macro([])

    assert db.connection_calls == 0
    assert db.commit_calls == 0


def test_latest_macro_read_has_deterministic_version_order() -> None:
    db = _FakeDb()
    db.fetchone_rows = [
        {
            "series_id": "STLFSI4",
            "observation_date": "2026-09-04",
            "value": -0.7884,
            "realtime_start": "2026-09-09",
            "realtime_end": "2026-09-09",
            "fetched_at": "2026-09-09T00:15:00+00:00",
        }
    ]
    repo = Repository(db)

    result = repo.get_latest_macro_observations(["STLFSI4"], "2026-09-09")

    assert result["STLFSI4"]["value"] == -0.7884
    sql = db.executed[0][0]
    assert "observation_date <= %s" in sql
    assert (
        "order by observation_date desc, realtime_start desc, fetched_at desc, id desc"
        in sql
    )


def test_latest_macro_read_without_as_of_uses_same_deterministic_order() -> None:
    db = _FakeDb()
    db.fetchone_rows = [
        {
            "series_id": "SP500",
            "observation_date": "2026-09-08",
            "value": 7673.52,
        }
    ]

    Repository(db).get_latest_macro_observations(["SP500"])

    sql = db.executed[0][0]
    assert "observation_date <= %s" not in sql
    assert (
        "order by observation_date desc, realtime_start desc, fetched_at desc, id desc"
        in sql
    )


def test_macro_history_returns_one_latest_version_per_observation_date() -> None:
    db = _FakeDb()
    db.fetchall_rows = [
        {
            "series_id": "STLFSI4",
            "observation_date": "2026-09-04",
            "value": -0.7884,
        }
    ]
    repo = Repository(db)

    result = repo.get_macro_history(["STLFSI4"])

    assert len(result["STLFSI4"]) == 1
    sql = db.executed[0][0]
    assert "distinct on (series_id, observation_date)" in sql
    assert (
        "order by series_id, observation_date, realtime_start desc, fetched_at desc, id desc"
        in sql
    )
    assert sql.endswith("order by series_id, observation_date")
