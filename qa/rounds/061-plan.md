# QA round 061 — plan

- date: 2026-10-29
- app under test: **real Piper**, single-origin (backend + built SPA) in a disposable
  container `qa061-app` on the box (`rohith@10.0.0.54`), image `multilingual-app`
  (= `main` f5dd62a, what is deployed), bound to the box's loopback `127.0.0.1:9301`;
  reach from the Mac with `ssh -N -L 9301:127.0.0.1:9301 rohith@10.0.0.54` ->
  `http://127.0.0.1:9301`. Scratch data `~/qa061/data` (never the live
  `multilingual-app-1` data). STT disabled. Invite codes `qa061-a`, `qa061-b`, `qa061-c`.
  Seed rows via `ssh rohith@10.0.0.54 docker exec -i qa061-app python -` on `/app/data/tef.db`.
- scope: the vocabulary content shipped in PRs #124-#129 (checked IPA for every bank
  card; +214 cards 1,852 -> 2,066 with decks, IPA, `say` audio, lessons, path units,
  reading sets). All script-generated, never human-reviewed: this is the first pass.

## Change surface (highest risk first)
1. 214 new cards + ~25 lessons + ~20 path units + 9 reading sets (a1 people/time-words/
   adverbs; a2 verbs, verbs-2, everyday, adjectives, adverbs; b1 ideas, useful-nouns,
   verbs-2, connectors). Generated text: glosses, mcq/word_bank/translate exercises,
   explain/grammar_point strings, passages.
2. `scripts/build_vocab_ipa.py` -> `ipa`/`fem_ipa` on every card (Lexique phon -> IPA,
   cross-checked vs Piper, `REVIEWED` hand fixes); rendered by `Ipa` in `web/src/VocabWord.tsx`.
3. `content/<lvl>/audio/<id>.mp3` generated with macOS `say`.
4. New path units appended after previously-last units (a1.u22-24, a2.u24-35,
   b1.u26-31): unlock order and existing learners' progress.
5. New deck tags (people, time, adverbs, verbs, everyday, adjectives, ideas, expressions,
   connectors): tile names/counts/icons.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content | Polysemous headwords taught bare (point, fond, coup, tour, type, air, lieu, suite, voler, pièce) get one-sense glosses; exercises/translate accept lists reject the other valid sense or the other sense is a distractor. | read new vocab/lesson YAML; submit alternate-sense answers | edge-case-breaker (content) |
| H2 | content | Generated exercises have a second correct answer: mcq distractor also valid, `translate` `accept` missing legit variants (tu/vous, contractions, articles), word_bank tiles allow another valid order. | read lesson YAML; POST answers via lesson/check endpoints | edge-case-breaker (content) |
| H3 | content | `grammar_point`/explain statements state wrong French (reflexive agreement, auxiliary être/avoir, connector + mood, adverb placement). | read the explain text of the reflexives/verbs/connecteurs/adverbs lessons | edge-case-breaker (content) |
| H4 | reading | Reading-set questions whose answer key is unsupported by the explain quote, answer ambiguous, or passages with French errors / above-level vocab. | read the 9 comprehension sets; fetch via API | exam-crammer |
| H5 | ipa | IPA wrong where Lexique/Piper disagree or for homographs (fils, est, plus, tous), reflexive/elided/multiword headwords (s'asseoir, se taire, s'intéresser à, d'abord, peut-être), schwa/liaison, `fem_ipa` on mf cards. | sample all 214 new cards vs Lexique + standard French; list every REVIEWED entry | edge-case-breaker (ipa/audio) |
| H6 | audio | New mp3s: missing, empty, wrong word, wrong voice, reflexive/elided forms mis-said, IPA not matching clip. | check every new id has mp3 of sane size/duration; ffprobe; fetch via API | edge-case-breaker (ipa/audio) |
| H7 | flow | New units unlock out of order or are reachable/locked wrongly; a learner who completed the old last unit sees new ones correctly; lesson completion does not seed SRS for new_vocab; Review lacks IPA/audio for new cards. | API: sign up, progress via lesson submit, read path, review queue | returning-learner |
| H8 | regression | Deck counts/tags and pre-existing cards changed (duplicate ids across files, id collisions, tag collision with existing decks, vocab-known on old keys). | /vocab decks counts vs file counts; duplicate id scan; old card sample | returning-learner |
| H9 | ui | New deck tiles show raw tag keys/odd names, unit icons fall back to the book glyph, IPA overflows/wraps, reflexive/long headwords overflow cards on mobile width, console errors. | Chrome: Decks, Path, a new lesson, Review | absolute-beginner (browser) |

## Coverage gaps
- No QA round has ever covered a1 time/people/adverb decks or any b1 ideas/connectors.
- IPA field never reviewed by a human; only the unit test (tests/test_build_vocab_ipa.py).
- Audio from `say` never auditioned/validated against the headword.

## Charters (per tester, with id blocks)
- `qa-tester` content-lessons, edge-case-breaker (ids 894-909): H1, H2, H3.
- `qa-tester` reading, exam-crammer (ids 910-919): H4.
- `qa-tester` ipa+audio, edge-case-breaker (ids 920-939): H5, H6.
- `qa-tester` flow, returning-learner (ids 940-949): H7, H8.
- `qa-browser-tester` absolute-beginner (ids 950-959): H9, plus H7 as seen in the UI.

## Don't re-file (already settled)
- 893 lookup gloss quality, 874/883 course-word preview / saved-card IPA display: deferred earlier.
- 755 lesson-vocab coherence (widespread) and 721 chauffeur/conducteur gloss: existing; file only new instances in new content.
- STT unavailable, Ollama-dependent features slow: expected.
- Never write to live data; only `qa061-app` on :9301.

<!-- Outcomes appended below after the round. -->

## Outcomes (post-round)
- H1 confirmed (895 single-sense glosses; fixed). H2 partly confirmed (894, 896, 897, 898, 901; fixed). H3 mostly refuted (899 only; fixed; 900 level mismatch deferred into 755).
- H4 partly confirmed: 910 options never shuffled (fixed), 911/912 text and ambiguous-option fixes. Answer keys and explain quotes sound.
- H5 mostly refuted: 920 liaison artifacts (fixed); 921 cosmetic, 922 docteur has no feminine form: deferred. H6 refuted (all 214 clips present, byte-identical to regenerated `say` output, served correctly).
- H7, H8 refuted (no issues): unlock order, SRS seeding, counts, ids, icons all sound.
- H9 refuted for layout/tiles/icons; 950 (no correct answer/explain on wrong answer) and 952 (people-01.e7 untaught) confirmed and fixed; 951 icon repetition deferred.
- Filed 894-901, 910-912, 920-922, 950-952 (17): 13 validated and done, 4 deferred (900, 921, 922, 951), 0 rejected, 0 needs-info.
- Scratch container qa061-app and ~/qa061 removed.
