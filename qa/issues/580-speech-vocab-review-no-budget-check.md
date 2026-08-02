---
id: 580
title: Speaking vocab-review endpoint has no daily-budget check — unlimited free LLM calls
severity: high
area: speech
persona: edge-case-breaker
status: done
found: 2026-08-01
---

## Steps to reproduce
STT is not configured in this environment, so the real end-to-end flow (record →
`/speech/turn` → `/speech/session/{id}/vocab-review`) can't be driven live. Verified
instead with a focused pytest test using the same fake-router/seed pattern as
`tests/test_speech.py` (dependency-overridden `get_ai_router`, `get_current_user`,
`get_session`, real `app.speech.api.session_vocab_review` code path, no mocking of
the endpoint itself):

1. Seed one `ContentVocab` row and post one `/speech/turn` (with a fake STT/router)
   under `session_id="sess-580-h1"` for user 580.
2. Call `POST /speech/session/sess-580-h1/vocab-review` 8 times back-to-back.
3. Inspect the router's call count and the `DailyUsage(user_id=580, feature="speaking")`
   row after.

Test file added at `tests/test_qa_580_vocab_review.py::test_h1_vocab_review_never_checks_budget_and_bills_every_call`
(scratch QA test, not part of the permanent suite — run with
`/tmp/tef312/bin/python -m pytest tests/test_qa_580_vocab_review.py -k h1 -q -s`).

## Expected
Like `/speech/turn` (which calls `examiner.turn(..., daily_budget=settings.speaking_daily_token_budget)`
and short-circuits with `{"over_budget": true}` *before* touching STT/LLM once the
day's ledger — `tokens_used_today(...) >= daily_budget` — is exceeded, see
`app/speech/examiner.py` lines ~78-81), `POST /speech/session/{id}/vocab-review`
should stop calling the extraction LLM (and stop billing) once the same
`speaking` daily budget is exhausted, returning some clean signal (e.g.
`{"candidates": [], "over_budget": true}` or a 503) instead of silently keeping
going.

## Actual
`session_vocab_review` (`app/speech/api.py`) never reads `tokens_used_today` and
never compares against `settings.speaking_daily_token_budget`. It unconditionally
calls `extract_review_words(ai_router, rows)` and then `add_usage(...)` on every
single invocation. In the test:

- All 8 repeated calls returned `200 OK`.
- The fake router was hit exactly once per call (plus once for the seeding
  `/speech/turn`) — 9 total LLM calls, none refused.
- The `DailyUsage` row for `(user=580, day=today, feature="speaking")` grew every
  time, ending at `9 * 1500 = 13500` input+output tokens, with nothing capping it.

Because the endpoint's own docstring says it's "re-runnable for a past session_id,"
a user (or a buggy/looping client) can call this endpoint indefinitely against any
of their own past sessions, and each call re-runs the extraction LLM and re-bills —
there is no limit at all, unlike every other metered speaking feature.

## Notes
- Root cause: `app/speech/api.py::session_vocab_review` is missing the same
  budget-check pattern used in `app/speech/examiner.py::SpeakingExaminer.turn`
  (`used = await tokens_used_today(...); if used >= daily_budget: ...`).
- This is specifically about `session_vocab_review`'s own missing guard — not the
  same issue as #240 (writing word-count validation), which is a different feature/
  different kind of check.
- Verified there's no other guard catching this (no rate limiter, no router/provider-level
  cap observed in `app/speech/api.py` or `app/ai/router.py` call path) — the gap is real.
- Severity: high, not blocker, since it requires the LLM/STT stack to be actually
  configured (the persona's environment doesn't hit this financially today), but it
  is a genuine unbounded-cost/abuse vector once Speaking is live in production.

## Triage

**Verdict: validated.**

