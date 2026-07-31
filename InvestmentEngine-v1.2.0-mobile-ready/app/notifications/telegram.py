from __future__ import annotations

import requests


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        if not self.bot_token or not self.chat_id:
            raise RuntimeError("Telegram token/chat id ayarlı değil.")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=15)
        r.raise_for_status()
        payload = r.json()
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description") or "Telegram gönderimi başarısız.")
