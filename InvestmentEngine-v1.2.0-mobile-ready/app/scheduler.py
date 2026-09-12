from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.engine import InvestmentEngine
from app.notifications.dispatcher import NotificationDispatcher
from app.run_context import contextual_job
from app.schedule_contract import SCHEDULE_SPECS

LOG = logging.getLogger(__name__)


def build_scheduler(engine: InvestmentEngine, timezone_name: str) -> BackgroundScheduler:
    tz = ZoneInfo(timezone_name)
    scheduler = BackgroundScheduler(
        timezone=tz,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 1800},
    )
    for job_name, cron_kwargs in SCHEDULE_SPECS.items():
        job = getattr(engine, job_name)
        scheduler.add_job(
            contextual_job(job, job_name, "scheduled"),
            CronTrigger(timezone=tz, **cron_kwargs),
            id=job_name,
            replace_existing=True,
        )

    # Notification delivery is an optional maintenance concern, not part of the
    # released Shadow scheduler/readiness contract. Keeping it out of
    # SCHEDULE_SPECS prevents push availability from changing model readiness.
    notification_dispatcher = NotificationDispatcher(engine.db)
    scheduler.add_job(
        contextual_job(notification_dispatcher.run_once, "notification_dispatcher", "maintenance"),
        CronTrigger(timezone=tz, minute="*"),
        id="notification_dispatcher",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    return scheduler
