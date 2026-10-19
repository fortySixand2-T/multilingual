"""Exam simulation API: start a timed mock, record each section's outcome, finish
with an aggregate report, and review history.

Composition only — section outcomes (comprehension correct/total, writing/speaking
CLB or DELF points) are produced by the existing modules and reported here; the exam
computes the report: a per-skill CLB profile for TEF mocks, a /100 pass/fail for
DELF mocks. The report is an estimate, never an official score.
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
from app.exam.clb import (
    DELF_SECTION_MAX,
    aggregate_report,
    clb_from_fraction,
    delf_points,
    delf_report,
    half_point,
)
from app.exam.models import Skill
from app.exam.tables import ExamAttempt, ExamBlueprintRow
from app.progress.models import UserProgress
from app.progress.service import record_activity
from app.users.models import User

router = APIRouter(prefix="/exam", tags=["exam"])

EXAM_XP = 25


class StartBody(BaseModel):
    blueprint_id: str


class SectionResultBody(BaseModel):
    skill: Skill
    correct: int | None = None  # reading / listening
    total: int | None = None
    clb_estimate: int | None = None  # writing / speaking (TEF)
    score: float | None = None  # writing / speaking (DELF), points /25


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
            {
                "id": r.id,
                "title": r.data["title"],
                "format": r.data.get("format", "tef"),
                "sections": len(r.data["sections"]),
            }
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
        return {
            "attempt_id": existing.id,
            "blueprint": bp.data,
            "started_at": existing.started_at.isoformat(),
        }

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
    return {"attempt_id": aid, "blueprint": bp.data, "started_at": attempt.started_at.isoformat()}


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
        "started_at": attempt.started_at.isoformat(),
        "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
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
    delf = _is_delf(await _blueprint_data(session, attempt.blueprint_id))

    if body.skill in ("reading", "listening"):
        if body.correct is None or not body.total:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "need correct + total")
        if body.total <= 0 or body.correct < 0 or body.correct > body.total:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "need 0 <= correct <= total and total > 0"
            )
        detail = {"correct": body.correct, "total": body.total}
        fraction = body.correct / body.total
        result = {"score": delf_points(fraction)} if delf else {"clb": clb_from_fraction(fraction)}
    elif delf:
        if body.score is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "need score")
        if not 0 <= body.score <= DELF_SECTION_MAX:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"need 0 <= score <= {DELF_SECTION_MAX}"
            )
        result = {"score": half_point(body.score)}
        detail = {"score": result["score"]}
    else:
        if body.clb_estimate is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "need clb_estimate")
        result = {"clb": max(1, min(12, body.clb_estimate))}
        detail = {"clb_estimate": result["clb"]}

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
                func.json(json.dumps({**result, "detail": detail})),
            )
        )
    )
    await session.commit()
    await session.refresh(attempt)
    return {
        "skill": body.skill,
        "clb": result.get("clb"),
        "score": result.get("score"),
        "recorded": sorted(attempt.sections),
    }


async def _blueprint_data(session: AsyncSession, blueprint_id: str) -> dict:
    bp = await session.get(ExamBlueprintRow, blueprint_id)
    return bp.data if bp else {"sections": []}


def _is_delf(bp_data: dict) -> bool:
    return bp_data.get("format") == "delf"


@router.post("/{attempt_id}/finish")
async def finish(
    attempt_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    attempt = await _owned_attempt(session, attempt_id, user.id)
    if attempt.status == "finished":  # idempotent
        prog = await session.get(UserProgress, user.id)
        return {
            "attempt_id": attempt.id,
            "report": attempt.clb_report,
            "xp": prog.xp if prog else 0,
            "streak": prog.streak if prog else 0,
        }

    bp_data = await _blueprint_data(session, attempt.blueprint_id)
    required = [s["skill"] for s in bp_data["sections"]]
    missing = [s for s in required if s not in attempt.sections]
    if missing:
        # No score until the test is complete.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"finish all sections first — missing: {', '.join(missing)}",
        )

    if _is_delf(bp_data):
        report = delf_report({skill: d["score"] for skill, d in attempt.sections.items()})
    else:
        report = aggregate_report({skill: d["clb"] for skill, d in attempt.sections.items()})
    now = datetime.now(UTC).replace(tzinfo=None)

    # Atomic status transition: only the first concurrent request that flips
    # "in_progress" -> "finished" wins the race and awards XP (qa-390).
    result = await session.execute(
        update(ExamAttempt)
        .where(ExamAttempt.id == attempt.id, ExamAttempt.status == "in_progress")
        .values(status="finished", finished_at=now, clb_report=report)
    )
    prog = None
    if result.rowcount == 1:
        prog = await record_activity(
            session, user.id, xp_award=EXAM_XP, source="exam", level=attempt.level
        )
    await session.commit()

    # Surface live XP/streak so the client isn't stale after finishing (qa-465,
    # consistent with comprehension submit qa-463). On the awarding request `prog`
    # was just written (xp is an atomic increment → refresh to read it back);
    # otherwise (idempotent loser of the race, or no award) read the current row.
    if prog is not None:
        await session.refresh(prog)
    else:
        prog = await session.get(UserProgress, user.id)
    return {
        "attempt_id": attempt.id,
        "report": report,
        "xp": prog.xp if prog else 0,
        "streak": prog.streak if prog else 0,
    }


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


_TARGET_CLB = 7  # the CLB 7 goal (matches aggregate_report's target_met threshold)


@router.get("/readiness")
async def readiness(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Per-skill CLB readiness from the user's finished mocks: for each skill, the
    best and most-recent CLB plus the chronological trend. Overall is the weakest
    skill's *best* (mirroring `aggregate_report`), so it reflects demonstrated
    ceiling; `weakest_skill` is the nudge target. Empty when no mock is finished."""
    rows = (
        (
            await session.execute(
                select(ExamAttempt)
                .where(ExamAttempt.user_id == user.id, ExamAttempt.status == "finished")
                .order_by(ExamAttempt.id.asc())  # chronological, for the trend
            )
        )
        .scalars()
        .all()
    )

    series: dict[str, list[int]] = {}
    # DELF points aren't CLB bands — readiness tracks the TEF/CLB mocks only.
    rows = [a for a in rows if (a.clb_report or {}).get("format") != "delf"]
    for attempt in rows:
        per_skill = (attempt.clb_report or {}).get("per_skill") or {}
        for skill, clb in per_skill.items():
            if clb is not None:
                series.setdefault(skill, []).append(clb)

    if not series:
        return {
            "attempts": len(rows),
            "per_skill": {},
            "overall": None,
            "target_met": False,
            "weakest_skill": None,
            "target_clb": _TARGET_CLB,
        }

    best = {skill: max(vals) for skill, vals in series.items()}
    report = aggregate_report(best)
    return {
        "attempts": len(rows),
        "per_skill": {
            skill: {"best": max(vals), "recent": vals[-1], "trend": vals}
            for skill, vals in series.items()
        },
        "overall": report["overall"],
        "target_met": report["target_met"],
        "weakest_skill": min(best, key=lambda s: best[s]),
        "target_clb": _TARGET_CLB,
    }
