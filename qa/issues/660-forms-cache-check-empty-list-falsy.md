---
id: 660
title: "`/vocab/personal/forms` cache check treats persisted empty forms as \"never generated\", so a non-inflecting-pos card wrongly returns `over_budget: true` when the vocab budget is exhausted, even though its answer (no forms) is already known and free"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-08-09
---

## Steps to reproduce
1. Sign up / log in (invite `friend-001`), get a bearer token.
2. Add a personal card with a non-inflecting part of speech (adverb, preposition,
   etc. — anything not in `{noun, verb, adjective}`):
   ```
   POST /vocab/personal
   {"fr":"vite","en":"quickly","gender":"","pos":"adverb","ipa":"","source":"manual"}
   ```
   -> `card_key = "uv:vite"`.
3. Call `POST /vocab/personal/forms {"card_key":"uv:vite"}` — first call, correctly
   returns `{"forms":[],"cached":false}` (no LLM call needed for this pos, per
   `generate_forms`'s early-return). The card's `forms` column is persisted as `[]`.
4. Call the SAME endpoint with the SAME `card_key` again (second, third, ... calls),
   while still under budget — response is `{"forms":[],"cached":false}` **every
   single time**, never `cached: true`, even though the card's `forms` was already
   persisted as `[]` on the previous call and nothing changed.
5. Seed the daily `vocab` usage budget to the cap for this user directly in
   `data/tef.db` (matching the server's local-timezone date, not sqlite's UTC
   `date('now')` — see Notes):
   ```sql
   INSERT OR REPLACE INTO daily_usage (user_id, day, feature, input_tokens, output_tokens)
   VALUES (197, '2026-08-09', 'vocab', 20000, 0);
   ```
6. Call `POST /vocab/personal/forms {"card_key":"uv:vite"}` again (same card, same
   non-inflecting pos, now over budget).

## Expected
Per the endpoint's own docstring/comment intent ("already generated — free, no
model call" / "persist even when empty so we don't retry a non-inflecting word"),
a card whose forms were already determined (even if the determination was "this
word has no forms") should short-circuit to a free, cached answer and never need
to re-check — let alone fail — the budget gate. Expected response at step 6:
`{"forms": [], "cached": true}` (or equivalent), never blocked by budget.

## Actual
- Step 4: response is `{"forms":[],"cached":false}` on every repeated call —
  `cached` never becomes `true` for this card, forever, because the code's cache
  check is `if card.forms: return {..., cached: True}` and `[]` is falsy in
  Python, so a persisted-but-empty `forms` list is indistinguishable from
  "never attempted."
- Step 6 (the concrete user-facing failure): response is
  ```json
  {"forms":[],"over_budget":true}
  ```
  incorrectly reporting the call as blocked by the daily budget, when the correct
  answer (no forms for an adverb) was already known and should have cost nothing.
  A learner who has already used up their daily vocab budget and re-opens a
  non-inflecting-pos card in "My Deck" will see a budget-exhausted message for a
  request that should never have touched the budget check at all — confusing and
  incorrect UX.

## Notes
- Root cause: `app/content/personal_api.py::card_forms`, line ~203:
  `if card.forms:  # already generated — free, no model call` — should
  distinguish "never generated" (`card.forms is None`) from "generated and
  empty" (`card.forms == []`), e.g. `if card.forms is not None:`.
- Confirmed the DB column really does persist `[]` (not `NULL`) after the first
  call: `sqlite3 data/tef.db "SELECT card_key, pos, forms FROM user_vocab WHERE
  card_key='uv:vite';"` -> `uv:vite|adverb|[]`.
- Aside (test-setup gotcha, not a bug): sqlite's `date('now')` is UTC while the
  running server's `date.today()` is local time — they differed by a day on this
  machine (UTC 2026-08-10 vs local 2026-08-09) during testing, which made an
  initial over-budget seed silently miss the day bucket the app actually reads.
  Worth remembering for future rounds seeding `daily_usage` by date.
- Same bug likely affects any card where `generate_forms`'s LLM call returns
  zero parseable forms for an inflecting pos (malformed model reply) — that
  card would also be re-billed/re-attempted forever, or show `over_budget` once
  the budget is exhausted, instead of caching the (odd but real) empty result.
- H3 (examples over-budget preserves history), H4 (404/ownership on unknown or
  cross-account `card_key`), H5 (degenerate `card_key` — empty/whitespace/65-char),
  and H6 (503 on provider-down leaves no partial DB write/billing for both
  `/forms` and `/examples`) were all also tested this round and found to work
  correctly — no issues filed for those.

## Triage
- Explanation: Confirmed by direct code + schema read. `app/content/tables.py`
  defines `forms: Mapped[list | None] = mapped_column(JSON, nullable=True)` —
  i.e. the column's "never generated" sentinel is `NULL`/`None`, not `[]`.
  `app/content/personal_api.py::card_forms` (line 203) guards the cache with
  `if card.forms:`, a Python truthy check, so a persisted `[]` (the correct,
  intentional result for any non-inflecting pos, or a rare malformed-parse on
  an inflecting pos — see `card.forms = forms  # persist even when empty so we
  don't retry a non-inflecting word` at line 215, which shows the empty-persist
  behavior is deliberate) is indistinguishable from "never attempted." Every
  repeat call therefore re-enters the budget-check branch (line 206-208)
  instead of short-circuiting, and once the daily `vocab` budget is exhausted
  it returns `{"forms": [], "over_budget": true}` for a request that should
  cost nothing and never touch the budget gate at all. This was pre-identified
  as hypothesis H1/H2 in the round plan (`qa/rounds/052-plan.md`) before
  testing began, and the tester's repro (including DB-column evidence,
  `uv:vite|adverb|[]`) matches the code path exactly — this is not a
  misreading of intended behavior, it's a straightforward None-vs-empty-list
  bug. The frontend has the same-shaped bug (noted as H8, not filed
  separately): `WordDetail.tsx`'s `useState<WordForm[] | null>(card.forms?.length
  ? card.forms : null)` also treats a persisted-but-empty `forms` array as
  "not yet fetched," so opening the panel refetches every time.
- Against spec: The endpoint's own docstring/comment states the intent plainly
  ("generated once and cached on the card — a second request returns the
  stored forms with no LLM call" / "persist even when empty so we don't retry
  a non-inflecting word") — the code doesn't honor its own stated contract.
  Not a spec ambiguity; the implementation contradicts its own comment.
- Verdict: validated
- Rationale: Real, in-scope, one-line-fix bug in this slice's new code. User
  impact: a learner who has exhausted their daily vocab budget and opens (or
  re-opens) a personal card for a non-inflecting part of speech (adverb,
  preposition, conjunction, etc. — a large fraction of real vocab) sees an
  incorrect "budget exhausted" message for an answer that was already known
  and should be free, every time, forever for that card. Fix: change the
  cache guard in `card_forms` to `if card.forms is not None:` (matching the
  column's actual None-vs-[] semantics); the client-side `WordDetail.tsx`
  `card.forms?.length ? card.forms : null` should get the analogous fix
  (`card.forms != null ? card.forms : null` / check `!== undefined`).

## Critic
- Challenge: Best case for "no change needed" would be (a) the empty-list
  persistence is itself a design mistake and the real fix should be "don't
  persist `[]`, leave it `NULL` and re-derive `inflects(pos)` cheaply
  client/server-side each time," making this report's proposed fix
  unnecessary; (b) the budget-gate exposure only manifests once a user
  exhausts their entire daily vocab budget, which may be rare enough to be
  theoretical; (c) fixing it adds an `is not None` branch — marginally more
  cognitive load than a bare truthy check — arguably not worth touching
  working code. Also worth checking whether `TEF_Platform_Technical_Plan.md`
  says anything about vocab-forms caching that would reframe intent.
- Holds up? No. (a) is contradicted by the code itself — line 215's comment
  `# persist even when empty so we don't retry a non-inflecting word` shows
  persisting `[]` is deliberate, not accidental; the bug is that the read
  side (line 203) doesn't honor what the write side intentionally records.
  (b) understates it: this isn't only reached at hard budget exhaustion —
  confirmed by direct code read that *every* repeat call for a non-inflecting
  card returns `cached: false` (never `true`), so the endpoint is silently
  doing wasted round-trip/DB-read work on every open regardless of budget;
  the budget-exhausted case is just the one with visible, incorrect
  user-facing output (`over_budget: true` for a free answer) and is entirely
  reachable through legitimate daily use — no tampering needed except to
  accelerate reproduction in this round. Non-inflecting parts of speech
  (adverbs, prepositions, conjunctions, etc.) are a large, ordinary fraction
  of real vocabulary, not an edge case. (c) is not a real cost — `is not
  None` is exactly as readable as `if card.forms:` and is the idiomatic
  Python way to distinguish "unset" from "empty," not added complexity.
  `TEF_Platform_Technical_Plan.md` has no mention of forms/vocab-budget
  caching, so there's no competing spec intent to weigh — the only "spec" is
  the endpoint's own docstring/comment, which the code contradicts. Verified
  independently against `app/content/tables.py` (`forms: Mapped[list | None]
  = mapped_column(JSON, nullable=True)`) and `app/content/personal_api.py`
  lines 202-217 — the PM's read of both files is accurate, not overstated.
