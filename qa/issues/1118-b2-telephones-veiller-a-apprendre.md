---
id: 1118
title: listen-b2-telephones-a-l-ecole: "veiller à apprendre aux jeunes à utiliser le numérique" is ungrammatical-sounding
severity: medium
area: comprehension
persona: exam-crammer
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/listen-b2-telephones-a-l-ecole (script in content/b2/comprehension/listen-b2-telephones-a-l-ecole.yaml), also spoken in the mp3.

## Expected
"veiller à" takes a noun or "à ce que + subjunctive", and avoids a stack of "à ... à ...".

## Actual
"Il faut aussi veiller à apprendre aux jeunes à utiliser le numérique avec esprit critique, plutôt que de recourir à l'interdiction comme seule réponse."
"veiller à apprendre" is not idiomatic (veiller à + infinitive of one's own action reads as 'take care to'), and the triple "à apprendre ... à utiliser ... à l'interdiction" is hard to follow by ear, in a listening exercise. Q3 option and explain copy the sentence verbatim, so the flaw is also in the question.

## Notes
Proposed replacement: "Il faut aussi veiller à ce que les jeunes apprennent à utiliser le numérique avec esprit critique, plutôt que de recourir à l'interdiction comme seule réponse." (Requires re-rendering the mp3 and updating q3 explain; option can stay 'Apprendre aux jeunes ...'.)


## Triage
- Explanation: 'veiller à' + infinitive is attested; the sentence is grammatical, if heavy.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: 'veiller à apprendre aux jeunes à utiliser' is grammatical though stacked; 'veiller à ce que' is more standard but not required. Speech-heavy for B2 listening is within level. Preference.

## Critic
- Challenge: The sentence is grammatical ('veiller à' + infinitive; 'apprendre à quelqu'un à'). It is heavy, but B2 listening tolerates this, and fixing it forces an mp3 re-render and q3 explain change. A convenient dismissal? I checked: 'veiller à apprendre' with an unspecified agent is a little loose, but not wrong or misleading. Real users won't be misled.
- Holds up? yes - dismissal survives
- Final verdict: rejected
