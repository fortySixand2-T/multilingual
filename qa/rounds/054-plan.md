# QA round 054 — plan

- date: 2026-09-07
- app under test: backend + SPA single-origin at `http://127.0.0.1:9101`
- scope: `feat/vocab-expansion` (810b992, PR #84) — content-only commit adding 640 new
  vocabulary words across 32 new themed decks (8 per level) plus 677 fr_CA TTS audio
  clips. No application code changed. Bank goes 813 → 1453 words, 51 → 83 decks.

## Change surface (highest risk first)
Single commit, no code diff — only data:
- `content/{a1,a2,b1,b2}/vocab/<theme>.yaml` × 32 (20 entries each): animals, school,
  house, verbs, adjectives, places, jobs, countries (a1); money, nature, studies,
  sports, celebrations, communication, people, emergencies (a2); health, technology,
  arts, relationships, rights, tourism, food, mobility (b1); justice, technologie,
  education, medias, entreprise, psychologie, migration, histoire (b2).
- `content/{a1,a2,b1,b2}/audio/*.mp3` × 677 (640 base clips + 37 `_f` feminine clips
  for `gender: mf` entries) — build artifacts of `scripts/gen_audio.py`.
- Decks surface automatically via `web/src/screens/Decks.tsx` (groups `/content/vocab`
  cards by `tags`); `web/src/screens/Deck.tsx` (per-deck flip view) and the SRS
  add-to-review path are pre-existing, untouched code exercising new data.
- Existing lessons' `new_vocab` were deliberately NOT touched — new words are
  browse/add-only, not lesson-seeded. That's an intentional scope boundary, not a bug.

**Preflight already done by the requester** (don't re-verify, build on it): full test
suite green, ruff clean, CI green on PR #84; no duplicate vocab ids or French headwords
bank-wide; 491/640 new noun genders cross-checked against `fr_gender.tsv` (9 flagged
mismatches were proper-noun table artifacts, not real errors); live smoke on :9000
showed 1453 cards / 83 decks, sampled new clips 200, `/srs/add` accepted a new word.

**Verified again in this planning pass** (also don't re-verify):
- All 32 new files are genuinely new (not edits to pre-existing per-deck files);
  exactly 640 entries, 37 of them `gender: mf`, and 640+37=677 matches the audio file
  count from `git show --stat` exactly — no accounting gap.
- Every `gender: mf` entry across the *new* files has both a base `<id>.mp3` and an
  `<id>_f.mp3` present on disk — full scan, not a sample. `app/content/api.py:248-249`
  confirms `_f` clip is only ever referenced when `gender == "mf"` (not for plain `m`
  epicene-marked nouns like `psychologue`/`notaire`/`témoin` — those get no feminine
  clip at all, by design, per H5 below).
- Multi-word French headwords (e.g. `date de péremption`, `chaîne d'approvisionnement`,
  `présomption d'innocence`, `la une`, `pièce de monnaie`) all have correctly
  slugified ids and matching audio filenames — no id/filename mismatch found by
  cross-referencing all ~120 multi-word headwords against `find content -name *.mp3`.
- No zero-byte or suspiciously truncated audio files — file sizes for all 677 new
  clips range ~2.5KB–14.3KB, consistent with short TTS utterances; no outliers.
- `/content/vocab` (authed) returns in ~26ms locally for the full 1453-card / 270KB
  payload — raw endpoint latency is a non-issue; any perceived slowness at scale is a
  frontend render/parse question, not a backend one — push testers toward the UI.
- Spot-read of `verbs.yaml` (pos: verb throughout), `people.yaml` (adjectives:
  mince/gros/chauve — correct pos, plausible glosses), `psychologie.yaml` (anxiété/f,
  dépression/f, épuisement professionnel/m — all correct) found nothing wrong, but
  this was ~3 files out of 32; content-accuracy is NOT exhaustively checked and is
  the main open risk.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content | Some fraction of the ~640 new gender tags are wrong (the requester's own cross-check flagged 9/491 as needing manual judgment, and 149 nouns were never cross-checked at all against `fr_gender.tsv`) — a wrong `le`/`la` taught as fact is the worst-case outcome of this whole round. | Sample aggressively across all 4 levels and all 32 decks (don't cluster on one level); for each sampled noun, independently verify gender (native-speaker knowledge / a reference). Flag any wrong `gender` value, and separately flag any `gender: mf` where the `fem` spelling itself looks wrong (e.g. an irregular feminine spelled as if regular). | edge-case-breaker |
| H2 | content | English glosses are ambiguous, wrong, or carry the wrong register/connotation for a beginner (e.g. `gros: "big, fat"` — is that gloss appropriate/clear?), or the French is metropolitan when Québec usage differs and the commit claims Québec register discipline (`efface` not `gomme`, `soccer` not `football`, dépanneur, infonuagique, francisation, Action de grâce, résidence permanente were the examples given) — spot-check a handful of *other* words in each level for the same discipline, since only ~7 examples were named out of 640. | Read through decks per level, esp. money/nature/studies (a2), technology/health (b1), technologie/entreprise (b2) for obviously metropolitan-only vocabulary or misleading glosses. | edge-case-breaker |
| H3 | content | CEFR level placement is off for some words — an A1 deck (animals/school/house/verbs/adjectives/places/jobs/countries) should stay concrete/high-frequency; a B2 deck (justice/technologie/education/medias/entreprise/psychologie/migration/histoire) should be abstract/academic. With 8 decks × 4 levels authored in one pass, some individual words are plausibly filed a level or two off from where a learner would expect them. | Read each level's decks with a learner's eye: does anything in a1 feel like it belongs in b1+ (or vice versa — anything in b2 that's actually everyday-easy)? | absolute-beginner (a1 lens), returning-learner (b1/b2 lens) |
| H4 | audio | TTS mangles multi-word or unusual headwords even though the clip *exists* and *plays* — existence/size was already verified for all 677 files, but not content correctness. Named risk words: `date de péremption`, `chaîne d'approvisionnement`, `présomption d'innocence`, `la une`, `pièce de monnaie`, plus any word with an apostrophe or elision (`s'il te plaît`, `d'approvisionnement`). | Browser: play a sample of these specific clips (and a broader sample of ~15-20 others) and listen for garbled/cut-off/wrong-word audio, not just "it plays". | absolute-beginner, returning-learner |
| H5 | content | Epicene nouns (`psychologue`, `notaire`, `actionnaire`, `apatride`, `autochtone`, `camarade`, `spécialiste`, `témoin`) are marked `gender: m` because the schema's `mf` requires a distinct feminine spelling — but these nouns are genuinely used with `la` for a female referent (`la psychologue`, `la témoin`) in real French. Marking them plain `m` may teach a learner to always say `le témoin`, which is misleading, not just an omission. | Judge whether the UI/card presentation for these (no `la` shown anywhere, no feminine clip) is acceptable or actively teaches a wrong default article. This is a judgment call, not a clear-cut bug — file as `low`/`medium` with clear reasoning either way, and let pm/critic weigh in. | edge-case-breaker |
| H6 | web/scale | The Decks screen (`web/src/screens/Decks.tsx`) now renders 19-24 deck tiles per level (up from ~11-13) across 4 levels — does the layout hold up (wrapping, spacing, tap targets on a phone-sized viewport), and does the "All words" deck (374 cards at a1) stay navigable (flip through without lag, no runaway memory/render)? | Browser at a phone-narrow viewport: open Vocabulary, scroll through all 4 levels' deck grids, open a couple of the new theme decks, open "All words" for a1 and flip through several cards quickly. | absolute-beginner |
| H7 | web/flow | New words are browse/add-only (not lesson-seeded) — does "add to review" from a new-deck card actually work end-to-end (card appears in the SRS review queue, flips correctly there, and known/reviewed state round-trips), same as it does for pre-existing cards? This is pre-existing code but newly exercised by 640 new rows it's never seen before — a plausible edge is a card whose id collides in an unexpected way with the review-key scheme, or a multi-word French headword breaking the review card's rendering. | Browser: from a new deck (e.g. b2/justice or a1/animals), add 2-3 new words to review, then go to Review and confirm they show up, flip, and can be marked. | returning-learner |
| H8 | data | Cross-level duplicate/collision check was already done bank-wide by the requester (no dup ids, no dup French headwords) — but not a check for **near-duplicate meanings** across levels/decks (e.g. does a2/money and the new a1/places or b1 decks accidentally teach two different French words for the same English concept, or the same French word under two different glosses in two decks?), which could confuse SRS review (same concept, different card, different accepted answer). | While reading through decks for H2/H3, note any English concept that appears to repeat with a different French word or a different gloss for what looks like the same French word. | edge-case-breaker |

## Coverage gaps
- No prior issue history at all touches `content/*/vocab/*.yaml` authoring quality —
  this is the first round exercising raw content correctness at this scale (past
  rounds focused on code paths: forms/examples, personal decks, SRS scheduling).
- Zero browser-driven coverage of the Decks screen at 83-deck scale — it's only ever
  been eyeballed at ~51 decks pre-commit.
- No round has previously assessed epicene-noun gender handling (H5) — new territory.

## Charters (per tester, with id blocks)
- `qa-tester` (curl, persona edge-case-breaker, ids **720–729**): chase H1 (gender
  accuracy — sample broadly across all 4 levels via `/content/vocab`, cross-reference
  a spread of ~30-40 nouns against your own French knowledge, weighting toward ones
  NOT already covered by the requester's `fr_gender.tsv` check if you can tell —
  otherwise just sample independently), H2 (register/gloss spot-check), H5 (epicene
  `gender: m` judgment call — read the actual card JSON for the 8 named epicene words
  and assess), H8 (near-duplicate concepts across decks/levels). Also do a light
  structural pass: confirm `/content/vocab?level=<lvl>&tag=<theme>` works for a few of
  the 32 new tags and returns exactly 20 cards each. App base `http://127.0.0.1:9101`;
  invite codes `friend-001`-`friend-004` available. This is content-accuracy work more
  than API-mechanics work — read the YAML/JSON payload carefully, not just status codes.
- `qa-browser-tester` (persona absolute-beginner, ids **730–739**): chase H3 (a1-lens
  level-appropriateness — do the new a1 decks feel genuinely beginner-concrete?), H4
  (audio correctness — play a sample including the named risk clips), H6 (Decks screen
  usability at 19-24 tiles/level, "All words" 374-card deck navigability, phone-narrow
  viewport). App `http://127.0.0.1:9101`, SPA pre-built and served single-origin — no
  separate dev server needed. Sign up fresh with `friend-001` if no session exists.
- `qa-browser-tester` (persona returning-learner, ids **740–749**): chase H3 (b1/b2-lens
  level-appropriateness — do the new b1/b2 decks feel appropriately abstract/advanced,
  not accidentally easy?), H4 (audio sample, focus on b1/b2 multi-word terms), H7 (new
  word → add to review → appears in Review queue → flips/marks correctly, end to end,
  for 2-3 words from different new decks). App `http://127.0.0.1:9101`. Sign up fresh
  with `friend-002` if no session exists.

## Don't re-file (already settled)
- Duplicate vocab ids / duplicate French headwords bank-wide — already checked clean
  by the requester across all 4 levels; don't re-run this check.
- Gender cross-check against `fr_gender.tsv` for the 491 nouns already covered, and
  the 9 flagged "mismatches" (proper nouns like *la France*) — already explained as
  table artifacts, not real errors; don't re-file these 9 specifically.
- Audio file existence/presence for any new word, including `_f` clips for `gender:
  mf` entries — verified 100% present in this planning pass (not a sample). Only file
  audio issues for *content* problems (mangled/wrong/garbled speech), not missing files.
- `/content/vocab` response latency — verified fast (~26ms) at full 1453-card scale;
  only file a perf issue if it's specifically about frontend render jank, not the API.
- Multi-word headword → audio filename slugification — verified correct for all
  ~120 multi-word entries in this planning pass; don't re-file id/filename mismatches
  unless you find a *specific* one this pass missed.
- Existing lessons not seeding the new words (`new_vocab` untouched) — this is
  explicitly called out as intentional scope in the commit; not a bug.
- Drill / Writing / Speaking 503 with no provider — expected, out of scope this round
  (this round has no LLM-backed surface in scope at all — pure content + browse/SRS).

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
