"""Personal vocab decks (Slice E): the user_vocab service, the /vocab/personal API,
lazy pronunciation, and that personal cards flow through the shared /srs review queue.

DB is a temp SQLite built from Base.metadata; the LLM/TTS/storage are faked, so the
whole thing runs offline and deterministically.
"""

import asyncio
import json
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401  (register user_vocab / content_vocab for create_all)
import app.srs.models  # noqa: F401  (register srs_cards)
import app.usage.models  # noqa: F401  (register daily_usage)
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.content import personal as P
from app.content.tables import UserVocab, VocabLookup
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/personal.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


class FakeRouter:
    """Returns a fixed dictionary-entry JSON; records calls."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[str] = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append(profile)
        return LLMResult(
            text=json.dumps(self.payload),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=10, output_tokens=6),
        )


class FakeTTS:
    name = "fake-tts"

    def __init__(self):
        self.calls = 0

    def synthesize(self, *, text, voice, lang="fr"):
        self.calls += 1
        return b"RIFFfakewav-" + text.encode("utf-8")


class FakeStorage:
    name = "fake"

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type="application/octet-stream"):
        self.objects[key] = data
        return f"mem://{key}"

    def get(self, key):
        return self.objects[key]


def _client(*, uid=7, router=None, tts=None):
    storage = FakeStorage()

    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = uid

    app = create_app()
    app.state.tts = tts
    app.state.stt = None
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router or FakeRouter({})
    app.dependency_overrides[get_storage] = lambda: storage
    return TestClient(app), storage


# --- pure helpers -------------------------------------------------------------


def test_key_namespacing():
    assert P.personal_key("café") == "uv:cafe"
    assert P.personal_key("l'ordinateur") == "uv:l_ordinateur"
    assert P.is_personal_key("uv:cafe")
    assert not P.is_personal_key("cafe")  # a content id is not personal


def test_add_personal_is_idempotent_per_user():
    async def go():
        async with _Session() as s:
            row1, created1 = await P.add_personal(s, 1, fr="ordinateur", en="computer", gender="m")
            row2, created2 = await P.add_personal(s, 1, fr="ordinateur", en="different gloss")
            await s.commit()
            return row1, created1, row2, created2

    row1, created1, row2, created2 = _run(go())
    assert created1 is True and created2 is False
    assert row1.card_key == row2.card_key == "uv:ordinateur"
    assert row2.en == "computer"  # re-add did NOT overwrite the original


# --- API: preview -------------------------------------------------------------


def test_preview_enriches_without_writing():
    router = FakeRouter({"en": "computer", "pos": "noun", "gender": "x", "ipa": "/ɔʁdinatœʁ/"})
    client, _ = _client(router=router)
    r = client.post("/vocab/personal/preview", json={"word": "le silence"})
    assert r.status_code == 200
    enr = r.json()["enrichment"]
    assert enr["fr"] == "silence"  # article stripped
    assert enr["en"] == "computer"
    # "silence" is in the seed gender table as masculine — table beats the model's junk 'x'
    assert enr["gender"] == "m" and enr["gender_source"] == "table"
    assert router.calls == ["vocab_enrich"]
    # preview stores no card (only the shared lookup cache)
    assert client.get("/vocab/personal").json()["cards"] == []


def test_preview_respects_daily_budget():
    router = FakeRouter({"en": "x", "pos": "noun", "gender": "m", "ipa": ""})
    client, _ = _client(uid=42, router=router)
    # exhaust the vocab budget directly via the usage ledger
    from datetime import date

    async def burn():
        async with _Session() as s:
            from app.usage.service import add_usage

            await add_usage(s, 42, "vocab", 999_999, 0, date.today())
            await s.commit()

    _run(burn())
    r = client.post("/vocab/personal/preview", json={"word": "chat"})
    assert r.json() == {"enrichment": None, "over_budget": True}
    assert router.calls == []  # no LLM call once over budget


# --- API: add + list + queue integration --------------------------------------


def test_add_card_seeds_review_and_appears_in_queue():
    client, _ = _client(uid=8)
    r = client.post(
        "/vocab/personal",
        json={"fr": "épanouissement", "en": "fulfillment", "gender": "m", "pos": "noun"},
    )
    body = r.json()
    assert body["added"] is True and body["review_seeded"] is True
    key = body["card"]["card_key"]
    assert key == "uv:epanouissement"
    assert body["card"]["audio_url"] == f"/vocab/personal/audio/{key}"

    # it's in "My deck"
    cards = client.get("/vocab/personal").json()["cards"]
    assert [c["card_key"] for c in cards] == [key]

    # ...and in the shared review queue, resolved from user_vocab (not content_vocab)
    due = client.get("/srs/queue").json()["due"]
    entry = next(d for d in due if d["card_key"] == key)
    assert entry["vocab"]["fr"] == "épanouissement"
    assert entry["vocab"]["personal"] is True
    assert entry["vocab"]["audio_url"] == f"/vocab/personal/audio/{key}"


def test_add_rejects_degenerate_words_no_blank_card():
    # QA round 049: whitespace / punctuation / non-Latin words slugify to "" and used to
    # be stored as a shared blank "uv:" card that leaked into the review queue. They must
    # now be rejected (422), and nothing gets stored.
    client, _ = _client(uid=13)
    for bad in ["   ", "!!!", "があ", "。。。"]:
        r = client.post("/vocab/personal", json={"fr": bad, "en": "junk"})
        assert r.status_code == 422, f"{bad!r} should be rejected, got {r.status_code}"
    assert client.get("/vocab/personal").json()["cards"] == []
    # and no blank card sneaked into the queue
    due = client.get("/srs/queue").json()["due"]
    assert not any(d["card_key"] == "uv:" for d in due)


def test_card_key_never_exceeds_column_limit():
    # QA round 049 #611: a long fr (API caps it at 128) must not mint a card_key past the
    # user_vocab.card_key String(64) column, or a length-enforcing DB (Postgres) 500s.
    client, _ = _client(uid=15)
    long_fr = ("anticonstitutionnellement " * 4).strip()  # ~103 chars, under the 128 API cap
    r = client.post("/vocab/personal", json={"fr": long_fr, "en": "x"})
    assert r.status_code == 200, r.text
    card = r.json()["card"]
    assert len(card["card_key"]) <= 64
    assert card["card_key"].startswith("uv:")


def test_long_phrases_sharing_a_prefix_get_distinct_keys():
    # QA 872: slugs were cut at 64, so "...demain matin" and "...demain mardi" shared
    # one cached lookup (the learner looked up "mardi" and heard "matin").
    from app.content.lookup import lookup_slug

    stem = "pas de problème mais il faut absolument que tu viennes demain "
    keys = {lookup_slug(stem + end) for end in ("matin", "mardi", "matin tôt")}
    assert len(keys) == 3 and all(len(k) <= 64 for k in keys)
    cards = {P.personal_key(stem + end) for end in ("matin", "mardi")}
    assert len(cards) == 2 and all(len(k) <= 64 for k in cards)
    assert lookup_slug("café") == "cafe"  # short words keep their plain slug


def test_add_strips_leading_article_like_preview():
    # A direct add of "le chien" should store the bare lemma (matching the preview flow),
    # not "le chien" with key uv:le_chien.
    client, _ = _client(uid=14)
    card = client.post("/vocab/personal", json={"fr": "le chien", "en": "dog"}).json()["card"]
    assert card["card_key"] == "uv:chien" and card["fr"] == "chien"


def test_add_card_is_idempotent():
    client, _ = _client(uid=9)
    first = client.post("/vocab/personal", json={"fr": "loisir", "en": "leisure"}).json()
    second = client.post("/vocab/personal", json={"fr": "loisir", "en": "hobby"}).json()
    assert first["added"] is True and second["added"] is False
    # only one card, original gloss kept
    cards = client.get("/vocab/personal").json()["cards"]
    assert len(cards) == 1 and cards[0]["en"] == "leisure"


# --- API: one-click enrich-and-add (Slice 3c rich tier) -----------------------


def test_from_word_enriches_and_adds():
    # Speaking rich tier: POST a bare word -> enrich (Slice D) -> stored personal card
    # + seeded review, in one call. Gender comes from the table backstop.
    router = FakeRouter({"en": "fulfillment", "pos": "noun", "gender": "x", "ipa": "epanwismɑ̃"})
    client, _ = _client(uid=20, router=router)
    r = client.post("/vocab/personal/from-word", json={"word": "l'épanouissement"})
    assert r.status_code == 200
    body = r.json()
    assert body["added"] is True and body["review_seeded"] is True
    assert body["card"]["card_key"] == "uv:epanouissement"  # article stripped
    assert body["card"]["en"] == "fulfillment"
    assert body["card"]["source"] == "speaking"
    assert router.calls == ["vocab_enrich"]
    # it's in the deck and the shared review queue
    assert client.get("/vocab/personal").json()["cards"][0]["card_key"] == "uv:epanouissement"
    assert any(d["card_key"] == "uv:epanouissement" for d in client.get("/srs/queue").json()["due"])


def test_from_word_respects_daily_budget():
    from datetime import date

    router = FakeRouter({"en": "x", "pos": "noun", "gender": "m", "ipa": ""})
    client, _ = _client(uid=21, router=router)

    async def burn():
        async with _Session() as s:
            from app.usage.service import add_usage

            await add_usage(s, 21, "vocab", 999_999, 0, date.today())
            await s.commit()

    _run(burn())
    r = client.post("/vocab/personal/from-word", json={"word": "chat"})
    assert r.json() == {"card": None, "added": False, "over_budget": True}
    assert router.calls == []  # no enrich call once over budget
    assert client.get("/vocab/personal").json()["cards"] == []  # nothing stored


def test_from_word_rejects_word_already_in_content_bank():
    # QA round-050 #620: a caller hitting from-word directly (bypassing the Speaking
    # UI's resolve_new_words filter) with a word already in the content bank must not
    # mint a duplicate uv: card for it.
    from app.content.tables import ContentVocab

    async def seed():
        async with _Session() as s:
            s.add(ContentVocab(id="cuisiner", level="a2", data={"fr": "cuisiner", "en": "to cook"}))
            await s.commit()

    _run(seed())

    router = FakeRouter({"en": "to cook", "pos": "verb", "gender": "", "ipa": ""})
    client, _ = _client(uid=22, router=router)
    r = client.post("/vocab/personal/from-word", json={"word": "cuisiner"})
    assert r.status_code == 422
    assert "content bank" in r.json()["detail"]
    # no duplicate uv: card was minted
    assert client.get("/vocab/personal").json()["cards"] == []
    due = client.get("/srs/queue").json()["due"]
    assert not any(d["card_key"] == "uv:cuisiner" for d in due)


# --- API: hardest deck (Slice 2) ----------------------------------------------


def test_hardest_endpoint_ranks_and_resolves_personal_card_vocab():
    # A personal card rated "again" is hard; it appears in /srs/hardest with its
    # difficulty and fully-resolved personal vocab metadata (fr/en/audio_url).
    client, _ = _client(uid=25)
    key = client.post("/vocab/personal", json={"fr": "quolibet", "en": "gibe"}).json()["card"][
        "card_key"
    ]
    client.post("/srs/review", json={"card_key": key, "rating": "again"})

    cards = client.get("/srs/hardest").json()["cards"]
    entry = next(c for c in cards if c["card_key"] == key)
    assert entry["difficulty"] >= 1.0
    assert entry["vocab"]["fr"] == "quolibet" and entry["vocab"]["personal"] is True
    assert entry["vocab"]["audio_url"] == f"/vocab/personal/audio/{key}"


def test_hardest_endpoint_excludes_unreviewed_cards():
    client, _ = _client(uid=26)
    key = client.post("/vocab/personal", json={"fr": "farfelu", "en": "wacky"}).json()["card"][
        "card_key"
    ]
    # never reviewed -> no difficulty signal -> not in the hardest deck
    cards = client.get("/srs/hardest").json()["cards"]
    assert all(c["card_key"] != key for c in cards)


def test_hardest_endpoint_rejects_negative_limit():
    # QA round 051 #621: a negative limit used to silently truncate the tail of the
    # ranked deck via Python slice semantics (`ranked[:-1]`) instead of erroring.
    client, _ = _client(uid=27)
    r = client.get("/srs/hardest", params={"limit": -1})
    assert r.status_code == 422


def test_queue_difficulty_rounded_same_as_hardest():
    # QA round 051 #622: /srs/queue used to return the raw unrounded FSRS float while
    # /srs/hardest rounded to 1dp for the same underlying signal.
    from datetime import datetime

    from sqlalchemy import update

    from app.srs.models import ReviewCard

    client, _ = _client(uid=28)
    key = client.post("/vocab/personal", json={"fr": "acariatre", "en": "cranky"}).json()["card"][
        "card_key"
    ]
    client.post("/srs/review", json={"card_key": key, "rating": "again"})

    # "again" reschedules the card into the future, which would drop it out of the due
    # queue; force it back due now so we can compare the same card's difficulty across
    # both endpoints.
    async def make_due():
        async with _Session() as s:
            await s.execute(
                update(ReviewCard)
                .where(ReviewCard.user_id == 28, ReviewCard.card_key == key)
                .values(due=datetime(2000, 1, 1))
            )
            await s.commit()

    _run(make_due())

    due = client.get("/srs/queue").json()["due"]
    hardest = client.get("/srs/hardest").json()["cards"]
    due_entry = next(d for d in due if d["card_key"] == key)
    hardest_entry = next(c for c in hardest if c["card_key"] == key)
    assert due_entry["difficulty"] == hardest_entry["difficulty"]
    assert due_entry["difficulty"] == round(due_entry["difficulty"], 1)


# --- API: lazy pronunciation --------------------------------------------------


def test_personal_audio_synthesizes_once_and_caches():
    tts = FakeTTS()
    client, storage = _client(uid=10, tts=tts)
    key = client.post("/vocab/personal", json={"fr": "papillon", "en": "butterfly"}).json()["card"][
        "card_key"
    ]

    r1 = client.get(f"/vocab/personal/audio/{key}")
    assert r1.status_code == 200 and r1.content == b"RIFFfakewav-papillon"
    assert tts.calls == 1

    # second play is served from the cached key — no re-synthesis
    r2 = client.get(f"/vocab/personal/audio/{key}")
    assert r2.status_code == 200 and r2.content == r1.content
    assert tts.calls == 1

    # the cache key was persisted on the row
    async def fetch():
        async with _Session() as s:
            return await s.scalar(select(UserVocab).where(UserVocab.card_key == key))

    row = _run(fetch())
    assert row.audio_key is not None


def test_personal_audio_unknown_card_is_404():
    client, _ = _client(uid=11, tts=FakeTTS())
    assert client.get("/vocab/personal/audio/uv:nope").status_code == 404


# --- durable shared lookup cache ------------------------------------------------


class FakePiper(FakeTTS):
    """A TTS that, like Piper, also reports the IPA it voiced."""

    def synthesize_ipa(self, *, text, voice=""):
        self.calls += 1
        return b"RIFFpiper-" + text.encode("utf-8"), "pakˈɛ"


def test_lookup_is_cached_across_users_case_and_accents():
    router = FakeRouter({"en": "peanut", "pos": "noun", "gender": "f", "ipa": "pəˈnæt"})
    tts = FakePiper()
    client, storage = _client(uid=31, router=router, tts=tts)
    first = client.post("/vocab/personal/preview", json={"word": "cacahuète"}).json()["enrichment"]
    # IPA comes from Piper's phonemes, not the LLM's English guess
    assert first["en"] == "peanut" and first["ipa"] == "kakawɛt"  # no stress; curated override
    assert storage.objects["vocablookup/cacahuete.wav"].startswith(b"RIFFpiper-")

    # another user, different case, no accent: served from the DB — no LLM, no TTS
    other, _ = _client(uid=32, router=router, tts=tts)
    again = other.post("/vocab/personal/preview", json={"word": "Cacahuete"}).json()["enrichment"]
    assert again == first
    assert router.calls == ["vocab_enrich"] and tts.calls == 1


def test_without_tts_card_has_no_llm_ipa_until_first_voiced():
    """QA 832: with TTS down, the LLM's English-shaped IPA ("hɒrəbəl") used to land on
    the card. Now there's no IPA until Piper voices the word on first play."""
    llm = {"en": "hair-raising", "pos": "adjective", "gender": "", "ipa": "ɪbʊrɪfænt"}
    router = FakeRouter(llm)
    client, _ = _client(uid=35, router=router, tts=None)
    card = client.post("/vocab/personal/from-word", json={"word": "ébouriffant"}).json()["card"]
    assert card["ipa"] == ""
    assert client.get("/vocab/personal/audio/uv:ebouriffant").status_code == 404  # no TTS

    voiced, _ = _client(uid=35, router=router, tts=FakePiper())
    assert voiced.get("/vocab/personal/audio/uv:ebouriffant").status_code == 200
    (card,) = voiced.get("/vocab/personal").json()["cards"]
    assert card["ipa"] == "pakɛ"  # what Piper voiced, stress stripped


