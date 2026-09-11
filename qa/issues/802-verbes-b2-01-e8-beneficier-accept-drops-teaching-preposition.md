---
id: 802
title: "translate exercise verbes-b2-01.e8 accepts bare 'bénéficier'/'beneficier', dropping the preposition that is this lesson's whole teaching point"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-09-10
---

## Steps to reproduce
1. Read `content/b2/lessons/verbes-b2-01.yaml`, exercise `verbes-b2-01.e8`:
   ```yaml
   - id: verbes-b2-01.e8
     type: translate
     prompt: "Translate: “to benefit from”"
     answer: "bénéficier de"
     accept: ["beneficier de", "bénéficier", "beneficier"]
   ```

## Expected
The lesson (`verbes-b2-01`, "Verbs + preposition") exists specifically to drill
"verb + preposition" as an inseparable unit (`grammar_point: "verbe + préposition
: « à » ou « de »"`). Every other `translate` exercise checked in this round's 6
new verb lessons that keeps the same verb meaning also keeps the preposition
requirement; the two exercises that drop the preposition AND change meaning were
filed as issues 800/801.

## Actual
Unlike issues 800/801, `bénéficier` alone does not change meaning (it's still
recognizably "to benefit"), so this is not a wrong-translation bug the way
arriver/plaindre are. But it is inconsistent with the lesson's own stated
purpose: accepting the bare verb without `de` teaches the learner that the
preposition is optional, in a lesson whose entire point is that it isn't.

## Notes
Severity kept low because the accepted answer is not actually wrong-meaning,
just under-strict for this lesson's specific pedagogical goal. Flagging per the
round charter's instruction to audit `accept` lists across all 6 new verb
lessons for prepositions being dropped "where the preposition IS the teaching
point of the deck." Triage may reasonably reject this as intentional leniency;
raising for a judgment call rather than re-filing it silently.

## Triage
- Explanation: Confirmed in `content/b2/lessons/verbes-b2-01.yaml:58-62`: exercise `verbes-b2-01.e8` has `answer: "bénéficier de"`, `accept: ["beneficier de", "bénéficier", "beneficier"]`. French usage check: unlike issues 800/801, `bénéficier` alone is not a wrong-meaning bug — it's still recognizably "to benefit", so this is a strictness/pedagogy question, not a correctness one. However, the lesson (`verbes-b2-01`, "Verbs + preposition") is explicitly and narrowly about verb+preposition as a fixed unit: `grammar_point: "verbe + préposition : « à » ou « de »"`; e5's `explain` field states outright "la préposition fait partie du verbe" (the preposition is part of the verb); e9 (`listen_type`) explicitly instructs "Type the verb you hear, with its preposition." The lesson is internally consistent about requiring the preposition everywhere else — e8's bare-verb accept entries are the one place that contradicts the lesson's own stated teaching point.
- Runtime behavior confirmed: same client-side exact-match path as issues 800/801 (`web/src/screens/Lesson.tsx:211-223`); no semantic/LLM layer. Submitting bare `bénéficier`/`beneficier` is marked correct.
- Against spec: not a wrong-meaning defect, so it's a closer call than 800/801, but it directly undercuts this specific lesson's stated pedagogical goal (per e5's own explain text and e9's own prompt), and the round charter explicitly asked for this class of check.
- Verdict: validated
- Rationale: Agree with the filer's low-severity framing — this is a leniency/consistency issue, not a wrong-answer-taught-as-right issue like 800/801. But given the lesson's explicit, repeated emphasis (in its own explain/prompt text) that the preposition is not optional, leaving the bare-verb accepts in place is inconsistent with the lesson's own design and worth a one-line content fix (drop `"bénéficier"` and `"beneficier"` from `accept`, keep `"beneficier de"` as the accent-free spelling variant of the correct answer).

## Critic
- This is the genuine judgment call of the three, so I actively looked for the strongest case to reject/defer it rather than rubber-stamp the pm.
- Considered: "maybe `accept` lists are just deliberately loose because grading is fuzzy/LLM-tolerant, so a missing preposition is intentionally forgiven." Checked independently: it's not. `web/src/screens/Lesson.tsx:211-223` is exact string match on `norm(val)` (trim/lowercase/collapse-space only — confirmed by reading the `norm` definition at line 7, no accent-stripping either), and `via_tutor` on `TranslateExercise` (`app/content/models.py:92`) is dead code, unused in `app/` or `web/src`. There is no tolerance mechanism; every entry in `accept` is a deliberate authoring choice, not a side-effect of fuzzy grading. This removes the main reason to wave this off as "the grader is lenient by design."
- Considered: "bare `bénéficier` isn't really wrong, so this is just a style/pedagogy nitpick not worth code churn." Checked the lesson's own text rather than taking the pm's characterization on faith: e5's `explain` field literally says "la préposition fait partie du verbe" (the preposition is part of the verb), and e9 instructs "Type the verb you hear, with its preposition." This is the lesson itself stating its teaching contract in two other exercises — e8 accepting the bare verb directly contradicts what the lesson already tells the learner elsewhere. That's a real internal-consistency defect, not just an outside opinion about what the lesson "should" emphasize.
- Considered: "fixing risks removing a legitimate variant." Checked: `bénéficier` in French is always used with `de` for this sense (there's no standalone transitive "bénéficier quelque chose"); removing the bare forms drops nothing genuine. The accent-free `"beneficier de"` entry is legitimately needed (norm() doesn't fold accents, and the same accent-free-variant pattern appears in sibling lessons, e.g. `ameliorer`, `mettre en oeuvre`), so the pm's proposed fix (keep `"beneficier de"`, drop the two bare forms) is precisely scoped and doesn't overcorrect.
- Considered: "cost/benefit — is this worth dev-fixer time at low severity?" The fix is a one-line YAML edit removing two list entries, zero code risk, and the round charter explicitly asked for this class of audit. Low severity correctly reflects that it's not a wrong-meaning bug like 800/801, but low severity is not the same as no-fix — README's ladder still schedules low-severity items, it just deprioritizes them relative to high.
- Also cross-checked against the other 5 new verb lessons (see issue 800's critic note): b1-03, b2-02, b2-03 don't have a preposition to strip, so this isn't a cherry-picked example — it's the third and mildest instance of the same authoring pattern as 800/801 (preposition dropped in an accept list for a verb+prep lesson), which supports treating it consistently rather than special-casing it as acceptable.
- Conclusion: no strong case survives for reject/defer here. Confirmed validated, not overturned.
- Final status: validated

## Fix
`content/b2/lessons/verbes-b2-01.yaml`: exercise `verbes-b2-01.e8`'s `accept` list
changed from `["beneficier de", "bénéficier", "beneficier"]` to `["beneficier de"]`
— removed the two bare-verb entries (`"bénéficier"`, `"beneficier"`) that let the
preposition be dropped, keeping only the accent-free spelling variant of the
correct answer (`answer: "bénéficier de"` unchanged). This now matches the
lesson's own stated teaching point (verb + preposition as a fixed unit, per e5's
explain text and e9's prompt). Verified with `scripts/check_content.py` (content
OK) and `tests/test_content_invariants.py` (5 passed).
