"""Anthropic via LiteLLM. Vendor lib confined to this directory."""
from __future__ import annotations

import litellm

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg


class AnthropicAdapter:
    name = "anthropic"

    def __init__(self, *, api_key: str) -> None:
        self._api_key = api_key

    def complete(
        self,
        *,
        system: str,
        messages: list[Msg],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResult:
        resp = litellm.completion(
            model=f"anthropic/{model}",
            api_key=self._api_key,
            messages=[
                {"role": "system", "content": system},
                *[{"role": m.role, "content": m.content} for m in messages],
            ],
            temperature=temperature,
            max_tokens=max_tokens,
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
