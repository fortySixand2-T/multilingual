# QA round 065 — plan

- date: 2026-11-12
- app under test: disposable container `qa065-app` on the box (`rohith@10.0.0.54`), image `multilingual-app:latest`
  (= main 84922d7, same content as live), bound to the box's `127.0.0.1:9305`; reach from the Mac at
  `http://127.0.0.1:9305` (ssh tunnel up, single-origin SPA + API). Scratch data `~/qa065/data` (own throwaway DB).
  Joined to the `multilingual_default` network so the model path works: `OLLAMA_BASE_URL=http://ollama:11434`
  (the live Ollama, qwen2.5:7b-instruct-q4_K_M; read-only use). TTS/STT disabled (so IPA/audio absent in scratch —
  not a bug). Invite codes `qa065-a`, `qa065-b`, `qa065-c`, `qa065-d`. Never touch `multilingual-app-1`, its data
  or the box docker-compose.yml. Daily vocab budget default 20000 (`VOCAB_DAILY_TOKEN_BUDGET`; the budget tester
  may recreate the scratch container, same name/port/data dir, with a tiny value).
- scope: PR #139 — My deck dictionary-backed lookup (`fr_gloss.tsv.gz`, `dictionary.py`, `enrich.py`,
  `personal_api._lookup`, `heal_gloss`). Endpoints: `POST /vocab/personal/preview`, `/vocab/personal`,
  `/vocab/personal/from-word`.
- issue ids for this round start at 1144 (highest existing: 1143).

## Change surface (highest risk first)
1. Gloss table built mechanically from Wiktionary: first-sense / sense-cap / filter heuristics can yield wrong,
   fragmentary or oddly cased glosses for common words.
2. pos choice: Lexique's "usual pos" vs the learner's intent; typed article forces noun.
3. Accent handling: accentless typing, ligatures, capitals, `ambiguous()` model call and respell.
4. Budget path: dictionary free over budget; model words refused; billing only when the model ran.
5. `heal_gloss` rewriting cached rows on preview; same-pos only; must not clobber user_vocab.
6. UI My deck preview/edit/add, long glosses.
7. Wiktionary CC BY-SA attribution requirement.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | gloss-quality | Common non-course A1-B2 words get a wrong first sense, definition fragment ("single-decked long-distance, bus"), odd parenthetical, capitalised definition, or lose the key meaning via the 2-sense cap (désolé, car, bien, rendre, falloir, quand même) | preview ~150 words across nouns/verbs/adjs/adverbs/function words/homographs/hyphen+apostrophe; judge as a native | qa-tester returning-learner |
| H2 | pos/gender | Lexique-usual pos is not what a learner means (personne, bien, été, pas, fin, mal, plus, tout, même); gender missing/wrong on nouns, shown on non-nouns; mf words; article override misbehaves ("le/la/un/une/l'/les X") | preview variants, compare pos/gender/en across with/without article | qa-tester exam-crammer |
| H3 | accents | Accentless typing (peche, ete, eleve, cote, ou/où, a/à, du/dû, sur/sûr), ligatures (boeuf/coeur/oeil/soeur), capitals/whitespace/unicode forms give wrong word, wrong spelling in `fr`, or model call for the wrong word; respell picks a different word | preview + compare `fr`; inspect usage | qa-tester edge-case-breaker |
| H4 | budget | Over budget: a dictionary word fails, a model-only word is not refused with over_budget, or usage is billed for dictionary words / unbilled for model calls | recreate scratch with tiny budget; check `/usage`-ish endpoints or DB `usage` rows | edge-case-breaker |
| H5 | healing | `heal_gloss` clobbers a different-pos cached row, runs when it should not, loses user edits in user_vocab, or breaks for rows with no dictionary entry | seed old model rows in scratch DB (docker exec sqlite), preview, then add edited card and re-preview | edge-case-breaker |
| H6 | ui | My deck preview shows dictionary meaning, editable before Add, long glosses wrap/overflow, errors (not found / over budget) show a clear message, no console errors | Chrome | qa-browser-tester absolute-beginner |
| H7 | licensing | Wiktionary CC BY-SA attribution absent in the UI/docs where Lexique's is credited | grep repo + look at UI (About/footer/My deck) | qa-browser-tester + code read |
| H8 | speaking | `/vocab/personal/from-word` yields same quality/pos as preview; course words still win via the course bank | curl from-word for course + non-course words | exam-crammer |
| H9 | input | Absurd inputs (multi-word, digits, 80 chars, empty, emoji, SQLi/HTML) don't 500 and don't call the model needlessly | curl | edge-case-breaker |

## Coverage gaps
- Gloss table quality has never been reviewed at scale; only unit tests with a few words.
- Over-budget path and heal_gloss only unit-tested.
- No attribution review for third-party data.

## Charters / id blocks
- qa-tester returning-learner, code `qa065-a` (ids 1144-1159): H1.
- qa-tester exam-crammer, code `qa065-b` (ids 1160-1174): H2, H8.
- qa-tester edge-case-breaker, code `qa065-c` (ids 1175-1189): H3, H4, H5, H9.
- qa-browser-tester absolute-beginner, code `qa065-d` (ids 1190-1199): H6, H7.

## Don't re-file
- Pre-#139 behaviour (model-only glosses) quality; 7B model quality on model-only words.
- TTS/STT/IPA absent in scratch container.
- Stylistic preference where the gloss is correct and understandable.
- Same root cause as another issue: file once, list examples inside.

<!-- Outcomes appended below after the round. -->

## Outcomes (post-round)
- H1 confirmed: ~330 non-course words sampled, ~70 bad (function words, missing main meaning, junk second senses). 1144/1146 fixed in build_gloss_table.py; 1145 (junk extra senses) and 1147 (cosmetic) deferred.
- H2 confirmed: ~230 lookups, ~40 bad. 1161 (pas), 1162 (bare adj homographs), 1163 (vase gender) fixed; 1160 (article ignored, lemma-keyed cache) and 1164 (plurals) deferred; 1165 rejected by critic (own-card only), 1166 rejected (designed).
- H3 confirmed (5 defects): 1175 (shared cache poisoned by accented homographs; 1177 dup) and 1176 (course match folds accents; 1148 dup) fixed; 1181 (alternatives hidden) deferred, by design.
- H4 mostly refuted (billing correct, dict words free over budget); 1180 (cached row refused over budget) deferred.
- H5 refuted (heal_gloss same-pos only, user cards keep edits); 1179 rejected as dup of 1146.
- H6 confirmed minor: 1191 (re-add says "Added") fixed; 1190 (long meaning raw error) deferred. H7 confirmed: 1192 (Wiktionary/Lexique attribution) fixed (UI credits, NOTICE, README).
- H8 mostly refuted (from-word shares cache; plurals -> 1164 deferred). H9: no 500s; 1178 (junk billed/cached) fixed.
- Filed 22 (1144-1148, 1160-1166, 1175-1181, 1190-1192): 10 validated and done (1144 1146 1161 1162 1163 1175 1176 1178 1191 1192), 4 rejected (1148 1165 1166 1177, plus 1179 = 5), 7 deferred (1145 1147 1160 1164 1180 1181 1190), 0 needs-info.
- Fix branch fix/qa-065 (8c06d96, 6394ecb, 5075a34): pytest 444 passed 1 skipped, ruff clean, check_content OK, web tests 79 + build green.
- Unreviewed follow-up: scripts/backfill_ipa.py poisoned-slug check may now flag accented-fr rows stored under a plain slug.
