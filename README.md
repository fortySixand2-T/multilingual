# TEF Platform — Phase 0 (Foundation & Provider Abstraction)

Modular-monolith scaffold for the TEF Canada prep platform. This phase ships the
backbone everything else plugs into: the **provider-agnostic AI layer**, config-driven
routing, app shell, persistence/storage/auth scaffolds, and Docker.

## Quick start (local, Ollama-first — no API key needed)

```bash
# 1. install deps
uv sync

# 2. start Ollama + MinIO + app
docker compose up -d
docker compose exec ollama ollama pull llama3.1   # pull a local model

# 3. (optional) enable Anthropic fallback
cp .env.example .env && echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 4. check it's alive
curl localhost:9000/health
```

`/health` returns the version, registered providers, and active routing profiles.

Run without Docker: `./start.sh serve` (needs Ollama reachable at `OLLAMA_BASE_URL`).

## The provider abstraction (the point of this phase)

Domain code never touches a vendor SDK. It calls a **task profile**:

```python
router.run("writing_feedback", system=..., messages=[Msg("user", "...")])
```

- **Swap a provider** → edit `app/config/ai_routing.yaml`. No code change. (Proven by `tests/test_provider_swap.py`.)
- **Add a provider** → drop an adapter in `app/ai/adapters/`, register it in `app/ai/registry.py`.
- **Fallback** → set `fallback:` on the profile; primary failure auto-routes. (Proven by `tests/test_ai_router.py`.)

Two adapters ship, intentionally different to prove the abstraction holds both ways:

| Adapter | Path | Mechanism |
|---|---|---|
| Anthropic | `app/ai/adapters/anthropic_adapter.py` | via **LiteLLM** (the router lib) |
| Ollama (local) | `app/ai/adapters/ollama_adapter.py` | **native REST**, no LiteLLM — so even the router is swappable |

**Boundary rule (enforced by test):** `litellm`/`anthropic`/`openai` may only be imported inside `app/ai/adapters/`.

## Layout

```
app/
  ai/            interfaces (LLM/STT/TTS) · registry · router · accounting
    adapters/    anthropic (LiteLLM) · ollama (native) — ONLY place vendor SDKs live
  config/        settings (pydantic) · ai_routing.yaml
  db/            async SQLAlchemy session
  storage/       ObjectStorage interface · local-fs · s3 adapters
  users/         User model · JWT helpers
  api/           health
  main.py        app factory (builds registry + router on startup)
migrations/      alembic
tests/           router + provider-swap + boundary
```

## Tests

```bash
./start.sh test     # or: uv run pytest -q
```

See `PHASE0_STATUS.md` for the per-acceptance-criterion status (what's verified vs. next-session).
