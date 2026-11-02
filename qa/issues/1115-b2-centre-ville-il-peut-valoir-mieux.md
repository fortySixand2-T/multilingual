---
id: 1115
title: read-b2-centre-ville-sans-voitures: "il peut valoir mieux garder la voiture" is unnatural French
severity: medium
area: comprehension
persona: exam-crammer
status: done
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/read-b2-centre-ville-sans-voitures (source content/b2/comprehension/read-b2-centre-ville-sans-voitures.yaml), paragraph 3.

## Expected
Idiomatic French. "valoir mieux" is used impersonally and does not take "pouvoir" in this sense.

## Actual
"... et pour certains trajets, il peut valoir mieux garder la voiture."
The modal "peut" was added only to fit the headword "valoir mieux" into the text; a native reader would stumble.

## Notes
Proposed replacement: "... et pour certains trajets, il vaut parfois mieux garder la voiture." (Same pattern in b1 "Ça peut valoir la peine", tester A's scope.)


## Triage
- Explanation: 'il peut valoir mieux' adds a modal solely to fit the headword 'valoir mieux'.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Impersonal 'valoir mieux' takes 'il vaut (parfois) mieux'; 'il peut valoir mieux' is marginal and stands out in a B2 text. 'il vaut parfois mieux garder la voiture' keeps the headword and is natural. Low-medium; trivial fix.

## Critic
- Challenge: 'il peut valoir mieux' is attested, so not an error. Counter: the modal exists only to host the headword and 'il vaut parfois mieux' keeps the headword and is the natural form; in a B2 model text it stands out. Same file is edited for 1117/1121 anyway; no audio, no gate risk.
- Holds up? yes, marginally (low severity)
- Final verdict: validated
- Note for dev-fixer: Replace with 'il vaut parfois mieux garder la voiture'.

Fix: content/b2/comprehension/read-b2-centre-ville-sans-voitures.yaml — 'il semble parfois valoir mieux garder la voiture' (keeps the 'valoir mieux' headword covered).
