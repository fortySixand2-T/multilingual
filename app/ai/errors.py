"""Domain errors for the AI layer (vendor-free).

Lets callers distinguish a *runtime* provider outage (retryable, → 503) from a
*configuration* mistake like an unknown profile (a bug, → 500). The router raises
these; the API maps `AllProvidersFailedError` to a graceful response.
"""

from __future__ import annotations


class AIError(Exception):
    """Base class for AI-layer failures."""


class AllProvidersFailedError(AIError):
    """Every provider in a profile's chain (primary + fallbacks) failed."""

    def __init__(self, profile: str, last_error: Exception | None = None) -> None:
        self.profile = profile
        self.last_error = last_error
        super().__init__(f"all providers failed for profile {profile!r}")
