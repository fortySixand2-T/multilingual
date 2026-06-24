# QA round 018 — plan

- date: 2026-06-24
- app under test: backend :9100 (E2E-spawned) / SPA :5180 (E2E-spawned)
- scope: PR #9 `test/playwright-e2e` — Playwright E2E harness + CI job (test-infra only, no app/backend changes)

## Change surface (highest risk first)
Single commit `1585613` adds:
- `web/playwright.config.ts` — defines E2E topology (ports, DB URL, server launch)
- `web/e2e/global-setup.ts` — wipes + migrates + syncs a throwaway `data/e2e.db`
- `web/e2e/auth.setup.ts` — signup-once auth bootstrap
- `web/e2e/helpers.ts` — shared login/signup drivers
- `web/e2e/specs/auth.spec.ts` — signup/logout/login round-trip
- `web/e2e/specs/lesson.spec.ts` — lesson completion driver (brute-forces match_pairs)
- `web/e2e/specs/vocab-deck.spec.ts` — known-counter persistence, pronunciation, add-to-review
- `.github/workflows/ci.yml` — new `e2e` job
- `web/.gitignore` — excludes auth state, reports, test results
- `web/package.json` / `web/package-lock.json` — adds `@playwright/test`, `e2e` script

No `app/` or `web/src/` changes. Verification: `git diff --stat main...test/playwright-e2e` confirms this.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | tester |
|---|------|------------|--------------|--------|
| H1 | DB isolation | The harness might leak writes to `data/tef.db` (dev DB). If `DATABASE_URL` isn't propagated to every subprocess, the backend could fall back to the default. | Snapshot `data/tef.db` mtime before/after E2E run; verify `global-setup.ts` and `playwright.config.ts` both set `DATABASE_URL` consistently; check no code path reads `TEF_DB` or similar env. | edge-case-breaker |
| H2 | Determinism / flakiness | Shuffle-dependent assertions could flake. The vocab deck shuffles cards (`shuffled()`), and lessons shuffle exercises (`shuffleLesson()`). If any assertion relies on card/exercise order, it will intermittently fail. | Run the full suite 3+ times and compare results. Audit assertions: known-counter checks deck-wide count (shuffle-safe); add-to-review clicks the first card's button (any card works); lesson driver is answer-agnostic. The risk is match_pairs brute-force — if the locator ordering is unstable, the nested loop could miss. | edge-case-breaker |
| H3 | Spec teeth / vacuous pass | A spec might pass even if the backend silently drops the write (e.g. known-counter spec passes because the reload reads from a cache, not the DB). | Code-review each spec's assertion: does it wait for the API response before asserting? Does it assert the server-side state (reload, navigate away + back)? The known-counter spec already proved teeth (fails when persistence is dropped). Check vocab-deck add-to-review (navigates to /review) and lesson (checks result heading). | edge-case-breaker |
| H4 | CI job wiring | The `e2e` job might have incorrect defaults, missing deps, or the report upload might not trigger. | Review the workflow YAML: does it `uv sync` before node deps? Does it install Playwright deps (`--with-deps`)? Is working-directory set correctly for all steps? Does the artifact upload path match where Playwright actually writes? Cross-reference with the passed run. | edge-case-breaker |
| H5 | Gitignore completeness | E2E artifacts (`e2e/.auth/`, `playwright-report/`, `test-results/`, `data/e2e.db`) might not be fully gitignored, leading to accidental commits. | Run the suite, then `git status` — nothing under `web/e2e/.auth/`, `web/playwright-report/`, `web/test-results/` should appear. `data/e2e.db` is covered by the repo-root `.gitignore` (`data/` is ignored). | edge-case-breaker |
| H6 | Regression — existing gates | The PR might break existing `pytest` or Vitest suites. | Run `pytest -q` and `npx vitest run` on the PR branch and confirm green. | edge-case-breaker |

## Coverage gaps
- This is a test-infra PR; the "coverage" question is whether the E2E specs themselves cover enough of the app. That's a design review, not a QA finding, so out of scope for this round.
- No previous QA issues target E2E infrastructure — this is the first time it's under test.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 320-329): Chase H1 (DB isolation), H2 (determinism), H3 (spec teeth), H4 (CI wiring), H5 (gitignore), H6 (regression). This is the only tester needed — the PR is test-infra, not user-facing behavior, so persona-based app exploration adds no value. The edge-case-breaker's job is to probe the harness itself for safety and correctness issues.

## Don't re-file (already settled)
- All existing issues 001-311 are about app behavior, not test infrastructure. None overlap with this PR's scope.
- Drill / Writing / Speaking 503 with no provider — expected (no Ollama provider configured for those profiles).

<!-- After the round, the planner notes each hypothesis: confirmed (-> issue NNN) /
     refuted (area sound) / untested. -->
