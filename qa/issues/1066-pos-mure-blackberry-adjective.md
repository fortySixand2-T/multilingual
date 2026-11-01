---
id: 1066
title: Lookup 'mure' -> 'mûre' glossed 'blackberry (f.)' tagged adjective with no gender
severity: medium
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"mure"}

## Expected
fr mûre, pos noun, gender f (gloss itself says f.).

## Actual
{"enrichment":{"fr":"mûre","en":"blackberry (f.)","pos":"adjective","gender":"",...}} (mûr adj dominates in Lexique so noun flipped to adjective; gender lost though gloss says f.).

## Notes
H4 confirmed. Related: 'male' returns fr mâle glossed 'man' (pos noun m) which is fine for the headword but the gloss is off.

## Triage
- Explanation: Duplicate of 1064: mûre is Lexique adjective (8.36) so a model 'noun' flips to adjective, dropping gender although the gloss says f. The 'mure' -> 'mûre' respell is correct.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Duplicate of 1064. The 'male -> mâle' aside is gloss quality; not tracked.

## Critic
- Challenge: Respell mure->mûre is right; the pos flip is Lexique saying mûr(e) is mostly an adjective (8.36) and bare input is ambiguous (mûre adj 'ripe' vs noun). Same reasoning as 1064; gender cannot be trusted from the model when it is exactly the invented-gender failure of 1000.
- Holds up? No change for bare input; 'la mure' covered by the article rule in 1065.
- Final verdict: rejected (folded into 1065)
