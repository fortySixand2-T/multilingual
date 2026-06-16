# TEF Canada Prep Platform — Technical Plan & Build Roadmap

> Plan-mode document. Defines architecture, the AI-provider abstraction, hosting,
> migration strategy, technical risks, and a phased set of task-files (ACs +
> frozen file lists + stop conditions) for Claude Code sessions.

---

## 0. Context & Objective

- **Users:** small closed group of friends (~5), all starting at **zero French**.
- **Target:** CLB 7 ≈ CEFR B2 across all four TEF Canada skills (listening, reading, writing, speaking).
- **Horizon:** ~10–12 months of near-daily study. **Build for sustained use, not a sprint.**
- **Cost goal:** single-digit USD/month at this scale; never let any single component create runaway cost or vendor lock-in.

**Two product truths driving the architecture:**
1. The high-value, hard-to-replace parts are **writing feedback** and **speaking practice** — the two assessor-graded TEF sections. These are AI-powered.
2. Everything you *produce* is **standard French**; Canadian/Québec French only matters for **listening comprehension** (accent exposure). This is a content rule, not an architecture rule, but it constrains the audio pipeline (real accent recordings vs. synthetic TTS).

---

## 1. Architecture Principles (non-negotiables)

These exist specifically to satisfy "modular, open, easy to migrate and pivot."

| Principle | What it means in practice |
|---|---|
| **Modular monolith** | One deployable app, internally split into bounded modules with explicit interfaces. No microservices — operational overhead isn't justified at this scale, but any module can be extracted later without a rewrite. |
| **Provider-agnostic AI** | The app never imports a vendor SDK directly. It talks to internal capability interfaces (`LLM`, `STT`, `TTS`). Vendors live behind adapters. Swapping Anthropic↔OpenAI↔local is a config change. |
| **No lock-in / portable data** | Content lives as version-controlled files. DB access goes through an ORM + migrations. Object storage uses the S3 API. Everything is containerized. |
| **Config-driven, 12-factor** | Provider selection, keys, hosting target, model routing — all via env/config, not code. |
| **Per-task routing** | Cheap/local model for drills; stronger paid model for nuanced feedback. Routing is a config table, not hardcoded calls. |

**Golden rule:** *no third-party type ever leaks into domain logic.* Even a router library (LiteLLM, Vercel AI SDK) is wrapped behind our own interface, so the router itself stays swappable.

---

## 2. System Architecture

Bounded modules (each owns its data, exposes a narrow interface):

```
                          ┌─────────────────────────┐
                          │        API layer         │  (HTTP / auth / rate-limit)
                          └────────────┬─────────────┘
        ┌──────────────┬──────────────┼──────────────┬───────────────┐
        ▼              ▼              ▼              ▼               ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐
   │ content │   │   srs    │   │  tutor   │   │assessment │   │ progress │
   │(lessons,│   │ (FSRS    │   │(level-   │   │(writing/  │   │(streaks, │
   │ MCQ,    │   │ schedule)│   │ gated AI │   │ speaking  │   │ level,   │
   │ audio)  │   │          │   │ drills/  │   │ grading,  │   │ group    │
   │         │   │          │   │ chat)    │   │ mocks)    │   │ board)   │
   └─────────┘   └──────────┘   └────┬─────┘   └─────┬─────┘   └──────────┘
                                     │               │
                                     ▼               ▼
                          ┌──────────────────────────────────┐
                          │   ai/  (provider abstraction)     │
                          │   LLM · STT · TTS interfaces      │
                          │   + adapter registry + router     │
                          └──────────────────────────────────┘
                                     │
              ┌──────────────────────┼───────────────────────┐
              ▼                      ▼                        ▼
        Anthropic/OpenAI/      Whisper(local)/          Piper(local)/
        OpenRouter/Ollama      Deepgram/Groq            ElevenLabs/Azure
```

Shared infra: `users/auth`, `storage` (S3-compatible abstraction), `config`, `db` (ORM + migrations).

---

## 3. The AI Provider Abstraction Layer (the core)

Three capability families, each an interface with multiple adapters and a config-driven router.

### 3.1 Capability interfaces

