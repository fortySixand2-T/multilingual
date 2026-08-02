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


def test_removes_misc_symbols_and_arrows_emoji():
    # U+2B50 (star), U+2B06 (up arrow) live in the Misc Symbols and Arrows block,
    # not covered by the other four _EMOJI ranges (qa-570).
    assert _clean("Bravo ⭐ continue ⬆ !") == "Bravo continue !"


def test_strips_truncated_markdown_link_missing_closing_paren():
    # A reply-length cap can cut a Markdown link mid-URL, leaving no ")" (qa-571).
    assert _clean("Regarde [le site](https://example.com/lo") == "Regarde le site"


def test_strips_bare_url():
    # A raw (non-Markdown) URL should not be voiced letter-by-letter (qa-572).
    out = _clean("Voir https://exemple.fr/page pour plus.")
    assert "https://" not in out
    assert out == "Voir pour plus."


def test_strips_leading_hyphen_bullet_markers():
    # "- item" list markers are list noise, not French text, and should be
    # stripped like the other _MD_MARKS bullets are (qa-573).
    assert _clean("- Bonjour\n- Ça va ?") == "Bonjour Ça va ?"


def test_hyphen_bullet_strip_preserves_french_elision_hyphens():
    # Mid-word hyphens (not at start of line) must survive.
    assert (
        _clean("Qu'est-ce qui t'a amenée, peut-être vas-y ?")
        == "Qu'est-ce qui t'a amenée, peut-être vas-y ?"
    )
