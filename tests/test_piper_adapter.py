"""Piper TTS text cleaning (`_clean`): strip markup/emoji, normalize typographic
punctuation, and collapse to one line.

The single-line part is load-bearing — Piper emits one WAV per input line and
concatenates them, so a multi-line reply would play only up to the first break.
The markup/emoji stripping keeps diction clean (Piper otherwise voices `*`, `#`,
emoji, etc.)."""

from app.ai.adapters.piper_adapter import _clean


def test_collapses_newlines_to_one_line():
    out = _clean("Bonjour Claire.\nQu'est-ce qui t'a amenée ?")
    assert "\n" not in out
    assert out == "Bonjour Claire. Qu'est-ce qui t'a amenée ?"


def test_collapses_all_whitespace_runs():
    assert _clean("  a\n\nb\tc   d  ") == "a b c d"


def test_single_clean_line_unchanged():
    assert _clean("Bonjour, je voudrais un café.") == "Bonjour, je voudrais un café."


def test_strips_markdown_emphasis_and_headings():
    assert _clean("**Très** bien ! _Bravo_ et `voilà` ## note") == "Très bien ! Bravo et voilà note"


def test_unwraps_markdown_links_to_label():
    assert _clean("Voir [le musée](https://x.fr) demain.") == "Voir le musée demain."


def test_removes_emoji():
    assert _clean("Bravo 👏🎉 continue ! 😀") == "Bravo continue !"


def test_normalizes_typographic_punctuation_keeping_french():
    # smart quotes/apostrophe -> plain; em dash -> comma; ellipsis -> period;
    # French accents and guillemets are preserved.
    assert _clean("L’avion — c’est “cher”… « oui »") == "L'avion , c'est \"cher\". « oui »"


def test_keeps_accents_and_guillemets():
    assert _clean("Ça coûte « très » cher à Montréal.") == "Ça coûte « très » cher à Montréal."