```python
# ai/interfaces.py  — domain-owned, vendor-free

class LLMProvider(Protocol):
    def complete(self, *, system: str, messages: list[Msg],
                 model: str, temperature: float = 0.3,
                 max_tokens: int = 1024) -> LLMResult: ...
    def complete_structured(self, *, system: str, messages: list[Msg],
                            schema: dict, model: str) -> dict: ...   # JSON out

class STTProvider(Protocol):
    def transcribe(self, *, audio: bytes, lang: str = "fr") -> Transcript: ...

class TTSProvider(Protocol):
    def synthesize(self, *, text: str, voice: str, lang: str = "fr") -> bytes: ...
```

`LLMResult` carries `text`, `usage` (tokens), `cost_estimate`, `model`, `provider` — so cost/usage accounting is uniform regardless of vendor.

### 3.2 Adapters

- **LLM:** `AnthropicAdapter`, `OpenAIAdapter`, `OpenRouterAdapter`, `OllamaAdapter` (local).
- **STT:** `FasterWhisperAdapter` (local), `GroqWhisperAdapter`, `DeepgramAdapter`.
- **TTS:** `PiperAdapter` (local), `ElevenLabsAdapter`, `AzureTTSAdapter`.

**Build-vs-buy for the LLM layer:** use **LiteLLM** (Python) as the engine inside the adapters — it already normalizes 100+ providers, retries, and fallback chains — but keep it *behind* `LLMProvider` so even LiteLLM is replaceable. (TS-stack equivalent: Vercel AI SDK.)

### 3.3 Router (config-driven, per-task)

A capability request names a **task profile**, not a provider:

```yaml
# config/ai_routing.yaml
profiles:
  drill_a1:          { capability: llm, primary: "ollama/llama3.1",      fallback: "anthropic/claude-haiku-4-5" }
  grammar_explain:   { capability: llm, primary: "anthropic/claude-sonnet-4-6" }
  writing_feedback:  { capability: llm, primary: "anthropic/claude-opus-4-8", fallback: "openai/gpt-..." }
  examiner_roleplay: { capability: llm, primary: "anthropic/claude-sonnet-4-6" }
  transcribe:        { capability: stt, primary: "faster-whisper/large-v3" }
  tts_generic:       { capability: tts, primary: "piper/fr_FR" }
```

Domain code calls `ai.run("writing_feedback", ...)`. Swapping providers = edit YAML. Adding a vendor = add one adapter + one registry line. This is the pivot point that keeps you free.

### 3.4 Structured-output contract

Grading must be machine-parseable and stable. Define a strict JSON schema (per-criterion scores, CLB estimate, inline corrections) and use `complete_structured`. Anchor with few-shot examples in the system prompt so scores don't drift across providers. **Calibration is a separate concern** — see Risk R3.

---

## 4. Recommended Stack (with migration notes)

| Layer | Choice | Why | Swap path |
|---|---|---|---|
| Backend | **Python + FastAPI** | LiteLLM, faster-whisper, Piper are Python-first; you already use Python. | Interfaces are language-agnostic; could port to TS later. |
| Frontend | **React / Next.js** | You know React. | Talks to backend over plain HTTP/JSON — backend-independent. |
| DB | **SQLite → Postgres** via SQLAlchemy + Alembic | Zero-ops now; migrate by changing one URL later. | Never write SQLite-specific SQL; migrations from day 1. |
| Object storage | **S3 API** (MinIO local → R2/B2/S3) | Audio assets portable across hosts. | Same code, change endpoint/creds. |
| Container | **Docker + docker-compose** | You already run Docker; same image everywhere. | Identical artifact for self-host / VPS / PaaS. |
| Auth | Invite-code + JWT (or Auth.js free tier) | Closed group; keep trivial. | Standard JWT; swap IdP later. |

### 4.1 Python toolchain (LOCKED)

| Concern | Choice | Notes |
|---|---|---|
| Runtime | **Python 3.12** | Mature, full ML-lib support. Avoid bleeding-edge until libs catch up. |
| Env / deps | **uv** | Fast, reproducible lockfile; single tool for venv + install. |
| Web | **FastAPI + uvicorn** (async) | Async API layer is the default path. |
| Config / schemas | **Pydantic v2 + pydantic-settings** | Settings from env; structured-output schemas reuse the same models. |
| LLM engine | **LiteLLM** *inside* the adapters | Normalizes providers/fallbacks; stays behind `LLMProvider` (never imported in domain code). |
| ORM / migrations | **SQLAlchemy 2.x (async) + Alembic** | SQLite now, Postgres later via URL swap. |
| SRS | **py-fsrs** | Don't hand-roll FSRS; wrap the lib behind `srs/`. |
| STT (Phase 4) | **faster-whisper** (local) | Sync/CPU-GPU bound → run via `anyio.to_thread`, never block the event loop. |
| TTS (Phase 4) | **Piper** (local) | Cache output by `(text, voice)`; generate async. |
| Storage | **boto3 / aioboto3** (S3 API) | MinIO locally → R2/B2/S3 in prod. |
| Tests | **pytest + httpx** | Async test client; contract tests per adapter. |
| Lint / format | **ruff** | Also enforces AC0.10 (no vendor SDK import outside `app/ai/adapters/`) via a custom rule/grep test. |

