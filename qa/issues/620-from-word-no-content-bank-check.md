---
id: 620
title: POST /vocab/personal/from-word never checks the content bank, so a caller can mint a `uv:` personal card that duplicates a real content-vocab word
severity: medium
area: content
persona: edge-case-breaker
status: done

## Triage
- Explanation: `POST /vocab/personal/from-word` (`app/content/personal_api.py::add_from_word`)
  calls `enrich()` then `add_personal()` directly; neither touches `ContentVocab`.
  `add_personal` (`app/content/personal.py`) only dedupes against the caller's own
  `UserVocab` rows via `personal_key()`. By contrast, the *intended* UI feeder
  `resolve_new_words` (`app/speech/vocab_review.py:171`) explicitly builds a
  deaccented-`fr` set from `ContentVocab` and drops any lemma already in it before
  ever returning it to the client. Verified live: `cuisiner` is a genuine
  `content_vocab` row (`id=fr='cuisiner'`), and `add_from_word` has no equivalent
  filter on its own path — confirmed by reading both call graphs; end-to-end mint of
  a duplicate `uv:cuisiner` card couldn't be driven on this box since it has no LLM
  configured (enrich() 503s before `add_personal` — matches the round-050 plan's
  documented constraint).
- Against spec: unspecified explicitly, but the Slice 3c intent (round plan, Speaking
  rich tier) is "words spoken that aren't already in the bank" — the whole reason
  `resolve_new_words` exists is to guarantee that invariant for the Speaking flow.
  `from-word` is a public authenticated primitive reachable independent of that
  guard, so the invariant silently doesn't hold for direct callers.
- Verdict: validated
- Rationale: Any authenticated caller (curl/devtools/modified client, not just the
  stock UI) hitting `from-word` with a word that's already in the content bank gets a
  second, unmerged `uv:`-prefixed SRS card duplicating the real content card — same
  lemma reviewed twice as if it were different vocabulary, with no error or warning.
  Low severity (requires bypassing the UI, no data loss/security impact) but cheap to
  close: reuse the same `_norm`/`_deaccent` content-membership check
  `resolve_new_words` already has, in `add_from_word` (or `add_personal`) before
  minting the `uv:` key.
found: 2026-08-05
---

## Steps to reproduce
1. Sign up / log in, get a bearer token.
2. Pick any word that's already a real content-bank vocab item, e.g. `cuisiner`
   (confirmed present via `ContentVocab` — id `cuisiner`, `fr: "cuisiner"`).
3. `POST /vocab/personal/from-word {"word": "cuisiner"}` directly (bypassing the
   Speaking UI's "New words for your deck" section, which only ever offers lemmas
   `resolve_new_words()` has already filtered against the content bank).
4. On a box with an LLM configured, this call would succeed (enrich `cuisiner` and
   call `add_personal`); on this box it 503s at the LLM step, but the code path up to
   that point — and `add_personal` itself — is fully reachable and never touches
   `ContentVocab`.

## Expected
Either the endpoint checks the content bank before minting a personal card (matching
what the *intended* UI flow already guarantees via `resolve_new_words`), or it's
documented/accepted that `/vocab/personal/from-word` is a raw, unchecked primitive.
Ideally: reject/short-circuit words that already resolve to a `ContentVocab` entry
(same `_norm`/`_deaccent` matching `resolve_to_vocab` and `resolve_new_words` already
use), or at least dedupe against it, since the caller now ends up with two SRS cards
for the same word — `cuisiner` (content) and `uv:cuisiner` (personal) — reviewed as if
they were different vocabulary.

## Actual
Read `app/content/personal_api.py::add_from_word`: it calls `enrich()` then
`add_personal()` directly. Neither function nor any code on this path ever queries
`ContentVocab`. `app/content/personal.py::add_personal` only dedupes against the
caller's own `UserVocab` rows (via `personal_key()`), not against the shared content
bank. So any authenticated user who calls `/vocab/personal/from-word` directly (curl,
devtools, a modified client — not just the stock Speaking UI) with a word that's
already in the content bank gets a second, independent `uv:`-prefixed SRS card for
the same lemma, sitting alongside (and never merged with) the real content card. This
is silent — no error, no warning that the word is already trackable via the shared
bank.

## Notes
- The *intended* UI flow (Speaking → "New words for your deck") never exposes this,
  because `resolve_new_words()` (in `app/speech/vocab_review.py`) already filters out
  any lemma whose deaccented normalized form is in the content bank before it's ever
  offered to the client. So this is not reachable through normal Speaking-screen use
  — only via calling the raw endpoint out of band.
