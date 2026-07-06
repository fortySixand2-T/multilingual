"""Tutor API: generate a scaffolded A1 drill for a lesson.

The AI router comes from app.state via a dependency so tests can inject a fake
(no live LLM). Over-budget is a graceful 200, not an error (AC1.5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import AIRouter
from app.api.auth import get_current_user
from app.api.deps import get_ai_router  # re-exported for callers/tests
from app.config.settings import Settings, get_settings
from app.content.tables import ContentLesson
from app.db.session import get_session
from app.tutor.orchestrator import Tutor
from app.users.models import User

router = APIRouter(prefix="/tutor", tags=["tutor"])


class DrillBody(BaseModel):
    lesson_id: str
    attempt: str | None = None


@router.post("/drill")
async def post_drill(
    body: DrillBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    lesson = await session.get(ContentLesson, body.lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"lesson {body.lesson_id!r} not found")

    data = lesson.data
    # Level-gated drills for every shipped level — the lesson's own level picks the
    # scaffolded prompt/profile. Unsupported levels degrade to a clean 400.
    try:
        tutor = Tutor(ai_router, level=lesson.level)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"tutor drills are not available for level {lesson.level!r}",
        ) from None
    result = await tutor.drill(
        session,
        user.id,
        grammar_point=data.get("grammar_point", ""),
        vocab=data.get("new_vocab", []),
        attempt=body.attempt,
        daily_budget=settings.tutor_daily_token_budget,
    )
    await session.commit()
    return {
        "lesson_id": body.lesson_id,
        "over_budget": result.over_budget,
        "drill": result.text,
        "provider": result.provider,
        "model": result.model,
        "tokens_used_today": result.tokens_used_today,
        "daily_budget": result.daily_budget,
    }
