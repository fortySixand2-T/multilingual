"""Runs scripts/check_content.py in CI, so the authoring checklist is enforced.

The checker is the single place the content rules live; this file exists only to
make them a build gate. A new level is picked up automatically.
"""

from __future__ import annotations

import pytest

from scripts.check_content import CONTENT_ROOT, check_global, check_level

LEVELS = sorted(p.parent.name for p in CONTENT_ROOT.glob("*/path.yaml"))


@pytest.mark.parametrize("level", LEVELS)
def test_level_content_is_well_formed(level):
    failures = check_level(level)
    assert not failures, "\n".join(["", *(f"  - {f}" for f in failures)])


def test_ids_that_are_database_keys_are_globally_unique():
    failures = check_global(LEVELS)
    assert not failures, "\n".join(["", *(f"  - {f}" for f in failures)])
