"""In-process TTL + LRU cache. Thread-safe; the default application cache backend.

Bounded by `max_entries` (LRU eviction) so a long-running process can't grow the
cache without limit. Expired entries are dropped lazily on access and also
evicted when encountered during insertion.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict


class MemoryCache:
    name = "memory"

    def __init__(self, *, default_ttl_seconds: int = 300, max_entries: int = 1024) -> None:
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries
        self._lock = threading.Lock()
        # key -> (expires_at_epoch | None, value)
        self._store: "OrderedDict[str, tuple[float | None, str]]" = OrderedDict()

    def _expired(self, expires_at: float | None) -> bool:
        return expires_at is not None and time.monotonic() >= expires_at

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if self._expired(expires_at):
                del self._store[key]
                return None
            self._store.move_to_end(key)  # LRU: mark recently used
            return value

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else ttl_seconds
        expires_at = None if ttl <= 0 else time.monotonic() + ttl
        with self._lock:
            self._store[key] = (expires_at, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)  # evict least-recently-used

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
