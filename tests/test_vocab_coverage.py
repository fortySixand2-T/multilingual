"""Regression tests for the round-055 content QA fixes (issues 750-755).

Covers:
- 750: a garbled mcq option in health-b1-01.e5.
- 751: an over-accepting `accept` entry in food-04.e7.
- 752/753/754: new_vocab words that were never shown in any exercise
  (adjectives-01, medias-b2-01, verbs-01, verbs-02).
- 755: the systemic new_vocab/exercise-coverage gap, now guarded across
  *every* lesson at every level rather than just the round's new lessons.
  Every `new_vocab` id should be resolvable to a headword that
  shows up somewhere in the lesson's own exercises (allowing for inflected/
  agreement forms via a stem match), since new_vocab is exactly what seeds
  SRS review cards on first lesson pass (`app.progress.api.seed_cards`).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.content.loader import load_content
from app.content.models import Exercise

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"

# Lessons from the round-055 new-lesson arc (PRs #87-#90) that issue 755 swept.
# `vouloir` in a1/verbs-01 is a known, human-verified exception: it's shown via
# the conjugated form "veux" as the graded word_bank answer in e6, which a
# literal/stemmed headword match can't detect.
KNOWN_CONJUGATED_ONLY = {("a1", "verbs-01"): {"vouloir"}}

LEVELS = ("a1", "a2", "b1", "b2")

# Legacy lessons that predate the round-055 arc and still have `new_vocab` words
# their own exercises never show. Tracked explicitly, and closed level by level
# (see docs/legacy-lesson-coherence-plan.md). This mapping may only ever shrink:
# `test_known_gaps_are_not_stale` fails if an entry is already fixed, and
# `test_all_lessons_new_vocab_is_practiced_in_exercises` fails if a lesson grows
# a gap that is not recorded here.
KNOWN_GAPS: dict[tuple[str, str], set[str]] = {
    ("a1", "cafe-03"): {
        "chocolat_chaud",
        "citron",
        "croissant",
        "glacon",
        "limonade",
        "pourboire",
        "tasse",
        "terrasse",
    },
    ("a1", "directions-01"): {"rue"},
    ("a1", "directions-03"): {"carrefour", "coin", "feu", "nord", "place", "pont", "pres", "sud"},
    ("a1", "family-02"): {"epouse"},
    ("a1", "family-03"): {
        "bebe",
        "cousin",
        "cousine",
        "grand_mere",
        "grand_pere",
        "oncle",
        "parents",
        "tante",
    },
    ("a1", "greetings-03"): {
        "a_demain",
        "bienvenue",
        "bonne_nuit",
        "desole",
        "madame",
        "mademoiselle",
        "monsieur",
        "stp",
    },
    ("a1", "numbers-03"): {
        "cinquante",
        "mille",
        "quarante",
        "quatorze",
        "quinze",
        "seize",
        "treize",
        "trente",
    },
    ("a1", "restaurant-02"): {
        "banane",
        "beurre",
        "fruit",
        "gateau",
        "poivre",
        "salade",
        "sel",
        "tomate",
    },
    ("a1", "restaurant-03"): {
        "bon_appetit",
        "chef",
        "delicieux",
        "fourchette",
        "nappe",
        "plat_du_jour",
        "vegetarien",
    },
    ("a1", "shopping-01"): {"carte"},
    ("a1", "shopping-03"): {
        "client",
        "essayer",
        "gratuit",
        "monnaie",
        "panier",
        "payer",
        "recu",
        "vendeur",
    },
    ("a1", "time-01"): {"heure"},
    ("a1", "time-03"): {"annee", "hier", "maintenant", "minute", "mois", "semaine", "soir"},
    ("a1", "weather-01"): {"meteo", "soleil"},
    ("a1", "weather-03"): {
        "brouillard",
        "ciel",
        "degre",
        "humide",
        "mauvais_temps",
        "parapluie",
        "saison",
        "temperature",
    },
    ("a2", "cuisine-a2-01"): {"four"},
    ("a2", "cuisine-a2-03"): {
        "bouillir",
        "couper",
        "cuire",
        "eplucher",
        "gouter",
        "ingredient",
        "poele",
        "saler",
    },
    ("a2", "loisirs-a2-01"): {"loisir", "sport"},
    ("a2", "loisirs-a2-03"): {
        "concert",
        "dessiner",
        "equipe",
        "jardiner",
        "peindre",
        "photographie",
        "voyager",
    },
    ("a2", "maison-a2-03"): {"canape", "cle", "escalier", "etage", "lit", "mur", "toit"},
    ("a2", "routine-a2-01"): {"se_laver", "se_lever", "shabiller"},
    ("a2", "routine-a2-03"): {
        "dejeuner",
        "diner",
        "habitude",
        "petit_dejeuner",
        "se_brosser",
        "se_depecher",
        "se_doucher",
        "se_reposer",
    },
    ("a2", "sante-a2-01"): {"avoir_mal", "medicament", "sante"},
    ("a2", "sante-a2-03"): {
        "bras",
        "dos",
        "fievre",
        "ordonnance",
        "pharmacie",
        "pied",
        "rhume",
        "toux",
    },
    ("a2", "sentiments-a2-01"): {"aimer", "fatigue", "triste"},
    ("a2", "sentiments-a2-03"): {
        "ennuye",
        "fier",
        "inquiet",
        "jaloux",
        "pleurer",
        "rire",
        "sourire",
        "surpris",
    },
    ("a2", "transport-a2-01"): {"conduire"},
    ("a2", "transport-a2-03"): {
        "bateau",
        "essence",
        "horaire",
        "permis",
        "quai",
        "retard",
        "taxi",
        "train",
    },
    ("a2", "travail-a2-03"): {
        "carriere",
        "chomage",
        "competence",
        "contrat",
        "diplome",
        "entretien",
        "experience",
        "stage",
    },
    ("a2", "vetements-a2-01"): {"chaussures", "vetement"},
    ("a2", "vetements-a2-03"): {
        "ceinture",
        "couleur",
        "cravate",
        "echarpe",
        "gant",
        "pull",
        "short",
    },
    ("a2", "voyage-a2-01"): {"voyage"},
    ("a2", "voyage-a2-03"): {
        "depart",
        "douane",
        "frontiere",
        "guide",
        "itineraire",
        "sejour",
        "souvenir",
    },
    ("b1", "argent-b1-03"): {"decouvert", "pouvoir_achat", "prelevement"},
    ("b1", "conseils-b1-03"): {
        "alternative",
        "bilan",
        "compromis",
        "doute",
        "precaution",
        "recommandation",
    },
    ("b1", "education-b1-03"): {"inscription", "pedagogie", "savoir"},
    ("b1", "environnement-b1-03"): {
        "biodiversite",
        "developpement_durable",
        "empreinte",
        "espece",
        "ressource",
    },
    ("b1", "immigration-b1-03"): {"administration", "installation", "naturalisation"},
    ("b1", "logement-b1-03"): {"agence_immobiliere", "ameublement", "copropriete", "hypotheque"},
    ("b1", "medias-b1-03"): {
        "audience",
        "censure",
        "desinformation",
        "presse",
        "reportage",
        "source",
    },
    ("b1", "mode-de-vie-b1-03"): {
        "epanouissement",
        "exercice",
        "hygiene",
        "sedentarite",
        "surmenage",
        "vitalite",
    },
    ("b1", "projets-b1-03"): {
        "motivation",
        "obstacle",
        "perseverance",
        "planification",
        "priorite",
        "progres",
    },
    ("b1", "travail-b1-03"): {
        "avancement",
        "demission",
        "hierarchie",
        "mutation",
        "negociation",
        "reconversion",
    },
}

_ARTICLES = ("le ", "la ", "les ", "l'", "un ", "une ", "des ")


def _norm(s: str) -> str:
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return stripped.lower()


def _strip_article(fr: str) -> str:
    n = _norm(fr)
    for a in _ARTICLES:
        if n.startswith(a):
            return n[len(a) :]
    return n


def _exercise_blob(ex: Exercise) -> str:
    t = ex.type
    if t == "match_pairs":
        parts = [w for pair in ex.pairs for w in pair]
    elif t == "mcq":
        parts = [ex.prompt, *[str(o) for o in ex.options], str(ex.answer)]
        if ex.explain:
            parts.append(ex.explain)
    elif t == "word_bank":
        parts = [*ex.tokens, *ex.answer, ex.prompt]
    elif t == "translate":
        parts = [ex.answer, *(ex.accept or []), ex.prompt]
    elif t == "listen_type":
        parts = [ex.answer, ex.prompt]
    else:
        parts = []
    return " | ".join(parts)


def _shown_in_lesson(headword_norm: str, blob_norm: str) -> bool:
    """True if the headword (or a plausible inflected/agreement stem of it)
    appears in the lesson's exercise text."""
    if headword_norm in blob_norm:
        return True
    for cut in range(0, max(len(headword_norm) - 3, 0)):
        stem = headword_norm[: len(headword_norm) - cut]
        if len(stem) < 4:
            break
        if re.search(r"\b" + re.escape(stem), blob_norm):
            return True
    return False


