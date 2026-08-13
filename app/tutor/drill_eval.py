"""Offline pairwise model comparison for the drill tutor (a subjective profile).

Drills have no gold label, so the critic is the LLM judge (app.ai.judge): each
candidate generates a scaffolded drill for real lesson items (grammar point +
vocabulary pulled straight from content YAML — no DB), and a strong judge compares
them head-to-head. Emits the same cost-penalized weight leaderboard as the writing
eval, plus a suggested `drill_<level>` routing block. Nothing is auto-applied.

    ./start.sh drill-eval "ollama/llama3.1,openrouter/z-ai/glm-4.6" b2

Offline only — never touches live traffic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.ai.evaluation import suggested_routing
from app.ai.judge import PairwiseJudge, run_pairwise_eval
from app.ai.registry import build_default_registry
from app.ai.router import AIRouter
from app.tutor.orchestrator import Tutor


@dataclass(frozen=True)
class DrillItem:
    grammar_point: str
    vocab: list[str]


def load_drill_items(content_root: str | Path, level: str, *, limit: int = 8) -> list[DrillItem]:
    """Pull (grammar_point, vocab) from a level's lesson YAML — a realistic drill
    eval set with no DB. Skips lessons missing a grammar point."""
    lessons = sorted((Path(content_root) / level / "lessons").glob("*.yaml"))
    items: list[DrillItem] = []
    for f in lessons:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        gp = (data.get("grammar_point") or "").strip()
        if not gp:
            continue
        items.append(DrillItem(grammar_point=gp, vocab=list(data.get("new_vocab") or [])))
        if len(items) >= limit:
            break
    return items


def run_drill_eval(
    candidates: list[str],
    content_root: str | Path,
    level: str,
    *,
    lam: float = 0.15,
    limit: int = 8,
):
    from app.config.settings import get_settings

    registry = build_default_registry(get_settings())
    available = [c for c in candidates if registry_has(registry, c)]
    for c in candidates:
        if c not in available:
            print(f"  skipped (provider not configured): {c}")
    if len(available) < 2:
        raise SystemExit("need at least two configured candidates to compare")

    items = load_drill_items(content_root, level, limit=limit)
    if not items:
        raise SystemExit(f"no drillable lessons (with a grammar_point) for level '{level}'")

    tutor = Tutor(AIRouter(registry, {}), level=level)  # message builder only

    def _messages(item: DrillItem):
        return tutor.build_messages(grammar_point=item.grammar_point, vocab=item.vocab)

    def generate(target: str, item: DrillItem):
        provider_name, _, model = target.partition("/")
        system, messages = _messages(item)
        result = registry.get(provider_name).complete(system=system, messages=messages, model=model)
        return result.text, result

    def describe(item: DrillItem) -> str:
        _, messages = _messages(item)
        return messages[0].content

    print(f"  comparing {available} on {len(items)} drill items (judge = pairwise_judge) ...")
    _s = get_settings()
    judge = PairwiseJudge(
        AIRouter.from_yaml(registry, _s.ai_routing_path, ollama_model=_s.ollama_model)
    )
    return run_pairwise_eval(
        available, items, generate=generate, describe=describe, judge=judge, lam=lam
    )


def registry_has(registry, target: str) -> bool:
    provider_name, _, _ = target.partition("/")
    return provider_name in registry.names()


def _print_leaderboard(ranked, *, level: str, lam: float) -> None:
    print(f"\n  model{'':<28}winrate  cost$    adv     weight")
    print("  " + "-" * 60)
    for r in ranked:
        print(
            f"  {r.model:<32}{r.quality:>6.2f}  {r.cost_usd:>7.4f}  "
            f"{r.advantage:>+5.2f}  {r.weight:>6.2f}"
        )
    primary, fallback = suggested_routing(ranked)
    print(
        f"\n  suggested drill_{level} (lam={lam}, quality-first): "
        f"primary={primary}, fallback={fallback}"
    )
    print("  (a suggestion only — nothing was applied to ai_routing.yaml)")


if __name__ == "__main__":
    import sys

    _save = "--save" in sys.argv
    _args = [a for a in sys.argv[1:] if a != "--save"]
    if not _args:
        print(
            'usage: python -m app.tutor.drill_eval "<target1,target2,...>" [level] [lam] [limit] '
            "[--save]\n"
            '  e.g. python -m app.tutor.drill_eval "ollama/llama3.1,openrouter/z-ai/glm-4.6" b2'
        )
        raise SystemExit(1)
    _candidates = [c.strip() for c in _args[0].split(",") if c.strip()]
    _level = _args[1] if len(_args) > 1 else "a1"
    _lam = float(_args[2]) if len(_args) > 2 and _args[2] else 0.15
    _limit = int(_args[3]) if len(_args) > 3 and _args[3] else 8
    _ranked = run_drill_eval(_candidates, "content", _level, lam=_lam, limit=_limit)
    _print_leaderboard(_ranked, level=_level, lam=_lam)
    if _save and _ranked:
        from app.ai.policy import save_ranking
        from app.config.settings import get_settings

        _profile = f"drill_{_level}"
        path = get_settings().model_weights_path
        save_ranking(path, _profile, _ranked)
        print(f"  saved learned routing for '{_profile}' -> {path} (takes effect on restart)")
