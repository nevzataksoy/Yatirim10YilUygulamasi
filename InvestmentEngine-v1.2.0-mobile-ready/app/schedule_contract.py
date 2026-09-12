from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# One source of truth for scheduler cadence and readiness expected-run accounting.
SCHEDULE_SPECS: dict[str, dict] = {
    "hourly_job": {"minute": 5},
    "macro_job": {"hour": "0,6,12,18", "minute": 15},
    "sec_event_job": {"minute": 35},
    "daily_crypto_job": {"hour": 5, "minute": 20},
    "daily_ura_job": {"hour": 2, "minute": 40},
    "daily_fx_job": {"day_of_week": "mon-fri", "hour": 16, "minute": 30},
    "weekly_job": {"day_of_week": "sat", "hour": 8, "minute": 0},
    "monthly_audit_job": {"day": 1, "hour": 9, "minute": 0},
}


def _as_int_set(value, *, default: set[int]) -> set[int]:
    if value is None:
        return default
    if isinstance(value, int):
        return {value}
    return {int(part) for part in str(value).split(",")}


def _weekday_allowed(value, weekday: int) -> bool:
    if value is None:
        return True
    if value == "mon-fri":
        return weekday <= 4
    names = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    allowed = {names[part.strip()] for part in str(value).split(",")}
    return weekday in allowed


def schedule_matches(local_minute: datetime, spec: dict) -> bool:
    if local_minute.minute not in _as_int_set(spec.get("minute"), default=set(range(60))):
        return False
    if local_minute.hour not in _as_int_set(spec.get("hour"), default=set(range(24))):
        return False
    if spec.get("day") is not None and local_minute.day not in _as_int_set(spec.get("day"), default=set()):
        return False
    return _weekday_allowed(spec.get("day_of_week"), local_minute.weekday())


def expected_run_counts(started_at: datetime, ended_at: datetime, timezone_name: str) -> dict[str, int]:
    """Count scheduler fire times in an inclusive interval using the shared cadence contract."""
    if started_at.tzinfo is None or ended_at.tzinfo is None:
        raise ValueError("Expected-run interval datetimes must be timezone-aware.")
    if ended_at < started_at:
        raise ValueError("Expected-run interval end precedes start.")

    tz = ZoneInfo(timezone_name)
    start_local = started_at.astimezone(tz)
    end_local = ended_at.astimezone(tz)
    cursor = start_local.replace(second=0, microsecond=0)
    if cursor < start_local:
        cursor += timedelta(minutes=1)

    counts = {name: 0 for name in SCHEDULE_SPECS}
    while cursor <= end_local:
        for job_name, spec in SCHEDULE_SPECS.items():
            if schedule_matches(cursor, spec):
                counts[job_name] += 1
        cursor += timedelta(minutes=1)
    return counts
