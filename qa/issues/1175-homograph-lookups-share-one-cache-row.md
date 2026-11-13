---
id: 1175
title: My deck: a/à, ou/où, du/dû, des/dés share one cached row, so the plain common word returns the accented homograph
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-11-12
---

## Steps to reproduce
1. Sign up (invite qa065-c) and POST /vocab/personal/preview {"word":"a"} then {"word":"ou"}, {"word":"du"}, {"word":"des"} (all give the plain-word reading).
2. Preview {"word":"à"}, {"word":"où"}, {"word":"dû"}, {"word":"dés"} (any user, once).
3. Preview {"word":"a"}, {"word":"ou"}, {"word":"du"}, {"word":"des"} again.

## Expected
The plain words keep their own meaning (ou = "or", du = "of the/some", des = "some", a = "has"). Typing an accented homograph must not change what the unaccented word returns.

## Actual
lookup_slug folds accents, so both spellings share one vocab_lookup row; the accented one overwrites it and the cache is shared by all users. After step 2, for every user:
- "ou" -> {"fr":"où","en":"where (interrogative)","pos":"adverb"} (the dictionary has ou = "or, either...or")
- "a" -> {"fr":"à","en":"to (destination), at, in","pos":"preposition"}
- "du" -> {"fr":"dû","en":"what is owed, what is due","pos":"noun","gender":"m"}
- "des" -> {"fr":"dés","en":"dice","pos":"noun"}
- "cru" -> {"fr":"crû","en":"raw"} (misspelling replaces the valid word)
The result depends on who looked up which spelling first; a beginner adding "ou" or "du" (some of the most common words) gets a wrong card. The card the user adds (fr "où") then also fails to match the course.

## Notes
app/content/lookup.py lookup_slug / cached_lookup (accent_count comparison only ever upgrades). Seen on qa065-app; rows in vocab_lookup slugs a, ou, du, des, cru.

## Triage
- Explanation: Reproduced mechanism: lookup_slug folds accents so a/à, ou/où, du/dû, des/dés share one vocab_lookup row; cached_lookup only ever 'upgrades' (accent_count(typed) > accent_count(row.fr)) and fresh_lookup merges over the row, so the accented homograph overwrites the plain word for every user (scratch: 'ou' now returns où). Plain word is a free first-class dictionary entry, so this is a real regression for the commonest words.
- Against spec: Slice QA 890 intent: accentless typing may be upgraded to the right accents; never meant to replace a different valid word.
- Verdict: validated
- Rationale: Real, medium (shared cache, affects all learners, permanent). PRIMARY for the accent-fold cache family (also covers 1177). FIX LOCATION: runtime lookup.py: key the cache by exact normalised form when the typed form is itself a dictionary/Lexique word (do not fold or upgrade onto it), and never let a model-proposed fr overwrite a row whose fr is a valid dictionary word.

## Critic
- Challenge: Argue the accented homograph being cached is intended (QA 890 upgrades accentless to accented).
- Holds up? Survives. Upgrading 'e' -> 'é' is intended, but overwriting valid plain words (ou, a, du, des) shared by all learners, permanently, is a clear regression on top-frequency words. Fix at runtime: do not fold/upgrade onto a spelling that is itself a valid dictionary/Lexique word. Primary for the cache family.
- Final verdict: validated

## Fix
- `app/content/lookup.py`: an accented spelling that is a word beside an accent-free one (où/ou, dû/du) gets its own cache key (`lookup_slug`), and `cached_lookup` no longer serves another spelling for a word that is itself right (a row left as où under `ou` is re-looked-up). `stored_lookup` keeps the add-card audio reuse working. Test: `tests/test_personal_vocab.py`.
