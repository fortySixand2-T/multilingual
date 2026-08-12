#!/usr/bin/env bash
# Generate real sample outputs for the blind quality eval, ON THE BOX.
# Models are already pulled by run_on_box.sh. For each, run one model resident at a
# time and pipe gen_samples.py into the app container. Raw outputs -> results/samples/.
# Restores the live model (llama3.1) at the end.
set -uo pipefail

OLLAMA_CTR="${OLLAMA_CTR:-multilingual-ollama-1}"
APP_CTR="${APP_CTR:-multilingual-app-1}"
LIVE_MODEL="${LIVE_MODEL:-llama3.1:latest}"
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/results/samples"
GEN_PY="$DIR/gen_samples.py"
mkdir -p "$OUT"

MODELS="${MODELS:-\
llama3.1:latest \
qwen2.5:3b-instruct-q4_K_M \
qwen2.5:7b-instruct-q4_K_M \
qwen2.5:7b-instruct-q5_K_M \
qwen2.5:7b-instruct-q6_K \
qwen2.5:14b-instruct-q3_K_M}"

unload_all() {
  docker exec "$OLLAMA_CTR" ollama ps 2>/dev/null | awk 'NR>1 && $1!="" {print $1}' \
    | while read -r m; do docker exec "$OLLAMA_CTR" ollama stop "$m" >/dev/null 2>&1; done
}

echo "== generating quality samples =="
for model in $MODELS; do
  safe="$(echo "$model" | tr '/:' '__')"
  echo ">> $model"
  docker exec "$OLLAMA_CTR" ollama pull "$model" >/dev/null 2>&1
  unload_all
  if docker exec -i "$APP_CTR" python - "$model" <"$GEN_PY" >"$OUT/$safe.json" 2>"$OUT/$safe.err"; then
    echo "   ok -> $safe.json"
  else
    echo "   FAILED (see $safe.err)"
  fi
  docker exec "$OLLAMA_CTR" ollama stop "$model" >/dev/null 2>&1
done

echo "== restoring live model: $LIVE_MODEL =="
docker exec "$OLLAMA_CTR" ollama run "$LIVE_MODEL" "ok" >/dev/null 2>&1
echo "samples in: $OUT"
