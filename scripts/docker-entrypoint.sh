#!/usr/bin/env bash
# Prod container boot: apply migrations, sync authored content into the DB, serve.
# Idempotent — safe to run on every start/redeploy (syncs upsert by id). Uses the
# uv-built venv directly so there's no runtime dependency resolution.
set -euo pipefail

VENV=/app/.venv/bin
LEVELS=(a1 a2 b1 b2)

echo "[entrypoint] applying database migrations ..."
"$VENV/alembic" upgrade head

echo "[entrypoint] syncing content for: ${LEVELS[*]}"
for lvl in "${LEVELS[@]}"; do
  "$VENV/python" -m app.content.sync "$lvl"
  "$VENV/python" -m app.comprehension.sync "$lvl"
  "$VENV/python" -m app.assessment.sync "$lvl"
  "$VENV/python" -m app.exam.sync "$lvl"
done

echo "[entrypoint] starting uvicorn on :9000"
exec "$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 9000
