# QA round 063 — plan

- date: 2026-10-31
- app under test: **real Piper + real Ollama (qwen2.5 7B)**, single-origin in disposable container
  `qa063-app` on the box (`rohith@10.0.0.54`), image `multilingual-app:latest` (= main 5ba3e35, deployed),
  bound to the box's `127.0.0.1:9303`; reach from the Mac at `http://127.0.0.1:9303` (ssh tunnel up).
  Scratch data `~/qa063/data` (own throwaway DB). STT disabled. Invite codes `qa063-a`, `qa063-b`, `qa063-c`.
  Never touch `multilingual-app-1`, its data or the box docker-compose.yml.
- scope: PR #133 (5ba3e35): Lexique `respell`/`pos`, `clean_gloss`, gender normalisation, headword-first pos/gender, a2.u17/b1.u24 icons.
- issue ids for this round start at 1060.

## Change surface (highest risk first)
1. `lexicon.respell` applied to the model's headword when the learner typed no accents. Planner's offline
   probe already shows suspicious outputs: du->dû, des->dès, cote->côté, peche->péché, salé->sale, maïs->mais,
   crû->cru, ete->été, general->général. `_headword` accepts any same-slug accent variant, so a wrong
   respell is stored as the headword (and shared via cache).
2. `lexicon.pos` flips a model "noun" to adjective/adverb/prep/conj by Lexique's dominant reading. Offline:
   jeune/malade/blanc/rouge/fou/ancien -> adjective (but they are also nouns: un jeune, un malade, le rouge,
   un fou, un ancien). public/général/moyen/vieux/voisin/français stay noun. Flip drops gender (resolve_gender runs on new pos).
3. `clean_gloss`: bracket stripping on legitimate glosses ("(to)", "(of)", "(in)"), regional regexes
   matching real content, trailing a/the/an stripping legit glosses ("vitamin A", "Plan A", "a la carte").
4. Gender normalisation: "masculine"/"f." fine; "mf"/"m/f"/"m.f." variants, "neutral".
5. Headword-first pos/gender: typed vs kept spelling when respell flips; table lookup on kept headword; cache slug unchanged.
6. Icons a2.u17 party, b1.u24 memo.

## Hypotheses (ranked)

| # | area | hypothesis | probe | tester |
|---|------|------------|-------|--------|
| H1 | respell | Accentless input of a very common unaccented word is re-accented to a rarer accented homograph (du->dû, des->dès, ou/a/la/sur/mur/pres...), corrupting `fr` shown and stored. | preview ~80 accentless common words (function words, homographs list), compare `fr` to expected | qa-tester A |
| H2 | respell | Accentless homographs where both are legit (peche, marche, cote, sale, cru, age, pate, tache) pick the wrong one for the sense the model glossed (fr/en mismatch: fr=péché, en=peach). | same, check fr vs en agree | qa-tester A |
| H3 | respell | Capitalised, apostrophe (curly/straight), hyphen, ligature (coeur/oeuf/soeur), multi-word phrases: tokenisation breaks, caps lost, slug changes, ligature not restored or cœur flipped to coeur. Typed-with-accents input unchanged. | preview + add, compare slug and fr | qa-tester B |
| H4 | pos | Common nouns also adjectives/adverbs get tagged wrongly and lose gender (jeune, malade, ancien, rouge, fou, vieux, bien, mal, pire, tout). Flip to adjective hides gender on nouns where noun reading is what learner meant. | preview words, check pos+gender | qa-tester A |
| H5 | gloss | clean_gloss mangles legitimate glosses: stripped "a"/"the" ending, regional-word matches, empty gloss after cleaning, double spaces, nested brackets, "(f. pl.)" on non-adjectives or on adjectives with only "(m)". | preview inflected adjectives, phrases ending with article, words glossed w/ brackets (e.g. à la carte, vitamine A) | qa-tester B |
| H6 | regression | Issues 1000-1004 stay fixed (éléphant m, grandes adjective, gloss format, à côté de, rez-de-chaussée), in-course preview unchanged, from-word add and saved card consistent with preview, cached repeat returns same row, slug unchanged. | repeat steps from qa/issues/1000-1004; add + list + repeat preview | qa-tester B |
| H7 | ui | Lookup result and My deck card render fr/en/pos/gender/IPA cleanly with changed text (long glosses, accents); a2.u17 party and b1.u24 memo icons render in Path, no duplicates/tofu. | Chrome | qa-browser-tester |

## Coverage gaps
- respell never exercised end-to-end with the live 7B; only unit tests with canned replies.
- pos override for words that are both noun and adjective.
- No tests on gloss cleaning of articles/brackets in valid glosses.

## Charters / id blocks
- qa-tester A, edge-case-breaker (ids 1060-1079): H1, H2, H4.
- qa-tester B, edge-case-breaker (ids 1080-1099): H3, H5, H6.
- qa-browser-tester, absolute-beginner (ids 1100-1109): H7.

## Don't re-file
- 7B model-quality glosses that predate #133 and are not about respell/pos/clean_gloss.
- 1000-1004, 1020-1022, 1050-1051 (fixed/deferred earlier, unless regressed).
- STT unavailable.

<!-- Outcomes appended below after the round. -->