- Filing as `medium`, not `high`: it requires deliberately bypassing the UI (curl/
  devtools), doesn't corrupt data or leak cross-user info, and the practical impact is
  "confusing duplicate SRS card," not data loss or a security issue. Still worth
  closing since `add_personal`/`add_from_word` is a public authenticated endpoint and
  the fix is cheap (reuse the same `_norm`/`_deaccent` content-membership check
  `resolve_new_words` already has).
- Could not verify the full happy path end-to-end on this box (no LLM configured, so
  `enrich()` 503s before `add_personal` is reached) — confirmed via code reading that
  `add_from_word` → `add_personal` never queries `ContentVocab`, and confirmed via a
  live DB query that `cuisiner` is a real content-bank id/lemma this would collide
  with.

## Critic
- Challenge: The strongest case for no change: `from-word` is only ever called by the
  Speaking UI's "New words for your deck" button, whose entire input set is produced
  by `resolve_new_words` — which already excludes anything in `ContentVocab` before the
  client sees it. Every stock code path is safe. Reaching the bug requires a learner to
  open devtools/curl and hand-craft a request with a word the UI never offered — that's
  self-inflicted tampering, not something a real learner does by using the product. The
  fix (bolting a second content-bank check onto a route that's supposed to be a thin
  "enrich+store" primitive) adds a second copy of the `_norm`/`_deaccent` filtering
  logic for a scenario nobody hits organically — arguably against the "fix only what's
  actually an issue" bar.
- Holds up? Partially, but not enough to overturn. I independently read all three files:
  `add_from_word` (`personal_api.py:125-166`) calls `enrich()` then `add_personal()`
  directly with zero `ContentVocab` reference; `add_personal` (`personal.py:76-113`)
  only dedupes against the caller's own `UserVocab` rows; `resolve_new_words`
  (`vocab_review.py:171-202`) explicitly builds the deaccented `ContentVocab` set and
  drops any match before ever returning candidates to the client. The PM's read of the
  code is accurate — no dispute there. Where the "self-inflicted" argument is weaker
  than for e.g. a forged auth token: this isn't out-of-band tampering with protocol
  internals, it's an authenticated user calling a real, documented, server-side
  endpoint with a value inside its own declared schema (`word: str`). Any user with
  devtools open (not a sophisticated attacker) can trigger it in seconds, and the
  round-050 plan itself flagged this as H6 during planning — it's not a stretch case
  invented after the fact. The consequence (duplicate, unmerged SRS cards for the same
  lemma, reviewed twice, no error) is a real, if minor, data-integrity/UX defect, and
  the fix is a one-line reuse of logic that already exists on the sibling code path —
  not "added complexity" so much as closing a gap between two flows that are supposed
  to share an invariant. Severity: agree `medium` is roughly right, if anything on the
  high side of what "requires the UI to be bypassed" issues usually get — leaving it as
  filed rather than downgrading, since the fix is cheap enough that severity precision
  doesn't change the outcome.
- Final verdict: validated

## Fix
- Added `find_content_match(session, word)` to `app/speech/vocab_review.py`, reusing
  the existing `_norm`/`_deaccent` normalization helpers that `resolve_new_words`
  already uses to filter the content bank — it looks up a word against `ContentVocab`
  with the same matching rules, rather than duplicating that logic.
- `app/content/personal_api.py::add_from_word` now calls `find_content_match` after
  enrichment (using the enriched `result.fr`, matching what would be stored) and, if
  it resolves to an existing `ContentVocab` row, commits any billed usage and raises a
  422 ("word is already in the content bank") — following the same pattern as the
  function's existing "couldn't look that word up" / "word has no letters" guard
  clauses, rather than the `over_budget` structured-field pattern (this is a rejection
  of the input, not an expected steady-state like budget exhaustion, and the Speaking
  UI's `addNew` already treats any thrown/non-2xx call as an `"error"` state via its
  existing try/catch, so no frontend change was needed).
- Added `test_from_word_rejects_word_already_in_content_bank` to
  `tests/test_personal_vocab.py`: seeds a `ContentVocab` row for `cuisiner`, posts it
  to `/vocab/personal/from-word`, and asserts a 422 with no `uv:cuisiner` card created
  in the personal deck or SRS queue. Confirmed existing `test_from_word_*` tests still
  pass.
- Verification: `/tmp/tef312/bin/python -m pytest -q` (285 passed, 1 skipped),
  `/tmp/tef312/bin/python -m ruff check app/ tests/` (all checks passed),
  `/tmp/tef312/bin/python -m ruff format --check app/ tests/` (132 files already
  formatted). No frontend files were touched, so `npm run build` was not run.
