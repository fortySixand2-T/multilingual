"""Application data-cache abstraction.

Same swappable-adapter pattern as `storage/` and `ai/`: domain code depends only
on this `Cache` protocol, never on a concrete backend. In-process now (no Redis
at this scale — see plan §4.1), but the bytes/str-in/str-out contract is
deliberately Redis-shaped so the backend can be swapped via config later with no
domain-code change.

Values are `str` (callers JSON-encode structured data) so an external backend
that only speaks strings/bytes is a drop-in replacement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    name: str

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
