---
id: 1191
title: My deck: looking up a word already in the deck gives no warning, then says "Added" but changes nothing
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-11-12
---

## Steps to reproduce
1. On /my-deck look up "pendant", change the meaning to "during (my edit)", press "Add to my deck" (card appears).
2. Look up "pendant" again. Preview shows the dictionary meaning "during, throughout" and an "Add to my deck" button, with no hint it is already in the deck.
3. Press "Add to my deck".

## Expected
Preview says "Already in your deck" (as it does for course words: "Already in your course vocab ... no need to add it"), or the add updates the card.

## Actual
Green banner: Added "pendant" - it's in your reviews now. The list still shows one card with "during (my edit)"; the new meaning was silently discarded (GET /vocab/personal returns a single card uv:pendant, en "during (my edit)"). The message implies something was added/changed.

## Notes
Course words get a clear "already in" message; personal duplicates do not.

## Triage
- Explanation: Confirmed in MyDeck.tsx: setAdded(preview.fr) fires on any 200 and ignores the response's added flag; add_personal is idempotent so a re-add returns added:false with the old meaning. Preview is cached per word and does not know the user's deck.
- Against spec: Course words already show 'Already in your course vocab'; same courtesy expected for My deck.
- Verdict: validated
- Rationale: Low but misleading ('Added' while nothing changed, edit silently discarded). FIX LOCATION: UI (honour added:false: 'Already in your deck' and show existing meaning); optionally preview could return in_deck. Not a duplicate of 1181 (unrelated to accents).

## Critic
- Challenge: Idempotent re-add is harmless; only the banner is off.
- Holds up? Yes. Confirmed: MyDeck.tsx line 107 shows 'Added ... in your reviews now' on any 200, ignoring added:false, and the learner's new meaning is silently discarded. Misleading in a common flow (re-adding a word). Fix in the UI only: honour added:false with an 'Already in your deck' message; no API change.
- Final verdict: validated

## Fix
- `web/src/screens/MyDeck.tsx`: honours `added: false` and says the word is already in the deck with its existing meaning, instead of "Added". Test: `web/src/screens/MyDeck.test.tsx`.
