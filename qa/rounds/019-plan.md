# QA round 019 — plan

- date: 2026-06-24
- app under test: E2E suite on branch `test/e2e-widen-screens` (PR #10)
- scope: validate the 10 new/changed E2E test files — determinism, seeding, assertion teeth, isolation, CI correctness

## Change surface (highest risk first)
PR #10 adds 5 new spec files and expands `global-setup.ts` to sync 4 content types.
No `app/` or `web/src/` changes — this is test-infrastructure only.

Changed files:
- `web/e2e/global-setup.ts` — now syncs content, comprehension, writing, exam (was content-only)
- `web/e2e/specs/comprehension.spec.ts` — NEW: graded reading flow
- `web/e2e/specs/exam.spec.ts` — NEW: full mock-exam attempt + CLB report
- `web/e2e/specs/path.spec.ts` — NEW: learn-path render
- `web/e2e/specs/review.spec.ts` — NEW: SRS reveal + rate
- `web/e2e/specs/screens-smoke.spec.ts` — NEW: writing/drill/speaking/board renders
- `web/playwright.config.ts` — minor config change
- `CHANGELOG.md` — updated

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | determinism | exam.spec.ts may flake: `recordAllSections` relies on Record-button count decreasing, but if two sections share a skill the count could drop by 2, and the guard loop (max 8) may not be enough or could race | Run full suite 3+ times; watch exam specifically for intermittent failures | edge-case-breaker |
| H2 | determinism | review.spec.ts may collide with vocab-deck.spec.ts — both add SRS cards; serial execution means vocab-deck runs first and seeds a card, then review.spec seeds another; the "Show answer" assertion could see the wrong card or fail if the first card was already rated | Run suite 3 times; check if review.spec is order-dependent on vocab-deck | edge-case-breaker |
| H3 | determinism | comprehension.spec.ts race: `.options` waitFor visible, then iterates `.card` with `.options` — if a slow render adds cards after the count snapshot, the loop misses questions | Run suite 3+ times; watch for intermittent failures on comprehension | edge-case-breaker |
| H4 | seeding | global-setup sync order correctness: exam.sync depends on comprehension + writing being synced first; if any sync fails silently (exit 0 but no data), downstream specs fail nondeterministically | Read global-setup output during a run; verify all 4 syncs complete | edge-case-breaker |
| H5 | isolation | E2E artifacts not gitignored: after a run, `e2e/.auth/`, `playwright-report/`, `test-results/`, `data/e2e.db` must all be gitignored — verify `git status` stays clean | Run suite then check `git status` | edge-case-breaker |
| H6 | assertion teeth | smoke specs (writing/drill/speaking/board) may pass vacuously — they assert a heading + one control but could pass on an error page that happens to have the right text | Read each smoke spec; verify assertions prove data loaded, not just a shell | edge-case-breaker |
| H7 | assertion teeth | comprehension and exam deep specs must assert real outcomes (score, CLB band), not just that a page rendered | Code review the assertions | edge-case-breaker |
| H8 | CI correctness | the 4-sync seeding is heavier; the e2e job has no explicit timeout — verify it ran within reasonable time on the PR's CI run | Check CI run duration | edge-case-breaker |
| H9 | dev-DB safety | global-setup must never touch `data/tef.db`; it sets DATABASE_URL to e2e.db — confirm the env override is correct and no fallback can leak to dev | Code review global-setup.ts | edge-case-breaker |
| H10 | regression | existing gates (pytest, vitest) must still pass — no app code changed but confirm | Run `pytest -q` and `npx vitest run` | edge-case-breaker |

## Coverage gaps
- The `reuseExistingServer: !process.env.CI` setting was flagged in issue 320 (rejected) — don't re-file.
- No test covers what happens if a sync command fails mid-sequence (e.g. comprehension.sync errors but exam.sync still runs). This is edge-case territory for CI, not a blocker.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 330–349): This is the only persona needed — the PR is test-infrastructure, not user-facing. Chase all hypotheses H1–H10:
  1. Run the full E2E suite 3 times locally; record pass/fail for each spec on each run
  2. After each run, check `git status` for leaked artifacts (H5)
  3. Code-review all new specs for assertion teeth (H6, H7)
  4. Code-review global-setup.ts for seeding correctness and dev-DB safety (H4, H9)
  5. Verify CI job wiring and timing (H8)
  6. Run pytest + vitest for regression (H10)
  7. Confirm no app/backend files changed in the diff (scope guard)

## Don't re-file (already settled)
- 320 reuseExistingServer bypasses DB isolation — rejected (by-design for local dev)
- Drill / Writing / Speaking 503 with no AI provider — expected; smoke specs correctly skip submission
