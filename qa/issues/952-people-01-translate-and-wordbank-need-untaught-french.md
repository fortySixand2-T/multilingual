---
id: 952
title: A1 People 01 asks a beginner to produce French never taught in the lesson
severity: medium
area: content
persona: absolute-beginner
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Reach A1 People 01 (unit "People"), play it through the UI on a phone-width screen.
2. Get to "Translate: What is your name? (formal)" and the word bank "Build: The man is a doctor".

## Expected
Exercises only use words/structures introduced by the lesson (or earlier lessons), or give a hint.

## Actual
The translate needs `quel est votre nom ?` - quel, est, votre are not in `new_vocab` (homme femme garcon gens personne maman papa docteur dame nom age) and no hint is shown; a natural answer (`comment vous appelez-vous`) gets "Not quite" with no answer shown (see 950). The word bank "L'homme est docteur" for "The man is a doctor" drops the article the English has, with no un/une teaching. First attempt scored 6/8 ("Almost there"), pass is 80%, so a true beginner is stuck repeating the lesson. Also the match pairs show the raw gloss "woman; wife" with a semicolon.

## Notes
Same family as existing 755 (lesson-vocab coherence); filing as a new instance in new content.


## Triage
- Explanation: people-01.e7 requires 'quel est votre nom ?' with none of quel/est/votre in new_vocab and no hint; word bank drops the article from the English; pass is 80%.
- Against spec: Lesson should test what it teaches (755 family, but this is a concrete blocker at the A1 entry).
- Verdict: validated
- Rationale: Absolute beginners can be stuck repeating the lesson. Swap e7 for a taught word or add a hint/teach 'nom'; relates to 896 (formal alternatives) and 950 (no answer shown). Raw gloss 'woman; wife' in match is minor.

## Critic
- Challenge: 755 family; widespread.
- Holds up? Concrete A1-entry blocker (quel/est/votre untaught, verified e7 in people-01, no hint). Fix e7 (use a taught word or add hint); 950 helps but does not replace this.
- Final verdict: validated

## Fix
people-01.e7 prompt gives a taught-word hint (quel/est/votre/nom) and accepts 'comment vous appelez-vous'; e6 prompt notes French drops 'a' before a job.
