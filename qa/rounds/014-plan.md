# QA round 014 — plan

- date: 2026-06-22
- app under test: backend :9000 / SPA :5174
- scope: deepened A1 (3 lessons/unit) + full A2 level (10 units, 30 lessons) — multi-lesson gating, exercise integrity across 60 lessons, SRS seeding, audio for new listen_type, cross-level consistency

## Change surface (highest risk first)
Since round 013, four commits landed (two PRs merged to main):
1. `799f97c` content/a1-deepen — A1 goes from 1 lesson/unit to 3 (intro/practice/review); 30 lessons, 135 exercises, 108 vocab, 19 comprehension sets, 6 writing, 2 exams. New TTS audio clips.
2. `6965f5b` content/a2-deepen — Full A2 level added: 10 units, 30 lessons, 133 exercises, 100 vocab, 19 comprehension sets (9 reading + 10 listening with `script`), 6 writing, 2 exams. New TTS audio.
3. `compute_unit_status` now gates on ALL lessons in a unit (not just one).
4. `greetings-02` was NOT renamed — both `greetings-02.yaml` (u1 "Casual greetings") and `politeness-01.yaml` (u3 "Please and thank you") exist as separate lessons in the path.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | progress/gating | Multi-lesson unit gating is broken: completing 1 or 2 of 3 lessons in a unit may incorrectly mark the unit `complete` and unlock the next unit | Sign up, complete only 1 of 3 lessons in u1, check path status; complete 2 of 3, check again; complete all 3, verify next unit unlocks. Repeat for A2. | edge-case-breaker |
| H2 | content | Exercise integrity violations in the 60 new lessons: MCQ answer not in options, word_bank answer not a subset of tokens, listen_type missing audio_ref, match_pairs malformed | Fetch all 60 lessons via API, programmatically validate every exercise against its type invariants | edge-case-breaker |
| H3 | srs | Practice lessons (-02) seed new_vocab into SRS but review lessons (-03) should seed nothing; duplicate or 990-interval cards may appear | Complete -01 then -02, check /srs/queue for seeded vocab; complete -03, verify no new cards; check for duplicates | returning-learner |
| H4 | audio | New listen_type exercises in A1+A2 reference audio_ref keys that may not resolve (404 or wrong content-type from /content/audio/{key}) | Extract all audio_ref values from all lessons, hit /content/audio/{key} for each, verify 200 + audio/mpeg | edge-case-breaker |
| H5 | content | Dangling greetings-02 file: user said it was renamed to politeness-01, but BOTH files exist. If greetings-02.yaml in u1 still has old politeness content (not casual-greetings), the lesson content is wrong | Fetch greetings-02 via API, verify its exercises are about casual greetings (not politeness); fetch politeness-01, verify politeness content | edge-case-breaker |
| H6 | content | Vocab IDs not globally unique across a1+a2: duplicate IDs would cause SRS card collisions | Fetch all vocab for both levels, check for duplicate IDs | edge-case-breaker |
| H7 | exam | A2 exam blueprints (mock-1, mock-2) may reference nonexistent comprehension_set_id or writing_task_id — brand new, never tested | Start both A2 mocks, submit all sections, finish; verify CLB report generates | exam-crammer |
| H8 | exam | A1 mock exams still work end-to-end after the content deepening (regression) | Run A1 mock-1 full flow: start, 4 sections, finish | exam-crammer |
| H9 | progress/gating | Cross-level gating: completing all A1 units should not affect A2 unit status (A2.u1 should always be `available` regardless of A1 progress) | Check A2 path as fresh user — u1 should be available | returning-learner |
| H10 | comprehension | A2 listening sets expose `script` field (the TTS transcript that is the answer source) in the API response — was guarded for A1 in round 013, but A2 sets are new | Fetch all A2 listening comprehension sets, inspect for `script` key in response | edge-case-breaker |
| H11 | regression | Comprehension XP double-award (issue 100), exam concurrent sections (issue 170), board display_name cap (issue 130) — verify all still hold with the larger corpus | Double-submit a comprehension set, submit concurrent exam sections, check board name length | exam-crammer |

## Coverage gaps
- All 30 A2 lessons: zero prior testing (brand new level)
- Multi-lesson gating (3 lessons/unit): never tested (was 1 lesson/unit before)
- A2 exam blueprints: never tested
- A2 comprehension sets (19): never fetched/submitted in QA
- A2 audio clips (23): never tested
- SRS seeding from practice (-02) vs review (-03) lessons: untested distinction

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 240-249): Chase H1 (multi-lesson gating), H2 (exercise integrity across all 60 lessons), H4 (audio_ref resolution), H5 (greetings-02 vs politeness-01), H6 (vocab ID uniqueness), H10 (A2 script leak). Heavy programmatic validation — script through all lessons, all audio_refs, all vocab.

- `exam-crammer` (ids 250-259): Chase H7 (A2 exam flows), H8 (A1 exam regression), H11 (regression on XP double-award, concurrent sections, board). Run both A2 mocks end-to-end, one A1 mock, and hit the known regression spots.

- `returning-learner` (ids 260-269): Chase H3 (SRS seeding from -01/-02/-03 lessons), H9 (cross-level gating). Walk through several lessons as a returning user, verify SRS queue fills correctly from practice but not review lessons, check A2 path is independent.

## Don't re-file (already settled)
- 001 invalid email — deferred (product decision)
- 007 negative elapsed_seconds — rejected (no impact)
- 030 exam section re-record — rejected (by design)
- 050 lesson score is client-reported — deferred (low risk)
- 071 comprehension no-replay not enforced — rejected (client-only rule)
- 102 CLB estimate clamped — rejected (by design)
- 131 password no max length — rejected
- 180 comprehension feedback reveals answers — deferred (post-submit, by design)
- 181 locked lesson content readable — rejected (content is not secret)
- 221 comprehension pass threshold not shown — deferred
- Drill / Writing / Speaking 503 with no LLM provider — expected (no Ollama model loaded)
