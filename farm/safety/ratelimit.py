"""Sliding-window rate limits per user. stop_all / pause are exempt (see MCP_TOOLS.md)."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

LIMITS = {"any": (30, 60.0), "action": (5, 60.0)}  # (calls, window seconds)
EXEMPT = {"stop_all", "pause"}


class RateLimiter:
    def __init__(self, limits: dict[str, tuple[int, float]] | None = None):
        self.limits = limits or LIMITS
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user: str, tool: str, is_action: bool) -> None:
        if tool in EXEMPT:
            return
        kinds = ["any"] + (["action"] if is_action else [])
        now = time.monotonic()
        with self._lock:
            for kind in kinds:
                limit, window = self.limits[kind]
                q = self._hits[(user, kind)]
                while q and now - q[0] > window:
                    q.popleft()
                if len(q) >= limit:
                    raise PermissionError(f"rate limit: {limit} {kind} calls per {int(window)} s")
            for kind in kinds:
                self._hits[(user, kind)].append(now)
