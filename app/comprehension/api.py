"""Comprehension delivery + grading + audio streaming.

Delivery never includes answers or explanations — those are revealed only by the
grader on submit (so a timed set can't be cheated from the payload). Audio is
served through the storage interface, so the backend is identical for local-FS
dev and S3/MinIO in prod.
"""

from __future__ import annotations

from datetime import UTC, datetime

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.comprehension.tables import ComprehensionAttempt, ComprehensionPass, ComprehensionSetRow
from app.db.session import get_session
from app.progress.service import record_activity, sync_weak_spots
from app.storage.interface import ObjectStorage
from app.users.models import User

router = APIRouter(prefix="/comprehension", tags=["comprehension"])

COMPREHENSION_XP = 15


def get_storage(request: Request) -> ObjectStorage:
    return request.app.state.storage


class SubmitBody(BaseModel):
    answers: dict[str, str]  # question_id -> chosen option
    elapsed_seconds: int | None = None


def _client_view(data: dict) -> dict:
    """Strip answers/explanations for delivery."""
    view = {
        "id": data["id"],
        "skill": data["skill"],
        "title": data["title"],
        "level": data["level"],
        "time_limit_seconds": data.get("time_limit_seconds"),
        "allow_replay": data.get("allow_replay", True),
        "accent": data.get("accent"),
        "questions": [
            {"id": q["id"], "prompt": q["prompt"], "options": q["options"]}
            for q in data["questions"]
        ],
    }
    if data["skill"] == "reading":
        view["passage"] = data.get("passage")
    else:
        view["audio_url"] = f"/comprehension/audio/{data['id']}"
    return view


@router.get("/sets")
async def list_sets(
    level: str,
    skill: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    q = select(ComprehensionSetRow).where(ComprehensionSetRow.level == level)
    if skill:
        q = q.where(ComprehensionSetRow.skill == skill)
    rows = (await session.execute(q.order_by(ComprehensionSetRow.id))).scalars().all()
    return {
        "sets": [
            {
                "id": r.id,
                "skill": r.skill,
                "title": r.data["title"],
                "accent": r.accent,
                "time_limit_seconds": r.data.get("time_limit_seconds"),
                "allow_replay": r.data.get("allow_replay", True),
                "questions": len(r.data["questions"]),
            }
            for r in rows
        ]
    }


@router.get("/sets/{set_id}")
async def get_set(
    set_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    row = await session.get(ComprehensionSetRow, set_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"set {set_id!r} not found")
    return _client_view(row.data)


@router.post("/sets/{set_id}/submit")
async def submit(
    set_id: str,
    body: SubmitBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    row = await session.get(ComprehensionSetRow, set_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"set {set_id!r} not found")
    data = row.data
    questions = data["questions"]

    results = []
    correct = 0
    for q in questions:
        chosen = body.answers.get(q["id"])
        ok = chosen == q["answer"]
        if ok:
            correct += 1
        results.append(
            {
                "question_id": q["id"],
                "correct": ok,
                "your_answer": chosen,
                "correct_answer": q["answer"],
                "explain": q.get("explain", ""),
            }
        )

    total = len(questions)
    score = correct / total if total else 0.0
    passed = score >= float(data.get("pass_threshold", 0.6))
    limit = data.get("time_limit_seconds")
    over_time = (
        limit is not None and body.elapsed_seconds is not None and body.elapsed_seconds > limit
    )

    session.add(
        ComprehensionAttempt(
            user_id=user.id,
            set_id=set_id,
            score=score,
            elapsed_seconds=body.elapsed_seconds,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )

    # Capture wrong answers for targeted re-practice (resolve any now answered right).
    await sync_weak_spots(
        session, user.id, set_id, [(r["question_id"], r["correct"]) for r in results]
    )

    # Award XP once per set, atomically: only an in-time pass tries to claim the unique
    # (user, set) marker, and rowcount==1 means this request claimed it first — so
    # concurrent submits can't double-pay (qa-100). Over-time runs never claim it (qa-040).
    first_pass = False
    if passed and not over_time:
        claim = (
            sqlite_insert(ComprehensionPass)
            .values(
                user_id=user.id,
                set_id=set_id,
                awarded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "set_id"])
        )
        first_pass = (await session.execute(claim)).rowcount == 1
        if first_pass:
            await record_activity(session, user.id, xp_award=COMPREHENSION_XP, level=row.level)
    await session.commit()

    return {
        "set_id": set_id,
        "score": round(score, 3),
        "correct": correct,
        "total": total,
        "passed": passed,
        "first_pass": first_pass,
        "over_time": over_time,
        "results": results,
    }


@router.get("/audio/{set_id}")
async def get_audio(
    set_id: str,
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> Response:
    row = await session.get(ComprehensionSetRow, set_id)
    if row is None or row.data.get("skill") != "listening" or not row.data.get("audio_ref"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio for this set")
    key = row.data["audio_ref"]
    try:
        # storage is sync (local-FS / boto3) — keep it off the event loop
        audio = await anyio.to_thread.run_sync(lambda: storage.get(key))
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "audio asset not found") from None
    return Response(content=audio, media_type="audio/mpeg")
