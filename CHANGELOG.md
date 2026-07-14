# Changelog

- [2026-07-13] Modified: docker-compose.yml — base stack now app + Ollama only; app on loopback 127.0.0.1:9000 (Tailscale/Caddy exposes it); Caddy moved to an override
- [2026-07-13] Created: docker-compose.gpu.yml — NVIDIA GPU passthrough override for Ollama
- [2026-07-13] Created: docker-compose.caddy.yml — optional Caddy override (public-domain HTTPS)
- [2026-07-13] Modified: docs/hosting.md — laptop (NVIDIA + Tailscale) as primary runbook; CPU/no-Ollama + public-domain alternatives
- [2026-07-13] Modified: Dockerfile — multi-stage build (Node builds SPA with VITE_API_BASE="" → Python runtime); fixes prod serving no UI
- [2026-07-13] Created: scripts/docker-entrypoint.sh — boot: migrate + sync all content (a1–b2), then serve (no reload)
- [2026-07-13] Modified: docker-compose.yml — production stack: app + Ollama + Caddy, local FS storage (dropped MinIO)
- [2026-07-13] Created: Caddyfile — reverse proxy + automatic HTTPS via SITE_ADDRESS
- [2026-07-13] Modified: start.sh — add sync-all + serve-prod
- [2026-07-13] Modified: .env.example — SITE_ADDRESS, JWT_SECRET/INVITE_CODES guidance
- [2026-07-13] Created: docs/hosting.md — single-VPS deploy runbook (verified: image builds, container self-boots to usable)
- [2026-07-13] Created: app/ai/policy.py — RoutingPolicy seam: StaticPolicy (default, zero regression) + BanditPolicy + JSON weight persistence (load/save)
- [2026-07-13] Created: tests/test_policy.py — policy ordering, persistence roundtrip, router-consults-policy
- [2026-07-13] Modified: app/ai/router.py — router consults a routing policy for target order (defaults to StaticPolicy)
- [2026-07-13] Modified: app/main.py, app/config/settings.py — load BanditPolicy from model_weights_path at startup (None -> static)
- [2026-07-13] Modified: app/assessment/model_eval.py, app/tutor/drill_eval.py — `--save` persists learned routing for the profile
- [2026-07-13] Modified: docs/model-eval.md — BanditPolicy now built; learned-routing section
- [2026-07-13] Created: app/ai/judge.py — pairwise LLM-judge critic (order-swapped for position bias) + generic round-robin pairwise-eval runner
- [2026-07-13] Created: app/ai/prompts/pairwise_judge.md — judge prompt (strict {"winner": A|B|tie})
- [2026-07-13] Created: app/tutor/drill_eval.py — pairwise model comparison for drills (items from lesson YAML, no DB)
- [2026-07-13] Created: tests/test_judge.py — win-rate aggregation, verdict parsing, bias handling, runner
- [2026-07-13] Modified: app/ai/evaluation.py — add pairwise_win_rates aggregation
- [2026-07-13] Modified: app/config/ai_routing.yaml — add pairwise_judge profile (strong model)
- [2026-07-13] Modified: start.sh — add `drill-eval` command
- [2026-07-13] Modified: docs/model-eval.md — pairwise judge now built; refreshed code map + follow-ups
- [2026-07-13] Created: app/ai/evaluation.py — actor-critic weighting math (advantages, cost-penalized exponential-weights rank, routing suggestion)
- [2026-07-13] Created: app/assessment/model_eval.py — offline shadow eval for writing_feedback (reuses calibration + grader as validity gate)
- [2026-07-13] Created: tests/test_model_eval.py — weighting-math unit tests
- [2026-07-13] Created: docs/model-eval.md — actor-critic model-comparison design + code map + follow-ups
- [2026-07-13] Modified: start.sh — add `eval "t1,t2" [level] [lam]` command
- [2026-07-13] Created: app/ai/adapters/litellm_adapter.py — generic LiteLLM adapter (name = route prefix) for any LiteLLM provider (OpenRouter/GLM, DeepSeek, OpenAI-compatible)
- [2026-07-13] Modified: app/ai/adapters/anthropic_adapter.py — now a thin subclass of LiteLLMAdapter (DRY)
- [2026-07-13] Modified: app/ai/registry.py — register openrouter/deepseek when keyed
- [2026-07-13] Modified: app/config/settings.py, .env.example — OPENROUTER_API_KEY / DEEPSEEK_API_KEY
- [2026-07-13] Modified: app/config/ai_routing.yaml — cost-tiered routing (cheap/local drills, strong model kept for graded writing) with safe fail-over
- [2026-07-13] Created: tests/test_litellm_adapter.py — model-string mapping, api_base, registry wiring

