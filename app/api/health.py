from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    state = request.app.state
    cache = getattr(state, "cache", None)
    return {
        "status": "ok",
        "version": state.settings.app_version,
        "providers": state.registry.names(),
        "profiles": state.ai_router.profiles(),
        "cache": cache.name if cache is not None else None,
    }
