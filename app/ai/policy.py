"""Routing policy: how a profile's candidate targets are ordered for the router.

The router asks a policy to order the profile's targets. `StaticPolicy` returns
them unchanged — the profile's `primary` then `fallback`, i.e. today's behavior
exactly (zero regression; it's the default). `BanditPolicy` reorders by weights
learned in an offline eval (app.ai.evaluation), persisted to a small JSON store;
a profile with no learned weights falls through to the static order, so enabling
the bandit never regresses an un-evaluated profile.

Persistence is a JSON file (config-file ethos, like ai_routing.yaml), not a DB
table — the router is synchronous and the store is tiny. An eval writes it via
`save_ranking`; the app loads it once at startup via `load_bandit_policy`.
"""

from __future__ import annotations

import json
from pathlib import Path


class StaticPolicy:
    """Profile's static order (primary, then fallback). The default."""

    def order(self, profile_name: str, static_targets: list[str]) -> list[str]:
        return static_targets


class BanditPolicy:
    """Order targets by learned weight; unknown profiles fall through to static."""

    def __init__(self, weights: dict[str, list[str]]) -> None:
        self._weights = weights  # profile -> targets, best-first

    def order(self, profile_name: str, static_targets: list[str]) -> list[str]:
        learned = self._weights.get(profile_name)
        if not learned:
            return static_targets
        # Learned order first, then any static target it didn't rank — the YAML
        # fallback stays reachable as a safety net for outages.
        ordered = list(learned)
        for t in static_targets:
            if t not in ordered:
                ordered.append(t)
        return ordered


def load_bandit_policy(path: str | Path) -> BanditPolicy | None:
    """Build a BanditPolicy from the JSON store, or None if it doesn't exist yet
    (the router then defaults to StaticPolicy — unchanged behavior)."""
    p = Path(path)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    weights = {prof: [row["target"] for row in rows] for prof, rows in data.items()}
    return BanditPolicy(weights)


def save_ranking(path: str | Path, profile_name: str, ranked) -> None:
    """Persist an eval's ranked order for one profile into the JSON store (merging
    with any other profiles already there). `ranked` is a list of RankedModel."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    data[profile_name] = [{"target": r.model, "weight": round(r.weight, 4)} for r in ranked]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
