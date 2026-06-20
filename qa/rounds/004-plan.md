# QA round 004 — plan

- date: 2026-06-19
- app under test: backend :9000 / SPA :5173
- scope: after the round-3 PII leak, probe **authorization** (can one user read another's
  data?) and **correctness** of the scoring/scheduling logic that earlier rounds never
  exercised (comprehension timing, SRS scheduling, lesson grading trust).

## Change surface (highest risk first)
- Round 3 touched `auth.py` (display_name now required) and the board fallback — low
  regression risk, already covered by tests.
- Untouched, untested logic is the real surface now: comprehension scoring/timing, SRS
  reschedule math, and how much grading the server *trusts the client* for.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | auth | A by-id endpoint leaks **another user's data** (IDOR) — exam attempt / writing submission / speech turn not scoped to the caller | user B `GET /exam/attempts/{A's id}` and `/assessment/submissions/{A's id}` | edge-case-breaker |
| H2 | comprehension | A submission **over the time limit still passes and awards XP** — the limit is advisory (`over_time` flag only), not enforced | submit with `elapsed_seconds` > the set's `time_limit_seconds`, all answers correct | exam-crammer |
| H3 | comprehension | Scoring is wrong — an all-wrong or partial submission mis-scores or wrongly passes | submit all-correct, all-wrong, half → check score/passed | returning-learner |
| H4 | srs | Reschedule is broken — a reviewed card stays in today's `due` queue, or a not-yet-due card is served | seed cards, review one `good`/`easy`, re-check `/srs/queue` | returning-learner |
| H5 | progress | Lesson grading is **fully client-reported** — POST `score:10` passes with no real answers (no server-side check of the exercises) | complete a lesson with a fabricated perfect score | edge-case-breaker |

## Coverage gaps
No issue history: `auth/me`, cross-user access on every `/{id}` route, SRS scheduling,
comprehension timing semantics. H1 and H4 cover the two highest-value gaps.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 040–049): chase H1, H5.
- `exam-crammer` (ids 060–069): chase H2.
- `returning-learner` (ids 050–059): chase H3, H4.

## Don't re-file (already settled)
- 007 negative elapsed — rejected; 001 email — deferred; 030 section redo — rejected.
- 006 gating, 010 board PII — fixed (round 2/3).
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round)
- **H1 — refuted.** Cross-user reads are scoped: B fetching A's exam attempt → 404;
  assessment/speech by-id endpoints check `user_id != user.id` in code. Authz sound.
- **H2 — confirmed → issue 040 (validated → fixed).** Over-time submission passed and
  awarded XP; the `over_time` flag was computed but never acted on.
- **H3 — refuted.** Server-side grading is correct: all-wrong→0/fail, half→0.5/pass.
- **H4 — refuted.** SRS reschedule is correct: `easy`→7 days out and off the queue;
  `again`→short interval (correctly not in the due-now queue).
- **H5 — confirmed → issue 050 (deferred).** Lesson score is client-reported; a
  fabricated perfect score passes. Real but by-design — fixing needs server-side grading,
  disproportionate to a 5-friend trust group. Deferred.

Net: 5 hypotheses → 2 confirmed, 3 refuted; 1 fixed (040), 1 deferred (050). The three
refutations are themselves results — authz, scoring, and SRS scheduling are proven sound.