1. **Real and reproducible.** Ran the scratch test myself:
   `/tmp/tef312/bin/python -m pytest tests/test_qa_580_vocab_review.py -k h1 -q -s`
   → 1 passed. Output confirms the report exactly: all 8 back-to-back calls to
   `/speech/session/{id}/vocab-review` returned `200`, the fake router was hit 9
   times total (1 seed turn + 8 review calls, one LLM call each), and the
   `DailyUsage` row for `(user=580, feature="speaking")` grew unbounded to
   `13500` tokens with nothing capping it. Read `app/speech/api.py`
   (`session_vocab_review`, lines ~206-246): it calls
   `extract_review_words(ai_router, rows)` and then unconditionally
   `add_usage(...)` — no `tokens_used_today` read, no comparison against any
   budget, before either the LLM call or the billing call. Read
   `app/speech/examiner.py::SpeakingExaminer.turn` (lines ~76-81): it has the
   exact guard this endpoint lacks — `used = await tokens_used_today(...); if
   used >= daily_budget: return TurnResult(True, ...)` — computed *before* the
   STT/LLM call, so `/speech/turn` never bills past the cap. Confirmed
   `app/speech/api.py` passes `daily_budget=settings.speaking_daily_token_budget`
   into that `turn()` call (line ~149), so the budget setting exists and is
   already wired for the sibling endpoint — it's simply not consulted here.

2. **In scope.** This is a brand-new endpoint (Slice 3a, vocab-review-from-
   transcript) shipped alongside `/speech/turn`, which already established the
   project's pattern for gating LLM spend on `settings.speaking_daily_token_budget`.
   The new endpoint bills the same `"speaking"` ledger but has no such gate, and
   its own docstring advertises it as "re-runnable for a past session_id" —
   i.e., the unlimited-recall behavior is intentional product behavior, but the
   missing cost cap on top of it is not. This is a straightforward parity gap
   with an already-established pattern in the same module, not a design
   question — fixing it means reusing the existing `tokens_used_today` /
   `daily_budget` helper the same way `examiner.turn` already does, no new
   architecture required.

3. **Severity: confirmed high, not raised to blocker.** It's an unbounded-cost
   vector — any authenticated user (or a buggy/looping client, since the
   endpoint is designed to be safely re-called) can redrive the extraction LLM
   indefinitely against any of their own past sessions with zero cap, unlike
   every other metered speaking feature. That's a real abuse/billing-risk
   surface once a paid LLM provider is behind this in production. It's not
   blocker-severity because (a) it doesn't corrupt data, break other users, or
   affect correctness of the returned candidates, and (b) per scope caveat
   below, the current deployment has no live financial exposure yet — high is
   the right level, not critical/blocker.

## Critic

**Verdict: validated (concur with pm).**

Independently re-verified rather than rubber-stamping:

1. **Code confirmed.** Read `app/speech/api.py::session_vocab_review` (lines
   205-246): it queries `SpeechTurn` rows, calls `extract_review_words(ai_router,
   rows)`, and unconditionally calls `add_usage(...)` on every invocation with a
   non-null `result` — no `tokens_used_today` read anywhere in the function, no
   comparison against `settings.speaking_daily_token_budget`, no early return.
   Read `app/speech/examiner.py::SpeakingExaminer.turn` (lines 61-91): the guard
   is exactly as described — `used = await tokens_used_today(session, user_id,
   _FEATURE, today); if used >= daily_budget: return TurnResult(True, ...)`,
   evaluated *before* the STT/LLM call at line 79-81. `speech_turn` in
   `app/speech/api.py` (line 149) wires `daily_budget=settings.speaking_daily_token_budget`
   into that call, confirming the setting and pattern both already exist and
   are simply not reused in the sibling endpoint. The gap is real, not a
   misreading of the code.

2. **Test confirmed independently.** Ran
   `/tmp/tef312/bin/python -m pytest tests/test_qa_580_vocab_review.py -k h1 -q -s`
   myself: `1 passed`. Captured output matches the report verbatim — all 8
   calls returned `200`, router hit 9 times total (1 seed turn + 8 review
   calls), `DailyUsage(user_id=580, feature="speaking")` grew unbounded to
   `13500` tokens with nothing capping it.

