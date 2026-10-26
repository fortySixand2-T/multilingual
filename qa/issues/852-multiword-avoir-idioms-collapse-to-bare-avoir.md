---
id: 852
title: Multi-word "avoir X" idioms (avoir faim, avoir besoin de) generate forms that drop the complement, collapsing to bare avoir conjugations
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Sign up / log in.
2. `POST /vocab/personal/from-word {"word":"avoir faim"}` -> pos comes back
   "verb", card_key `uv:avoir_faim`.
3. `POST /vocab/forms {"card_key":"uv:avoir_faim"}`.
4. Repeat with `"avoir besoin de"` -> card_key `uv:avoir_besoin_de`.
5. For comparison, repeat with a non-"avoir" multi-word phrase, `"être content
   de"` -> card_key `uv:etre_content_de`.

## Expected
Forms for a multi-word verb headword should conjugate the whole phrase,
keeping the fixed complement in every tense: "j'ai faim", "j'ai eu faim",
"j'aurai faim", "j'avais faim" (and similarly "j'ai besoin de", "j'aurai
besoin de", "j'avais besoin de").

## Actual
`avoir faim`:
```json
{"forms":[{"label":"présent","fr":"j'ai"},{"label":"passé composé","fr":"j'ai eu"},{"label":"futur","fr":"j'aurai"},{"label":"imparfait","fr":"j'avais"}]}
```
`avoir besoin de`:
```json
{"forms":[{"label":"présent","fr":"j'ai"},{"label":"passé composé","fr":"j'ai eu"},{"label":"futur","fr":"j'aurai"},{"label":"imparfait","fr":"j'avais"}]}
```
Both phrases lose their complement entirely in every one of the 4 forms,
collapsing to bare "avoir" conjugations — a learner studying "avoir faim"
would be shown forms that look identical to generic "avoir", with no trace of
the idiom they added. Reproduced identically (same pattern, same degenerate
output) on both of the 2 "avoir X" phrases sampled.

By contrast `être content de` (a multi-word adjectival-complement phrase) is
unaffected — it correctly keeps "content de" in all 4 forms:
```json
{"forms":[{"label":"présent","fr":"je suis content de"},{"label":"passé composé","fr":"j'ai été content de"},{"label":"futur","fr":"j'aurai été content de"},{"label":"imparfait","fr":"j'étais content de"}]}
```

## Notes
QA round 059's H9, probing `app/content/forms.py` with multi-word headwords.
`generate_forms` sends the full lemma to the model (`prompt = f"Headword:
{lemma}\nPart of speech: {pos}"`, `app/content/forms.py` line ~169) — the
truncation to bare "avoir" happens in the model's reply itself, not in a
string-processing rule, and `_verb_form`'s rescue/elision logic has no
mechanism to detect or restore a dropped complement, so the degenerate reply
is stored and served as-is. Whether the eventual fix belongs in the prompt
(e.g. instructing the model to repeat the full headword in every form) or in
post-processing validation, the net effect reaching the learner today is a
systematically wrong set of forms for this class of idiom, confirmed 2/2 on
"avoir faim" / "avoir besoin de".

## Triage
- Explanation: confirmed by code read that the defect sits upstream of any code this
  PR added. `generate_forms` builds `prompt = f"Headword: {lemma}\nPart of speech:
  {pos}"` unchanged by 686cebd, and sends it to a `_FORMS_SYSTEM` prompt whose verb
  section was edited by this PR only to add "each with its subject pronoun" — nothing
  about preserving a multi-word complement was ever instructed, before or after. The
  degenerate "j'ai" reply is the 7B model dropping the complement on its own; the new
  `_verb_form`/`tidy_forms` rule code never touches or re-derives the complement
  (there's no mechanism in the whole file that could — it only restores a missing
  subject pronoun and fixes elision), so it has no opportunity to introduce or fix
  this. `être content de` surviving intact (model-driven, not rule-driven) supports
  that this is pure model-reply variance by idiom shape, not a rule bug.
- Against spec: no prompt or schema text, before or after this PR, ever told the
  model to repeat a multi-word headword's complement in every conjugated form — this
  gap existed in the `generate_forms` prompt design prior to 686cebd and is unchanged
  by it.
- Verdict: deferred
- Rationale: genuine, learner-visible, 2/2-reproducible defect, but it is not caused
  by this PR's new rule-engine code (tidy_forms has no complement-restoring
  mechanism to regress, and the multi-word-prompt gap predates this PR's changes to
  the verb-forms prompt). Fixing it properly needs either a prompt rework (instruct
  the model to echo the full headword/complement per form) or new post-processing
  that detects the single-word collapse and re-appends the complement — a larger,
  dedicated change to forms.py's prompt/validation strategy rather than a surgical
  rule patch like 850/851. Route to a follow-up round scoped to multi-word-headword
  handling in `generate_forms`.

