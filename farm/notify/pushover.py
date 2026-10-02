"""Pushover alerts (https://pushover.net/api). priority 2 = repeats until acknowledged."""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)
API = "https://api.pushover.net/1/messages.json"


class Notifier:
    def __init__(self, token: str, user: str, client: httpx.Client | None = None):
        self.enabled = bool(token and user)
        self._token, self._user = token, user
        self._http = client or httpx.Client(timeout=15)

    def send(self, title: str, message: str, priority: int = 0, image_jpeg: bytes | None = None) -> bool:
        if not self.enabled:
            log.info("alert (pushover not configured): %s — %s", title, message)
            return False
        data = {"token": self._token, "user": self._user, "title": title[:250],
                "message": message[:1024], "priority": str(priority)}
        if priority == 2:
            data |= {"retry": "60", "expire": "3600"}
        files = {"attachment": ("snap.jpg", image_jpeg, "image/jpeg")} if image_jpeg else None
        try:
            r = self._http.post(API, data=data, files=files)
            r.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            log.error("pushover failed: %s", exc)
            return False
