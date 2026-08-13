"""Capture REAL model outputs for a blind quality evaluation.

Companion to ollama_perf.py (which measures speed). This runs the same kind of
prompts but keeps the generated TEXT, so a blind judge can score how good/bad each
model actually is — not just how fast it is. Runs inside the app container (only it
reaches http://ollama:11434), stdlib-only.

Fairness: greedy decoding (temperature 0) + fixed seed, identical prompts for every
model, so differences are model capability, not sampling luck. Several tasks have a
known correct answer (see ANSWER KEY in the judge prompt, NOT sent to the models) so
scoring can be objective.

    python gen_samples.py <model-tag>   ->  JSON {model, samples:[{task, prompt, output}]}
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://ollama:11434"
SEED = 42

# Tasks span the app's real work. Where a task has a checkable answer it's noted in
# the judge's answer key (kept out of the model prompt on purpose).
TASKS = [
    {
        "id": "grammar_depuis",
        "system": "You are a French grammar teacher. Explain clearly in English with correct "
        "French examples.",
        "user": "Explain when to use 'depuis', 'il y a', and 'pendant' in French time "
        "expressions. Give one correct example sentence for each.",
        "format": None,
        "max_tokens": 400,
    },
    {
        "id": "writing_feedback",
        "system": "You are a TEF writing examiner. Return ONLY valid JSON.",
        "user": "Grade this A2 French text and return JSON with keys "
        '{"clb_estimate": int (1-12), "errors": [str], "feedback": str}. '
        "List each grammatical error you find. Text: "
        "\"Je suis allé au marché hier. J'ai acheter des pomme et j'ai bu un cafés. "
        'Il faisait très beau et je suis rentrer à la maison à midi."',
        "format": "json",
        "max_tokens": 500,
    },
    {
        "id": "vocab_enrich",
        "system": "You are a French dictionary. Return ONLY valid JSON.",
        "user": 'For the French word "grenouille" return JSON '
        '{"en": str, "pos": str, "gender": "masculine"|"feminine"|null, "ipa": str}.',
        "format": "json",
        "max_tokens": 200,
    },
    {
        "id": "drill_subjunctive",
        "system": "You are a French (FLE) tutor. Reply in French.",
        "user": "Crée un exercice à trous de niveau B1 pour pratiquer le subjonctif après "
        "'il faut que', avec le verbe 'faire' à la 2e personne du singulier (tu). Donne la "
        "phrase avec un trou, puis la bonne réponse.",
        "format": None,
        "max_tokens": 200,
    },
    {
        "id": "examiner_roleplay",
        "system": "You are a TEF oral examiner. Reply in natural spoken French, 2-4 sentences.",
        "user": "Le candidat dit : « Je pense que les réseaux sociaux sont mauvais pour les "
        "jeunes. » Réagissez et posez une question de relance.",
        "format": None,
        "max_tokens": 220,
    },
    {
        "id": "correction_translation",
        "system": "You are a French teacher.",
        "user": "Correct and translate into natural French: 'I have been learning French since "
        "three years and I want improve my speaking.' Give only the corrected French sentence.",
        "format": None,
        "max_tokens": 150,
    },
]


def _chat(model: str, task: dict) -> str:
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0, "seed": SEED, "num_predict": task["max_tokens"]},
        "messages": [
            {"role": "system", "content": task["system"]},
            {"role": "user", "content": task["user"]},
        ],
    }
    if task["format"]:
        payload["format"] = task["format"]
    req = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    return (data.get("message") or {}).get("content", "")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python gen_samples.py <model-tag>", file=sys.stderr)
        raise SystemExit(2)
    model = sys.argv[1]
    samples = [{"task": t["id"], "prompt": t["user"], "output": _chat(model, t)} for t in TASKS]
    out = {"model": model, "seed": SEED, "samples": samples}
    print(json.dumps(out, ensure_ascii=False, indent=2))
