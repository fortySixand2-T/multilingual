# QA round 017 — plan

- date: 2026-06-23
- app under test: backend :9000 / SPA :5174
- scope: "Add to review" feature (PR #8) — POST /srs/add, in_review flag on GET /content/vocab

## Change surface (highest risk first)
What changed since round 016 (commit 5cd6596):
- `app/srs/api.py` — new POST /srs/add endpoint (AddBody model, calls seed_cards, commits)
- `app/content/api.py` — GET /content/vocab now queries ReviewCard to add `in_review: bool` per card
- `app/content/tables.py` — imports added
- Frontend `Deck.tsx` — "Add to review" action button

The core risk is in the bridge between the vocab deck and the SRS system: new endpoint + new join query.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | idempotency | POST /srs/add twice for the same card_key returns added:false on the 2nd call, no 500 from unique constraint violation | POST twice, check response + DB state | edge-case-breaker |
| H2 | cross-user isolation | User A adding "cafe" to review must NOT make in_review:true for user B on GET /content/vocab | Create 2 users, add with A, check B's vocab | edge-case-breaker |
| H3 | seeded card reviewable | After /srs/add, the card appears in GET /srs/queue (due now) and POST /srs/review on it succeeds | Add then queue then review | returning-learner |
| H4 | in_review accuracy | in_review reflects only the current user's srs_cards; correct for all-levels (no level param) and tag-filtered queries; defaults false for unreviewed cards | Check vocab with/without level, with tag filter | returning-learner |
| H5 | validation / malformed input | Missing, empty, null, or wrong-type card_key in POST /srs/add body returns 422 not 500; no auth returns 401/403 | Send bad bodies, no auth header | edge-case-breaker |
| H6 | non-existent card_key | Arbitrary card_key that doesn't exist in vocab is accepted by /srs/add (no FK), shows in queue with vocab:null | Add "zzz_fake", check queue | edge-case-breaker |
| H7 | interaction with lesson seeding | A word already seeded by lesson completion is not duplicated by /srs/add (returns added:false); FSRS state is not reset | Complete a lesson that seeds, then /srs/add the same key | returning-learner |
| H8 | add-review-re-add cycle | After adding, reviewing (rating "good"), then calling /srs/add again, the FSRS state is preserved (due date not reset) | Full cycle: add -> review -> re-add -> check due | returning-learner |
| H9 | regression: known-marks | POST /content/vocab/known still works correctly alongside in_review | Mark known, check both flags | returning-learner |
| H10 | regression: pytest suite | All existing tests pass (125+) | Run pytest | edge-case-breaker |

## Coverage gaps
- POST /srs/add is brand new — no issue history; primary target.
- in_review join on GET /content/vocab — no prior coverage; primary target.
- Interaction between known-marks and in_review on the same card — untested.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 310-319): chase H1 (idempotency/no 500), H2 (cross-user isolation), H5 (validation), H6 (non-existent key), H10 (pytest regression). Two users needed. Hammer the endpoint with bad inputs, duplicate calls, missing auth.
- `returning-learner` (ids 320-329): chase H3 (seeded card reviewable), H4 (in_review accuracy), H7 (interaction with lesson seeding), H8 (add-review-re-add cycle), H9 (regression: known-marks). Normal user flow: browse vocab, add to review, review it, re-add, check known-marks.

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 006 lesson gating not enforced server-side — rejected/deferred
- 007 comprehension accepts negative elapsed — rejected
- 030 exam section rerecord overwrites — rejected/deferred
- 050 lesson score is client-reported — rejected/deferred
- 071 comprehension no replay not enforced — rejected/deferred
- 102 exam CLB estimate clamped — rejected/deferred
- 130 display-name no max length — existing issue
- 131 password no max length — existing issue
- 180 comprehension feedback reveals answers — deferred
- 181 locked lesson content readable — deferred
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — rejected
- 290 srs queue negative limit bypasses pagination — rejected/deferred
- 300 vocab known accepts string bool — rejected
- Drill / Writing / Speaking 503 with no provider — expected (no LLM configured)
