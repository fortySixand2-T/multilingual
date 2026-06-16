"""Writing assessment API: deliver tasks, grade a submission, retrieve feedback.

Grading routes through the AI router (injected, so tests use a fake). A malformed
grade is a graceful 502; a provider outage is the global 503. The CLB estimate is
presented as an estimate (R3) — the prompt + low temperature keep it stable.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import AIRouter
from app.api.auth import get_current_user
from app.api.deps import get_ai_router
from app.assessment.grader import GradingError, WritingGrader
from app.assessment.tables import WritingSubmission, WritingTaskRow
from app.config.settings import Settings, get_settings
from app.db.session import get_session
from app.users.models import User

router = APIRouter(prefix="/assessment", tags=["assessment"])


class SubmitBody(BaseModel):
    text: str


@router.get("/tasks")
async def list_tasks(
    level: str,
    section: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    q = select(WritingTaskRow).where(WritingTaskRow.level == level)
    if section:
        q = q.where(WritingTaskRow.section == section)
    rows = (await session.execute(q.order_by(WritingTaskRow.id))).scalars().all()
    return {
        "tasks": [
            {
                "id": r.id,
                "section": r.section,
                "title": r.data["title"],
                "prompt": r.data["prompt"],
                "min_words": r.data["min_words"],
                "max_words": r.data.get("max_words"),
            }
            for r in rows
        ]
    }


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    row = await session.get(WritingTaskRow, task_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"task {task_id!r} not found")
    return row.data


@router.post("/tasks/{task_id}/submit")
async def submit(
    task_id: str,
    body: SubmitBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    row = await session.get(WritingTaskRow, task_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"task {task_id!r} not found")
    if not body.text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "submission is empty")

    grader = WritingGrader(ai_router)
    try:
        result = await grader.grade(
            session,
            user.id,
            task_prompt=row.data["prompt"],
            section=row.data["section"],
            submission=body.text,
            daily_budget=settings.writing_daily_token_budget,
        )
    except GradingError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"could not grade: {e}") from None

    if result.over_budget:
        return {
            "task_id": task_id,
            "over_budget": True,
            "word_count": result.word_count,
            "feedback": None,
        }

    fb = result.feedback
    min_words = row.data.get("min_words", 0)
    submission = WritingSubmission(
        user_id=user.id,
        task_id=task_id,
        text=body.text,
        clb_estimate=fb.clb_estimate,
        feedback=fb.model_dump(mode="json"),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(submission)
    await session.commit()
    return {
        "task_id": task_id,
        "submission_id": submission.id,
        "over_budget": False,
        "word_count": result.word_count,
        "meets_min_words": result.word_count >= min_words,
        "provider": result.provider,
        "model": result.model,
        "feedback": fb.model_dump(mode="json"),
    }


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    sub = await session.get(WritingSubmission, submission_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
    return {
        "submission_id": sub.id,
        "task_id": sub.task_id,
        "text": sub.text,
        "clb_estimate": sub.clb_estimate,
        "feedback": sub.feedback,
        "created_at": sub.created_at.isoformat(),
    }
