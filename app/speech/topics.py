"""Speaking topics: authored TEF Expression Orale prompts the learner picks to
frame a practice session.

`SpeakingTopic` is authored content (content/<level>/speaking/*.yaml). Topics are
synced into `speaking_topics` per level (delete-and-replace), then listed by the
API and used to seed the examiner's system prompt for a focused session.

Section A = obtain information (the learner asks the examiner questions);
Section B = give and defend an opinion (the learner develops an argument).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.loaders import load_keyed_yaml
from app.speech.tables import SpeakingTopicRow

DEFAULT_CONTENT_ROOT = "content"


class TopicError(Exception):
    pass


class SpeakingTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    level: str
    section: Literal["A", "B"]
    title: str
    prompt: str  # the French task statement shown to the learner
    # Angles the learner can develop — shown as hints and blended into the
    # examiner framing so follow-ups push toward these.
    points: list[str] = []


def load_topics(content_root: str | Path, level: str) -> dict[str, SpeakingTopic]:
    return load_keyed_yaml(
        Path(content_root) / level / "speaking",
        SpeakingTopic,
        duplicate_error=lambda i, f: TopicError(f"duplicate speaking topic id {i!r} ({f})"),
    )


def framing(topic: SpeakingTopic) -> str:
    """A system-prompt addendum that focuses the examiner on this topic. Composed
    from the section so Section A (get info) and Section B (argue) are role-played
    correctly."""
    points = ", ".join(topic.points)
    hint = f" Encourage them to cover: {points}." if points else ""
    if topic.section == "A":
        return (
            "\n\n## Today's task (TEF Expression Orale — Section A: obtenir des informations)\n"
            f"The learner is practising this task: «{topic.prompt}». Play the relevant role and "
            "let THEM lead by asking you questions to get the information they need. Answer "
            "naturally, and if they stall, prompt them for the next question they could ask."
            f"{hint}"
        )
    return (
        "\n\n## Today's task (TEF Expression Orale — Section B: donner son opinion)\n"
        f"The learner is practising this task: «{topic.prompt}». Keep the conversation on this "
        "topic and help them build and structure an argument: acknowledge their point, then ask "
        "one follow-up that pushes them to develop or justify it further."
        f"{hint}"
    )


async def sync_topics(session: AsyncSession, content_root: str | Path, level: str) -> int:
    topics = load_topics(content_root, level)
    await session.execute(delete(SpeakingTopicRow).where(SpeakingTopicRow.level == level))
    for t in topics.values():
        session.add(
            SpeakingTopicRow(
                id=t.id, level=level, section=t.section, data=t.model_dump(mode="json")
            )
        )
    await session.commit()
    return len(topics)


async def _main(level: str, content_root: str) -> None:
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        n = await sync_topics(session, content_root, level)
    print(f"synced level {level!r}: {n} speaking topics")


if __name__ == "__main__":
    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    _root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CONTENT_ROOT
    asyncio.run(_main(_level, _root))
