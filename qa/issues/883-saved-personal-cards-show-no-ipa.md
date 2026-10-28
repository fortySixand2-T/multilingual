---
id: 883
title: IPA is only visible in the add-preview; saved My deck cards (and Forms panel) show none
severity: low
area: web
persona: absolute-beginner
status: deferred
found: 2026-10-27
---

## Steps to reproduce
1. My deck -> look up "cacahuète" (panel shows /…/), Add to my deck.
2. Look at the saved card in the list; open "Forms & examples".

## Expected
The saved card shows the same IPA next to the word (or in its details), so the learner can see it later.

## Actual
Saved card shows "cacahuète (fe) / peanut / 🔊🐢 / Forms & examples" only; forms panel lists singular/plural and examples, no IPA. The IPA is gone once the preview closes (only MyDeck.tsx preview renders ipa).

## Notes
H6 part: IPA lives only in the preview.

## Triage
- Explanation: Saved cards render no IPA by design; MyDeck.tsx only renders ipa in the add-preview.
- Against spec: Not in the spec'd scope of this slice; PO priority is making the IPA that is shown correct.
- Verdict: deferred
- Rationale: Real UX gap but not the reported bug; showing IPA on cards would widen exposure of still-imperfect eSpeak IPA before the Lexique slice. Revisit after the next slice.


## Critic
- Challenge: Perhaps it is the missing piece of the complaint: the learner never sees IPA on cards.
- Holds up? Deferral stands: the complaint was wrong IPA, not missing IPA; adding UI exposure before the IPA is trustworthy widens the blast radius. Not in this slice.
- Final verdict: deferred
