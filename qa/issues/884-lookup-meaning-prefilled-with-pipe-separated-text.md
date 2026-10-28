---
id: 884
title: Lookup pre-fills the editable meaning as "packet|package" (raw pipe-separated LLM output)
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-10-27
---

## Steps to reproduce
1. My deck -> look up "paquet".

## Expected
A clean meaning such as "packet, package".

## Actual
"Meaning (edit if it's not right)" field contains "packet|package". The card would be saved with the literal pipe unless the learner edits it; a beginner won't know what the pipe means.

## Triage
- Explanation: Lookup LLM output uses pipe-separated alternatives and the preview prefill copies en verbatim.
- Against spec: unspecified; learner-facing raw delimiter is a bug.
- Verdict: validated
- Rationale: Low severity: a beginner would save 'packet|package' literally. Fix: join alternatives with ', ' in lookup_payload/prefill (and for cached rows). Trivial, ship if cheap.


## Critic
- Challenge: Cosmetic; the learner can edit the field.
- Holds up? Holds as trivial: a beginner saves 'packet|package' literally and the string is shown on cards. Normalize in lookup_payload (replace '|' with ', ', collapse spaces) so cached rows are covered too; do not migrate stored rows or change enrich parsing/grading semantics.
- Final verdict: validated

## Fix
`lookup_payload` renders the model's `a|b` alternatives as `a, b` (covers cached rows; stored data unchanged).
- Files: `app/content/lookup.py`
- Tests: `tests/test_personal_vocab.py::test_pipe_separated_meanings_are_shown_as_a_list`
