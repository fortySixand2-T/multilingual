"""Progress API: submit a lesson result (the hub that lights up gating + SRS),
read your own progress, and the group board.

`POST /progress/lessons/{id}/result` is the seam everything converges on:
- records completion (→ content gating unlocks the next unit),
- updates the daily streak and XP,
- seeds the lesson's `new_vocab` into the SRS review queue.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.content.tables import ContentLesson
from app.db.session import get_session
from app.progress.models import LessonCompletion, UserProgress
from app.progress.service import get_or_create_progress, record_activity
from app.srs.service import seed_cards
from app.users.models import User

router = APIRouter(prefix="/progress", tags=["progress"])

XP_PER_LESSON = 10


class LessonResultBody(BaseModel):
    score: float


async def _already_completed(session: AsyncSession, user_id: int, lesson_id: str) -> bool:
    row = await session.execute(
        select(LessonCompletion.id).where(
            LessonCompletion.user_id == user_id, LessonCompletion.lesson_id == lesson_id
        )
    )
    return row.scalar_one_or_none() is not None


@router.post("/lessons/{lesson_id}/result")
async def submit_result(
    lesson_id: str,
    body: LessonResultBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    lesson = await session.get(ContentLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"lesson {lesson_id!r} not found")

    data = lesson.data
    passed = body.score >= float(data.get("pass_threshold", 0.8))

    if not passed:
        prog = await get_or_create_progress(session, user.id, lesson.level)
        await session.commit()
        return {
            "lesson_id": lesson_id,
            "passed": False,
            "first_time": False,
            "streak": prog.streak,
            "xp": prog.xp,
        }

    first_time = not await _already_completed(session, user.id, lesson_id)
    if first_time:
        session.add(
            LessonCompletion(
                user_id=user.id,
                lesson_id=lesson_id,
                level=lesson.level,
                score=body.score,
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        await seed_cards(session, user.id, data.get("new_vocab", []))

    # Shared write path: streak counts daily activity; XP only on first pass.
    prog = await record_activity(
        session, user.id, xp_award=(XP_PER_LESSON if first_time else 0), level=lesson.level
    )

    await session.commit()
    return {
        "lesson_id": lesson_id,
        "passed": True,
        "first_time": first_time,
        "streak": prog.streak,
        "xp": prog.xp,
    }


@router.get("/me")
async def get_me(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    prog = await session.get(UserProgress, user.id)
    return {
        "user_id": user.id,
        "level": prog.level if prog else "a1",
        "xp": prog.xp if prog else 0,
        "streak": prog.streak if prog else 0,
        "last_active": prog.last_active.isoformat() if prog and prog.last_active else None,
    }


@router.get("/board")
async def get_board(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    rows = (
        await session.execute(
            select(User, UserProgress).join(
                UserProgress, UserProgress.user_id == User.id, isouter=True
            )
        )
    ).all()
    members = [
        {
            "user_id": u.id,
            "display_name": u.display_name or u.email,
            "level": p.level if p else "a1",
            "xp": p.xp if p else 0,
            "streak": p.streak if p else 0,
        }
        for (u, p) in rows
    ]
    members.sort(key=lambda m: m["xp"], reverse=True)  # leaderboard order
    return {"members": members}
