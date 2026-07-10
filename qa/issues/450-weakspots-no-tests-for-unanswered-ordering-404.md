---
id: 450
title: "WeakSpots: test suite missing coverage for unanswered-as-miss, ordering, and nonexistent-id 404"
severity: medium
area: test
persona: edge-case-breaker
status: fixed
found: 2026-07-05
---

## Steps to reproduce
1. Review `tests/test_comprehension.py` weak-spot tests (lines 275–327).
2. Note three behaviors specified in the feature design but not covered by any test:
   a. **Unanswered-as-miss (H5)**: submitting `{"answers": {}}` should create weak-spots for all questions.
   b. **Ordering (H14)**: `GET /progress/weak-spots` must return most-missed question first.
   c. **Nonexistent-id 404**: `POST /progress/weak-spots/999999/answer` and `/dismiss` must return 404 (not 500).

## Expected
All three behaviors should have automated test coverage, as they are non-trivial code paths:
- The unanswered-as-miss path relies on `body.answers.get(q["id"])` returning `None` → graded wrong.
- Ordering relies on `.order_by(WeakSpot.times_missed.desc())` in the query.
- Nonexistent-id 404 relies on `_owned_weak_spot` returning 404 when `session.get()` returns None.

## Actual
```
tests/test_comprehension.py (weak_spot section):
  - test_weak_spot_captured_on_wrong_and_resolved_on_correct  ✓
  - test_weak_spot_answer_and_dismiss_endpoints               ✓
  - test_weak_spot_wrong_reanswer_keeps_open_and_counts       ✓
  - test_weak_spot_answer_404_for_other_user                  ✓ (cross-user 404)

Missing:
  - test for unanswered questions → weak spots created
  - test for GET ordering by times_missed desc
  - test for /answer with nonexistent id → 404
  - test for /dismiss with nonexistent id → 404
```

## Notes
- The unanswered-as-miss and ordering behaviors were manually verified as working during QA round 037 (H5 and H14 passed), but without automated tests, regressions won't be caught.
- The nonexistent-id 404 was also manually verified as working.
- Severity medium: the behaviors work correctly, but the missing test coverage leaves them unprotected against future regressions.

## Triage
- Explanation: Reviewing `tests/test_comprehension.py` lines 275–327, the four existing weak-spot tests cover: wrong→weak-spot creation + correct→resolve, the `/answer` and `/dismiss` endpoints, wrong re-answer count increment, and cross-user 404. None of the four tests submits an empty answers dict, orders two spots by miss count to verify descending order, or calls `/answer` or `/dismiss` with a non-existent ID to assert 404. The behaviors themselves are confirmed working (manually verified per the issue notes and visible in the `order_by(WeakSpot.times_missed.desc())` in `api.py` and the `_owned_weak_spot` None check). This is a test coverage gap, not a product defect.
- Against spec: The spec has no explicit AC for test coverage levels. CLAUDE.md / memory has no rule mandating coverage thresholds. The qa/README.md workflow requires working behaviors to be confirmed, not that every code path has a dedicated test. Missing tests for verified-working paths are a quality-of-life / safety-net concern, not a spec violation.
- Verdict: deferred
- Rationale: All three behaviors work correctly today; no user-facing defect exists. The test gaps are a regression risk, not a current bug. Adding the three tests is straightforward and worthwhile, but it does not unblock any learner today. Defer to a test-hardening task; re-prioritize if any of these paths are touched in a future refactor.

## Critic
- Challenge: The three uncovered paths are non-trivial: ordering by `times_missed desc` is a deliberate product decision (most-missed first), the nonexistent-id 404 guard is a security boundary, and unanswered-as-miss is a core spec behaviour (H5). The existing 156-test suite gives false confidence that these paths are protected. A refactor could silently remove the `order_by` clause or change the None check and no CI gate would catch it. One could argue these should be validated and fixed now precisely because the cost (three short tests) is negligible and the regression risk is real.
- Holds up? Yes — the deferred verdict holds. The key rule from qa/README.md is that the gate confirms *working behaviors*, not that every code path has a dedicated test. All three behaviors have been manually verified this round (H5 and H14 confirmed, 404 confirmed). No learner is harmed today; no current test is failing; no spec AC is unmet. Upgrading to validated would mean the dev-fixer writes tests for code that already works, which is test-hygiene work, not a bug fix. That is textbook deferred territory. The regression argument is real but speculative — if any of these paths is touched in a future PR, that PR's QA round would catch it. The conservative default (no change) applies.
- Final verdict: deferred
