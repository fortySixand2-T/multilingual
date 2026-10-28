# QA round 060 — plan

- date: 2026-10-27
- app under test: **real Piper**, single-origin (backend + built SPA) in a disposable
  container `qa060-app` on the box (`rohith@10.0.0.54`), image `multilingual-app`
  (= `origin/main` 604ad6d, exactly what is deployed), bound to the box's loopback
  `127.0.0.1:9300`; reach it from the Mac with `ssh -N -L 9300:127.0.0.1:9300 rohith@10.0.0.54`
  -> `http://127.0.0.1:9300`. Scratch DB/storage in `~/qa060/data` (never the live
  `multilingual-app-1` data). `TTS_BACKEND=piper`, `PIPER_VOICE=fr_FR-upmc-medium`
  (word voice = siwis-medium, as live), Ollama on the box (`qwen2.5:7b-instruct-q4_K_M`),
  invite codes `qa060-a`, `qa060-b`, `qa060-c`. Seed stale rows by running python/sqlite3
  inside the container: `ssh rohith@10.0.0.54 docker exec -i qa060-app python -` against
  `/app/data/tef.db`.
- scope: "the word pronunciation isn't fixed" after PR #121 (QA 832: IPA from Piper only)
  and PR #122 (QA 868: a voicing overwrites stale IPA). Rounds 058/059 ran with TTS
  disabled, so the real Piper pronunciation path has never been QA'd live.

## Change surface (highest risk first)
1. `app/content/personal_api.py::_serve_audio` — overwrites `row.ipa` only on the
   *synthesis* branch. The early `if row.audio_key:` return serves the cached clip and
   never touches IPA, so any row with a clip AND a stale IPA is stuck forever.
2. `app/content/lookup.py::fresh_lookup` / `cached_lookup` — `vocab_lookup` rows written
   before #121 hold LLM IPA + a cached clip; `/preview` returns them verbatim. The preview
   panel (`web/src/screens/MyDeck.tsx` `/{preview.ipa}/`) is the *only* place a learner
   sees IPA, and it reads straight from this cache.
3. `POST /vocab/personal` (`add`) — trusts client `ipa`, copies only `audio_key` from the
   lookup row, so the card's IPA can differ from the lookup's Piper IPA.
4. `app/ai/adapters/piper_adapter.py::synthesize_ipa` — IPA parsed from `piper --debug`
   stderr; stress marks, `-` stripping, multi-line join, 64-char truncation.
