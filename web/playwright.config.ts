import { defineConfig, devices } from "@playwright/test";

// End-to-end tests: a real Chromium browser drives the SPA against a real, seeded
// FastAPI backend — exercising the seams the Vitest component tests mock out (the
// /api proxy, JWT-in-localStorage auth, routing, persistence across reload).
//
// Topology (all isolated from the dev DB):
//   - backend  :9100  on a throwaway data/e2e.db  (DATABASE_URL below)
//   - frontend :5180  Vite dev server, /api proxied to :9100 (VITE_API_TARGET)
// globalSetup wipes + migrates + content-syncs the e2e DB before the servers boot.
//
// The python/uv commands are overridable via env so this runs both in CI (uv on
// PATH) and locally against a prebuilt venv — e.g.
//   E2E_BACKEND_CMD="/tmp/tef312/bin/uvicorn app.main:app --port 9100"
//   E2E_MIGRATE_CMD="/tmp/tef312/bin/alembic upgrade head"
//   E2E_SYNC_CMD="/tmp/tef312/bin/python -m app.content.sync a1"

const BACKEND_PORT = 9100;
const WEB_PORT = 5180;
const DB_URL = "sqlite+aiosqlite:///./data/e2e.db";

// Backend env: a throwaway DB, a known invite code (so signup works), a fixed JWT secret.
const backendEnv = {
  DATABASE_URL: DB_URL,
  INVITE_CODES: "e2e-invite",
  JWT_SECRET: "e2e-secret",
};

const backendCmd = process.env.E2E_BACKEND_CMD ?? `uv run uvicorn app.main:app --port ${BACKEND_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // The backend is a shared, stateful resource (one SQLite file) — keep specs serial
  // so they don't race on it. The suite is small; this is plenty fast.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  globalSetup: "./e2e/global-setup.ts",

  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "on-first-retry",
  },

  projects: [
    // Signs up once and saves the auth storageState the feature specs reuse.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/user.json" },
      dependencies: ["setup"],
      testMatch: /specs\/.*\.spec\.ts/,
    },
  ],

  // Backend DB is prepared by globalSetup; here we just launch the two servers. From
  // the working dir (web/), the backend runs in the repo root (cwd: "..").
  webServer: [
    {
      command: backendCmd,
      cwd: "..",
      port: BACKEND_PORT,
      env: backendEnv,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --port ${WEB_PORT}`,
      port: WEB_PORT,
      env: { VITE_API_TARGET: `http://localhost:${BACKEND_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