def test_stale_ipa_is_overwritten_on_next_voicing():
    """QA 868: a card added before the 832 fix (or otherwise carrying a stale/wrong
    IPA) must have it replaced, not permanently skipped, once a working TTS voices it
    — matching lookup.py::fresh_lookup's unconditional overwrite."""
    router = FakeRouter({"en": "hair-raising", "pos": "adjective", "gender": "", "ipa": ""})
    client, _ = _client(uid=36, router=router, tts=None)
    client.post("/vocab/personal/from-word", json={"word": "horrible"})

    async def poison():
        async with _Session() as s:
            row = await s.scalar(select(UserVocab).where(UserVocab.card_key == "uv:horrible"))
            row.ipa = "hɒrəbəl"  # stale, LLM-guessed English-shaped IPA
            await s.commit()

    _run(poison())

    voiced, _ = _client(uid=36, router=router, tts=FakePiper())
    assert voiced.get("/vocab/personal/audio/uv:horrible").status_code == 200
    (card,) = voiced.get("/vocab/personal").json()["cards"]
    assert card["ipa"] == "pakɛ"  # overwritten with what Piper actually voiced


def test_failed_lookup_is_not_cached_and_says_why():
    client, _ = _client(uid=33, router=FakeRouter({"en": "", "pos": ""}))
    r = client.post("/vocab/personal/preview", json={"word": "zxqwv"})
    assert r.status_code == 422 and "check the spelling" in r.json()["detail"]
    # a later good answer is used, not a cached failure
    ok, _ = _client(uid=33, router=FakeRouter({"en": "thing", "pos": "noun"}))
    assert ok.post("/vocab/personal/preview", json={"word": "zxqwv"}).json()["enrichment"]["en"]


