from __future__ import annotations

import copy
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

from app.collectors.globalx_ura import (
    GlobalXUraHoldingsCollector,
    UraHolding,
    UraHoldingsSnapshot,
)
from app.database.ura_holdings_persistence import (
    get_ura_holdings_snapshot_refs,
    persist_ura_holdings_snapshot,
)


def _normalize(sql: str) -> str:
    return " ".join(sql.lower().split())


class _FakeCursor:
    def __init__(self, conn: "_FakeConnection") -> None:
        self.conn = conn
        self._row = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        query = _normalize(sql)
        self.conn.sql.append(query)

        if query.startswith("insert into fundamentals.ura_holdings_snapshots"):
            holding_date, source_url, fetched_at, content_sha256, raw_csv, constituent_count = params
            self.conn.next_id += 1
            row = {
                "id": self.conn.next_id,
                "holding_date": holding_date,
                "source_url": source_url,
                "fetched_at": fetched_at,
                "content_sha256": content_sha256,
                "raw_csv": bytes(raw_csv),
                "constituent_count": constituent_count,
            }
            self.conn.working_snapshots.append(row)
            self._row = {"id": row["id"], "fetched_at": fetched_at}
            return

        if query.startswith("delete from fundamentals.ura_holdings"):
            if self.conn.fail_on == "canonical":
                raise RuntimeError("injected canonical failure")
            holding_date = str(params[0])
            self.conn.working_holdings = {
                key: value
                for key, value in self.conn.working_holdings.items()
                if key[0] != holding_date
            }
            return

        if query.startswith("select id,holding_date,source_url,fetched_at,content_sha256"):
            holding_date = str(params[0])
            candidates = [
                row
                for row in self.conn.working_snapshots
                if str(row["holding_date"]) == holding_date
            ]
            candidates.sort(key=lambda row: (row["fetched_at"], row["id"]), reverse=True)
            if not candidates:
                self._row = None
                return
            row = copy.deepcopy(candidates[0])
            row["raw_size_bytes"] = len(row["raw_csv"])
            self._row = row
            return

        raise AssertionError(f"Beklenmeyen SQL: {query}")

    def executemany(self, sql: str, rows) -> None:
        query = _normalize(sql)
        self.conn.sql.append(query)
        if not query.startswith("insert into fundamentals.ura_holdings"):
            raise AssertionError(f"Beklenmeyen executemany SQL: {query}")
        for row in rows:
            (
                holding_date,
                ticker,
                name,
                weight,
                shares,
                market_value,
                market_price,
                source_url,
                fetched_at,
            ) = row
            key = (str(holding_date), str(ticker))
            self.conn.working_holdings[key] = {
                "holding_date": str(holding_date),
                "ticker": str(ticker),
                "name": name,
                "weight": weight,
                "shares": shares,
                "market_value": market_value,
                "market_price": market_price,
                "source_url": source_url,
                "fetched_at": fetched_at,
            }

    def fetchone(self):
        row, self._row = self._row, None
        return row


class _FakeConnection:
    def __init__(self, db: "_FakeDb") -> None:
        self.db = db
        self.fail_on = db.fail_on
        self.next_id = db.next_id
        self.sql: list[str] = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.working_snapshots = copy.deepcopy(db.snapshots)
        self.working_holdings = copy.deepcopy(db.holdings)

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commit_calls += 1
        self.db.snapshots = copy.deepcopy(self.working_snapshots)
        self.db.holdings = copy.deepcopy(self.working_holdings)
        self.db.next_id = self.next_id

    def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeDb:
    def __init__(self) -> None:
        self.snapshots: list[dict] = []
        self.holdings: dict[tuple[str, str], dict] = {}
        self.next_id = 0
        self.fail_on: str | None = None
        self.connection_calls = 0
        self.last_conn: _FakeConnection | None = None

    @contextmanager
    def connection(self):
        self.connection_calls += 1
        conn = _FakeConnection(self)
        self.last_conn = conn
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise


def _snapshot(
    holding_date: str,
    *,
    raw_csv: bytes,
    tickers: tuple[str, ...] = ("AAA", "BBB"),
    fetched_at: datetime,
) -> UraHoldingsSnapshot:
    source_url = f"https://example.test/ura_full-holdings_{holding_date.replace('-', '')}.csv"
    holdings = [
        UraHolding(
            holding_date=holding_date,
            ticker=ticker,
            name=f"{ticker} Corp",
            weight=0.5 / len(tickers),
            shares=100.0 + index,
            market_value=1_000.0 + index,
            market_price=10.0 + index,
            source_url=source_url,
        )
        for index, ticker in enumerate(tickers)
    ]
    return UraHoldingsSnapshot(
        holding_date=holding_date,
        source_url=source_url,
        holdings=holdings,
        fetched_at=fetched_at,
        raw_csv=raw_csv,
    )


