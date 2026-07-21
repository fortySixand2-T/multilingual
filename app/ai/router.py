"""Config-driven router: task profile -> provider/model, with fallback chain.

Profiles may opt into **response caching** (`cache: true`): identical requests
to a cache-enabled profile are served from the application cache instead of
re-calling the provider. This is a cost/latency optimization for repeated,
stable prompts (e.g. fixed A1 drills, grammar explanations) — see plan R7. Cache
is keyed on the full request (profile, system, messages, model, params), so any
change in input is a cache miss. Leave `cache` off for anything that should vary
per call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.ai.errors import AllProvidersFailedError
from app.ai.interfaces import LLMResult, Msg, Usage


@dataclass(frozen=True)
class ProfileConfig:
    capability: str
    primary: str
    fallback: str | None = None
    cache: bool = False
    cache_ttl: int | None = None  # seconds; None -> cache backend default
    format: str | None = None  # "json" -> ask the provider for strict JSON output


class AIRouter:
    def __init__(
        self, registry, profiles: dict[str, ProfileConfig], cache=None, policy=None
    ) -> None:
        from app.ai.policy import StaticPolicy

        self._registry = registry
        self._profiles = profiles
        self._cache = cache
        # Policy orders a profile's targets. Default = static (primary, fallback).
        self._policy = policy or StaticPolicy()

    @classmethod
    def from_yaml(cls, registry, path: str, cache=None, policy=None) -> AIRouter:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        profiles = {name: ProfileConfig(**cfg) for name, cfg in (raw.get("profiles") or {}).items()}
        return cls(registry, profiles, cache=cache, policy=policy)

    def profiles(self) -> list[str]:
        return sorted(self._profiles)

    @staticmethod
    def _cache_key(profile_name: str, target: str, *, system, messages, temperature, max_tokens):
        payload = json.dumps(
            {
                "profile": profile_name,
                "target": target,
                "system": system,
                "messages": [[m.role, m.content] for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return "llm:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def run(
        self,
        profile_name: str,
        *,
        system: str,
        messages: list[Msg],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResult:
        if profile_name not in self._profiles:
            raise KeyError(f"unknown profile '{profile_name}'")
        prof = self._profiles[profile_name]
        use_cache = self._cache is not None and prof.cache
        static_targets = [prof.primary] + ([prof.fallback] if prof.fallback else [])
        targets = self._policy.order(profile_name, static_targets)
        last_err: Exception | None = None
        for target in targets:
            provider_name, _, model = target.partition("/")
            key = (
                self._cache_key(
                    profile_name,
                    target,
                    system=system,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if use_cache
                else None
            )
            if key is not None:
                hit = self._cache.get(key)
                if hit is not None:
                    return _result_from_cache(hit)
            try:
                provider = self._registry.get(provider_name)
                result = provider.complete(
                    system=system,
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    format=prof.format,
                )
            except Exception as e:  # noqa: BLE001 - intentional fallback boundary
                last_err = e
                continue
            if key is not None:
                self._cache.set(key, _result_to_cache(result), prof.cache_ttl)
            return result
        raise AllProvidersFailedError(profile_name, last_err) from last_err


def _result_to_cache(result: LLMResult) -> str:
    return json.dumps(
        {
            "text": result.text,
            "provider": result.provider,
            "model": result.model,
            "usage": {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "cost_usd": result.usage.cost_usd,
            },
        }
    )


def _result_from_cache(blob: str) -> LLMResult:
    data = json.loads(blob)
    u = data["usage"]
    # A served-from-cache hit incurs no new provider spend.
    return LLMResult(
        text=data["text"],
        provider=data["provider"],
        model=data["model"],
        usage=replace(
            Usage(
                input_tokens=u["input_tokens"],
                output_tokens=u["output_tokens"],
                cost_usd=u["cost_usd"],
            ),
            cost_usd=0.0,
        ),
    )