## Session summary — 2026-06-27 → 2026-07-12
- **Completed the B2 level** (Upper Intermediate): 10 units, 30 lessons, 180 vocab, 12 comprehension
  sets, 8 writing tasks, 4 mock exams — delivered as 5 QA'd slices (MVP + expansions 2/3/4), bringing
  the app to full **A1 → A2 → B1 → B2** coverage. Also deepened B1 (4 new themes + comprehension/writing/mocks + a harder challenge tier).
- **Four student-help features** (each a QA'd slice, PRs #31–#34): grammar reference index,
  per-skill CLB readiness dashboard, weak-spot / mistake review (+ `weak_spots` migration 0012),
  and extending the drill tutor from A1-only to **all levels** (A1–B2).
- **Single-port LAN hosting**: FastAPI serves the built SPA from `web/dist` (PR #24).
- **Cleared the QA backlog** across rounds 029–039: fixed 416, 419, 428 (first_time→first_pass),
  429/430/431, 442, 443, 445, 447, 448, 449, 450, 451, 452, 463. PRs #24–#36.

- [2026-07-09] Created: qa/rounds/039-plan.md — QA round 039 plan: hardening slice 449/450/452 + student-help regression sweep; 11 hypotheses, 0 validated, 1 deferred (463)
- [2026-07-09] Modified: qa/issues/463-comprehension-submit-response-missing-xp-streak.md — Critic block appended: deferred (backend omission confirmed but UI never reads xp/streak from this response; described stale-counter harm is not reproducible; fix is incomplete without co-ordinated frontend changes)
- [2026-07-09] Modified: qa/issues/463-comprehension-submit-response-missing-xp-streak.md — Triage block appended: validated (xp/streak discarded after record_activity call; returning-learner sees stale UI until next /progress/me fetch)
- [2026-07-06] Modified: qa/issues/451-api-docstring-stale-says-a1-drill-only.md — Critic block appended: rejected (inline comment at line 43-44 neutralises re-hardcoding risk; docstring is cosmetic, not a defect)
- [2026-07-06] Modified: qa/issues/452-levelgate-test-missing-a2-b2-http-coverage.md — Critic block appended: deferred (PM's "missing level field" risk is structurally impossible; gap is hygiene not urgent CI blind spot; severity downgraded from medium to low)
- [2026-07-06] Modified: qa/issues/451-api-docstring-stale-says-a1-drill-only.md — Triage block appended: validated (stale docstring is a real maintainability risk; implementation is multi-level but docstring still says A1-only)
- [2026-07-06] Modified: qa/issues/452-levelgate-test-missing-a2-b2-http-coverage.md — Triage block appended: validated (a2/b2 HTTP-level routing is unexercised in CI; a2/b2 content exists on disk and is loadable)
- [2026-07-05] Modified: web/src/screens/WeakSpots.tsx — fix wrong-pick highlight: add picked state, apply .option.wrong CSS class to user's incorrect selection (issue 448)
- [2026-07-05] Modified: qa/issues/450-weakspots-no-tests-for-unanswered-ordering-404.md — Triage block appended: deferred (behaviors work, test gaps are regression risk not current defect)
- [2026-07-05] Modified: qa/issues/449-weakspots-answer-resolves-but-no-filter-on-resolved.md — Triage block appended: deferred (real data mutation but only reachable via direct API abuse, no UI path)
- [2026-07-09] Created: qa/rounds/039-plan.md, qa/issues/463-comprehension-submit-response-missing-xp-streak.md — QA round 039 on the 449/450/452 hardening: clean (11 hypotheses sound, all 3 target fixes confirmed); 463 filed and deferred (full-stack, no user-visible harm)
- [2026-07-11] Modified: app/comprehension/api.py, tests/test_comprehension.py — fix 463: comprehension submit returns xp/streak (capture record_activity's prog + refresh, or read existing row), matching the lesson-result endpoint
- [2026-07-11] Modified: web/src/api.ts, web/src/screens/ComprehensionSet.tsx — surface live streak/XP on the comprehension result (🔥 streak / ⭐ xp XP + first-pass cue) instead of a hardcoded "+15 XP"
