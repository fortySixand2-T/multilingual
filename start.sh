#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-serve}"
case "$cmd" in
  serve)       uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload ;;
  test)        uv run pytest -q ;;
  lint)        uv run ruff check . ;;
  fmt)         uv run ruff format . ;;
  migrate)      uv run alembic upgrade head ;;
  content-sync) uv run python -m app.content.sync "${2:-a1}" ;;
  comprehension-sync) uv run python -m app.comprehension.sync "${2:-a1}" ;;
  ollama-pull)  docker compose exec ollama ollama pull "${2:-llama3.1}" ;;
  *) echo "usage: $0 {serve|test|lint|fmt|migrate|content-sync [level]|comprehension-sync [level]|ollama-pull [model]}"; exit 1 ;;
esac
