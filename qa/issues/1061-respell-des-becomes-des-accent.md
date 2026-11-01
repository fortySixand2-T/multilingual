---
id: 1061
title: Typing accentless 'des' stores headword 'dès' (preposition) glossed 'some, several'
severity: high
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"des"}

## Expected
fr "des" (indefinite plural article, 'some').

## Actual
{"enrichment":{"fr":"dès","en":"some, several","pos":"preposition",...,"ipa":"dɛ"}} Headword dès means 'from/as early as'; gloss is for des. fr/en mismatch.

## Notes
H1 confirmed, same cause as 1060.

## Triage
- Explanation: Same cause as 1060: 'des' absent from Lexique forms, respell -> 'dès' (preposition, 418.8). Duplicate of 1060.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Duplicate of 1060 (fix together; add des to the regression test). Kept validated only as a test case, not separate work.

## Critic
- Challenge: Separate bug? No: identical cause and site as 1060 (des absent from Lexique forms, respell -> dès).
- Holds up? Duplicate. Closed as duplicate of 1060; fix and test des there.
- Final verdict: rejected (duplicate of 1060)
