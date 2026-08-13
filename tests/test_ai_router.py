import pytest

from app.ai.accounting import make_usage
from app.ai.errors import AllProvidersFailedError
from app.ai.interfaces import LLMResult, Msg
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter, ProfileConfig


class FakeOK:
    def __init__(self, name):
        self.name = name

    def complete(self, *, system, messages, model, **kw):
        return LLMResult(text="ok", provider=self.name, model=model, usage=make_usage())


class FakeFail:
    def __init__(self, name):
        self.name = name

    def complete(self, *, system, messages, model, **kw):
        raise RuntimeError("boom")


def test_resolves_profile_to_provider():
    reg = ProviderRegistry()
    reg.register(FakeOK("anthropic"))
    r = AIRouter(reg, {"grammar": ProfileConfig("llm", "anthropic/claude-sonnet-4-6")})
    out = r.run("grammar", system="s", messages=[Msg("user", "x")])
    assert out.provider == "anthropic"
    assert out.model == "claude-sonnet-4-6"


def test_fallback_used_when_primary_fails():
    reg = ProviderRegistry()
    reg.register(FakeFail("ollama"))
    reg.register(FakeOK("anthropic"))
    r = AIRouter(
        reg,
        {"drill": ProfileConfig("llm", "ollama/llama3.1", fallback="anthropic/claude-haiku-4-5")},
    )
    out = r.run("drill", system="s", messages=[Msg("user", "x")])
    assert out.provider == "anthropic"


def test_unknown_profile_raises():
    r = AIRouter(ProviderRegistry(), {})
    with pytest.raises(KeyError):
        r.run("nope", system="s", messages=[])


def test_all_providers_failing_raises_typed_error():
    reg = ProviderRegistry()
    reg.register(FakeFail("ollama"))
    reg.register(FakeFail("anthropic"))
    r = AIRouter(
        reg,
        {"drill": ProfileConfig("llm", "ollama/llama3.1", fallback="anthropic/claude-haiku-4-5")},
    )
    with pytest.raises(AllProvidersFailedError) as ei:
        r.run("drill", system="s", messages=[Msg("user", "x")])
    assert ei.value.profile == "drill"
    assert isinstance(ei.value.last_error, RuntimeError)


def test_from_yaml(tmp_path):
    p = tmp_path / "routing.yaml"
    p.write_text(
        "profiles:\n  g:\n    capability: llm\n    primary: anthropic/claude-sonnet-4-6\n",
        encoding="utf-8",
    )
    reg = ProviderRegistry()
    reg.register(FakeOK("anthropic"))
    r = AIRouter.from_yaml(reg, str(p))
    assert "g" in r.profiles()
    assert r.run("g", system="s", messages=[Msg("user", "x")]).text == "ok"


def test_from_yaml_substitutes_ollama_model(tmp_path):
    # ${OLLAMA_MODEL} in the routing text is filled from the ollama_model arg — one
    # env var swaps the local model+quant without editing the file per profile.
    p = tmp_path / "routing.yaml"
    p.write_text(
        "profiles:\n  drill:\n    capability: llm\n    primary: ollama/${OLLAMA_MODEL}\n",
        encoding="utf-8",
    )
    reg = ProviderRegistry()
    reg.register(FakeOK("ollama"))
    r = AIRouter.from_yaml(reg, str(p), ollama_model="qwen2.5:14b-instruct-q3_K_M")
    out = r.run("drill", system="s", messages=[Msg("user", "x")])
    assert out.model == "qwen2.5:14b-instruct-q3_K_M"


def test_from_yaml_default_ollama_model_and_no_placeholder(tmp_path):
    # No placeholder -> file passes through untouched; default fills a bare ${OLLAMA_MODEL}.
    p = tmp_path / "routing.yaml"
    p.write_text(
        "profiles:\n"
        "  a:\n    capability: llm\n    primary: anthropic/claude-sonnet-4-6\n"
        "  b:\n    capability: llm\n    primary: ollama/${OLLAMA_MODEL}\n",
        encoding="utf-8",
    )
    reg = ProviderRegistry()
    reg.register(FakeOK("anthropic"))
    reg.register(FakeOK("ollama"))
    r = AIRouter.from_yaml(reg, str(p))
    assert r.run("a", system="s", messages=[Msg("user", "x")]).model == "claude-sonnet-4-6"
    assert r.run("b", system="s", messages=[Msg("user", "x")]).model == "llama3.1"
