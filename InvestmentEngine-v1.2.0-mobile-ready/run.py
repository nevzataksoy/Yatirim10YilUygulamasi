from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
from datetime import datetime, timezone

from app.engine import InvestmentEngine
from app.logging_config import configure_logging
from app.observability import build_shadow_observability
from app.paths import BUNDLE_DIR, LOG_DIR
from app.run_context import job_run_context
from app.scheduler import build_scheduler
from app.security.settings_store import SettingsStore
from app.ui.configure import configure_settings


_CLI_FLAGS = {
    "--install-service",
    "--uninstall-service",
    "--start-service",
    "--stop-service",
    "--service-status",
    "--run-foreground",
    "--once",
    "--test-realtime",
    "--validate-model",
    "--backfill-crypto",
    "--shadow-observability",
}
_CLI_ATTACHED = False


def _attach_parent_console() -> bool:
    """Best-effort console attachment for the single --windowed EXE.

    CLI commands never fall back to a QMessageBox.  `InvestmentEngineCLI.cmd`
    is included for a blocking terminal workflow on Windows.
    """
    global _CLI_ATTACHED
    if sys.platform != "win32":
        _CLI_ATTACHED = True
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ATTACH_PARENT_PROCESS = 0xFFFFFFFF
        attached = bool(kernel32.GetConsoleWindow())
        if not attached:
            attached = bool(kernel32.AttachConsole(ATTACH_PARENT_PROCESS))
        if attached:
            # `os.fdopen` around CONOUT$ is more reliable in a PyInstaller GUI
            # executable than assuming sys.stdout exists.
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            _CLI_ATTACHED = True
        return attached
    except Exception:
        return False


def _emit_cli(message: str) -> None:
    if _CLI_ATTACHED and sys.stdout is not None:
        try:
            print(message, flush=True)
            return
        except Exception:
            pass
    # Never show GUI alerts for terminal commands. If console attachment is not
    # possible, leave an auditable result beside the normal engine log.
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "investment-engine-cli.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")
    except Exception:
        pass


def _load_engine(*, publish_engine_health: bool) -> InvestmentEngine | None:
    """Open an engine process without letting one-shot CLI tools impersonate the service.

    Only long-lived scheduler owners (Windows service / --run-foreground) may
    publish the shared ENGINE lifecycle row. Diagnostic and maintenance CLI
    commands still need the DB pool, but must not overwrite a running service's
    ENGINE=OK state when their short-lived process exits.
    """
    store = SettingsStore()
    if not store.is_configured:
        if not configure_settings(force_unlock=False):
            return None
    settings = store.load()
    if settings is None:
        return None
    configure_logging()
    engine = InvestmentEngine(settings, BUNDLE_DIR)
    if publish_engine_health:
        engine.start()
    else:
        engine.db.open()
    return engine


def _close_engine(engine: InvestmentEngine, *, publish_engine_health: bool) -> None:
    if publish_engine_health:
        engine.stop()
    else:
        engine.db.close()


def _run_foreground(once: str | None = None) -> int:
    owns_engine_health = once is None
    engine = _load_engine(publish_engine_health=owns_engine_health)
    if engine is None:
        return 2
    try:
        if once:
            jobs = {
                "crypto": (engine.daily_crypto_job, "daily_crypto_job"),
                "ura": (engine.daily_ura_job, "daily_ura_job"),
                "hourly": (engine.hourly_job, "hourly_job"),
                "macro": (engine.macro_job, "macro_job"),
                "fx": (engine.daily_fx_job, "daily_fx_job"),
                "events": (engine.sec_event_job, "sec_event_job"),
                "weekly": (engine.weekly_job, "weekly_job"),
                "monthly": (engine.monthly_audit_job, "monthly_audit_job"),
            }
            job, job_name = jobs[once]
            _emit_cli(f"{job_name} çalıştırılıyor...")
            with job_run_context(job_name, "manual"):
                job()
            row = engine.repo.get_latest_job_run(job_name)
            if not row:
                _emit_cli(f"{job_name}: job kaydı oluşmadı.")
                return 1
            status = str(row.get("status") or "UNKNOWN")
            message = str(row.get("message") or "").strip()
            suffix = f" — {message}" if message else ""
            _emit_cli(f"{job_name}: {status}{suffix}")
            return 0 if status in {"OK", "DEGRADED", "SKIPPED"} else 1

        scheduler = build_scheduler(engine, engine.settings.timezone)
        scheduler.start()
        stop = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, lambda *_: stop.set())
        stop.wait()
        scheduler.shutdown(wait=False)
        return 0
    finally:
        _close_engine(engine, publish_engine_health=owns_engine_health)


