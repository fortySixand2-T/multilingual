#!/usr/bin/env python3
"""Re-derive learner-facing IPA for stored words with the app's own Piper TTS (QA 060).

Rows written before PR #121 hold LLM-guessed English-shaped IPA ("cacahuetes" ->
/pəˈnuːz/), and older Piper rows carry stress marks. This re-voices every
`vocab_lookup` and `user_vocab` word and stores the result of the shared
`normalize_ipa` (the same function the live path uses), IPA only: clips and card
data are never touched.

Also deletes `vocab_lookup` rows whose slug no longer matches `lookup_slug(row.fr)`
(the old "il" row holding "œil", QA 871) together with their clip, so the next lookup
regenerates them. Cards whose `fr` is an unaccented spelling of a known accented
headword (QA 891) are only reported; user data is never rewritten.

Idempotent. Dry-run unless `--apply`. On the box, inside the app container:

    docker exec multilingual-app-1 /app/.venv/bin/python scripts/backfill_ipa.py  # preview
    docker exec multilingual-app-1 /app/.venv/bin/python scripts/backfill_ipa.py --apply

TTS_BACKEND/PIPER_VOICE/PIPER_WORD_VOICE come from the app settings; `--database-url`
defaults to the app's DATABASE_URL.

Agreement of Piper's raw output with a Wiktionary-style reference (measured by hand on
the QA 060 box): 22/35 words exact after stripping stress marks; the real misses were
cacahuète (kakayɛt), fils (fil) and oignon (onjɔ̃), which `IPA_OVERRIDES` now covers
(see tests/test_ipa.py).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # run as a plain script

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config.settings import get_settings  # noqa: E402
from app.content.lookup import lookup_slug, voice_with_ipa  # noqa: E402
from app.content.tables import UserVocab, VocabLookup  # noqa: E402
from app.speech.factory import build_tts  # noqa: E402
from app.storage.factory import build_storage  # noqa: E402

log = logging.getLogger("backfill_ipa")


async def backfill(session: AsyncSession, tts, storage, voice: str, *, apply: bool) -> Counter:
    """Returns counts: lookup_deleted, lookup_ipa, card_ipa, unaccented_cards, unchanged."""
    done: Counter = Counter()
    derived: dict[str, str] = {}

    def derive(fr: str) -> str:
        if fr not in derived:
            derived[fr] = voice_with_ipa(tts, fr, voice)[1]
        return derived[fr]

    lookups = (await session.scalars(select(VocabLookup))).all()
    for row in lookups:
        if lookup_slug(row.fr) != row.slug:  # poisoned: the shared slug holds another word
            log.info("delete lookup %r (fr=%r)", row.slug, row.fr)
            done["lookup_deleted"] += 1
            if apply:
                if row.audio_key:
                    storage.delete(row.audio_key)
                await session.delete(row)
            continue
        _update_ipa(row, derive(row.fr), done, "lookup_ipa", apply)

    headwords = {r.slug: r.fr for r in lookups}
    for card in (await session.scalars(select(UserVocab))).all():
        _update_ipa(card, derive(card.fr), done, "card_ipa", apply)
        known = headwords.get(lookup_slug(card.fr), "")
        if card.fr.isascii() and not known.isascii():
            log.info("report: card %r (user %d) vs headword %r", card.fr, card.user_id, known)
            done["unaccented_cards"] += 1
    if apply:
        await session.commit()
    return done


def _update_ipa(row, ipa: str, done: Counter, name: str, apply: bool) -> None:
    if not ipa or ipa == row.ipa:
        done["unchanged"] += 1
        return
    log.info("%s %r: %r -> %r", name, row.fr, row.ipa, ipa)
    done[name] += 1
    if apply:
        row.ipa = ipa


async def _main(args: argparse.Namespace) -> None:
    settings = get_settings()
    tts = build_tts(settings)
    if tts is None:
        raise SystemExit("TTS_BACKEND is disabled: nothing to derive IPA with")
    engine = create_async_engine(args.database_url or settings.database_url)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        done = await backfill(
            session, tts, build_storage(settings), settings.word_voice, apply=args.apply
        )
    await engine.dispose()
    print(f"{'APPLIED' if args.apply else 'DRY RUN (use --apply to write)'}: {dict(done)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--database-url", help="default: the app's DATABASE_URL")
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
