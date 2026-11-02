---
id: 1121
title: read-b2-centre-ville-sans-voitures q1/q2: prompts don't match the text or the options
severity: low
area: comprehension
persona: exam-crammer
status: done
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/read-b2-centre-ville-sans-voitures, questions q1 and q2.

## Expected
Prompt asks what the text actually states; options answer the prompt grammatically.

## Actual
- q1 "Qu'est-ce que l'auteur pouvait craindre au début ?" - the text says "je pensais que personne ne pourrait se passer de sa voiture" (a belief, not a fear); the modal "pouvait craindre" is forced and the option copies the belief verbatim.
- q2 "De quoi l'auteur peut-il se réjouir un an plus tard ?" - options are full clauses ("La fréquentation des commerces a augmenté"), which do not answer a "De quoi..." prompt; and the author never says he rejoices.

## Notes
Proposed: q1 "Que pensait l'auteur au début ?"; q2 "Quel résultat positif l'auteur constate-t-il un an plus tard ?" with options as noun groups ("Une hausse de la fréquentation des commerces").


## Triage
- Explanation: Q2 prompt 'De quoi l'auteur peut-il se réjouir' takes a noun/clause but options are full indicative clauses; the author never says he rejoices.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Q2 is a prompt/option grammatical mismatch; fix per the issue (« Quel résultat positif... » with noun-group options). Q1 'pouvait craindre' is awkward but its subjunctive option does fit 'craindre', so only a minor part; fix both together. Low severity.

## Critic
- Challenge: Q1 'pouvait craindre' is awkward but its subjunctive option fits; Q2 is the real defect: 'De quoi ... se réjouir' with full indicative clauses as answers, and the author never expresses joy. Learners see a prompt/answer grammar mismatch.
- Holds up? yes (Q2 primarily)
- Final verdict: validated
- Note for dev-fixer: Rewrite Q2 prompt + options (noun groups); Q1 prompt to 'Que pensait l'auteur au début ?' only if options and explain are changed consistently. Interacts with 1120 (equalise lengths) and 1116 (q4 untouched).

Fix: content/b2/comprehension/read-b2-centre-ville-sans-voitures.yaml — Q1 'Que pensait l'auteur au début ?', Q2 'Quel résultat positif...' with noun-group options; 'se réjouir' now in the passage.
