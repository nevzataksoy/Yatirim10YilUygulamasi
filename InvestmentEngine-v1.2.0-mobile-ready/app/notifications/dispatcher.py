from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.notifications.fcm import FcmClient, FirebaseNotConfigured

if TYPE_CHECKING:
    from app.database.db import DatabaseService

LOG = logging.getLogger(__name__)


class NotificationDispatcher:
    """Drain notification outbox without affecting investment-engine health.

    The job is deliberately outside SCHEDULE_SPECS so Shadow scheduler readiness
    keeps measuring only the released market/model contract.
    """

    def __init__(self, db: "DatabaseService") -> None:
        self.db = db

    def run_once(self, limit: int = 20) -> dict[str, int]:
        summary = {"queued": 0, "processed": 0, "sent": 0, "failed": 0, "skipped": 0}
        try:
            summary["queued"] = self._enqueue_due()
            rows = self._claim(limit)
        except Exception as exc:
            # Most commonly: migration 0011 is not applied yet. Notifications are
            # optional and must never stop market/model jobs or the Windows service.
            LOG.debug("notification dispatcher unavailable: %s", exc)
            return summary

        for row in rows:
            summary["processed"] += 1
            try:
                status = self._process(row)
            except Exception as exc:  # pragma: no cover - defensive boundary
                LOG.exception("notification outbox %s failed", row.get("id"))
                self._finish(row["id"], "FAILED", str(exc)[:1000])
                status = "FAILED"
            if status == "SENT":
                summary["sent"] += 1
            elif status == "SKIPPED":
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
        return summary

    def _enqueue_due(self) -> int:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("select public.enqueue_due_portfolio_notifications(now()) as count")
            row = cur.fetchone() or {}
            conn.commit()
            return int(row.get("count") or 0)

    def _claim(self, limit: int) -> list[dict]:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                update public.notification_outbox
                set status='PENDING', locked_at=null
                where status='PROCESSING' and locked_at < now()-interval '10 minutes'
            """)
            cur.execute("""
                select * from public.notification_outbox
                where status='PENDING' and available_at <= now()
                order by id
                for update skip locked
                limit %s
            """, (limit,))
            rows = list(cur.fetchall())
            if rows:
                ids = [row["id"] for row in rows]
                cur.execute("""
                    update public.notification_outbox
                    set status='PROCESSING', locked_at=now(), attempts=attempts+1
                    where id = any(%s)
                """, (ids,))
            conn.commit()
            return rows

    @staticmethod
    def _format_number(value: Any, digits: int = 2) -> str:
        try:
            number = Decimal(str(value))
            return f"{number:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")
        except Exception:
            return str(value or "0")

    @staticmethod
    def _render(template: str, context: dict[str, Any]) -> str:
        result = str(template or "")
        for key, value in context.items():
            result = result.replace("{{" + key + "}}", str(value if value is not None else ""))
        return result

    def _load_context(self, row: dict, template: dict) -> dict[str, Any]:
        context = dict(row.get("context") or {})
        if row.get("event_type") == "PORTFOLIO_DAILY":
            account_id = template.get("account_id") or context.get("account_id")
            display_currency = template.get("display_currency") or context.get("display_currency") or "USD"
            with self.db.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "select public.notification_portfolio_value(%s,%s) as valuation",
                    (account_id, display_currency),
                )
                valuation = (cur.fetchone() or {}).get("valuation") or {}
                cur.execute("select name from public.investment_accounts where id=%s", (account_id,))
                account = cur.fetchone() or {}
            context.update(valuation)
            context["portfolio_value"] = self._format_number(valuation.get("value"), 2)
            context["display_currency"] = display_currency
            context["account_name"] = account.get("name") or "Portföy"
            context.setdefault("route", "/portfolio")
        else:
            for key in ("edge", "confidence", "data_quality"):
                if key in context:
                    context[key] = self._format_number(context[key], 1)
            context.setdefault("route", "/signals")
        return context

    def _process(self, row: dict) -> str:
        if row.get("event_type") == "SIGNAL_CREATED":
            created_at = row.get("created_at")
            if created_at is not None:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
                if age_seconds > 6 * 60 * 60:
                    self._finish(row["id"], "SKIPPED", "Signal notification is older than 6 hours")
                    return "SKIPPED"

        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("select * from public.notification_templates where id=%s", (row.get("template_id"),))
            template = cur.fetchone()
            if not template or not template.get("enabled"):
                self._finish(row["id"], "SKIPPED", "Template disabled or missing")
                return "SKIPPED"
            cur.execute("select * from public.push_provider_settings where user_id=%s", (row["user_id"],))
            provider = cur.fetchone() or {}
            cur.execute("""
                select * from public.notification_devices
                where user_id=%s and is_active=true and permission_status='GRANTED'
                  and nullif(push_target,'') is not null
                order by last_seen_at desc
            """, (row["user_id"],))
            devices = list(cur.fetchall())

        context = self._load_context(row, template)
        title = self._render(template.get("title_template") or "Yatırım 10Yıl", context)
        body = self._render(template.get("body_template") or "", context)

        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.notification_messages
                  (user_id,template_id,outbox_id,event_type,title,body,payload)
                values (%s,%s,%s,%s,%s,%s,%s::jsonb)
                on conflict(outbox_id) where outbox_id is not null do update set
                  title=excluded.title, body=excluded.body, payload=excluded.payload
                returning id
            """, (
                row["user_id"], template["id"], row["id"], row["event_type"],
                title, body, json.dumps(context, ensure_ascii=False, default=str),
            ))
            message_id = str((cur.fetchone() or {})["id"])
            conn.commit()

        if not provider.get("enabled"):
            self._finish(row["id"], "SKIPPED", "FCM provider disabled")
            return "SKIPPED"
        if not devices:
            self._finish(row["id"], "SKIPPED", "No active push device")
            return "SKIPPED"

        try:
            fcm = FcmClient(provider.get("firebase_project_id"))
        except FirebaseNotConfigured as exc:
            self._log_without_device(row, template, message_id, "SKIPPED", str(exc))
            self._finish(row["id"], "SKIPPED", str(exc))
            return "SKIPPED"

        successes = 0
        failures = 0
        for device in devices:
            data = {**context, "message_id": message_id, "event_type": row["event_type"]}
            try:
                provider_message_id = fcm.send(
                    target=device["push_target"],
                    target_kind=device.get("target_kind") or "TOKEN",
                    title=title,
                    body=body,
                    data=data,
                )
                successes += 1
                self._log_delivery(row, template, message_id, device["id"], "SENT", provider_message_id, None)
            except Exception as exc:
                failures += 1
                self._log_delivery(row, template, message_id, device["id"], "FAILED", None, str(exc)[:1000])

        if successes:
            self._finish(row["id"], "SENT", None)
            return "SENT"
        self._finish(row["id"], "FAILED", f"All {failures} device sends failed")
        return "FAILED"

    def _log_delivery(self, row: dict, template: dict, message_id: str, device_id: str, status: str,
                      provider_message_id: str | None, error: str | None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.notification_logs
                  (user_id,message_id,template_id,device_id,provider,status,provider_message_id,error_message)
                values (%s,%s,%s,%s,'FCM',%s,%s,%s)
            """, (row["user_id"], message_id, template["id"], device_id, status, provider_message_id, error))
            conn.commit()

    def _log_without_device(self, row: dict, template: dict, message_id: str, status: str, error: str) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                insert into public.notification_logs
                  (user_id,message_id,template_id,provider,status,error_message)
                values (%s,%s,%s,'FCM',%s,%s)
            """, (row["user_id"], message_id, template["id"], status, error[:1000]))
            conn.commit()

    def _finish(self, outbox_id: int, status: str, error: str | None) -> None:
        with self.db.connection() as conn, conn.cursor() as cur:
            cur.execute("""
                update public.notification_outbox
                set status=%s, processed_at=now(), last_error=%s
                where id=%s
            """, (status, error, outbox_id))
            conn.commit()
