---
id: 895
title: "New polysemous headwords glossed with one sense only; the missing sense is used by the course's own A1/A2 content (temps, mal, personne, histoire, pièce, garder, juste)"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Read the `en:` of these new cards, then grep the existing course for the other sense.
2. Instances (file, id, current gloss -> missing sense and where the course already uses it):
   - `content/a1/vocab/time-words.yaml` `temps`: "time" -> also "weather". A1 content asks "Quel temps fait-il ?" (`a1/comprehension/reading-postcard.yaml:20`, `listening-weather.yaml:15`, `read-a1-la-meteo-de-la-semaine.yaml:15`). Suggest `time; weather`.
   - `content/a1/vocab/adverbs.yaml:51` `mal`: "badly" -> also "pain / ache" (`avoir mal à`; A1 `read-a1-chez-le-medecin.yaml:10` "J'ai mal à l'épaule"). Suggest `badly; pain (avoir mal)`.
   - `content/a1/vocab/people.yaml:34` `personne`: "person" -> also the pronoun "nobody / no one" (`ne … personne`). Suggest `person; (with ne) nobody`.
   - `content/a2/vocab/everyday.yaml` `histoire_recit` (fr: histoire): "story" -> also "history". No other card for "history". Suggest `story; history`.
   - `content/a2/vocab/everyday.yaml:58` `pièce`: "room (of a home)" -> also "coin", "play", "document" (`pièce d'identité`, used in `b1/comprehension/read-b1-community-library.yaml`). Suggest `room; coin; ID document (pièce d'identité)`.
   - `content/a2/vocab/verbs.yaml:121` `garder`: "to keep" -> also "to look after" (garder les enfants). Suggest `to keep; to look after`.
   - `content/a2/vocab/adjectives.yaml` `juste`: "fair; right" (pos adjective) -> also adverb "just / only". Suggest `fair; right; (adv.) just`.
3. In-app: Lesson 1 summary / vocab lookup / SRS card shows only the single sense.

## Expected
Cards for headwords whose main second sense is already met in the course carry both senses
(as done for `voler` "to fly; to steal", `poser`, `tour`).

## Actual
One-sense glosses. A learner who meets "Quel temps fait-il ?" or "J'ai mal" after the card
has a wrong or missing mental mapping; Review marks "weather"/"pain" answers wrong if used as
a free-text check.

## Notes
Also minor: `a1/vocab/people.yaml` `maman` is glossed "mum" (British); TEF Canada audience uses "mom".
Not re-filing 893 (lookup gloss) or 721 (chauffeur/conducteur).


## Triage
- Explanation: Cards were generated with a single gloss; course's own A1 content uses the other senses (temps=weather, mal=ache, etc.).
- Against spec: Precedent in bank: voler/poser/tour carry both senses.
- Verdict: validated
- Rationale: Learner meets 'Quel temps fait-il ?' / 'J'ai mal' after a card that glosses a different sense: misleading. Cheap data fix. 'mum' vs 'mom' is a note only, not a defect.

## Critic
- Challenge: Single-gloss cards are normal; 'mum' note is nitpick.
- Holds up? Yes for the data fix (temps/mal/personne etc. sense used by course content); mum/mom is a note, not in scope.
- Final verdict: validated

## Fix
Added alternate senses to the temps, mal, personne, histoire, pièce, garder, juste cards (vocab YAML) and the matching match_pairs glosses in their lessons.
