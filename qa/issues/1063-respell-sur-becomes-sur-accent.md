---
id: 1063
title: Typing 'sur' returns 'sûr' (adjective, 'sure; safe') not the preposition 'on'
severity: medium
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"sur"}

## Expected
fr "sur", preposition 'on'.

## Actual
{"enrichment":{"fr":"sûr","en":"sure; safe","pos":"adjective",...,"in_course":"a2"}}

## Notes
H1 confirmed. Same class as du/des/la: accentless function word resolved to rarer accented homograph.

## Triage
- Explanation: Offline: respell('sur') returns 'sur' (sur 7908 vs sûr 1145), so respell itself is fine. The model proposed 'sûr' for typed 'sur'; _headword accepts any same-slug variant with accents >= typed, and nothing compares frequency of the typed spelling to the proposal. Deterministic gap in lookup._headword; the 7B choosing sûr is the trigger.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real: preposition 'sur' unreachable. Fix in _headword: when typed (no accents) is itself a Lexique form markedly more frequent than the accented proposal, keep typed.

## Critic
- Challenge: PM suggested keeping the typed 'sur' in _headword when it is far more frequent than sûr. Live preview: fr sûr, en 'sure; safe', adjective. The model chose the sense sûr (respell('sur') is 'sur' offline, so #133 is not the cause). Forcing headword 'sur' would keep gloss 'sure; safe' and produce the opposite fr/en mismatch; a real fix needs a re-prompt or retry, i.e. new machinery. The accepted-accent rule (QA 891) predates #133. Learner can type sûr/ re-edit meaning; ambiguity is genuine (sur/sûr differ only by accent).
- Holds up? No; model-quality, fix worse than the bug.
- Final verdict: rejected