def _run_realtime_smoke(duration: int) -> int:
    engine = _load_engine(publish_engine_health=False)
    if engine is None:
        return 2
    try:
        _emit_cli(f"Coinbase realtime smoke test başlatılıyor ({duration} sn)...")
        with job_run_context("realtime_test", "test"):
            details = engine.realtime_smoke_test(duration)
        _emit_cli(
            "realtime_test: OK — "
            f"run={details['test_run_id']} snapshots={details['snapshots']} products={','.join(details['products'])}"
        )
        return 0
    except Exception as exc:
        _emit_cli(f"realtime_test: ERROR — {exc}")
        return 1
    finally:
        _close_engine(engine, publish_engine_health=False)


def _run_model_validation() -> int:
    engine = _load_engine(publish_engine_health=False)
    if engine is None:
        return 2
    try:
        _emit_cli("Model validation başlatılıyor...")
        with job_run_context("model_validation_job", "manual"):
            result = engine.model_validation_job()
        shadow = result.get("shadow_readiness") or {}
        core = result.get("ethbtc_core") or {}
        calibration = result.get("calibration") or {}
        candidate = calibration.get("best_candidate")
        candidate_text = (
            f" candidate_edge={candidate['edge_threshold']}"
            if isinstance(candidate, dict) and candidate.get("edge_threshold") is not None
            else ""
        )
        _emit_cli(
            "model_validation: OK — "
            f"core={core.get('status')} observations={core.get('observations', 0)} "
            f"shadow={shadow.get('status')}{candidate_text}"
        )
        return 0
    except Exception as exc:
        _emit_cli(f"model_validation: ERROR — {exc}")
        return 1
    finally:
        _close_engine(engine, publish_engine_health=False)


def _run_crypto_backfill(days: int) -> int:
    engine = _load_engine(publish_engine_health=False)
    if engine is None:
        return 2
    try:
        _emit_cli(f"Crypto history backfill başlatılıyor ({days} gün)...")
        with job_run_context("crypto_history_backfill", "backfill"):
            details = engine.backfill_crypto_history(days)
        _emit_cli(
            "crypto_history_backfill: OK — "
            f"provider={details['provider']} common_days={details['common_days']}"
        )
        return 0
    except Exception as exc:
        _emit_cli(f"crypto_history_backfill: ERROR — {exc}")
        return 1
    finally:
        _close_engine(engine, publish_engine_health=False)


