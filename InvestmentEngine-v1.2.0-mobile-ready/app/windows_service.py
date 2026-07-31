from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

from app.engine import InvestmentEngine
from app.logging_config import configure_logging
from app.paths import BUNDLE_DIR, SETTINGS_PATH, LOCK_PATH
from app.scheduler import build_scheduler
from app.security.settings_store import SettingsStore

LOG = logging.getLogger(__name__)
SERVICE_NAME = "RosaInvestmentEngine"
SERVICE_DISPLAY_NAME = "Rosa Investment Engine"
SERVICE_DESCRIPTION = (
    "BTC/ETH ve URA veri toplama, karar destek ve Telegram servisidir. "
    "Otomatik emir vermez."
)


class RosaInvestmentEngineService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.engine: InvestmentEngine | None = None
        self.scheduler = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        try:
            configure_logging()
            store = SettingsStore()
            settings = store.load()
            if settings is None:
                raise RuntimeError(
                    f"Settings bulunamadı. Önce EXE'yi yönetici olarak açıp ayarları kaydedin: {SETTINGS_PATH}"
                )
            self.engine = InvestmentEngine(settings, BUNDLE_DIR)
            self.engine.start()
            self.scheduler = build_scheduler(self.engine, settings.timezone)
            self.scheduler.start()
            servicemanager.LogInfoMsg(f"{SERVICE_NAME} started")
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except Exception as exc:
            LOG.exception("Windows service failed")
            try:
                servicemanager.LogErrorMsg(f"{SERVICE_NAME} failed: {exc}")
            except Exception:
                pass
            raise
        finally:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            if self.engine:
                self.engine.stop()
            try:
                servicemanager.LogInfoMsg(f"{SERVICE_NAME} stopped")
            except Exception:
                pass


def run_service_dispatcher() -> None:
    """Enter the Windows Service Control Manager dispatcher.

    The Inno Setup installer registers the same one-file EXE with the --service
    argument, so no Python runtime or second service executable is required.
    """
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(RosaInvestmentEngineService)
    servicemanager.StartServiceCtrlDispatcher()


def _require_frozen_executable() -> Path:
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "Service kurulum komutları paketlenmiş InvestmentEngine.exe üzerinden çalıştırılmalıdır."
        )
    return Path(sys.executable).resolve()


def _run_sc(*args: str, tolerate: bool = False) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        ["sc.exe", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if cp.returncode != 0 and not tolerate:
        msg = (cp.stdout + "\n" + cp.stderr).strip()
        raise RuntimeError(f"sc.exe başarısız ({cp.returncode}): {msg}")
    return cp


def _query_state() -> str:
    cp = _run_sc("query", SERVICE_NAME, tolerate=True)
    text = (cp.stdout + "\n" + cp.stderr).upper()
    if cp.returncode != 0:
        return "MISSING"
    for state in ("RUNNING", "STOPPED", "START_PENDING", "STOP_PENDING", "PAUSED"):
        if state in text:
            return state
    return "UNKNOWN"


def _wait_state(target: str, timeout_seconds: int = 30) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _query_state() == target:
            return True
        time.sleep(0.5)
    return _query_state() == target


def install_service() -> None:
    exe = _require_frozen_executable()
    # Remove an old registration only when it exists. Generated settings are not touched.
    if _query_state() not in {"MISSING", "STOPPED"}:
        _run_sc("stop", SERVICE_NAME, tolerate=True)
        _wait_state("STOPPED", 30)
    _run_sc("delete", SERVICE_NAME, tolerate=True)
    _wait_state("MISSING", 15)

    bin_path = f'"{exe}" --service'
    _run_sc(
        "create",
        SERVICE_NAME,
        "binPath=",
        bin_path,
        "start=",
        "auto",
        "DisplayName=",
        SERVICE_DISPLAY_NAME,
    )
    _run_sc("description", SERVICE_NAME, SERVICE_DESCRIPTION)
    _run_sc(
        "failure",
        SERVICE_NAME,
        "reset=",
        "86400",
        "actions=",
        "restart/5000/restart/15000/restart/60000",
    )
    _run_sc("failureflag", SERVICE_NAME, "1", tolerate=True)


def uninstall_service() -> None:
    if _query_state() not in {"MISSING", "STOPPED"}:
        _run_sc("stop", SERVICE_NAME, tolerate=True)
        _wait_state("STOPPED", 30)
    _run_sc("delete", SERVICE_NAME, tolerate=True)
    _wait_state("MISSING", 15)


def start_service() -> None:
    if not SETTINGS_PATH.is_file() or not LOCK_PATH.is_file():
        raise RuntimeError(
            "settings/rosalock bulunamadı. Servis başlatılmadan önce ayarlar kaydedilmelidir."
        )
    if _query_state() == "RUNNING":
        return
    _run_sc("start", SERVICE_NAME)
    if not _wait_state("RUNNING", 45):
        raise RuntimeError(f"Service RUNNING durumuna geçmedi. Son durum: {_query_state()}")


def stop_service() -> None:
    state = _query_state()
    if state in {"MISSING", "STOPPED"}:
        return
    _run_sc("stop", SERVICE_NAME, tolerate=True)
    _wait_state("STOPPED", 30)


def service_status() -> str:
    cp = _run_sc("query", SERVICE_NAME, tolerate=True)
    return (cp.stdout + "\n" + cp.stderr).strip()
