# QA round 020 -- plan

- date: 2026-06-24
- app under test: E2E test infrastructure (PR #11, branch `test/e2e-cross-browser`)
- scope: cross-browser Playwright expansion (chromium + firefox + webkit) -- no app/backend changes

## Change surface (highest risk first)
PR #11 touches only test infrastructure (5 files, +49/-25):

1. **web/e2e/auth.setup.ts** -- setup now loops over 3 browsers, creating per-browser users (`e2e-{chromium,firefox,webkit}@test.com`), saving separate storageState files, and clearing localStorage between passes. Risk: if the clear/re-signup sequence races or fails mid-loop, downstream browser projects get stale or empty auth.
2. **web/playwright.config.ts** -- adds firefox + webkit projects, each pointing to its own storageState file. Risk: config typo or wrong device mapping; projects run in serial (workers:1) so ordering matters.
3. **web/e2e/specs/auth.spec.ts** -- signup email now uses `testInfo.project.name` for uniqueness. Risk: if project.name doesn't match expected values, email format could be wrong.
4. **.github/workflows/ci.yml** -- installs all 3 browsers. Risk: timeout increase from 3x test count.
5. **CHANGELOG.md** -- no risk.

No app/ or web/src/ files changed -- confirmed via `git diff --stat`.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | state isolation | If all 3 browsers share one DB but use separate users, then each browser's initial-state assertions (e.g. vocab `✓ 0`) should hold even after an earlier browser mutated state. If the user separation is wrong, firefox/webkit will see chromium's "known" marks. | Run full suite, check that vocab-deck `✓ 0` passes for all 3 browsers. Inspect auth files to confirm distinct user emails. | edge-case-breaker |
| H2 | determinism | If firefox/webkit have different timing than chromium, existing waits may be insufficient, causing flaky failures. Engines render async content at different speeds. | Run the full suite 3+ times; any intermittent failure is a finding. | edge-case-breaker |
| H3 | setup correctness | If the auth.setup loop fails partway (e.g. signup collision or localStorage.clear doesn't fully reset), one or more storageState files may be empty/stale, causing downstream projects to fail auth. | Verify all 3 `.auth/*.json` files exist after a run and contain valid JWT tokens. | edge-case-breaker |
| H4 | auth.spec collision | If `testInfo.project.name` produces unexpected values or if the email format collides with the setup users, auth.spec signup will 409. | Check that auth-flow-{chromium,firefox,webkit}@test.com don't collide with e2e-{browser}@test.com. Code review confirms this. | edge-case-breaker |
| H5 | CI timeout | The e2e job now runs 40 tests (up from ~14). If per-test timeouts or job timeouts are too tight, CI could fail. The first run passed at ~3m14s but with no margin analysis. | Review ci.yml for timeout settings; check playwright.config for test timeout defaults; compare 3m14s against GitHub's default 6h job timeout. | edge-case-breaker |
| H6 | test hygiene | After a run, e2e artifacts (`.auth/`, `playwright-report/`, `test-results/`, `data/e2e.db`) should be gitignored and not dirty the working tree. | Run suite, then `git status` to check for untracked artifacts. | edge-case-breaker |
| H7 | stale comment | `vocab-deck.spec.ts` line 4 references `e2e@test.com` but the user is now `e2e-{browser}@test.com`. Minor hygiene. | Code review (already confirmed). | edge-case-breaker |
| H8 | regression | Existing backend tests (pytest) and frontend unit tests (vitest) should still pass on this branch. No app code changed, so they should be green. | Run `pytest -q` and `npx vitest run`. | edge-case-breaker |

## Coverage gaps
- No prior QA issue has tested cross-browser E2E behavior (all previous rounds tested app behavior via API/UI).
- The auth setup loop pattern (sequential signup in one context with localStorage.clear between passes) is new and untested.

## Charters (per tester, with id blocks)

- **edge-case-breaker** (ids 330--339): This is a test-infrastructure round, so a single tester focused on infrastructure correctness covers all hypotheses. Chase H1--H8 in order of priority. Specifically:
  1. Run `npm run e2e` from `web/` (with the E2E env vars) at least 3 times. Record pass/fail for each browser project on each run.
  2. After a successful run, inspect the 3 `.auth/*.json` files for valid tokens and distinct emails.
  3. After a run, check `git status` for leaked artifacts.
  4. Run `pytest -q` and `npx vitest run` to confirm regression gates.
  5. Review CI workflow for timeout concerns.
  6. Note the stale comment in vocab-deck.spec.ts line 4 as a minor finding.

## Don't re-file (already settled)
- 320 reuseExistingServer bypasses DB isolation -- rejected (contrived scenario, CI safe)
- 001 invalid email -- deferred
- 007 negative elapsed_seconds -- rejected
- Drill/Writing/Speaking 503 with no LLM provider -- expected behavior