def test_lookup_audio_is_served_and_reused_by_the_added_card():
    tts = FakePiper()
    client, storage = _client(uid=34, router=FakeRouter({"en": "parcel", "pos": "noun"}), tts=tts)
    enr = client.post("/vocab/personal/preview", json={"word": "colis"}).json()["enrichment"]
    assert client.get(enr["audio_url"]).content.startswith(b"RIFFpiper-colis")

    card = client.post("/vocab/personal", json={"fr": enr["fr"], "en": enr["en"]}).json()["card"]
    audio = client.get(card["audio_url"])
    # the card plays the lookup's clip immediately — no second clip is stored
    assert audio.content.startswith(b"RIFFpiper-colis") and list(storage.objects) == [
        "vocablookup/colis.wav"
    ]


def test_preview_of_a_course_word_skips_the_llm():
    from app.content.tables import ContentVocab

    async def seed():
        async with _Session() as s:
            data = {
                "fr": "la boulangerie",
                "en": "bakery",
                "gender": "f",
                "audio": "a1/b.mp3",
                "ipa": "la bulɑ̃ʒʁi",
            }
            s.add(ContentVocab(id="boulangerie", level="a1", data=data))
            await s.commit()

    _run(seed())
    router = FakeRouter({"en": "x"})
    client, _ = _client(uid=35, router=router)
    r = client.post("/vocab/personal/preview", json={"word": "Boulangerie"}).json()
    assert r["in_course"] == "a1" and r["enrichment"]["en"] == "bakery"
    assert r["enrichment"]["audio_url"] == "/content/audio/a1/b.mp3"
    assert r["enrichment"]["ipa"] == "la bulɑ̃ʒʁi"  # the bank's checked IPA (QA 874)
    assert router.calls == []


