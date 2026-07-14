"""Generic LiteLLM adapter: model-string mapping, cost accounting, registry wiring.

litellm.completion is monkeypatched so these stay offline (no network / no key).
"""

from types import SimpleNamespace

import litellm

from app.ai.adapters.anthropic_adapter import AnthropicAdapter
from app.ai.adapters.litellm_adapter import LiteLLMAdapter
from app.ai.interfaces import Msg
from app.ai.registry import build_default_registry


def _fake_completion(monkeypatch, capture: dict):
    def fake(**kwargs):
        capture.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="bonjour"))],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
        )

    monkeypatch.setattr(litellm, "completion", fake)
    monkeypatch.setattr(litellm, "completion_cost", lambda **_: 0.0025)


def test_name_becomes_litellm_prefix(monkeypatch):
    cap: dict = {}
    _fake_completion(monkeypatch, cap)
    a = LiteLLMAdapter(name="openrouter", api_key="k")
    out = a.complete(system="s", messages=[Msg("user", "salut")], model="z-ai/glm-4.6")

    # registry name + model recombine into the LiteLLM route string.
    assert cap["model"] == "openrouter/z-ai/glm-4.6"
    assert cap["api_key"] == "k"
    assert "api_base" not in cap  # omitted unless configured
    assert out.provider == "openrouter"
    assert out.model == "z-ai/glm-4.6"
    assert out.text == "bonjour"
    assert out.usage.input_tokens == 11
    assert out.usage.output_tokens == 7
    assert out.usage.cost_usd == 0.0025


def test_api_base_passed_through_for_openai_compatible(monkeypatch):
    cap: dict = {}
    _fake_completion(monkeypatch, cap)
    a = LiteLLMAdapter(name="openai", api_key="k", api_base="http://vllm:8000/v1")
    a.complete(system="s", messages=[Msg("user", "x")], model="local-model")
    assert cap["api_base"] == "http://vllm:8000/v1"


def test_anthropic_adapter_is_litellm_with_anthropic_prefix(monkeypatch):
    cap: dict = {}
    _fake_completion(monkeypatch, cap)
    a = AnthropicAdapter(api_key="k")
    assert isinstance(a, LiteLLMAdapter)
    a.complete(system="s", messages=[Msg("user", "x")], model="claude-haiku-4-5")
    assert cap["model"] == "anthropic/claude-haiku-4-5"


def test_registry_registers_cheap_providers_only_when_keyed():
    base = SimpleNamespace(
        anthropic_api_key="",
        openrouter_api_key="",
        deepseek_api_key="",
        ollama_base_url="http://localhost:11434",
    )
    assert build_default_registry(base).names() == ["ollama"]

    keyed = SimpleNamespace(
        anthropic_api_key="a",
        openrouter_api_key="o",
        deepseek_api_key="d",
        ollama_base_url="http://localhost:11434",
    )
    assert build_default_registry(keyed).names() == [
        "anthropic",
        "deepseek",
        "ollama",
        "openrouter",
    ]
