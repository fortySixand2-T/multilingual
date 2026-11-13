---
id: 1176
title: My deck preview: course match drops typed accents, so sur returns sûr (sure) and mûr returns mur (wall)
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"sur"}; then {"word":"mûr"}; then {"word":"cote"}.

## Expected
"sur" is the preposition "on"; "mûr" is "ripe/mature" (not "wall"); an accent the learner typed explicitly must not be ignored. "cote" should not silently become "côté" without noting "côte" (coast/rib) exists.

## Actual
- "sur" -> in_course a2, {"fr":"sûr","en":"sure; safe","pos":"adjective"}  (the preposition sur, a top-20 word, is unreachable)
- "sûr" -> same (correct)
- "mur" and "mûr" -> both {"fr":"mur","en":"wall","pos":"noun"}, in_course a2. Typing the accented "mûr" (ripe) returns "wall".
- "cote" -> {"fr":"côté","en":"side"} in_course a2.
Same word entered with the accent gets the wrong word and a card that is "in your reviews already", so the learner cannot add the one they meant.

## Notes
find_content_match (app/speech/vocab_review.py) folds accents on both sides and picks one course card. Prefer exact accent match first, and for accentless input prefer the more frequent word (Lexique).

## Triage
- Explanation: Reproduced on scratch: sur -> in_course a2 'sûr'; mûr -> course 'mur' wall; d'accord -> course 'accord'. personal_api.preview runs find_content_match (vocab_review._match_key = deaccent + hyphen->space) before any lookup and returns the first folded match, ignoring typed accents; d'accord is also reduced to accord by the article/elision strip.
- Against spec: Plan/QA 890 treat accent folding as a convenience for accentless typing, not for overriding accents the learner typed.
- Verdict: validated
- Rationale: Real, medium: top-frequency sur is unreachable and mûr yields 'wall'. PRIMARY for course-match accent folding (1148 closed as duplicate). FIX LOCATION: runtime find_content_match: prefer exact accented match; fold only when the typed form has no accents AND no exact word exists (use Lexique frequency among candidates); do not strip d'/l' when the remainder changes the word (d'accord, phrase list).

## Critic
- Challenge: Course folding is a convenience for accentless typing.
- Holds up? Survives. 'sur' (top-20 preposition) is unreachable and the typed accent in 'mûr' is ignored, returning 'wall': wrong word returned. Fix: prefer exact accented match first; fold only when no exact word exists. Include the d'accord elision case from 1148 (strip d'/l' only when the exact form is not itself a word).
- Final verdict: validated

## Fix
- `app/speech/vocab_review.py` `find_content_match`: exact spelling first; typed accents are never folded away (mûr is not mur); accentless input folds only when the typed spelling is not the commoner word by Lexique (sur is not sûr); d'accord is not accord. Test: `tests/test_personal_vocab.py`.
