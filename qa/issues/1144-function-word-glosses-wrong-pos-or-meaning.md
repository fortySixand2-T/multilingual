---
id: 1144
title: My deck preview: very common function words get a wrong pos or wrong meaning (nous, ou, celle, son, chez, celui)
severity: high
area: content
persona: returning-learner
status: done
found: 2026-11-12
---

## Steps to reproduce
1. Sign up with invite code qa065-a, then for each word below call `POST /vocab/personal/preview {"word": "<w>"}` (Bearer token).
2. Read `enrichment.en` / `pos` / `gender` as a learner adding the word to My deck.

## Expected
Learners add the most common words first; the preview must give the main meaning and right pos.

## Actual
(all `enrichment` values; none in the course)
- `nous` -> pos noun, gender m, en "nous, (divine) reason in philosophy" (should be pronoun, "we / us")
- `ou` -> fr "où", en "where (interrogative)" (the word "ou" = "or" is unreachable; accent folding picks où; also see où itself, same gloss, correct)
- `celle` -> pronoun "she, that one" ("she" is wrong; should be "the one (f.)")
- `son` -> pos adjective, en "sound, bran" (main use is possessive "his/her/its"; and "sound" is a noun, not adjective)
- `chez` -> preposition "to, at" (should be "at the home/place of"; "to" misleads)
- `celui` -> pronoun "one"; `leur` -> "(to) them" (misses possessive "their"); `lui` -> "him, he, her" ("he" is a subject form and "her" are mixed up)
- `selon` -> "according to, whichever applies"; `après` -> "after, coming for" (second glosses are noise)

## Notes
Root cause (scripts/build_gloss_table.py): the `translations()` filter drops any sense longer than 3 words ("nous" pronoun sense is a long definition), so only incidental short senses survive; a word whose pronoun/determiner senses are all long falls through to a noun or odd entry. `gloss()` then joins first senses of every same-pos entry and the 2-sense cap keeps whatever is left. Suggest a small hand-curated override list for the ~300 most frequent function words, or a review of the highest-frequency words in the generated TSV.

## Triage
- Explanation: Reproduced (nous -> noun m 'nous, (divine) reason'). TSV has nous only as noun; pronoun senses are long definitions dropped by build_gloss_table.translations() (MAX_WORDS=3). son: TSV has only noun 'sound, bran'; at runtime lexicon.pos() rewrites pos to Lexique's usual 'adjective' AFTER the gloss was chosen (enrich.enrich), giving adjective + noun gloss. chez/selon/apres: first-sense heuristics. 'ou' returning où is the accent-fold cache/course issue (see 1175/1176), not a table problem (TSV ou = 'or, either...or').
- Against spec: Unspecified in the plan beyond 'dictionary-backed meanings, cheaper and more correct than the model' (PR #139 intent); top-frequency function words are the learner's first lookups.
- Verdict: validated
- Rationale: Real and high impact: the most frequent words get wrong pos/meaning, and the card is added with confidence. FIX LOCATION: scripts/build_gloss_table.py (small hand-curated override for ~300 top function words, plus review of top-frequency TSV rows); runtime half (pos rewritten after gloss) is tracked in 1161.

## Critic
- Challenge: Fix could mean a hand-curated ~300-word override list, which is heavy and brittle; the preview is editable.
- Holds up? Yes. Reproduced in fr_gloss.tsv.gz: nous only as 'noun m nous, (divine) reason', son only 'noun m sound, bran'. These are the most frequent words and the card is added confidently. Scope the fix to the generator (keep the first piece of long definitions, see 1146) with at most a tiny override for pronouns/determiners that still fail; do NOT hand-edit 300 rows. ou->où is 1175, not this issue.
- Final verdict: validated

## Fix
- Gloss table rebuilt (`scripts/build_gloss_table.py`, `app/content/data/fr_gloss.tsv.gz`): a sense under a header line takes the line below it (nous = we, us), determiners are kept (son = his, her; leur = their), and a handful of hand-checked rows cover what the rules cannot reach (pas, chez, selon, après, celui, celle, leur, sinon). `ou` returning `où` was the cache bug fixed under 1175.
