import { execSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Prepare a fresh backend DB for the E2E run, BEFORE Playwright boots the servers.
// Mirrors `start.sh migrate` + `start.sh content-sync a1`, but against a throwaway
// data/e2e.db so the dev DB is never touched. A clean DB every run means specs can
// rely on fixed fixtures (one known user, a1 content) without cross-run bleed.
//
// Commands default to `uv run …` (CI has uv); override via env to use a local venv.

// web/ is "type": "module", so __dirname doesn't exist — derive it from import.meta.
// this file is web/e2e/global-setup.ts → repo root is two levels up.
const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const DB_FILE = resolve(REPO_ROOT, "data", "e2e.db");
const DB_URL = "sqlite+aiosqlite:///./data/e2e.db";

const MIGRATE_CMD = process.env.E2E_MIGRATE_CMD ?? "uv run alembic upgrade head";
const SYNC_CMD = process.env.E2E_SYNC_CMD ?? "uv run python -m app.content.sync a1";

function run(cmd: string) {
  execSync(cmd, {
    cwd: REPO_ROOT,
    stdio: "inherit",
    env: { ...process.env, DATABASE_URL: DB_URL },
  });
}

export default function globalSetup() {
  // Wipe any leftover DB (and SQLite sidecar files) for a deterministic start.
  for (const f of [DB_FILE, `${DB_FILE}-wal`, `${DB_FILE}-shm`]) {
    if (existsSync(f)) rmSync(f);
  }
  console.log("[e2e] migrating fresh test DB →", DB_FILE);
  run(MIGRATE_CMD);
  console.log("[e2e] syncing a1 content");
  run(SYNC_CMD);
}
