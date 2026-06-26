# QA round 024 — plan

- date: 2025-06-25
- app under test: backend :9000
- scope: PR #19 `mock-vocab-blend` — exam-blueprint reference validation + two new vocab-blended mocks (mock-3 per level)

## Change surface (highest risk first)
1. `app/exam/loader.py` — new `_check_references()` validates comprehension set ids and writing task ids against this-level content at load time. New cross-module imports (assessment.loader, comprehension.loader).
2. `content/a1/exam/mock-3.yaml` — third A1 mock (read-schedule, listen-shopping, write-a-shopping + write-b-seasons, 2 speaking prompts).
3. `content/a2/exam/mock-3.yaml` — third A2 mock (read-a2-itinerary, listen-a2-directions-transport, write-a2-doctor + write-a2-public-transport, 2 speaking prompts).
4. `tests/test_exam.py` — 5 new unit tests for reference validation + 3-blueprint count check.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | exam | The new mock-3 blueprints may reference comprehension sets or writing tasks that don't exist or whose skill doesn't match, causing `_check_references` to reject them at sync time | Sync both levels via API; call GET /exam/blueprints for a1 and a2; verify mock-3 and a2-mock-3 appear with 4 sections each | exam-crammer |
| H2 | exam | End-to-end mock flow for the new blueprints (start -> 4 sections -> finish -> history) may fail if section structure differs from mock-1/mock-2 | Run a full mock flow for mock-3 and a2-mock-3 over HTTP; verify CLB report and history | exam-crammer |
| H3 | exam | _check_references may have false negatives — a dangling id, cross-level ref, or skill mismatch might slip through if the check has an off-by-one or logic gap | Craft requests with deliberately bad blueprint data (dangling comprehension id, cross-level writing task, skill mismatch) and verify the validator rejects them. The unit tests cover this, but probe via API too (e.g. what happens if sync is called with bad content?) | edge-case-breaker |
| H4 | exam | Existing mock-1/mock-2 flows may regress — the new loader code runs on every load path including sync, so a bug in _check_references could break previously-valid blueprints | Run full mock flow for mock-1 (already tested in test suite, but verify over live HTTP); check mock-2 loads | exam-crammer |
| H5 | exam | The new cross-module imports (assessment.loader, comprehension.loader) in exam/loader.py may create import cycles or slow down startup | Check app health; verify no import errors in test output; check if there's a circular import path | edge-case-breaker |
| H6 | content | The 4 new speaking prompts may have French quality issues — wrong register for level, missing accents, non-TEF-realistic scenarios | Review prompts in mock-3.yaml files for linguistic accuracy, level-appropriateness, TEF realism | exam-crammer |
| H7 | exam | Edge cases in the mock flow — starting mock-3 while another mock is in-progress, finishing without all sections, double-finishing — may behave differently for mock-3 than mock-1 | Try resume semantics, early finish, double-finish with mock-3 | edge-case-breaker |

## Coverage gaps
- No prior QA issue touches `_check_references` (brand new code).
- mock-3 and a2-mock-3 have never been exercised over HTTP outside the unit tests.
- Speaking prompts have no automated quality check.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 380-389): chase H1, H2, H4, H6 — verify the new mocks load, run end-to-end, produce correct CLB reports, and that existing mocks still work. Review French quality of speaking prompts.
- `edge-case-breaker` (ids 390-399): chase H3, H5, H7 — probe validation edge cases (dangling refs, cross-level refs, skill mismatches via API), check for import issues, and test mock-3 edge cases (resume, early finish, concurrent sections).

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 007 negative elapsed_seconds — rejected
- 030 re-recording section overwrites — rejected (by design)
- 050 client-reported scores — deferred
- 071 no-replay re-fetch — rejected
- 102 clb_estimate out-of-range — rejected (clamped by design)
- 131 password max length — deferred
- 180 answer key in feedback — rejected
- 181 locked lesson readable — deferred
- 221 comprehension threshold hidden — deferred
- 251 history ignores level param — deferred
- 290 SRS negative limit — deferred
- 300 vocab boolean coercion — rejected
- 320 reuseExistingServer — deferred
- 330 spec comment email — rejected
- 370 writing tasks not synced — done (fixed)
- 371 target vocab off-theme — rejected
- Drill / Writing / Speaking 503 with no provider — expected
