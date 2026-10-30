---
id: 897
title: "Two new translate accept lists accept a non-equivalent answer ('le prix est haut' calque, 'même dimanche' = a single Sunday)"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. `b1/connecteurs-b1-01.e7` "however, the price is high" (use cependant): `accept` contains
   "Cependant, le prix est haut". Standard French is "le prix est élevé" (prices are "élevés"/"hauts" only colloquially; "haut" is an English calque and is not what the exam expects).
2. `a2/adverbs-a2-01.e6` "even on Sunday": `accept` contains "même dimanche". Without the article
   "dimanche" means "this coming/that one Sunday"; "même le dimanche" is the habitual "even on Sundays". The
   English prompt is the habitual sense.

## Expected
Accept lists contain only answers equivalent to the prompt (same pattern as 751, 800, 801).

## Actual
Both are marked Correct.

## Notes
Low: wrong answers pass rather than right answers failing, but it teaches the calque.


## Triage
- Explanation: Accept lists generated without review.
- Against spec: Same family as 751/800/801.
- Verdict: validated
- Rationale: 'même dimanche' is not the habitual sense of the prompt and should be removed. 'le prix est haut' is acceptable colloquial French, so that half is not a defect; keep scope to même dimanche (low).

## Critic
- Challenge: 'le prix est haut' is colloquially fine.
- Holds up? Partly: verified accept list has 'même dimanche' for 'même le dimanche' (habitual) -> remove that. Leave 'le prix est haut' (answer is already 'élevé'; haut is tolerable). Scope: même dimanche only.
- Final verdict: validated

## Fix
Removed 'même dimanche' from adverbs-a2-01.e6 accept (le prix est haut left per triage).
