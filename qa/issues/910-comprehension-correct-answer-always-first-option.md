---
id: 910
title: Comprehension mcq - correct answer is always the first option (never shuffled)
severity: medium
area: comprehension
persona: exam-crammer
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Sign up with invite `qa061-b` on http://127.0.0.1:9301, then `GET /comprehension/sets/read-a2-le-marche-du-samedi` (repeat for the other 7 new reading sets and the 2 other new ones: read-a1-le-nouveau-voisin, read-a1-mon-samedi).
2. Compare `questions[].options` with the answer (from `POST .../submit` results `correct_answer`).
3. Open the same set in the SPA (`web/src/screens/ComprehensionSet.tsx` renders `q.options.map` as received).

## Expected
Option order is varied (server or client shuffles, as `web/src/shuffle.ts` does for lesson mcq) so the key position carries no information.

## Actual
In all 30 questions of the 8 new reading sets the correct answer is `options[0]`, in the order the API returns. Repo-wide, 585 of 589 comprehension questions have the answer first. A test-taker who always taps the first option scores ~100% without reading; a crammer would discover it in one set. Scores/XP/weak-spots on reading sets are therefore meaningless.

## Notes
Systemic (pre-existing pattern, now extended by the new sets). Fix is a shuffle in `_client_view` (`app/comprehension/api.py`) or in `ComprehensionSet.tsx`.


## Triage
- Explanation: comprehension API returns options in authored order and ComprehensionSet.tsx renders as received; no shuffle (unlike lessons via shuffle.ts). Authored keys are all first (585/589).
- Against spec: Exam-prep integrity; lessons already shuffle.
- Verdict: validated
- Rationale: Answer position leaks the key, making reading scores/weak-spots meaningless. Systemic but a one-place fix (server _client_view or client shuffle). Note: also pre-existing.

## Critic
- Challenge: Pre-existing, exam answers possibly meant to be authored order.
- Holds up? Verified api.py:53 returns options as authored, client renders as-is; first-option key makes scoring meaningless. Real learner impact, one-place shuffle fix.
- Final verdict: validated

## Fix
_client_view in app/comprehension/api.py shuffles options per request; grading is by option text so scoring is unchanged. Test in tests/test_comprehension.py.