def _missing_words(level: str, lesson_id: str) -> list[str]:
    bundle = load_content(CONTENT_ROOT, level)
    lesson = bundle.lessons[lesson_id]
    blob_norm = _norm(" | ".join(_exercise_blob(e) for e in lesson.exercises))
    exceptions = KNOWN_CONJUGATED_ONLY.get((level, lesson_id), set())
    missing = []
    for vid in lesson.new_vocab:
        if vid in exceptions:
            continue
        headword = _strip_article(bundle.vocab[vid].fr)
        if not _shown_in_lesson(headword, blob_norm):
            missing.append(vid)
    return missing


def test_health_b1_01_e5_mcq_options_are_well_formed():
    """Issue 750: the second mcq option was the garbled 'allée aller'."""
    bundle = load_content(CONTENT_ROOT, "b1")
    ex = next(e for e in bundle.lessons["health-b1-01"].exercises if e.id == "health-b1-01.e5")
    assert ex.options == ["allé", "allée", "vais"]
    assert all(" " not in o for o in ex.options), "each mcq option should be a single word/phrase"


def test_food_04_e7_accept_does_not_over_specify():
    """Issue 751: 'accept' shouldn't add unrequested meaning (red wine) to a
    prompt that only asked for 'a glass of wine'."""
    bundle = load_content(CONTENT_ROOT, "a1")
    ex = next(e for e in bundle.lessons["food-04"].exercises if e.id == "food-04.e7")
    accept = ex.accept or []
    assert "un verre de vin rouge" not in accept
    assert all("rouge" not in a for a in accept)