def test_course_word_preview_matches_typed_variants_and_has_audio():
    """QA 1020/1021/1022: curly apostrophe + accent-less ligature still hit the course
    word, and a card with a blank `audio` still gets the conventional clip key."""
    from app.content.tables import ContentVocab

    async def seed():
        async with _Session() as s:
            for id_, fr in (("coeur", "cœur"), ("eau", "eau")):
                s.add(ContentVocab(id=id_, level="a1", data={"id": id_, "fr": fr, "audio": ""}))
            await s.commit()

    _run(seed())
    router = FakeRouter({"en": "x"})
    client, _ = _client(uid=36, router=router)
    for word, fr in (("coeur", "cœur"), ("L\u2019eau", "eau")):
        r = client.post("/vocab/personal/preview", json={"word": word}).json()
        assert r["in_course"] == "a1" and r["enrichment"]["fr"] == fr
    assert r["enrichment"]["audio_url"] == "/content/audio/a1/audio/eau.mp3"
    assert router.calls == []


def test_word_voice_prefers_siwis_and_falls_back_when_missing(tmp_path):
    from app.config.settings import Settings

    siwis = tmp_path / "siwis.onnx"
    s = Settings(piper_voice="upmc.onnx", piper_word_voice=str(siwis))
    assert s.word_voice == "upmc.onnx"  # not installed (e.g. local dev) -> sentence voice
    siwis.write_bytes(b"onnx")
    assert s.word_voice == str(siwis)


