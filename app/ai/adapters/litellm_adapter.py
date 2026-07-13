"""Generic LiteLLM adapter: one wrapper for every provider LiteLLM speaks.

Any hosted model reachable through LiteLLM — Anthropic, OpenRouter (GLM, DeepSeek,
Qwen, ...), DeepSeek direct, or any OpenAI-compatible endpoint — goes through this
single adapter. The provider ``name`` doubles as the LiteLLM route prefix, so a
routing target like ``openrouter/z-ai/glm-4.6`` (registry name ``openrouter``,
model ``z-ai/glm-4.6``) is sent to LiteLLM as ``openrouter/z-ai/glm-4.6``.

Vendor lib (litellm) is confined to this directory, per the AI abstraction.
"""

from __future__ import annotations

import litellm

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg


class LiteLLMAdapter:
    def __init__(self, *, name: str, api_key: str, api_base: str | None = None) -> None:
        self.name = name
        self._api_key = api_key
        self._api_base = api_base

    def complete(
        self,
        *,
        system: str,
        messages: list[Msg],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResult:
        extra = {"api_base": self._api_base} if self._api_base else {}
        resp = litellm.completion(
            model=f"{self.name}/{model}",
            api_key=self._api_key,
            messages=[
                {"role": "system", "content": system},
                *[{"role": m.role, "content": m.content} for m in messages],
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )
        text = resp.choices[0].message.content or ""
        u = getattr(resp, "usage", None)
        try:
            cost = float(litellm.completion_cost(completion_response=resp) or 0.0)
        except Exception:
            cost = 0.0
        return LLMResult(
            text=text,
            provider=self.name,
            model=model,
            usage=make_usage(
                input_tokens=getattr(u, "prompt_tokens", 0),
                output_tokens=getattr(u, "completion_tokens", 0),
                cost_usd=cost,
            ),
        )
