# Changelog

- [2026-07-22] Created: qa/issues/321-vocab-known-accepts-nonexistent-card-key.md — QA issue: POST /content/vocab/known accepts phantom card_key with no vocab table check
- [2026-07-22] Created: qa/issues/322-exam-section-time-limit-not-enforced-server-side.md — QA issue: exam blueprint time_limit_seconds per section is display-only, not enforced on submit

- [2026-07-22] Created: qa/issues/341-writing-feedback-overall-contradicts-clb-estimate.md — QA issue: writing feedback overall text says "prevent reaching CLB 7" even when clb_estimate is 8
- [2026-07-22] Created: qa/issues/342-readiness-mixes-clb-scores-across-cefr-levels.md — QA issue: readiness endpoint mixes CLB trends from B1 and B2 exams without level separation
- [2026-07-22] Created: qa/issues/464-match-pairs-no-prompt-no-instructions.md — QA issue: match_pairs exercise has no prompt field, beginner sees no instructions
- [2026-07-22] Created: qa/issues/465-exam-finish-response-missing-xp-streak.md — QA issue: exam finish response does not include xp/streak after awarding 25 XP

- [2026-07-21] Modified: app/ai/router.py, interfaces.py — per-profile `format` option passed to provider.complete
- [2026-07-21] Modified: app/ai/adapters/ollama_adapter.py — pass `format` (e.g. json) to Ollama; litellm_adapter.py — map format=json to response_format
- [2026-07-21] Created: app/config/ai_routing.ollama.yaml — fully self-hosted routing preset (all profiles on ollama/llama3.1; writing_feedback format:json)
- [2026-07-21] Created: tests/test_json_format.py — format flows config→router→adapters
- [2026-07-21] Modified: docker-compose.yml — OLLAMA_KEEP_ALIVE env-driven; .env.example — OLLAMA_KEEP_ALIVE + ollama-only AI_ROUTING_PATH

- [2026-07-20] Modified: docker-compose.yml — ollama image tag configurable via ${OLLAMA_IMAGE_TAG:-latest} (pin CUDA-12 build on driver <570)
- [2026-07-20] Modified: .env.example — document OLLAMA_IMAGE_TAG
- [2026-07-22] Modified: app/exam/api.py — qa-465: exam finish() returns live xp/streak
- [2026-07-22] Modified: app/content/api.py — qa-321: vocab/known validates card_key (404 on phantom)
- [2026-07-22] Modified: tests/test_exam.py — assert finish response carries xp/streak
- [2026-07-22] Modified: tests/test_progress.py — test vocab/known rejects phantom card_key
- [2026-07-22] Triaged: qa/issues/{321,322,341,342,360,464,465}.md — live-round verdicts (2 fixed, 2 rejected, 3 deferred)
- [2026-07-22] Modified: app/users/models.py — add Invite model (managed reusable signup tokens)
- [2026-07-22] Created: app/users/invites.py — token gen + redemption service (find_redeemable/create_invite)
- [2026-07-22] Created: migrations/versions/0013_invites.py — invites table
- [2026-07-22] Modified: app/api/auth.py — signup accepts managed invite tokens, consumes a use atomically
- [2026-07-22] Modified: app/config/settings.py — add PUBLIC_BASE_URL for building invite links
- [2026-07-22] Created: scripts/make_invite.py — CLI to mint/list/revoke invite links
- [2026-07-22] Modified: web/src/screens/Login.tsx — ?invite=<token> link prefills code + opens signup
- [2026-07-22] Modified: tests/test_auth.py — invite token redemption tests (reuse/cap/expiry/rollback)
- [2026-07-22] Modified: .env.example, docs/hosting.md — document invite links
