---
id: 921
title: IPA vowel inconsistencies - professeur vs professeure differ (ofɛ/ɔfɛ), premier(s) shown with ø
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. `GET /content/vocab`, find `professeur` (a1), `premiers_soins` (a2), `premier_ministre` (b2), `serrer` (a2 new), `camping` (a1).
2. Compare `ipa` / `fem_ipa` with each other and with Wiktionary.

## Expected
A card's masculine and feminine IPA agree on shared sounds; "premier" uses the usual schwa.

## Actual
| word | current IPA | correct IPA | evidence |
|---|---|---|---|
| professeur / professeure (a1) | pʁofɛsœʁ / pʁɔfɛsœʁ | same first vowel in both (pʁɔfɛsœʁ) | the two forms of the same card show different o vs ɔ; masculine came from Lexique, feminine from Piper (not in Lexique) |
| premiers soins (a2) | pʁømje swɛ̃ | pʁəmje swɛ̃ | Lexique `premier` = pʁømje; Wiktionary pʁə.mje |
| premier ministre (b2) | pʁømje ministʁ | pʁəmje ministʁ | same |
| serrer (a2, new) | seʁe | sɛʁe | Wiktionary sɛ.ʁe; Lexique gives e |
| camping (a1) | kɑ̃piŋ | kɑ̃piŋ (only card using ŋ; check the IPA glyph set the UI font/TTS compare handles) | fyi |

## Notes
Cosmetic; all within accepted variation of the script's `_loose` comparison, which is why none were flagged for review. All other new cards (214) matched Lexique and my own knowledge of standard French; no stray characters, spaces, stress marks or missing ipa anywhere in the 2,066-card bank; fem_ipa is present for every `fem`, and equals `ipa` only for true homophones (ami/amie, employé/ée, réfugié/ée, abonné/ée, député/ée, ingénieur/e, superviseur/e).


## Triage
- Explanation: Within the script's loose-compare tolerance; Lexique vs Piper source differences.
- Against spec: Accepted variation (pʁømje is Lexique's own form).
- Verdict: deferred
- Rationale: Cosmetic, not misleading. Only the professeur/professeure o/ɔ mismatch is worth a one-line REVIEWED fix whenever the file is next touched.

## Critic
- Challenge: Within accepted variation.
- Holds up? PM deferral is right; cosmetic.
- Final verdict: deferred

## Fix
`REVIEWED` pins in `scripts/build_vocab_ipa.py`: premier, premiers soins and premier ministre use pʁəmje; serrer is sɛʁe; professeur is pʁɔfɛsœʁ, matching professeure. camping keeps ŋ, which is correct IPA.
