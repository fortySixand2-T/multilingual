---
id: 1103
title: Reading b1-bien-s-installer: 'quand je voyage, une voisine a la gentillesse de s'occuper de mon chat' is a stilted non sequitur
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
Natural sentence tied to the preceding point (asking for help). Suggested: « quand je voyage, une voisine accepte gentiment de s'occuper de mon chat. »

## Actual
« il faut aussi accepter de demander de l'aide : quand je voyage, une voisine a la gentillesse de s'occuper de mon chat. » 'avoir la gentillesse de' is formal/ironic register and the colon makes the cat anecdote read as unrelated to 'demander de l'aide' (she does not say she asked).



## Triage
- Explanation: 'avoir la gentillesse de' is a polite/slightly formal idiom, not ungrammatical.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: The cat anecdote is a plausible illustration of accepting help (the colon introduces an example). Register is a little formal for a forum but correct. Preference only.

## Critic
- Challenge: 'avoir la gentillesse de' is correct, slightly formal; example after colon is coherent. Preference.
- Holds up? yes
- Final verdict: rejected