## Critic
- Challenge: the triage's "tidy_forms has no complement-restoring mechanism... needs
  a prompt rework" claim is exactly the "no surgical fix available" framing this
  round was told to stress-test before accepting. `tidy_forms` already restores one
  kind of model-dropped content (a missing subject pronoun, via the "je" rescue) —
  worth checking whether the same restoration trick generalizes to a dropped
  multi-word complement, rather than trusting that it structurally can't.
- Holds up? No — a cheap, rule-level mitigation is available and the triage didn't
  find it. `_verb_form(fr, lemma)` already receives the full multi-word lemma
  ("avoir faim") as `lemma`; nothing stops it from splitting off the fixed
  complement (`lemma.partition(" ")[2]`, i.e. "faim" / "besoin de") and, if that
  complement string is missing from the model's reply, appending it — the same
  "rule restores what the small model dropped" shape as the existing je-rescue and
  l'/j' elision, in the same function, no prompt change needed:
  ```python
  head, _, complement = lemma.partition(" ")
  if complement and complement.lower() not in fr.lower():
      fr = f"{fr} {complement}"
  ```
  Traced through the actual repros: "j'ai" + "faim" -> "j'ai faim"; "j'ai eu" +
  "faim" -> "j'ai eu faim"; "j'aurai"/"j'avais" + "faim" -> correct; same for
  "besoin de" across all 4 forms — matches the issue's own "Expected" column
  exactly. `être content de` (already correct) is untouched since "content de" is
  already present in its output, so the check is a no-op there. This is not as
  trivial as 850/851's one-set-literal fix — the naive version above has a real
  edge case (a reply that already contains a *partial* complement, e.g. "j'ai
  besoin" for "avoir besoin de", would get the full complement re-appended and
  duplicate "besoin": "j'ai besoin besoin de" — dev-fixer should check for a
  partial prefix overlap before blindly appending, not just full-string absence) —
  but it's the same order of complexity as 853's reflexive auxiliary swap, which
  this round already accepted as in-scope despite being "more involved than
  850/851." Difficulty alone isn't the deferral bar this round set for 853; it
  shouldn't be the bar here either.
- Final verdict: **validated** (overturning qa-pm's `deferred`). The PM's
  conclusion that no rule-level fix exists is incorrect — a complement-preservation
  rule analogous to the existing je-rescue is available in the same function, same
  file, same design philosophy as 850/851/853's fixes. Flag for dev-fixer: guard
  the append against partial-complement overlap, not just a blind "complement not
  in fr" substring check, to avoid duplicated words on a partially-correct reply.

## Fix
`_verb_form` now receives the full lemma already; added `_restore_complement`, scoped
to lemmas whose head word is "avoir" (so a reflexive lemma's second word, e.g. "laver"
in "se laver", is never mistaken for a fixed complement). It appends the idiom's
complement (`lemma.partition(" ")[2]`) when the model's reply doesn't already contain
it — checking for a partial-prefix overlap first (e.g. "j'ai besoin" for "avoir besoin
de") so the complement isn't duplicated.
- Files: `app/content/forms.py`
- Tests: `tests/test_forms.py::test_avoir_idiom_keeps_its_complement`,
  `test_avoir_idiom_partial_complement_overlap_not_duplicated`,
  `test_reflexive_lemma_second_word_is_not_treated_as_a_complement`
