---
id: 853
title: Reflexive verbs' passé composé systematically drops the reflexive pronoun and uses avoir instead of être (rule engine has no reflexive-aware check for compound tenses)
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Sign up / log in.
2. For each of these reflexive verbs, get/confirm a card_key then
   `POST /vocab/forms`:
   - content-bank: `se_lever`, `se_depecher`, `se_laver`, `se_coucher`,
     `se_reveiller` (card_key = bare content id, e.g. `{"card_key":"se_lever"}`)
   - personal (`POST /vocab/personal/from-word` first): `s'amuser`,
     `se souvenir`, `s'inquiéter`, `se rappeler` (card_key `uv:<slug>`)
3. Read the "passé composé" row of each response.

## Expected
Reflexive verbs form the passé composé with être + past participle, keeping
the reflexive pronoun agreeing with the subject: "je me suis levé(e)", "je
m'suis amusé(e)"/"je me suis amusé(e)", "je me suis souvenu(e)", "je me suis
inquiété(e)", "je me suis rappelé(e)", "je me suis lavé(e)", "je me suis
couché(e)", "je me suis réveillé(e)", "je me suis dépêché(e)".

## Actual
9/9 sampled reflexive verbs produced an ungrammatical passé composé: the
reflexive pronoun is dropped (or, in one case, garbled) and the auxiliary is
avoir instead of être.

| verb | passé composé returned |
|---|---|
| se lever | `j'ai levé` |
| se dépêcher | `j'ai dépêché` |
| se laver | `j'ai lavé` |
| se coucher | `j'ai couché` |
| se réveiller | `j'ai réveillé` |
| s'amuser | `j'ai amusé` |
| se souvenir | `j'ai souvenir` (not even a participle) |
| s'inquiéter | `j'ai s'inquiété` (infinitive's "s'" stuck onto the participle) |
| se rappeler | `j'ai rappelé` |

