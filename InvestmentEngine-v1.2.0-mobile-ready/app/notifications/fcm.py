from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # Optional until notification deployment is enabled.
    firebase_admin = None
    credentials = None
    messaging = None


class FirebaseNotConfigured(RuntimeError):
    pass


class FcmClient:
    """Server-side FCM sender.

    Private credentials are read only on the Python host. Quasar/Supabase stores
    non-secret project metadata and device targets; it never receives a service
    account private key.
    """

    def __init__(self, project_id: str | None = None) -> None:
        self.project_id = (project_id or "").strip() or None
        self._app = self._get_or_create_app()

    def _get_or_create_app(self):
        if firebase_admin is None or credentials is None:
            raise FirebaseNotConfigured(
                "firebase-admin paketi kurulu değil. requirements.txt ile yeni backend build hazırlanmalı."
            )
        name = f"rosa-fcm-{self.project_id or 'default'}"
        try:
            return firebase_admin.get_app(name)
        except ValueError:
            pass

        options = {"projectId": self.project_id} if self.project_id else None
        configured_path = (
            os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            or ""
        ).strip()

        if configured_path:
            path = Path(configured_path).expanduser()
            if not path.is_file():
                raise FirebaseNotConfigured(f"Firebase service-account dosyası bulunamadı: {path}")
            credential = credentials.Certificate(str(path))
            return firebase_admin.initialize_app(credential, options=options, name=name)

        try:
            credential = credentials.ApplicationDefault()
            return firebase_admin.initialize_app(credential, options=options, name=name)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise FirebaseNotConfigured(
                "Firebase credential yok. FIREBASE_SERVICE_ACCOUNT_PATH veya "
                "GOOGLE_APPLICATION_CREDENTIALS tanımlanmalı."
            ) from exc

    @staticmethod
    def _string_data(payload: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                result[str(key)] = json.dumps(value, ensure_ascii=False, default=str)
            else:
                result[str(key)] = str(value)
        return result

    def send(
        self,
        *,
        target: str,
        target_kind: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        if messaging is None:
            raise FirebaseNotConfigured("firebase-admin messaging modülü kullanılamıyor.")
        kwargs: dict[str, Any] = {
            "notification": messaging.Notification(title=title, body=body),
            "data": self._string_data(data or {}),
            "android": messaging.AndroidConfig(priority="high"),
        }
        if str(target_kind).upper() == "FID":
            kwargs["fid"] = target
        else:
            # Capacitor PushNotifications currently exposes the FCM registration
            # token. Firebase Admin 7.x still accepts it during the FID migration.
            kwargs["token"] = target
        message = messaging.Message(**kwargs)
        return messaging.send(message, app=self._app)
