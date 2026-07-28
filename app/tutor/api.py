"""Tutor API: generate a scaffolded drill for a lesson (A1–B2).

The lesson's own level picks the level-gated prompt/profile. The AI router comes
from app.state via a dependency so tests can inject a fake (no live LLM).
Over-budget is a graceful 200, not an error (AC1.5).
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
from app.progress.models import UserProgress
from app.progress.service import DAILY_XP_GOAL, record_activity, xp_earned_today
from app.tutor.orchestrator import Tutor
from app.users.models import User

router = APIRouter(prefix="/tutor", tags=["tutor"])

DRILL_XP = 10  # bonus for the day's first drill (once per day — see record_activity)


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
    # A delivered drill (not an over-budget no-op) counts toward the streak; the XP
    # bonus is claimed once per day so repeated drills can't inflate XP.
    prog = None
    if not result.over_budget:
        prog = await record_activity(
            session,
            user.id,
            xp_award=DRILL_XP,
            source="drill",
            once_per_day=True,
            level=lesson.level,
        )
    await session.commit()
    if prog is not None:
        await session.refresh(prog)
    else:
        prog = await session.get(UserProgress, user.id)
    return {
        "lesson_id": body.lesson_id,
        "over_budget": result.over_budget,
        "drill": result.text,
        "provider": result.provider,
        "model": result.model,
        "tokens_used_today": result.tokens_used_today,
        "daily_budget": result.daily_budget,
        "streak": prog.streak if prog else 0,
        "xp": prog.xp if prog else 0,
        "xp_today": await xp_earned_today(session, user.id),
        "daily_goal": DAILY_XP_GOAL,
    }
