#!/usr/bin/env python3
"""Generate TTS audio for content audio refs (text -> say -> mp3).

Audio is a *build artifact* regenerated from version-controlled text, so the text
stays the single source of truth:

  - vocab cards (`audio`)        <- the French word (`fr`)
  - listening comprehension      <- the set `script` (transcript)
  - lesson `listen_type` drills  <- the exercise `answer`

macOS only (uses `say`); encodes AIFF -> PCM WAV (built-in `afconvert`) -> MP3 (`lame`).
Idempotent: existing files are skipped unless `--force`.

    python scripts/gen_audio.py a1            # generate missing clips for level a1
    python scripts/gen_audio.py a1 --force    # regenerate all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content"

# accent tag (ComprehensionSet.accent) -> installed macOS voice.
# Default is Québécois — the platform targets TEF Canada.
VOICE_BY_ACCENT = {"qc": "Amélie", "fr": "Jacques"}
DEFAULT_VOICE = "Amélie"


def _voice(accent: str | None) -> str:
    return VOICE_BY_ACCENT.get(accent or "", DEFAULT_VOICE)


def _iter_yaml(d: Path):
    for f in sorted(d.glob("*.yaml")):
        yield yaml.safe_load(f.read_text())


def collect(level: str) -> list[tuple[str, str, str]]:
    """Return (filename, text, voice) jobs for every audio ref in the level."""
    root = CONTENT_ROOT / level
    jobs: list[tuple[str, str, str]] = []

    vdir = root / "vocab"
    if vdir.is_dir():
        for data in _iter_yaml(vdir):
            for card in data or []:
                # every vocab word gets a pronunciation clip, keyed by convention
                # `<level>/audio/<id>.mp3` (matches get_vocab in app/content/api.py)
                ref = card.get("audio") or f"{level}/audio/{card['id']}.mp3"
                jobs.append((Path(ref).name, card["fr"], DEFAULT_VOICE))

    cdir = root / "comprehension"
    if cdir.is_dir():
        for data in _iter_yaml(cdir):
            if data and data.get("skill") == "listening" and data.get("audio_ref"):
                text = data.get("script") or data.get("title", "")
                jobs.append((Path(data["audio_ref"]).name, text, _voice(data.get("accent"))))

    ldir = root / "lessons"
    if ldir.is_dir():
        for data in _iter_yaml(ldir):
            for ex in (data or {}).get("exercises", []):
                if ex.get("type") == "listen_type" and ex.get("audio_ref"):
                    jobs.append((Path(ex["audio_ref"]).name, ex["answer"], DEFAULT_VOICE))

    return jobs


def synthesize(text: str, voice: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        txt = Path(td) / "in.txt"
        aiff = Path(td) / "a.aiff"
        wav = Path(td) / "a.wav"
        txt.write_text(text)
        subprocess.run(["say", "-v", voice, "-f", str(txt), "-o", str(aiff)], check=True)
        subprocess.run(["afconvert", str(aiff), str(wav), "-d", "LEI16", "-f", "WAVE"], check=True)
        subprocess.run(["lame", "--quiet", "-V5", str(wav), str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("level", nargs="?", default="a1")
    ap.add_argument("--force", action="store_true", help="regenerate files that exist")
    args = ap.parse_args()

    out_dir = CONTENT_ROOT / args.level / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = collect(args.level)
    if not jobs:
        print(f"no audio refs found for level {args.level!r}")
        return 0

    made = skipped = 0
    for name, text, voice in jobs:
        out = out_dir / name
        if out.exists() and not args.force:
            skipped += 1
            continue
        if not (text or "").strip():
            print(f"  ! {name}: empty text, skipping")
            continue
        synthesize(text, voice, out)
        made += 1
        print(f"  ♪ {name:24s} {voice:8s} <- {text[:48]!r}")

    print(f"level {args.level!r}: {made} generated, {skipped} already present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
