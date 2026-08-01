#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-serve}"
case "$cmd" in
  serve)       uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload ;;
  serve-prod)  uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 ;;
  sync-all)    for lvl in a1 a2 b1 b2; do
                 uv run python -m app.content.sync "$lvl"
                 uv run python -m app.comprehension.sync "$lvl"
                 uv run python -m app.assessment.sync "$lvl"
                 uv run python -m app.speech.topics "$lvl"
                 uv run python -m app.exam.sync "$lvl"
               done ;;
  test)        uv run pytest -q ;;
  lint)        uv run ruff check . ;;
  fmt)         uv run ruff format . ;;
  migrate)      uv run alembic upgrade head ;;
  content-sync) uv run python -m app.content.sync "${2:-a1}" ;;
  comprehension-sync) uv run python -m app.comprehension.sync "${2:-a1}" ;;
  writing-sync) uv run python -m app.assessment.sync "${2:-a1}" ;;
  exam-sync)    uv run python -m app.exam.sync "${2:-a1}" ;;
  calibrate)    uv run python -m app.assessment.calibration "${2:-a1}" ;;
  eval)         uv run python -m app.assessment.model_eval "${2:?comma-separated targets}" "${3:-a1}" "${4:-}" ;;
  drill-eval)   uv run python -m app.tutor.drill_eval "${2:?comma-separated targets}" "${3:-a1}" "${4:-}" "${5:-}" ;;
  ollama-pull)  docker compose exec ollama ollama pull "${2:-llama3.1}" ;;
  *) echo "usage: $0 {serve|serve-prod|test|lint|fmt|migrate|sync-all|content-sync|comprehension-sync|writing-sync|exam-sync [level]|calibrate [level]|eval \"t1,t2\" [level] [lam]|drill-eval \"t1,t2\" [level] [lam] [limit]|ollama-pull [model]}"; exit 1 ;;
esac
