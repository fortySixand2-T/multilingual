# QA round 050 — plan

- date: 2026-08-05
- app under test: single-origin backend+SPA at http://127.0.0.1:8091 (branch
  `feat/speaking-rich-tier`, commit b507e22, not yet PR'd)
- scope: Slice 3c — Speaking rich tier (spoken words not in the content bank →
  dictionary-enriched → added to the learner's personal deck)

## Environment constraint (read first)
No LLM is configured on this box → any endpoint that calls the model returns a clean
503. The happy paths (`POST /speech/session/{id}/vocab-review` returning real
`new_words`, `POST /vocab/personal/from-word` actually enriching) are **not**
end-to-end-testable over HTTP here. Do not file the 503s as bugs. Focus on: the
budget-gate short-circuit (no LLM call, no 503, clean JSON), auth, scoping, and the
pure-logic pieces (`resolve_new_words`) via code + existing unit tests, plus browser
UI states that don't require a live conversation.

## Change surface (highest risk first)
Diff vs. previous slice (`git show b507e22 --stat`):
- `app/speech/vocab_review.py` — new `resolve_new_words()` (rich-tier lemma resolution)
- `app/speech/api.py` — `session_vocab_review` now also returns `new_words`
- `app/content/personal_api.py` — new `POST /vocab/personal/from-word` (enrich + add +
  seed SRS, budget-gated)
- `web/src/screens/Speaking.tsx` — new "New words for your deck" section in
  `SessionReview` (states: adding/added/limit/error)
- `web/src/api.ts` — `new_words?`/`over_budget?` on the vocab-review response type,
  `personalAddFromWord()`

Regression hotspots from history on this exact surface:
- #580 (round pre-050, `done`): `session_vocab_review` originally had **no** daily
  "speaking"-budget check — unbounded free LLM calls. Fixed by porting the
  `tokens_used_today >= daily_budget` guard from `SpeakingExaminer.turn`. **3c's new
  `new_words` field rides the same endpoint — must confirm the fix still holds and
  that `new_words` degrades sanely (omitted key, not a crash) when over budget.**
- #610/#611 (`done`): `add_personal`/`personal_key` used to mint degenerate `uv:` card
  keys for whitespace-only `fr` and overflow the 64-char column for long `fr`. Fixed
  via `normalize_lemma()` raising `EmptyLemmaError` → 422, and `personal_key()`
  clamping the slug length. **`from-word` and `resolve_new_words` both funnel through
  `personal_key()`/`add_personal()` — must confirm the fix's protection carries
  through this new call path, not just the original `/vocab/personal` POST.**

## Recon already done during planning (informs charters below — testers should still
independently verify, not just trust this)
Read `app/speech/vocab_review.py`, `app/content/personal.py`, `app/content/personal_api.py`,
`app/content/enrich.py`, and probed the live API directly (curl, plus two DB
one-liners to seed `daily_usage` rows) as user id 182:
- `resolve_new_words` cannot return a word that's also in `candidates`: it drops any
  lemma whose deaccented form is in the content-bank set *before* the owned/dup check,
  same deaccent-normalization convention `resolve_to_vocab` uses. No overlap found by
  inspection — **H3 below looks refuted, but hand to a tester to double-check with a
  constructed case** (e.g. an accented vs. unaccented spoken variant).
- `POST /vocab/personal/from-word`: unauthenticated → 401 (confirmed). Seeded
  `daily_usage(user=182, feature="vocab")` to 30000 (default budget 20000) → returned
  `{"card":null,"added":false,"over_budget":true}` HTTP 200, **no 503**, and
  `GET /vocab/personal` for that user stayed empty — the gate short-circuits before
  the enrich() call as designed. Confirmed with `word:"   "` too (budget gate fires
  before any lemma validation, so no wasted call on garbage input while over budget).
- `POST /vocab/personal` (existing Slice E path, unaffected by 3c) still works
  end-to-end (non-LLM) and is correctly scoped per-user (second signed-up user's
  `GET /vocab/personal` came back empty).
- `POST /speech/session/{id}/vocab-review`: seeded a real `SpeechTurn` row directly,
  then seeded `daily_usage(feature="speaking")` over `speaking_daily_token_budget`
  (60000) → returned `{"candidates":[],"over_budget":true}` HTTP 200, no LLM call.
  Confirms #580's fix is intact under 3c. Note: this branch (and the empty-session
  branch) omits the `new_words` key entirely rather than returning `new_words: []`;
  `web/src/api.ts` types it optional and `Speaking.tsx` does `res.new_words ?? []`,
  so this isn't a UI bug, just a minor API-shape inconsistency worth a tester's eyes
  (H4).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content | `from-word` / `resolve_new_words` reintroduce a #610/#611-style degenerate or oversized `uv:` card key via a path the original fix didn't cover (e.g. a spoken lemma with leading/trailing punctuation the LLM might emit, or a very long lemma) | construct `from-word` calls (budget available, expect 503 from missing LLM — but if reachable, check the pre-LLM validation order) and read `enrich()`/`add_personal()` call order for whether garbage lemmas get billed before being rejected | edge-case-breaker |
