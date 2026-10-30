---
id: 896
title: "New translate accept lists miss common valid translations (formal 'Comment vous appelez-vous ?', feminine plurals, inversion, 3-pièces)"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Read the exercises, type the alternate valid answer (checked via the client rule
   `norm(val) === norm(a)` over `[answer, ...accept]`: lowercase, whitespace-collapsed, no accent folding).
2. Instances:
   - `a1/people-01.e7` "What is your name?" (formal): only "quel est votre nom ?" accepted. "Comment vous appelez-vous ?" (the standard formal form; `s'appeler` is already taught in `greetings-03`) is rejected.
   - `a2/reflexives-a2-01.e6` "We had fun!": accepts masculine "amusés"/"amusé" only. "On s'est amusées !" / "Nous nous sommes amusées !" (all-female group) rejected; also "On s'est bien amusés".
   - `a2/adjectives-a2-01.e8` "Are you sure?" (to a friend): "Es-tu sûr ?" / "Es-tu sûre ?" rejected (the lesson elsewhere models inversion with "es-tu").
   - `a2/everyday-a2-01.e7` "a three-room apartment (use pièce)": "un trois-pièces", "un appartement de 3 pièces" rejected (digit form is common).
   - `a2/verbs-a2-06.e6` "we shake hands": "nous nous serrons les mains" and "on se serre les mains" rejected.
   - `a2/verbs-a2-02.e7` "keep the change (formal)": "Vous pouvez garder la monnaie" / "Gardez la monnaie." rejected.
   - `a2/verbs-a2-01.e7` "Stop! (to a friend)": "Stop !" (very common) rejected.

## Expected
Natural equivalents of the English prompt are accepted.

## Actual
"Not quite — keep going." for a correct translation; the learner is told they are wrong and the
only feedback is the unaccepted canonical answer.

## Notes
Also cosmetic: several accept lists repeat the answer after lowercasing (e.g. `verbs-a2-03.e7`
"Je vis à Montréal" / "je vis à montréal"), which suggests the lists were generated, not reviewed.


## Triage
- Explanation: Hand-less generated accept lists; check is exact match after norm() with no accent folding or variants.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Correct, natural translations (Comment vous appelez-vous, feminine plural, es-tu sûr, Stop !, 3 pièces) rejected with only 'Not quite'. Add the variants. Duplicate lowercase accept entries are cosmetic.

## Critic
- Challenge: Accept lists can never be exhaustive.
- Holds up? Yes, narrowly: add the clear cases (Comment vous appelez-vous, feminine plural, Stop !, es-tu sûr). Duplicate lowercase entries are cosmetic, ignore.
- Final verdict: validated

## Fix
Added accept variants: people-01.e7, reflexives-a2-01.e6, adjectives-a2-01.e8, everyday-a2-01.e7, verbs-a2-06.e6, verbs-a2-02.e7, verbs-a2-01.e7.
