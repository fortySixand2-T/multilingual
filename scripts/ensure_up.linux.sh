#!/usr/bin/env bash
# Bring the multilingual stack up on the self-hosted box.
#
# The containers already run `restart: unless-stopped` and dockerd is enabled at
# boot, so a normal reboot restarts them on its own. This script is the belt-and-
# suspenders: an `@reboot` cron entry that guarantees the stack is up even if a
# container was left stopped, an image/compose file changed, or dockerd was slow
# to come up. `up -d` is idempotent — already-running containers are left alone.
#
# Install (on the box):
#   (crontab -l 2>/dev/null; echo '@reboot /home/rohith/projects/multilingual/scripts/ensure_up.linux.sh') | crontab -
set -euo pipefail

REPO="/home/rohith/projects/multilingual"
LOG="$REPO/reboot.log"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.gpu.yml)

exec >>"$LOG" 2>&1
echo "=== ensure_up $(date -Is) ==="

cd "$REPO"

# Wait for the Docker daemon (up to ~2 min) — on a cold boot cron can fire before
# dockerd has finished starting.
for _ in $(seq 1 24); do
  if docker info >/dev/null 2>&1; then break; fi
  echo "waiting for dockerd..."
  sleep 5
done

"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps
echo "=== done $(date -Is) ==="
