# QA round 015 — plan

- date: 2026-06-22
- app under test: backend :9000
- scope: regression on round-014 fixes (240/250/252/260) + new angles on writing boundaries, exam idempotency, level promotion ordering, SRS cross-level, auth validation, malformed input 500s

## Change surface (highest risk first)
Since round 014, a single fix commit landed (`a422402`) on branch `qa/round-014-fixes`:
1. `app/assessment/api.py` — word count validation (min_words/max_words) added before LLM grading. Uses `body.text.split()` for counting, `if min_words and ...` guard.
2. `app/exam/api.py` — `started_at` added to start/resume/get_attempt responses; `record_activity(xp_award=25)` called on finish; idempotent finish returns early for already-finished attempts (before `record_activity`).
3. `app/progress/service.py` — `_LEVEL_ORDER` list added; `record_activity` now promotes `prog.level` when incoming level index > current level index.

All three files are the primary risk surface — the fixes themselves may have edge cases or regressions.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | assessment | Writing word-count boundary: exactly min_words (40) or exactly max_words (100) might be rejected due to off-by-one in `<`/`>` vs `<=`/`>=` | Submit text with exactly 40 words and exactly 100 words to a section-a task; both should pass (the code uses strict `<`/`>`, so boundaries are inclusive — verify) | edge-case-breaker |
| H2 | exam | Exam finish idempotency: finishing a completed exam a second time might double-award XP (25+25) since `record_activity` was added | Finish an exam, note XP, finish same attempt again, check XP unchanged; the early return at line 198-199 should prevent this | edge-case-breaker |
| H3 | progress | Level promotion never demotes: completing an A1 lesson AFTER A2 activity might reset level from a2 back to a1 | Sign up, complete A2 lesson (level should be a2), then complete A1 lesson, check /progress/me still shows a2 | edge-case-breaker |
| H4 | exam | started_at regression: verify start, resume, and get_attempt all return started_at as ISO string (fix 250) | Start an exam, check response; call start again (resume path), check response; GET /exam/attempts/{id}, check response | exam-crammer |
| H5 | exam | Exam XP award verified: completing a mock awards exactly 25 XP (fix 252); comprehension XP (15) and exam XP (25) don't interfere | Complete comprehension set (15 XP), complete exam (25 XP), verify total is 40 | exam-crammer |
| H6 | progress | Level promotion verified: completing A2 activity after A1 updates profile level to a2 (fix 260); board reflects correct level | Sign up, complete A1 lesson, check level=a1, complete A2 lesson, check level=a2 | returning-learner |
| H7 | assessment | Writing word-count validated: submitting below min_words or above max_words returns 422 (fix 240) | Submit 2-word and 200-word texts to section-a task (min=40, max=100); both should get 422 | edge-case-breaker |
| H8 | srs | SRS queue with both A1+A2 vocab seeded: completing lessons from both levels seeds cards correctly without duplicates or collisions | Complete one A1 and one A2 lesson, check /srs/queue returns cards from both levels | returning-learner |
| H9 | auth | Signup validation edge cases: empty display_name, very long password (10k chars), duplicate email, invalid invite code — should all get clean 4xx, not 500 | Send malformed signup payloads | edge-case-breaker |
| H10 | exam | Exam section with malformed input: negative correct, zero total, correct > total, missing required fields — should all get 422 | Send bad section payloads to an in-progress attempt | edge-case-breaker |
| H11 | comprehension | Comprehension double-submit regression: submitting the same set twice should not double-award XP (regression from issue 100 fix) | Submit same comprehension set twice, check XP only incremented once | exam-crammer |

## Coverage gaps
- Writing word-count boundary values (exactly min, exactly max): never tested
- Exam finish idempotency (double-finish XP): never tested with the new `record_activity` call
- Level promotion ordering (A1 after A2): never tested
- SRS queue with mixed-level vocab: untested
- Auth signup validation edge cases: last tested round 007 (display_name cap), not re-checked on this branch

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 270-279): Chase H1 (word-count boundaries), H2 (exam finish idempotency + XP), H3 (level demotion), H7 (word-count rejection), H9 (auth validation), H10 (exam section malformed input). Focus on boundary values and double-submit patterns across all three fixed files.

- `exam-crammer` (ids 280-289): Chase H4 (started_at in responses), H5 (exam XP award + total), H11 (comprehension double-submit XP regression). Run one full A1 or A2 mock end-to-end, verify CLB report, XP, and started_at.

- `returning-learner` (ids 290-299): Chase H6 (level promotion verification), H8 (SRS cross-level queue). Walk through A1 and A2 lessons, verify level transitions on profile and board, check SRS seeding from both levels.

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 007 negative elapsed_seconds — rejected
- 030 exam section re-record — rejected (by design)
- 050 lesson score is client-reported — deferred (low risk)
- 071 comprehension no-replay not enforced — rejected (client-only rule)
- 102 CLB estimate clamped — rejected (by design)
- 131 password no max length — rejected
- 180 comprehension feedback reveals answers — deferred (post-submit, by design)
- 181 locked lesson content readable — rejected (content is not secret)
- 221 comprehension pass threshold not shown — deferred
- 230 listen_type exercise empty prompt — done
- 231 board pre-fix oversized display_name — done
- 251 exam history ignores level filter — rejected (feature request)
- Drill / Writing / Speaking 503 with no LLM provider — expected (no Ollama model loaded)

<!-- After the round, the planner notes each hypothesis: confirmed (-> issue NNN) /
     refuted (area sound) / untested. -->