**Concurrency rule:** API is async; **all blocking ML calls (Whisper, Piper) go through a threadpool**, not the event loop. No Celery/Redis at this scale — keep background work in-process (asyncio tasks); flag a job queue as a later pivot point only if speech volume demands it.

---

## 5. Hosting & Deployment

Because the app is one config-driven container, hosting is a deploy detail, not an architecture decision:

1. **Self-host on your machine + Tailscale** (recommended start): ~$0, no public exposure, friends connect over the tailnet. Local Whisper/Piper run on the same box.
2. **VPS** (e.g. Hetzner): always-on, same compose file.
3. **PaaS** (Fly.io / Railway): same image, push to deploy.

All three consume the same `docker-compose.yml` and `.env`. Switching is a redeploy.

---

## 6. Data & Content Portability

- **Content as files:** lessons, MCQ banks, rubrics, prompt templates live as Markdown/YAML/JSON in the repo, versioned and diffable, loaded into the DB by a sync step. Content is never trapped in the DB.
- **Audio assets:** in S3-compatible storage via the `storage` interface. TTS output is cached (deterministic by text+voice).
- **Migrations from day one:** schema evolves via Alembic; SRS state and progress survive upgrades.
- **Export:** a `progress export` command dumps each user's data to JSON (portability + backup).

---

## 7. Technical Risks & Mitigations

> "Consider all technical difficulties." These are the real ones, ranked by how much they can hurt.

| # | Risk | Why it bites | Mitigation |
|---|---|---|---|
| **R1** | **STT "auto-corrects" beginner French** | Whisper tends to transcribe what a fluent speaker *would* say, hiding the learner's actual errors → false positive feedback. | Use STT for *content/fluency* feedback only, not as ground truth for what they said. Set lower-correction decoding where possible; show learner the transcript to confirm. |
| **R2** | **Pronunciation/accent scoring is genuinely hard** | An LLM grading a transcript cannot judge accent or phonemes. | **Don't over-promise.** AI examiner judges content, range, coherence, fluency. For true phoneme scoring, treat a specialized pronunciation-assessment API as an optional later module — not core. |
| **R3** | **LLM grading drift / inconsistent CLB estimates** | Same answer → different scores across runs/providers. | Strict JSON schema + low temperature + few-shot anchored exemplars + a small **calibration set** of human-rated sample answers to validate the rubric prompt. Present scores as estimates. |
| **R4** | **Hallucinated grammar / wrong corrections** | Beginners can't catch subtly wrong explanations → they learn errors. | Pin a strong model for `grammar_explain`; have it cite a curated verified grammar reference; human spot-check the high-traffic lessons. |
| **R5** | **Content authoring volume** | A year of curriculum is a lot; AI-generated content has errors. | AI-assisted authoring + human review gate; reuse vetted open resources (mind licensing); version content so fixes propagate. |
| **R6** | **Authentic Québécois listening audio** | Synthetic TTS won't reproduce real Québec accent features the exam tests. | Use **real recordings** (e.g. Radio-Canada) for accent training — *check licensing/usage rights*; reserve TTS for generic standard-French content. |
| **R7** | **Cost runaway (speech + multi-provider)** | Speech loops and big models add up. | Per-user token/minute budgets in `tutor`/`assessment`; cache TTS; route drills to local models; fallback chains capped. |
| **R8** | **Provider API drift** | Vendor changes break calls. | The adapter layer absorbs it — that's its job. Pin versions; contract tests per adapter. |
| **R9** | **Speech-loop latency** | STT→LLM→TTS round-trip feels slow. | Stream where possible; do TTS async; keep examiner turns short; pre-generate fixed prompts. |
| **R10** | **Voice-data privacy** | Storing recordings of people's voices. | Store only what's needed, encrypted at rest; allow delete/export; default to discarding raw audio after transcription unless review is requested. |
| **R11** | **Motivation collapse (weeks 1–6)** | #1 reason self-study apps fail before any French sticks. | Group progress board, streaks, weekly group role-play; ship the motivation layer in Phase 1, not "later." |

