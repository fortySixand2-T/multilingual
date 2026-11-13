---
id: 1148
title: My deck preview: 'mûr' returns the course word 'mur' (wall) and "d'accord" returns 'accord' (agreement)
severity: medium
area: content
persona: returning-learner
status: rejected
found: 2026-11-12
---

## Steps to reproduce
1. Sign up with invite code qa065-a, then for each word below call `POST /vocab/personal/preview {"word": "<w>"}` (Bearer token).
2. Read `enrichment.en` / `pos` / `gender` as a learner adding the word to My deck.

## Expected
`mûr` -> "ripe, mature"; `d'accord` -> "OK / agreed" (an extremely common word).

## Actual
```
mûr      -> {"fr":"mur","en":"wall","pos":"noun","gender":"m",...,"in_course":"a2"}
d'accord -> {"fr":"accord","en":"agreement","pos":"noun","gender":"m",...,"in_course":"b1"}
ou       -> {"fr":"où","en":"where (interrogative)",...}
```
The learner typed a different word and gets another word's card, with no warning that the spelling was changed. Also `est-ce que` returns `{"enrichment":null,"over_budget":true}` (may be the budget tester's change on the scratch app; sibling words resolved fine before).

## Notes
Accent-insensitive/elision-stripping matching prefers the course/most-frequent word over the exact typed form. Prefer an exact (accented) match first; strip d'/l' only when the exact form is absent.

## Triage
- Explanation: Duplicate of 1176 (course match ignores typed accents; mur/mûr, sur/sûr). The extra d'accord case is the elision strip: enrich._ARTICLES contains "d'" and find_content_match normalises the same way, so "d'accord" becomes 'accord'; reproduced on scratch (in_course b1 'accord'). 'ou' -> où is 1175 (shared accent-folded cache) plus course match. 'est-ce que' gave a plain 422 for me (not over_budget); the over_budget was the budget tester's scratch state.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: Duplicate; tracked under 1176 (including the d'accord elision sub-case, which should be added to that fix's scope).

## Critic
- Challenge: Is it actually a distinct bug? The d'accord elision case is real.
- Holds up? Rejection stands as a duplicate; 1176 triage already includes the d'accord elision sub-case and 1175 covers ou->où. est-ce que over_budget was scratch state. No separate fix.
- Final verdict: rejected
