---
id: 911
title: New reading passages contain unnatural French and stray untested sentences
severity: low
area: content
persona: exam-crammer
status: done
found: 2026-10-29
---

## Steps to reproduce
Read the passages (`GET /comprehension/sets/<id>`), content in `content/<lvl>/comprehension/`.

## Expected
Natural, correct French at the stated level.

## Actual
- read-a2-mon-endroit-prefere: "La mer, c'est une autre chose." should be "c'est autre chose"; "Mon ami Marc dit que la mer, c'est meilleur" is odd (natural: "c'est mieux").
- read-a2-les-conseils-de-ma-grand-mere: "Quand tu vas recevoir un cadeau, dis merci." is unnatural (expected "Quand tu reçois un cadeau"); "elles peuvent mourir" after "Ne laisse pas les enfants toucher les plantes" reads as if the children could die.
- read-a2-le-marche-du-samedi: "Mon voisin Paul préfère faire ses courses ailleurs, plutôt au centre commercial." is clumsy (redundant "ailleurs, plutôt").
- read-a1-le-nouveau-voisin: "Quel âge a la petite sœur du garçon ? Elle a deux ans." is a stray self-asked question that no question tests; reads like vocabulary stuffing and breaks the passage flow.
- read-a2-a-velo-en-hiver: "Il ne faut jamais lâcher le guidon avec les deux mains" implies one hand is fine; reads like a literal translation (natural: "des deux mains").

## Notes
Script-generated text: sentences appear to exist to carry target vocabulary rather than to make a coherent text.


## Triage
- Explanation: Script-generated passages with vocabulary stuffing.
- Against spec: Passages should be natural correct French.
- Verdict: validated
- Rationale: 'c'est une autre chose' and 'Quand tu vas recevoir un cadeau' are errors/unnatural; the 'mourir' sentence misleads. Fix the listed sentences (low, text-only).

## Critic
- Challenge: Stylistic nitpicks.
- Holds up? Mostly yes, but 'c'est une autre chose', 'Quand tu vas recevoir', and the 'mourir' ambiguity are real errors/misleading; fix listed sentences only.
- Final verdict: validated

## Fix
Fixed the listed sentences in the five reading passages (mieux, autre chose, reçois, plantes peuvent mourir, plutôt/ailleurs, des deux mains, stray question removed).
