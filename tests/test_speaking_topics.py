"""Speaking topic bank: authored YAML -> sync -> list API -> examiner framing."""

import asyncio
import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.speech.tables  # noqa: F401  (register tables on Base metadata)
import app.usage.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Transcript
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.db.session import get_session
from app.main import create_app
from app.speech.topics import SpeakingTopic, framing, load_topics, sync_topics
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/topics.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


# --- loader + framing (no DB) -------------------------------------------------


def _write_topic(root: Path, level: str, name: str, doc: dict) -> None:
    d = root / level / "speaking"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


def test_load_topics_validates_and_keys_by_id():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_topic(
            root,
            "b1",
            "avion",
            {
                "id": "t-avion",
                "level": "b1",
                "section": "B",
                "title": "Avion",
                "prompt": "Faut-il limiter l'avion ?",
                "points": ["environnement"],
            },
        )
        topics = load_topics(root, "b1")
        assert set(topics) == {"t-avion"}
        assert topics["t-avion"].section == "B"
    # absent section -> empty, not an error
    with tempfile.TemporaryDirectory() as td:
        assert load_topics(Path(td), "a1") == {}


def test_framing_differs_by_section_and_includes_prompt_and_points():
    a = framing(
        SpeakingTopic(
            id="x",
            level="a1",
            section="A",
            title="T",
            prompt="Réserver une table",
            points=["le jour"],
        )
    )
    b = framing(
        SpeakingTopic(
            id="y",
            level="b1",
            section="B",
            title="T",
            prompt="Faut-il limiter l'avion ?",
            points=["coût"],
        )
    )
    assert "Section A" in a and "Réserver une table" in a and "le jour" in a
    assert "Section B" in b and "l'avion" in b and "coût" in b
    assert a != b


# --- sync + HTTP --------------------------------------------------------------


class _FakeSTT:
    name = "fake-stt"

    def transcribe(self, *, audio, lang="fr"):
        return Transcript(text="Bonjour, je voudrais réserver.", provider=self.name)


class _CapturingRouter:
    def __init__(self):
        self.calls = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append({"profile": profile, "system": system})
        return LLMResult(
            text="Bien sûr, pour quel jour ?",
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=10, output_tokens=5),
        )


class _FakeStorage:
    def __init__(self):
        self.objects = {}

    def put(self, key, data, content_type="application/octet-stream"):
        self.objects[key] = data
        return f"mem://{key}"

    def get(self, key):
        return self.objects[key]


def _client(router):
    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = 42

    app = create_app()
    app.state.stt = _FakeSTT()
    app.state.tts = None
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router
    app.dependency_overrides[get_storage] = lambda: _FakeStorage()
    return TestClient(app)


async def _seed():
    async with _Session() as s:
        await sync_topics(
            s,
            _seed_root(),
            "b1",
        )


def _seed_root() -> Path:
    root = Path(tempfile.mkdtemp())
    _write_topic(
        root,
        "b1",
        "avion",
        {
            "id": "t-avion",
            "level": "b1",
            "section": "B",
            "title": "Les voyages en avion",
            "prompt": "Faut-il limiter l'avion ?",
            "points": ["environnement", "coût"],
        },
    )
    _write_topic(
        root,
        "b1",
        "info",
        {
            "id": "t-info",
            "level": "b1",
            "section": "A",
            "title": "Renseignements",
            "prompt": "Obtenez des informations.",
            "points": [],
        },
    )
    return root


def test_sync_and_list_topics_endpoint_with_section_filter():
    _run(_seed())
    client = _client(_CapturingRouter())

    body = client.get("/speech/topics?level=b1").json()
    assert {t["id"] for t in body["topics"]} == {"t-avion", "t-info"}

    only_b = client.get("/speech/topics?level=b1&section=B").json()["topics"]
    assert [t["id"] for t in only_b] == ["t-avion"]
    assert only_b[0]["points"] == ["environnement", "coût"]

    assert client.get("/speech/topics?level=zz").json()["topics"] == []


def test_turn_with_topic_id_frames_system_prompt():
    _run(_seed())
    router = _CapturingRouter()
    client = _client(router)
    r = client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"rawaudio", "audio/wav")},
        data={"mode": "examiner", "topic_id": "t-avion"},
    )
    assert r.status_code == 200
    system = router.calls[0]["system"]
    assert "Faut-il limiter l'avion" in system and "Section B" in system


def test_turn_without_topic_has_no_framing():
    _run(_seed())
    router = _CapturingRouter()
    client = _client(router)
    client.post(
        "/speech/turn", files={"audio": ("a.wav", b"x", "audio/wav")}, data={"mode": "examiner"}
    )
    assert "Today's task" not in router.calls[0]["system"]


def test_unknown_topic_id_is_ignored_not_an_error():
    _run(_seed())
    router = _CapturingRouter()
    client = _client(router)
    r = client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "topic_id": "does-not-exist"},
    )
    assert r.status_code == 200
    assert "Today's task" not in router.calls[0]["system"]
