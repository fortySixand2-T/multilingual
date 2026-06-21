# QA round 007 — plan

- date: 2026-06-20
- app under test: backend :9000 / SPA :5173
- scope: hunt **missing upper bounds / resource limits**. Past rounds added *lower* bounds
  (min password, non-blank name, score ranges) but never *maximums* — an unbounded string
  is a DoS or abuse vector. Also confirm SRS review is owner-scoped and probe exam attempt
  hygiene.

## Change surface (highest risk first)
- `auth.py` got `min_length`/normalization but **no `max_length`** on `password` or
  `display_name`. Password feeds PBKDF2 (CPU), display_name renders on the shared board.
- No request-size discipline anywhere — writing text, comprehension answers are unbounded.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | auth | **Unbounded password** → a multi-hundred-KB password makes PBKDF2 burn CPU on every signup/login (cheap DoS) | sign up with a 500 KB password, time it vs a normal one | edge-case-breaker |
| H2 | auth | **Unbounded display_name** → a multi-KB name is accepted and rendered to everyone on the group board | sign up with a 20 KB display_name, GET /progress/board | edge-case-breaker |
| H3 | srs | SRS review isn't owner-scoped — you can reschedule someone else's card | as user B, review a card_key user A owns | edge-case-breaker |
| H4 | exam | No "one active attempt" guard — a user can spawn many in-progress attempts of one blueprint, cluttering resume/history | start mock-1 three times, list history | exam-crammer |

## Coverage gaps
No issue history: upper bounds on any string field, request-size limits, exam attempt
lifecycle hygiene. H1/H2 are the highest-value (real, cheap to fix).

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 130–149): chase H1, H2, H3.
- `exam-crammer` (ids 150–159): chase H4.

## Don't re-file (already settled)
- 007 negative elapsed, 030 section redo, 071 no-replay, 102 clb clamp — rejected.
- 001 email format, 050 client-graded lessons — deferred.
- 006 gating, 010 board PII, 040 over-time XP, 070 completion race, 100 comp-XP race,
  101 email normalize — fixed.
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round)
- **H1 — refuted → issue 131 (rejected).** A 500 KB password signs up in ~0.07s (vs
  ~0.05s): PBKDF2 cost is iteration-bound, not length-bound. No DoS.
- **H2 — confirmed → issue 130 (validated → fixed).** A 20 KB display_name rendered on
  the shared board for everyone. Capped at `max_length=80`.
- **H3 — refuted.** SRS review is owner-scoped — reviewing another user's card → 404.
- **H4 — confirmed → issue 150 (validated → fixed).** `start` spawned duplicate
  in-progress attempts; it now resumes the open one.

Net: 4 hypotheses → 2 confirmed/fixed (130, 150), 1 rejected (131), 1 refuted (H3). The
theme paid off — every prior round added *lower* bounds; this one found the missing
*upper* bound that mattered (display_name) and ruled out the one that didn't (password).
