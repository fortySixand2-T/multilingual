---
id: 1105
title: Reading b1-cafe-philo: forced/odd prose ('le genre de personne', 'vont prier', 'chercher à créer', 'sauver un peu de son âme')
severity: low
area: comprehension
persona: returning-learner
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/read-b1-cafe-philo (source: content/b1/comprehension/read-b1-cafe-philo.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
Natural sentences. Suggested: « Ensuite, un homme qui avait toujours une blague prête a rappelé qu'il existe tant de façons de donner un sens à sa vie : certains prient, d'autres préfèrent créer, par la musique ou la peinture. » and « Ce qui compte, c'est de préserver un peu de son âme dans un monde pressé. »

## Actual
« un homme, le genre de personne qui a toujours une blague prête » (appositive that adds nothing, forced 'genre de'); « certains vont prier, d'autres préfèrent chercher à créer » ('aller prier' is not idiomatic, 'chercher à créer' is padding); « sauver un peu de son âme » (sauver son âme is theological, 'un peu de' makes it odd). Also 'la question était simple' for a deep philosophical question.



## Triage
- Explanation: Spoken-register phrasing, all grammatical.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: 'le genre de personne qui', 'certains vont prier' and 'chercher à créer' are acceptable, informal-leaning French in an oral-report narrative; 'sauver un peu de son âme' is a playful twist, not an error. Preference. (Not to be mixed with 1106, which is validated.)

## Critic
- Challenge: Spoken-register, grammatical phrasing; no error a learner would copy harmfully.
- Holds up? yes
- Final verdict: rejected
