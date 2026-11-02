---
id: 1106
title: Reading b1-cafe-philo: 'la force ne peut pas permettre de résoudre un conflit' is clumsy
severity: low
area: comprehension
persona: returning-learner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/read-b1-cafe-philo (source: content/b1/comprehension/read-b1-cafe-philo.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
« Selon lui, la force ne permet pas de résoudre un conflit ; elle peut seulement empêcher l'autre de parler. »

## Actual
« la force ne peut pas permettre de résoudre un conflit » stacks two modals (pouvoir + permettre) to host the headword; no native would say it. Q2's correct option « Elle peut seulement empêcher l'autre de parler » is unaffected.



## Triage
- Explanation: 'la force ne peut pas permettre de résoudre un conflit' stacks pouvoir + permettre to host the headword 'permettre de'.
- Against spec: Unspecified; coverage gate b1=100 constrains the fix.
- Verdict: validated
- Rationale: A native would write 'la force ne permet pas de résoudre'. It is clumsy, forced prose a B1 learner may imitate. Low severity, trivial fix; the fix must keep 'permettre de' covered somewhere (the directrice listening has it) or the 100% coverage gate will trip.

## Critic
- Challenge: Not ungrammatical: 'ne peut pas permettre de' is attested. Counter: stacked modals with an inanimate subject read as forced headword hosting, 'la force ne permet pas de' is plainly better. Low value but zero-risk one-line edit.
- Holds up? yes, marginally (low severity)
- Final verdict: validated
- Note for dev-fixer: Keep 'permettre de' covered (directrice script has it, so gate stays 100). Reading set, no audio impact.

Fix: content/b1/comprehension/read-b1-cafe-philo.yaml — 'la force ne permet pas de résoudre un conflit'.
