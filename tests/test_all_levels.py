"""Level-agnostic content validation — covers every level under content/ (a1, a2, …).

Adding a new level (a new `content/<level>/path.yaml`) is automatically validated here:
each level must load + cross-reference cleanly, exam section refs must resolve, and content
ids that are DB primary keys (vocab) must be globally unique across levels.
"""

from pathlib import Path

import pytest

from app.assessment.loader import load_tasks
from app.comprehension.loader import load_sets
from app.content.loader import load_content
from app.exam.loader import load_blueprints

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
LEVELS = sorted(p.parent.name for p in CONTENT_ROOT.glob("*/path.yaml"))


def test_at_least_a1_and_a2_present():
    assert {"a1", "a2"} <= set(LEVELS)


@pytest.mark.parametrize("level", LEVELS)
def test_level_loads_and_cross_references(level):
    bundle = load_content(CONTENT_ROOT, level)  # raises on bad vocab/lesson/path refs
    assert bundle.path.units and bundle.lessons and bundle.vocab

    sets = load_sets(CONTENT_ROOT, level)
    tasks = load_tasks(CONTENT_ROOT, level)
    blueprints = load_blueprints(CONTENT_ROOT, level)
    assert sets and tasks and blueprints

    # every listening set carries a script (so its audio is reproducible from text)
    for s in sets.values():
        if s.skill == "listening":
            assert s.script, f"{s.id}: listening set needs a script"

    # exam sections must reference content that actually exists at this level
    for bp in blueprints.values():
        for sec in bp.sections:
            if sec.comprehension_set_id:
                assert sec.comprehension_set_id in sets, f"{bp.id}: bad set ref"
            for tid in sec.writing_task_ids:
                assert tid in tasks, f"{bp.id}: bad writing ref {tid}"


def test_vocab_ids_globally_unique_across_levels():
    # ContentVocab.id is the table primary key (and the FSRS card key) — a collision
    # across levels would make sync fail and corrupt SRS state.
    seen: dict[str, str] = {}
    for level in LEVELS:
        for vid in load_content(CONTENT_ROOT, level).vocab:
            assert vid not in seen, f"vocab id {vid!r} in both {seen[vid]} and {level}"
            seen[vid] = level
