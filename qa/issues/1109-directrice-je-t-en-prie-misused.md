---
id: 1109
title: Listening b1-message-de-la-directrice: 'Rappelle-moi avant midi, je t'en prie' misuses 'je t'en prie'
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
« Rappelle-moi avant midi, s'il te plaît. » ('je t'en prie' answers a thanks or invites someone to go ahead; it is not a plain request tag. A learner will copy it.)

## Actual
Final sentence of script: « Rappelle-moi avant midi, je t'en prie. »



## Triage
- Explanation: 'je t'en prie' is a valid insistent request tag ('please, I beg you').
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: Used after an imperative, 'je t'en prie' is idiomatic French, not just a reply to thanks. A little emphatic from a boss, but not misuse. Preference.

## Critic
- Challenge: 'je t'en prie' after an imperative is idiomatic.
- Holds up? yes
- Final verdict: rejected
