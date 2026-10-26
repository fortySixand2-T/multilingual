---
id: 850
title: Impersonal verbs (pleuvoir, neiger) get a wrongly-prepended "je" in generated forms
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Sign up / log in (`@qa.test` email, invite code `friend-001`).
2. `POST /vocab/personal/from-word {"word":"pleuvoir"}` -> card_key `uv:pleuvoir`.
3. `POST /vocab/forms {"card_key":"uv:pleuvoir"}`.
4. Repeat steps 2-3 for `neiger` (card_key `uv:neiger`).
5. For comparison, repeat for `falloir` (card_key `uv:falloir`).

## Expected
Impersonal verbs only take the subject "il" ("il pleut", "il a plu", "il pleuvra",
"il pleuvait"; "il neige", "il a neigé", "il neigera"). `_verb_form` in
`app/content/forms.py` should never prepend "je" to these.

## Actual
`pleuvoir` forms:
```json
{"forms":[{"label":"présent","fr":"je pleut"},{"label":"passé composé","fr":"j'ai pleuvu"},{"label":"futur","fr":"je pleuvra"},{"label":"imparfait","fr":"je pleuvait"}]}
```
`neiger` forms:
```json
{"forms":[{"label":"présent","fr":"je neige"},{"label":"passé composé","fr":"j'ai neigé"},{"label":"futur","fr":"je neigerai"},{"label":"imparfait","fr":"je neige"}]}
```
All four forms of both verbs are ungrammatical — "je pleut"/"je pleuvra"/"je
neige" (for "it rains"/"it will rain"/"it snows") are nonsensical; impersonal
verbs cannot take "je" as subject.

By contrast, `falloir` (card_key `uv:falloir`) came back correct in every form
because the model itself already included "il " in its reply, which satisfies
`_SUBJECT.match` and skips the rescue:
```json
{"forms":[{"label":"présent","fr":"il faut"},{"label":"passé composé","fr":"il a fallu"},{"label":"futur","fr":"il faudra"},{"label":"imparfait","fr":"il fallait"}]}
```

## Notes
This is QA round 059's H2, probing the `app/content/forms.py` rule engine added
in PR #121 (fix for issue 830). `_verb_form` (lines ~116-119):
```python
def _verb_form(fr: str, lemma: str) -> str:
    if not _SUBJECT.match(fr) and not lemma.startswith(("se ", "s'")):
        fr = "je " + fr  # the model often drops the pronoun: 'ai mangé'
    return _elide(fr, before_h=not lemma.lower().startswith(_H_ASPIRE_VERBS))
```
The guard only excludes reflexive lemmas (`se `/`s'`) from the "prepend je"
rescue; it does not exclude impersonal verbs (`pleuvoir`, `neiger`, `falloir`,
`geler` used impersonally, `s'agir de`, etc.). When the model correctly drops
the subject for an impersonal verb (e.g. replies with bare "pleut"), the rescue
wrongly inserts "je ", producing ungrammatical French that is then stored and
served to the learner as the canonical conjugation. Confirmed with 2/2 sampled
impersonal verbs (pleuvoir, neiger); `falloir` only avoided the bug because the
model happened to include "il" itself.

## Triage
- Explanation: confirmed by direct code read, `app/content/forms.py::_verb_form`
  (lines ~116-119, added/modified by this PR's `tidy_forms` rule engine):
  `if not _SUBJECT.match(fr) and not lemma.startswith(("se ", "s'")): fr = "je " + fr`.
  The reflexive exclusion (`se `/`s'`) was added by 686cebd specifically to stop the
  rescue from fighting reflexive pronouns, but no equivalent exclusion exists for
  impersonal verbs — there's no impersonal-verb list anywhere in `forms.py` (contrast
  with the existing `_H_ASPIRE_VERBS` list, which is the right shape for this kind of
  fix). The repro is exactly what the code predicts: a bare "pleut"/"neige" reply (no
  subject) hits the rescue and gets "je " prepended unconditionally.
- Against spec: the system prompt (`_FORMS_SYSTEM`, also touched by this PR) explicitly
  tells the model "1st person singular 'je' unless the verb is impersonal" — i.e. the
  PR's own prompt anticipates impersonal verbs dropping "je", but the post-processing
  rescue added in the same PR doesn't honor that exception.
- Verdict: validated
- Rationale: squarely new code from 686cebd (the rescue clause + its reflexive-only
  exclusion), 100% reproducible on both sampled impersonal verbs, produces
  ungrammatical French stored as canonical conjugation for a learner. Cheap, surgical
  fix in scope: add a small impersonal-verb set (pleuvoir, neiger, falloir, geler used
  impersonally, s'agir, etc.) to the exclusion alongside the existing reflexive check —
  same shape as the existing `_H_ASPIRE_VERBS` special-case list already in the file.

## Critic
- Challenge: the triage calls this a "cheap, surgical fix... same shape as
  `_H_ASPIRE_VERBS`" — worth checking that claim literally against the code rather
  than taking the analogy on faith, since `_H_ASPIRE_VERBS` is used inside `_elide`
  for a different purpose (gating an elision regex, not gating the "je" rescue).
- Holds up? Yes. Read `app/content/forms.py::_verb_form` directly: the rescue is
  `if not _SUBJECT.match(fr) and not lemma.startswith(("se ", "s'")): fr = "je " + fr`.
  Adding `and lemma.lower() not in _IMPERSONAL_VERBS` (a plain tuple/set membership
  check, exactly the same shape as the existing `startswith(("se ", "s'"))` reflexive
  guard, and structurally identical to how `_H_ASPIRE_VERBS` is consulted a few lines
  later) is in fact a one-line, mechanically trivial change — no new control flow, no
  new function, no risk to the other 850-adjacent paths (851/852/853). The repro is
  clean: both sampled impersonal verbs are 100% reproducible, the fix target is
  exactly the clause named in the report, and the system prompt (also touched by this
  PR) already tells the model to omit "je" for impersonal verbs, so the rescue is
  actively fighting the prompt's own correct instruction. No reason to defer this.
- Final verdict: validated

## Fix
Added `_IMPERSONAL_VERBS` (pleuvoir, neiger, falloir, geler, s'agir, grêler, tonner) to
`app/content/forms.py` and excluded them from the "prepend je" rescue in `_verb_form`,
alongside the existing reflexive exclusion.
- Files: `app/content/forms.py`
- Tests: `tests/test_forms.py::test_impersonal_verbs_keep_il_not_je`