---

## 8. Build Roadmap (phased task-files)

Track the build to the learning curve — finish each phase just before learners need it.

| Phase | Theme | Gated by |
|---|---|---|
| **0** | Foundation & Provider Abstraction | — (do first) |
| **1** | A1 Learning Core (SRS + content + level-gated drill tutor + group/progress) | Phase 0 |
| **2** | Comprehension modules (reading + listening MCQ, audio pipeline, Québec accents) | Phase 1 |
| **3** | Writing assessment (rubric grading + calibration) | Phase 1 |
| **4** | Speech loop (STT/TTS, speaking practice) — hardest | Phases 0,3 |
| **5** | Exam simulation & calibration (timed mocks, no-replay listening, CLB report) | Phases 2–4 |

Each phase is its own task-file. Commit after each AC. Split a file if it exceeds ~8 ACs.

---

## 9. PHASE 0 — Foundation & Provider Abstraction  *(task-file)*

### Objective
Stand up the modular monolith skeleton, the AI provider abstraction (LLM at minimum, with two working adapters to *prove* swappability), config/routing, DB + migrations, storage abstraction, auth shell, and Docker. No learning features yet — this is the backbone everything else plugs into.

### In scope
- Repo scaffold with module boundaries and dependency rules.
- `ai/` layer: `LLMProvider` interface, `AnthropicAdapter`, `OllamaAdapter`, registry, YAML-driven router with fallback, uniform usage/cost accounting.
- `STTProvider` + `TTSProvider` **interfaces only** (no adapters yet — stubs).
- Config system (env + `ai_routing.yaml`), `.env.example`.
- DB via SQLAlchemy + Alembic (SQLite); `storage` interface with local-FS + S3 adapters.
- Auth shell (invite-code + JWT), `users` module.
- `docker-compose.yml`, healthcheck, `start.sh` with subcommands (mirrors your options_analyzer setup).

### Frozen file list (only these may be created/edited this phase)
```
app/main.py
app/config/__init__.py
app/config/settings.py
app/config/ai_routing.yaml
app/ai/interfaces.py
app/ai/registry.py
app/ai/router.py
app/ai/adapters/anthropic_adapter.py
app/ai/adapters/ollama_adapter.py
app/ai/accounting.py
app/db/__init__.py
app/db/session.py
app/storage/interface.py
app/storage/local_fs.py
app/storage/s3.py
app/users/models.py
app/users/auth.py
app/api/__init__.py
app/api/health.py
alembic.ini
migrations/env.py
docker-compose.yml
Dockerfile
start.sh
.env.example
tests/test_ai_router.py
tests/test_provider_swap.py
```

### Acceptance criteria
- **AC0.1** `docker compose up` starts the app; `GET /health` returns 200 with version + active AI profiles.
- **AC0.2** `LLMProvider` interface defined; `AnthropicAdapter` returns a real completion given a key.
- **AC0.3** `OllamaAdapter` returns a completion from a local model — **proving the abstraction with a second, architecturally different provider.**
- **AC0.4** Router resolves a task profile (e.g. `grammar_explain`) to a provider via `ai_routing.yaml`; **changing only the YAML** switches provider with no code change (covered by `test_provider_swap.py`).
- **AC0.5** Fallback chain works: primary failure routes to fallback (simulated in test).
- **AC0.6** Every `LLMResult` carries normalized `usage` + `cost_estimate` + `provider`/`model`.
- **AC0.7** Alembic migration creates the `users` table on SQLite; one migration up/down cycle passes.
- **AC0.8** `storage` interface works against both local-FS and an S3 endpoint (MinIO in compose).
- **AC0.9** Invite-code signup + JWT login issue/verify works; protected route rejects missing/invalid token.
- **AC0.10** No vendor SDK import exists outside `app/ai/adapters/` (enforced by a lint/grep test).

### Stop conditions
- STOP if implementing any learning feature (content, SRS, tutor) — out of scope.
- STOP if a vendor type appears outside `app/ai/adapters/` — fix the boundary first.
- STOP and surface for decision if the chosen router lib can't express fallback per-profile.

---

## 10. PHASE 1 — A1 Learning Core  *(task-file)*

### Objective
Deliver a usable A1 study loop for absolute beginners: spaced-repetition vocab, structured lessons, a **level-gated** drill tutor (scaffolded, not open chat), and the group progress/motivation layer. This alone carries learners through ~months 1–3.

