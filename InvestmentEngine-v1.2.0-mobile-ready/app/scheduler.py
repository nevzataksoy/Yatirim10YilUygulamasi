from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.engine import InvestmentEngine

LOG=logging.getLogger(__name__)


def build_scheduler(engine: InvestmentEngine, timezone_name: str) -> BackgroundScheduler:
    tz=ZoneInfo(timezone_name); s=BackgroundScheduler(timezone=tz,job_defaults={"coalesce":True,"max_instances":1,"misfire_grace_time":1800})
    s.add_job(engine.hourly_job,CronTrigger(minute=5,timezone=tz),id="hourly_job",replace_existing=True)
    s.add_job(engine.macro_job,CronTrigger(hour="0,6,12,18",minute=15,timezone=tz),id="macro_job",replace_existing=True)
    s.add_job(engine.sec_event_job,CronTrigger(minute=35,timezone=tz),id="sec_event_job",replace_existing=True)
    s.add_job(engine.daily_crypto_job,CronTrigger(hour=5,minute=20,timezone=tz),id="daily_crypto_job",replace_existing=True)
    s.add_job(engine.daily_ura_job,CronTrigger(hour=2,minute=40,timezone=tz),id="daily_ura_job",replace_existing=True)
    s.add_job(engine.daily_fx_job,CronTrigger(day_of_week="mon-fri",hour=16,minute=30,timezone=tz),id="daily_fx_job",replace_existing=True)
    s.add_job(engine.weekly_job,CronTrigger(day_of_week="sat",hour=8,minute=0,timezone=tz),id="weekly_job",replace_existing=True)
    s.add_job(engine.monthly_audit_job,CronTrigger(day=1,hour=9,minute=0,timezone=tz),id="monthly_audit_job",replace_existing=True)
    return s
