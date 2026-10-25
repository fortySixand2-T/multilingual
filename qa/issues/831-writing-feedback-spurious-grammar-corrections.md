---
id: 831
title: writing_feedback flags already-correct French as an error and "corrects" it to a worse/no-better form
severity: medium
area: writing
persona: edge-case-breaker
status: deferred
found: 2026-10-25
---

## Steps to reproduce
1. Sign up (`friend-001`), sync writing tasks if needed
   (`python -m app.assessment.sync <level> content`).
2. `POST /assessment/tasks/write-b1-bank-error/submit` with a well-formed,
   grammatically correct 89-word French email that includes the phrase
   "Je vous remercie sincèrement de votre compréhension".
3. `POST /assessment/tasks/write-b2-city-letter/submit` with a well-formed
   150-word French letter that includes "des pistes cyclables adaptées à la
   circulation quotidienne des habitants".
4. Read the `corrections` array in each response.

## Expected
`corrections` should only flag text that is actually grammatically wrong, so
the learner can trust the feedback.

## Actual
Both submissions got a "correction" on text that was already correct,
actively teaching the wrong thing:

- Submission 1: `{"excerpt":"Je vous remercie sincèrement de votre compréhension","correction":"Je vous remercie sincèrement pour votre compréhension","explanation":"Replace 'de votre' with 'pour votre' in this context."}` —
  "remercier qqn de qqch" is standard, correct French (if anything the more
  classic/formal choice for a written register); there is nothing to fix here.
- Submission 2: `{"excerpt":"adaptées à la circulation quotidienne des habitants","correction":"adaptées pour la circulation quotidienne des habitants","explanation":"Use 'pour' instead of 'à' with 'circulation'."}` —
  "adapté à qqch" is the standard construction; "adapté pour" is not an
  improvement and the stated rule ("use pour instead of à with circulation")
  is not a real rule of French grammar.

Both full submissions are otherwise scored sensibly (CLB 7, high
task_fulfillment/coherence), so the grader is not broken wholesale — it is
specifically hallucinating corrections for text it has nothing to actually
mark down.

## Notes
- JSON schema itself is fine every time (H1 confirmed sound across 5 writing
  submissions + 10+ vocab-extras calls — no 500s, no malformed JSON, no
  prose-wrapped JSON). This is a content-quality finding (H3), not a raw-mode
  rendering break.
- Risk: a learner trusting this feedback will "fix" correct French into an
  incorrect or non-idiomatic alternative, which is worse than no feedback at
  all for an assessment feature whose whole value proposition is trustworthy
  correction.
- `writing_feedback` profile / grader prompt in `app/assessment/grader.py` is
  the likely place to tighten ("only include a correction if the excerpt
  contains an actual error") — flagging for triage, not diagnosing further.

## Triage
- Explanation: `app/assessment/prompts/writing_grader.md` instructs the model
  to return a correction "for each notable error" with a `reference` from a
  curated grammar-point list, but gives it no explicit permission/anchor for
  "correctly, there is nothing to fix here" on a near-perfect submission —
  so at low temperature (0.1) the 7B model still occasionally invents a
  correction to satisfy the instinct to find *something*, picking a
  defensible-sounding but wrong rule (e.g. "remercier de" → "pour", or
  "j'ai choisi" → "j'avais choisi" with a fabricated tense justification).
  Verified directly against the box's real Ollama with the grader's exact
  system prompt and a comparable well-formed formal-letter submission:
  4 runs (`/api/chat`, old pre-PR rendering, x2; `/api/generate` with
  `raw:true` + client-rendered ChatML, this PR's new rendering, x2) all
  hallucinated at least one spurious correction on grammatically correct
  text, with no systematic difference in rate or character between the two
  rendering modes. This is a `writing_feedback`/grader-prompt quality issue
  that predates and is independent of PR #120's raw-ChatML adapter change.
- Against spec: unspecified beyond the grader prompt's own intent
  ("Inline corrections... for each notable error"); round 058's H3
  explicitly treats content/grading quality as separate from and likely
  predating the raw-mode transport change this round gates.
- Verdict: deferred
- Rationale: real defect with real user-trust impact (a learner "fixing"
  correct French into something worse), but reproduces at the same rate
  through the pre-PR `/api/chat` rendering, so it is not caused by, and does
  not gate, PR #120. Route to a future round scoped to the writing-grader
  prompt (e.g. add an explicit "if the excerpt is already correct, omit it
  from `corrections`" instruction, or a zero-correction anchor example
  alongside the existing one).

## Critic
- Challenge: like 830, this profile's LLM calls now route through the new
  global raw-ChatML `/api/generate` path (the `model.startswith("qwen")`
  branch in `app/ai/adapters/ollama_adapter.py` applies to every qwen call,
  including `writing_feedback`), so this is reachable through code this PR
  actually changed, not just theoretically adjacent to it.
- Holds up? Yes. `git log -- app/assessment/grader.py` and
  `app/assessment/prompts/writing_grader.md` show no commits on this branch
  — the grader prompt predates #119/#120 entirely. The `options` payload
  (temperature/num_predict, no `stop`) is identical across the old `/api/chat`
  and new raw `/api/generate` branches, so the raw-mode-specific risk this
  review was asked to check (missing stop token behavior) isn't a
  distinguishing factor between the two call shapes. The PM's 4-run A/B
  (2x old rendering, 2x new rendering, same exact prompt) is a reasonable
  sample size for a qualitative "does rendering change hallucination
  character" check and found no systematic difference. This is a genuine,
  trust-damaging grader defect (hallucinating a "correction" on already-
  correct French), but the evidence supports it being a pre-existing
  `writing_grader.md` prompt gap (no "omit if correct" anchor) rather than
  something PR #120 caused or made worse. Per CLAUDE.md's "fix only what's
  actually an issue," gating a speaking-latency PR on an unrelated,
  pre-existing writing-grader prompt defect would be scope creep — it
  belongs in its own round against `writing_grader.md`, as the PM proposes.
- Final verdict: deferred
