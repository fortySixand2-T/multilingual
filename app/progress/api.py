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
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.comprehension.tables import ComprehensionSetRow
from app.content.api import is_lesson_unlocked
from app.content.tables import ContentLesson
from app.db.session import get_session
from app.progress.models import LessonCompletion, UserProgress, WeakSpot
from app.progress.service import (
    DAILY_XP_GOAL,
    get_or_create_progress,
    record_activity,
    xp_earned_today,
)
from app.srs.service import seed_cards
from app.users.models import User

router = APIRouter(prefix="/progress", tags=["progress"])

XP_PER_LESSON = 10
# Failed full-lesson attempts before the learner may "continue anyway" (waive) past
# a lesson to unlock the next unit. Keeps mastery the default; relaxes only when stuck.
WAIVE_AFTER_ATTEMPTS = 2


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
    now = datetime.now(UTC).replace(tzinfo=None)
    passed = body.score >= float(data.get("pass_threshold", 8.0))  # 0–10 scale

    if not passed:
        # Record/increment a failed attempt (a row may not exist yet). This no longer
        # unlocks anything — completed_lesson_ids counts passed|waived only — but it
        # powers the "continue anyway" escape hatch once enough attempts pile up.
        bump = (
            sqlite_insert(LessonCompletion)
            .values(
                user_id=user.id,
                lesson_id=lesson_id,
                level=lesson.level,
                score=body.score,
                completed_at=now,
                passed=False,
                waived=False,
                attempts=1,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "lesson_id"],
                set_={"attempts": LessonCompletion.attempts + 1, "score": body.score},
            )
        )
        await session.execute(bump)
        row = (
            await session.execute(
                select(LessonCompletion).where(
                    LessonCompletion.user_id == user.id, LessonCompletion.lesson_id == lesson_id
                )
            )
        ).scalar_one()
        prog = await get_or_create_progress(session, user.id, lesson.level)
        await session.commit()
        # `first_pass` = "this submission was the first successful pass". A failing
        # score never passes, so it's False here by definition.
        return {
            "lesson_id": lesson_id,
            "passed": False,
            "first_pass": False,
            "attempts": row.attempts,
            "can_waive": row.attempts >= WAIVE_AFTER_ATTEMPTS and not row.passed and not row.waived,
            "streak": prog.streak,
            "xp": prog.xp,
        }

    # Passing. Race-safe first-pass detection that also tolerates a pre-existing
    # attempts row: insert-or-ignore a passed row (rowcount 1 → we're first); else the
    # row already existed, so flip passed False→True under a guard (rowcount 1 → we
    # flipped it, i.e. first pass; 0 → it was already passed). qa-070 stays covered.
    completion = (
        sqlite_insert(LessonCompletion)
        .values(
            user_id=user.id,
            lesson_id=lesson_id,
            level=lesson.level,
            score=body.score,
            completed_at=now,
            passed=True,
            waived=False,
            attempts=0,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
    )
    first_pass = (await session.execute(completion)).rowcount == 1
    if not first_pass:
        flip = (
            update(LessonCompletion)
            .where(
                LessonCompletion.user_id == user.id,
                LessonCompletion.lesson_id == lesson_id,
                LessonCompletion.passed.is_(False),
            )
            .values(passed=True, score=body.score, completed_at=now)
        )
        first_pass = (await session.execute(flip)).rowcount == 1

    if first_pass:
        await seed_cards(session, user.id, data.get("new_vocab", []))

    # Shared write path: streak counts daily activity; XP only on first pass.
    prog = await record_activity(
        session,
        user.id,
        xp_award=(XP_PER_LESSON if first_pass else 0),
        source="lesson",
        level=lesson.level,
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


@router.post("/lessons/{lesson_id}/waive")
async def waive_lesson(
    lesson_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Escape hatch: after WAIVE_AFTER_ATTEMPTS failed tries, move past a lesson so
    the next unit unlocks. The lesson is marked `waived` (not passed) — it stays
    retryable and flagged for review, and earns no XP. Idempotent once waived."""
    lesson = await session.get(ContentLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"lesson {lesson_id!r} not found")
    if not await is_lesson_unlocked(session, user.id, lesson):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"lesson {lesson_id!r} is locked — complete its prerequisites first",
        )
    row = (
        await session.execute(
            select(LessonCompletion).where(
                LessonCompletion.user_id == user.id, LessonCompletion.lesson_id == lesson_id
            )
        )
    ).scalar_one_or_none()
    if row is None or row.passed:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "nothing to waive — lesson not attempted or already passed"
        )
    if not row.waived and row.attempts < WAIVE_AFTER_ATTEMPTS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"keep trying — you can continue anyway after {WAIVE_AFTER_ATTEMPTS} attempts",
        )
    row.waived = True  # idempotent if already waived
    prog = await record_activity(session, user.id, xp_award=0, source="lesson", level=lesson.level)
    await session.commit()
    await session.refresh(prog)
    return {
        "lesson_id": lesson_id,
        "passed": False,
        "waived": True,
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
        "xp_today": await xp_earned_today(session, user.id),
        "daily_goal": DAILY_XP_GOAL,
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


class WeakSpotAnswer(BaseModel):
    chosen: str


@router.get("/weak-spots")
async def get_weak_spots(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Unresolved missed comprehension questions, re-hydrated with their
    prompt/options/explain from the owning set — a targeted re-practice queue,
    most-missed first."""
    rows = (
        (
            await session.execute(
                select(WeakSpot)
                .where(WeakSpot.user_id == user.id, WeakSpot.resolved.is_(False))
                .order_by(WeakSpot.times_missed.desc(), WeakSpot.last_missed.desc())
            )
        )
        .scalars()
        .all()
    )
    sets: dict[str, ComprehensionSetRow | None] = {}
    for w in rows:
        if w.set_id not in sets:
            sets[w.set_id] = await session.get(ComprehensionSetRow, w.set_id)

    items = []
    for w in rows:
        srow = sets.get(w.set_id)
        if srow is None:
            continue  # set was removed by a re-sync; skip (still resolvable via dismiss)
        question = next((q for q in srow.data["questions"] if q["id"] == w.ref_id), None)
        if question is None:
            continue
        items.append(
            {
                "id": w.id,
                "set_id": w.set_id,
                "set_title": srow.data.get("title", w.set_id),
                "skill": srow.skill,
                "question_id": w.ref_id,
                "prompt": question["prompt"],
                "options": question["options"],
                "explain": question.get("explain", ""),
                "times_missed": w.times_missed,
            }
        )
    return {"weak_spots": items}


async def _owned_weak_spot(session: AsyncSession, weak_spot_id: int, user_id: int) -> WeakSpot:
    w = await session.get(WeakSpot, weak_spot_id)
    if w is None or w.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "weak spot not found")
    return w


@router.post("/weak-spots/{weak_spot_id}/answer")
async def answer_weak_spot(
    weak_spot_id: int,
    body: WeakSpotAnswer,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Re-answer a missed question. Correct → resolved; wrong → another miss."""
    w = await _owned_weak_spot(session, weak_spot_id, user.id)
    if w.resolved:
        # already cleared and not in the active queue — don't let a stray call
        # inflate times_missed on a resolved row (qa-449).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "weak spot already resolved")
    srow = await session.get(ComprehensionSetRow, w.set_id)
    question = next(
        (q for q in (srow.data["questions"] if srow else []) if q["id"] == w.ref_id), None
    )
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "question no longer exists")
    correct = body.chosen == question["answer"]
    if correct:
        w.resolved = True
    else:
        w.times_missed += 1
        w.last_missed = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    return {
        "correct": correct,
        "correct_answer": question["answer"],
        "explain": question.get("explain", ""),
        "resolved": w.resolved,
    }


@router.post("/weak-spots/{weak_spot_id}/dismiss")
async def dismiss_weak_spot(
    weak_spot_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Clear a weak spot without re-answering ('I've got this')."""
    w = await _owned_weak_spot(session, weak_spot_id, user.id)
    w.resolved = True
    await session.commit()
    return {"id": weak_spot_id, "resolved": True}
