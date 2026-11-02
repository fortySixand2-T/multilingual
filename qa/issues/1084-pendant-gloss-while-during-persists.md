---
id: 1084
title: "pendant" still glosses as "while during" (1001 not fully fixed)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"pendant"}
2. POST $B/vocab/personal/from-word {"word":"pendant"}; GET $B/vocab/personal.

## Expected
A single clean gloss, e.g. "during" (or "during, while").

## Actual
en "while during" in both preview and saved card (pos preposition).

## Notes
Listed in 1001 as noisy gloss; clean_gloss does not touch it (two glosses run together without a comma). Could be handled by rejecting glosses of two bare words for a preposition, or a prompt example.

## Triage
- Explanation: clean_gloss does not touch two run-together bare words; 'while during' is the 7B's output. Pre-dates #133 (1001 noisy gloss).
- Against spec: Plan 'Don't re-file' lists pre-#133 model-quality glosses. Unspecified.
- Verdict: deferred
- Rationale: Model quality; defer. Prompt example or gloss rule could address it later.

## Critic
- Challenge: Predates #133 (1001), clean_gloss does not touch it, and the plan lists such glosses under Don't re-file.
- Holds up? Deferral confirmed.
- Final verdict: deferred

## Fix
`en` is now a JSON list of senses, joined with ", "; clean_gloss also splits on | , ; and drops repeats. Real 7B: pendant -> "while, during" (was "while during"), which the issue lists as acceptable. Sense order stays the model's. Test: test_clean_gloss_separates_and_dedupes_senses.