| H2 | content | `from-word`'s budget gate can be bypassed or miscounted — e.g. exactly-at-threshold (`used == budget`), or budget checked against the wrong feature/user | seed `daily_usage` to exactly `vocab_daily_token_budget - 1` and to exactly the budget for two different users; confirm gate fires only for the right user at the right boundary | edge-case-breaker |
| H3 | speech | a word can appear in **both** `candidates` and `new_words` in the same vocab-review response (dedup logic gap between `resolve_to_vocab` and `resolve_new_words`) | construct a scenario where a spoken lemma matches content only loosely (accent-insensitive) vs. exactly, or where the same lemma appears twice with different casing/accents in the extracted word list; also read `tests/test_speech.py::test_vocab_review_new_words_rich_tier` for existing coverage and look for an untested variant | edge-case-breaker |
| H4 | speech | frontend mishandles the `new_words` key being entirely absent (over-budget / empty-session branches) vs. present-but-empty — could show a stale word list from a prior successful call if `SessionReview` doesn't reset state between debrief fetches | drive `/speech` end-to-end in browser: trigger a debrief once (gets whatever it gets, likely 503-driven error state), and check state resets correctly if `finish()` is called again (e.g. via "last session" nudge) | qa-browser-tester |
| H5 | web | Speaking screen renders without console errors / layout breakage on load, and `/my-deck` (personal deck list) renders the API-added `chat noir` personal card correctly (gender/pos blank, audio button present) | log in as the seeded user, visit `/my-deck` and `/speech`, check console + rendering | qa-browser-tester |
| H6 | content | `from-word` called directly (bypassing the Speaking UI's `resolve_new_words` filter) with a word that's *already* a content-bank word creates a redundant personal card duplicating a real content card (no server-side content-bank check in `add_from_word`) — defense-in-depth gap, not exercised by the intended UI flow | if budget/LLM allow, POST `/vocab/personal/from-word {"word":"chat"}` where "chat" is a real content word, see if it creates `uv:chat` alongside the content `chat` card; otherwise reason from code (`add_from_word` never queries `ContentVocab`) | edge-case-breaker |

## Coverage gaps (LLM-blocked, cannot be closed this round)
- `resolve_new_words`'s actual extraction-to-suggestion behavior with a *real* LLM
  transcript (word capping at 6, ordering, interaction with the 10-word extraction cap)
  — covered by `tests/test_speech.py::test_vocab_review_new_words_rich_tier` only.
- `from-word`'s real enrich-and-add happy path, and its "New words for your deck"
  one-click UI (adding/added states) — needs a live LLM to populate `new_words` and
  the enrich result. Covered by `tests/test_personal_vocab.py::test_from_word_*`
  (faked router) only.

## Charters (per tester, with id blocks)
- `qa-tester` "edge-case-breaker" (ids 620–629): API/curl testing of H1, H2, H3, H6.
  Log in with invite code `friend-001` or `friend-002` (both valid). Seed
  `daily_usage` rows directly via a short python one-liner against `data/tef.db`
  using `app.usage.service.add_usage` (see recon section above for the exact
  pattern) — don't guess at the schema. Do NOT file the LLM 503s as bugs; they are
  expected given no provider is configured. Focus on gate correctness, boundary
  values, cross-user isolation, and reading `resolve_new_words`/`add_personal` for the
  dedup and validation-order questions H1/H3/H6 raise.
- `qa-browser-tester` "edge-case-breaker" (ids 630–639): drive the real UI for H4, H5.
  Sign up/log in via the UI (invite code `friend-001` or `friend-002`), visit
  `/speech` and `/my-deck`, check the console for errors, and attempt to reach the
  "New words for your deck" section (expect it to fail gracefully behind a 503 debrief
  — that's expected, note it as a coverage gap rather than forcing it). Confirm no
  broken/blank screens, no stale word lists across repeated debrief attempts.

## Don't re-file (already settled)
- #580 — `session_vocab_review` unbounded LLM billing — **fixed**, re-verified live
  by the planner this round (see recon above). Don't re-file the same gap; do flag if
  a tester finds the fix regressed.
- #610 — whitespace-only `fr` → degenerate `uv:` card key — **fixed** via
  `normalize_lemma()`/`EmptyLemmaError`. Don't re-file; do check the fix reaches the
  new `from-word` path (H1).
- #611 — long `fr` → oversized `uv:` card key past the 64-char column — **fixed** via
  `personal_key()` slug clamping. Don't re-file; do check the fix reaches `from-word`.
- Drill / Writing / Speaking 503 with no provider configured — expected in this
  environment, not a bug.
- #600, #602 — rejected (Speaking nudge dismiss persistence, `&amp;` entity) — unrelated
  to 3c, out of scope this round.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
