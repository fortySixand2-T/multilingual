---
id: 1122
title: read-b2-semaine-de-quatre-jours: "il a fallu parvenir à une présence continue" is forced
severity: low
area: comprehension
persona: exam-crammer
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/read-b2-semaine-de-quatre-jours, paragraph 3.

## Expected
"parvenir à" followed by an infinitive or a result noun.

## Actual
"Dans les services ouverts au public, il a fallu parvenir à une présence continue avec moins de jours travaillés" - a presence is 'assured', not 'reached'; headword "parvenir à" was packed in with a noun. Same paragraph: "L'étude permet d'abord de mettre en évidence un net recul..." is heavy where "L'étude met d'abord en évidence" is the natural form (q2 prompt itself uses the simple form).

## Notes
Proposed: "il a fallu parvenir à assurer une présence continue avec moins de jours travaillés".


## Triage
- Explanation: 'parvenir à' + noun and 'permet de mettre en évidence' are both grammatical.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: 'parvenir à une présence continue' is a stretch but understandable; 'l'étude permet de mettre en évidence' is normal report style at B2. Preference.

## Critic
- Challenge: 'parvenir à une présence continue' is a stretch yet grammatical; 'permet de mettre en évidence' normal report style.
- Holds up? yes
- Final verdict: rejected
