---
id: 1166
title: Lookup returns pos noun with empty gender for some nouns (manœuvre, hors via article)
severity: low
area: content
persona: exam-crammer
status: rejected
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"la manœuvre"}; {"word":"un hors"}.

## Expected
A gender (manœuvre f, or mf/m by sense), or no noun pos.

## Actual
- "la manœuvre" / "le manœuvre" -> noun gender "" "maneuver" (gender_source "")
- "un hors" -> noun "" "outside" (hors is a preposition; noun forced by the article)
Nouns with no gender show a blank gender on the card, so the learner gets no article hint.

## Notes
Model-path words with no table/suffix/dictionary gender.

## Triage
- Explanation: By design: enrich.resolve_gender returns '' when neither Lexique table, suffix rule nor dictionary gives a gender, and the module docstring says unresolved is '(flagged for a human)'. 'un hors' forces noun through the typed article (lexicon.pos) on a word that is a preposition: user error/garbage input.
- Against spec: enrich.py docstring: unresolved gender stays empty rather than guessed.
- Verdict: rejected
- Rationale: Working as designed; a blank gender is more honest than a guess. If manoeuvre/similar gaps matter, add them to fr_gender.tsv as a content request, not a bug.

## Critic
- Challenge: Blank gender is honest; 'un hors' is garbage input.
- Holds up? Rejection holds.
- Final verdict: rejected