def test_parse_csv_preserves_exact_raw_bytes_and_fetch_time() -> None:
    text = (
        "URA Holdings\n"
        "as of 09/08/2026\n"
        "Ticker,Name,% of Net Assets,Shares Held,Market Value ($),Market Price ($)\n"
        "AAA,AAA Corp,50,100,1000,10\n"
    )
    raw_csv = text.encode("utf-8")
    fetched_at = datetime(2026, 9, 9, 1, 2, 3, tzinfo=timezone.utc)

    snapshot = GlobalXUraHoldingsCollector.parse_csv(
        text,
        "https://example.test/ura.csv",
        raw_csv=raw_csv,
        fetched_at=fetched_at,
    )

    assert snapshot.raw_csv == raw_csv
    assert snapshot.fetched_at == fetched_at
    assert snapshot.holding_date == "2026-09-08"
    assert [row.ticker for row in snapshot.holdings] == ["AAA"]


def test_persist_uses_one_transaction_and_records_raw_snapshot() -> None:
    db = _FakeDb()
    fetched_at = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    snapshot = _snapshot("2026-09-08", raw_csv=b"raw-v1", fetched_at=fetched_at)

    meta = persist_ura_holdings_snapshot(db, snapshot)

    assert db.connection_calls == 1
    assert db.last_conn is not None
    assert db.last_conn.commit_calls == 1
    assert db.last_conn.rollback_calls == 0
    assert meta["id"] == 1
    assert meta["content_sha256"] == hashlib.sha256(b"raw-v1").hexdigest()
    assert meta["raw_size_bytes"] == len(b"raw-v1")
    assert len(db.snapshots) == 1
    assert db.snapshots[0]["raw_csv"] == b"raw-v1"
    assert set(db.holdings) == {("2026-09-08", "AAA"), ("2026-09-08", "BBB")}
    assert {row["fetched_at"] for row in db.holdings.values()} == {fetched_at}


def test_repeated_identical_fetch_keeps_distinct_snapshot_ids_and_same_hash() -> None:
    db = _FakeDb()
    first_time = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(hours=1)

    first = persist_ura_holdings_snapshot(
        db,
        _snapshot("2026-09-08", raw_csv=b"same-bytes", fetched_at=first_time),
    )
    second = persist_ura_holdings_snapshot(
        db,
        _snapshot("2026-09-08", raw_csv=b"same-bytes", fetched_at=second_time),
    )

    assert first["id"] == 1
    assert second["id"] == 2
    assert first["content_sha256"] == second["content_sha256"]
    assert len(db.snapshots) == 2
    assert [row["fetched_at"] for row in db.snapshots] == [first_time, second_time]


def test_same_date_refresh_replaces_complete_canonical_set() -> None:
    db = _FakeDb()
    first_time = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(hours=1)

    persist_ura_holdings_snapshot(
        db,
        _snapshot(
            "2026-09-08",
            raw_csv=b"with-aaa-bbb",
            tickers=("AAA", "BBB"),
            fetched_at=first_time,
        ),
    )
    persist_ura_holdings_snapshot(
        db,
        _snapshot(
            "2026-09-08",
            raw_csv=b"aaa-only",
            tickers=("AAA",),
            fetched_at=second_time,
        ),
    )

    assert set(db.holdings) == {("2026-09-08", "AAA")}
    assert len(db.snapshots) == 2
    assert db.snapshots[0]["content_sha256"] != db.snapshots[1]["content_sha256"]


def test_canonical_failure_rolls_back_raw_snapshot_and_replacement() -> None:
    db = _FakeDb()
    first_time = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    persist_ura_holdings_snapshot(
        db,
        _snapshot("2026-09-08", raw_csv=b"baseline", fetched_at=first_time),
    )
    baseline_snapshots = copy.deepcopy(db.snapshots)
    baseline_holdings = copy.deepcopy(db.holdings)
    baseline_next_id = db.next_id

    db.fail_on = "canonical"
    with pytest.raises(RuntimeError):
        persist_ura_holdings_snapshot(
            db,
            _snapshot(
                "2026-09-08",
                raw_csv=b"failed-refresh",
                tickers=("AAA",),
                fetched_at=first_time + timedelta(hours=1),
            ),
        )

    assert db.snapshots == baseline_snapshots
    assert db.holdings == baseline_holdings
    assert db.next_id == baseline_next_id
    assert db.last_conn is not None
    assert db.last_conn.commit_calls == 0
    assert db.last_conn.rollback_calls == 1


def test_snapshot_refs_identify_current_and_previous_raw_sources() -> None:
    db = _FakeDb()
    first_time = datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc)
    second_time = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
    persist_ura_holdings_snapshot(
        db,
        _snapshot("2026-09-07", raw_csv=b"previous", fetched_at=first_time),
    )
    persist_ura_holdings_snapshot(
        db,
        _snapshot("2026-09-08", raw_csv=b"current", fetched_at=second_time),
    )

    refs = get_ura_holdings_snapshot_refs(
        db,
        {"current_date": "2026-09-08", "previous_date": "2026-09-07"},
    )

    assert refs["current"] is not None
    assert refs["previous"] is not None
    assert refs["current"]["id"] == 2
    assert refs["previous"]["id"] == 1
    assert refs["current"]["content_sha256"] == hashlib.sha256(b"current").hexdigest()
    assert refs["previous"]["content_sha256"] == hashlib.sha256(b"previous").hexdigest()
    assert refs["current"]["raw_size_bytes"] == len(b"current")
