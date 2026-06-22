# QA round 013 — plan

- date: 2026-06-21
- app under test: backend :9000 / SPA :5174
- scope: A1 content bank expansion + audio endpoint (PR #1, branch content/a1-bank)

## Change surface (highest risk first)
Two commits on `content/a1-bank`:
1. `51137d7` — deep A1 content bank: 10 vocab themes (98 cards), 10 lessons across 10 gated units, 19 comprehension sets (9 reading + 10 listening), 6 writing tasks, 2 exam blueprints (mock-1, mock-2). New optional `ComprehensionSet.script` field on listening sets.
2. `02f7c75` — `GET /content/audio/{key}` endpoint serving audio from object storage; auth-gated; key regex `^[a-z0-9]+/audio/[A-Za-z0-9._-]+\.mp3$`. 15 TTS clips in `content/a1/audio/`.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | audio endpoint | Path traversal may bypass the regex guard (e.g. `../etc/passwd`, URL-encoded variants, double-dot in key, non-.mp3 suffix) | Try traversal payloads, bad keys, missing keys; confirm 404 not 500/file leak | edge-case-breaker |
| H2 | audio endpoint | Unauthenticated requests to `/content/audio/{key}` may succeed (missing auth check) | Call without token; expect 401/403 | edge-case-breaker |
| H3 | listening script leak | `GET /comprehension/sets/{id}` or `GET /comprehension/sets?level=a1` may expose the `script` field (TTS transcript = answer source) for listening sets | Fetch each listening set, inspect response for `script` key | edge-case-breaker |
| H4 | content integrity | MCQ answers may not be in options, word_bank answers may not be subset of tokens, match_pairs may be malformed — across 10 lessons with ~40 exercises | Fetch every lesson via API, validate answer-in-options invariant per exercise type | exam-crammer |
| H5 | exam blueprint refs | mock-1 and mock-2 may reference nonexistent comprehension_set_id or writing_task_ids (id mismatch between blueprint and content) | Start both mocks, confirm section data loads; also cross-check IDs from blueprint YAML vs actual DB rows | exam-crammer |
| H6 | unit gating | With 10 linearly-gated units, compute_unit_status may miscalculate for partial progress (e.g. completing u1 but not u2 should leave u3+ locked) | Sign up fresh user, complete lessons incrementally, check `/content/path?level=a1` status transitions | absolute-beginner |
| H7 | SRS seeding | New lessons' `new_vocab` should seed the SRS queue after lesson completion | Complete a lesson, check `/srs/queue` includes the lesson's vocab items | absolute-beginner |
| H8 | audio serves real bytes | Valid audio keys should return `audio/mpeg` with non-empty body; 404 for keys pointing to nonexistent files | Fetch known-good keys (e.g. `a1/audio/bonjour.mp3`), check Content-Type + body length | edge-case-breaker |
| H9 | exam mock-2 full flow | Start mock-2, submit all 4 sections (reading, listening, writing, speaking), finish, confirm CLB report generates | Full exam lifecycle for mock-2 specifically (it's new and untested) | exam-crammer |
| H10 | regression: comprehension XP | With 19 new sets, the one-pass XP claim (qa-100 fix) should hold — double-submit should not double-award | Submit same set twice, verify XP awarded only once | exam-crammer |

## Coverage gaps
- `/content/audio/{key}` — brand new endpoint, zero prior testing
- 17 of 19 comprehension sets have never been fetched/submitted in QA
- mock-2 blueprint never tested end-to-end
- SRS seeding from new vocab themes untested
- Unit gating across 10 units untested (prior tests only had 2 lessons)

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 210-219): Chase H1 (audio traversal), H2 (audio auth), H3 (script leak), H8 (audio serves bytes). Security-focused: hammer the new audio endpoint with bad inputs, check every listening set for script leakage.

- `exam-crammer` (ids 220-229): Chase H4 (content integrity), H5 (blueprint refs), H9 (mock-2 flow), H10 (XP regression). Content-correctness focused: validate every lesson's exercises, run both exam blueprints, double-submit comprehension.

- `absolute-beginner` (ids 230-239): Chase H6 (unit gating), H7 (SRS seeding). Happy-path focused: sign up fresh, walk through the first few lessons, check the path unlocks and SRS fills in.

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 007 negative elapsed_seconds — rejected (no impact)
- 030 exam section re-record — rejected (by design)
- 050 lesson score is client-reported — deferred (low risk)
- 071 comprehension no-replay not enforced — rejected (client-only rule)
- 102 CLB estimate clamped — rejected (by design)
- 131 password no max length — rejected
- 180 comprehension feedback reveals answers — deferred (by design, post-submit)
- 181 locked lesson content readable — rejected (content is not secret)
- Drill / Writing / Speaking 503 with no LLM provider — expected (no Ollama model loaded)

## Results

| # | hypothesis | result | notes |
|---|------------|--------|-------|
| H1 | Audio path traversal | refuted | All traversal payloads return clean 404; regex guard holds |
| H2 | Audio auth bypass | refuted | 401 without token on both /content/audio and /comprehension/audio |
| H3 | Listening script leak | refuted | _client_view whitelist excludes script; verified on all 10 listening sets |
| H4 | Content integrity | refuted | All 10 lessons, all exercise types validate (answers in options, tokens, etc.) |
| H5 | Exam blueprint refs | refuted | All 8 referenced resources (comprehension + writing) resolve 200 |
| H6 | Unit gating 10 units | refuted | Strictly linear; completing u1 unlocks only u2; locked lessons return 409 |
| H7 | SRS seeding | refuted | new_vocab items appear in /srs/queue after lesson completion |
| H8 | Audio serves bytes | refuted | Valid keys return audio/mpeg with real content; missing keys return 404 |
| H9 | Mock-2 full flow | refuted | Start, 4 sections, finish, CLB report all work; history records it |
| H10 | XP double-award regression | refuted | Second submit returns first_pass: false, XP unchanged |

### Issues filed: 4 -- validated: 3, deferred: 1, fixed: 3

| id | title | severity | final status |
|----|-------|----------|-------------|
| 220 | Exam history missing level field | low | done |
| 221 | Comprehension pass threshold not shown | medium | deferred |
| 230 | listen_type exercise empty prompt in greetings-01 | medium | done |
| 231 | Board still serves pre-fix oversized display_name | medium | done |

Commit: `8ec5595` -- all 108 tests pass.
