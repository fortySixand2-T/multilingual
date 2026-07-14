from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from app.ai.errors import AllProvidersFailedError
from app.ai.policy import load_bandit_policy
from app.ai.registry import build_default_registry
from app.ai.router import AIRouter
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.assessment.api import router as assessment_router
from app.cache.factory import build_cache
from app.comprehension.api import router as comprehension_router
from app.config.settings import get_settings
from app.content.api import router as content_router
from app.exam.api import router as exam_router
from app.progress.api import router as progress_router
from app.speech.api import router as speech_router
from app.speech.factory import build_stt, build_tts
from app.srs.api import router as srs_router
from app.storage.factory import build_storage
from app.tutor.api import router as tutor_router


async def _ai_unavailable(request: Request, exc: AllProvidersFailedError) -> JSONResponse:
    # A provider outage is a transient, retryable condition — degrade gracefully.
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI service is temporarily unavailable. Please try again shortly."},
    )


def _mount_spa(app: FastAPI, api_routers: list, web_dist: Path) -> None:
    """Serve the built SPA from ``web_dist`` on the same origin as the API.

    ``api_routers`` must already be registered on ``app`` (they take precedence).
    A path under a real API prefix that matched no route is a genuine API 404 and
    returns JSON; everything else falls back to ``index.html`` for client-side
    routing."""
    app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")
    index_html = web_dist / "index.html"

    # Top-level segments owned by the API (health, auth, content, exam, …),
    # derived from the routers themselves so this stays correct as they change.
    api_prefixes = {
        route.path.split("/", 2)[1]
        for router in api_routers
        for route in router.routes
        if isinstance(route, APIRoute)
    }

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def _spa(full_path: str) -> FileResponse | JSONResponse:
        if full_path.split("/", 1)[0] in api_prefixes:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return FileResponse(index_html)


def create_app(web_dist: Path | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TEF Platform", version=settings.app_version)

    registry = build_default_registry(settings)
    cache = build_cache(settings)
    app.state.settings = settings
    app.state.registry = registry
    app.state.cache = cache
    app.state.storage = build_storage(settings)
    app.state.stt = build_stt(settings)
    app.state.tts = build_tts(settings)
    # Learned routing (BanditPolicy) if an offline eval has persisted weights;
    # otherwise None -> router falls back to the static ai_routing.yaml order.
    policy = load_bandit_policy(settings.model_weights_path)
    app.state.ai_router = AIRouter.from_yaml(
        registry, settings.ai_routing_path, cache=cache, policy=policy
    )

    app.add_exception_handler(AllProvidersFailedError, _ai_unavailable)

    api_routers = [
        health_router,
        auth_router,
        content_router,
        srs_router,
        progress_router,
        tutor_router,
        comprehension_router,
        assessment_router,
        speech_router,
        exam_router,
    ]
    for router in api_routers:
        app.include_router(router)

    # Serve the built SPA when present (single-port prod). Build the SPA with
    # VITE_API_BASE="" so it calls these routes directly (no /api proxy). Guarded
    # on the build existing, so dev/tests without a build are unaffected.
    web_dist = web_dist or Path(__file__).resolve().parent.parent / "web" / "dist"
    if web_dist.is_dir():
        _mount_spa(app, api_routers, web_dist)

    return app


app = create_app()
