---
id: 405
title: Mock-3 writing section reuses all tasks from mock-1 and mock-2 -- no unique practice
severity: low
area: exam
persona: exam-crammer
status: rejected
found: 2026-06-26
---

## Steps to reproduce
1. GET /exam/blueprints?level=b1 (with auth).
2. Compare writing_task_ids across the 3 mocks:
   - mock-1: write-b1-cover-letter, write-b1-social-media
   - mock-2: write-b1-remote-request, write-b1-environment
   - mock-3: write-b1-remote-request, write-b1-social-media
3. Mock-3's writing tasks are entirely borrowed: write-b1-remote-request from mock-2, write-b1-social-media from mock-1.

## Expected
Each mock should provide at least one unique writing prompt so that a crammer taking all 3 mocks gets fresh practice each time. Currently there are 4 writing tasks total, which is enough for 2 unique per mock if distributed without full overlap.

## Actual
Mock-3 offers zero new writing practice for a user who has already completed mock-1 and mock-2. A possible redistribution: mock-1 gets cover-letter + social-media (as-is), mock-2 gets remote-request + environment (as-is), mock-3 gets cover-letter + environment (or two new tasks). This is a content composition issue in `content/b1/exam/mock-3.yaml`.

## Notes
Severity is low because the prompts still work correctly and the user can still practice writing. The issue is about diminishing returns for repeat test-takers, which is exactly the exam-crammer use case.

## Triage
- Explanation: There are exactly 4 B1 writing tasks (cover-letter, social-media, remote-request, environment) and 3 mocks each needing 2 tasks (6 slots total). Mock-1 uses cover-letter + social-media, mock-2 uses remote-request + environment, mock-3 uses remote-request + social-media. Mock-3's pairing is entirely drawn from the other two mocks.
- Against spec: Unspecified -- the spec does not mandate unique tasks per mock. However, each mock section uses one Section A (formal) and one Section B (opinion) task, which is correct structurally.
- Verdict: validated
- Rationale: With 4 tasks and 3 mocks, overlap is inevitable, but mock-3 could use cover-letter + environment instead, giving every mock at least one unique task. The fix is a one-line YAML change. Low severity, but real diminishing returns for the exam-crammer persona taking all three mocks.

## Critic
- Challenge: The proposed fix does not actually solve the stated problem. The issue says "Mock-3 offers zero new writing practice for a user who has already completed mock-1 and mock-2." The proposed redistribution gives mock-3 cover-letter + environment. But cover-letter already appears in mock-1 and environment already appears in mock-2 -- so a user who completed both still sees zero new tasks in mock-3. The "fix" just rearranges the overlap pattern without reducing it. With 4 tasks and 6 slots (3 mocks x 2), full coverage for a user doing all 3 is mathematically impossible without adding new tasks. The current arrangement is one valid combination among several equivalent ones. The spec does not mandate unique-per-mock distribution. Shuffling YAML for zero measurable improvement is pure churn.
- Holds up? No. The PM's validation does not survive the challenge. The proposed fix (cover-letter + environment in mock-3) still gives the all-three-mocks user zero new writing tasks. The only real fix would be authoring new writing tasks, which is content-depth work outside the scope of this vertical slice. Rearranging the existing 4 tasks across 3 mocks is cosmetic -- no arrangement avoids full overlap for someone doing all three.
- Final verdict: rejected
