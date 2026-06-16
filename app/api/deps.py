"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Request

from app.ai.router import AIRouter


def get_ai_router(request: Request) -> AIRouter:
    """The app's AI router (from app.state). Overridable in tests with a fake."""
    return request.app.state.ai_router
