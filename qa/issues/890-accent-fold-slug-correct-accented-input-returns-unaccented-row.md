---
id: 890
title: Correctly accented input (été, très, déjà, âme, éléphant, sûr, à) returns the accentless cached row
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: B=http://127.0.0.1:9300; T=<bearer from POST /auth/signup, invite qa060-b>. P(w) = curl -s $B/vocab/personal/preview -H "authorization: Bearer $T" -H 'content-type: application/json' -d '{"word":"w"}'
1. P(ete) -> fr "ete".
2. P(été), P(très) after P(tres), P(déjà) after P(deja), P(âme) after P(ame), P(éléphant) after P(elephant), P(sûr) after P(sur), P(à) after P(a).

## Expected
Typing the correct spelling returns the correct headword with accents, IPA and audio for that word; accent-distinct words (sûr/sur, où/ou, à/a, mûr/mur) never share one row.

## Actual
lookup slug folds accents, so the first spelling ever looked up wins for every learner. P(été) -> {"fr":"ete","en":"summer","ipa":"ˈiːt"}; très -> "tres" ipa "tʁ"; déjà -> "deja"; âme -> "ame"; éléphant -> "elephant"; sûr -> {"fr":"sur","en":"above|on top of"} (wrong word, "sure" lost); mûr -> "mur" (wall); à -> {"fr":"a","en":"an|a","gender":"m"}. Reverse order (accented first) gives the accented fr for pâtes/pêche/côte/où, so it is order-dependent and poisons all users. A user typing perfectly gets a misspelled word that Piper then reads.

## Notes
Same family as 871 (lookup_slug in app/content/lookup.py) but different cause: NFD accent fold, not ligature. Fix: on cache hit prefer/refresh to accented headword, or key by exact NFC form; at minimum never return a headword that differs from exact accented input.

## Triage
- Explanation: Confirmed by code. `lookup_slug` = `slugify(normalize_lemma(word))[:64]` NFD-folds accents, so été/ete, sûr/sur, à/a, où/ou share one `vocab_lookup` PK. `cached_lookup` returns the row whenever the slug matches and nothing compares the cached `fr` with what was typed, so first writer wins for every learner. Also `fresh_lookup` stores `fr=result.fr`, and `enrich()` sets `fr` to the *typed* lemma (the LLM is never asked for a headword), so whatever spelling arrived first is what gets stored and voiced. (Reporter's note that cacahuete->cacahuète/foret->forêt are "LLM-corrected" is wrong: they only look corrected because a learner typed the accented form first. Order-dependence is the whole mechanism.)
- Against spec: Pronunciation/word must make sense (user complaint). VocabLookup docstring intends "cacahuète"/"cacahuete" to share a row; that intent is fine ONLY when the shared row holds the accented headword. Accent-distinct homographs (sûr/sur, où/ou, à/a, mûr/mur) were never considered.
- Verdict: validated
- Rationale: Correct spelling in, misspelled + mis-voiced word out, poisoned for all users. Agreed minimum fix (shared with 891): KEEP the ASCII-slug shared row (do not re-key; slug is the PK, the lookup-audio URL, the storage key and the card-key convention, so re-keying is a wide change). Add a headword check on cache hit in `lookup.py`: if the typed input contains accents and NFC-casefold(typed) != NFC-casefold(row.fr), treat as a miss and re-enrich/re-voice, overwriting the row (merge) with the accented headword (clip + IPA regenerated together). If typed is accentless and the row's fr is its accented form, serve the row. Accentless homograph ambiguity (ou vs où typed bare) is unresolvable and accepted; last accented spelling wins and never serves a wrong-accent word to someone who typed accents. Known residual: personal card keys `uv:<slug>` also fold accents (sûr/sur share a card); out of scope, note only.


## Critic
- Challenge: Order-dependent poisoning only matters for accent-distinct homographs (sûr/sur, ou/où, a/à), most of which are course words that bypass the lookup via find_content_match; the VocabLookup docstring intentionally shares accent variants.
- Holds up? Holds for non-course words (été, éléphant, âme, déjà, pâtes) which are the exact failure mode: correct input returns a misspelled, mis-voiced headword for every learner. Guard against a re-enrich loop: the cache-hit check must be 'typed contains an accent AND the row's fr has strictly fewer accented letters than typed' (e.g. row fr 'ete', typed 'été'), NOT 'NFC(typed) != NFC(row.fr)': typed 'éleve' vs row 'élève' would otherwise miss and burn an LLM+Piper call on every lookup forever. Row is overwritten via the existing merge (same slug PK, no re-keying), clip + IPA regenerated together. Accept the stated residuals (bare ou/sur; uv: card-key fold).
- Final verdict: validated

## Fix
`cached_lookup` treats a row as a miss when the typed word has strictly more accented letters than the row's `fr` (ete -> été); the row is re-enriched and overwritten via the existing merge (same slug, clip and IPA reset and regenerated together). Fewer-or-equal accents never re-run, so no loop.
- Files: `app/content/lookup.py`
- Tests: `tests/test_personal_vocab.py::test_accented_input_replaces_an_accentless_cached_row_once`