def _run_shadow_observability() -> int:
    engine = _load_engine(publish_engine_health=False)
    if engine is None:
        return 2
    started = datetime.now(timezone.utc)
    try:
        _emit_cli("Shadow observability raporu hazırlanıyor...")
        with job_run_context("shadow_observability", "manual"):
            result = build_shadow_observability(engine)
            status = str(result.get("status") or "UNKNOWN")
            readiness = result.get("readiness") or {}
            stats = readiness.get("stats") or {}
            engine.repo.insert_validation_run(
                validation_type="SHADOW_OBSERVABILITY",
                system="ALL",
                status=status,
                started_at=started,
                start_date=None,
                end_date=None,
                observations=None,
                signals=None,
                metrics=result,
                details={"behavior_change": False, "source": "task4-hardening"},
            )
            engine.repo.publish_validation_snapshot(
                validation_type="SHADOW_OBSERVABILITY",
                system="ALL",
                status=status,
                start_date=None,
                end_date=None,
                metrics=result,
                details={"behavior_change": False, "source": "task4-hardening"},
            )
            engine.repo.log_job(
                "shadow_observability",
                "OK",
                started,
                details={
                    "status": status,
                    "shadow_epoch_key": stats.get("shadow_epoch_key"),
                    "job_completed_rate": stats.get("job_completed_rate"),
                    "job_ok_rate": stats.get("job_ok_rate"),
                },
            )
        _emit_cli(
            "shadow_observability: "
            f"{status} — epoch={stats.get('shadow_epoch_key')} "
            f"scheduled={stats.get('job_actual_count')}/{stats.get('job_expected_count')} "
            f"completed={float(stats.get('job_completed_rate') or 0):.3%} "
            f"ok={float(stats.get('job_ok_rate') or 0):.3%}"
        )
        _emit_cli(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        _emit_cli(f"shadow_observability: ERROR — {exc}")
        return 1
    finally:
        _close_engine(engine, publish_engine_health=False)


def main() -> int:
    if any(flag in sys.argv[1:] for flag in _CLI_FLAGS):
        _attach_parent_console()

    parser = argparse.ArgumentParser(description="Rosa Investment Engine")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--service", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--install-service", action="store_true")
    parser.add_argument("--uninstall-service", action="store_true")
    parser.add_argument("--start-service", action="store_true")
    parser.add_argument("--stop-service", action="store_true")
    parser.add_argument("--service-status", action="store_true")
    parser.add_argument("--run-foreground", action="store_true")
    parser.add_argument("--test-realtime", action="store_true")
    parser.add_argument("--validate-model", action="store_true")
    parser.add_argument("--backfill-crypto", action="store_true")
    parser.add_argument("--shadow-observability", action="store_true")
    parser.add_argument("--history-days", type=int, default=2500)
    parser.add_argument("--realtime-seconds", type=int, default=20)
    parser.add_argument(
        "--once",
        choices=["crypto", "ura", "hourly", "macro", "fx", "events", "weekly", "monthly"],
    )
    args = parser.parse_args()

    if args.service:
        from app.windows_service import run_service_dispatcher

        run_service_dispatcher()
        return 0

    if any(
        [
            args.install_service,
            args.uninstall_service,
            args.start_service,
            args.stop_service,
            args.service_status,
        ]
    ):
        from app.windows_service import (
            install_service,
            service_status,
            start_service,
            stop_service,
            uninstall_service,
        )

        if args.install_service:
            install_service()
            _emit_cli("RosaInvestmentEngine servisi kuruldu.")
        elif args.uninstall_service:
            uninstall_service()
            _emit_cli("RosaInvestmentEngine servisi kaldırıldı.")
        elif args.start_service:
            start_service()
            _emit_cli("RosaInvestmentEngine servisi başlatıldı.")
        elif args.stop_service:
            stop_service()
            _emit_cli("RosaInvestmentEngine servisi durduruldu.")
        else:
            _emit_cli(service_status())
        return 0

    store = SettingsStore()
    if args.configure:
        return 0 if configure_settings(force_unlock=store.is_configured) else 2

    if args.test_realtime:
        return _run_realtime_smoke(args.realtime_seconds)

    if args.validate_model:
        return _run_model_validation()

    if args.backfill_crypto:
        return _run_crypto_backfill(args.history_days)

    if args.shadow_observability:
        return _run_shadow_observability()

    if args.once or args.run_foreground:
        return _run_foreground(args.once)

    # Double-click behavior: this EXE is the configuration frontend. The 24/7
    # scheduler belongs to the Windows service and is never started twice by a
    # normal GUI launch.
    return 0 if configure_settings(force_unlock=store.is_configured) else 2


if __name__ == "__main__":
    raise SystemExit(main())
