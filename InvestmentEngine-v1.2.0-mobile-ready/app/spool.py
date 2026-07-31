from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.paths import SPOOL_PATH, ensure_directories


class SpoolQueue:
    def __init__(self, path: Path = SPOOL_PATH) -> None:
        ensure_directories()
        self.path = Path(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""
                create table if not exists queue(
                    id integer primary key autoincrement,
                    topic text not null,
                    payload text not null,
                    created_at text not null,
                    attempts integer not null default 0,
                    last_error text
                )
            """)

    def enqueue(self, topic: str, payload: dict) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("insert into queue(topic,payload,created_at) values(?,?,?)",
                       (topic, json.dumps(payload, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))

    def pending(self, limit: int = 100) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(x) for x in db.execute("select * from queue order by id limit ?", (limit,)).fetchall()]

    def ack(self, item_id: int) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("delete from queue where id=?", (item_id,))

    def fail(self, item_id: int, error: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("update queue set attempts=attempts+1,last_error=? where id=?", (error[:500], item_id))
