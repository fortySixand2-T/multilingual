"""Usage/cost helpers. Deliberately vendor-free: adapters compute provider
cost (they have the SDK) and hand plain numbers here."""

from __future__ import annotations

from app.ai.interfaces import Usage


def make_usage(*, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0) -> Usage:
    return Usage(
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        cost_usd=float(cost_usd or 0.0),
    )


def add(a: Usage, b: Usage) -> Usage:
    return Usage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        cost_usd=round(a.cost_usd + b.cost_usd, 6),
    )
