"""Load + validate file-based content into a `ContentBundle`.

This is the file-reading half of AC1.1: YAML on disk → validated domain objects.
The DB-sync step (upsert by id into content tables) plugs in on top of this and
lands with the Phase 1 content migration — `load_content()` is the input to it.

Beyond per-model validation (in `models.py`), this enforces *referential
integrity across files*: path lesson refs resolve, unlock prerequisites exist,
and every `new_vocab` id has a vocab entry. Authoring errors fail the load.
"""

from __future__ import annotations

from pathlib import Path as FsPath

import yaml

from app.content.models import ContentBundle, Lesson, Path, Vocab


class ContentError(Exception):
    """Raised when content fails to load or cross-file references don't resolve."""


def _read_yaml(path: FsPath):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_content(content_root: str | FsPath, level: str) -> ContentBundle:
    root = FsPath(content_root) / level
    if not root.is_dir():
        raise ContentError(f"content level dir not found: {root}")

    path_file = root / "path.yaml"
    if not path_file.is_file():
        raise ContentError(f"missing path.yaml in {root}")
    path = Path.model_validate(_read_yaml(path_file))

    lessons: dict[str, Lesson] = {}
    for f in sorted((root / "lessons").glob("*.yaml")):
        lesson = Lesson.model_validate(_read_yaml(f))
        if lesson.id in lessons:
            raise ContentError(f"duplicate lesson id {lesson.id!r} ({f.name})")
        lessons[lesson.id] = lesson

    vocab: dict[str, Vocab] = {}
    for f in sorted((root / "vocab").glob("*.yaml")):
        rows = _read_yaml(f) or []
        for row in rows:
            v = Vocab.model_validate(row)
            if v.id in vocab:
                raise ContentError(f"duplicate vocab id {v.id!r} ({f.name})")
            vocab[v.id] = v

    _check_references(path, lessons, vocab)
    return ContentBundle(path=path, lessons=lessons, vocab=vocab)


def _check_references(path: Path, lessons: dict[str, Lesson], vocab: dict[str, Vocab]) -> None:
    errors: list[str] = []
    unit_ids = {u.id for u in path.units}

    for unit in path.units:
        for lid in unit.lessons:
            if lid not in lessons:
                errors.append(f"unit {unit.id}: references missing lesson {lid!r}")
        for req in unit.unlock.requires:
            if req not in unit_ids and req not in lessons:
                errors.append(f"unit {unit.id}: unlock requires unknown id {req!r}")

    for lesson in lessons.values():
        for vid in lesson.new_vocab:
            if vid not in vocab:
                errors.append(f"lesson {lesson.id}: new_vocab references missing vocab {vid!r}")

    if errors:
        raise ContentError("content reference errors:\n  - " + "\n  - ".join(errors))
