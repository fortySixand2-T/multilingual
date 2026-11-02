# QA round 064 — plan

- date: 2026-11-01
- app under test: disposable container `qa064-app` on the box (`rohith@10.0.0.54`), image `multilingual-app:latest`
  (= main abeed23, same content as live), bound to the box's `127.0.0.1:9304`; reach from the Mac at
  `http://127.0.0.1:9304` (ssh tunnel up, single-origin SPA + API). Scratch data `~/qa064/data` (own throwaway DB).
  TTS/STT disabled (comprehension plays pre-built mp3 only). Invite codes `qa064-a`, `qa064-b`, `qa064-c`.
  Never touch `multilingual-app-1`, its data or the box docker-compose.yml.
- scope: PRs #136/#137 — 7 new comprehension sets (b1: 2 reading, 2 listening; b2: 2 reading, 1 listening) written to
  push B1/B2 deck-word coverage to 100% (`MIN_COMPREHENSION_COVERAGE` b1/b2 = 100 in `scripts/check_content.py`).
- issue ids for this round start at 1102.

## Change surface (highest risk first)
1. Prose forced to contain headword-form multi-word verbs (se renseigner, tenir compte de, convaincre de, valoir
   mieux/la peine, se rendre compte de, témoigner de, apercevoir...). Likely unnatural/ungrammatical French.
2. Questions + options + `explain` for the 7 sets (answer position, distractor plausibility, length giveaways,
   explain quoting text literally, a second defensible answer — cf. past 910-912).
3. Listening scripts vs rendered mp3 (Amélie qc via macOS `say`): mispronunciations (Saint-Denis, Laval, numbers,
   acronyms), script/audio drift; audio length vs `time_limit_seconds` (34 s / 26 s / 33 s vs 120/120/150).
4. Level fit: B1 sets drifting to B2 register (subjunctive, passive, complex relatives) or B2 sets too easy.
5. Rendering/scoring in the SPA: Comprehension list/filter, reading passage layout (blank-line paragraphs, « »),
   audio player + replay, timer, submit, results + explain.
6. `check_content.py` gate: threshold 100 means any later deck-word edit that drops a word breaks the build;
   verify the gate really reports the exact missing words.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content-fr | B2 readings/listening contain forced, unnatural or ungrammatical sentences ("convaincre de son utilité ceux qui…", "il peut valoir mieux", "témoigner de la réussite", "veiller à apprendre aux jeunes") | read passages via API, judge each sentence as a native would | qa-tester B (exam-crammer) |
| H2 | content-fr | B1 sets contain awkward headword-form phrases ("Ça peut valoir la peine", "ne pas oublier de renouveler sa carte", odd "quand je voyage, une voisine a la gentillesse…") and level drift | same on b1 sets | qa-tester A (returning-learner) |
| H3 | questions | some question has a second defensible option, an answer unsupported by text, giveaway by length, or `explain` quote not literally in the text | fetch sets, check each q: answer in text, distractors wrong, `explain` quote substring | qa-tester A + B |
| H4 | answer-order | correct answer position is biased (910 recurrence) across the 7 sets | tally shuffled positions across repeated GETs | qa-tester B |
| H5 | audio | listening mp3 mispronounces names/numbers/words or differs from script; length mismatch with time_limit | afinfo durations, transcribe mp3 if a local ASR exists, compare with script; mp3 served with right type/range | qa-tester C (edge-case-breaker) |
| H6 | scoring | submit/score/results for new sets: pass threshold math, wrong ids, partial answers, resubmit, unauth; replay flag (`allow_replay`) exposed | curl submit variants | qa-tester C |
| H7 | ui | new sets render cleanly (list shows level/skill, title with accents/apostrophes, long options wrap, audio plays + replay, results show explain) | Chrome | qa-browser-tester (absolute-beginner) |
| H8 | gate | coverage gate: `check_content.py` passes at 100 and fails (naming words) if a word is removed | run script, dry removal in a temp copy | qa-tester C |

## Coverage gaps
- No prior review of the 6 b1/b2 sets' French by a native-level reader; the 100% coverage constraint is new.
- Audio correctness never checked automatically (only duration/presence).
- Coverage gate failure path untested.

## Charters / id blocks
- qa-tester A, returning-learner (ids 1102-1114): H2, H3 on the 4 b1 sets.
- qa-tester B, exam-crammer (ids 1115-1129): H1, H3, H4 on the 3 b2 sets (+ b1 position tally).
- qa-tester C, edge-case-breaker (ids 1130-1139): H5, H6, H8.
- qa-browser-tester, absolute-beginner (ids 1140-1149): H7.

## Don't re-file
- 910-912 class fixes on older sets; any older (pre-#136) comprehension set quality.
- 7B model-quality, STT/TTS unavailable (disabled in scratch container).
- Stylistic preference where French is correct and natural.

<!-- Outcomes appended below after the round. -->

## Outcomes (post-round)
- H1 partly confirmed: "il peut valoir mieux" (1115) fixed; "convaincre de son utilité" (1116), "veiller à apprendre" (1118), "accepte de prendre position" (1119) judged grammatical, rejected.
- H2 mostly refuted: B1 French acceptable (1102/1103/1105/1109/1110 rejected); 1106 (stacked modals) and 1107 (residents at table yet "réveiller") fixed, mp3 regenerated; 1108 overturned to rejected.
- H3 confirmed: 1104 (second defensible distractor), 1121 (prompts vs options), 1117 (non sequitur) fixed. Explain quotes all literal.
- H4 refuted for position (no bias) but found length giveaway: 1120 (+dup 1111) fixed in the 7 new sets; older corpus 70% longest-correct left as backlog.
- H5 refuted: audio matches script (Whisper), durations 26-34 s vs 120-150 s limits.
- H6 refuted: scoring/auth/validation sound. 1131 (Range) rejected, SPA plays blob URL.
- H7 confirmed: 1140/1141 passage hard-wrap + guillemet orphans fixed (render-time, new passageParagraphs.ts); 1143 replay inconsistency fixed; 1142 deferred.
- H8 confirmed: gate works but unnamed words (1130) fixed.
- Filed 25 (1102-1111, 1115-1123, 1130-1131, 1140-1143): 11 validated and done (1104 1106 1107 1115 1117 1120 1121 1130 1140 1141 1143), 12 rejected (1102 1103 1105 1108 1109 1110 1111 1116 1118 1119 1122 1131), 2 deferred (1123 1142), 0 needs-info. Final verify: check_content OK (b1/b2 100%), ruff clean, pytest 422 passed 1 skipped, web tsc/tests/build green.
