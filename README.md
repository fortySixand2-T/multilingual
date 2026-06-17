# TEF Canada Prep Platform

A small, modular study app for a closed group of friends preparing for the TEF
Canada exam (target CLB 7 ≈ CEFR B2). Python/FastAPI backend + a Duolingo-style
React SPA. Built provider-agnostic so the AI vendors (and STT/TTS, storage, DB)
are config-swappable. Full design in `TEF_Platform_Technical_Plan.md`.

## What's in it

| Module (`app/…`) | What it does |
|---|---|
| `ai/` | Vendor-free `LLM`/`STT`/`TTS` interfaces, adapters (Anthropic via LiteLLM, Ollama, faster-whisper, Piper), YAML-driven router with fallback + typed failure (`AllProvidersFailedError` → 503). Vendor SDKs live **only** in `ai/adapters/`. |
| `content/` | A1 lesson path: units → lessons → exercises (mcq/word_bank/listen_type/match_pairs/translate), file-authored, synced to the DB, with derived unlock gating. |
| `srs/` | Spaced repetition via py-fsrs (wrapped); review queue. |
| `progress/` | Per-user streak/XP + lesson completions; group board. Shared `record_activity` is the one streak/XP write path. |
| `tutor/` | Level-gated A1 drill generation (scaffolded, never open chat) via the `drill_a1` profile. |
| `comprehension/` | Reading + listening MCQ with server-side grading, per-question explanations, timed + no-replay; audio served through the `storage` interface. |
| `assessment/` | TEF writing grading (strict-JSON rubric, inline corrections citing grammar refs, CLB estimate) + calibration harness. |
| `speech/` | Speaking loop: record → transcribe → examiner role-play → TTS reply. Content-only feedback (no pronunciation scoring); raw audio never stored. |
| `exam/` | Timed four-section mock composed of the above; aggregate per-skill CLB report + score history. |
| `usage/` `cache/` `storage/` `users/` | Shared: per-feature daily token budgets, app cache, object storage, auth. |

Everything metered runs on a per-user **daily token budget**; learner state is
keyed by string ids (not FKs into content), so content re-syncs never touch it.

## Run it

```bash
# backend (http://localhost:9000)
uv sync
./start.sh migrate
./start.sh content-sync a1        # also: comprehension-sync, writing-sync, exam-sync
./start.sh serve

# frontend (http://localhost:5173, proxies /api -> :9000)
cd web && npm install && npm run dev
```

Local-first: Ollama needs no key; set `ANTHROPIC_API_KEY` in `.env` to enable the
paid fallback. Speech is `disabled` by default — set `STT_BACKEND=faster-whisper`
/ `TTS_BACKEND=piper` on a self-host box. See `.env.example` and `web/README.md`.

## The AI abstraction

Domain code calls a **task profile**, never a vendor:

```python
router.run("writing_feedback", system=..., messages=[Msg("user", "...")])
```

- **Swap a provider** → edit `app/config/ai_routing.yaml` (no code change).
- **Add one** → drop an adapter in `app/ai/adapters/`, register it in `registry.py`.
- **Fallback** → set `fallback:` on the profile; a total outage degrades to a clean 503.

## Develop

```bash
./start.sh test          # pytest (also: lint, fmt)
./start.sh calibrate a1  # grade calibration samples vs expected CLB (needs a provider)
```

CI (`.github/workflows/ci.yml`) runs ruff lint + format check + pytest, and the
web type-check/build, on every push and PR. Schema changes go through Alembic
migrations (`migrations/versions/`).