5. Live data: `user_vocab` paquet=`pakɛt`, cacahuetes=`pəˈnuːz` (pre-fix, never voiced).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | vocab/lookup | Rows with a cached clip but stale IPA (pre-#121 `vocab_lookup`, and `user_vocab` whose clip was copied from a lookup) are never corrected: `_serve_audio` returns the clip before the IPA line; `/preview` + `/vocab/personal` keep serving the LLM IPA. Nothing backfills. | seed stale rows with audio_key set + a real clip (do a real lookup, then UPDATE ipa to `hɒrəbəl`); `POST /vocab/personal/preview`, `GET /vocab/personal`, GET the audio, re-read | edge-case-breaker + returning-learner |
| H2 | vocab/add | `POST /vocab/personal` keeps client-sent `ipa` (any string, up to 64) even when a Piper-derived lookup row exists for the word; copies only `audio_key`. | preview a word (Piper IPA), then POST add with `ipa:"WRONG"`; GET deck | edge-case-breaker |
| H3 | vocab/other | Other IPA surfaces not Piper-derived: `/preview` for course words returns `ipa:""`; `from-word` copies `result.ipa` (may be stale/empty); review queue / `/vocab/extra` payloads carry `ipa`; lookup rows created while TTS errored have `ipa=""` forever until played. | call each path, compare to a direct Piper IPA | edge-case-breaker |
| H4 | display | eSpeak puts `ˈ` on the last syllable (`velˈo`, `pakˈɛ`) — French has no lexical stress, so a learner sees misleading stress marks. | list of 30 words via preview, inspect `ˈ`/`ˌ` | absolute-beginner (browser) |
| H5 | audio/IPA | Piper IPA/audio is wrong for realistic inputs: elision (`l'avion`), multiword (`pomme de terre`), hyphen (`peut-être`), capitals, accents (`cacahuète`/`cacahuete`), long phrases (IPA cut at 64 chars mid-symbol), known eSpeak misses (`fils`, `oignon`). Audio uses siwis while IPA is phonemized from the same text — check they agree. | preview ~40 words; fetch audio; compare IPA to expected French phonology (listen not possible: check IPA + WAV size/valid) | edge-case-breaker |
| H6 | UI | Browser: preview panel shows IPA only if present at preview time; a row that got IPA on first play (ipa was `""`) doesn't refresh the panel; stale IPA stays shown after play; saved cards show no IPA anywhere (IPA lives only in the add-preview). | Chrome: look up fresh word, stale-seeded word, empty-ipa word; press 🔊; re-open | absolute-beginner (browser) |
| H7 | vocab/word | The *word* side makes no sense too: input typed without its accent ("cacahuetes", "cacahuete") is stored/voiced exactly as typed (no headword normalisation), and the LLM gloss can be odd (`packet\|package`). | preview accentless/plural/inflected inputs (cacahuetes, ecole, eleve, etudiant, mangeons, chevaux), read `fr` returned | edge-case-breaker (extra, ids 890-899) |
| H8 | pronunciation quality | Piper/eSpeak disagree with a human reference for a handful of common words (cacahuète->kakayɛt vs kakawɛt, fils->fil vs fis, oignon->onjɔ̃ vs ɔɲɔ̃). Measure agreement against a fixed Wiktionary-style table (no network in tests) and add a small curated override. | fixer: table test + override | (fixer) |

## Coverage gaps
- Real Piper path never tested end-to-end in QA (058/059 disabled TTS).
- No backfill/migration for IPA on existing rows (test-gap, fix = script).
- `synthesize_ipa` parsing has unit tests only against a fake stderr.

## Charters (per tester, with id blocks)
- `qa-tester` as **edge-case-breaker** (ids 869–879): H1, H2, H3, H5 via curl against `http://127.0.0.1:9300`.
- `qa-browser-tester` as **absolute-beginner** (ids 880–889): H4, H6, plus H1 as seen in the UI.

## Don't re-file (already settled)
- 868 overwrite-on-voicing — fixed (synthesis branch only; the cached-clip branch is H1 here, file as new).
- 832 LLM IPA removal — fixed.
- STT unavailable (`STT_BACKEND=disabled` in the scratch container) — expected.
- Piper pronounces what eSpeak produces; wrong IPA that *equals* Piper's output for a hard word (`fils`) is a H5 data point, file once, not per word.

<!-- After the round: hypothesis outcomes appended below. -->

## Outcomes (post-round)
- H1 confirmed (869; 880/881 duplicates -> acceptance tests) — fixed: heal on play, empty-IPA heal on preview, backfill script.
- H2 confirmed (870) — fixed: client ipa ignored, taken from lookup row.
- H3 confirmed (874 course-word preview has no IPA/audio: deferred to the Lexique slice; 883 saved cards show no IPA: deferred).
- H4 confirmed (882) — fixed: stress marks stripped.
- H5 partly confirmed: 871 (œ slug), 873 (64-char cut), 875 (eSpeak misses) fixed; 872 deferred.
- H6 confirmed (880/881/883) — covered by 869 fix.
- H7 confirmed (890, 891; 892 dup) — fixed: LLM headword validated by slug; accent-poor cache rows re-enriched; 893 gloss quality deferred.
- H8 measured: 22/35 exact vs Wiktionary after stress strip (coordinator); fixture test 27/30 raw -> 30/30 with overrides.
