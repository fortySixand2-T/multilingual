---
id: 1146
title: My deck preview: common words lose their main meaning (sinon, exprès, sujet, plan, truc, pas, bête, ancien, pire, nouvelle)
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
The everyday sense should be first in the gloss.

## Actual
- `sinon` -> "except, apart from, if not" (main: "otherwise")
- `exprès` -> adjective "express, special delivery" (main: adverb "on purpose")
- `sujet` -> "subject (in a monarchy)" (main: subject / topic)
- `plan` -> "map, plane (flat surface)" (main: "plan")
- `truc` -> "procedure, technique, trick" (main: "thing, whatsit")
- `pas` -> adverb "step, pace, strait" (the negation particle is lost; en is noun senses under an adverb pos)
- `bête` -> noun f "beast, animal" (learners mean adjective "stupid")
- `ancien` -> noun m "old person" (main: adjective "old / former"); `pire` -> noun "worst" (main: adjective "worse")
- `nouvelle` -> pos adjective, en "news, piece of information, novella (f.)" (pos and gloss disagree; main adjective sense "new (f.)" absent)
- `tandis` -> pos noun "while" (only used in "tandis que"); `n'importe quoi` -> noun "anything" (means "nonsense" as an exclamation); `en fait` -> pos noun; `celle-ci` -> noun f
- `vase` -> noun f "silt, mud, vase" (the usual noun is un vase, m; gender of the rare entry applied)
- `sujet`, `plan`, `rang`, `truc` show that long definitional senses are dropped so only side senses remain.

## Notes
Root cause: build_gloss_table.translations() returns [] for any gloss longer than MAX_WORDS=3 words, so the central, definitional senses of polysemous common words vanish and the minor short senses win. Gender comes from the union of tags across all entries (_gender(tags)), so a rare feminine entry makes "vase" f.

## Triage
- Explanation: Reproduced from the TSV: sujet noun is 'subject (in a monarchy)', plan noun 'map, plane', truc 'procedure, technique, trick', bete noun-first. Cause: translations() drops long definitional glosses (MAX_WORDS=3) so only side senses survive; Wiktionary pos order puts noun before adjective (bete, ancien noun m); gender via _gender(tags) union per entry (vase f from rare 'silt' entry).
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Real and high: everyday meanings missing from very common words. PRIMARY for the 'main meaning missing' family; marteau/cuite (1179) are further examples. FIX LOCATION: scripts/build_gloss_table.py (keep/shorten the first sense even when long, e.g. keep first piece before ';', frequency-aware ordering, override list). The pas/nouvelle pos-vs-gloss mismatch part is runtime (1161); noun-vs-adjective choice is 1162; vase gender is 1163.

## Critic
- Challenge: Possibly only fixable with curated overrides.
- Holds up? Yes. Everyday meaning absent for sujet/plan/truc/sinon/marteau/cuite is a real wrong-card defect for common words. Generator cause is concrete (translations() drops glosses longer than 3 words), so the fix is a rule change (keep/shorten first piece of a long first sense), not hand data. This is the primary issue; marteau/cuite/rang/file regressions go on its checklist. Pos/gloss mismatch is 1161, noun-vs-adjective 1162, vase gender 1163.
- Final verdict: validated

## Fix
- `scripts/build_gloss_table.py`: a noun's long leading definition is cut where it starts describing (marteau = hammer, ...), and a small override block fixes plan, sujet, truc, sinon, rang, file, pire, bête. Pos/gloss mismatch is 1161; vase gender is 1163. Table diff vs before: 17,270 -> 17,304 rows, 0 removed, 21 changed, 34 added (mostly determiners).
