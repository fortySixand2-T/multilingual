---
id: 1116
title: read-b2-centre-ville-sans-voitures: "convaincre de son utilité ceux qui habitent en banlieue" is clumsy and has an ambiguous "son"
severity: medium
area: comprehension
persona: exam-crammer
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/read-b2-centre-ville-sans-voitures, last sentence of the passage.

## Expected
Natural French with a clear antecedent.

## Actual
"L'enjeu est maintenant de convaincre de son utilité ceux qui habitent en banlieue."
The object of "convaincre" is displaced after the "de" complement (headword form "convaincre de" packed in), and "son" has no near antecedent (the last noun is "projet" two sentences earlier; "ville"/"banlieue" are closer). Also, question q4's correct option is a clean rewording ("Convaincre les habitants de la banlieue de l'utilité du projet"), showing the text itself is the awkward one.

## Notes
Proposed replacement: "L'enjeu est maintenant de convaincre les habitants de la banlieue de l'utilité du projet." Then update q4 explain quote and consider rewording the q4 option so it is not a verbatim copy.


## Triage
- Explanation: Syntax is grammatical (heavy-NP shift); 'son' has an adjacent antecedent.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: Reporter's antecedent claim is wrong: the previous sentence ends « en faveur du projet », so 'son utilité' = the project. The inversion is a recognised literary/tribune style at B2. Q4's option is a paraphrase, which is desirable (see 1123). Preference.

## Critic
- Challenge: Reporter's own claim fails: previous sentence ends 'en faveur du projet', so 'son utilité' has an adjacent antecedent. Heavy-NP shift ('convaincre de son utilité ceux qui...') is grammatical tribune style and the paraphrased q4 option is desirable. Rewriting would also force an explain-quote change for no gain.
- Holds up? yes - dismissal survives
- Final verdict: rejected
