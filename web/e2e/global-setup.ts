import { execSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Prepare a fresh backend DB for the E2E run, BEFORE Playwright boots the servers.
// Mirrors `start.sh migrate` + the `*-sync a1` commands, but against a throwaway
// data/e2e.db so the dev DB is never touched. A clean DB every run means specs can
// rely on fixed fixtures (one known user, a1 content) without cross-run bleed.
//
// Commands default to `uv run …` (CI has uv); override via env to use a local venv:
//   E2E_MIGRATE_CMD="/tmp/tef312/bin/alembic upgrade head"
//   E2E_PYTHON="/tmp/tef312/bin/python"   (prefix for the `-m <module> a1` syncs)

// web/ is "type": "module", so __dirname doesn't exist — derive it from import.meta.
// this file is web/e2e/global-setup.ts → repo root is two levels up.
const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const DB_FILE = resolve(REPO_ROOT, "data", "e2e.db");
const DB_URL = "sqlite+aiosqlite:///./data/e2e.db";

const MIGRATE_CMD = process.env.E2E_MIGRATE_CMD ?? "uv run alembic upgrade head";
const PYTHON = process.env.E2E_PYTHON ?? "uv run python";

// Every content type the screens need. Order matters: the exam blueprint references
// comprehension sets + writing tasks, so it syncs last.
const SYNC_MODULES = [
  "app.content.sync", // units / lessons / vocab
  "app.comprehension.sync", // reading + listening sets (uploads audio if present)
  "app.assessment.sync", // writing tasks
  "app.exam.sync", // mock-exam blueprints
];

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
  // Seed a1 + a2 + b1 so the level switcher has the full set to switch between.
  for (const level of ["a1", "a2", "b1"]) {
    for (const m of SYNC_MODULES) {
      console.log("[e2e] syncing", m, level);
      run(`${PYTHON} -m ${m} ${level}`);
    }
  }
}
