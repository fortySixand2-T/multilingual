from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai.errors import AllProvidersFailedError
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


def create_app() -> FastAPI:
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
    app.state.ai_router = AIRouter.from_yaml(registry, settings.ai_routing_path, cache=cache)

    app.add_exception_handler(AllProvidersFailedError, _ai_unavailable)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(content_router)
    app.include_router(srs_router)
    app.include_router(progress_router)
    app.include_router(tutor_router)
    app.include_router(comprehension_router)
    app.include_router(assessment_router)
    app.include_router(speech_router)
    app.include_router(exam_router)

    # Serve the built SPA when present (single-port prod). The API routers above
    # are registered first, so explicit API routes win; everything else falls
    # back to index.html for client-side routing. Build the SPA with
    # VITE_API_BASE="" so it calls these routes directly (no /api proxy).
    web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if web_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")
        index_html = web_dist / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa(full_path: str) -> FileResponse:
            return FileResponse(index_html)

    return app


app = create_app()
