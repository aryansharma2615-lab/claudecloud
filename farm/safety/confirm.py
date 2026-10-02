"""Two-step confirm tokens (pattern from sairaph/creality_k2_mcp, MIT).

An action tool returns a preflight + token; confirm_action(token) re-checks every
interlock before acting. Tokens are single-use, bound to one user, short-lived.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

TTL_S = 120


@dataclass
class Pending:
    action: str
    params: dict
    user: str
    expires: float = field(default_factory=lambda: time.monotonic() + TTL_S)


class ConfirmTokens:
    def __init__(self, ttl_s: float = TTL_S):
        self.ttl = ttl_s
        self._pending: dict[str, Pending] = {}
        self._lock = threading.Lock()

    def issue(self, action: str, params: dict, user: str) -> str:
        token = secrets.token_urlsafe(9)
        with self._lock:
            now = time.monotonic()
            self._pending = {k: v for k, v in self._pending.items() if v.expires > now}
            self._pending[token] = Pending(action, dict(params), user, now + self.ttl)
        return token

    def consume(self, token: str, user: str) -> Pending:
        with self._lock:
            p = self._pending.pop(token, None)
        if p is None:
            raise PermissionError("unknown or already-used confirm token")
        if p.expires < time.monotonic():
            raise PermissionError("confirm token expired: run the action again")
        if p.user != user:
            raise PermissionError("confirm token belongs to another user")
        return p
