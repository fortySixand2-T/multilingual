---
id: 1064
title: Lookup 'son' glossed 'sound' gets pos adjective, gender dropped
severity: medium
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"son"}

## Expected
pos noun, gender m for 'sound' (le son).

## Actual
{"enrichment":{"fr":"son","en":"sound","pos":"adjective","gender":"",...}} gloss is a noun but pos is adjective and no gender shown.

## Notes
H4 confirmed: lexicon.pos flips noun->adjective by Lexique's dominant reading (possessive son) regardless of the model's gloss. The flip should be skipped when the gloss is clearly the other sense.

## Triage
- Explanation: Offline: lexicon.pos('son','noun') -> 'adjective'. Lexique stores one dominant pos per form (son = possessive adjective, 6525) and pos() overrides any model 'noun' when that pos is in _NOT_NOUNS, ignoring the gloss. resolve_gender then runs on adjective so the gender m is lost. Deterministic, enrich.py:300 / lexicon.pos.
- Against spec: Plan 2 change surface #2 flagged this risk; user need is gender on nouns. Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real: 'sound' card loses noun/gender. Primary for the pos-flip class (dups 1065, 1066). Fix: skip the flip when the typed input had an article (strong noun signal), when the gloss is a noun sense, or restrict flip to forms where Lexique noun freq is negligible (needs per-pos freq).

## Critic
- Challenge: Bare 'son' is genuinely ambiguous: Lexique's dominant reading is the possessive adjective (6525), which is exactly the signal that fixes 1000/pendant. Any gloss-based or table-based exception reopens 1000 (the gender table itself wrongly lists grandes as an f noun, so it cannot arbitrate; Lexique has one pos per form, no per-pos frequency). A learner wanting 'sound' types 'le son', which is covered by the article-signal fix in 1065.
- Holds up? Bare-word case is working as designed (plan change surface #2); the narrow, safe fix is the typed-article rule tracked in 1065. Folded into 1065.
- Final verdict: rejected (bare form by design; article case folded into 1065)
