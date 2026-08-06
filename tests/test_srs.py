"""AC1.2 — FSRS scheduling + the review-queue persistence layer."""

import asyncio
import tempfile
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.srs.models  # noqa: F401 - register table
from app.srs.fsrs import FSRSEngine, difficulty
from app.srs.service import due_cards, hardest_cards, review_card, seed_cards
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


def test_difficulty_none_until_reviewed():
    eng = FSRSEngine()
    fresh = eng.new()
    assert difficulty(fresh.state) is None  # no signal before the first review
    hard = eng.review(fresh.state, "again")
    easy = eng.review(fresh.state, "easy")
    assert difficulty(hard.state) > difficulty(easy.state)  # "again" is harder than "easy"


def test_hardest_cards_ranks_reviewed_by_difficulty_excluding_new():
    # Slice 2: three cards rated again/hard/easy rank hardest-first; an unreviewed card
    # (no difficulty signal) is excluded entirely.
    async def go():
        async with _Session() as s:
            await seed_cards(s, user_id=30, card_keys=["tough", "medium", "trivial", "fresh"])
            await s.commit()
            await review_card(s, 30, "tough", "again")
            await review_card(s, 30, "medium", "hard")
            await review_card(s, 30, "trivial", "easy")
            await s.commit()  # "fresh" is never reviewed
            ranked = await hardest_cards(s, user_id=30)
            return [(c.card_key, round(d, 1)) for c, d in ranked]

    ranked = _run(go())
    keys = [k for k, _ in ranked]
    assert "fresh" not in keys  # unreviewed cards carry no difficulty -> excluded
    assert keys == ["tough", "medium", "trivial"]  # hardest first
    assert ranked[0][1] >= ranked[-1][1]


def test_hardest_cards_respects_limit():
    async def go():
        async with _Session() as s:
            keys = [f"w{i}" for i in range(5)]
            await seed_cards(s, user_id=31, card_keys=keys)
            await s.commit()
            for k in keys:
                await review_card(s, 31, k, "hard")
            await s.commit()
            return await hardest_cards(s, user_id=31, limit=2)

    assert len(_run(go())) == 2


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


def test_again_persists_sooner_due_than_easy():
    # Slice 2 (H8): the difficulty->frequency invariant at the service/persistence
    # layer, not just the raw FSRS engine — an "again"-rated card must be persisted
    # with a due date sooner than an "easy"-rated card, seeded and reviewed under
    # the exact same DB/service path a real request takes.
    async def go():
        async with _Session() as s:
            await seed_cards(s, user_id=40, card_keys=["tough_word", "easy_word"])
            await s.commit()
            again_due = await review_card(s, 40, "tough_word", "again")
            easy_due = await review_card(s, 40, "easy_word", "easy")
            await s.commit()
            return again_due, easy_due

    again_due, easy_due = _run(go())
    assert again_due < easy_due


def test_personal_card_key_gets_identical_scheduling_to_content_key():
    # Slice 2 (H8): personal (`uv:`) cards ride the exact same FSRSEngine/service
    # path as content cards — an "again" rating on a `uv:` key must schedule sooner
    # than an "easy" rating on another `uv:` key, matching the content-card gap.
    async def go():
        async with _Session() as s:
            await seed_cards(s, user_id=41, card_keys=["uv:chameau", "uv:hibou"])
            await s.commit()
            again_due = await review_card(s, 41, "uv:chameau", "again")
            easy_due = await review_card(s, 41, "uv:hibou", "easy")
            await s.commit()
            return again_due, easy_due

    again_due, easy_due = _run(go())
    assert again_due < easy_due
