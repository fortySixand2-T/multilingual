---
id: 1147
title: My deck preview: glosses with capitalised words, odd parentheticals or non-infinitive reflexive forms (sage 'Chaste', foi 'Faith', s'ennuyer 'bore oneself')
severity: low
area: content
persona: returning-learner
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. Sign up with invite code qa065-a, then for each word below call `POST /vocab/personal/preview {"word": "<w>"}` (Bearer token).
2. Read `enrichment.en` / `pos` / `gender` as a learner adding the word to My deck.

## Expected
Consistent lower-case translations, infinitives written "to ...", no scientific or untranslated parentheticals.

## Actual
- `sage` -> adjective "Chaste, modest, good" (capitalised; "wise" absent)
- `foi` -> "Faith" (capitalised)
- `s'ennuyer` -> "bore oneself" (should be "to get bored"); `se promener` -> "take a walk"; `se tromper` -> "make a mistake"; `se rappeler`, `se sentir`, `se passer`, `s'apercevoir` have no "to" while `se lever`/`se dépêcher` do
- `quelqu'un` -> "someone, somebody, (colloquial) (a) somebody"
- `oignon` -> "onion (Allium cepa), bulb (of a plant)"; `brun` -> "brown (color/colour)"; `carotte` -> "carrot (vegetable), carotte"; `noisette` -> "hazelnut, noisette"; `cerise` -> "cherry (fruit), cerise (color)"; `nous` -> "nous, ..." (French word in the English gloss)
- `meilleur` etc. (course words) use ";" while dictionary words use ","; inconsistent separators

## Notes
Root cause: pieces are kept verbatim from Wiktionary (only _ARTICLE stripped, case untouched); parentheticals <=3 words kept. Normalise case, drop pieces equal to the headword, and prefix "to" for verbs.

## Triage
- Explanation: Reproduced from code: pieces kept verbatim from Wiktionary (only the leading article stripped): 'Chaste', 'Faith' capitalised; pieces equal to the headword ('nous', 'carotte') kept; reflexive verbs have no 'to' because the Wiktionary gloss lacks it; parentheticals <=3 words kept.
- Against spec: CLAUDE.md/QA history (QA 1001) already cleans model glosses for consistency; dictionary glosses bypass that only partly (clean_gloss runs, but not case/to-normalisation).
- Verdict: validated
- Rationale: Low cosmetic but cheap and visible. FIX LOCATION: scripts/build_gloss_table.py (lowercase unless proper noun/acronym, drop piece == headword, prefix 'to' for verbs) and/or enrich.clean_gloss (runtime, no rebuild needed).

## Critic
- Challenge: Purely cosmetic: capitalised 'Faith', 'carotte' repeated, missing 'to' on reflexives. Meaning is still understandable and editable. Three normalisations (case, headword, to-prefix) add code for little learner value.
- Holds up? No. Cosmetic; if 1146 rebuilds the table, lowercasing can ride along opportunistically but is not worth its own fix.
- Final verdict: deferred
