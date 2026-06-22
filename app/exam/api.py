"""Exam simulation API: start a timed mock, record each section's outcome, finish
with an aggregate per-skill CLB report, and review history.

Composition only — section outcomes (comprehension correct/total, writing/speaking
CLB) are produced by the existing modules and reported here; the exam computes the
CLB profile. The report is an estimate, never an official score.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.session import get_session
from app.exam.clb import aggregate_report, clb_from_fraction
from app.exam.models import Skill
from app.exam.tables import ExamAttempt, ExamBlueprintRow
from app.users.models import User

router = APIRouter(prefix="/exam", tags=["exam"])


class StartBody(BaseModel):
    blueprint_id: str


class SectionResultBody(BaseModel):
    skill: Skill
    correct: int | None = None  # reading / listening
    total: int | None = None
    clb_estimate: int | None = None  # writing / speaking


async def _owned_attempt(session: AsyncSession, attempt_id: int, user_id: int) -> ExamAttempt:
    attempt = await session.get(ExamAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "attempt not found")
    return attempt


@router.get("/blueprints")
async def list_blueprints(
    level: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    rows = (
        (
            await session.execute(
                select(ExamBlueprintRow)
                .where(ExamBlueprintRow.level == level)
                .order_by(ExamBlueprintRow.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "blueprints": [
            {"id": r.id, "title": r.data["title"], "sections": len(r.data["sections"])}
            for r in rows
        ]
    }


@router.post("/start")
async def start(
    body: StartBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    bp = await session.get(ExamBlueprintRow, body.blueprint_id)
    if bp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"blueprint {body.blueprint_id!r} not found")

    # Resume an in-progress attempt for this blueprint instead of spawning duplicates,
    # so "start" can't litter the resume list / history (qa-150).
    existing = (
        await session.execute(
            select(ExamAttempt).where(
                ExamAttempt.user_id == user.id,
                ExamAttempt.blueprint_id == bp.id,
                ExamAttempt.status == "in_progress",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"attempt_id": existing.id, "blueprint": bp.data}

    attempt = ExamAttempt(
        user_id=user.id,
        blueprint_id=bp.id,
        level=bp.level,
        status="in_progress",
        sections={},
        clb_report=None,
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(attempt)
    await session.flush()
    aid = attempt.id
    await session.commit()
    return {"attempt_id": aid, "blueprint": bp.data}


@router.get("/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Resume support: current state of an attempt — recorded vs remaining sections."""
    attempt = await _owned_attempt(session, attempt_id, user.id)
    bp = await session.get(ExamBlueprintRow, attempt.blueprint_id)
    required = [s["skill"] for s in (bp.data["sections"] if bp else [])]
    return {
        "attempt_id": attempt.id,
        "blueprint_id": attempt.blueprint_id,
        "blueprint": bp.data if bp else None,
        "status": attempt.status,
        "recorded": sorted(attempt.sections),
        "remaining": [s for s in required if s not in attempt.sections],
        "clb_report": attempt.clb_report,
    }


@router.post("/{attempt_id}/section")
async def record_section(
    attempt_id: int,
    body: SectionResultBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    attempt = await _owned_attempt(session, attempt_id, user.id)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "attempt already finished")

    if body.skill in ("reading", "listening"):
        if body.correct is None or not body.total:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "need correct + total")
        if body.total <= 0 or body.correct < 0 or body.correct > body.total:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "need 0 <= correct <= total and total > 0"
            )
        clb = clb_from_fraction(body.correct / body.total)
        detail = {"correct": body.correct, "total": body.total}
    else:
        if body.clb_estimate is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "need clb_estimate")
        clb = max(1, min(12, body.clb_estimate))
        detail = {"clb_estimate": clb}

    # Patch just this skill's key with an atomic json_set instead of overwriting the whole
    # JSON blob — a read-modify-write here loses concurrent sections for *other* skills
    # (qa-170). body.skill is a fixed Literal, so the path is safe.
    await session.execute(
        update(ExamAttempt)
        .where(ExamAttempt.id == attempt.id)
        .values(
            sections=func.json_set(
                ExamAttempt.sections,
                f"$.{body.skill}",
                func.json(json.dumps({"clb": clb, "detail": detail})),
            )
        )
    )
    await session.commit()
    await session.refresh(attempt)
    return {"skill": body.skill, "clb": clb, "recorded": sorted(attempt.sections)}


async def _required_skills(session: AsyncSession, blueprint_id: str) -> list[str]:
    bp = await session.get(ExamBlueprintRow, blueprint_id)
    return [s["skill"] for s in (bp.data["sections"] if bp else [])]


@router.post("/{attempt_id}/finish")
async def finish(
    attempt_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    attempt = await _owned_attempt(session, attempt_id, user.id)
    if attempt.status == "finished":  # idempotent
        return {"attempt_id": attempt.id, "report": attempt.clb_report}

    required = await _required_skills(session, attempt.blueprint_id)
    missing = [s for s in required if s not in attempt.sections]
    if missing:
        # No score until the test is complete.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"finish all sections first — missing: {', '.join(missing)}",
        )

    per_skill = {skill: data["clb"] for skill, data in attempt.sections.items()}
    report = aggregate_report(per_skill)
    attempt.clb_report = report
    attempt.status = "finished"
    attempt.finished_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    return {"attempt_id": attempt.id, "report": report}


@router.get("/history")
async def history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    rows = (
        (
            await session.execute(
                select(ExamAttempt)
                .where(ExamAttempt.user_id == user.id)
                .order_by(ExamAttempt.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "attempts": [
            {
                "attempt_id": a.id,
                "blueprint_id": a.blueprint_id,
                "level": a.level,
                "status": a.status,
                "clb_report": a.clb_report,
                "started_at": a.started_at.isoformat(),
                "finished_at": a.finished_at.isoformat() if a.finished_at else None,
            }
            for a in rows
        ]
    }
