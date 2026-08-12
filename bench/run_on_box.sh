#!/usr/bin/env bash
# Orchestrate the Ollama perf benchmark ON THE BOX (ssh rohith@10.0.0.54).
#
# For each candidate model tag it: pulls the model, unloads every other resident
# model (so the VRAM-fit reading is clean), pipes bench/ollama_perf.py into the app
# container to measure it, and captures `ollama ps` (VRAM size + GPU-vs-CPU split).
# Raw results land in bench/results/. Re-run safe: pulls skip if already present.
#
# Usage (from the repo checkout on the box, or copy bench/ over):
#   bash bench/run_on_box.sh
# Override the matrix:
#   MODELS="qwen2.5:3b-instruct-q4_K_M llama3.1:latest" bash bench/run_on_box.sh
#
# At the end it restores llama3.1 as the resident model so the live app is unaffected.
set -uo pipefail

OLLAMA_CTR="${OLLAMA_CTR:-multilingual-ollama-1}"
APP_CTR="${APP_CTR:-multilingual-app-1}"
LIVE_MODEL="${LIVE_MODEL:-llama3.1:latest}"
OUT="$(cd "$(dirname "$0")" && pwd)/results"
BENCH_PY="$(cd "$(dirname "$0")" && pwd)/ollama_perf.py"
mkdir -p "$OUT"

MODELS="${MODELS:-\
llama3.1:latest \
qwen2.5:3b-instruct-q4_K_M \
qwen2.5:7b-instruct-q4_K_M \
qwen2.5:7b-instruct-q5_K_M \
qwen2.5:7b-instruct-q6_K \
qwen2.5:14b-instruct-q3_K_M}"

unload_all() {
  # Stop every currently-loaded model so only the target occupies VRAM. Parse the
  # first column of plain `ollama ps` (skip header) — no --format dependency.
  docker exec "$OLLAMA_CTR" ollama ps 2>/dev/null | awk 'NR>1 && $1!="" {print $1}' \
    | while read -r m; do
      docker exec "$OLLAMA_CTR" ollama stop "$m" >/dev/null 2>&1
    done
}

echo "== Ollama perf benchmark =="
docker exec "$OLLAMA_CTR" ollama --version 2>/dev/null | head -1
for model in $MODELS; do
  safe="$(echo "$model" | tr '/:' '__')"
  echo ""
  echo ">> $model"
  echo "   pull..."
  if ! docker exec "$OLLAMA_CTR" ollama pull "$model" >/dev/null 2>"$OUT/$safe.pull.err"; then
    echo "   PULL FAILED (see $safe.pull.err) — skipping"
    continue
  fi
  unload_all
  echo "   measure..."
  if docker exec -i "$APP_CTR" python - "$model" <"$BENCH_PY" >"$OUT/$safe.json" 2>"$OUT/$safe.err"; then
    # Capture the fit picture while the model is still resident.
    docker exec "$OLLAMA_CTR" ollama ps >"$OUT/$safe.ps.txt" 2>&1
    rate="$(python3 -c "import json;print(json.load(open('$OUT/$safe.json'))['mean_gen_tok_per_s'])" 2>/dev/null)"
    echo "   done: mean ${rate} gen tok/s"
    grep -iE "gpu|cpu" "$OUT/$safe.ps.txt" | head -2 | sed 's/^/   ps: /'
  else
    echo "   MEASURE FAILED (see $safe.err)"
  fi
  docker exec "$OLLAMA_CTR" ollama stop "$model" >/dev/null 2>&1
done

echo ""
echo "== restoring live model: $LIVE_MODEL =="
docker exec "$OLLAMA_CTR" ollama run "$LIVE_MODEL" "ok" >/dev/null 2>&1
docker exec "$OLLAMA_CTR" ollama ps
echo "results in: $OUT"
