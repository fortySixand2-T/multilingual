"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Request

from app.ai.router import AIRouter
from app.storage.interface import ObjectStorage


def get_ai_router(request: Request) -> AIRouter:
    """The app's AI router (from app.state). Overridable in tests with a fake."""
    return request.app.state.ai_router


def get_storage(request: Request) -> ObjectStorage:
    """The app's object storage (from app.state). Overridable in tests."""
    return request.app.state.storage
