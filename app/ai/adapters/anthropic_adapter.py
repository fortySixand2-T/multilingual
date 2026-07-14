"""Anthropic via LiteLLM. A thin alias over the generic LiteLLMAdapter, kept as a
named type so the registry (and tests) can wire it explicitly. Vendor lib confined
to this directory."""

from __future__ import annotations

from app.ai.adapters.litellm_adapter import LiteLLMAdapter


class AnthropicAdapter(LiteLLMAdapter):
    def __init__(self, *, api_key: str) -> None:
        super().__init__(name="anthropic", api_key=api_key)
