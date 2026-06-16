# Phase 0 — Acceptance Criteria status

Verified by tests in this scaffold; the rest are correct-by-construction and need a
live environment (Docker / Ollama / API key) to confirm.

| AC | What | Status |
|----|------|--------|
| 0.1 | `docker compose up`; `/health` returns version + profiles | READY — needs Docker to confirm (now also reports `cache` backend) |
| 0.2 | Anthropic adapter returns a real completion | READY — needs `ANTHROPIC_API_KEY` + `litellm` installed |
| 0.3 | Ollama adapter returns a completion from a local model | READY — needs Ollama running + `ollama pull llama3.1` |
| 0.4 | Router resolves profile via YAML; **swap by YAML only** | ✅ VERIFIED (`test_provider_swap`, `test_ai_router`) |
| 0.5 | Fallback chain on primary failure | ✅ VERIFIED (`test_ai_router`) |
| 0.6 | Every `LLMResult` carries normalized usage + cost + provider | DONE — cost numbers need one live call to confirm |
| 0.7 | Alembic migration creates `users`; up/down cycle | ✅ VERIFIED — `migrations/versions/0001_init.py`; `upgrade head` + `downgrade base` cycle passes on SQLite |
| 0.8 | `storage` works on local-FS and S3 (MinIO) | READY — both adapters written; MinIO in compose |
| 0.9 | Invite-code signup + JWT login | ✅ VERIFIED (`test_auth`) — `POST /auth/signup`, `POST /auth/login`, protected `GET /auth/me` |
| 0.10 | No vendor SDK import outside `app/ai/adapters/` | ✅ VERIFIED (`test_provider_swap`) |

## Application data cache (added)

In-process, TTL + LRU cache behind a `Cache` protocol (`app/cache/`), same
swappable-adapter pattern as `storage/` and `ai/` — backend is config-driven
(`CACHE_BACKEND`), with a Redis swap path for later (plan §4.1: no Redis at this
scale yet). Wired into `AIRouter`: profiles may opt in with `cache: true` in
`ai_routing.yaml` so identical requests are served from cache instead of
re-calling the provider (cost/latency win for stable, repeated prompts — plan
R7). Verified by `test_cache` and `test_router_cache`.

## Test status

All 17 tests pass on Python 3.12:
`test_ai_router`, `test_provider_swap`, `test_cache`, `test_router_cache`, `test_auth`.

## Remaining before Phase 1
- `0.8` — wire a `get_storage()` factory off settings (local vs S3) + a smoke test against MinIO.
- `0.1` — `docker compose up`, confirm `/health`.
- `0.2/0.3/0.6` — one live call each to confirm completions + cost accounting.

Then start Phase 1 (A1 learning core) per the master plan.
