---
id: 800
title: "translate exercise verbes-b1-01.e8 accepts bare 'arriver' for 'to manage to', teaching the wrong verb meaning"
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-09-10
---

## Steps to reproduce
1. Read `content/b1/lessons/verbes-b1-01.yaml`, exercise `verbes-b1-01.e8`:
   ```yaml
   - id: verbes-b1-01.e8
     type: translate
     prompt: "Translate: “to manage to” (succeed in doing)"
     answer: "arriver à"
     accept: ["arriver"]
   ```
2. Equivalently over the API: complete/preview this exercise and submit the answer
   `arriver` for the prompt "to manage to (succeed in doing)".

## Expected
Only translations that preserve the meaning "to manage to / to succeed in doing"
should be marked correct. Since the whole grammar point of this lesson is "verb +
à/de + infinitive" (`grammar_point: "verbe + infinitif : « à » ou « de »"`), the
lesson exists specifically to teach that dropping the preposition changes the verb.

## Actual
`accept: ["arriver"]` marks the bare verb `arriver` as a correct translation of
"to manage to". But `arriver` (without `à` + infinitive) means "to arrive" — a
completely different, unrelated verb. A learner who answers "arriver" is told
they got it right, actively reinforcing a wrong translation, and undermines the
lesson's own teaching point (à vs de after arriver-style verbs).

## Notes
Contrast with the lesson's other `translate` exercises and its own vocab bank
entry `arriver_a` (`content/b1/vocab/verbs.yaml`): `fr: "arriver à"`,
`en: "to manage to (+ infinitive)"` — the vocab bank correctly requires the
preposition; only this exercise's `accept` list is wrong.
Likely fix: drop `arriver` from `accept`, or if leniency for a missing/misplaced
preposition is desired, accept `"arriver à faire"`-style variants instead, never
the bare infinitive alone.
Same bug class as `verbes-b1-02.e8` (issue 801) — file together, likely same root
cause (accept list authored by stripping the preposition without checking meaning).

## Triage
- Explanation: Confirmed in `content/b1/lessons/verbes-b1-01.yaml:58-62`: exercise `verbes-b1-01.e8` has `answer: "arriver à"`, `accept: ["arriver"]`. French usage check: bare `arriver` (no `à` + infinitive) means "to arrive"; only `arriver à + infinitif` means "to manage to / succeed in doing" — this is exactly the grammar point of the lesson (`grammar_point: "verbe + infinitif : « à » ou « de »"`). The vocab bank (`content/b1/vocab/verbs.yaml`, entry `arriver_a`) correctly glosses `arriver à` as "to manage to (+ infinitive)", confirming the `accept` entry is the outlier.
- Runtime behavior confirmed: traced the answer-checking path for `translate` exercises. `TranslateExercise` (`app/content/models.py:82-92`) declares `accept: list[str] = []` and a `via_tutor: bool = True` field, but `via_tutor` is not read anywhere in `app/` or `web/src` — there is no LLM/tutor routing wired up for this exercise type today. Grading happens entirely client-side in `web/src/screens/Lesson.tsx:211-223` (`Translate` component): `accept = [ex.answer, ...ex.accept]`, and the Check button calls `onChecked(accept.some((a) => norm(a) === norm(val)))`. So submitting the bare string `arriver` is normalized and directly string-matched against the `accept` list — there is no other validation layer, semantic check, or LLM tolerance step. Accepting `arriver` unconditionally marks the learner correct for a mistranslation.
- Against spec: `qa/README.md` scope note only exempts missing-LLM-provider 503s for Drill/Writing/Speaking; this is a plain `content` YAML defect in a deterministic (non-LLM) exercise type, squarely in scope.
- Verdict: validated
- Rationale: Real defect, high severity as filed — the exercise actively teaches/rewards a wrong translation in a lesson whose entire point is the preposition distinction. Fix is a one-line content edit (drop `arriver` from `accept`, optionally add legitimate `arriver à faire`-style variants), not a code change.

## Critic
- Challenged the pm's central runtime claim independently rather than trusting the citation: read `web/src/screens/Lesson.tsx:211-223` myself. `Translate` builds `accept = [ex.answer, ...ex.accept]` and checks `accept.some((a) => norm(a) === norm(val))`, and `norm = (s) => s.trim().toLowerCase().replace(/\s+/g, " ")` — no accent-folding, no fuzzy/semantic matching. Also grepped `via_tutor` across `app/` and `web/src`: it's declared on `TranslateExercise` (`app/content/models.py:92`) but read nowhere, so the "maybe this is deliberate leniency because grading is LLM/fuzzy" hypothesis is false — there is no tolerance layer at all, it's exact string match. This closes off the strongest reason this might not be a bug.
- Checked severity against the README ladder (`blocker > high > medium > low`): "high" fits — the description "broken/wrong" applies directly, since the exerise doesn't just fail to catch an error, it actively affirms a wrong translation as correct. Not blocker (doesn't stop progress), not medium (this isn't merely confusing, it's factually wrong).
- Cross-lesson sanity check: surveyed all `translate` exercises in the 6 new B1/B2 verb lessons (verbes-b1-01/02/03, verbes-b2-01/02/03). Only the three "verb+preposition" grammar-point lessons (b1-01, b1-02, b2-01) have this accept-list pattern; the other three have no preposition to strip and their accept lists are unremarkable. Confirms this is a real, narrow authoring bug class (preposition stripped without checking meaning), not an overreach.
- No grounds found to overturn. Verdict stands.
- Final status: validated

## Fix
`content/b1/lessons/verbes-b1-01.yaml`: removed `accept: ["arriver"]` from exercise
`verbes-b1-01.e8` entirely (the bare `"arriver"` was the only entry, and it means
"to arrive" — a different verb — not "to manage to"; no genuine meaning-preserving
lenient variant exists for this answer, since the correct form is exactly
`"arriver à"` and there's no accent/spelling variant to add per the file's house
style). `answer: "arriver à"` is unchanged, so the exercise now requires the
preposition, matching the lesson's own grammar point (verb + à/de + infinitive).
Verified with `scripts/check_content.py` (content OK) and
`tests/test_content_invariants.py` (5 passed).
