---
id: 1104
title: Reading b1-cafe-philo q3: distractor 'Il est plus fort que la mort' is defensible from the text
severity: medium
area: comprehension
persona: returning-learner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/read-b1-cafe-philo (source: content/b1/comprehension/read-b1-cafe-philo.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
Exactly one option supported. 

## Actual
Q3 « Que dit la dame âgée de l'amour ? » Correct: « Il ne disparaît pas, il change de forme ». Distractor: « Il est plus fort que la mort ». The passage: « Elle a perdu son mari l'an dernier et, depuis sa mort, ce sentiment ne l'a pas quittée ». A reader can fairly infer love outlasted death, so the distractor is arguable. Suggested replacement distractor: « Il s'affaiblit avec les années » (clearly contradicted).



## Triage
- Explanation: Q3 asks what the woman SAYS; the correct option quotes her. But the passage frames the story as love surviving her husband's death, so 'plus fort que la mort' is a fair inference.
- Against spec: Distractors must be unambiguously wrong (past 910-912 rule).
- Verdict: validated
- Rationale: A B1 reader who reasons from 'depuis sa mort, ce sentiment ne l'a pas quittée' can defend the distractor. Same class as past 910-912 (second defensible option). Cheap content fix: replace with a clearly contradicted distractor (e.g. « Il s'affaiblit avec les années »).

## Critic
- Challenge: Q3 asks what she SAYS; the distractor is not her statement. Counter: the passage frames love outliving her husband's death, so 'plus fort que la mort' is a fair inference and a B1 reader can defend it (910-912 class). One-option swap, zero risk.
- Holds up? yes - second defensible option is a real fairness defect
- Final verdict: validated
- Note for dev-fixer: Replace only that distractor with a clearly contradicted one.

Fix: content/b1/comprehension/read-b1-cafe-philo.yaml — Q3 distractor replaced with a clearly contradicted one.
