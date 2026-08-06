# Changelog

- [2026-08-05] Fixed: app/srs/api.py — QA round 051 #621: GET /srs/hardest `limit` is now `Query(30, ge=0)` (422 on negative, matching Field(ge=...) convention) instead of silently truncating the tail of the ranked deck via `ranked[:limit]`; #622: GET /srs/queue's `difficulty` is now rounded to 1dp (None-safe) to match GET /srs/hardest; tests/test_personal_vocab.py — regression tests for #621/#622
- [2026-08-05] Fixed: web/src/screens/Review.tsx — QA round 051 #640: tough-card badge emoji/label split into separate flex spans (fixes visually-collapsing space) and lowercased to "one of your tough ones"; web/src/screens/Review.test.tsx — new regression test
- [2026-08-05] Modified: qa/issues/621-hardest-negative-limit-silently-drops-cards.md, qa/issues/622-queue-difficulty-unrounded-vs-hardest-rounded.md, qa/issues/640-review-tough-badge-missing-space-after-emoji.md — marked done with Fix notes

- [2026-08-05] Modified: app/srs/fsrs.py — difficulty(state) reader (FSRS 1–10, null until first review)
- [2026-08-05] Modified: app/srs/service.py — hardest_cards() ranks a user's reviewed cards by difficulty
- [2026-08-05] Modified: app/srs/api.py — GET /srs/hardest (Slice 2); shared _resolve_vocab helper; /srs/queue gains `difficulty`
- [2026-08-05] Created: web/src/screens/Hardest.tsx + Hardest.test.tsx — "Hardest for you" deck (difficulty bands, reveal, audio)
- [2026-08-05] Modified: web/src/App.tsx, web/src/screens/Path.tsx — /hardest route + 🔥 hub tile; web/src/api.ts — hardest() + HardCard/DueCard.difficulty; web/src/screens/Review.tsx — tough-card badge

- [2026-08-05] Fixed: app/content/personal_api.py — QA #620: /vocab/personal/from-word now rejects (422) words that already resolve to a ContentVocab entry instead of silently minting a duplicate uv: card; app/speech/vocab_review.py — added find_content_match() reusing resolve_new_words' _norm/_deaccent matching; tests/test_personal_vocab.py — regression test for #620; qa/issues/620-from-word-no-content-bank-check.md — marked done

- [2026-08-05] Modified: app/speech/vocab_review.py — Slice 3c: resolve_new_words() (rich tier — extracted lemmas not in content bank, not already personal cards)
- [2026-08-05] Modified: app/speech/api.py — vocab-review response carries `new_words`
- [2026-08-05] Modified: app/content/personal_api.py — POST /vocab/personal/from-word (enrich + add in one budget-gated call)
- [2026-08-05] Modified: web/src/screens/Speaking.tsx, web/src/api.ts — SessionReview "New words for your deck" one-click add; speechVocabReview new_words + personalAddFromWord
- [2026-08-05] Modified: tests/test_speech.py, tests/test_personal_vocab.py, web/.../Speaking.test.tsx — Slice 3c tests

- [2026-08-05] Fixed: app/content/personal.py — QA round 049 #610 (reject degenerate/empty-slug words → 422, strip leading article) + #611 (clamp uv:<slug> to the card_key 64-char column); app/content/personal_api.py maps EmptyLemmaError→422
- [2026-08-05] Modified: tests/test_personal_vocab.py — regression tests for #610/#611 (11 tests total)
- [2026-08-05] Created: qa/rounds/049-plan.md; qa/issues/610-*, 611-* (marked done) — Slice E QA round (run by hand after orchestrator failed)

