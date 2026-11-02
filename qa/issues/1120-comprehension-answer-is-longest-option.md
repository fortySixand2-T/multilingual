---
id: 1120
title: Correct option is the longest in 22 of 25 questions across the 7 new comprehension sets
severity: medium
area: comprehension
persona: exam-crammer
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Fetch the 7 new sets (read-b2-semaine-de-quatre-jours, read-b2-centre-ville-sans-voitures, listen-b2-telephones-a-l-ecole, read-b1-bien-s-installer, read-b1-cafe-philo, listen-b1-un-voisin-courageux, listen-b1-message-de-la-directrice).
2. Compare character length of the correct option with the distractors (compare with answer key in the yaml).

## Expected
Correct answers not identifiable by length alone.

## Actual
Correct option is strictly or jointly the longest in 22/25 questions; 10/11 in the three b2 sets. Examples: centre-ville q1 69 chars vs 35/31; q4 62 vs 37/31; telephones q3 65 vs 42/20; semaine q4 49 vs 24/34. Test-wise users (exam-crammer) can score well without reading. Position is fine (answer index tally over 60 GETs per set: pos0 514, pos1 501, pos2 485, no bias; H4 not reproduced).

## Notes
Shorten the correct option or lengthen distractors to similar length and grammatical shape.


## Triage
- Explanation: Correct option is strictly longest in 20/25 questions of the 7 new sets (my recount; reporter said 22 jointly-longest). Chance is about 33%. Authoring bias, not rule-based.
- Against spec: Correct-answer cues violate fair-test principle (cf. 910-912).
- Verdict: validated
- Rationale: Real test-wiseness giveaway; exam-crammer persona can score without reading. Position bias is absent (H4 refuted). Scope: fix the 7 new sets only (lengthen distractors / trim answers). Baseline check: the older 589 questions are strictly-longest in 415 (70%), so the bias is corpus-wide; a bulk pass on older sets is a separate deferred follow-up, not this round. Canonical for 1111.

## Critic
- Challenge: Challenge: bias is corpus-wide (70% of 589 older questions), so fixing only 7 sets is arbitrary, and the PM's count (20/25) is below the reporter's (22). Counter: the exam-crammer issue is real for the sets this round delivered, answers are position-balanced, and scoping to the 7 new sets limits the change to authoring edits. Scope is acceptable provided: (a) options only in the 7 new sets (b1: bien-s-installer, cafe-philo, un-voisin-courageux, message-de-la-directrice; b2: semaine-de-quatre-jours, centre-ville-sans-voitures, telephones-a-l-ecole); (b) lengthen/balance distractors rather than rewriting answers, so explain quotes and audio stay valid (no mp3 re-render); (c) coordinate with 1104/1121/1107 edits to the same files; (d) no bulk pass on older sets.
- Holds up? yes, scoped as above
- Final verdict: validated
- Note for dev-fixer: Older sets explicitly out of scope (backlog).

Fix: distractors lengthened in the 7 new sets (content/b1|b2/comprehension/*) so the correct option is no longer systematically the longest.
