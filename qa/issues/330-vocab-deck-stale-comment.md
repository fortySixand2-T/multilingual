---
id: 330
title: "vocab-deck.spec.ts comment references old single-user email"
severity: low
area: other
persona: Edge-Case Breaker
status: rejected
found: 2026-06-24
---

## Steps to reproduce
1. Open `web/e2e/specs/vocab-deck.spec.ts`.
2. Read line 4: `// Authed via the project storageState (e2e@test.com).`

## Expected
The comment should reference the current per-browser email pattern (`e2e-{browser}@test.com`) since PR #11 changed auth.setup.ts to create separate users per browser project.

## Actual
The comment still says `e2e@test.com`, which was the single-user email before the cross-browser change. The old email is no longer created by the setup.

## Notes
- Pure documentation/comment issue -- no functional impact.
- The code itself works correctly (storageState is loaded from the project config, not from this comment).
- Affected file: `web/e2e/specs/vocab-deck.spec.ts`, line 4.
- Other spec files may have the same stale comment pattern.

## Triage
- Explanation: Line 3 of `web/e2e/specs/vocab-deck.spec.ts` contains the comment `(e2e@test.com)` which references the pre-PR#11 single-user email. After `auth.setup.ts` was changed to create per-browser users (`e2e-{chromium,firefox,webkit}@test.com`), this comment became stale. No other spec files have the same stale reference (confirmed via grep).
- Against spec: Unspecified -- no spec governs test-file comments, but correctness of documentation is a reasonable baseline expectation.
- Verdict: validated
- Rationale: The comment is factually wrong and could mislead a contributor debugging auth setup failures. The fix is trivial (update one comment line), so the cost of fixing is near zero while the cost of leaving it is minor but real confusion for anyone reading the test.

## Critic
- Challenge: This is a parenthetical comment in a test file with zero functional impact on any user, learner, or developer workflow. The PM's "could mislead a contributor debugging auth setup failures" argument does not hold up -- anyone debugging auth would look at auth.setup.ts and playwright.config.ts, not a parenthetical remark in an unrelated spec file. No spec or plan requires comment accuracy in test files. Every codebase carries stale comments; dedicating a fix cycle and commit to updating three words in a test comment adds git noise for negligible value. The conservative default (no change) applies: a change is guilty until proven necessary, and this change is not necessary.
- Holds up? No. The issue is real in the narrowest sense (the comment is factually outdated), but the impact is effectively zero. Nobody will be confused by this comment because nobody consults it when debugging. The fix cost is near-zero but so is the benefit, and the project rule is to fix only what is actually an issue. A stale comment in a test file does not meet that bar.
- Final verdict: rejected
