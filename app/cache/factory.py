"""Config-driven cache factory. Selecting the backend is a settings change.

Only the in-process backend ships now (plan §4.1: no Redis at this scale). A
future `redis` backend slots in here behind the same `Cache` protocol with no
change to any caller.
"""
from __future__ import annotations

from app.cache.interface import Cache
from app.cache.memory import MemoryCache


def build_cache(settings) -> Cache:
    backend = (settings.cache_backend or "memory").lower()
    if backend == "memory":
        return MemoryCache(
            default_ttl_seconds=settings.cache_ttl_seconds,
            max_entries=settings.cache_max_entries,
        )
    raise ValueError(f"unknown cache backend '{backend}' (have: memory)")