### In scope
- `content` module: lesson + MCQ + vocab schema, file-based authoring (`content/a1/*.yaml`) with a DB sync step.
- `srs` module: FSRS scheduling, review queue API.
- `tutor` module: **level-gated** prompt orchestration. A1 mode = scaffolded drills (target sentence → learner manipulates pieces, single grammar point, English support allowed). Calls `ai.run("drill_a1", ...)`.
- `progress` module: per-user level/streak, group board.
- Frontend: review screen, lesson screen, drill screen, group board.

### Frozen file list
```
app/content/models.py
app/content/loader.py
app/content/api.py
content/a1/lessons/*.yaml
content/a1/vocab/*.yaml
app/srs/fsrs.py
app/srs/api.py
app/tutor/prompts/a1_drill.md
app/tutor/orchestrator.py
app/tutor/api.py
app/progress/models.py
app/progress/api.py
migrations/<phase1>_*.py
web/src/screens/Review.tsx
web/src/screens/Lesson.tsx
web/src/screens/Drill.tsx
web/src/screens/GroupBoard.tsx
tests/test_srs.py
tests/test_tutor_levelgate.py
tests/test_content_sync.py
```

### Acceptance criteria
- **AC1.1** Authoring an A1 lesson as YAML and running the sync loads it into the DB; content never edited directly in DB.
- **AC1.2** FSRS schedules reviews; answering updates the next due date correctly (unit-tested against known FSRS vectors).
- **AC1.3** Drill tutor in A1 mode produces **scaffolded** output (gives the model sentence, asks for a small manipulation) — verified by `test_tutor_levelgate.py` asserting it does **not** demand free-form French.
- **AC1.4** Tutor routes through `drill_a1` profile; works with the local provider (cost ≈ 0).
- **AC1.5** Per-user daily token budget enforced; over-budget returns a graceful message.
- **AC1.6** Progress: streak increments on daily activity; group board shows each member's level/streak.
- **AC1.7** Full loop runs end-to-end in the browser over Tailscale on the self-host target.

### Stop conditions
- STOP if building reading/listening MCQ delivery, writing grading, or any speech feature — later phases.
- STOP if the tutor's A1 behavior degrades into open conversation — fix the level gate.
- STOP if content is being written directly to the DB instead of files.

---

## 11. PHASES 2–5 (task-file stubs)

**Phase 2 — Comprehension.** Reading + listening MCQ delivery; audio pipeline via `storage`; ingest real Québec-accent clips (licensing-checked) + TTS for generic content; **no-replay** practice mode toggle. *Key ACs:* timed MCQ sets, per-question explanations, accent-tagged audio library, replay-disable flag. *Stop:* no grading of free text here.

**Phase 3 — Writing assessment.** `assessment` module: TEF writing tasks (2 task types), strict-JSON rubric grading via `writing_feedback` profile, inline corrections, CLB estimate. *Key ACs:* schema-valid output, calibration set agreement within tolerance (R3), grammar references cited (R4). *Stop:* no speaking yet.

**Phase 4 — Speech loop.** First real `STTProvider`/`TTSProvider` adapters; speaking practice = record → transcribe → examiner role-play → TTS reply; level-gated (drills → conversation → examiner). *Key ACs:* round-trip works on self-host with local Whisper+Piper; transcript shown (R1); content-only feedback, pronunciation explicitly out of scope (R2); voice data discarded post-transcription by default (R10). *Stop:* don't claim pronunciation scoring.

**Phase 5 — Exam simulation.** Full timed four-section mock; no-replay listening; aggregate CLB report per skill; plateau-buster harder mock. *Key ACs:* timing matches exam (40q/40q comprehension, 2 writing tasks, 2 speaking tasks), per-skill CLB band output, score history. *Stop:* treat CLB output as estimate, not official.

---

## 12. Open Decisions (resolve before Phase 0)

1. ~~Full-stack language~~ **RESOLVED → Python.** Backend = Python 3.12 / FastAPI (see §4.1); frontend = React/Next talking over plain HTTP/JSON.
2. **Local model baseline:** which Ollama model for `drill_a1` — depends on your self-host box's RAM/GPU.
3. **TTS budget path:** Piper-only (free, decent) vs. paid TTS for examiner voice quality in Phase 4.
4. **Content sourcing:** how much AI-authored (with review) vs. licensed existing material — affects Phase 1–2 timeline and R5/R6.
