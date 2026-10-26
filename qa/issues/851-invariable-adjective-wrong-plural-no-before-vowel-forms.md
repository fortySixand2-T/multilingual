---
id: 851
title: Invariable color adjective "marron" gets a wrong rule-generated plural/feminine; beau/nouveau/vieux never get their before-vowel irregular forms
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Sign up / log in.
2. `POST /vocab/forms {"card_key":"marron"}` (content-bank a1 adjective card).
3. Repeat for `card_key":"beau"`, `"nouveau"`, `"vieux"` (all content-bank a1
   adjective cards).

## Expected
- `marron` used as a color adjective is invariable in French: masculine,
  feminine, masculine plural and feminine plural should all be "marron"
  ("des yeux marron", "une veste marron").
- `beau`, `nouveau`, `vieux` additionally have an irregular masculine-singular
  form used before a vowel-initial noun ("un bel homme", "un nouvel ami", "un
  vieil arbre") distinct from their ordinary masculine form ("un beau
  garçon"). The forms response has no way to surface this at all.

## Actual
`marron`:
```json
{"forms":[{"label":"masculine","fr":"marron"},{"label":"feminine","fr":"marronne"},{"label":"masculine plural","fr":"marrons"},{"label":"feminine plural","fr":"marronnes"}]}
```
`marronne`/`marrons`/`marronnes` are all wrong — invented, non-standard forms a
learner could easily take as correct, since they're presented as the
authoritative morphology for the word.

`beau`/`nouveau`/`vieux` all return only 4 forms (masculine, feminine,
masculine plural, feminine plural) with no "before a vowel" variant at all —
`bel`/`nouvel`/`vieil` are never produced:
```json
beau:    {"masculine":"beau","feminine":"belle","masculine plural":"beaux","feminine plural":"belles"}
nouveau: {"masculine":"nouveau","feminine":"nouvelle","masculine plural":"nouveaux","feminine plural":"nouvelles"}
vieux:   {"masculine":"vieux","feminine":"vieille","masculine plural":"vieux","feminine plural":"vieilles"}
```

## Notes
QA round 059's H3, probing `app/content/forms.py`'s `_adjective_plural` and
`_adjective_forms` (fix for issue 830). `_adjective_plural` has no invariable-
word exception at all:
```python
def _adjective_plural(w: str, *, feminine: bool) -> str:
    if w.endswith(("s", "x")):
        return w
    if not feminine and w.endswith("eau"):
        return w + "x"
    if not feminine and w.endswith("al") and w.lower() not in _AL_PLURAL_S:
        return w[:-2] + "aux"
    return w + "s"
```
`marron` ends in neither "s"/"x"/"eau"/"al", so it falls through to the
default `w + "s"` branch for the plural, and `_adjective_forms` always derives
the feminine from the model's reply or the bare lemma with no invariable-list
check, so "marronne" is accepted uncorrected. Other known invariable color/
descriptive adjectives (chic, sympa, super, orange when used as a color) would
hit the same gap — not independently retested this round to stay in budget,
but the same code path applies.

Separately, `_adjective_forms` always sets `masc = lemma` with no special-case
for `beau`/`nouveau`/`vieux`, and the 4-label output shape (masculine/feminine/
masc-plural/fem-plural) has no slot for the before-vowel form in the first
place — this is a missing feature of the forms schema, not just a wrong rule
result.

## Triage
This report bundles two distinct findings with different verdicts; splitting them:

1. **"marron" gets an invented, wrong feminine/plural ("marronne"/"marrons"/
   "marronnes").**
   - Explanation: confirmed by code read. `_adjective_plural` (new in 686cebd) has
     branches for `-s/-x` (unchanged), `-eau` (+x), `-al` (→ `-aux`, with an explicit
     exclusion set `_AL_PLURAL_S`) and a bare default of `w + "s"` — there is no
     invariable-word exception at all, so `marron` falls to the default and gets a
     fabricated plural/feminine. The file already has the right *pattern* for this
     (`_AL_PLURAL_S`, a hand-curated exception set) — it's just missing the
     invariable-adjective case entirely.
   - Against spec: none explicit, but the PR's own stated goal ("whatever a rule can
     decide is decided here rather than by the model") implies the rule should be
     right, not merely rule-shaped; inventing "marronne" is worse than the pre-PR
     behavior of trusting the model's (at least plausible) feminine guess.
   - Verdict: validated. Squarely new code (`_adjective_plural`/`_adjective_forms`),
     cheap surgical fix in scope — add an `_INVARIABLE_ADJECTIVES` set (marron, chic,
     sympa, super, orange/color nouns-as-adjectives, …) alongside the existing
     `_AL_PLURAL_S` pattern, short-circuiting to the bare lemma for all four forms.

2. **beau/nouveau/vieux never get a masculine-before-vowel form (bel/nouvel/viel).**
   - Explanation: confirmed — the 4-label schema (masculine/feminine/masc
     plural/fem plural) has never had a 5th "before vowel" slot; this isn't a
     regression in the rule logic, it's an absence of a slot the schema never
     defined, in the system prompt or the output shape, before or after this PR.
   - Against spec: no spec (prompt, schema docstring, or original issue 830) ever
     described a before-vowel slot; adding one is a product/schema decision (new
     label, new prompt instruction, new UI row) rather than a bug fix to existing
     rule code.
   - Verdict: deferred. Real gap, but out of scope for a quick patch to this PR's
     rule engine — it needs a schema change (new label + prompt update), which is a
     product decision about whether "before-vowel form" is worth a 5th row for a
     small, closed class of irregular adjectives (beau/nouveau/vieux, maybe fou/mou).
     Route to a future forms-schema round rather than bundling into this PR's fix.

- Overall issue verdict: **validated** (finding 1 is the actionable, in-scope defect;
  finding 2 is noted above as deferred and should not block or expand the fix for
  finding 1).

## Critic
- Challenge: a single `validated` status on an issue that bundles a clearly-in-scope
  bug (finding 1) with a clearly-out-of-scope schema question (finding 2) risks
  sending dev-fixer a vague mandate — does "validated" implicitly bless building the
  bel/nouvel/vieil slot too, since it's in the same issue number? That's the one
  thing worth stress-testing before letting this through as-is rather than asking
  qa-pm to re-split it.
- Holds up? The per-finding split and the explicit "should not block or expand"
  sentence already do the job a second issue number would have done — re-splitting
  now would just be process overhead on content that's already cleanly separated in
  the triage text. Confirmed finding 1 independently: `_adjective_plural` (read in
  full above) has branches for `-s/-x`, `-eau`, `-al` (with an exception set) and a
  bare `w + "s"` default with no invariable-word branch at all, so `marron` -> plural
  "marrons"/feminine "marronne" is exactly as predicted, and an `_INVARIABLE_ADJECTIVES`
  set (same pattern as `_AL_PLURAL_S`) is a clean, bounded, one-set-literal fix.
  Finding 2 (bel/nouvel/vieil) is correctly scoped out: the 4-label schema has never
  had a 5th slot in the system prompt or the output shape, before or after this PR —
  adding one is a product decision (new label text, new UI row), not a bug in code
  this PR shipped, so `deferred` for that half is right.
- Final verdict: validated — with the explicit caveat, restated here for dev-fixer:
  the fix for this issue number is the `_INVARIABLE_ADJECTIVES` set only. Do not
  attempt a before-vowel masculine slot (bel/nouvel/vieil) under this issue; that
  needs its own schema-design issue if the product wants it.

## Fix
Added an `_INVARIABLE_ADJECTIVES` set (marron, chic, sympa, super, orange, kaki,
turquoise) to `app/content/forms.py`; `_adjective_forms` short-circuits to the bare
lemma for all four form slots when the lemma is in that set. The before-vowel
masculine form (bel/nouvel/vieil) was explicitly left out of scope per the critic's
note — not attempted.
- Files: `app/content/forms.py`
- Tests: `tests/test_forms.py::test_invariable_adjective_never_gets_a_fabricated_plural_or_feminine`
