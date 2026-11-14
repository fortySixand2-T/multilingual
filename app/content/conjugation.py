"""Present-tense conjugation of ~3,700 common French verbs, from Wiktionary
(`data/fr_conj.tsv.gz`, built by scripts/build_conj_table.py and checked against
Lexique), for the verb decks: each card shows its verb with every subject pronoun.

A card's word may be more than a bare infinitive: pronominal (se lever, s'asseoir) or
a phrase (faire face à, se rendre compte); its head verb is conjugated and the rest
kept. Wiktionary is CC BY-SA 4.0.
"""

from __future__ import annotations

import functools
import gzip
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "fr_conj.tsv.gz"
PERSONS = ("je", "tu", "il / elle / on", "nous", "vous", "ils / elles")
_REFLEXIVE = ("me", "te", "se", "nous", "vous", "se")
_VOWELS = tuple("aeiouyâàéèêëîïôûùœh")
IMPERSONAL = {"falloir", "valoir mieux", "pleuvoir", "neiger"}
_H_ASPIRÉ = {"haïr", "hurler", "heurter", "hausser", "hacher", "harceler", "hâter", "hanter"}


@functools.cache
def _table() -> dict[str, tuple[str, ...]]:
    """{infinitive: six present forms}, "" for a person the verb has none for."""
    if not _PATH.exists():
        return {}
    with gzip.open(_PATH, "rt", encoding="utf-8") as f:
        return {w: tuple(rest) for w, *rest in (line.rstrip("\n").split("\t") for line in f)}


def _parse(word: str) -> tuple[bool, str, str]:
    """(pronominal, head infinitive, the rest): "se rendre compte" -> (True, "rendre", "compte")."""
    w = word.strip().lower()
    pronominal = w.startswith(("se ", "s'"))
    w = w[3:] if w.startswith("se ") else w[2:] if pronominal else w
    head, _, rest = w.partition(" ")
    return pronominal, head, rest


def _elides(word: str, verb: str) -> bool:
    """True before a vowel or a mute h: j'achète, m'assieds, but je hais."""
    return word.startswith(_VOWELS) and not (word.startswith("h") and verb in _H_ASPIRÉ)


def present(word: str) -> list[tuple[str, str]] | None:
    """[(subject, verb), …] for each person the verb has: ("je", "vais"), ("j'", "achète"),
    ("il / elle / on", "se lève"); None for a word with no table. Impersonal verbs
    (falloir, valoir mieux) have il only."""
    pronominal, head, rest = _parse(word)
    forms = _table().get(head)
    if not forms:
        return None
    if word.strip().lower() in IMPERSONAL:
        return [("il", f"{forms[2]} {rest}".strip())]
    out = []
    for person, reflexive, form in zip(PERSONS, _REFLEXIVE, forms, strict=True):
        if not form:
            continue
        if pronominal:
            elided = reflexive in ("me", "te", "se") and _elides(form, head)
            form = f"{reflexive[0]}'{form}" if elided else f"{reflexive} {form}"
        elif person == "je" and _elides(form, head):
            person = "j'"
        out.append((person, f"{form} {rest}".strip()))
    return out


def group(word: str) -> str:
    """ "regular" for the -er verbs (all but aller; spelling changes such as j'achète
    included) and the -ir verbs that take -issons (finir), "irregular" for the rest,
    "" for a word with no table."""
    _, head, _ = _parse(word)
    forms = _table().get(head)
    if not forms:
        return ""
    if head.endswith("er") and head != "aller":
        return "regular"
    regular_ir = head.endswith("ir") and forms[3] == head[:-2] + "issons"
    return "regular" if regular_ir else "irregular"
