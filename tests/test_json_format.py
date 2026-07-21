"""Per-profile `format: json` flows from routing config through the router into the
provider call, and each adapter renders it in its own request shape."""

from types import SimpleNamespace

import httpx
import litellm

from app.ai.accounting import make_usage
from app.ai.adapters.litellm_adapter import LiteLLMAdapter
from app.ai.adapters.ollama_adapter import OllamaAdapter
from app.ai.interfaces import LLMResult, Msg
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter, ProfileConfig


class RecordingProvider:
    name = "ollama"

    def __init__(self):
        self.seen_format = "UNSET"

    def complete(self, *, system, messages, model, format=None, **kw):
        self.seen_format = format
        return LLMResult(text="{}", provider=self.name, model=model, usage=make_usage())


def test_router_passes_profile_format():
    reg = ProviderRegistry()
    prov = RecordingProvider()
    reg.register(prov)
    r = AIRouter(reg, {"w": ProfileConfig("llm", "ollama/llama3.1", format="json")})
    r.run("w", system="s", messages=[Msg("user", "x")])
    assert prov.seen_format == "json"


def test_router_defaults_format_none():
    reg = ProviderRegistry()
    prov = RecordingProvider()
    reg.register(prov)
    r = AIRouter(reg, {"d": ProfileConfig("llm", "ollama/llama3.1")})
    r.run("d", system="s", messages=[Msg("user", "x")])
    assert prov.seen_format is None


def test_from_yaml_parses_format(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text(
        "profiles:\n  w:\n    capability: llm\n    primary: ollama/llama3.1\n    format: json\n",
        encoding="utf-8",
    )
    r = AIRouter.from_yaml(ProviderRegistry(), str(p))
    assert r._profiles["w"].format == "json"


def test_ollama_adapter_sends_format(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": "{}"}, "prompt_eval_count": 1, "eval_count": 1},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    OllamaAdapter().complete(
        system="s", messages=[Msg("user", "x")], model="llama3.1", format="json"
    )
    assert captured["format"] == "json"
    # omitted when not requested
    captured.clear()
    OllamaAdapter().complete(system="s", messages=[Msg("user", "x")], model="llama3.1")
    assert "format" not in captured


def test_litellm_adapter_maps_format_to_response_format(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **_: 0.0)
    LiteLLMAdapter(name="openrouter", api_key="k").complete(
        system="s", messages=[Msg("user", "x")], model="m", format="json"
    )
    assert captured["response_format"] == {"type": "json_object"}
