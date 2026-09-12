from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.collectors.globalx_ura import UraHoldingsSnapshot
from app.database.db import DatabaseService


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def persist_ura_holdings_snapshot(
    db: DatabaseService,
    snapshot: UraHoldingsSnapshot,
) -> dict[str, Any]:
    """Persist one immutable raw fetch and replace its canonical holdings day.

    The raw snapshot insert and canonical delete+insert share one transaction.
    A failure therefore leaves neither a partial raw snapshot nor a mixed
    canonical constituent set behind.
    """
    rows = list(snapshot.holdings)
    if not rows:
        raise ValueError("URA holdings snapshot boş olamaz.")

    holding_date = str(snapshot.holding_date)
    if any(str(row.holding_date) != holding_date for row in rows):
        raise ValueError("URA holdings snapshot içinde birden fazla holding_date var.")

    tickers = [str(row.ticker).strip() for row in rows]
    if any(not ticker for ticker in tickers):
        raise ValueError("URA holdings snapshot boş ticker içeremez.")
    if len(set(tickers)) != len(tickers):
        raise ValueError("URA holdings snapshot aynı ticker'ı birden fazla kez içeriyor.")

    raw_csv = bytes(snapshot.raw_csv or b"")
    if not raw_csv:
        raise ValueError("URA holdings raw CSV boş olamaz.")

    fetched_at = snapshot.fetched_at or datetime.now(timezone.utc)
    content_sha256 = hashlib.sha256(raw_csv).hexdigest()
    source_url = str(snapshot.source_url or "")

    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into fundamentals.ura_holdings_snapshots(
              holding_date,source_url,fetched_at,content_sha256,raw_csv,constituent_count
            ) values(%s,%s,%s,%s,%s,%s)
            returning id,fetched_at
            """,
            (
                holding_date,
                source_url,
                fetched_at,
                content_sha256,
                raw_csv,
                len(rows),
            ),
        )
        inserted = cur.fetchone()
        if not inserted:
            raise RuntimeError("URA holdings raw snapshot insert id döndürmedi.")

        # The issuer CSV is a complete dated holdings snapshot. Replacing the
        # whole day prevents a removed ticker from surviving a same-date refresh.
        cur.execute(
            "delete from fundamentals.ura_holdings where holding_date=%s",
            (holding_date,),
        )
        cur.executemany(
            """
            insert into fundamentals.ura_holdings(
              holding_date,ticker,name,weight,shares,market_value,market_price,
              source_url,fetched_at
            ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            [
                (
                    row.holding_date,
                    row.ticker,
                    row.name,
                    row.weight,
                    row.shares,
                    row.market_value,
                    row.market_price,
                    row.source_url,
                    fetched_at,
                )
                for row in rows
            ],
        )
        conn.commit()

    return {
        "id": int(inserted["id"]),
        "holding_date": holding_date,
        "source_url": source_url,
        "fetched_at": _iso(inserted.get("fetched_at") or fetched_at),
        "content_sha256": content_sha256,
        "constituent_count": len(rows),
        "raw_size_bytes": len(raw_csv),
    }


def get_ura_holdings_snapshot_refs(
    db: DatabaseService,
    summary: dict | None,
) -> dict[str, dict[str, Any] | None]:
    """Return current/prior raw snapshot identities used by fundamentals scoring."""
    refs: dict[str, dict[str, Any] | None] = {"current": None, "previous": None}
    if not summary:
        return refs

    with db.connection() as conn, conn.cursor() as cur:
        for role, key in (("current", "current_date"), ("previous", "previous_date")):
            holding_date = summary.get(key)
            if not holding_date:
                continue
            cur.execute(
                """
                select id,holding_date,source_url,fetched_at,content_sha256,
                       constituent_count,octet_length(raw_csv) as raw_size_bytes
                from fundamentals.ura_holdings_snapshots
                where holding_date=%s
                order by fetched_at desc,id desc
                limit 1
                """,
                (holding_date,),
            )
            row = cur.fetchone()
            if not row:
                continue
            refs[role] = {
                "id": int(row["id"]),
                "holding_date": str(row["holding_date"]),
                "source_url": str(row.get("source_url") or ""),
                "fetched_at": _iso(row.get("fetched_at")),
                "content_sha256": str(row.get("content_sha256") or ""),
                "constituent_count": int(row.get("constituent_count") or 0),
                "raw_size_bytes": int(row.get("raw_size_bytes") or 0),
            }
    return refs