def test_piper_reads_ipa_from_debug_log(monkeypatch):
    import subprocess

    from app.ai.adapters.piper_adapter import PiperAdapter

    def fake_run(cmd, **kw):
        assert "--debug" in cmd
        log = "[piper] [debug] Converting 5 phoneme(s) to ids: pakˈɛ\n".encode()
        return subprocess.CompletedProcess(cmd, 0, stdout=b"RIFF", stderr=log)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert PiperAdapter(voice_model="v.onnx").synthesize_ipa(text="paquet") == (b"RIFF", "pakˈɛ")


# --- QA 060: Piper pronunciation correctness ----------------------------------


class RecordingPiper(FakeTTS):
    """Piper stand-in that records the text it voiced and reports IPA derived from it."""

    def __init__(self, ipa="ɛlɛv"):
        super().__init__()
        self.voiced: list[str] = []
        self.ipa = ipa

    def synthesize_ipa(self, *, text, voice=""):
        self.voiced.append(text)
        return b"RIFFpiper-" + text.encode(), "ˈ" + self.ipa


def _lookup_row(slug, **cols):
    async def go():
        async with _Session() as s:
            row = await s.get(VocabLookup, slug)
            for k, v in cols.items():
                setattr(row, k, v)
            await s.commit()
            return row.ipa

    return _run(go())


