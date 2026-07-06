---
id: 449
title: "WeakSpots /answer endpoint accepts calls on already-resolved spots"
severity: medium
area: backend
persona: edge-case-breaker
status: deferred
found: 2026-07-05
---

## Steps to reproduce
1. Authenticate as user A (`TOKEN_A`).
2. Submit a comprehension set with a wrong answer to create a weak spot (e.g., id=7 for `read-cafe-01.q2`).
3. Dismiss the weak spot:
   ```
   POST /progress/weak-spots/7/dismiss
   ```
   Response: `{"id": 7, "resolved": true}` — spot now resolved.
4. Confirm it's gone from the list:
   ```
   GET /progress/weak-spots  →  {"weak_spots": []}
   ```
5. Now POST a wrong answer directly to the resolved spot:
   ```
   POST /progress/weak-spots/7/answer
   Content-Type: application/json
   {"chosen": "Oui"}
   ```

## Expected
The endpoint should return 404 (or 409) since the weak spot is already resolved and not in the active queue. Accepting calls on resolved spots is confusing — the learner was not presented this card, yet their answer modifies state.

## Actual
Returns HTTP 200:
```json
{"correct": false, "correct_answer": "Non", "explain": "...", "resolved": true}
```
The `times_missed` counter is incremented on the resolved row even though the user never saw the card in the UI. The spot stays resolved (resolved=True) since the code doesn't set `resolved=False` on a wrong answer in `/answer`. However, it silently mutates data the user didn't interact with.

## Notes
- `_owned_weak_spot` only checks `user_id`, not `resolved` status.
- The inverse is also true: a correct answer on a resolved spot returns 200 with `resolved: true` (idempotent, harmless).
- The wrong-answer case silently increments `times_missed` on a resolved row, corrupting the miss count. If that spot is ever re-opened (by a future wrong submit), the count is inflated.
- Affected code: `app/progress/api.py::_owned_weak_spot` — add `or w.resolved` to the 404 guard, or accept this as a soft-state edge (low priority if UX doesn't expose resolved spots).

## Triage
- Explanation: `_owned_weak_spot` in `app/progress/api.py` (line 202–206) only checks `w is None or w.user_id != user_id`. It does not check `w.resolved`. So `POST /weak-spots/{id}/answer` on an already-resolved spot succeeds, calls `w.times_missed += 1` on the wrong-answer branch, and commits. The UI never presents resolved cards (GET filters `resolved.is_(False)`), so this path is only reachable via direct API calls — not through normal app use. The data mutation is real but requires deliberate API abuse; it cannot happen accidentally in the browser.
- Against spec: The spec does not explicitly require a 404 or 409 guard for resolved weak spots on `/answer`. The endpoint's docstring says "Re-answer a missed question" implying active spots only, but no formal AC mandates the guard. The tester's observation is technically correct — the data corruption (inflated `times_missed`) only matters if the spot is later re-opened by a fresh wrong submission, which reuses the same DB row. That is a plausible future scenario but is not a current user-facing path.
- Verdict: deferred
- Rationale: The bug is real (a resolved spot's `times_missed` can be silently inflated via direct API call), but it is not reachable through the UI, and the spec has no AC requiring the guard. Adding `or w.resolved` to `_owned_weak_spot` is a one-line fix, but the product impact today is zero for normal users. Defer to a hardening pass; re-open if the feature is ever exposed to API-level consumers or if re-opening resolved spots becomes a product feature.

## Critic
- Challenge: The fix is literally one line (`or w.resolved` in `_owned_weak_spot`). At that cost, why defer? Silent data corruption — even if only reachable by API abuse — violates the principle of least surprise and could mislead future analytics or debugging. One could argue even low-probability corruption should be blocked cheaply.
- Holds up? Yes — the deferred verdict holds. The "convenient explanation" test is satisfied here: the claim is not that the corruption is impossible to trigger, but that it requires deliberate API manipulation outside the UI. `WeakSpots.tsx` confirms there is no browser-path that calls `/answer` on a resolved card — the UI filters them out at GET time and never renders them. The data corruption risk (inflated `times_missed` if a spot is re-opened) relies on a future feature (re-opening resolved spots) that does not exist. The one-liner cost argument cuts both way: adding it would pass the CLAUDE.md simplicity test, but the project rule is to fix what *actually* harms users, not to speculatively harden. Defer is consistent with that policy; this is not a convenient dismissal of something users will hit.
- Final verdict: deferred
