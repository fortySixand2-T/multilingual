"""Ollama model/quant performance probe for the self-hosted box (GTX 1070, 8 GB).

Runs INSIDE the app container (`docker exec -i multilingual-app-1 python - <model>`)
because Ollama has no host-published port — only the app container can reach
`http://ollama:11434`. Dependency-free (stdlib urllib) so it works in the slim
image, which has no httpx.

For one model it runs a fixed suite of prompts that mirror the app's real routing
profiles (a plain short drill, a longer grammar explanation, two strict-JSON
profiles, and the length-capped examiner), and reports Ollama's *native* timing
fields (exact, not wall-clock guesses):

  eval_count / eval_duration          -> generation tokens/sec  (the headline number)
  prompt_eval_count / prompt_eval_dur -> prompt-ingest tokens/sec
  load_duration                       -> cold model-load time
  total_duration                      -> end-to-end latency

Plus one streaming request per profile to measure real time-to-first-token (TTFT),
the number that decides whether the box "feels" responsive.

Output: one JSON object on stdout (raw per-run samples + medians). The driver
(run_on_box.sh) captures `ollama ps` separately for the VRAM-fit / GPU-vs-CPU-spill
picture and render_report.py turns the JSON into the markdown report.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.request

BASE = "http://ollama:11434"
RUNS = 3  # measured runs per profile (after 1 warmup), medianed

# Prompts mirror the live routing profiles (app/config/ai_routing.ollama.yaml) so the
# numbers reflect real usage, not a synthetic micro-benchmark. temperature/max_tokens/
# format match how the app actually calls each profile.
SUITE = [
    {
        "profile": "drill_a2",
        "system": "You are a French (FLE) tutor. Reply only in French. Be concise.",
        "user": "Crée un exercice à trous de niveau A2 sur le passé composé avec le verbe "
        "'aller'. Donne la phrase à trous puis la réponse.",
        "temperature": 0.3,
        "max_tokens": 200,
        "format": None,
    },
    {
        "profile": "grammar_explain",
        "system": "You are a French grammar teacher. Explain clearly in English with French "
        "examples.",
        "user": "Explain the difference between the passé composé and the imparfait, with two "
        "example sentences each.",
        "temperature": 0.3,
        "max_tokens": 400,
        "format": None,
    },
    {
        "profile": "writing_feedback",
        "system": "You are a TEF writing examiner. Return ONLY JSON.",
        "user": 'Grade this A2 text and return JSON {"clb_estimate": int, "feedback": str}. '
        "Text: \"Hier je suis allé au marché. J'ai acheter des pommes et du pain. "
        'Il faisait beau."',
        "temperature": 0.3,
        "max_tokens": 400,
        "format": "json",
    },
    {
        "profile": "examiner_roleplay",
        "system": "You are a TEF oral examiner. Reply in French, 2-4 sentences, natural spoken "
        "style.",
        "user": "Bonjour ! Pouvez-vous vous présenter et me parler de votre travail ?",
        "temperature": 0.5,
        "max_tokens": 220,
        "format": None,
    },
    {
        "profile": "vocab_enrich",
        "system": "You are a French dictionary. Return ONLY JSON.",
        "user": 'For the French word "aboutir" return JSON '
        '{"en": str, "pos": str, "gender": str|null, "ipa": str}.',
        "temperature": 0.2,
        "max_tokens": 200,
        "format": "json",
    },
]


def _post(path: str, payload: dict, *, stream: bool = False, timeout: float = 300.0):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=timeout)


def _chat_once(model: str, item: dict) -> dict:
    """One non-streamed /api/chat call; returns Ollama's native timing block."""
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": item["temperature"], "num_predict": item["max_tokens"]},
        "messages": [
            {"role": "system", "content": item["system"]},
            {"role": "user", "content": item["user"]},
        ],
    }
    if item["format"]:
        payload["format"] = item["format"]
    with _post("/api/chat", payload) as r:
        data = json.loads(r.read())
    ev, evd = data.get("eval_count", 0), data.get("eval_duration", 0) or 1
    pv, pvd = data.get("prompt_eval_count", 0), data.get("prompt_eval_duration", 0) or 1
    return {
        "total_s": data.get("total_duration", 0) / 1e9,
        "load_s": data.get("load_duration", 0) / 1e9,
        "prompt_tokens": pv,
        "prompt_tok_per_s": pv / (pvd / 1e9),
        "gen_tokens": ev,
        "gen_tok_per_s": ev / (evd / 1e9),
    }


def _ttft_once(model: str, item: dict) -> float:
    """Streamed call; wall-clock seconds until the first content chunk arrives."""
    payload = {
        "model": model,
        "stream": True,
        "options": {"temperature": item["temperature"], "num_predict": item["max_tokens"]},
        "messages": [
            {"role": "system", "content": item["system"]},
            {"role": "user", "content": item["user"]},
        ],
    }
    if item["format"]:
        payload["format"] = item["format"]
    start = time.perf_counter()
    with _post("/api/chat", payload, stream=True) as r:
        for line in r:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if (chunk.get("message") or {}).get("content"):
                return time.perf_counter() - start
            if chunk.get("done"):
                break
    return time.perf_counter() - start


def _fit(model: str) -> dict:
    """From /api/ps: total footprint vs the part actually on the GPU. When
    size_vram < size the model spilled to CPU (slow on old cards) — the single most
    important compatibility signal on an 8 GB 1070."""
    with urllib.request.urlopen(BASE + "/api/ps", timeout=30) as r:
        models = json.loads(r.read()).get("models", [])
    m = next((x for x in models if x.get("name") == model or x.get("model") == model), None)
    if not m:
        return {"resident": False}
    size, vram = m.get("size", 0), m.get("size_vram", 0)
    return {
        "resident": True,
        "size_gb": round(size / 1e9, 2),
        "vram_gb": round(vram / 1e9, 2),
        "gpu_fraction": round(vram / size, 3) if size else 0.0,
        "fully_on_gpu": bool(size) and vram >= size,
    }


def run_model(model: str) -> dict:
    profiles = []
    cold_load_s = None
    for item in SUITE:
        warm = _chat_once(model, item)  # triggers cold load on the very first profile
        if cold_load_s is None:
            cold_load_s = round(warm["load_s"], 3)  # load_duration is ~0 once resident
        samples = [_chat_once(model, item) for _ in range(RUNS)]
        ttft = _ttft_once(model, item)
        med = {
            k: round(statistics.median(s[k] for s in samples), 3)
            for k in ("total_s", "gen_tok_per_s", "prompt_tok_per_s", "gen_tokens", "prompt_tokens")
        }
        med["ttft_s"] = round(ttft, 3)
        profiles.append({"profile": item["profile"], **med, "samples": samples})

    gen_rates = [p["gen_tok_per_s"] for p in profiles]
    return {
        "model": model,
        "runs_per_profile": RUNS,
        "fit": _fit(model),
        "cold_load_s": cold_load_s,
        "mean_gen_tok_per_s": round(statistics.mean(gen_rates), 2),
        "profiles": profiles,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ollama_perf.py <model-tag>", file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(run_model(sys.argv[1]), indent=2))