3. **Docstring argument considered and rejected as a defense.** The endpoint's
   docstring says it's "re-runnable for a past session_id" specifically to
   justify *re-reading old transcripts* (so a later slice can resurface "words
   from your last conversation") — that's a statement about data-access scope,
   not a statement about cost. Nothing in the docstring, the surrounding
   comments, or the commit history addresses billing at all; the missing guard
   reads as an oversight (endpoint added without porting the budget check),
   not a considered decision to exempt this LLM call from the ledger cap that
   every other speaking feature respects. Re-runnability and cost-capping are
   orthogonal — you can gate the LLM call while still allowing the endpoint to
   be called again for the same `session_id` once the budget resets tomorrow;
   fixing this does not need to touch or weaken the re-runnable behavior at
   all. So the "maybe intentional" reading doesn't hold up against the code
   pattern the same module already establishes for the near-identical
   `/speech/turn` case.

4. **In scope, real bug, not a duplicate/covered case.** Distinct from #240
   (word-count validation) as the reporter notes. It's the same PR's own
   author establishing a budget-check convention (`examiner.turn`) and then
   not applying it to a second LLM-billing code path added in the same slice —
   a straightforward parity/completeness gap, not a design question requiring
   product input.

5. **Severity: high is correct, not raised or lowered.** Unbounded-cost/abuse
   vector once a real paid provider sits behind this, but zero *current*
   financial exposure since STT is unconfigured in this environment — matches
   the reporter's and pm's reasoning. No data corruption, no cross-user impact,
   no correctness issue with returned candidates, so blocker/critical is not
   warranted; high correctly reflects "must fix before Speaking goes to
   production, not urgent today."

**Final status: validated** — independently reproduced (code read + test run),
in scope, not a false positive, not already covered elsewhere, severity
confirmed at high.

4. **Scope caveat: correct and already well-flagged by the reporter.** This
   only translates into real dollars once Speaking is live against an actual
   paid LLM provider (STT is unconfigured in this environment today per the
   issue's own repro notes). That changes *urgency* (no fire today) but not
   *validity* — the code path is exercised and demonstrably unbounded right
   now via direct API calls with any STT/router configured, and the project is
   explicitly mid-build on shipping Speaking to production (per repo history:
   "faster response" tuning commit just landed). Shipping without this guard
   means the very first production day is exposed. Recommend fixing before (or
   concurrently with) taking Speaking live, not deferring past that point.

## Fix

Ported the exact daily-budget gate that `SpeakingExaminer.turn` already uses
(`used = await tokens_used_today(...); if used >= daily_budget: ...`) into
`session_vocab_review`, so it no longer bills the `"speaking"` ledger without limit.

- `app/speech/api.py::session_vocab_review` — added a `settings: Settings =
  Depends(get_settings)` param, imported `tokens_used_today` from
  `app.usage.service`, and inserted a check (after the empty-session early
  return, before `extract_review_words` is called) that reads today's
  `"speaking"` usage and, if it's already `>= settings.speaking_daily_token_budget`,
  returns `{"candidates": [], "over_budget": True}` immediately — no LLM call,
  no `add_usage` call.
- `web/src/api.ts` — widened `speechVocabReview`'s response type to
  `{ candidates: VocabCandidate[]; over_budget?: boolean }` so the frontend can
  see the new field.
- `web/src/screens/Speaking.tsx` (`SessionReview`) — tracks `overBudget` from
  the response and, when true, shows "You've reached today's speaking-practice
  limit. Come back tomorrow to review words from this conversation." instead
  of the normal empty/candidates states.
- `tests/test_speech.py` — added
  `test_vocab_review_over_budget_skips_llm_and_stops_billing`: seeds a real
  turn (via `FakeRouter`, before exhausting the ledger), sets the `DailyUsage`
  row for `(user, today, "speaking")` to exactly `speaking_daily_token_budget`,
  then calls `/speech/session/{id}/vocab-review` with a `BoomRouter` (raises if
  invoked). Asserts the response is `{"candidates": [], "over_budget": True}`
  and that the `DailyUsage` row is unchanged (nothing re-billed).
- `tests/test_qa_580_vocab_review.py` — deleted. It was a scratch QA
  demonstration file; its own H1 repro (8 calls × 1500 tokens = 12000, well
  under the default 60000 budget) never actually crosses the new cap, so it
  can't demonstrate the fix either way, and the new permanent regression test
  above supersedes its purpose. H2-H4 in that file were about unrelated,
  already-refuted hypotheses (session isolation, resolve_to_vocab edge cases,
  session-id-less turns) and are not budget-related.

Verified: `/tmp/tef312/bin/python -m pytest -q` → 244 passed, 1 skipped (up
from 243 passed before this change). `ruff check .` and `ruff format --check .`
clean on the touched files (two unrelated pre-existing files need reformatting,
untouched by this fix). Frontend: `npx tsc --noEmit` clean, `npx vitest run` →
37 passed (10 files), including `src/screens/Speaking.test.tsx`.
