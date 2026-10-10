"""In-memory cache for weather and places lookups with a configurable TTL."""

from __future__ import annotations

import time
from typing import Any


class SimpleTTLCache:
    """A lightweight in-memory cache expiring items after a set TTL in seconds."""

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[tuple[Any, ...], tuple[float, Any]] = {}

    def get(self, key: tuple[Any, ...], now: float | None = None) -> Any | None:
        current_time = now if now is not None else time.time()
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if current_time >= expires_at:
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: tuple[Any, ...], value: Any, now: float | None = None) -> None:
        current_time = now if now is not None else time.time()
        self._entries[key] = (current_time + self.ttl_seconds, value)

    def clear(self) -> None:
        self._entries.clear()
