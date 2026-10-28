"""The shared IPA normalizer (app/content/ipa.py) and the backfill script that uses it.

Offline: no Piper, no network. `WIKTIONARY` pins ~30 common words to their Wiktionary
IPA (stress marks and syllable dots removed) and measures how many the normalize/override
layer reproduces from Piper-style raw phonemes. Measured by hand on the QA 060 box with
real Piper: 22/35 words matched exactly after stripping stress; the real misses were
cacahuète (kakayˈɛt vs kakawɛt), fils (fil vs fis) and oignon (onjˈɔ̃ vs ɔɲɔ̃). Those three
use their real raw Piper output below and are what `IPA_OVERRIDES` repairs; every other
word's raw form is its reference with eSpeak's stress mark prepended (stripping is what
is under test), so agreement here is 30/30 with the overrides and 27/30 without them.
"""

import asyncio
import tempfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401
from app.content.ipa import IPA_MAX, IPA_OVERRIDES, normalize_ipa
from app.content.tables import UserVocab, VocabLookup
from app.users.models import Base
from scripts.backfill_ipa import backfill

# word -> Wiktionary IPA (no stress, no dots)
WIKTIONARY = {
    "bonjour": "bɔ̃ʒuʁ",
    "merci": "mɛʁsi",
    "maison": "mɛzɔ̃",
    "chat": "ʃa",
    "chien": "ʃjɛ̃",
    "pain": "pɛ̃",
    "eau": "o",
    "livre": "livʁ",
    "école": "ekɔl",
    "été": "ete",
    "fils": "fis",
    "oignon": "ɔɲɔ̃",
    "cacahuète": "kakawɛt",
    "ordinateur": "ɔʁdinatœʁ",
    "fenêtre": "fənɛtʁ",
    "table": "tabl",
    "porte": "pɔʁt",
    "rouge": "ʁuʒ",
    "vert": "vɛʁ",
    "bleu": "blø",
    "manger": "mɑ̃ʒe",
    "garçon": "ɡaʁsɔ̃",
    "femme": "fam",
    "homme": "ɔm",
    "enfant": "ɑ̃fɑ̃",
    "café": "kafe",
    "fromage": "fʁɔmaʒ",
    "voiture": "vwatyʁ",
    "lundi": "lœ̃di",
    "semaine": "səmɛn",
}
# Real raw Piper output where it disagrees with Wiktionary (QA 060)
RAW_MISSES = {"cacahuète": "kakayˈɛt", "fils": "fil", "oignon": "onjˈɔ̃"}


def _raw(word: str) -> str:
    return RAW_MISSES.get(word) or "ˈ" + WIKTIONARY[word]


def test_normalize_agrees_with_wiktionary_table():
    agree = [w for w, ref in WIKTIONARY.items() if normalize_ipa(_raw(w), w) == ref]
    assert sorted(set(WIKTIONARY) - set(agree)) == []
    plain = [w for w, ref in WIKTIONARY.items() if normalize_ipa(_raw(w)) == ref]
    assert sorted(set(WIKTIONARY) - set(plain)) == sorted(RAW_MISSES)  # overrides earn their keep


def test_overrides_are_only_for_words_the_table_covers():
    assert set(IPA_OVERRIDES) - {"oignons", "cacahuètes"} <= set(WIKTIONARY)


def test_normalize_strips_stress_and_collapses_spaces():
    assert normalize_ipa("  ʒə  vˈyɛ ˌa ", "x") == "ʒə vyɛ a"
    assert normalize_ipa("", "fils") == ""


def test_long_phrase_is_cut_on_a_word_boundary():
    raw = "ʒə vudʁˈɛz œ̃ ɡʁˈɑ̃ kafˈe kʁˈɛm avˌɛk œ̃ kʁwasˈɑ̃ o bˈœʁ sil vu plˈɛ e œ̃ bˈaɡɛt"
    ipa = normalize_ipa(raw, "phrase")
    whole = " ".join(raw.replace("ˈ", "").replace("ˌ", "").split())
    assert len(whole) > IPA_MAX >= len(ipa) and whole.startswith(ipa + " ")
    assert not ipa.endswith(" ")
    assert len(normalize_ipa("a" * 100, "x")) == IPA_MAX  # no space to cut at


# --- backfill script ----------------------------------------------------------


class FakePiper:
    """Reports stressed Piper-style IPA for every word."""

    def synthesize_ipa(self, *, text, voice=""):
        return b"RIFF", f"ˈ{text[:3]}"


class FakeStorage:
    def __init__(self, keys):
        self.keys = set(keys)

    def delete(self, key):
        self.keys.discard(key)


def _db():
    engine = create_async_engine(f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/b.db")

    async def create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create())
    return async_sessionmaker(engine, expire_on_commit=False)


def test_backfill_dry_run_apply_and_idempotence():
    Session = _db()

    async def seed():
        async with Session() as s:
            s.add_all(
                [
                    VocabLookup(slug="chat", fr="chat", en="cat", ipa="kæt", audio_key="k/chat"),
                    VocabLookup(slug="fils", fr="fils", en="son", ipa="", audio_key="k/fils"),
                    VocabLookup(slug="il", fr="œil", en="eye", ipa="œj", audio_key="k/il"),
                    VocabLookup(slug="ete", fr="été", en="summer", ipa=""),
                    UserVocab(user_id=1, card_key="uv:chat", fr="chat", en="cat", ipa="WRONG"),
                    UserVocab(user_id=1, card_key="uv:ete", fr="ete", en="summer", ipa="x"),
                ]
            )
            await s.commit()

    async def snapshot():
        async with Session() as s:
            lk = {r.slug: r.ipa for r in (await s.scalars(select(VocabLookup))).all()}
            cards = {r.card_key: r.ipa for r in (await s.scalars(select(UserVocab))).all()}
            return lk, cards

    async def run(apply, storage):
        async with Session() as s:
            return await backfill(s, FakePiper(), storage, "v", apply=apply)

    asyncio.run(seed())
    before = asyncio.run(snapshot())
    storage = FakeStorage({"k/il"})

    dry = asyncio.run(run(False, storage))
    assert asyncio.run(snapshot()) == before and storage.keys == {"k/il"}  # dry run: no change
    assert dry["lookup_deleted"] == 1 and dry["unaccented_cards"] == 1

    asyncio.run(run(True, storage))
    lookups, cards = asyncio.run(snapshot())
    assert "il" not in lookups and storage.keys == set()  # poisoned row + clip gone
    assert lookups["fils"] == "fis"  # override; empty IPA with a clip is filled
    assert lookups["chat"] == "cha" and lookups["ete"] == "été"[:3]
    assert cards == {"uv:chat": "cha", "uv:ete": "ete"}  # IPA only; fr untouched

    again = asyncio.run(run(True, storage))
    assert asyncio.run(snapshot()) == (lookups, cards)
    assert not (again["lookup_deleted"] or again["lookup_ipa"] or again["card_ipa"])
