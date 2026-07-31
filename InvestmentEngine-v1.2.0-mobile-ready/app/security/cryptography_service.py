from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import secrets
import sys
from ctypes import wintypes
from typing import Any

SETTINGS_ENTROPY = b"RosaInvestmentEngine/settings/v1"
LOCK_ENTROPY = b"RosaInvestmentEngine/rosalock/v1"
PASSWORD_ITERATIONS = 600_000


class CryptographyError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _make_blob(data: bytes) -> tuple[_DataBlob, Any]:
    if not data:
        data = b"\x00"
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buffer


class DpapiProtector:
    """Windows DPAPI wrapper.

    LocalMachine scope is deliberate: settings must be readable by the Windows
    service after reboot without asking for the UI password. File-system ACLs therefore form part of the security boundary; settings and rosalock are stored beside the EXE and restricted to SYSTEM and Administrators.
    """

    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    CRYPTPROTECT_LOCAL_MACHINE = 0x04

    def __init__(self, machine_scope: bool = True) -> None:
        if sys.platform != "win32":
            raise CryptographyError("DPAPI yalnızca Windows üzerinde kullanılabilir.")
        self.machine_scope = machine_scope
        self._crypt32 = ctypes.windll.crypt32
        self._kernel32 = ctypes.windll.kernel32
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @property
    def _flags(self) -> int:
        flags = self.CRYPTPROTECT_UI_FORBIDDEN
        if self.machine_scope:
            flags |= self.CRYPTPROTECT_LOCAL_MACHINE
        return flags

    def protect(self, plaintext: bytes, entropy: bytes = SETTINGS_ENTROPY) -> bytes:
        if not plaintext:
            raise CryptographyError("Boş veri şifrelenemez.")
        input_blob, input_buffer = _make_blob(plaintext)
        entropy_blob, entropy_buffer = _make_blob(entropy)
        output_blob = _DataBlob()
        _ = (input_buffer, entropy_buffer)
        ok = self._crypt32.CryptProtectData(
            ctypes.byref(input_blob), "Rosa Investment Engine",
            ctypes.byref(entropy_blob), None, None, self._flags,
            ctypes.byref(output_blob),
        )
        if not ok:
            raise CryptographyError(f"DPAPI şifreleme başarısız: {ctypes.WinError()}")
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            self._kernel32.LocalFree(output_blob.pbData)

    def unprotect(self, ciphertext: bytes, entropy: bytes = SETTINGS_ENTROPY) -> bytes:
        if not ciphertext:
            raise CryptographyError("Şifreli veri boş.")
        input_blob, input_buffer = _make_blob(ciphertext)
        entropy_blob, entropy_buffer = _make_blob(entropy)
        output_blob = _DataBlob()
        description = wintypes.LPWSTR()
        _ = (input_buffer, entropy_buffer)
        ok = self._crypt32.CryptUnprotectData(
            ctypes.byref(input_blob), ctypes.byref(description),
            ctypes.byref(entropy_blob), None, None,
            self.CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output_blob),
        )
        if not ok:
            raise CryptographyError(f"DPAPI çözme başarısız: {ctypes.WinError()}")
        try:
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            if description:
                self._kernel32.LocalFree(description)
            self._kernel32.LocalFree(output_blob.pbData)


def create_password_record(password: str) -> dict[str, Any]:
    if len(password) < 10:
        raise CryptographyError("Ayar şifresi en az 10 karakter olmalıdır.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS, dklen=32
    )
    return {
        "version": 1,
        "algorithm": "pbkdf2_sha256",
        "iterations": PASSWORD_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "digest": base64.b64encode(digest).decode("ascii"),
    }


def verify_password_record(password: str, record: dict[str, Any]) -> bool:
    try:
        if record.get("version") != 1 or record.get("algorithm") != "pbkdf2_sha256":
            return False
        iterations = int(record["iterations"])
        salt = base64.b64decode(record["salt"], validate=True)
        expected = base64.b64decode(record["digest"], validate=True)
    except (KeyError, TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
    )
    return hmac.compare_digest(actual, expected)
