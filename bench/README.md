# Ollama model/quant benchmark (self-hosted box)

Decides which local model + quantization to run on the GTX 1070 (8 GB, Pascal
CC 6.1) box before flipping `OLLAMA_MODEL`. Measures the numbers that actually
matter on old hardware: **VRAM fit** (does it stay 100% on the GPU or spill to
CPU), **generation tokens/sec**, **prompt-ingest tokens/sec**, **time-to-first-token**,
and **cold-load time** — across a matrix that spans a 3B up to a 14B.

## Files
- `ollama_perf.py` — the probe. Runs **inside the app container** (only it can reach
  `http://ollama:11434`), stdlib-only. Takes one model tag, prints a JSON result.
- `run_on_box.sh` — orchestration on the box: pull → unload others → measure →
  capture fit → restore the live model. Writes `results/*.json`.
- `render_report.py` — turns `results/*.json` into `reports/ollama-perf-<date>.md`.
- `results/` — raw JSON + `ollama ps` snapshots (committed for the record).
- `reports/` — the rendered markdown report.

## Run it
The probe must run where it can reach Ollama, so `run_on_box.sh` execs into the
containers. Copy `bench/` to the box (or `git pull` the branch there) and:

```bash
# on rohith@10.0.0.54, from the repo root
bash bench/run_on_box.sh                       # full default matrix
MODELS="qwen2.5:3b-instruct-q4_K_M llama3.1:latest" bash bench/run_on_box.sh   # subset
```

Then render locally (or on the box):

```bash
python3 bench/render_report.py
```

The driver restores `llama3.1:latest` as the resident model at the end, so the
live app is unaffected once the run completes. During the run the app's LLM is
briefly swapped out — run it when the box is idle.

## Matrix (default)
`llama3.1:latest` (baseline) · `qwen2.5:3b-instruct-q4_K_M` ·
`qwen2.5:7b-instruct-q4_K_M` · `q5_K_M` · `q6_K` · `qwen2.5:14b-instruct-q3_K_M`.

K-quants only (not IQ-quants): the importance-matrix IQ formats run slowly on
Pascal, so they're excluded on purpose.