def test_accentless_input_is_stored_and_voiced_as_the_headword():
    """QA 891 (+892): "cacahuetes" is voiced and stored as the accented headword."""
    router = FakeRouter({"fr": "cacahuètes", "en": "peanuts", "pos": "noun", "gender": "f"})
    tts = RecordingPiper()
    client, _ = _client(uid=60, router=router, tts=tts)
    enr = client.post("/vocab/personal/preview", json={"word": "cacahuetes"}).json()["enrichment"]
    assert enr["fr"] == "cacahuètes" and tts.voiced == ["cacahuètes"]
    assert enr["ipa"] == "kakawɛt"  # override on the headword, never English-shaped IPA


def test_headword_from_the_model_is_only_accepted_for_the_same_word():
    def preview(typed, proposed, uid):
        router = FakeRouter({"fr": proposed, "en": "x", "pos": "noun"})
        client, _ = _client(uid=uid, router=router, tts=RecordingPiper())
        return client.post("/vocab/personal/preview", json={"word": typed}).json()["enrichment"]

    assert preview("zorgle", "zörgle", 61)["fr"] == "zörgle"  # accents added: same word
    assert preview("blimpo", "chat", 61)["fr"] == "blimpo"  # a different word: ignored
    assert preview("très", "tres", 61)["fr"] == "très"  # never drops a typed accent