- [2026-08-04] Created: migrations/versions/0018_user_vocab.py — user_vocab table (personal decks)
- [2026-08-04] Modified: app/content/tables.py — UserVocab model (per-user cards, uv:<slug> key, lazy audio_key)
- [2026-08-04] Created: app/content/personal.py — personal-deck service (key namespacing, add/list/get, queue resolver)
- [2026-08-04] Created: app/content/personal_api.py — /vocab/personal API: preview (enrich), add, my-deck, lazy TTS audio
- [2026-08-04] Modified: app/srs/api.py — /srs/queue resolves uv: keys from user_vocab (personal cards ride the shared FSRS loop)
- [2026-08-04] Modified: app/main.py — register personal-vocab router; app/config/settings.py — vocab_daily_token_budget
- [2026-08-04] Created: tests/test_personal_vocab.py — 8 tests (service, preview+budget, add/queue, lazy audio)
- [2026-08-04] Modified: web/src — MyDeck screen + route/nav, api personal methods, AudioButton audioUrl, Review personal audio; MyDeck.test.tsx (Slice E)

- [2026-08-02] Created: app/content/enrich.py — Slice D: dictionary enrichment engine (LLM gloss/pos/ipa + deterministic gender backstop: table > suffix rule > model guess)
- [2026-08-02] Created: app/content/data/fr_gender.tsv — seed French noun-gender table (source of truth; drop-in slot for a full Lexique383 extract)
- [2026-08-02] Created: tests/test_enrich.py — 14 tests for the enrichment engine (suffix rules, table precedence, JSON parsing, async orchestration)
- [2026-08-02] Modified: app/config/ai_routing.yaml, ai_routing.ollama.yaml — add cached vocab_enrich JSON profile
- [2026-08-02] Modified: docs/anki-vocab-plan.md — mark Slice 1 merged (#68) + Slice D built

- [2026-07-28] Fixed: app/ai/adapters/piper_adapter.py — collapse reply whitespace to one line so Piper emits a single WAV; multi-line examiner replies were cut off at the first line break (played only the first sentence)
- [2026-07-28] Created: tests/test_piper_adapter.py — _one_line normalization (CI); tests/test_speech_integration.py — multi-line reply → single WAV (gated)

- [2026-07-27] Modified: web/src/screens/Path.tsx, web/src/styles.css — daily-goal ring on the home (progress + goal-reached celebration)
- [2026-07-27] Modified: web/src/api.ts — Me type carries xp_today/daily_goal
- [2026-07-27] Modified: web/src/screens/Path.test.tsx — daily-goal ring tests (progress + reached)
- [2026-07-27] Created: migrations/versions/0015_daily_xp.py, app/progress/models.py DailyXp — per-(user,day,source) XP ledger for the daily-goal ring + anti-farm caps
- [2026-07-27] Modified: app/progress/service.py — record_activity gains source/once_per_day (writes daily ledger); add xp_earned_today + DAILY_XP_GOAL
- [2026-07-27] Modified: app/srs/api.py, app/tutor/api.py — Review & Drill now award XP (once/day) + advance the streak; return xp/xp_today
- [2026-07-27] Modified: app/progress/api.py (me: +xp_today/daily_goal), app/comprehension/api.py, app/exam/api.py — tag record_activity with source
- [2026-07-27] Created: tests/test_daily_xp.py — once-per-day cap, cross-source ring sum, streak coverage, next-day reset

- [2026-07-27] Modified: app/speech/api.py — reject empty (400) / oversized (413, 10MB cap) / undecodable (422) audio cleanly; skip billing on no-speech (422) — H9
- [2026-07-27] Modified: app/speech/examiner.py — empty transcript short-circuits before the LLM/billing (no_speech)
- [2026-07-27] Modified: app/ai/adapters/faster_whisper_adapter.py — wrap decode failures as TranscriptionError; vad_filter=True so silence→empty (no phantom transcript)
- [2026-07-27] Modified: app/ai/errors.py — add TranscriptionError (bad audio → 4xx, not 500)
- [2026-07-27] Modified: tests/test_speech.py, tests/test_speech_integration.py — H9 input-hardening tests (unit + real-model)

- [2026-07-27] Created: qa/fixtures/speech/english-speech.wav — synthetic English clip (macOS say) for the H9 wrong-language case; Tatoeba source rejected as CC BY-NC-ND
- [2026-07-27] Modified: qa/fixtures/speech/README.md — document english-speech.wav (H9 whisper-translates finding); correct the Tatoeba block's wrong CC-BY assumption (verify per-clip license)

- [2026-07-27] Created: qa/fixtures/speech/hello-fr.webm — real Chrome MediaRecorder webm/opus blob captured through the Speaking screen (H1 fixture)
- [2026-07-27] Modified: tests/test_speech_integration.py — add webm/opus decode+transcribe test (H1)
- [2026-07-27] Modified: qa/fixtures/speech/README.md — mark hello-fr.webm done; document the capture method

- [2026-07-27] Modified: qa/issues/530-topbar-nav-overflow-320px.md — triaged: validated (independently reproduced 320px `.nav` overflow via iframe + getBoundingClientRect, not just tester's screenshots)
- [2026-07-27] Modified: qa/issues/540-speaking-record-requests-mic-before-checking-availability.md — triaged: validated (mic-permission-before-availability-check confirmed real via source read of Speaking.tsx/api.py; in-scope per qa/README's "handling is poor" carve-out)

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
- [2026-07-27] Created: qa/issues/540-speaking-record-requests-mic-before-checking-availability.md — QA round 043 H8 finding: Speaking screen requests mic permission before checking backend speech availability
- [2026-07-27] Modified: web/src/styles.css — fix qa-530: contain the phone `.nav` row's overflow (overflow-x: auto strip) instead of leaking into page scroll at 320px
- [2026-07-27] Created: web/src/styles.test.ts — regression test for qa-530 (phone media query keeps .nav overflow-safe)
- [2026-07-27] Modified: qa/issues/530-topbar-nav-overflow-320px.md — status: done, add Fix section
- [2026-07-27] Modified: app/speech/api.py — fix qa-540: add GET /speech/status capability check ({"available": bool})
- [2026-07-27] Modified: web/src/api.ts — fix qa-540: add api.speechStatus()
- [2026-07-27] Modified: web/src/screens/Speaking.tsx — fix qa-540: preflight speech availability on mount; disable Record + show message upfront when unconfigured, instead of after a wasted mic-grant/record/transcribe round-trip
- [2026-07-27] Modified: tests/test_speech.py — regression tests for GET /speech/status (available true/false)
- [2026-07-27] Created: web/src/screens/Speaking.test.tsx — regression test for qa-540 (Record disabled + message shown when speech unavailable)
- [2026-07-27] Modified: qa/issues/540-speaking-record-requests-mic-before-checking-availability.md — status: done, add Fix section
- [2026-07-30] Created: web/src/speed.tsx — Shared, localStorage-backed slow-replay rate (0.9×–0.5×) + header control
- [2026-07-30] Modified: web/src/AudioButton.tsx — 🐢 button now uses the user-set slow rate
- [2026-07-30] Modified: web/src/screens/Speaking.tsx — Added 🐢 slow-replay to examiner reply audio
- [2026-07-30] Modified: web/src/App.tsx — Wrapped app in SpeedProvider; added SlowSpeedControl to header
- [2026-07-30] Modified: web/src/VocabWord.tsx — Enabled 🐢 slow replay on vocab word audio
- [2026-07-30] Modified: web/src/screens/Review.tsx — Enabled 🐢 slow replay on vocab audio
- [2026-07-30] Modified: web/src/screens/Lesson.tsx — Enabled 🐢 slow replay on listen-type drill audio
- [2026-08-01] Created: app/speech/topics.py — SpeakingTopic model + YAML loader + per-level sync + examiner framing
- [2026-08-01] Modified: app/speech/tables.py — add SpeakingTopicRow (synced speaking topics)
- [2026-08-01] Modified: app/speech/examiner.py — turn() accepts system_extra to append topic framing
- [2026-08-01] Modified: app/speech/api.py — GET /speech/topics; POST /speech/turn accepts topic_id
- [2026-08-01] Created: migrations/versions/0016_speaking_topics.py — speaking_topics table
- [2026-08-01] Modified: start.sh — sync-all now syncs speaking topics
- [2026-08-01] Created: content/{a1,a2,b1,b2}/speaking/*.yaml — 8 authored TEF speaking topics
- [2026-08-01] Created: tests/test_speaking_topics.py — loader/framing/list/turn-framing tests
- [2026-08-01] Modified: web/src/api.ts — SpeakingTopic type, speakingTopics(), postSpeechTurn topicId
- [2026-08-01] Modified: web/src/screens/Speaking.tsx — topic picker + task card; passes topic_id per turn
- [2026-08-01] Modified: web/src/screens/Speaking.test.tsx — mock useLevel/speakingTopics; topic-picker test
- [2026-08-01] Modified: app/config/settings.py — add whisper_device/whisper_compute_type + examiner_max_tokens
- [2026-08-01] Modified: app/speech/factory.py — pass device/compute_type to FasterWhisperAdapter
- [2026-08-01] Modified: app/speech/examiner.py — turn() forwards max_tokens to the router
- [2026-08-01] Modified: app/speech/api.py — cap examiner reply via examiner_max_tokens setting
- [2026-08-01] Modified: .env.example — document whisper device/compute + examiner token knobs
- [2026-08-01] Created: tests/test_speech_speed.py — STT device/compute wiring + max_tokens cap tests
- [2026-08-01] Modified: web/src/screens/Speaking.tsx — qa-560: topic-aware record hint (was static "introduce yourself" text)
- [2026-08-01] Modified: web/src/screens/Speaking.test.tsx — qa-560: test generic vs topic-aware hint copy
- [2026-08-01] Modified: qa/issues/560-speaking-instruction-hint-ignores-picked-topic.md — status: done, added Fix note
- [2026-08-01] Modified: app/ai/adapters/piper_adapter.py — _clean(): strip markdown/emoji, normalize typographic punctuation before TTS (was _one_line)
- [2026-08-01] Modified: tests/test_piper_adapter.py — cover markup/emoji/punctuation sanitizing
- [2026-08-01] Modified: app/speech/prompts/examiner.md — instruct plain spoken French (no markdown/emoji/English)
- [2026-08-01] Modified: app/speech/prompts/conversation.md — same clean-spoken-French output rule
- [2026-08-01] Modified: Dockerfile — bake fr_FR-upmc-medium voice (clearer than siwis; Piper has no fr_CA)
- [2026-08-01] Modified: docker-compose.yml — PIPER_VOICE=fr_FR-upmc-medium.onnx
- [2026-08-01] Modified: .env.example — note upmc voice + no Canadian Piper voice
- [2026-08-01] Modified: tests/test_speech_integration.py — default voice fallback fr_FR-upmc-medium
- [2026-08-01] Modified: app/ai/adapters/piper_adapter.py — qa-570/571/572/573: extend emoji range, strip truncated md-links, bare URLs, and leading list bullets
- [2026-08-01] Modified: tests/test_piper_adapter.py — regression tests for qa-570..573
- [2026-08-01] Created: qa/rounds/046-plan.md; qa/issues/570-573 — round 046 (diction sanitizer)
- [2026-08-01] Modified: app/speech/api.py — lazy audio: POST /speech/turn no longer synthesizes; GET /speech/audio synthesizes on first play and caches
- [2026-08-01] Modified: tests/test_speech.py — lazy-audio tests (no synth at POST, synth+cache on GET, no-TTS 404)
- [2026-08-01] Modified: scripts/docker-entrypoint.sh — sync speaking topics on boot (was missing; only start.sh had it)
- [2026-08-01] Created: migrations/versions/0017_speech_session_id.py — Add nullable session_id to speech_turns (conversation grouping)
- [2026-08-01] Modified: app/speech/tables.py — SpeechTurn.session_id column
- [2026-08-01] Created: app/speech/vocab_review.py — Slice 3a: extract review words from a session transcript + resolve to existing vocab ids
- [2026-08-01] Modified: app/speech/api.py — session_id on /speech/turn, session-scoped history, POST /speech/session/{id}/vocab-review endpoint
- [2026-08-01] Modified: app/config/ai_routing.yaml, ai_routing.ollama.yaml — vocab_extract profile (cheap, JSON)
- [2026-08-01] Modified: web/src/api.ts — postSpeechTurn sessionId param, VocabCandidate type, speechVocabReview()
- [2026-08-01] Modified: web/src/screens/Speaking.tsx — per-conversation session id + end-of-conversation SessionReview (confirm-seed words to SRS)
- [2026-08-01] Modified: tests/test_speech.py — tests for vocab-review extraction/resolution/exclusion, empty-session no-LLM, session_id persistence
- [2026-08-01] Created: tests/test_qa_580_vocab_review.py — QA scratch tests probing speaking vocab-review budget/isolation/resolve hypotheses (H1-H4)
- [2026-08-01] Created: qa/issues/580-speech-vocab-review-no-budget-check.md — filed H1 finding: session_vocab_review has no daily-budget check, bills unbounded
- [2026-08-01] Modified: app/speech/api.py — Slice 3b: GET /speech/last-session (most recent prior session for resurface nudge)
- [2026-08-01] Modified: web/src/api.ts — speechLastSession()
- [2026-08-01] Modified: web/src/screens/Speaking.tsx — generalized SessionReview; "Review words from your last conversation" nudge (opt-in, dismissible)
- [2026-08-01] Modified: web/src/screens/Speaking.test.tsx — mock speechLastSession
- [2026-08-01] Modified: tests/test_speech.py — tests for /speech/last-session (latest/exclude/null)
- [2026-08-01] Modified: docs/anki-vocab-plan.md — mark Slice 3b built
- [2026-08-02] Modified: web/src/screens/Speaking.tsx — QA-601: clearer prior-session nudge label (add-to-deck action)
- [2026-08-02] Created: qa/issues/600-602, qa/rounds/048-plan.md — Slice 3b QA round (601 fixed; 600,602 rejected)
- [2026-08-02] Created: scripts/import_anki.py — Slice 1: AnkiWeb .apkg → review-ready vocab YAML (clean/normalize/dedup/enrich/emit)
- [2026-08-02] Created: tests/test_import_anki.py — 10 tests for the importer (synthetic .apkg fixture)
- [2026-08-02] Modified: .gitignore — ignore imports/ (.apkg build inputs, not redistributed)
- [2026-08-02] Modified: docs/anki-vocab-plan.md — mark Slice 1 importer built
- [2026-08-02] Created: content/b2/vocab/actualite.yaml — 33-card news/economy vocab deck imported from AnkiWeb Wiktionary frequency list (curated) + 33 TTS clips
- [2026-08-02] Modified: docs/anki-vocab-plan.md — Direction update: dictionary enrichment (LLM+Lexique) + personal user decks (Slices D, E); reframed 3c; revised roadmap
- [2026-08-05] Created: qa/issues/610-personal-vocab-whitespace-degenerate-card-key.md — QA finding: whitespace-only fr collapses to degenerate uv: card_key
- [2026-08-05] Created: qa/issues/611-personal-vocab-card-key-exceeds-column-limit.md — QA finding: long fr produces card_key exceeding declared 64-char DB column
- [2026-08-05] Modified: qa/issues/621-hardest-negative-limit-silently-drops-cards.md — critic gate: appended Critic block, kept validated
- [2026-08-05] Modified: qa/issues/622-queue-difficulty-unrounded-vs-hardest-rounded.md — critic gate: appended Critic block, kept validated
- [2026-08-05] Modified: qa/issues/640-review-tough-badge-missing-space-after-emoji.md — critic gate: appended Critic block, kept validated (repro'd live in browser)
