# QA round 052 — plan

- date: 2026-08-09
- app under test: http://127.0.0.1:8091 (backend + built SPA, single origin).
  Port 9000 was occupied by an unrelated stray colima/ssh port-forward (an
  "Options Scanner" app on this laptop) — not our app, left untouched. DB:
  `data/tef.db` (sqlite, relative to repo root). No LLM provider is reachable
  from this machine (`ollama` isn't running here) — any code path that must
  make a real model call will 503 via the app's `AllProvidersFailedError` ->
  503 handler. That's expected (matches prior rounds' "no provider" note) and
  is NOT itself a bug to file. Design hypotheses/probes to be provider-independent
  where possible; where a real call is unavoidable, only check for a clean 503
  and no partial/corrupt state — not the generated content itself.
- scope: branch feat/vocab-forms-examples (be094c4) — word forms + on-demand
  example sentences on personal ("My deck") vocab cards.

## Change surface (highest risk first)
- `app/content/forms.py` (new): `generate_forms` (cached profile, skips LLM
  entirely for non-{noun,verb,adjective} pos), `generate_examples` (uncached,
  temp 0.9, `avoid` list), `merge_examples` (dedup by fr case-insensitive, cap
  MAX_EXAMPLE_HISTORY=6, newest first).
- `app/content/personal_api.py` `POST /vocab/personal/forms` and
  `POST /vocab/personal/examples` — brand new endpoints, zero issue history.
- `app/ai/router.py` — profile-level response cache: on a cache hit, `cost_usd`
  is zeroed but `input_tokens`/`output_tokens` are NOT (`_result_from_cache`,
  lines ~140-155) — a cache hit still bills full token usage to the caller's
  daily budget via `add_usage`. This is pre-existing router behavior (also used
  by `vocab_enrich`), not new to this slice, but the new `forms` endpoint's own
  app-level cache check interacts with it (see H1).
- `migrations/versions/0019_vocab_forms_examples.py`, `app/content/tables.py`
  — nullable JSON `forms`/`examples` columns on `user_vocab`.
- `web/src/screens/WordDetail.tsx` (new) — lazy expand, forms fetched once,
  examples fetched fresh every press; `web/src/screens/MyDeck.tsx` renders it.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | forms cache check | `card_forms` checks `if card.forms:` to decide "already generated, free" — but an **empty list is falsy in Python**, so a card whose persisted `forms` is `[]` (any non-inflecting pos: adverb/preposition/etc., or a rare malformed-parse on an inflecting pos) never reports `cached: true` and re-enters the budget-check branch on *every* call, forever. Concretely reproducible without a provider: add a card with pos not in {noun,verb,adjective} (e.g. "adverb"), call `/forms` twice — expect second call to say "already know: free, cached" but it re-runs the (no-op) budget check and can return `over_budget: true` for a word that was already known to cost zero, instead of the correct free empty-forms answer. | edge-case-breaker (curl) |
