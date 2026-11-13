---
id: 1181
title: Accentless typing of ambiguous words silently picks one spelling (peche, eleve, pate, repere, releve) with no hint of the other
severity: low
area: content
persona: edge-case-breaker
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. Preview "peche", "eleve", "pate", "repere", "releve" (also over budget).

## Expected
Since the app knows several words match, show the chosen spelling prominently and offer the alternative (péché "sin", élevé "high", pâté, repère, relevé), or prefer the more common one.

## Actual
- peche -> pêche "peach, fishing, angling" (péché not offered; peche is very commonly meant as "sin" by learners)
- eleve -> élève "schoolboy, pupil, schoolchild" (élevé "high/raised" not offered)
- pate -> pâte (pâté not offered); costs a model call each time it is uncached
- repere (over budget, no model) -> "repéré / marked, spotted", an adjective, when the noun repère (landmark) is the likelier word; releve -> relève "changing, changeover" not relevé.
The user adds a card with the preview spelling and cannot tell another word existed.

## Notes
dictionary.ambiguous() + respell; low severity. Healing checks passed: same-pos-only (pos noun row stays noun; mousse noun/verb row untouched), rows without dictionary entries untouched, user_vocab card keeps edited meaning ("hammer (my edit)") after later previews; a re-add with a different edit silently returns added:false with the old text (by design, but unannounced).

## Triage
- Explanation: By design: enrich.enrich uses dictionary.ambiguous() then the model + respell (Lexique frequency) to pick one spelling; pêche for 'peche' is the QA 1101 intent. The preview shows the chosen spelling in fr.
- Against spec: QA 890/1002 prefer the most common accent variant; no spec for showing alternatives.
- Verdict: deferred
- Rationale: Enhancement (offer alternatives such as péché), not a defect. Low; defer to a later My deck polish slice. The over-budget 'repere -> repéré adjective' is a frequency pick, same family.

## Critic
- Challenge: Enhancement (show alternatives), not a defect.
- Holds up? Deferral holds.
- Final verdict: deferred
