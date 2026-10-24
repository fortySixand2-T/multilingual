"""Local Ollama via its native REST API (no LiteLLM).

Deliberately bypasses the router library to prove the LLMProvider abstraction
holds for a provider that does NOT go through LiteLLM - i.e. even the router is
swappable. Local inference => cost is always 0.
"""

from __future__ import annotations

import httpx

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg


def _chatml(messages: list[dict]) -> str:
    """Qwen's chat template (ChatML), rendered client-side, ending on an open assistant turn."""
    turns = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
    return turns + "<|im_start|>assistant\n"


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
        format: str | None = None,
    ) -> LLMResult:
        msgs = [
            {"role": "system", "content": system},
            *[{"role": m.role, "content": m.content} for m in messages],
        ]
        payload = {
            "model": model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if format:
            payload["format"] = format  # e.g. "json" -> Ollama constrains output to valid JSON
        # /api/chat re-tokenizes every suffix of the history to fit the context window,
        # ~0.25 s at 8 turns and ~0.8 s at 16 on the 1070. For ChatML models we render
        # the prompt ourselves and skip that. See bench/reports/speaking-history-2026-10-24.md.
        raw = model.startswith("qwen")
        if raw:
            payload |= {"prompt": _chatml(msgs), "raw": True}
        else:
            payload["messages"] = msgs
        endpoint = "generate" if raw else "chat"
        r = httpx.post(f"{self._base}/api/{endpoint}", json=payload, timeout=self._timeout)
        r.raise_for_status()
        data = r.json()
        text = data["response"] if raw else (data.get("message") or {}).get("content", "")
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
