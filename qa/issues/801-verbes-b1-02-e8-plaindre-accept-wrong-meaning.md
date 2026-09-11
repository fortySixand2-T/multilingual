---
id: 801
title: "translate exercise verbes-b1-02.e8 accepts bare 'plaindre' for 'to complain', teaching the wrong verb meaning"
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-09-10
---

## Steps to reproduce
1. Read `content/b1/lessons/verbes-b1-02.yaml`, exercise `verbes-b1-02.e8`:
   ```yaml
   - id: verbes-b1-02.e8
     type: translate
     prompt: "Translate: “to complain”"
     answer: "se plaindre"
     accept: ["plaindre", "se plaindre de"]
   ```
2. Submit the answer `plaindre` (no reflexive pronoun) for the prompt "to
   complain".

## Expected
Only translations meaning "to complain" should be accepted. The lesson's own
grammar point is pronominal verbs (`grammar_point: "les verbes pronominaux dans
les démarches quotidiennes"`), so dropping the reflexive `se` is exactly the
mistake the lesson should catch, not reward.

## Actual
`accept: ["plaindre", ...]` marks the bare, non-reflexive `plaindre` as correct
for "to complain". But transitive `plaindre` (without `se`) means "to pity
(someone)" — e.g. "je le plains" = "I pity him" — a different verb sense from
reflexive "se plaindre" (to complain). Accepting the bare form teaches a wrong
translation and contradicts the lesson's own pronominal-verb teaching point.

Note `accept: ["se plaindre de", ...]` in the same list is fine/defensible
(same verb, includes the common preposition variant); only the bare `plaindre`
entry is the bug.

## Notes
Same bug class as `verbes-b1-01.e8` (issue 800): an `accept` entry that strips
away the exact grammatical element (reflexive pronoun / preposition) the lesson
is designed to teach, changing the verb's meaning rather than just being a
lenient spelling/article variant. Fix: remove `plaindre` from `accept`.

## Triage
- Explanation: Confirmed in `content/b1/lessons/verbes-b1-02.yaml:58-62`: exercise `verbes-b1-02.e8` has `answer: "se plaindre"`, `accept: ["plaindre", "se plaindre de"]`. French usage check: transitive `plaindre` (no reflexive `se`) means "to pity (someone)" (e.g. "je le plains" = "I pity him"), a different verb sense from the reflexive/pronominal `se plaindre` ("to complain"). The lesson's own grammar point is pronominal verbs (`grammar_point: "les verbes pronominaux dans les démarches quotidiennes"`), so dropping `se` is precisely the error the lesson exists to catch. `se plaindre de` (also in the accept list) is a legitimate, meaning-preserving variant and is not in question.
- Runtime behavior confirmed: same code path as issue 800 — `web/src/screens/Lesson.tsx:211-223` does client-side exact string matching (after `norm()`) against `[answer, ...accept]`, no LLM/tutor layer involved despite the `via_tutor` field on `TranslateExercise` (`app/content/models.py:82-92`), which is unused anywhere in `app/` or `web/src`. Submitting `plaindre` is marked correct for "to complain".
- Against spec: in-scope content defect in a deterministic exercise type; not covered by the LLM-provider scope exemption in `qa/README.md`.
- Verdict: validated
- Rationale: Same bug class and same reasoning as issue 800 — accepting a form that changes the verb's actual meaning, in a lesson whose teaching point is exactly the grammatical element being dropped. Fix is a one-line content edit (drop `plaindre` from `accept`, keep `se plaindre de`).

## Critic
- Independently re-verified (not re-trusting issue 800's shared citation): `web/src/screens/Lesson.tsx:211-223` does exact string match via `norm()` (trim/lowercase/collapse-whitespace only, no accent-folding or semantic tolerance) against `[answer, ...accept]`; `via_tutor` on `TranslateExercise` is unused anywhere in `app/` or `web/src`. So there is no fuzzy-grading layer that would make `accept: ["plaindre", ...]` a deliberate leniency choice — submitting bare `plaindre` is mechanically marked correct.
- French usage check stands: transitive `plaindre` (no `se`) = "to pity," a genuinely different verb sense from pronominal `se plaindre` = "to complain." This is a meaning change, not a spelling/article leniency, same bug class as 800.
- Severity "high" matches the README ladder (broken/wrong translation actively affirmed) — appropriate, same as 800.
- No case found for rejecting/deferring — this isn't a judgment call like 802, it's a plain wrong-meaning accept entry contradicting the lesson's own grammar point.
- Final status: validated

## Fix
`content/b1/lessons/verbes-b1-02.yaml`: exercise `verbes-b1-02.e8`'s `accept` list
changed from `["plaindre", "se plaindre de"]` to `["se plaindre de"]` — removed the
bare, non-reflexive `"plaindre"` (means "to pity someone", a different verb sense),
kept the legitimate `"se plaindre de"` variant. `answer: "se plaindre"` is
unchanged, so the reflexive `se` is now required, matching the lesson's pronominal-
verbs grammar point. Verified with `scripts/check_content.py` (content OK) and
`tests/test_content_invariants.py` (5 passed).
