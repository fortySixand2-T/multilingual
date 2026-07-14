"""Provider registry + default factory.

Adapter imports are LAZY (inside the factory) so this module stays importable
in unit tests without provider SDKs installed, and so vendor libs never enter
the import graph until a provider is actually constructed.
"""

from __future__ import annotations


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, object] = {}

    def register(self, provider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str):
        if name not in self._providers:
            raise KeyError(f"provider '{name}' not registered (have: {self.names()})")
        return self._providers[name]

    def names(self) -> list[str]:
        return sorted(self._providers)


def build_default_registry(settings) -> ProviderRegistry:
    from app.ai.adapters.anthropic_adapter import AnthropicAdapter
    from app.ai.adapters.litellm_adapter import LiteLLMAdapter
    from app.ai.adapters.ollama_adapter import OllamaAdapter

    reg = ProviderRegistry()
    if settings.anthropic_api_key:
        reg.register(AnthropicAdapter(api_key=settings.anthropic_api_key))
    # Cheaper hosted providers via LiteLLM. Registered only when a key is present;
    # a routing target for an unregistered provider fails over to its `fallback`.
    if settings.openrouter_api_key:
        reg.register(LiteLLMAdapter(name="openrouter", api_key=settings.openrouter_api_key))
    if settings.deepseek_api_key:
        reg.register(LiteLLMAdapter(name="deepseek", api_key=settings.deepseek_api_key))
    reg.register(OllamaAdapter(base_url=settings.ollama_base_url))
    return reg
