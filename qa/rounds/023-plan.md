# QA round 023 — plan

- date: 2026-06-25
- app under test: backend :9000 / SPA :5173
- scope: PR #18 `write-vocab-blend` — target_vocab on writing tasks, within-level guard, grader prompt threading, fr resolution, 4 new tasks, UI chip row

## Change surface (highest risk first)
1. `app/assessment/loader.py` — new `_check_target_vocab` guard (within-level constraint)
2. `app/assessment/grader.py` — `build_messages`/`grade_text`/`grade` now thread `target_vocab_fr`; prompt injection surface
3. `app/assessment/api.py` — `_resolve_vocab_fr` (order preservation, missing-id drop); wired into `get_task` + `submit`
4. `app/content/loader.py` — extracted `load_level_vocab` (shared by content loader + writing loader)
5. Content YAML — 12 backfilled tasks + 4 new tasks with `target_vocab` lists
6. `web/src/screens/WritingTask.tsx` — "Try to use:" chip row
7. `web/src/api.ts` — `target_vocab_fr?` on WritingTaskSummary
8. `app/assessment/prompts/writing_grader.md` — nudge-not-penalty instruction

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | within-level guard | If a writing task references a vocab id from another level, the loader should reject it. The guard exists — but does the real content pass cleanly, and can we trigger the guard with a synthetic bad id? | Unit test + loader validation of shipped content | edge-case-breaker |
| H2 | grader prompt stability | If target_vocab_fr is empty or None, the grader prompt must be byte-identical to the pre-PR prompt (no extra newline, no "Target vocabulary" line). Drift would break calibration. | Call `build_messages` with empty/None, compare output | edge-case-breaker |
| H3 | _resolve_vocab_fr edge cases | If ids list contains a non-existent id, it should be silently dropped (not crash). Order must be preserved. Empty input must return []. | API calls with synced DB + manual inspection | edge-case-breaker |
| H4 | list_tasks omits target_vocab_fr | The list endpoint does NOT include target_vocab_fr — only get_task does. If a tester expects it on list, it's not there. Is this intentional and correct? | Hit /assessment/tasks?level=a1 and /assessment/tasks/{id} | absolute-beginner |
| H5 | new task French quality | The 4 new task prompts (shopping, seasons, doctor, public-transport) should be natural French at the right register and level (A1/A2). Accents correct. target_vocab words should be on-theme. | Read YAML prompts, check French | absolute-beginner |
| H6 | submit with target_vocab | When submitting against a task that has target_vocab, the grader prompt should include the French forms. The grader should reward use, not penalise omission. | Submit via API, inspect grader call | edge-case-breaker |
| H7 | backfilled tasks regression | The 12 existing tasks that got `target_vocab` backfilled must still load, list, get, and submit correctly. No regression in word-count gates. | Full flow: list -> get -> submit for existing tasks | absolute-beginner |
| H8 | UI chip row rendering | target_vocab_fr chips should appear on task detail but not crash when absent. The "Try to use:" label should be clear to a beginner. | Inspect TSX code for conditional rendering | absolute-beginner |

## Coverage gaps
- No existing issue covers the target_vocab feature (first round on this PR).
- `_resolve_vocab_fr` has no unit test — only integration via API tests.
- The `list_tasks` endpoint does not expose `target_vocab_fr`; if the frontend list view ever needs it, it's missing.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 360-369): Chase H1, H2, H3, H6. Focus on the within-level guard (can you break it?), grader prompt stability (empty/None must be identical), _resolve_vocab_fr edge cases (missing ids, order, empty), and submit-with-vocab flow. Hammer boundary conditions: duplicate vocab ids in target_vocab, very long target_vocab lists, ids with special characters.

- `absolute-beginner` (ids 370-379): Chase H4, H5, H7, H8. Walk the happy path: list tasks, pick one, see the vocab chips, write something, submit. Check the 4 new task prompts for French correctness and level-appropriateness. Verify the UI shows "Try to use:" only when there are target words. Check that existing tasks still work after backfill.

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 007 negative elapsed_seconds — rejected (no impact)
- 030 exam section rerecord — deferred
- 050 lesson score client-reported — deferred
- 071 comprehension no-replay — deferred
- 102 exam CLB clamped — rejected (by design)
- 131 password no max length — deferred
- 180/181 comprehension feedback/locked content — deferred (data exposure audit)
- 221 comprehension pass threshold — deferred
- 251 exam history level filter — rejected
- 290 SRS negative limit — rejected
- 300 vocab string bool — rejected
- 320 e2e test isolation — rejected (test-only)
- 330 vocab deck stale comment — done
- 340/350 audio sync — done
- Drill/Writing/Speaking 503 with no provider — expected behavior
