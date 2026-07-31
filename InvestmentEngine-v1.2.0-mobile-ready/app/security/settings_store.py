from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.models import AppSettings, SettingsValidationError
from app.paths import LOCK_PATH, SETTINGS_PATH, ensure_directories
from app.security.cryptography_service import (
    LOCK_ENTROPY,
    SETTINGS_ENTROPY,
    CryptographyError,
    DpapiProtector,
    create_password_record,
    verify_password_record,
)

SETTINGS_MAGIC = b"IES1"
LOCK_MAGIC = b"IRL1"


class SettingsStoreError(RuntimeError):
    pass


class SettingsStore:
    def __init__(
        self,
        settings_path: Path = SETTINGS_PATH,
        lock_path: Path = LOCK_PATH,
        protector: DpapiProtector | None = None,
    ) -> None:
        ensure_directories()
        self.settings_path = Path(settings_path)
        self.lock_path = Path(lock_path)
        # LocalMachine scope is intentional: the same encrypted settings must be
        # readable by the LocalSystem Windows service after reboot.
        self._protector = protector or DpapiProtector(machine_scope=True)

    @property
    def is_configured(self) -> bool:
        return self.settings_path.is_file() and self.lock_path.is_file()

    def load(self) -> AppSettings | None:
        if not self.is_configured:
            return None
        try:
            raw = self.settings_path.read_bytes()
            if not raw.startswith(SETTINGS_MAGIC):
                raise SettingsStoreError("Settings dosya imzası geçersiz.")
            plaintext = self._protector.unprotect(
                raw[len(SETTINGS_MAGIC) :], SETTINGS_ENTROPY
            )
            document = json.loads(plaintext.decode("utf-8"))
            if document.get("version") not in {1, 2}:
                raise SettingsStoreError("Settings sürümü desteklenmiyor.")
            return AppSettings.from_dict(document["settings"])
        except SettingsStoreError:
            raise
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            CryptographyError,
            SettingsValidationError,
        ) as exc:
            raise SettingsStoreError(f"Settings okunamadı: {exc}") from exc

    def save(self, settings: AppSettings, settings_password: str) -> None:
        settings.validate()
        try:
            settings_doc = {"version": 2, "settings": settings.to_dict()}
            lock_doc = {
                "version": 1,
                "password_record": create_password_record(settings_password),
            }
            settings_bytes = SETTINGS_MAGIC + self._protector.protect(
                json.dumps(
                    settings_doc, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                SETTINGS_ENTROPY,
            )
            lock_bytes = LOCK_MAGIC + self._protector.protect(
                json.dumps(lock_doc, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                ),
                LOCK_ENTROPY,
            )
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_temp = self._write_temp(self.settings_path, settings_bytes)
            lock_temp = self._write_temp(self.lock_path, lock_bytes)
            # Replace the lock first. If the second replace fails, the old
            # settings are never left unencrypted.
            os.replace(lock_temp, self.lock_path)
            os.replace(settings_temp, self.settings_path)
            self._secure_windows_acl(self.lock_path)
            self._secure_windows_acl(self.settings_path)
        except (OSError, CryptographyError, SettingsValidationError) as exc:
            raise SettingsStoreError(f"Ayarlar kaydedilemedi: {exc}") from exc

    def verify_settings_password(self, password: str) -> bool:
        if not self.lock_path.is_file():
            return False
        try:
            raw = self.lock_path.read_bytes()
            if not raw.startswith(LOCK_MAGIC):
                return False
            plaintext = self._protector.unprotect(raw[len(LOCK_MAGIC) :], LOCK_ENTROPY)
            document = json.loads(plaintext.decode("utf-8"))
            return verify_password_record(password, document.get("password_record", {}))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, CryptographyError):
            return False

    @staticmethod
    def _write_temp(target: Path, content: bytes) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f"{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            return temp_name
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    @staticmethod
    def _secure_windows_acl(path: Path) -> None:
        """Restrict settings/rosalock to SYSTEM and local Administrators.

        icacls receives well-known SIDs rather than localized account names, so
        the same command works on Turkish and English Windows installations.
        """
        import subprocess
        import sys

        if sys.platform != "win32":
            return
        cp = subprocess.run(
            [
                "icacls.exe",
                str(path),
                "/inheritance:r",
                "/grant:r",
                "*S-1-5-18:F",       # LocalSystem
                "*S-1-5-32-544:F",   # Built-in Administrators
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if cp.returncode != 0:
            msg = (cp.stdout + "\n" + cp.stderr).strip()
            raise OSError(
                f"{path.name} dosya izinleri güvenli hale getirilemedi: {msg}"
            )
