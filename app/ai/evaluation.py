"""Actor-critic model comparison: the pure weighting math.

Model selection is a discrete action set (which provider/model runs a profile), so
this is a bandit with a learned critic:

  actor      -> a candidate provider/model ("arm")
  critic     -> scores an actor's output => reward in [0, 1]
  advantage  -> reward minus the pool mean (the actor-critic baseline; makes the
                comparison relative and lowers variance)
  policy     -> cost-penalized exponential weights over cumulative advantage

`utility = advantage - lam * normalized_cost` is the whole knob: `lam` small =>
quality-first, cost only breaks near-ties (graded work stays on strong models);
`lam` large => aggressively prefer the cheap model unless it is clearly worse.

Pure functions only (unit-tested). The live runner that calls candidates + critic
needs an LLM and lives next to the task it evaluates (see app.assessment.model_eval).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelStats:
    """A candidate's measured performance over an eval set."""

    model: str  # full routing target, e.g. "openrouter/z-ai/glm-4.6"
    quality: float  # mean critic reward in [0, 1]
    cost_usd: float  # total provider spend over the eval set (0.0 for local)
    plays: int  # items evaluated


@dataclass(frozen=True)
class RankedModel:
    model: str
    quality: float
    cost_usd: float
    advantage: float
    utility: float
    weight: float  # policy weight in [0, 1]; the whole set sums to 1


def pairwise_win_rates(outcomes: list[tuple[str, str, str]]) -> dict[str, float]:
    """Per-model win rate in [0, 1] from pairwise judgements — the critic reward
    for subjective profiles that have no gold labels.

    Each outcome is ``(model_a, model_b, winner)`` where ``winner`` is ``model_a``,
    ``model_b``, or ``"tie"``. Win scores 1, tie 0.5, loss 0; a model's quality is
    the mean over every comparison it took part in. Models with no comparisons are
    absent from the result.
    """
    points: dict[str, float] = {}
    games: dict[str, int] = {}
    for a, b, winner in outcomes:
        for m in (a, b):
            games[m] = games.get(m, 0) + 1
            points.setdefault(m, 0.0)
        if winner == "tie":
            points[a] += 0.5
            points[b] += 0.5
        else:
            points[winner] += 1.0
    return {m: points[m] / games[m] for m in games}


def advantages(quality: dict[str, float]) -> dict[str, float]:
    """Reward minus the pool mean — the actor-critic baseline subtraction."""
    if not quality:
        return {}
    base = sum(quality.values()) / len(quality)
    return {m: q - base for m, q in quality.items()}


def _normalized_cost(cost: dict[str, float]) -> dict[str, float]:
    """Scale cost to [0, 1] by the most expensive actor (free/local -> 0)."""
    hi = max(cost.values(), default=0.0)
    if hi <= 0:
        return dict.fromkeys(cost, 0.0)
    return {m: c / hi for m, c in cost.items()}


def rank(stats: list[ModelStats], *, lam: float = 0.15, eta: float = 6.0) -> list[RankedModel]:
    """Cost-penalized exponential-weights ranking, best weight first.

    `lam` is cost sensitivity (small => quality-first). `eta` is the softmax
    temperature (higher => sharper preference for the top actor).
    """
    quality = {s.model: s.quality for s in stats}
    cost = {s.model: s.cost_usd for s in stats}
    adv = advantages(quality)
    ncost = _normalized_cost(cost)
    util = {m: adv[m] - lam * ncost[m] for m in quality}

    hi = max(util.values(), default=0.0)  # shift for numerical stability
    exps = {m: math.exp(eta * (u - hi)) for m, u in util.items()}
    z = sum(exps.values()) or 1.0
    weight = {m: e / z for m, e in exps.items()}

    ranked = [
        RankedModel(s.model, s.quality, s.cost_usd, adv[s.model], util[s.model], weight[s.model])
        for s in stats
    ]
    return sorted(ranked, key=lambda r: r.weight, reverse=True)


def suggested_routing(ranked: list[RankedModel]) -> tuple[str, str | None]:
    """Top actor as primary, runner-up as fallback (an ai_routing.yaml suggestion)."""
    if not ranked:
        return "", None
    primary = ranked[0].model
    fallback = ranked[1].model if len(ranked) > 1 else None
    return primary, fallback
