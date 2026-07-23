---
id: 341
title: Writing feedback overall message contradicts clb_estimate when score exceeds CLB 7
severity: medium
area: writing
persona: exam-crammer
status: deferred
found: 2026-07-22
---

## Steps to reproduce
1. Sign up and obtain a bearer token.
2. POST `/assessment/tasks/write-b2-open-letter/submit` with a well-written French response of 120+ words.
3. Observe the response: `clb_estimate` is 8 and `feedback.overall` reads: "A well-written response; minor errors in grammar and sentence structure prevent reaching CLB 7."

## Expected
The `feedback.overall` text should be consistent with the `clb_estimate`. If the estimate is 8 (i.e., the learner already exceeds CLB 7), the overall comment must not say "prevent reaching CLB 7" — it should instead acknowledge the learner is above that threshold (e.g., "Solid CLB 8 response; to reach CLB 9, tighten…").

## Actual
The LLM grader returns `clb_estimate: 8` but the `overall` text says "minor errors in grammar and sentence structure prevent reaching CLB 7." The two fields directly contradict each other. A crammer reading this would think they failed to meet the B2 target (CLB 7) when in fact their score is above it.

Verified on live deployment: `POST /assessment/tasks/write-b2-open-letter/submit`
```json
{
  "clb_estimate": 8,
  "feedback": {
    "overall": "A well-written response; minor errors in grammar and sentence structure prevent reaching CLB 7."
  }
}
```

## Notes
Root cause is in the LLM system prompt at `app/assessment/prompts/writing_grader.md`. The `overall` example in the few-shot anchor says "tighten agreement and connectors to reach CLB 7." The LLM anchors its phrasing to this template and produces "prevent reaching CLB 7" even when the actual `clb_estimate` it generates is 8 or 9. The prompt does not tell the LLM to calibrate the `overall` text to the CLB band it assigns.

Severity: medium — this directly misleads the exam-crammer persona who is scrutinizing the CLB numbers to gauge real readiness. A learner who achieves CLB 8 but reads "prevent reaching CLB 7" may mistakenly believe they scored below target, which is the primary feedback they act on.

Found on live remote deployment: https://rohith-alienware-17-r4.tail592ffa.ts.net

## Triage
- Explanation: The writing grader's `overall` prose can contradict its own clb_estimate (e.g. "errors prevent reaching CLB 7" while estimate=8). On llama3.1 the model anchors phrasing to the CLB 7 example in app/assessment/prompts/writing_grader.md.
- Against spec: known limitation of the self-hosted 8B model — writing CLB grading is documented/accepted as rough on Ollama. A prompt tweak (force the summary to agree with clb_estimate, or de-anchor the example) MIGHT mitigate, but small models can still drift.
- Verdict: deferred
- Rationale: fundamentally a model-quality limitation accepted for the local deployment; revisit with a larger/cloud model or dedicated prompt-tuning + the eval harness — not a code bug.

## Critic
- Challenge: could a cheap prompt fix resolve it now?
- Holds up as deferred? Yes — worth a prompt experiment later, but reliability needs the eval harness + a better model; not a quick validated fix.
- Final verdict: deferred
