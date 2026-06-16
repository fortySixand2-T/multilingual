from __future__ import annotations

from fastapi import FastAPI

from app.ai.registry import build_default_registry
from app.ai.router import AIRouter
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.cache.factory import build_cache
from app.config.settings import get_settings
from app.content.api import router as content_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TEF Platform", version=settings.app_version)

    registry = build_default_registry(settings)
    cache = build_cache(settings)
    app.state.settings = settings
    app.state.registry = registry
    app.state.cache = cache
    app.state.ai_router = AIRouter.from_yaml(registry, settings.ai_routing_path, cache=cache)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(content_router)
    return app


app = create_app()