def test_anchor_lessons_have_no_unpracticed_new_vocab():
    """Issues 752/753/754: adjectives-01, medias-b2-01, verbs-01, verbs-02 each
    had several new_vocab words never shown in any exercise; closed by adding
    a match_pairs exercise covering the gap."""
    for level, lesson_id in [
        ("a1", "adjectives-01"),
        ("b2", "medias-b2-01"),
        ("a1", "verbs-01"),
        ("a1", "verbs-02"),
    ]:
        missing = _missing_words(level, lesson_id)
        assert missing == [], f"{level}/{lesson_id} still has unpracticed new_vocab: {missing}"


def _iter_lessons():
    for level in LEVELS:
        bundle = load_content(CONTENT_ROOT, level)
        for lesson_id, lesson in bundle.lessons.items():
            if lesson.new_vocab:
                yield level, lesson_id


def test_all_lessons_new_vocab_is_practiced_in_exercises():
    """Every lesson's `new_vocab` should be shown (verbatim or via an inflected
    stem) in at least one of that lesson's own exercises — `new_vocab` seeds SRS
    cards on first pass, so a gap means a learner is quizzed on a word they were
    never taught. Known legacy gaps are carved out via KNOWN_GAPS."""
    failures = {}
    for level, lesson_id in _iter_lessons():
        missing = set(_missing_words(level, lesson_id))
        allowed = KNOWN_GAPS.get((level, lesson_id), set())
        unexpected = missing - allowed
        if unexpected:
            failures[f"{level}/{lesson_id}"] = sorted(unexpected)
    assert not failures, f"new_vocab words never shown in exercises: {failures}"


def test_known_gaps_are_not_stale():
    """KNOWN_GAPS may only shrink. Once a legacy lesson is fixed, its entry has
    to be deleted, so the carve-out can never quietly outlive the defect."""
    stale = {}
    for (level, lesson_id), allowed in KNOWN_GAPS.items():
        missing = set(_missing_words(level, lesson_id))
        fixed = allowed - missing
        if fixed:
            stale[f"{level}/{lesson_id}"] = sorted(fixed)
    assert not stale, f"these words are now practiced -- remove them from KNOWN_GAPS: {stale}"
