from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from app.backtest.validation import classify_shadow_readiness
from app.schedule_contract import SCHEDULE_SPECS, expected_run_counts
from app.version import MODEL_VERSION

if TYPE_CHECKING:
    from app.engine import InvestmentEngine

_COMPLETED_STATUSES = {"OK", "DEGRADED", "SKIPPED"}
_SCHEDULED_RUN_KINDS = {"scheduled", "scheduled_legacy"}


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _decision_diagnostics(engine: "InvestmentEngine", epoch: dict) -> dict:
    with engine.db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select system,
                   count(*) as decisions,
                   count(distinct as_of) as decision_days,
                   percentile_cont(0.5) within group(order by edge_score) as median_edge,
                   min(edge_score) as min_edge,
                   max(edge_score) as max_edge,
                   percentile_cont(0.5) within group(order by confidence) as median_confidence,
                   percentile_cont(0.5) within group(order by data_quality) as median_quality,
                   count(*) filter(where edge_score < 45) as edge_lt_45,
                   count(*) filter(where edge_score >= 45 and edge_score < 55) as edge_45_55,
                   count(*) filter(where edge_score >= 55 and edge_score < 70) as edge_55_70,
                   count(*) filter(where edge_score >= 70 and edge_score < 80) as edge_70_80,
                   count(*) filter(where edge_score >= 80) as edge_ge_80,
                   count(*) filter(where confidence < 70) as confidence_lt_70,
                   count(*) filter(where confidence >= 70 and confidence < 80) as confidence_70_80,
                   count(*) filter(where confidence >= 80) as confidence_ge_80,
                   count(*) filter(where data_quality < 70) as quality_lt_70,
                   count(*) filter(where data_quality >= 70 and data_quality < 80) as quality_70_80,
                   count(*) filter(where data_quality >= 80 and data_quality < 90) as quality_80_90,
                   count(*) filter(where data_quality >= 90) as quality_ge_90,
                   count(*) filter(where action_event) as action_events
            from model.decisions
            where model_version=%s and created_at >= %s
            group by system
            order by system
            """,
            (epoch["model_version"], epoch["started_at"]),
        )
        aggregate_rows = cur.fetchall()

        cur.execute(
            """
            select system,status,count(*) as n
            from model.decisions
            where model_version=%s and created_at >= %s
            group by system,status order by system,status
            """,
            (epoch["model_version"], epoch["started_at"]),
        )
        status_rows = cur.fetchall()
        cur.execute(
            """
            select system,direction,count(*) as n
            from model.decisions
            where model_version=%s and created_at >= %s
            group by system,direction order by system,direction
            """,
            (epoch["model_version"], epoch["started_at"]),
        )
        direction_rows = cur.fetchall()

    out: dict[str, dict] = {}
    for row in aggregate_rows:
        system = str(row["system"])
        out[system] = {
            "decisions": int(row["decisions"] or 0),
            "decision_days": int(row["decision_days"] or 0),
            "edge": {
                "median": float(row["median_edge"] or 0),
                "min": float(row["min_edge"] or 0),
                "max": float(row["max_edge"] or 0),
                "buckets": {
                    "<45": int(row["edge_lt_45"] or 0),
                    "45-<55": int(row["edge_45_55"] or 0),
                    "55-<70": int(row["edge_55_70"] or 0),
                    "70-<80": int(row["edge_70_80"] or 0),
                    ">=80": int(row["edge_ge_80"] or 0),
                },
            },
            "confidence": {
                "median": float(row["median_confidence"] or 0),
                "buckets": {
                    "<70": int(row["confidence_lt_70"] or 0),
                    "70-<80": int(row["confidence_70_80"] or 0),
                    ">=80": int(row["confidence_ge_80"] or 0),
                },
            },
            "quality": {
                "median": float(row["median_quality"] or 0),
                "buckets": {
                    "<70": int(row["quality_lt_70"] or 0),
                    "70-<80": int(row["quality_70_80"] or 0),
                    "80-<90": int(row["quality_80_90"] or 0),
                    ">=90": int(row["quality_ge_90"] or 0),
                },
            },
            "action_events": int(row["action_events"] or 0),
            "statuses": {},
            "directions": {},
        }
    for row in status_rows:
        out.setdefault(str(row["system"]), {}).setdefault("statuses", {})[str(row["status"])] = int(row["n"] or 0)
    for row in direction_rows:
        out.setdefault(str(row["system"]), {}).setdefault("directions", {})[str(row["direction"])] = int(row["n"] or 0)
    return out


def build_shadow_observability(engine: "InvestmentEngine") -> dict:
    """Build a behavior-preserving Shadow readiness diagnostic from an explicit epoch.

    The released readiness thresholds are reused unchanged. The only change is
    accounting provenance: scheduled runs are compared with expected schedule
    fires, while manual/test/backfill/dependency/maintenance rows are excluded.
    """
    with engine.db.connection() as conn, conn.cursor() as cur:
        cur.execute("select now() as now_utc")
        now_utc = (cur.fetchone() or {}).get("now_utc") or datetime.now(timezone.utc)
        cur.execute(
            """
            select id,epoch_key,model_version,started_at,ended_at,status,details
            from model.shadow_epochs
            where status='ACTIVE' and model_version=%s
            order by started_at desc limit 1
            """,
            (MODEL_VERSION,),
        )
        epoch = cur.fetchone()
        if not epoch:
            raise RuntimeError("Aktif Shadow Epoch bulunamadı. Önce migration 0010 uygulanmalıdır.")

    window_start = max(epoch["started_at"], now_utc - timedelta(days=7))
    expected_by_job = expected_run_counts(window_start, now_utc, engine.settings.timezone)

    with engine.db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select job_name,status,run_kind,count(*) as n
            from system.job_runs
            where shadow_epoch_id=%s
              and started_at >= %s and started_at <= %s
              and run_kind = any(%s)
            group by job_name,status,run_kind
            order by job_name,status,run_kind
            """,
            (epoch["id"], window_start, now_utc, list(_SCHEDULED_RUN_KINDS)),
        )
        rows = cur.fetchall()

    actual: dict[str, dict[str, int]] = {name: {} for name in SCHEDULE_SPECS}
    for row in rows:
        job_name = str(row["job_name"])
        status = str(row["status"])
        actual.setdefault(job_name, {})[status] = actual.setdefault(job_name, {}).get(status, 0) + int(row["n"] or 0)

    breakdown: dict[str, dict] = {}
    expected_total = actual_total = completed_total = ok_total = error_total = 0
    for job_name in SCHEDULE_SPECS:
        statuses = actual.get(job_name, {})
        expected = int(expected_by_job.get(job_name, 0))
        actual_count = sum(statuses.values())
        completed = sum(count for status, count in statuses.items() if status in _COMPLETED_STATUSES)
        ok_count = int(statuses.get("OK", 0))
        error_count = int(statuses.get("ERROR", 0))
        breakdown[job_name] = {
            "expected": expected,
            "actual": actual_count,
            "completed": completed,
            "ok": ok_count,
            "errors": error_count,
            "degraded": int(statuses.get("DEGRADED", 0)),
            "skipped": int(statuses.get("SKIPPED", 0)),
            "missing": max(0, expected - actual_count),
            "unexpected_extra": max(0, actual_count - expected),
            "statuses": statuses,
        }
        expected_total += expected
        actual_total += actual_count
        completed_total += completed
        ok_total += ok_count
        error_total += error_count

    base_stats = engine.repo.shadow_readiness_stats()
    tz = ZoneInfo(engine.settings.timezone)
    calendar_days = (now_utc.astimezone(tz).date() - epoch["started_at"].astimezone(tz).date()).days + 1
    base_stats.update(
        {
            "calendar_days": max(0, calendar_days),
            "shadow_epoch_id": int(epoch["id"]),
            "shadow_epoch_key": str(epoch["epoch_key"]),
            "shadow_started_at": epoch["started_at"].isoformat(),
            "job_window_start": window_start.isoformat(),
            "job_window_end": now_utc.isoformat(),
            "job_expected_count": expected_total,
            "job_actual_count": actual_total,
            "job_completed_count": completed_total,
            "job_ok_count": ok_total,
            "job_error_count": error_total,
            "job_count": expected_total,
            # Backward-compatible classifier key: same released semantic set
            # (OK/DEGRADED/SKIPPED), now divided by expected scheduled fires.
            "job_success_rate": _rate(completed_total, expected_total),
            "job_completed_rate": _rate(completed_total, expected_total),
            "job_ok_rate": _rate(ok_total, expected_total),
            "job_capture_rate": _rate(actual_total, expected_total),
            "job_schedule_breakdown": breakdown,
        }
    )
    base_stats["decision_diagnostics"] = _decision_diagnostics(engine, epoch)
    readiness = classify_shadow_readiness(base_stats)
    return {
        "status": readiness["status"],
        "shadow_epoch": {
            "id": int(epoch["id"]),
            "key": str(epoch["epoch_key"]),
            "model_version": str(epoch["model_version"]),
            "started_at": epoch["started_at"].isoformat(),
            "status": str(epoch["status"]),
        },
        "readiness": readiness,
        "scheduler": {
            "timezone": engine.settings.timezone,
            "window_start": window_start.isoformat(),
            "window_end": now_utc.isoformat(),
            "expected": expected_total,
            "actual": actual_total,
            "completed": completed_total,
            "ok": ok_total,
            "errors": error_total,
            "capture_rate": _rate(actual_total, expected_total),
            "completed_rate": _rate(completed_total, expected_total),
            "ok_rate": _rate(ok_total, expected_total),
            "breakdown": breakdown,
        },
        "note": (
            "Tanısal hardening: threshold/weight/K1-K2/reversal/action-size/mode değiştirilmedi. "
            "DEGRADED ve SKIPPED, yayımlanmış readiness semantiğiyle tamamlanmış run kabul edilir; "
            "OK rate ayrıca görünürdür."
        ),
    }
