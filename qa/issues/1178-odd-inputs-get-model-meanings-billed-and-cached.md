---
id: 1178
title: My deck preview accepts digits, repeated letters, whole sentences and ligature glyphs as words, bills model tokens, and caches them for everyone
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview with each of: "12345", 80 x "a", "je suis content", "Je Suis Content", "ﬁn" (U+FB01 ligature), "é".
2. POST /vocab/personal/from-word {"word":"12345"}.
3. Preview "n".

## Expected
Non-words (digits, multi-word phrases, gibberish) get a 422 "Couldn't find a meaning" without spending the model budget or entering the shared cache; a ligature glyph folds to the letters it represents.

## Actual (no 500s anywhere; empty/whitespace/emoji/"!!!"/"l'"/"ß" give clean 422s; 81 chars gives a pydantic 422 list)
- "12345" -> 200 {"fr":"12345","en":"12345","pos":""}; from-word adds card uv:12345 (en "12345") with a review seeded.
- 80 x "a" -> 200 {"en":"repetition","pos":"noun"}
- "je suis content" -> 200 {"en":"I am happy","pos":"verb"} (a phrase typed as a "verb"); "Je Suis Content" hits the same row.
- "ﬁn" -> {"fr":"ﬁn","en":"end"} stored under slug "n"; then previewing "n" returns "ﬁn / end".
- "123abc", "<b>x</b>", "'; DROP TABLE ...", "../../etc/passwd" -> 422 (fine) but each costs ~320 model tokens before failing (~2000 tokens for the series).
Each junk lookup consumed ~320 input tokens from the learner daily budget (daily_usage rows).

## Notes
Cheap pre-filters (must contain a letter, no digits, single token or known phrase) would avoid the spend.

## Triage
- Explanation: Reproduced by reading lookup path: preview/from-word have no pre-filter; '12345' gets a model call (~320 input tokens billed to the learner's daily vocab budget) and is cached shared; 'ﬁn' (U+FB01) is not NFKC-normalised so slug folds to 'n'; lookup_slug handles only œ/æ ligatures.
- Against spec: Daily vocab budget exists to bound model spend; plan expects 'Couldn't find a meaning' for non-words.
- Verdict: validated
- Rationale: Low severity (no crash, small spend) but it pollutes the shared cache with junk cards and a digits-only 'word' can become a card. FIX LOCATION: runtime lookup/personal_api: NFKC-normalise input, require letters and no digits, single token or known hyphen/apostrophe phrase before any model call.

## Critic
- Challenge: No crash, small token spend bounded by the daily budget; the user who types digits only hurts themselves.
- Holds up? Holds, narrowly. The shared cache is polluted (ﬁn stored under slug n, 12345 becomes a card) and it is two cheap guards: NFKC-normalise and require a letter / no digits before any model call. Do not add phrase detection or other heuristics.
- Final verdict: validated

## Fix
- `app/content/personal.py` `normalize_lemma`: NFKC-normalises and rejects input with digits before any model call; `app/content/personal_api.py`: request words are NFKC-normalised (ﬁn -> fin). No phrase detection (critic scope).
