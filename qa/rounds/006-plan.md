# QA round 006 — plan

- date: 2026-06-19
- app under test: backend :9000 / SPA :5173
- scope: pressure-test **auth-token security** (expiry, tampering, alg confusion) and
  chase the round-5 concurrency class into the path it *didn't* cover — comprehension
  XP, which (unlike lessons) has no unique guard to catch a double-award race.

## Change surface (highest risk first)
- Round 5 made *lesson* completion concurrency-safe. The sibling write path —
  comprehension first-pass XP — shares the "check prior, then award" shape but has **no
  unique constraint**, so a race would silently double XP instead of 500ing. Top suspect.
- Auth primitives (`create_token`/`verify_token`) are untested end-to-end.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | progress | **Concurrency**: two simultaneous first-pass comprehension submits both miss `prior_pass` and **double-award XP** (no unique guard to stop it) | fresh user, fire 5 parallel correct submits for one set → check xp | edge-case-breaker |
| H2 | auth | JWT is too lax — an **expired**, **tampered**, or **alg=none** token is accepted | craft each and hit `/auth/me` | edge-case-breaker |
| H3 | auth | Email isn't normalized — `Bob@x.com` vs `bob@x.com` (or trailing space) make **near-duplicate accounts**, and login can't find them | sign up two casings, then log in | returning-learner |
| H4 | exam | `clb_estimate` garbage (999, -5) is **silently clamped** into the report instead of rejected | record a writing section with `clb_estimate: 999` | edge-case-breaker |

## Coverage gaps
No issue history: JWT lifecycle, email normalization, comprehension XP under concurrency,
`clb_estimate` bounds. H1 and H2 are the highest-value.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 100–119): chase H1, H2, H4.
- `returning-learner` (ids 120–129): chase H3.

## Don't re-file (already settled)
- 007 negative elapsed, 030 section redo, 071 no-replay — rejected.
- 001 email format, 050 client-graded lessons — deferred.
- 006 gating, 010 board PII, 040 over-time XP, 070 completion race — fixed.
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round)
- **H1 — confirmed → issue 100 (validated → fixed).** Concurrent first-pass submits
  double-awarded XP (5 parallel → xp 75). The lesson fix didn't cover this path — no
  unique guard. Fixed with a `comprehension_passes` marker table (migration 0009) +
  atomic insert-or-ignore.
- **H2 — refuted.** JWT is solid: tampered → 401, forged `alg=none` → 401
  (`algorithms=[ALGO]` pins it), and `exp` is checked by PyJWT.
- **H3 — confirmed → issue 101 (validated → fixed).** Email wasn't normalized; casing
  made duplicate accounts and broke login. Fixed with a shared strip+lower validator.
- **H4 — confirmed → issue 102 (rejected).** `clb_estimate` is clamped, not rejected —
  the gate ruled clamping acceptable (out-of-range, not contradictory like qa-005).

Net: 5 confirmations across 4 hypotheses → 2 fixed (100, 101), 1 rejected (102), 1
refuted (auth security sound). 100 is the round-5 concurrency class striking the path it
missed — now both XP paths are race-safe via insert-or-ignore on a unique key.