All 9 are wrong in the same two ways (missing reflexive clitic, wrong
auxiliary); 2 of the 9 (se souvenir, s'inquiéter) are additionally malformed
beyond that. This is 100% reproducible across every reflexive verb sampled —
not an occasional model slip.

Other tenses for the same verbs (présent, futur, imparfait) mostly keep the
reflexive pronoun correctly (e.g. "je me lèverai", "je m'amusais", "je me
souviens"), so the defect is specific to the passé composé/compound-tense
case.

## Notes
QA round 059's H1 targeted a narrower, related mechanism: `_verb_form` in
`app/content/forms.py` skips its "prepend je if missing" rescue whenever
`lemma.startswith(("se ", "s'"))`, with the stated worry that a bare,
pronoun-less model reply (e.g. "me lève") would then be left with no subject
at all. That exact scenario was not observed in 9 samples — the model always
included "je"/"j'" as the grammatical subject. What was observed instead, and
is far more consistently reproducible, is that the code's only reflexive-aware
behavior is this one skip; there is no logic anywhere in `_verb_form` (or
elsewhere in `tidy_forms`) that checks whether a reflexive verb's compound
tense actually contains its reflexive clitic or uses être. Because of that
gap, the model's well-known tendency to drop the clitic and default to avoir
in compound tenses sails through completely uncorrected and is stored/served
as the canonical passé composé for every reflexive verb a learner adds — this
is likely the single most learner-visible defect of the four `forms.py`
hypotheses probed this round, since passé composé is a core A2 drill item and
the error is 100% reproducible rather than occasional.

## Triage
- Explanation: confirmed by code read. `tidy_forms`/`_verb_form` (both new in
  686cebd) have exactly one reflexive-aware line — the "skip the je-rescue for
  `se `/`s'` lemmas" guard — and nothing else anywhere in `forms.py` inspects
  whether a verb is reflexive when fixing a compound tense. The model's well-known
  tendency to drop the clitic and default to "avoir" in compound tenses for
  reflexive verbs is never checked or corrected, so it passes straight through.
- Against spec: unlike 852 (multi-word idiom collapse, which needs a prompt
  rethink the file was never designed to handle), reflexive passé composé is
  exactly the kind of thing the file's own stated design is supposed to catch:
  "whatever a rule can decide is decided here rather than by the model" (module
  docstring). Whether a reflexive verb's compound tense uses être + an
  agreeing reflexive pronoun is 100% rule-decidable (it's always true for every
  reflexive verb, no model judgment needed) — the same category of fix as the
  file's existing subject-pronoun rescue and l'/j' elision, just not implemented
  for this case.
- Verdict: validated
- Rationale: squarely in scope for this PR's new rule engine (same design
  philosophy, same file, same function family), 100% reproducible across all 9
  sampled reflexive verbs, and the single most learner-visible defect raised this
  round — passé composé is a core A2 drill item, and two of the nine samples
  (se souvenir, s'inquiéter) are additionally malformed beyond the clitic/
  auxiliary error. A fix is more involved than 850/851 (needs to detect a
  reflexive lemma + compound-tense label and rewrite to "<pronoun> <être-form>
  <clitic> <participle>"), but per this round's guidance, difficulty alone
  doesn't move this to `deferred` — it's a genuine, in-scope defect in exactly
  the code this PR shipped, and should be fixed, not routed to a separate round.

## Critic
- Challenge: the issue's own Notes section is careful to distinguish this from
  H1's original hypothesis (pronoun-dropping on a *bare* model reply) — worth
  verifying that distinction is real and that the "100% reproducible, only passé
  composé" framing isn't overstating what's actually a narrower or more variable
  bug. Also: is "reflexive verbs always take être + agreeing clitic in compound
  tenses" actually something `_verb_form` can decide correctly in every case it
  sees, or could a label-blind fix mis-fire on présent/futur/imparfait (which
  must NOT get an être rewrite)?
- Holds up? Yes, and the label-scoping concern is real but already handled by
  the data, not by the current code. Re-reading `_verb_form(fr, lemma)`: it
  receives `fr` and `lemma` only — no `label` parameter — and `tidy_forms`
  applies the same `fix` lambda to all 4 forms uniformly via
  `[{"label": f["label"], "fr": fix(f["fr"])} for f in forms]`. So today there
  is no way to apply an être-rewrite only to "passé composé" without first
  threading the label into `_verb_form` — the report's own fix sketch
  ("detect a reflexive lemma + compound-tense label") correctly identifies
  this as the needed shape, i.e. a real (if modest) refactor, not a one-liner,
  which is why the report accurately flags it as harder than 850/851 rather
  than claiming it's equally cheap. Confirmed the repro is real and distinct
  from H1: `_SUBJECT.match` is satisfied for all 9 compound-tense replies
  (each already has "j'ai..."), so the reflexive-skip guard in the je-rescue
  is irrelevant here — it's not that rescue misfiring, it's that nothing
  anywhere checks compound-tense reflexive auxiliary/clitic at all, exactly as
  claimed. The other 3 tenses (présent/futur/imparfait) don't need être, and
  nothing in the proposed fix shape would touch them if scoped correctly
  (reflexive-lemma AND label == "passé composé" only) — so the "could this
  mis-fire on tenses that don't need être" risk is avoidable by construction,
  not a reason to defer.
- Final verdict: validated

## Fix
Threaded the form `label` into `_verb_form` (via `tidy_forms`) so the fix is scoped to
exactly "passé composé" for reflexive lemmas. Added `_reflexive_passe_compose`, which
rewrites the model's reply (whatever avoir-based auxiliary/clitic combination it used)
to `<subject> <clitic> <être-form> <participle>`. Présent/futur/imparfait are
untouched since the rewrite only fires when `label == "passé composé"`.
- Files: `app/content/forms.py`
- Tests: `tests/test_forms.py::test_reflexive_passe_compose_uses_etre_and_restores_clitic`