| H2 | forms over-budget gate, non-inflecting pos | Seed `daily_usage` (feature='vocab', input+output >= `vocab_daily_token_budget`=20000) directly in `data/tef.db` for the test user, then call `/vocab/personal/forms` on an already-added non-inflecting-pos card. Expect (per docstring intent) the known-empty forms answer, no LLM call needed — but per H1's bug, the endpoint will likely return `{forms: [], over_budget: true}`, masking a legitimately free/known answer behind an incorrect over-budget response. | edge-case-breaker (curl, direct sqlite seed) |
| H3 | examples over-budget gate | Same seeded-over-budget setup; call `/vocab/personal/examples` on any card. Confirm response is `{examples: <existing history unchanged>, over_budget: true}` and that `card.examples` in the DB is provably untouched (not cleared, not partially mutated) — i.e. the existing-history-preserved contract in the docstring actually holds. | edge-case-breaker |
| H4 | 404 / ownership | Both `/forms` and `/examples` 404 on an unknown `card_key`; and a second user's token can't fetch/mutate the first user's card via either endpoint (cross-account `card_key` guess) — should 404, not leak/mutate. | edge-case-breaker |
| H5 | degenerate input | `card_key` field is `min_length=1, max_length=64` on `CardBody` — probe empty string, whitespace-only, a 65-char string, and a well-formed but nonexistent key; confirm clean 422/404, no 500. | edge-case-breaker |
| H6 | provider-down path | With no provider reachable, call `/forms` on an **inflecting**-pos card (forces a real `router.run`) and `/examples` on any card. Expect clean 503 (not 500), and confirm via `GET /vocab/personal` that the card's `forms`/`examples` and `daily_usage` are unchanged after the 503 (no partial commit/billing on a failed call). | edge-case-breaker |
| H7 | merge_examples dedup/cap | Not directly exercisable without a live provider generating real sentences — **defer to unit-test read**: confirm `tests/` already covers dedup-by-fr-casefold and the 6-item cap (`app/content/forms.py::merge_examples`) with edge cases like an all-duplicate fresh batch collapsing to no-op, and that fresh sentences win ties (prepended) over older stored ones. If coverage is thin, note as a gap rather than trying to force it live. | edge-case-breaker (code/test read, not live call) |
| H8 | frontend lazy fetch | `WordDetail.tsx` mirrors the same falsy-empty-array trap client-side: `useState<WordForm[] | null>(card.forms?.length ? card.forms : null)` — a card with a persisted-but-empty forms array starts with `forms === null`, so `expand()` re-fires the forms fetch every time the panel is opened, for a non-inflecting-pos card that (per H1) will just re-hit the same broken cache-vs-budget path. Also check: expanding an inflecting-pos card while the backend 503s (no provider) shows a plain "No forms for this word." (mapped from the catch-all) rather than a clear "couldn't load" — verify the panel doesn't get stuck on "Loading forms…" forever, and that examples "Get examples" gracefully shows something sane (not a silent freeze) on the 503. | qa-browser-tester |
| H9 | frontend rendering | Expand panel for a real noun/verb/adjective card (pos set) and a non-inflecting card (pos empty/adverb): forms section only renders when `inflects(pos)` is true (matches backend skip) — confirm no "Forms" section/heading appears at all for a non-inflecting card, only the Examples section; confirm the expand toggle label, button state transitions ("✨ Get examples" -> "🔄 New example" once history exists), and layout hold up at a narrow viewport (this app has a history of 320px overflow bugs — issue 530). | qa-browser-tester |

## Coverage gaps
- `/vocab/personal/forms` and `/vocab/personal/examples` are brand new — zero
  prior issue history, first round to touch them at all.
- No existing issue has probed the AI router's own cache (`cache: true` on
  `vocab_forms`) interacting with per-user token budgets — H1/H2 is the first look.
- `merge_examples`'s dedup/cap logic (H7) has no integration coverage plan here
  since it needs real generated sentences; note whatever the unit tests already
  cover rather than leaving it silently unchecked.

## Charters (per tester, with id blocks)
- `qa-tester` (edge-case-breaker) — ids 660–669: chase H1–H6. Sign up/login
  (invite `friend-001`), add a non-inflecting-pos card (e.g. `POST /vocab/personal`
  with an adverb-like word, or add any card then directly `UPDATE user_vocab SET
  pos='adverb' WHERE card_key=...` in `data/tef.db` if enrichment doesn't reliably
  tag pos) and an inflecting-pos card. Exercise `/forms` and `/examples` normally,
  then seed `daily_usage` via sqlite3 to force over-budget and re-test both
  endpoints (H2/H3), verifying DB state before/after with direct sqlite reads.
  Check 404 (H4), degenerate `card_key` (H5), and the inflecting-pos 503 path (H6)
  confirming no partial billing/persistence. Also skim `tests/` for `merge_examples`
  coverage (H7) and note gaps rather than trying to force live generation.
- `qa-browser-tester` (edge-case-breaker or returning-learner styling) — ids
  670–679: chase H8, H9. Add a card via the UI (or reuse a seeded account),
  open My Deck, expand "Forms & examples" on both an inflecting-pos and a
  non-inflecting-pos card, and on a card where the backend will 503 (no
  provider) — confirm no infinite spinner, no console error left unhandled,
  and check layout at 320px width.

## Don't re-file (already settled)
- 610/611 (whitespace/degenerate `fr`, card_key length clamp) — already fixed;
  don't re-test those exact reproduction steps, though H5's `card_key` field
  probes on `/forms`/`/examples` are a *different* surface (existing-key lookup,
  not creation) so are in scope.
- Drill / Writing / Speaking / this-round's-forms-or-examples-on-inflecting-pos
  503 with no provider reachable on this machine — expected, not a bug (see H6:
  only file if the 503 leaves corrupted/partial state, not for the 503 itself).
- 300 vocab "known" accepts string bool — unrelated area, already triaged.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
