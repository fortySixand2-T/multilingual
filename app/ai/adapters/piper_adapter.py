"""TTS via Piper (local, subprocess). Vendor confined to adapters/.

Piper synthesizes WAV to stdout. Blocking; callers run it in a worker thread.
Output is cacheable by (text, voice) — see plan §6.
"""

from __future__ import annotations

import re
import subprocess

# LLM replies sometimes carry markup/emoji that Piper voices literally or stumble
# on ("astérisque", odd pauses). We strip those before synthesis so diction stays
# clean. French letters, accents, and guillemets « » are kept — only formatting
# noise is removed. (The reply text shown to the learner is unaffected.)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [label](url) -> label
_MD_MARKS = re.compile(r"[*_`#>|~]+")  # emphasis / heading / quote / table markers
_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"  # symbols, pictographs, emoji
    "\U00002600-\U000027bf"  # misc symbols + dingbats
    "\U0001f1e6-\U0001f1ff"  # regional indicators (flags)
    "\U00002190-\U000021ff"  # arrows
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U000020e3"  # combining enclosing keycap
    "]+",
    flags=re.UNICODE,
)
# Typographic punctuation Piper mis-voices -> plain equivalents that give the same
# pauses. Apostrophe/quote variants matter for French elision (l'avion).
_PUNCT = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "—": ",", "–": ",", "…": "."})


def _clean(text: str) -> str:
    """Strip markup/emoji, normalize typographic punctuation, and collapse all
    whitespace to a single line.

    The single-line part is load-bearing: Piper emits one WAV per input *line* and
    concatenates them to stdout — a malformed stream that players stop reading after
    the first WAV, so a multi-line reply would cut off at the first line break.
    Sentence punctuation (`.`, `?`, `!`) still gives natural pauses within the line.
    """
    text = _MD_LINK.sub(r"\1", text)
    text = _EMOJI.sub("", text)
    text = _MD_MARKS.sub("", text)
    text = text.translate(_PUNCT)
    return " ".join(text.split())


class PiperAdapter:
    name = "piper"

    def __init__(self, *, voice_model: str, piper_bin: str = "piper") -> None:
        self._voice = voice_model
        self._bin = piper_bin

    def synthesize(self, *, text: str, voice: str = "", lang: str = "fr") -> bytes:
        model = voice or self._voice
        proc = subprocess.run(
            [self._bin, "--model", model, "--output_file", "-"],
            input=_clean(text).encode("utf-8"),
            capture_output=True,
            check=True,
        )
        return proc.stdout  # WAV bytes (one file — see _clean)
