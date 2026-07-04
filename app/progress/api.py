"""Progress API: submit a lesson result (the hub that lights up gating + SRS),
read your own progress, and the group board.

`POST /progress/lessons/{id}/result` is the seam everything converges on:
- records completion (→ content gating unlocks the next unit),
- updates the daily streak and XP,
- seeds the lesson's `new_vocab` into the SRS review queue.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.content.api import is_lesson_unlocked
from app.content.tables import ContentLesson
from app.db.session import get_session
from app.progress.models import LessonCompletion, UserProgress
from app.progress.service import get_or_create_progress, record_activity
from app.srs.service import seed_cards
from app.users.models import User

router = APIRouter(prefix="/progress", tags=["progress"])

XP_PER_LESSON = 10


class LessonResultBody(BaseModel):
    score: float = Field(ge=0, le=10)  # 0–10 scale


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

    if not await is_lesson_unlocked(session, user.id, lesson):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"lesson {lesson_id!r} is locked — complete its prerequisites first",
        )

    data = lesson.data
    passed = body.score >= float(data.get("pass_threshold", 8.0))  # 0–10 scale

    if not passed:
        prog = await get_or_create_progress(session, user.id, lesson.level)
        await session.commit()
        # `first_pass` = "this submission was the first successful pass" (it gates
        # first-pass XP + SRS seeding). A failing score never passes, so it's
        # False here by definition — not a claim about whether it's a first attempt.
        return {
            "lesson_id": lesson_id,
            "passed": False,
            "first_pass": False,
            "streak": prog.streak,
            "xp": prog.xp,
        }

    # Atomic insert-or-ignore: the DB decides who's first via the unique (user, lesson)
    # constraint, so concurrent double-submits can't double-award XP or 500 on a race
    # (qa-070). rowcount is 1 only for the request that actually inserted.
    completion = (
        sqlite_insert(LessonCompletion)
        .values(
            user_id=user.id,
            lesson_id=lesson_id,
            level=lesson.level,
            score=body.score,
            completed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
    )
    first_pass = (await session.execute(completion)).rowcount == 1

    if first_pass:
        await seed_cards(session, user.id, data.get("new_vocab", []))

    # Shared write path: streak counts daily activity; XP only on first pass.
    prog = await record_activity(
        session, user.id, xp_award=(XP_PER_LESSON if first_pass else 0), level=lesson.level
    )
    await session.commit()
    await session.refresh(prog)  # xp was an atomic increment expression — read it back

    return {
        "lesson_id": lesson_id,
        "passed": True,
        "first_pass": first_pass,
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
            # never fall back to email — the board is shared with the whole group (qa-010)
            "display_name": (u.display_name or "Learner")[:80],
            "level": p.level if p else "a1",
            "xp": p.xp if p else 0,
            "streak": p.streak if p else 0,
        }
        for (u, p) in rows
    ]
    members.sort(key=lambda m: m["xp"], reverse=True)  # leaderboard order
    return {"members": members}
