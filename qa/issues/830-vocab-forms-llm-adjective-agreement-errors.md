---
id: 830
title: /vocab/forms LLM output has adjective agreement/elision errors (valid JSON, wrong French)
severity: medium
area: content
persona: edge-case-breaker
status: fixed
found: 2026-10-25
---

## Steps to reproduce
1. Sign up (`friend-001`), add personal cards for adjectives via
   `POST /vocab/personal/from-word` with `{"word":"ébouriffant"}`,
   `{"word":"intéressant"}`, `{"word":"amusant"}`.
2. For each, `POST /vocab/forms {"card_key":"uv:<word>"}`.
3. Inspect the `fr` value under the `"masculine"` label.

## Expected
The JSON schema is fine (this round's H1 target: raw-mode `/api/generate` +
`format: json` through a real endpoint) — but the *content* of each labelled
form should be grammatically correct French matching its own label.

## Actual
Three separate adjectives, three distinct grammar errors, each internally
inconsistent with its own label:

- `uv:ebouriffant` → `{"label":"masculine","fr":"ce ébouriffant"}` — missing
  the mandatory elision: before a vowel-initial word, masculine singular "ce"
  becomes "cet". Should be "cet ébouriffant".
- `uv:interessant` → `{"label":"masculine","fr":"un intéressante"}` — the
  article is masculine ("un") but the adjective ending is feminine
  ("intéressante"). Should be "un intéressant". The feminine row for the same
  card correctly says `"une intéressante"`, so the model has simply copied
  the feminine adjective form into the masculine row.
- `uv:amusant` (fine, for contrast): `{"label":"masculine","fr":"l'amusant"}`
  is at least self-consistent, but note the pattern: the demonstrative/article
  chosen per word is inconsistent across cards (ce/un/l' for three plain
  adjectives), suggesting the prompt doesn't anchor a fixed frame, making
  agreement slips like the above easy to generate.

Full response, `uv:interessant`:
```
{"forms":[{"label":"masculine","fr":"un intéressante"},{"label":"feminine","fr":"une intéressante"},{"label":"masculine plural","fr":"des intéressants"},{"label":"feminine plural","fr":"des intéressantes"}],"cached":false}
```

## Notes
- This is a genuine French-grammar defect in the generated content served to
  learners studying adjective forms, not just "could be nicer" — a beginner
  reading "un intéressante" as the masculine form of "intéressant" is being
  taught a wrong gender agreement.
- Results are cached once generated (confirmed via a repeat call returning
  `"cached":true` for `uv:ebouriffant` with the identical wrong text), so a bad
  generation sticks around for that user/card indefinitely.
- Reproduced with 3/5 adjective cards tried (ébouriffant, intéressant; amusant
  was internally consistent). Likely `vocab_enrich`/`vocab_forms` profile
  prompt issue, independent of the raw-ChatML change itself (H3 scope — flag
  quality, not attribute to raw mode specifically; same class of error could
  predate this PR, but it is newly visible because this round is the first to
  sample `/vocab/forms` broadly against the real Ollama qwen model).

## Triage
- Explanation: `app/content/forms.py`'s `_FORMS_SYSTEM` prompt for the
  `vocab_forms` profile doesn't anchor a fixed article/determiner frame per
  form, so the 7B model is free to pick "un"/"ce"/"l'" per sample and
  occasionally copies the feminine adjective ending onto the masculine row
  (classic small-model gender-agreement slip) or picks "ce" without applying
  the "cet" vowel-elision rule. Verified directly against the box's real
  Ollama with the app's exact system/user prompts: `curl`'ing
  `http://10.0.0.54:11434/api/chat` (old pre-PR rendering) and
  `/api/generate` with `raw:true` + client-rendered ChatML (this PR's new
  rendering) for "intéressant" returned the *identical* wrong JSON
  (`"masculine":"un intéressante"`) in both modes; 5x sampling "ébouriffant"
  through both `/api/chat` and the raw/ChatML path showed the same
  ce/cet-elision slip appearing in either mode (1/5 raw, 0/5 chat this run,
  but driven by sampling variance in an unconstrained prompt, not a
  structural difference between the two call shapes). This is a
  `vocab_forms` prompt/model-quality issue that predates and is independent
  of PR #120's raw-ChatML adapter change.
