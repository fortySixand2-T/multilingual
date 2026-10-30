---
id: 922
title: New a1 card "docteur" is gender m with no feminine (docteure) form or fem_ipa/audio
severity: low
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-29
---

## Steps to reproduce
1. Read `content/a1/vocab/people.yaml` card `docteur` (or `GET /content/vocab`, id `docteur`).

## Expected
Person nouns with a feminine form are `gender: mf` with `fem` (docteure, same pronunciation dɔktœʁ) so the card, `fem_ipa` and `docteur_f.mp3` exist, like professeur/professeure and ingénieur/ingénieure in the same bank (TEF Canada uses "docteure").

## Actual
`gender: m`, no `fem`, `fem_ipa` empty; learners never see docteure. Other new people cards (garçon m, dame f, homme, femme) are fine.

## Notes
Content gap, not an IPA error (fem_ipa would equal ipa).


## Triage
- Explanation: docteur card authored gender m with no fem.
- Against spec: Unspecified; no rule requires every person noun to have a feminine card.
- Verdict: deferred
- Rationale: Missing extra info, not wrong info. Fold into a future people-card pass (docteure, fem_ipa, audio).

## Critic
- Challenge: Missing extra info only.
- Holds up? PM deferral right.
- Final verdict: deferred
