"""Content loader + schema validation (Phase 1 content slice)."""
from pathlib import Path as FsPath

import pytest
from pydantic import ValidationError

from app.content.loader import ContentError, load_content
from app.content.models import McqExercise, WordBankExercise

CONTENT_ROOT = FsPath(__file__).resolve().parents[1] / "content"


def test_loads_example_a1_content():
    bundle = load_content(CONTENT_ROOT, "a1")
    assert bundle.path.level == "a1"
    assert [u.id for u in bundle.path.units] == ["a1.u1", "a1.u2"]
    assert set(bundle.lessons) == {"greetings-01", "cafe-01"}
    assert {"bonjour", "salut", "bonsoir", "cafe", "eau"} <= set(bundle.vocab)

    # discriminated union parses each exercise to its concrete type
    types = [e.type for e in bundle.lessons["greetings-01"].exercises]
    assert types == ["mcq", "word_bank", "listen_type", "match_pairs"]


def test_unit_gating_is_declared_not_computed():
    bundle = load_content(CONTENT_ROOT, "a1")
    u1, u2 = bundle.path.units
    assert u1.unlock.type == "none"
    assert u2.unlock.type == "all_of" and u2.unlock.requires == ["a1.u1"]


def test_mcq_answer_must_be_in_options():
    with pytest.raises(ValidationError):
        McqExercise(id="x", type="mcq", prompt="?", options=["a", "b"], answer="c")


def test_word_bank_answer_must_come_from_tokens():
    with pytest.raises(ValidationError):
        WordBankExercise(id="x", type="word_bank", prompt="?", tokens=["a"], answer=["b"])


def test_missing_lesson_reference_is_an_error(tmp_path):
    (tmp_path / "a1" / "lessons").mkdir(parents=True)
    (tmp_path / "a1" / "vocab").mkdir()
    (tmp_path / "a1" / "path.yaml").write_text(
        "level: a1\ntitle: t\nunits:\n"
        "  - id: a1.u1\n    title: U\n    lessons: [does-not-exist]\n"
        "    unlock: { type: none }\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="missing lesson"):
        load_content(tmp_path, "a1")


def test_new_vocab_must_resolve(tmp_path):
    (tmp_path / "a1" / "lessons").mkdir(parents=True)
    (tmp_path / "a1" / "vocab").mkdir()
    (tmp_path / "a1" / "path.yaml").write_text(
        "level: a1\ntitle: t\nunits:\n"
        "  - id: a1.u1\n    title: U\n    lessons: [l1]\n    unlock: { type: none }\n",
        encoding="utf-8",
    )
    (tmp_path / "a1" / "lessons" / "l1.yaml").write_text(
        "id: l1\ntitle: L\nnew_vocab: [ghost]\nexercises:\n"
        "  - id: l1.e1\n    type: listen_type\n    audio_ref: x.mp3\n    answer: a\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="missing vocab"):
        load_content(tmp_path, "a1")
