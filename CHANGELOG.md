# Changelog

- [2026-07-27] Created: qa/fixtures/speech/hello-fr.webm — real Chrome MediaRecorder webm/opus blob captured through the Speaking screen (H1 fixture)
- [2026-07-27] Modified: tests/test_speech_integration.py — add webm/opus decode+transcribe test (H1)
- [2026-07-27] Modified: qa/fixtures/speech/README.md — mark hello-fr.webm done; document the capture method

- [2026-07-27] Created: qa/fixtures/speech/graded-{a1,a2,b1,b2}-fr.wav — graded French STT fixtures (llama3.1 text + Piper voice, 16kHz mono)
- [2026-07-27] Modified: qa/fixtures/speech/README.md — document graded llama3.1+Piper fixtures + observed whisper-small transcription

- [2026-07-27] Created: tests/test_speech_integration.py — real faster-whisper+piper adapter tests (gated behind RUN_SPEECH_INTEGRATION; runs on the self-host box)

- [2026-07-27] Modified: pyproject.toml, uv.lock — add faster-whisper (CPU int8 STT) dependency
- [2026-07-27] Modified: Dockerfile — install Piper binary + fr_FR-siwis-medium voice, libgomp1, bake whisper 'small' model into HF_HOME
- [2026-07-27] Modified: docker-compose.yml — enable speech stack (STT=faster-whisper, TTS=piper, WHISPER_MODEL=small, PIPER_VOICE) for self-host app
- [2026-07-27] Modified: .env.example — document speech stack now enabled via compose; whisper on CPU

- [2026-07-26] Modified: web/src/App.tsx — slim topbar nav from 12 pills to 4 (Learn/Review/Mock/Group); routes unchanged
- [2026-07-26] Modified: web/src/screens/Path.tsx — add home "Practice & tools" hub grid linking the 8 off-nav destinations
- [2026-07-26] Modified: web/src/styles.css — add .tool-grid/.tool-card styles; remove obsolete mobile nav horizontal-scroll hack

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
- [2026-07-24] Modified: web/src/api.ts — qa-465 fe: examFinish response type carries xp/streak
- [2026-07-24] Modified: web/src/screens/Exam.tsx — qa-465 fe: Mock results shows 🔥 streak / ⭐ xp pills
- [2026-07-25] Created: migrations/versions/0014_lesson_attempts.py — passed/waived/attempts on completions
- [2026-07-25] Modified: app/progress/models.py — LessonCompletion gains passed/waived/attempts
- [2026-07-25] Modified: app/progress/service.py — gating counts passed|waived; lesson_states helper
- [2026-07-25] Modified: app/progress/api.py — attempt counting + /lessons/{id}/waive escape hatch
- [2026-07-25] Modified: app/content/api.py — path exposes passed_lessons/waived_lessons
- [2026-07-25] Created: tests/test_lesson_waive.py — full escape-hatch flow
- [2026-07-25] Modified: web/src/api.ts — waiveLesson + attempts/can_waive/waived + path lesson sets
- [2026-07-25] Modified: web/src/screens/Lesson.tsx — "Continue anyway" on a stuck lesson
- [2026-07-25] Modified: web/src/screens/Path.tsx — mark passed (⭐) vs waived (review) lessons
- [2026-07-25] Modified: web/src/api.ts — qa-466: 401 on authed request clears token + fires tef:unauthorized
- [2026-07-25] Modified: web/src/auth.tsx — qa-466: AuthProvider drops to login on tef:unauthorized
- [2026-07-25] Created: web/src/api.test.ts — 401 interceptor tests
- [2026-07-25] Created: qa/issues/466-invalid-token-shows-broken-shell.md — filed + resolved
- [2026-07-25] Modified: .github/workflows/ci.yml — add clean-deploy job (docker build + entrypoint boot + smoke)
- [2026-07-25] Modified: web/src/styles.css — responsive nav: tabs become a horizontally scrollable strip on phones (<=640px)
- [2026-07-25] Created: qa/rounds/041-plan.md — QA round plan for the speech module (end-to-end with real STT/TTS/LLM)
- [2026-07-25] Created: qa/fixtures/speech/README.md — speech test fixtures spec for QA round 041
- [2026-07-26] Created: qa/fixtures/speech/*.wav,*.mp3,*.bin — locally-generated (macOS say) speech fixtures for round 041
- [2026-07-26] Modified: qa/fixtures/speech/README.md — document generated fixtures + what still needs recording
- [2026-07-26] Modified: qa/fixtures/speech/README.md — pre-write Tatoeba CC-BY attribution block + incoming-clip rows, afconvert transcode note
- [2026-07-26] Modified: web/src/screens/Path.tsx — fix qa-490: add visible "Practice & tools" h2 heading above the tool grid nav
- [2026-07-26] Modified: web/src/styles.css — fix qa-490: add .section-label style for small muted section headings
- [2026-07-26] Created: web/src/screens/Path.test.tsx — regression test for qa-490 (visible heading above tool grid)