- Final verdict: validated

## Resolution
- Status: done
- Fix: `app/content/personal_api.py::card_forms` — cache guard changed from
  `if card.forms:` to `if card.forms is not None:`, so a persisted empty list
  (deliberately written for non-inflecting parts of speech, or a rare
  malformed-parse on an inflecting one) is now correctly treated as "already
  generated" — free and cached — instead of re-entering the budget-check/
  generation path on every subsequent call.
- Also fixed the mirrored client-side bug noted in triage:
  `web/src/screens/WordDetail.tsx` initialized `forms` state with
  `card.forms?.length ? card.forms : null` (empty array treated as unfetched).
  Changed to `card.forms ?? null` (undefined/never-set is the only "unfetched"
  sentinel now, matching the server's None-vs-`[]` semantics) and the initial
  `formsState` is seeded to `"none"` when the card already carries a
  persisted-empty `forms` array, so the panel shows "No forms for this word."
  immediately instead of refetching on every open.
- Tests added: `tests/test_personal_vocab.py::test_forms_empty_result_is_cached_for_non_inflecting_pos`
  and `::test_forms_cached_empty_result_survives_exhausted_budget` (backend);
  `web/src/screens/WordDetail.test.tsx` — new case "treats a persisted-but-empty
  forms array as already known, not unfetched (qa-660)".
- Verified: `/tmp/tef312/bin/python -m pytest -q` — 313 passed, 1 skipped.
  `cd web && VITE_API_BASE="" npm run build` — clean. `npx vitest run` — 47
  passed (14 files).