- Against spec: unspecified in the technical plan beyond "content should be
  correct"; round 058's own H3 explicitly separates "content quality" from
  "H1 raw-mode JSON/transport correctness" and flags this class of finding as
  likely pre-existing ("same class of error could predate this PR").
- Verdict: deferred
- Rationale: real French-grammar defect worth fixing (a learner could
  internalize wrong gender agreement), but reproduces identically through the
  pre-PR `/api/chat` rendering, so it is not caused by, and does not gate,
  PR #120. Route to a future round scoped to `vocab_forms`/`vocab_enrich`
  prompt quality (e.g. anchor a fixed article per label, add a short
  few-shot anchor like the writing-grader prompt already does).

## Critic
- Challenge: the raw-ChatML change in `app/ai/adapters/ollama_adapter.py` is
  a global `model.startswith("qwen")` branch, not scoped to speech — so
  after this PR merges, every `vocab_forms` call to the (already-production)
  qwen2.5 model goes through the new raw/`/api/generate` path instead of the
  old `/api/chat` path. That's a real code-path change for this exact
  profile, not a hypothetical one, so "PM says it ran a comparison" deserves
  scrutiny rather than a pass.
- Holds up? Yes. Confirmed independently: (1) `git log -- app/content/forms.py`
  shows no commits on this branch — the `_FORMS_SYSTEM` prompt predates and
  is untouched by both #119 and #120; (2) the `options` dict sent to Ollama
  (`temperature`, `num_predict`) is byte-identical between the old
  `/api/chat` branch and the new raw `/api/generate` branch — no `stop`
  option is set in either mode, so the specific mechanism this review was
  asked to probe (raw mode lacking an explicit stop) is a non-factor: it's
  equally absent before and after. The PM's A/B test (same system/user
  prompt, same model, `/api/chat` vs. raw ChatML, repeated sampling) is the
  right instrument to isolate transport-vs-content causation, and it found
  no differential failure rate. A genuinely PR-introduced risk would show
  as a higher error rate under raw mode; it didn't. This is a real,
  learner-facing French-grammar defect, but it is a `vocab_forms`
  prompt/model-quality bug that exists identically whether or not PR #120
  ships. Blocking an unrelated speaking-latency PR on it would conflate
  scopes and violate the "fix only what's actually an issue" default.
- Final verdict: deferred

## Fix
- Branch `fix/llm-content-quality`. `app/content/forms.py`: the model now only supplies
  what a rule can't (an adjective's feminine, a verb's conjugation, a noun's plural);
  `tidy_forms` decides the rest — adjective masculine = the headword, articles/determiners
  stripped, plurals by rule (-s/-x unchanged, -eau +x, -al → -aux except banal/final/…);
  le/la/je/me/te/se elide before a vowel (verbs also before h unless h aspiré); a dropped
  `je` is restored; un/une/des on nouns → le/la/les; stray non-Latin script dropped.
  Forms run at temperature 0. `tidy_forms` is also applied on read in
  `vocab_extra_api.py`, so forms stored before the fix are served corrected without
  rewriting user rows.
- Measured on the box (qwen2.5 7B, 38 hand-checked words × 2): exact-match forms
  32/76 → 64/76. Every adjective agreement/elision error is gone; the 12 left are the
  7B model's own conjugation/irregular-plural mistakes (venir → "j'ai venu",
  œil → "les œils", gros → "grande"), not agreement/elision.
- Tests: `tests/test_forms.py` (QA repro + stored-row correction + idempotence).
