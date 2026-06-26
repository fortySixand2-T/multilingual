---
id: 371
title: Target vocab for write-b-opinion and write-b-technology is generic time words, not on-theme
severity: low
area: content
persona: absolute-beginner
status: rejected
found: 2026-06-25
---

## Steps to reproduce
1. `GET /assessment/tasks/write-b-opinion` -- task about learning a second language.
   `target_vocab_fr` resolves to: `['semaine', 'jour', 'heure']` (week, day, hour).
2. `GET /assessment/tasks/write-b-technology` -- task about phone usage.
   `target_vocab_fr` resolves to: `['heure', 'jour', 'maintenant', 'soir']` (hour, day, now, evening).

## Expected
The "Try to use:" vocab hints should help guide the writing and be thematically relevant to the prompt. For an opinion about language learning, words like "langue", "apprendre", "ecole" would be more useful. For phone usage, words like "telephone", "message", "internet" would be more relevant.

## Actual
Both tasks have only generic time-related words that don't support the writing topic. A beginner sees "Try to use: semaine, jour, heure" for an essay about language learning, which doesn't help them write on-topic.

## Notes
- Severity is low because the tasks are still usable -- the vocab hints are optional guidance.
- The other 10 synced tasks have well-themed vocab (e.g., write-a2-landlord has appartement, loyer, chambre, fenetre, cle).
- Likely these two tasks were backfilled with whatever A1 words were available rather than carefully themed ones.
- YAML files: `content/a1/writing/section-b-opinion.yaml` and `content/a1/writing/section-b-technology.yaml`.

## Triage
- Explanation: The `target_vocab` field on `write-b-opinion` is `[semaine, jour, heure]` (all tagged `time`) and on `write-b-technology` is `[heure, jour, maintenant, soir]` (also all `time`). The opinion task is about language learning and the technology task is about phone usage -- neither topic relates to time/calendar words. By contrast, all other backfilled tasks have thematically relevant vocab (e.g., write-a-shopping uses `magasin, acheter, pain, fromage, prix, argent`; write-b-seasons uses `soleil, pluie, neige, chaud, froid, saison`). The A1 vocab bank has 188 words but lacks domain-specific terms for "technology" or "language learning" -- these two tasks were likely backfilled with leftover time words as a fallback.
- Against spec: The spec does not define target_vocab quality requirements, but the feature's purpose (per PR #18) is to guide learners toward on-topic vocabulary. Generic time words do not fulfill that purpose for these two prompts.
- Verdict: validated
- Rationale: A beginner seeing "Try to use: semaine, jour, heure" for an essay about language learning gets no useful guidance. The vocab hints are pedagogically misleading -- they imply the learner should write about time rather than the actual topic. While the A1 vocab bank lacks perfect matches, better options exist (e.g., for opinion: `famille, enfant` to discuss personal experience; for technology: `heure, jour, maintenant` could be partially kept but supplemented). Two of 16 tasks are affected; low severity but a real content defect worth fixing in this PR.

## Critic
- Challenge: The PM calls this "pedagogically misleading," but that overstates the impact. The grader prompt explicitly treats target_vocab as a "nudge, not a requirement" and says "do not penalise omissions." The words are presented as optional hints ("Try to use:"), not mandatory constraints. Time words like `semaine`, `jour`, `heure` are perfectly valid A1 French words a learner could naturally use in any essay ("chaque jour j'utilise mon telephone," "je passe deux heures a apprendre"). The A1 vocab bank (188 words) genuinely lacks domain-specific terms for "technology" or "language learning" -- there is no `telephone`, `langue`, `apprendre`, `ecole`, or `internet`. The PM's proposed replacements (`famille, enfant` for an opinion on language learning) are equally off-theme -- they are just different generic words, not thematic matches. Swapping one set of loosely-related words for another adds content churn with no real pedagogical improvement. The feature's value comes from the 14 of 16 tasks that have strong thematic matches; these two simply lack good candidates in the A1 bank, and that is a vocab-bank coverage gap, not a content defect in the writing tasks.
- Holds up? No, overriding the PM. The available A1 vocab has no good thematic matches for these two topics. Any "fix" would just substitute one set of weakly-related words for another. The optional nature of the hints means the impact on learners is negligible. This is not worth a code change.
- Final verdict: rejected
