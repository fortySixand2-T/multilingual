"""Actor-critic weighting math: advantages, cost-penalized ranking, suggestion."""

import math

from app.ai.evaluation import (
    ModelStats,
    advantages,
    rank,
    suggested_routing,
)


def test_advantages_are_baseline_subtracted():
    adv = advantages({"a": 0.9, "b": 0.6, "c": 0.3})
    assert math.isclose(sum(adv.values()), 0.0, abs_tol=1e-9)  # zero-mean by construction
    assert adv["a"] > 0 > adv["c"]


def test_weights_sum_to_one_and_favor_quality():
    stats = [
        ModelStats("strong", quality=0.9, cost_usd=1.0, plays=10),
        ModelStats("weak", quality=0.5, cost_usd=1.0, plays=10),
    ]
    ranked = rank(stats, lam=0.15)
    assert math.isclose(sum(r.weight for r in ranked), 1.0, abs_tol=1e-9)
    assert ranked[0].model == "strong"  # equal cost -> quality wins
    assert ranked[0].weight > ranked[1].weight


def test_cost_breaks_near_ties_quality_first():
    # Near-identical quality; small lam should tip the weight to the cheaper model.
    stats = [
        ModelStats("pricey", quality=0.80, cost_usd=10.0, plays=10),
        ModelStats("cheap", quality=0.78, cost_usd=0.5, plays=10),
    ]
    ranked = rank(stats, lam=0.15)
    assert ranked[0].model == "cheap"


def test_big_quality_gap_ignores_cost():
    # Cheap-but-bad must not win when quality is clearly worse (quality-first).
    stats = [
        ModelStats("pricey_good", quality=0.92, cost_usd=10.0, plays=10),
        ModelStats("cheap_bad", quality=0.55, cost_usd=0.2, plays=10),
    ]
    ranked = rank(stats, lam=0.15)
    assert ranked[0].model == "pricey_good"


def test_free_local_costs_normalize_to_zero_penalty():
    stats = [
        ModelStats("local", quality=0.7, cost_usd=0.0, plays=10),
        ModelStats("hosted", quality=0.7, cost_usd=5.0, plays=10),
    ]
    ranked = rank(stats, lam=0.5)
    assert ranked[0].model == "local"  # same quality, zero cost -> wins


def test_suggested_routing_picks_top_two():
    stats = [
        ModelStats("a", quality=0.9, cost_usd=1.0, plays=5),
        ModelStats("b", quality=0.7, cost_usd=1.0, plays=5),
        ModelStats("c", quality=0.5, cost_usd=1.0, plays=5),
    ]
    primary, fallback = suggested_routing(rank(stats))
    assert primary == "a"
    assert fallback == "b"


def test_empty_is_safe():
    assert advantages({}) == {}
    assert rank([]) == []
    assert suggested_routing([]) == ("", None)
