"""Routing policy: static passthrough, bandit ordering, persistence, and that the
router consults the policy (default StaticPolicy = unchanged behavior)."""

from app.ai.accounting import make_usage
from app.ai.evaluation import RankedModel
from app.ai.interfaces import LLMResult, Msg
from app.ai.policy import (
    BanditPolicy,
    StaticPolicy,
    load_bandit_policy,
    save_ranking,
)
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter, ProfileConfig


class Fake:
    def __init__(self, name):
        self.name = name

    def complete(self, *, system, messages, model, **kw):
        return LLMResult(text="ok", provider=self.name, model=model, usage=make_usage())


def test_static_policy_is_identity():
    assert StaticPolicy().order("p", ["a/1", "b/2"]) == ["a/1", "b/2"]


def test_bandit_reorders_known_profile_and_keeps_fallback_safety_net():
    pol = BanditPolicy({"drill_a1": ["ollama/llama3.1", "openrouter/z-ai/glm-4.6"]})
    # learned order wins; a static target not in the learned set is appended.
    out = pol.order("drill_a1", ["openrouter/z-ai/glm-4.6", "anthropic/claude-haiku-4-5"])
    assert out == [
        "ollama/llama3.1",
        "openrouter/z-ai/glm-4.6",
        "anthropic/claude-haiku-4-5",
    ]


def test_bandit_falls_through_for_unranked_profile():
    pol = BanditPolicy({"drill_a1": ["ollama/llama3.1"]})
    assert pol.order("writing_feedback", ["anthropic/opus", "glm"]) == ["anthropic/opus", "glm"]


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "weights.json"
    ranked = [
        RankedModel("ollama/llama3.1", 0.8, 0.0, 0.1, 0.1, 0.7),
        RankedModel("openrouter/z-ai/glm-4.6", 0.6, 0.3, -0.1, -0.15, 0.3),
    ]
    save_ranking(path, "drill_b2", ranked)
    pol = load_bandit_policy(path)
    assert pol is not None
    assert pol.order("drill_b2", ["x"]) == ["ollama/llama3.1", "openrouter/z-ai/glm-4.6", "x"]


def test_save_merges_multiple_profiles(tmp_path):
    path = tmp_path / "weights.json"
    save_ranking(path, "drill_a1", [RankedModel("m1", 0.9, 0.0, 0.0, 0.0, 1.0)])
    save_ranking(path, "writing_feedback", [RankedModel("m2", 0.9, 0.0, 0.0, 0.0, 1.0)])
    pol = load_bandit_policy(path)
    assert pol.order("drill_a1", []) == ["m1"]
    assert pol.order("writing_feedback", []) == ["m2"]


def test_load_missing_file_returns_none(tmp_path):
    assert load_bandit_policy(tmp_path / "nope.json") is None


def test_router_uses_policy_order():
    reg = ProviderRegistry()
    reg.register(Fake("ollama"))
    reg.register(Fake("anthropic"))
    profiles = {"p": ProfileConfig("llm", "anthropic/m1", fallback="ollama/m2")}
    # Bandit flips the order so ollama (normally fallback) is tried first.
    pol = BanditPolicy({"p": ["ollama/m2", "anthropic/m1"]})
    r = AIRouter(reg, profiles, policy=pol)
    assert r.run("p", system="s", messages=[Msg("user", "x")]).provider == "ollama"
    # Default policy keeps the static primary.
    r_static = AIRouter(reg, profiles)
    assert r_static.run("p", system="s", messages=[Msg("user", "x")]).provider == "anthropic"
