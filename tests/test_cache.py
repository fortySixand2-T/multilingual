import time

from app.cache.factory import build_cache
from app.cache.memory import MemoryCache


class _Settings:
    cache_backend = "memory"
    cache_ttl_seconds = 300
    cache_max_entries = 2


def test_factory_builds_memory_backend():
    cache = build_cache(_Settings())
    assert cache.name == "memory"


def test_get_set_delete():
    c = MemoryCache()
    assert c.get("k") is None
    c.set("k", "v")
    assert c.get("k") == "v"
    c.delete("k")
    assert c.get("k") is None


def test_ttl_expiry():
    c = MemoryCache(default_ttl_seconds=300)
    c.set("k", "v", ttl_seconds=1)
    assert c.get("k") == "v"
    # expire by faking the clock forward via a real short sleep
    time.sleep(1.05)
    assert c.get("k") is None


def test_lru_eviction_respects_max_entries():
    c = MemoryCache(max_entries=2)
    c.set("a", "1")
    c.set("b", "2")
    c.get("a")  # touch a -> b becomes least-recently-used
    c.set("c", "3")  # evicts b
    assert c.get("a") == "1"
    assert c.get("c") == "3"
    assert c.get("b") is None
