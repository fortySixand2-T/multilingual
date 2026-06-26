---
id: 401
title: match_pairs English side drops secondary translations present in vocab deck
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-06-25
---

## Steps to reproduce
1. Open any vocab deck (e.g. `content/b1/vocab/travail.yaml`) and note multi-meaning `en` fields like `objectif` -> "goal, target".
2. Open the corresponding lesson match_pairs exercise (e.g. `travail-b1-01.e5`).
3. Observe the English side of the pair for `objectif` shows only "goal", not "goal, target".

## Expected
The match_pairs English side should match the vocab deck `en` field so learners see a consistent translation across the app.

## Actual
Seven match_pairs entries truncate the deck translation to only the first meaning:

| Exercise | French | Pair shows | Deck says |
|---|---|---|---|
| travail-b1-01.e5 | objectif | goal | goal, target |
| travail-b1-03.e5 | licenciement | dismissal | dismissal, layoff |
| medias-b1-01.e5 | actualite | current events | current events, news |
| medias-b1-01.e5 | information | information | (piece of) information |
| medias-b1-02.e5 | emission | programme | programme, broadcast |
| conseils-b1-01.e5 | conseil | advice | advice, tip |
| environnement-b1-02.e5 | dechet | waste | waste, rubbish |

## Notes
All 7 instances follow the same pattern: the match_pairs exercise uses only the primary meaning from the deck's comma-separated or parenthetical `en` field. A learner who studies the deck and then does the exercise sees inconsistent translations. Low severity because the primary meaning is still correct, but this could cause confusion during SRS review or matching drills.

## Triage
- Explanation: The match_pairs exercises deliberately use only the primary/first meaning from the vocab deck's `en` field. All 7 instances follow this same consistent pattern across every B1 topic. A1/A2 vocab decks have no multi-meaning entries so there is no counter-precedent. The spec does not prescribe that match_pairs must mirror the full vocab deck translation verbatim.
- Against spec: Unspecified. The spec says nothing about match_pairs content granularity or requiring exact vocab deck mirroring.
- Verdict: rejected
- Rationale: This is by-design, not a bug. Match_pairs is a UI-constrained exercise where brevity matters -- showing "dismissal, layoff" or "(piece of) information" as match targets would clutter the interface and add cognitive noise without pedagogical benefit. The primary meaning is always correct. The vocab deck and match_pairs serve different purposes: the deck is a reference with full nuance, while match_pairs tests recognition of the core meaning. Consistency across all 7 instances confirms this is an intentional authoring pattern.

## Critic
- Challenge: Could the inconsistency between deck and match_pairs confuse learners during SRS review? If a learner drills the deck and memorizes "objectif = goal, target", then sees only "goal" in match_pairs, they might second-guess themselves or think they misremembered. Seven occurrences across multiple topics means this is not an isolated edge case. Additionally, a strict reading of AC1.1 ("content authored as YAML") could imply a single source of truth, and divergence between deck and exercise could be seen as a consistency violation.
- Holds up? No. The PM's rejection survives. Every truncated translation is still factually correct -- "goal" is a valid translation of "objectif", "dismissal" is a valid translation of "licenciement". No learner is being taught something wrong. The deck and match_pairs serve different pedagogical functions: reference vs. recognition drill. The spec (AC1.1) governs the authoring format, not whether exercise text must be identical to deck text. Requiring verbatim mirroring would make match_pairs cluttered ("(piece of) information" as a match target is genuinely bad UX) and would add authoring complexity for zero pedagogical gain. The consistent pattern across all 7 instances confirms intentional editorial judgment, not accidental omission.
- Final verdict: rejected
