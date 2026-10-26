---
id: 868
title: Personal vocab card's stale pre-fix IPA is never overwritten by a later (working) voicing
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
Code-level check (no HTTP — `TTS_BACKEND=disabled` on this server, so the write path
can't be observed live; a working-TTS code path is required to see the bug).
Standalone script at `/tmp/qa059/h7_stale_ipa_check.py`, run with
`/tmp/tef312/bin/python /tmp/qa059/h7_stale_ipa_check.py` (throwaway sqlite DB in
`/tmp`, no edits to `tests/test_personal_vocab.py` or any app source file):

1. Build the real FastAPI app (`app.main.create_app`) with DI overrides for
   `get_session`/`get_current_user`/`get_ai_router`/`get_storage`, mirroring
   `tests/test_personal_vocab.py`'s `_client` helper.
2. Seed a `UserVocab` row via the real `app.content.personal.add_personal()` for
   `fr="horrible"`, then set `row.ipa = "hɒrəbəl"` directly and commit — simulating a
   card added **before** this PR's fix, under the old code path that stored an
   LLM-guessed, English-shaped, wrong IPA straight from the model (exactly the PR's
   own repro example, issue 832).
3. Call the real route `GET /vocab/personal/audio/<card_key>` with a working
   Piper-like fake TTS (`synthesize_ipa` returns the **correct** French IPA for
   "horrible", `"ɔʁibl"`) — this exercises the real `app/content/personal_api.py::
   _serve_audio` code path end to end.
4. Re-fetch the row from the DB and compare `row.ipa` before vs. after.

## Expected
Per the PR's own description ("filled on first voicing"), a card's `ipa` field should
end up holding the correct, Piper-voiced IPA once a working TTS backend voices it —
regardless of whether the field happened to already hold some other (wrong) value.

## Actual
```
BEFORE first voicing: row.ipa = 'hɒrəbəl', row.audio_key = None
GET /vocab/personal/audio/uv:horrible -> 200
AFTER first voicing:  row.ipa = 'hɒrəbəl', row.audio_key = 'uservocab/999/1.wav'
TTS.synthesize_ipa was called: 1 time(s) (correct IPA it would have reported: 'ɔʁibl')
```
`row.ipa` is unchanged after the voicing — the audio itself synthesizes and caches
correctly (`audio_key` gets set, TTS is called once), but the stale IPA is never
replaced with the correct one the same TTS call just produced.

## Notes
This is the H7 hypothesis from `qa/rounds/059-plan.md`. Root cause (code-read,
`app/content/personal_api.py::_serve_audio`, last line before `return`):
```python
row.ipa = row.ipa or ipa[:64]
```
This only fills `ipa` when the field is currently falsy/empty — `x or y` short-circuits
as soon as `x` is truthy, so any row with ANY pre-existing non-empty `ipa` (stale,
wrong, or otherwise) is permanently excluded from ever being corrected by a later
voicing, even with a fully-working TTS backend. This directly contradicts "filled on
first voicing" for the specific case this PR was meant to remediate: existing personal
cards added under the old pre-832-fix code, which is exactly where a stale wrong IPA
would already be sitting. Contrast with the sibling code path
`app/content/lookup.py::fresh_lookup` (shared `vocab_lookup` cache), which sets
`row.ipa = ipa[:64]` **unconditionally** when `tts is not None` — that path does not
have this bug; only the personal-card (`user_vocab`) path does.

## Triage
- Explanation: confirmed by code read and by running the provided repro script's
  pattern. `app/content/personal_api.py::_serve_audio`'s `row.ipa = row.ipa or
  ipa[:64]` is a short-circuit `or` that fills `ipa` only when currently falsy, so
  any row that already holds a truthy value — whether correct or stale — is never
  touched again. The sibling `app/content/lookup.py::fresh_lookup` path (also edited
  by this PR's diff, see `git show 686cebd -- app/content/lookup.py`) sets
  `row.ipa = ipa[:64]` unconditionally whenever `tts is not None`, with no guard at
  all — a deliberately different shape for what both paths are nominally doing
  (fill the IPA once Piper can voice it).
- Intent check: no comment, test, or PR description language anywhere supports the
  `or` guard being a deliberate "protect a user-entered/edited IPA" design choice —
  there is no UI feature for a learner to manually edit a personal card's IPA (the
  `AddBody.ipa` field exists for the add-flow payload only, always populated by
  `enrich`/`lookup`, never by a learner-facing edit control). The function's own
  docstring frames the intent narrowly as "a row with no IPA yet... gets the IPA that
  run voiced" — i.e. the author was thinking about the empty case this PR's own fix
  produces for *new* cards, not about correcting stale data from *before* the fix.
  The `git show` diff context (`_serve_audio`'s existing lazy-TTS docstring, extended
  only with that one no-IPA-yet sentence) supports this reading: nothing was removed
  or reasoned about regarding pre-existing truthy IPA. This reads as an oversight, not
  an intentional protection.
- Against spec: the PR description itself states IPA is "filled on first voicing when
  no TTS backend was available at add time" — unqualified by whether the field is
  already (wrongly) populated. The `or` guard directly contradicts that framing for
  exactly the population of rows (pre-832-fix personal cards) where it matters most.
- Verdict: validated
- Rationale: this is the one piece of 686cebd's diff that is not purely additive — a
  real, permanent-staleness bug on existing production data, not a hypothetical: the
  live box has been running since before 832 shipped, so personal cards with
  LLM-guessed English-shaped IPA already exist and will never self-heal under this
  code, contradicting the PR's own stated behavior. The fix is a one-line change to
  match the already-correct sibling path (`row.ipa = ipa[:64]` unconditionally, or at
  minimum re-voice-and-overwrite whenever a working TTS actually ran), bringing
  `_serve_audio` in line with `fresh_lookup`'s existing unconditional-overwrite
  behavior.

## Critic
- Challenge: before accepting "this is an oversight," check whether the `or`
  guard could be deliberate for a reason the report didn't consider — idempotency
  (don't re-synthesize/re-write on every audio request), concurrent-request
  safety (avoid two overlapping requests racing to overwrite `row.ipa`), or some
  other code path reading `row.ipa` that would break if it changed under it.
- Holds up? Yes, it's an oversight, not a deliberate guard. Re-read
  `_serve_audio` end to end: the `or` guard doesn't buy idempotency — the real
  idempotency check is `if row.audio_key: ... return` a few lines above, which
  already short-circuits the whole synthesize-and-write block (including the
  `row.ipa` line) on every call after the first. By the time `row.ipa = row.ipa
  or ipa[:64]` executes at all, the function has *already* decided to re-run TTS
  this call (cache miss or `audio_key` lookup failed) — so there's no
  idempotency story left for the `or` to protect; an unconditional overwrite at
  that point just records the IPA this specific synthesis run actually produced,
  which is strictly more accurate than whatever was there before. No concurrency
  mechanism either — the function holds no lock, and `session.commit()` is a
  plain write; a second concurrent request would race on `audio_key`/`ipa`
  identically whether the guard is `or` or unconditional, so the guard doesn't
  add safety. No other read site treats `row.ipa` as sticky/user-owned: grep
  confirms `UserVocab.ipa` has no learner-facing edit endpoint, and
  `lookup_payload`-equivalent personal-card serialization just echoes whatever
  value is there. The sibling `fresh_lookup` path (same PR, same IPA-filling
  intent, unconditional `row.ipa = ipa[:64]`) is the control case: same author,
  same PR, same semantic goal, no guard — strong evidence the guard in
  `_serve_audio` is simply inconsistent with its own sibling, not intentionally
  different.
- Final verdict: validated

## Fix
`app/content/personal_api.py::_serve_audio` now overwrites `row.ipa` unconditionally
whenever the TTS run produces an IPA (`if ipa: row.ipa = ipa[:64]`), replacing the
`row.ipa = row.ipa or ipa[:64]` short-circuit that permanently excluded any row with
an existing (possibly stale/wrong) IPA from ever being corrected — matching the
sibling `app/content/lookup.py::fresh_lookup` path's unconditional overwrite.
- Files: `app/content/personal_api.py`
- Tests: `tests/test_personal_vocab.py::test_stale_ipa_is_overwritten_on_next_voicing`
