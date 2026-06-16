import re
from pathlib import Path

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter, ProfileConfig


class FakeProvider:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def complete(self, *, system, messages, model, **kw):
        self.calls.append(model)
        return LLMResult(text=f"{self.name}:{model}", provider=self.name, model=model, usage=make_usage())


def _registry():
    reg = ProviderRegistry()
    reg.register(FakeProvider("anthropic"))
    reg.register(FakeProvider("ollama"))
    return reg


def test_swap_provider_via_config_only():
    reg = _registry()
    r1 = AIRouter(reg, {"p": ProfileConfig("llm", "anthropic/m1")})
    assert r1.run("p", system="s", messages=[Msg("user", "hi")]).provider == "anthropic"
    r2 = AIRouter(reg, {"p": ProfileConfig("llm", "ollama/m2")})
    assert r2.run("p", system="s", messages=[Msg("user", "hi")]).provider == "ollama"


VENDOR_IMPORT = re.compile(r"^\s*(?:import|from)\s+(litellm|anthropic|openai)\b", re.M)


def test_no_vendor_sdk_import_outside_adapters():
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders = []
    for py in app_root.rglob("*.py"):
        if "ai/adapters" in py.as_posix():
            continue
        if VENDOR_IMPORT.search(py.read_text(encoding="utf-8")):
            offenders.append(py.as_posix())
    assert not offenders, f"vendor SDK imported outside adapters: {offenders}"
