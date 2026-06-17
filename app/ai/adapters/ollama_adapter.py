"""Local Ollama via its native REST API (no LiteLLM).

Deliberately bypasses the router library to prove the LLMProvider abstraction
holds for a provider that does NOT go through LiteLLM - i.e. even the router is
swappable. Local inference => cost is always 0.
"""

from __future__ import annotations

import httpx

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg


class OllamaAdapter:
    name = "ollama"

    def __init__(self, *, base_url: str = "http://localhost:11434", timeout: float = 120.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def complete(
        self,
        *,
        system: str,
        messages: list[Msg],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResult:
        payload = {
            "model": model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                *[{"role": m.role, "content": m.content} for m in messages],
            ],
        }
        r = httpx.post(f"{self._base}/api/chat", json=payload, timeout=self._timeout)
        r.raise_for_status()
        data = r.json()
        text = (data.get("message") or {}).get("content", "")
        return LLMResult(
            text=text,
            provider=self.name,
            model=model,
            usage=make_usage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                cost_usd=0.0,
            ),
        )