def test_accented_input_replaces_an_accentless_cached_row_once():
    """QA 890: typing "éléphant" must not return the cached "elephant"; and a row that
    already has the accents (or a model that adds none) never loops."""
    tts = RecordingPiper()
    plain, _ = _client(uid=62, router=FakeRouter({"en": "elephant", "pos": "noun"}), tts=tts)
    assert (
        plain.post("/vocab/personal/preview", json={"word": "elephant"}).json()["enrichment"]["fr"]
        == "elephant"
    )
    router = FakeRouter({"en": "elephant", "pos": "noun"})  # model adds no headword
    client, storage = _client(uid=62, router=router, tts=tts)
    for _ in range(2):
        enr = client.post("/vocab/personal/preview", json={"word": "éléphant"}).json()["enrichment"]
        assert enr["fr"] == "éléphant"
    assert router.calls == ["vocab_enrich"] and tts.voiced[-1] == "éléphant"  # one re-voice
    # accentless input is served the accented row
    again = client.post("/vocab/personal/preview", json={"word": "elephant"}).json()["enrichment"]
    assert again["fr"] == "éléphant" and router.calls == ["vocab_enrich"]


def test_ligature_words_do_not_share_a_cache_row():
    """QA 871: "il" is the pronoun, not "œil"."""
    tts = RecordingPiper()
    client, _ = _client(uid=63, router=FakeRouter({"en": "eye", "pos": "noun"}), tts=tts)
    eye = client.post("/vocab/personal/preview", json={"word": "œil"}).json()["enrichment"]
    assert eye["audio_url"].endswith("/oeil")
    pron, _ = _client(uid=63, router=FakeRouter({"en": "he", "pos": "pronoun"}), tts=tts)
    il = pron.post("/vocab/personal/preview", json={"word": "il"}).json()["enrichment"]
    assert il["fr"] == "il" and il["en"] == "he"


def test_cached_clip_play_heals_only_an_empty_ipa():
    """QA 869/880: a clip with an empty IPA is filled on play; a filled IPA (stale ones
    are the backfill's job) costs no extra Piper run per play."""
    tts = RecordingPiper(ipa="ɔʁibl")
    client, _ = _client(uid=64, router=FakeRouter({"en": "horrible", "pos": "adjective"}), tts=tts)
    enr = client.post("/vocab/personal/preview", json={"word": "horrible"}).json()["enrichment"]
    _lookup_row("horrible", ipa="")
    assert client.get(enr["audio_url"]).status_code == 200
    assert _lookup_row("horrible") == "ɔʁibl"
    n = len(tts.voiced)
    assert client.get(enr["audio_url"]).status_code == 200
    assert len(tts.voiced) == n


def test_empty_ipa_with_a_clip_is_filled_on_next_preview():
    """QA 881: a cold first run left ipa="" next to a clip; the next lookup fills it."""
    tts = RecordingPiper(ipa="ɔʁibl")
    client, _ = _client(uid=65, router=FakeRouter({"en": "awful", "pos": "adjective"}), tts=tts)
    client.post("/vocab/personal/preview", json={"word": "affreux"})
    _lookup_row("affreux", ipa="")
    again = client.post("/vocab/personal/preview", json={"word": "affreux"}).json()["enrichment"]
    assert again["ipa"] == "ɔʁibl"
    n = len(tts.voiced)
    client.post("/vocab/personal/preview", json={"word": "affreux"})
    assert len(tts.voiced) == n  # healed once; a filled IPA is not re-derived on preview


def test_add_card_ignores_client_ipa_and_takes_the_lookups():
    """QA 870."""
    tts = RecordingPiper(ipa="pakɛ")
    client, _ = _client(uid=66, router=FakeRouter({"en": "packet", "pos": "noun"}), tts=tts)
    client.post("/vocab/personal/preview", json={"word": "paquet"})
    body = {"fr": "paquet", "en": "packet", "ipa": "WRONG"}
    assert client.post("/vocab/personal", json=body).json()["card"]["ipa"] == "pakɛ"
    other, _ = _client(uid=67, tts=tts)
    body = {"fr": "inconnu", "en": "unknown", "ipa": "WRONG"}
    assert other.post("/vocab/personal", json=body).json()["card"]["ipa"] == ""


def test_pipe_separated_meanings_are_shown_as_a_list():
    """QA 884."""
    client, _ = _client(uid=68, router=FakeRouter({"en": "packet|package", "pos": "noun"}))
    enr = client.post("/vocab/personal/preview", json={"word": "colisage"}).json()["enrichment"]
    assert enr["en"] == "packet, package"
