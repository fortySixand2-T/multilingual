"""Piper TTS text normalization. Piper emits one WAV per input line and
concatenates them to stdout, so a multi-line reply plays only up to the first
line break — `_one_line` collapses whitespace so a whole reply is one WAV."""

from app.ai.adapters.piper_adapter import _one_line


def test_collapses_newlines_to_one_line():
    out = _one_line("Bonjour Claire.\nQu'est-ce qui t'a amenée ?")
    assert "\n" not in out
    assert out == "Bonjour Claire. Qu'est-ce qui t'a amenée ?"


def test_collapses_all_whitespace_runs():
    assert _one_line("  a\n\nb\tc   d  ") == "a b c d"


def test_single_line_unchanged():
    assert _one_line("Bonjour, je voudrais un café.") == "Bonjour, je voudrais un café."
