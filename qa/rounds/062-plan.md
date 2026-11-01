# QA round 062 — plan

- date: 2026-10-31
- app under test: **real Piper + real Ollama (qwen2.5 7B)**, single-origin in disposable container
  `qa062-app` on the box (`rohith@10.0.0.54`), image `multilingual-app` (= main 492a447, deployed),
  bound to the box's `127.0.0.1:9302`, on network `multilingual_default` (Ollama at `http://ollama:11434`).
  Reach from the Mac at `http://127.0.0.1:9302` (ssh tunnel is up). Scratch data `~/qa062/data`.
  STT disabled. Invite codes `qa062-a`, `qa062-b`, `qa062-c`.
  Seed/inspect via `ssh rohith@10.0.0.54 docker exec -i qa062-app python -` on `/app/data/tef.db`.
  Never touch `multilingual-app-1`, its data or the box docker-compose.yml.
- scope: PR #131 (492a447), nine deferred issues fixed: 867 872 874 883 893 900 921 922 951.
- issue ids for this round start at 1000.

## Change surface (highest risk first)
1. 893 `app/content/enrich.py`: gloss prompt rewritten, never benched on the live 7B; `_pos` 3-letter
   mapping; LLM gender only for nouns. Touches every fresh lookup that all learners share via cache.
2. 872 `clamp_slug` in personal.py: changes lookup PK, clip storage key, audio URL, and `uv:` card keys
   for >64-char slugs; old rows/cards must still resolve.
3. 874/883: preview IPA for course words; My deck saved-card IPA.
4. 922 docteur mf + fem + new mp3; 921 IPA pins; 900 reworded A1 exercises (single correct answer?).
5. 951 icons + `check_unit_icons_exist`; 867 pill removal in WritingTask.

## Hypotheses (ranked)

| # | area | hypothesis | probe | tester |
|---|------|------------|-------|--------|
| H1 | lookup/LLM | The new gloss prompt regresses the headword `fr` (891), yields over-long or definition-style glosses, over-applies "(f. pl.)" to non-inflected words, or leaves pos empty on adverbs/prepositions/phrases. | fresh uncached words (issue 893 list + ~40 nouns, inflected adj, verbs, adverbs, preps, phrases, accent-less input) via preview | qa-tester A |
| H2 | lookup/LLM | Gender: noun-only gate leaves nouns with pos mis-mapped (e.g. "n.", "Noun (common)") genderless, or wrong gender on common nouns; non-nouns (à, adjectives) wrongly gendered. | same sample, check gender vs pos | qa-tester A |
| H3 | slug | clamp_slug: long phrases (>64 slug) collide or fail audio; boundary lengths (63/64/65/80 chars) off by one; accents/apostrophes in slug; old short words still hit cached rows; card add of long phrase, its audio, delete and re-add, personal_key `uv:` consistency. | API: preview/add/audio fetch/list/delete | qa-tester B |
| H4 | preview | Course-word preview returns ipa for every sampled course word incl. mf cards (docteur, professeur) and accent-less input; non-course words unaffected; audio_url present. | API preview over many course words | qa-tester B |
| H5 | content | A1 time-words-02.e5 / adverbs-02.e6 rewording leaves two correct answers or untaught structure; docteur/docteure card data, fem_ipa, both mp3s served; IPA pins (premier*, serrer, professeur) live; unit icons all exist in UNIT_ICONS, no duplicates. | read YAML, submit answers via lesson check, GET /content/vocab, fetch mp3 | qa-tester C |
| H6 | ui | My deck saved card shows /ipa/ without overflow (long phrases, none case); new icons render on A1/A2/B1 paths; docteur card shows both forms and plays audio; writing feedback renders cleanly without the pill. | Chrome | qa-browser-tester |

## Coverage gaps
- Real-LLM lookup quality after prompt change: none benched.
- Long-phrase end-to-end including audio and delete.
- Icon visual rendering of the 15 new glyphs.

## Charters / id blocks
- qa-tester A, edge-case-breaker (ids 1000-1019): H1, H2.
- qa-tester B, edge-case-breaker (ids 1020-1039): H3, H4.
- qa-tester C, returning-learner (ids 1040-1049): H5.
- qa-browser-tester, absolute-beginner (ids 1050-1059): H6.

## Don't re-file
- 884 pipes handled earlier; 755 lesson coherence; STT unavailable; 7B slowness/model-quality quirks that
  pre-date the change (only file glosses that are wrong or regressed vs the issue 893 expectations).
- Writing grader may mis-state a rule in free text (867 residual, disclosed).

<!-- Outcomes appended below after the round. -->

## Outcomes (post-round)
- H1 partly confirmed: headword accents mostly restored (891 not regressed), no pipes/long definitions/over-applied "(f. pl.)"; but 1000 (inflected adjectives tagged noun + gender), 1001 (noisy suffixes), 1002 (misplaced accents) are 7B model quality: deferred. 1003 (no conjunction/pronoun pos) fixed.
- H2 partly confirmed: 1004 noun without gender (deferred, raw reply not captured); 1050 phrase tagged (m) via suffix rule (fixed).
- H3 refuted: clamp_slug sound (distinct rows/audio, boundaries 63/64/65/80, 81+ gives 422, long cards save/play, isolation). Delete/re-add untestable (no delete endpoint). Legacy truncated rows not exercised.
- H4 partly confirmed: IPA present and matches bank everywhere; 1021 no audio_url on course preview, 1020 curly apostrophe, 1022 oe ligature (all fixed).
- H5 refuted (no issues): A1 rewordings, docteur card/audio, IPA pins, icons all sound; lesson answers were judged from served JSON (no check endpoint).
- H6 mostly refuted: My deck IPA, icons, writing without pill fine; 1051 docteur slow-button wrap (fixed).
- Filed 1000-1004, 1020-1022, 1050-1051 (10): 6 validated and done on branch qa/062-fixes (76c193d, unmerged); 4 deferred (1000, 1001, 1002, 1004); 0 rejected, 0 needs-info.
