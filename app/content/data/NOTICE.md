# Third-party data

The tables in this directory are derived from two openly licensed sources. Both are
**CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/); the derived tables
below are shared under the same licence.

## fr_gloss.tsv.gz: English Wiktionary

Short English meanings of common French words, taken from the English Wiktionary
(https://en.wiktionary.org) through the kaikki.org extract
(https://kaikki.org/dictionary/French/). Wiktionary contributors hold the copyright of
the text.

**Changes made:** only current, neutral senses of words Lexique counts at least once per
million are kept; each is shortened to a translation of at most three words (long
definitions are cut or dropped), at most three translations per word and part of
speech, and a few high-frequency rows are corrected by hand. Rebuild with
`scripts/build_gloss_table.py`.

## fr_forms.tsv.gz, fr_gender.tsv: Lexique 3

Each spelling's usual part of speech, frequency (films and books, per million) and
noun gender, from Lexique 383 (http://www.lexique.org; New, Pallier, Brysbaert and
Ferrand). **Changes made:** reduced to one line per spelling, with a few gender rows
corrected by hand. Rebuild with `scripts/build_forms_table.py` and
`scripts/build_gender_table.py`.

The app credits both sources in its footer.
