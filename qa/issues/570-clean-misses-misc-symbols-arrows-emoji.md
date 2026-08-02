---
id: 570
title: TTS sanitizer `_clean` leaves emoji outside covered Unicode ranges (e.g. ⭐ U+2B50, ⬆ U+2B06) unstripped
severity: medium
area: speech
persona: edge-case-breaker
status: done
found: 2026-08-01
---

## Steps to reproduce
1. From the repo root, run:
   ```
   /tmp/tef312/bin/python -c "from app.ai.adapters.piper_adapter import _clean; print(repr(_clean('Bravo ⭐ continue ⬆ !')))"
   ```
2. Compare with an emoji that *is* covered, e.g. `_clean("Super 👍 bien joué 😂")`.

## Expected
All emoji/pictograph characters a chatty LLM reply is likely to use are stripped
before the text is handed to Piper for synthesis, so nothing gets voiced literally
or mis-synthesized. `_clean("Bravo ⭐ continue ⬆ !")` should read something like
`'Bravo continue !'`.

## Actual
```
_clean("Bravo ⭐ continue ⬆ !") -> 'Bravo ⭐ continue ⬆ !'
_clean("Super 👍 bien joué 😂")  -> 'Super bien joué'
```
⭐ (U+2B50) and ⬆ (U+2B06) both live in the Miscellaneous Symbols and Arrows block
(U+2B00–U+2BFF), which is not covered by any of the four `_EMOJI` ranges in
`app/ai/adapters/piper_adapter.py`:
```
"\U0001f300-\U0001faff"  # symbols, pictographs, emoji
"\U00002600-\U000027bf"  # misc symbols + dingbats
"\U0001f1e6-\U0001f1ff"  # regional indicators (flags)
"\U00002190-\U000021ff"  # arrows
"\U0000fe00-\U0000fe0f"  # variation selectors
"\U000020e3"             # combining enclosing keycap
```
These two are common in casual chat replies ("Bravo ⭐", "continue comme ça ⬆").
They would sail through to Piper unstripped, which per the module's own docstring
is exactly the "voiced literally or stumbles" failure this sanitizer exists to
prevent.

## Triage
- Explanation: `_EMOJI` in `app/ai/adapters/piper_adapter.py` covers four Unicode
  ranges (pictographs 1F300-1FAFF, misc symbols+dingbats 2600-27BF, flags,
  arrows 2190-21FF, variation selectors) but omits the Miscellaneous Symbols and
  Arrows block (2B00-2BFF), so ⭐ U+2B50 and ⬆ U+2B06 pass through untouched.
  Reproduced directly: `_clean("Bravo ⭐ continue ⬆ !")` → `'Bravo ⭐ continue ⬆
  !'` (verbatim, unstripped) vs. a covered-range emoji which is correctly
  stripped (`_clean("Super 👍 bien joué 😂")` → `'Super bien joué'`).
- Against spec: `examiner.md`/`conversation.md` now instruct the LLM to write
  "plain French prose only... no emoji," so on a compliant turn this is
  unreachable. But `_clean`'s own docstring/comment states its purpose is to
  catch markup/emoji "Piper voices literally or stumbles on" as a safety net
  regardless of what the LLM does — this is exactly the class of gap that
  purpose statement calls out, and 2B00-2BFF is a mainstream emoji block (⭐ ⬆
  ⬇ ⬅ ➡ ✳ etc. all live there), not an obscure one.
- Verdict: validated
- Rationale: Real, easily-triggerable gap in the sanitizer's own stated
  contract (defense-in-depth for non-compliant LLM output); fix is a one-line
  regex range addition (`\U00002b00-\U00002bff`) with negligible risk of
  over-stripping French text. Medium severity as filed — an unstripped emoji
  glyph handed to Piper is more disruptive (undefined synthesis behavior) than
  a stray punctuation mark, but it's not as jarring as a spelled-out URL (571).

## Notes
Fix would be adding `\U00002b00-\U00002bff` (Miscellaneous Symbols and Arrows) to
the `_EMOJI` regex in `app/ai/adapters/piper_adapter.py`. Likely other emoji blocks
worth auditing too (e.g. Supplemental Arrows-C U+1F800-1F8FF is already inside the
0001f300-1faff range so that's fine; Dingbats U+2700-27BF is covered).

## Critic
- Challenge: The prompt explicitly bans emoji ("plain French prose only... no
  emoji"), so a compliant model never triggers this at all — it's a
  defense-in-depth gap for non-compliant output, not a live user-facing bug.
  The technical plan doesn't mandate a complete emoji sanitizer, and "medium"
  severity for one unstripped glyph mid-sentence (Piper likely just skips or
  mangles a single unknown symbol, not a catastrophic failure) looks
  overstated for what's really cosmetic polish on a rare path.
- Holds up? Partially, but not enough to kill it. Reproduced independently:
  `_clean("Bravo ⭐ continue ⬆ !")` → unstripped, byte-for-byte matching the
  report. The self-hosted stack runs a local Ollama model (per project
  config), and habitually decorating replies with stars/arrows even against
  explicit "no emoji" instructions is a well-documented behavior of smaller
  local models — this isn't a contrived/tampered input, it's a realistic
  emission. More importantly, the existing `_EMOJI` regex already deliberately
  covers four separate ranges specifically to catch exactly this class of
  non-compliant output — the author's own design intent was broad emoji
  coverage, so 2B00-2BFF (stars/arrows, one of the more common blocks) is an
  inconsistency in that same intent, not scope creep. Fix is a single added
  range with zero risk to French text. I'd downgrade my confidence in "medium"
  severity (this reads more like low-to-medium — a stray glyph, not a spelled
  URL) but that's not grounds to reject the fix itself.
- Final verdict: validated

## Fix
Added `\U00002b00-\U00002bff` (Miscellaneous Symbols and Arrows) to the `_EMOJI` regex in `app/ai/adapters/piper_adapter.py`, so ⭐/⬆ and the rest of that block are stripped like other emoji ranges. Covered by `test_removes_misc_symbols_and_arrows_emoji` in `tests/test_piper_adapter.py`.
