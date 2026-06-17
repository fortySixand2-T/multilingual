"""AC1.2 — FSRS scheduling + the review-queue persistence layer."""

import asyncio
import tempfile
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.srs.models  # noqa: F401 - register table
from app.srs.fsrs import FSRSEngine
from app.srs.service import due_cards, review_card, seed_cards
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/srs.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


# --- engine (no DB) -----------------------------------------------------------


def test_new_card_then_good_moves_due_into_future():
    eng = FSRSEngine()
    now = datetime.now(UTC)
    fresh = eng.new(now=now)
    reviewed = eng.review(fresh.state, "good", now=now)
    assert reviewed.due > now


def test_again_schedules_sooner_than_good():
    eng = FSRSEngine()
    now = datetime.now(UTC)
    fresh = eng.new(now=now)
    again = eng.review(fresh.state, "again", now=now)
    good = eng.review(fresh.state, "good", now=now)
    assert again.due < good.due


def test_unknown_rating_raises():
    eng = FSRSEngine()
    with pytest.raises(ValueError):
        eng.review(eng.new().state, "brilliant")


# --- service (DB) -------------------------------------------------------------


def test_seed_is_idempotent_and_queue_returns_due_cards():
    async def go():
        async with _Session() as s:
            created = await seed_cards(s, user_id=7, card_keys=["bonjour", "salut", "bonjour"])
            await s.commit()
            again = await seed_cards(s, user_id=7, card_keys=["bonjour", "salut"])
            await s.commit()
            queue = await due_cards(s, user_id=7)
            return created, again, sorted(c.card_key for c in queue)

    created, again, keys = _run(go())
    assert created == 2  # de-duped; "bonjour" counted once
    assert again == 0  # existing cards not re-seeded
    assert keys == ["bonjour", "salut"]


def test_review_advances_due_and_missing_card_returns_none():
    async def go():
        async with _Session() as s:
            await seed_cards(s, user_id=9, card_keys=["eau"])
            await s.commit()
            before = (await due_cards(s, user_id=9))[0].due
            new_due = await review_card(s, user_id=9, card_key="eau", rating="good")
            await s.commit()
            missing = await review_card(s, user_id=9, card_key="ghost", rating="good")
            return before, new_due, missing

    before, new_due, missing = _run(go())
    assert new_due > before
    assert missing is None
