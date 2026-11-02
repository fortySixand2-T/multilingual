---
id: 1102
title: Reading b1-bien-s-installer: headword-form 'ne pas oublier de renouveler sa carte' is a dangling infinitive in a forum post addressed to 'vous'
severity: low
area: comprehension
persona: returning-learner
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/read-b1-bien-s-installer (source: content/b1/comprehension/read-b1-bien-s-installer.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
Consistent address. The post says « Prenez votre temps », « Je vous recommande », then switches to a bare infinitive with 'sa'. Suggested: « Et surtout, n'oubliez pas de renouveler votre carte d'assurance maladie avant la date limite. »

## Actual
« Et surtout, ne pas oublier de renouveler sa carte d'assurance maladie avant la date limite. » A fragment with no governing verb, forced to carry the headword 'oublier de'. Reads as a copied dictionary form; a B1 learner may imitate it.



## Triage
- Explanation: Passage line in the forum post; plain infinitive as advice.
- Against spec: Unspecified (CLAUDE.md: natural French; this is natural).
- Verdict: rejected
- Rationale: Bare infinitive for advice/instruction is standard French (recipes, forum tips) and the same post already uses it: « Mon conseil : se mettre à un sport d'hiver ». « sa carte » is the generic possessive that goes with it. Natural, not an error; no learner harm. Rejected as preference.

## Critic
- Challenge: Triage is right: bare infinitive advice is standard and the same post already uses it.
- Holds up? yes
- Final verdict: rejected
