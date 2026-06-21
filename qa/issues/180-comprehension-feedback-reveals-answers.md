---
id: 180
title: Comprehension submit feedback reveals the answer key (enables known-answer retry)
severity: low
area: comprehension
persona: edge-case-breaker
status: deferred
found: 2026-06-20
---

## Steps to reproduce
1. Submit `listen-greet-01` with all-wrong answers.
2. Read `results[].correct_answer` in the response.
3. Resubmit with those answers.

## Actual
The failed submit returns every question's `correct_answer` + `explain`; the retry passes
and earns first-pass XP. Found via round-010 H4.

## Notes
Comprehension is server-graded so the answers aren't in the GET payload (the stated
anti-cheat goal holds) — but the post-submit *feedback* re-exposes them, enabling a
retry-based cheat. XP feeds the shared board.

## Triage
- Explanation: `submit` returns per-question `correct_answer`/`explain` for all questions
  as learning feedback; a later attempt with known answers claims the qa-100 first-pass
  XP marker.
- Against spec: the GET-payload anti-cheat goal is met; this is a separate, retry vector.
- Verdict: borderline — real self-cheat path, but the reveal is intended pedagogy.

## Critic
- Challenge: showing correct answers + explanations after an attempt is the core of a
  learning tool — hiding them until you pass would gut the value, and gating XP on the
  *first attempt* would punish a learner who legitimately fails, re-listens, and passes.
  The only stake is self-inflicted practice XP (same family as qa-050).
- Holds up? Yes — there's no clean fix that doesn't harm legitimate learning, and the
  harm is self-inflicted on a practice board. Not worth degrading pedagogy.
- Final verdict: deferred — accept the learning-vs-anti-cheat tradeoff. Revisit only if
  XP integrity ever matters (options then: award XP once per set per *attempt-1*, or
  reveal explanations without the literal correct answer). No change now.
