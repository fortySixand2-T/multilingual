---
id: 404
title: All B1 listening comprehension sets allow replay -- no exam-realistic no-replay practice
severity: medium
area: comprehension
persona: exam-crammer
status: deferred
found: 2026-06-26
---

## Steps to reproduce
1. GET /comprehension/sets?level=b1 (with auth).
2. Filter for skill=listening.
3. Observe all 4 listening sets have `allow_replay: true`.

## Expected
At least some B1 listening sets (especially those used in mock exams) should have `allow_replay: false` to simulate real TEF conditions, where listening audio is played once (or at most twice) and cannot be freely replayed. A1 has a healthy mix: 4 of 10 listening sets are no-replay. B1 has 0 of 4.

## Actual
All 4 B1 listening sets (`listen-b1-future-plans`, `listen-b1-health-tips`, `listen-b1-job-voicemail`, `listen-b1-radio-news`) have `allow_replay: true`. This means the mock exam listening section never enforces the no-replay constraint, undermining realistic exam practice.

## Notes
This is a content-level issue in the YAML files under `content/b1/comprehension/`. The exam crammer persona explicitly cares about the no-replay rule being enforced for realistic timed practice. The mock blueprints reference these sets for their listening sections, so the mock exam inherits the permissive replay setting.

## Triage
- Explanation: All 4 B1 listening YAML files set `allow_replay: true`. A1 has 4/10 no-replay sets, A2 has 3/10, but B1 has 0/4. The mock blueprints reference these sets, so B1 mock exams never exercise no-replay listening.
- Against spec: Phase 5 spec explicitly calls out "no-replay listening" as a key AC for exam simulation. Phase 2 spec mentions "replay-disable flag" as a key AC. The flag mechanism works (client-enforced per issue 071), but no B1 content uses it.
- Verdict: validated
- Rationale: B1 is the exam-preparation level where no-replay matters most, yet it is the only level with zero no-replay listening sets. At least 1-2 of the 4 B1 listening sets should have `allow_replay: false` so the mock exams can deliver exam-realistic conditions. Content authoring gap, not a code bug.

## Critic
- Challenge: (1) The no-replay flag is client-enforced only -- issue 071 established that the server does not enforce it, and the critic rejected 071 as by-design. So flipping the flag in YAML only changes a hint to a future SPA player that does not exist yet in this vertical slice. The flag is decorative until a client enforces it. (2) This is a content-depth issue on a vertical slice / mock-golive branch. B1 has only 4 listening sets total -- this is minimal viable content, not a finished level. Adding no-replay flags is content authoring work for a future phase, not a bug fix. (3) The spec says "replay-disable flag" as a key AC for Phase 2, and the flag mechanism exists and works at A1/A2. The Phase 5 AC says "no-replay listening" but the B1 branch is explicitly a vertical slice. Content completeness is not the same as a defect.
- Holds up? No. The PM's validation does not survive the challenge. The flag is a YAML metadata field consumed by a client that is not shipped. At A1, the flag was set on some sets as part of content authoring for that level's completeness -- B1 is a vertical slice with minimal content. Flipping `allow_replay: false` on 1-2 YAML files has zero user-facing effect until a client enforces it, and the critic already ruled (issue 071) that server-side enforcement is not warranted. This is content-depth polish, not a defect. Defer to when B1 content is fully authored.
- Final verdict: deferred
