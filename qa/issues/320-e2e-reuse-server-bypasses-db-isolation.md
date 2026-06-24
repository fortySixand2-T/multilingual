---
id: 320
title: "reuseExistingServer lets E2E silently hit dev DB when port 9100 is already occupied"
severity: high
area: other
persona: Edge-Case Breaker
status: rejected
found: 2026-06-24
---

## Steps to reproduce
1. Manually start a backend on port 9100 without `DATABASE_URL` override:
   `/tmp/tef312/bin/uvicorn app.main:app --port 9100` (this uses the default dev DB `data/tef.db`).
2. Run the E2E suite: `cd web && npm run e2e` (with the E2E env vars set).
3. Observe that Playwright's `webServer` config has `reuseExistingServer: !process.env.CI` (i.e. `true` locally).
4. Playwright detects port 9100 is already listening, skips launching its own backend, and never applies the `backendEnv` (`DATABASE_URL=sqlite+aiosqlite:///./data/e2e.db`, `INVITE_CODES=e2e-invite`, `JWT_SECRET=e2e-secret`).
5. The E2E tests now run against the dev DB (`data/tef.db`), creating test users and mutating real data.

The same issue applies to the Vite dev server on port 5180: if already occupied, the reused server's proxy target likely points to `:9000` (the dev backend), not `:9100`.

## Expected
E2E tests should always run against the throwaway `data/e2e.db` and never silently fall back to the dev DB, even when a stale process occupies the E2E ports.

## Actual
`reuseExistingServer: true` (the local default) causes Playwright to skip launching the configured backend, so the `backendEnv` (with `DATABASE_URL` pointing to `e2e.db`) is never applied. Tests silently hit whatever DB the existing server uses.

## Notes
- In CI (`process.env.CI` is set), `reuseExistingServer` is `false`, so this is a local-only issue.
- Fix options: (a) set `reuseExistingServer: false` unconditionally, or (b) add a pre-flight check in `globalSetup` that confirms port 9100 is free (or that the server on it is using the right DB), or (c) document clearly that port 9100 must be free.
- Affected file: `web/playwright.config.ts`, lines 66 and 73.
- Severity rationale: DB isolation is the single most critical property of the E2E harness. A silent violation -- even in a niche local scenario -- is high severity because the developer gets no warning.

## Triage
- Explanation: `reuseExistingServer: !process.env.CI` evaluates to `true` locally. When a process already occupies port 9100, Playwright skips launching the configured backend command and never injects `backendEnv` (DATABASE_URL, JWT_SECRET, INVITE_CODES). The global-setup creates e2e.db correctly, but the reused server ignores it because it was started with its own env. The same applies to the Vite server on port 5180.
- Against spec: The playwright.config.ts header comment (lines 7-8) explicitly states "all isolated from the dev DB." The reuseExistingServer setting can silently violate this invariant. DB isolation is the harness's stated critical property.
- Verdict: validated
- Rationale: A stale uvicorn on port 9100 is realistic (the E2E docs show manual launch on that port, and lingering processes are common). Impact is silent mutation of the dev DB with no warning. Fix is low-cost: set `reuseExistingServer: false` unconditionally or add a preflight port-free check in globalSetup.

## Critic
- Challenge: The dangerous scenario requires a developer to manually start uvicorn on port 9100 (the E2E-specific port, not the dev port 9000) against the dev DB, AND then run the E2E suite separately. The config comment example the PM cites (E2E_BACKEND_CMD) is an env var override for Playwright itself, not instructions to manually start a server beforehand. The most realistic stale-process scenario (Ctrl-C Playwright, orphaned uvicorn) would leave a server that WAS started with the correct backendEnv pointing at e2e.db -- not the dev DB. globalSetup then wipes and recreates e2e.db, so the stale server would hit a deleted/recreated SQLite file and produce obvious errors, not silent dev-DB pollution. Meanwhile, setting reuseExistingServer to false unconditionally has a real cost: it kills the standard Playwright local-iteration workflow, adding server restart overhead on every run during spec debugging. CI is already safe (reuseExistingServer is false there). The reuseExistingServer pattern follows Playwright's own recommended docs.
- Holds up? No. The PM's validation rests on "silent mutation of the dev DB" but this requires a contrived, self-inflicted setup. The realistic stale-process case (orphaned E2E uvicorn) would not hit the dev DB. The fix penalizes every local run to guard against a scenario that requires deliberate misuse and would manifest as obvious test failures rather than silent corruption.
- Final verdict: rejected
