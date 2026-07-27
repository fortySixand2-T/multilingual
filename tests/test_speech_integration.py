"""Real-adapter integration for the speech stack: faster-whisper (STT) + Piper (TTS).

Unlike test_speech.py (which fakes STT/TTS to test orchestration), this exercises
the *actual* models — the thing the self-host deploy stands up. The models are
heavy and absent in CI / local dev, so the whole module is skipped unless
RUN_SPEECH_INTEGRATION=1. They ARE baked into the self-host image, so run there:

    docker exec multilingual-app-1 sh -lc \
      "cd /app && RUN_SPEECH_INTEGRATION=1 uv run pytest tests/test_speech_integration.py -q"

Gating is explicit-opt-in (not auto-detect) so a stray run can never trigger a
multi-hundred-MB model download on an unsuspecting box.
"""

from __future__ import annotations

import io
import os
import shutil
import wave
from pathlib import Path

import pytest

if os.getenv("RUN_SPEECH_INTEGRATION") != "1":
    pytest.skip(
        "real STT/TTS integration — set RUN_SPEECH_INTEGRATION=1 (needs whisper + piper)",
        allow_module_level=True,
    )

from app.ai.adapters.faster_whisper_adapter import FasterWhisperAdapter
from app.ai.adapters.piper_adapter import PiperAdapter

_FIXTURES = Path(__file__).resolve().parent.parent / "qa" / "fixtures" / "speech"
_VOICE = os.getenv("PIPER_VOICE", "/app/voices/fr_FR-siwis-medium.onnx")
_WHISPER = os.getenv("WHISPER_MODEL", "small")


@pytest.fixture(scope="session")
def piper() -> PiperAdapter:
    # When integration is explicitly requested, a missing engine is a real failure,
    # not a skip — otherwise a broken deploy would look like a passing run.
    assert shutil.which("piper"), "piper binary not on PATH"
    assert Path(_VOICE).exists(), f"piper voice model missing: {_VOICE}"
    return PiperAdapter(voice_model=_VOICE)


@pytest.fixture(scope="session")
def whisper() -> FasterWhisperAdapter:
    return FasterWhisperAdapter(model=_WHISPER, device="cpu", compute_type="int8")


def _wav_frames(b: bytes) -> int:
    with wave.open(io.BytesIO(b)) as w:
        return w.getnframes()


def test_piper_synthesizes_nonempty_wav(piper: PiperAdapter) -> None:
    out = piper.synthesize(text="Bonjour, je voudrais un café, s'il vous plaît.")
    assert out[:4] == b"RIFF", "output is not a WAV/RIFF container"
    assert _wav_frames(out) > 0, "synthesized WAV has no audio frames"


def test_whisper_transcribes_french_fixture(whisper: FasterWhisperAdapter) -> None:
    audio = (_FIXTURES / "hello-fr.wav").read_bytes()
    t = whisper.transcribe(audio=audio, lang="fr")
    low = t.text.lower()
    # hello-fr.wav: "Bonjour, je m'appelle Claire et j'habite à Montréal…"
    assert any(w in low for w in ("claire", "montréal", "montreal", "appelle")), (
        f"unexpected transcript: {t.text!r}"
    )
    assert t.provider == "faster-whisper"


def test_whisper_transcribes_browser_webm(whisper: FasterWhisperAdapter) -> None:
    # hello-fr.webm is a genuine Chrome MediaRecorder webm/opus blob (same utterance
    # as hello-fr.wav), captured through the Speaking screen. This is the H1 path:
    # the real browser codec must decode (via PyAV) and transcribe, not just a clean wav.
    audio = (_FIXTURES / "hello-fr.webm").read_bytes()
    low = whisper.transcribe(audio=audio, lang="fr").text.lower()
    assert any(w in low for w in ("claire", "montréal", "montreal", "appelle")), (
        f"browser webm/opus did not decode+transcribe: {low!r}"
    )


def test_whisper_rejects_non_audio(whisper: FasterWhisperAdapter) -> None:
    # H9: corrupt / non-audio uploads must surface as TranscriptionError (→ 4xx),
    # not an opaque crash. empty.bin is 0 bytes; not-audio.bin is random bytes.
    from app.ai.errors import TranscriptionError

    for name in ("empty.bin", "not-audio.bin"):
        with pytest.raises(TranscriptionError):
            whisper.transcribe(audio=(_FIXTURES / name).read_bytes(), lang="fr")


def test_whisper_silence_is_empty_transcript(whisper: FasterWhisperAdapter) -> None:
    # H9: silence must decode to an empty transcript so the turn is skipped, not billed.
    t = whisper.transcribe(audio=(_FIXTURES / "silence.wav").read_bytes(), lang="fr")
    assert t.text.strip() == "", f"silence produced a phantom transcript: {t.text!r}"


def test_piper_to_whisper_roundtrip(piper: PiperAdapter, whisper: FasterWhisperAdapter) -> None:
    # Synthesize known French, transcribe it back — proves both adapters interoperate
    # (incl. Piper's 22.05 kHz output decoding through whisper) without the LLM/HTTP.
    text = "Je voudrais réserver une table pour deux personnes."
    wav = piper.synthesize(text=text)
    low = whisper.transcribe(audio=wav, lang="fr").text.lower()
    assert any(w in low for w in ("réserver", "table", "personnes", "deux")), (
        f"roundtrip lost the content: {low!r}"
    )
