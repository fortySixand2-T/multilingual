---
id: 1086
title: "peut etre" (space) does not match the course word peut-être and gets a different gloss than "peut-etre"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"peut-etre"} then {"word":"peut etre"} (both slug peut_etre).

## Expected
Same result for both spellings: in_course a1, en "maybe", audio /content/audio/a1/audio/peut_etre.mp3.

## Actual
peut-etre -> {"en":"maybe","gender_source":"course","in_course":"a1", audio a1 course mp3}. "peut etre" -> {"en":"maybe, perhaps","gender_source":"","audio_url":"/vocab/personal/lookup-audio/peut_etre"} (no in_course; a fresh LLM lookup and a separate TTS file for a word already in the course). Same for "Rez-De-Chaussée" etc. is fine; only space-for-hyphen differs.

## Notes
find_content_match appears to key on the typed spelling rather than the slug. A learner typing without the hyphen gets a duplicate personal card instead of being told it is in the course.

## Triage
- Explanation: find_content_match (app/speech/vocab_review.py:176) compares _deaccent(_norm(word)) to the content fr; _deaccent folds accents but not hyphen vs space, so 'peut etre' != 'peut-etre'. Hence no in_course, a separate LLM lookup and TTS file. Deterministic; not from #133.
- Against spec: Course words should be recognised rather than duplicated (find_content_match docstring). Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real but low: duplicate personal card for a course word. Fix: normalise hyphens/apostrophes to spaces in the match key on both sides.

## Critic
- Challenge: Rare input and not from #133. But 'peut etre' (no hyphen, no accent) is a very natural way to type it; live preview returns a fresh LLM lookup ('maybe, perhaps') instead of the course match, and from-word would mint a duplicate personal card (find_content_match docstring says it must not). Cause confirmed: _deaccent folds accents only, not hyphens.
- Holds up? Yes, low severity: normalise '-' (and apostrophes) to space in the match key on both sides; slug already treats them the same.
- Final verdict: validated

## Fix
Fix: app/speech/vocab_review.py — find_content_match uses _match_key (hyphen as space) on both sides. Tests: tests/test_personal_vocab.py
