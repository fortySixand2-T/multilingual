---
id: 1081
title: "a la carte" returns the untranslated gloss "a la carte" (pos adjective)
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"a la carte"} (also "À LA CARTE" and "  a  la   carte ").

## Expected
A real English gloss, e.g. "from the menu / individually priced", pos adjective or phrase.

## Actual
{"enrichment":{"fr":"à la carte","en":"a la carte","pos":"adjective","ipa":"a la kaʁt",...}} - en is just the French phrase echoed back, so the card teaches nothing. Identical for the caps/whitespace variants (same slug).

## Notes
Possibly the model reply was "(a la carte)"-style or "a la carte" echoed; either way no gloss validation rejects en == fr (ignoring accents). Suggest treating en that equals fr modulo accents/case as a failed lookup/retry.

## Triage
- Explanation: Offline clean_gloss leaves 'a la carte' alone; the 7B echoed the French. No code removes the gloss. A guard (en == fr modulo accents/case -> treat as failed lookup) is possible but is new validation, not a defect in #133.
- Against spec: Unspecified. Not about respell/pos/clean_gloss.
- Verdict: deferred
- Rationale: Model-quality, low impact (rare phrase); revisit as a general en==fr guard if it recurs.

## Critic
- Challenge: PM deferred as model quality. But 'a la carte' is itself an English term (menu sense), so en 'a la carte' is a correct, if lazy, gloss; and an en==fr guard would be new validation that wrongly rejects cognates (important, restaurant, animal).
- Holds up? No bug to defer; close.
- Final verdict: rejected
