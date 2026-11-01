---
id: 1022
title: Accent-less ligature input (coeur, soeur, oeuf) is not recognised as a course word in preview
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: http://127.0.0.1:9302 (qa062-app), invite qa062-b.
1. POST /vocab/personal/preview {"word":"cœur"} -> in_course a1 (also sœur, œuf).
2. POST /vocab/personal/preview {"word":"coeur"} (also "soeur", "oeuf"; no œ key on most keyboards).
3. Compare with {"word":"velo"}, "hotel", "noel", "grand-mere" which do return in_course.

## Expected
Same in_course result (cœur, a1), no LLM call, nothing to add.

## Actual
Step 2 returns no `in_course`: a fresh LLM lookup `{"fr":"cœur","gender":"m","audio_url":"/vocab/personal/lookup-audio/coeur"}`, and the learner can add a personal duplicate of a course word (card key uv:coeur). Other accent-less course words work, only œ/oe fails.

## Notes
find_content_match `_deaccent` does not fold œ -> oe (lookup.py already has a `_LIGATURES` table for this).

## Triage
- Explanation: find_content_match uses _deaccent (NFD strip) which does not fold ligatures: coeur != cœur. lookup.py already has _LIGATURES for slugs but vocab_review._deaccent does not use it. Confirmed in code.
- Against spec: Course-word recognition should work for keyboard-typed input (as for velo, hotel).
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Low severity (the learner can still type cœur), but the failure creates a duplicate personal card for a course word and no keyboard-friendly way to hit the match; verified _deaccent in speech/vocab_review.py:119 is NFD-strip only, so coeur != cœur, while lookup.py already has _LIGATURES. Fix is one line.
- Holds up? Yes. Fixer scope: make _deaccent fold œ/æ to oe/ae (reuse or move the _LIGATURES table; beware circular imports between lookup.py and speech/vocab_review.py, a small shared constant is fine). Applies to both sides of the comparison so cœur and coeur match. Add test for coeur/soeur/oeuf.
- Final verdict: validated

## Fix
_deaccent in app/speech/vocab_review.py now spells out oe/ae ligatures (own small table, avoids a lookup.py import cycle), so coeur/soeur/oeuf match cœur etc. Test: tests/test_personal_vocab.py::test_course_word_preview_matches_typed_variants_and_has_audio (coeur).
