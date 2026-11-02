---
id: 1110
title: Listening b1-message-de-la-directrice: 'te proposer de faire une réunion' is an anglicism; Q2 and its explain repeat it
severity: low
area: comprehension
persona: returning-learner
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/listen-b1-message-de-la-directrice (source: content/b1/comprehension/listen-b1-message-de-la-directrice.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
« Je voudrais te proposer d'organiser une réunion jeudi matin avec le fournisseur » (or « de tenir »). Update q2 explain quote accordingly and re-render audio.

## Actual
« Je voudrais te proposer de faire une réunion jeudi matin avec le fournisseur. » 'faire une réunion' is calqued on 'to make a meeting'; French uses 'tenir/organiser/avoir une réunion'. Also « cherche à le résoudre depuis lundi » is awkward (cherche à + depuis) for 'essaie de le résoudre depuis lundi'.



## Triage
- Explanation: 'faire une réunion' is widespread everyday French; 'cherche à ... depuis lundi' is grammatical.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: Purists prefer tenir/organiser but 'faire une réunion' is attested and understood; 'chercher à' + 'depuis' is fine. Not wrong. Preference.

## Critic
- Challenge: 'faire une réunion' is common, if disliked by purists; 'cherche à ... depuis' grammatical.
- Holds up? yes
- Final verdict: rejected
