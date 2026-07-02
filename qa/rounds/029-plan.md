# QA round 029 — plan

- date: 2026-07-01
- app under test: backend :9000 / SPA served via catch-all at same port
- scope: content/b1-new-themes — 2 new mock exams (mock-4, mock-5), 8 new comprehension
  sets, 4 new writing tasks, 4 new B1 units (u7–u10), catch-all SPA route regression

## Change surface (highest risk first)

1. **Two new mock exam blueprints** `b1-mock-4` (éducation & logement) and `b1-mock-5`
   (argent & immigration) in `content/b1/exam/`. Each wires new comprehension sets and
   writing tasks together in a 4-section timed mock.
2. **8 new comprehension sets** in `content/b1/comprehension/`:
   - reading: `read-b1-university-enrolment`, `read-b1-rental-listing`,
     `read-b1-household-budget`, `read-b1-residency-steps`
   - listening: `listen-b1-student-orientation`, `listen-b1-landlord-message`,
     `listen-b1-bank-advisor`, `listen-b1-citizenship-info`
   All 4 listening sets have TTS audio in `content/b1/audio/` and all have
   `allow_replay: true` (same pattern as issue #404, which was deferred).
3. **4 new writing tasks**: `write-b1-education` (B), `write-b1-rental-issue` (A),
   `write-b1-bank-error` (A), `write-b1-immigration` (B). New tasks — confirm they are
   seeded in the DB, min/max bounds enforced, target_vocab resolves.
4. **4 new B1 units u7–u10** (education, housing, money, immigration): 12 new lesson files
   + 4 new vocab decks (72 cards, themes: education/logement/argent/immigration). Total
   B1 vocab is now 180 cards across 10 decks (confirmed via `/content/vocab?level=b1`).
   Chain: u7 requires u6 requires u5 … — gating must hold.
5. **SPA catch-all route** added to `app/main.py` AFTER all API routers. Confirmed active:
   `GET /nonexistent-path` returns HTTP 200 with `text/html` (index.html). Non-existent
   paths that look like API routes will silently return HTML instead of JSON 404 — this
   may mislead clients that don't check Content-Type.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | mock-4 / mock-5 end-to-end | The new blueprints start cleanly, all 4 sections load, finish produces a CLB report; the new comprehension set refs and writing task refs resolve at runtime without dangling-ID errors | Start mock-4, submit all 4 sections, finish, verify CLB. Repeat for mock-5 | exam-crammer |
| H2 | new comprehension sets — grading | Submitting correct/incorrect answers for all 8 new sets returns expected scores and per-question explanations | POST /comprehension/sets/{id}/submit with all answers correct, then with wrong answers; check score and explain fields | exam-crammer |
| H3 | new listening sets — audio serving | The 4 new listen-b1-* sets serve audio via /comprehension/audio/{set_id} without 404/500; bytes are non-zero | GET /comprehension/audio/{id} for each of the 4 new listening sets | edge-case-breaker |
| H4 | new writing tasks — word-count enforcement | Submissions below min_words or above max_words are rejected (422); exact-boundary submissions pass | POST /assessment/tasks/{id}/submit with 1 word, min_words-1, min_words, max_words, max_words+1 | edge-case-breaker |
| H5 | new writing tasks — DB sync | All 4 new tasks appear in /assessment/tasks?level=b1 and are individually fetchable by ID | GET /assessment/tasks and /assessment/tasks/{id} for each of the 4 new tasks | exam-crammer |
| H6 | unit unlock gating u7-u10 | u7 is locked until u6 complete; unlocking u6 unlocks u7; same chain for u8, u9, u10 — a shortcut attempt to access u9/u10 lessons before prerequisites fails or reports locked | Check /content/path?level=b1 for lock status; attempt /content/lessons/{id} for locked units | edge-case-breaker |
| H7 | SPA catch-all shadows API 404s | GET on a plausible-but-wrong API path (e.g. /exam/blueprints/nonexistent, /comprehension/sets/bad-id) returns HTML 200 instead of JSON 404 — callers can't detect errors cleanly | Hit typo/missing-resource API URLs without auth and with auth; check Content-Type and status | edge-case-breaker |
| H8 | new mock sections — score history | After completing mock-4 and mock-5, /exam/history shows both attempts with correct level label and all section scores | GET /exam/history after finishing both mocks | exam-crammer |
| H9 | mock-5 writing tasks — bank-error + immigration pair | write-b1-bank-error (section A) and write-b1-immigration (section B) are new; no other mock has used them — verify they load in mock-5's writing section without empty or mismatched content | Start mock-5, advance to writing section, verify both task prompts render | exam-crammer |
| H10 | new vocab decks — SRS wiring | Cards from education/logement/argent/immigration decks can be added to SRS and appear in /srs/queue with audio keys (prior issue #350 was about missing audio on SRS cards) | Add a card from each new deck, hit /srs/queue, verify audio_key field present | edge-case-breaker |

## Coverage gaps

- `read-b1-university-enrolment` and `read-b1-residency-steps` have never been graded
  via the API (new files, no prior test).
- `write-b1-rental-issue` has not been individually tested for min/max bounds.
- `write-b1-immigration` target_vocab includes terms from the new immigration deck — not
  validated that these resolve to known card IDs.
- mock-4 and mock-5 have never been started (first time in API).
- Unit unlock chain for u7–u10 is untested (prior rounds only verified u1–u6).
- SPA catch-all route is new code in `app/main.py` — no prior QA coverage.
- `/exam/history` behavior with 5 mocks (mock-4, mock-5 adding to history) is new.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 406–415): chase H1, H2, H5, H8, H9
  - Start and complete mock-4 end-to-end (start → 4 sections → finish → CLB report) (H1)
  - Start and complete mock-5 end-to-end, paying attention to writing section task pair (H9)
  - Submit correct + incorrect answers to all 8 new comprehension sets; verify score/explain (H2)
  - Verify all 4 new writing tasks appear in /assessment/tasks?level=b1 (H5)
  - Check /exam/history shows both new mocks with correct labels after finishing (H8)

- `edge-case-breaker` (ids 416–425): chase H3, H4, H6, H7, H10
  - GET /comprehension/audio/{id} for each of the 4 new listening sets; check 200 + non-zero bytes (H3)
  - Word-count boundary tests for all 4 new writing tasks: too-short, min, max, too-long (H4)
  - Check /content/path?level=b1 for u7–u10 lock status; attempt locked lesson access (H6)
  - Test SPA catch-all: call plausible but wrong API paths; confirm HTML 200 vs JSON (H7)
  - SRS add cards from each new vocab deck; verify /srs/queue audio_key field present (H10)

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred (product decision)
- 007 comprehension accepts negative elapsed — rejected (no impact)
- 050 lesson score is client-reported — deferred
- 030 / 403 exam section rerecord overwrites — rejected
- 071 / 404 comprehension no-replay not enforced (allow_replay client-only) — deferred
- 131 password no max length — deferred
- 102 exam CLB estimate clamped — rejected
- 181 locked lesson content readable — deferred
- 180 comprehension feedback reveals answers — deferred
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — deferred
- 290 SRS queue negative limit — deferred
- 300 vocab known accepts string bool — rejected
- 320 e2e reuse server — deferred
- 330 vocab deck stale comment — rejected
- 370 new writing tasks not synced — rejected (by-design)
- 371 writing target vocab off-theme — rejected
- 394 level-filtered endpoints accept empty string — deferred
- 400 SRS queue vocab missing level field — done
- 401 match pairs en truncated — rejected
- 402 word bank global warming missing climatique — rejected
- 405 mock-3 writing tasks all duplicated — rejected
- Drill / Writing / Speaking 503 with no AI provider configured — expected (by-design)
- "B1 is shallow / only 6 units" — not a bug; vertical slice by design

## Outcome table

| # | hypothesis | result | issue | gate outcome |
|---|------------|--------|-------|--------------|
| H1 | mock-4 and mock-5 start, 4 sections each, finish → CLB report | REFUTED — both mocks complete end-to-end, CLB report includes per_skill + overall + note | none | n/a |
| H2 | new comprehension sets grading broken | REFUTED — all 8 sets grade correctly; correct answers → 1.0 score + explain fields; wrong answer → partial score | none | n/a |
| H3 | new listening audio not served | REFUTED — all 4 listen-b1-* sets return HTTP 200 audio/mpeg, 170–191 KB each | none | n/a |
| H4 | writing word-count bounds not enforced | REFUTED — short (4-word) submissions return 422 with clear message; above-max also 422; at min_words reaches AI layer (503 expected) | none | n/a |
| H5 | new writing tasks missing from API | REFUTED — all 4 tasks present in /assessment/tasks?level=b1 with correct prompt, min_words, max_words | none | n/a |
| H6 | unit unlock gating u7–u10 broken | REFUTED — u2–u10 locked for fresh user; POST progress on locked lesson returns 409; read content still accessible (deferred 181 still applies) | none | n/a |
| H7 | SPA catch-all shadows API 404s broadly | PARTIALLY CONFIRMED — /exam/blueprints/{id} (never registered) returns HTML 200; existing routes with bad IDs (/comprehension/sets/bad, /assessment/tasks/bad, /content/lessons/bad) return proper JSON 404 | 416 | rejected — route never planned; no client calls it; by-design |
| H8 | exam history missing new mocks | REFUTED — /exam/history shows both b1-mock-4 and b1-mock-5 with level=b1, status=finished, blueprint_id correct | none | n/a |
| H9 | mock-5 write-b1-bank-error + write-b1-immigration pair broken | REFUTED — writing section loads both tasks with correct prompts and word limits | none | n/a |
| H10 | new vocab deck SRS audio_key missing | REFUTED — cards from all 4 new themes add to SRS; /srs/queue returns vocab.audio with correct path (e.g. b1/audio/accueil.mp3) | none | n/a |

## Issues filed and gate results

| id | title | PM verdict | critic verdict | final |
|----|-------|-----------|----------------|-------|
| 416 | GET /exam/blueprints/{id} not registered — SPA catch-all returns HTML 200 | rejected (route never planned; frontend never calls it; by-design SPA behavior) | rejected (holds; no spec, no client, no regression) | rejected |

**Round verdict: CLEAN.** Zero validated issues. All 10 hypotheses refuted or rejected without warranted fix. The B1 new-themes slice (mock-4, mock-5, 8 comprehension sets, 4 writing tasks, 4 units u7–u10) is sound.

## Test suite and lint

- `pytest -q`: **144 passed**, 5 deprecation warnings (httpx/starlette — pre-existing, unrelated to this branch)
- `ruff check`: **all checks passed**
