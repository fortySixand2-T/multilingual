# QA round 032 — plan

- date: 2026-07-03
- app under test: backend + SPA at http://localhost:8080 (port 8080)
- scope: content/b2-expansion-2 — B2 Slice 2 (units u4 environnement, u5 santé, u6 culture):
  3 vocab decks (54 new cards), 9 lessons, 3 comprehension sets, 2 writing tasks,
  b2-mock-2, 55 TTS clips. Regression on B2 MVP (u1–u3) and a1/a2/b1.

## Change surface (highest risk first)

One commit since round 031 (B2 MVP — clean):

1. **`af78be7` — B2 expansion Slice 2**: entire u4/u5/u6 content tree added.
   - `path.yaml`: extended from 3 → 6 units; u4 unlocks after u3, u5 after u4, u6 after u5.
   - 9 lesson YAMLs: environnement-b2-01/02/03, sante-b2-01/02/03, culture-b2-01/02/03.
   - 3 vocab decks: environnement.yaml (18 cards), sante.yaml (18 cards), culture.yaml (18 cards).
   - 3 comprehension sets: read-b2-climate-policy, read-b2-healthcare, listen-b2-culture-radio.
   - 2 writing tasks: write-b2-health-letter (Section A, 120–200 w), write-b2-ecology (Section B, 250–350 w).
   - 1 mock blueprint: b2-mock-2 (reading: read-b2-healthcare, listening: listen-b2-culture-radio).
   - ~55 audio files under content/b2/audio/.

Pure content addition — no code changes. Risk is concentrated in data correctness and
level surfacing.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | grammar — gérondif (u4) | environnement-b2-01/02/03: gérondif and participe présent answer keys may be subtly wrong. « Tout en + gérondif » (e03.e1) is a concessive pattern; « étant conscients » (e02.e4) is a participe présent absolute construction. Check each answer and distractor is the correct form. | Read all 9 exercises across the 3 lessons; verify each answer against the grammar rule; flag any arguable distractor | exam-crammer |
| H2 | grammar — pronoms relatifs composés (u5) | sante-b2-01/02/03: pronoms relatifs composés depend on the preposition of the verb (faire confiance à → auquel; avoir besoin de → dont; être affilié à → à laquelle; parler de → dont; « pour laquelle » in e03.e4). Any mismatch between the verb's required preposition and the relative pronoun chosen = grammar bug. | Read all 9 exercises; verify preposition→relative mapping for every mcq + word_bank prompt | exam-crammer |
| H3 | grammar — nominalisation / cause / conséquence (u6) | culture-b2-01/02/03: nominalisation keys (conservation not conserver), cause markers (grâce à vs à cause de vs en raison de — grâce à should be positive), and consequence (si bien que vs bien que — bien que takes subjonctif, si bien que indicative; distractors include bien que which is a near-miss). | Read all 9 exercises; verify answer and explain for each distractor | exam-crammer |
| H4 | comprehension grading — reading | read-b2-climate-policy and read-b2-healthcare: server-side grading; all-correct → 1.0; one-wrong → partial. Answer keys traceable to passage text. Inference/attitude keys (q4 climate-policy on infrastructure, q5 on position) are arguable — probe. | POST /comprehension/sets/{id}/submit all-correct and one-wrong; verify scores; evaluate each key against passage | exam-crammer |
| H5 | comprehension grading — listening | listen-b2-culture-radio: allow_replay=false in payload; audio serves; grading correct. q4 ("l'essentiel est de donner à chacun l'envie") is an inference key — probe for defensibility. | GET set (verify allow_replay); POST /comprehension/audio/{id}; POST correct/wrong submissions; verify scores | exam-crammer |
| H6 | unit gating — 6 units, fresh user | /content/path?level=b2 returns 6 units; u1 available, u2–u6 locked for a fresh user. Attempting to POST lesson progress on a locked u4 lesson (environnement-b2-01) returns 409. | GET /content/path?level=b2; verify unit statuses; POST lesson-progress on locked lesson | edge-case-breaker |
| H7 | writing tasks — word-count bounds | write-b2-health-letter (120–200 w) and write-b2-ecology (250–350 w) present in /assessment/tasks?level=b2; 422 under/over; target_vocab resolves. | POST under/over/valid payloads for each task; verify status codes | edge-case-breaker |
| H8 | b2-mock-2 — end-to-end | b2-mock-2 starts (POST /exam/start?blueprint=b2-mock-2), accepts reading (read-b2-healthcare), listening (listen-b2-culture-radio), writing (two tasks), speaking; returns CLB report; appears in exam history. | Full mock run end-to-end; verify CLB report returned; check history entry | exam-crammer |
| H9 | listen audio — new comprehension + lesson clips | listen-b2-culture-radio.mp3 serves HTTP 200 audio/mpeg. 9 lesson listen_type audio_refs for u4/u5/u6 all resolve (renouvelable, pesticide, inondation for u4; vaccin, contagion, handicap for u5; artiste, tradition, festival for u6). | GET /comprehension/audio/listen-b2-culture-radio; GET /content/audio/{key} for all 9 new vocab audio refs | edge-case-breaker |
| H10 | vocab id uniqueness — 54 new ids | The 54 new vocab ids across environnement/sante/culture decks must not collide with any a1/a2/b1/b2-MVP id. Several ids use common French words (conservation, diffusion, heritage) that could easily exist in earlier decks. | Run pytest tests/test_all_levels.py -q | edge-case-breaker |
| H11 | regression — B2 MVP units u1–u3 + other levels | Adding u4/u5/u6 did not break the B2 MVP: /content/path?level=b2 still lists all 6 units with u1 intact; a B2 lesson from u1 still loads; /content/levels lists all 4 levels; a b1 comprehension grade still works. | GET /content/path?level=b2 (6 units, u1 details); GET /content/levels; grade one b1 comprehension set | edge-case-breaker |

## Coverage gaps

- The new reading comprehension set `read-b2-climate-policy` and `read-b2-healthcare` are
  the first climate-policy and healthcare reading passages at B2 — never tested before.
- `listen-b2-culture-radio` is the first solo (non-debate) B2 listening set added in Slice 2.
- The extended unlock chain u4→u5→u6 (three new links) has not been exercised; u4 gating
  against a fresh user is the new risk (u2 and u3 gating were verified in round 031).
- `write-b2-ecology` (Section B, 250–350 w) is the first ecology writing task — target_vocab
  pointing at environnement deck ids (rechauffement_climatique, empreinte_carbone,
  transition_energetique, durabilite) — verify all four ids exist in the right deck.
- 54 new vocab ids — some (conservation, diffusion, heritage) are semantically generic
  and could plausibly collide with earlier decks.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 429–438): chase H1, H2, H3, H4, H5, H8
  - Read all 9 environnement lessons; verify gérondif / participe présent keys; check that
    « tout en + gérondif » is the correct pattern for the concessive reading (H1)
  - Read all 9 santé lessons; trace each relative pronoun back to the verb's required
    preposition; confirm auquel (faire confiance à), dont (avoir besoin de / parler de),
    à laquelle (être affilié à), pour laquelle (pour laquelle); flag any mapping error (H2)
  - Read all 9 culture lessons; verify nominalisation key; verify grâce à is positive cause;
    verify si bien que is followed by indicative; check distractors (bien que → subjonctif
    is the near-miss; it should be the wrong answer in culture-b2-03.e1) (H3)
  - POST /comprehension/sets/read-b2-climate-policy/submit all-correct → expect 1.0;
    one-wrong → expect ~0.8; read each explain and flag arguable q5 position-of-author key (H4)
  - POST /comprehension/sets/read-b2-healthcare/submit all-correct → 1.0; one-wrong → ~0.8 (H4)
  - GET /comprehension/sets/listen-b2-culture-radio; verify allow_replay=false;
    POST correct → 1.0; POST one-wrong → ~0.75; evaluate q4 inference key (H5)
  - Run full b2-mock-2: POST /exam/start?blueprint=b2-mock-2; submit reading section;
    submit listening section; submit writing section (minimal valid word-counts for both
    tasks); submit speaking section; call finish; verify CLB report; check /exam/history (H8)

- `edge-case-breaker` (ids 439–448): chase H6, H7, H9, H10, H11
  - Sign up a fresh user; GET /content/path?level=b2; verify 6 units returned; verify
    b2.u1 status=available and b2.u4 status=locked; POST lesson progress for
    environnement-b2-01 → expect 409 (H6)
  - GET /assessment/tasks?level=b2; confirm write-b2-health-letter and write-b2-ecology
    present; POST write-b2-health-letter with 5-word body → 422; with 201-word body → 422;
    with valid 150-word body → 200 or 503; POST write-b2-ecology with 200-word body → 422;
    with 351-word body → 422; with valid 300-word body → 200 or 503 (H7)
  - GET /comprehension/audio/listen-b2-culture-radio; verify 200 + audio/mpeg + Content-Length > 0 (H9)
  - GET /content/audio/b2/audio/renouvelable.mp3; /b2/audio/pesticide.mp3; /b2/audio/inondation.mp3;
    /b2/audio/vaccin.mp3; /b2/audio/contagion.mp3; /b2/audio/handicap.mp3;
    /b2/audio/artiste.mp3; /b2/audio/tradition.mp3; /b2/audio/festival.mp3 — all expect 200 (H9)
  - Run /tmp/tef312/bin/python -m pytest tests/test_all_levels.py -q; confirm passes including
    test_vocab_ids_globally_unique_across_levels (H10)
  - GET /content/levels; confirm "b2" listed; GET /content/path?level=b2 (6 units, check u1
    lessons intact); POST /comprehension/sets/listen-b1-radio-news/submit all-correct → 1.0 (H11)

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 030 / 403 exam section rerecord overwrites — rejected
- 071 / 404 comprehension no-replay not enforced server-side — deferred (allow_replay is client-enforced)
- 131 password no max length — deferred
- 102 exam CLB estimate clamped — rejected
- 181 locked lesson content readable — deferred
- 180 comprehension feedback reveals answers — deferred
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — deferred
- 290 SRS queue negative limit — deferred
- 300 vocab known accepts string bool — rejected
- 320 e2e reuse server — deferred
- 330 vocab deck stale comment — rejected
- 370 / 371 writing tasks — rejected
- 394 level-filtered endpoints accept empty string — deferred
- 400 SRS queue vocab missing level field — done
- 401 match pairs en truncated — rejected
- 402 word bank missing card — rejected
- 403 exam section overwrite allows score gaming — rejected
- 405 mock-3 writing tasks duplicated — rejected
- 416 exam blueprints/{id} SPA catch-all — rejected
- 417 charter submit payload format — rejected
- 418 mock exam stuck when LLM unavailable — rejected (self-scored by design; don't re-file)
- 419 word_bank elision split as bare l token — done (fixed)
- 428 lesson fail first_time always false — deferred (pre-existing, all levels)
- Drill / Writing / Speaking 503 with no AI provider — expected (by-design)
- comprehension model has no "difficulty" field — intentional (extra=forbid)
- word_bank elisions as single tiles (l'œuvre, c'est) — correct, not a bug (fix from 419)

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcome (round 032 — complete)

| # | area | result |
|---|------|--------|
| H1 | gérondif / participe présent (u4 environnement) | REFUTED — all 9 exercises verified; keys correct; word_bank token lists complete; "tout en reconnaissant" concessive correct |
| H2 | pronoms relatifs composés (u5 santé) | REFUTED — all preposition→relative mappings correct: faire confiance à→auquel, avoir besoin de→dont, parler de→dont/ce dont, être affilié à→à laquelle, travailler pour→pour laquelle |
| H3 | nominalisation / cause / conséquence (u6 culture) | CONFIRMED (→ issue 429) — culture-b2-02.e1 distractors "À cause" / "En raison" ungrammatical with fixed "au" stem; fixed |
| H4 | reading comprehension grading | REFUTED — read-b2-climate-policy and read-b2-healthcare grade correctly; all-correct→1.0, one-wrong→0.8; all keys traceable; q5 position-of-author not arguable |
| H5 | listening comprehension grading | REFUTED — listen-b2-culture-radio: allow_replay=false confirmed; audio 200/439 KB; all-correct→1.0, one-wrong→0.75; q4 inference key defensible |
| H6 | unit gating — 6 units, fresh user | REFUTED — 6 units returned; u1 available, u2–u6 locked; POST to locked environnement-b2-01 → 409 with clear message |
| H7 | writing tasks — word-count bounds | REFUTED — both tasks present in /assessment/tasks?level=b2; under-min → 422, over-max → 422, valid → 503 (no AI, expected); target_vocab ids all resolve |
| H8 | b2-mock-2 — end-to-end | REFUTED — mock starts, all 4 sections accepted, CLB report returned, history entry appears |
| H9 | audio serving — comprehension + 9 lesson clips | REFUTED — listen-b2-culture-radio.mp3 serves 200/audio-mpeg/439 KB; all 9 lesson listen_type refs (renouvelable, pesticide, inondation, vaccin, contagion, handicap, artiste, tradition, festival) serve 200 |
| H10 | vocab id uniqueness — 54 new ids | REFUTED — pytest test_vocab_ids_globally_unique_across_levels passes; 9/9 tests pass |
| H11 | regression — B2 MVP + other levels | REFUTED — all 4 levels listed; b2.u1 intact; a1 path (10 units) intact; listen-b1-radio-news grading → 1.0 |

## Issues filed and gate results

| id | title | verdict | rationale |
|----|-------|---------|-----------|
| 429 | culture-b2-02.e1 MCQ distractors ungrammatical with fixed "au" stem | **done** | Real content bug: "À cause" / "En raison" require "de" not "à", making "À cause au" / "En raison au" ungrammatical; learner could eliminate distractors on surface grammar alone without testing the semantic cause concept. Fixed: options changed to ["Grâce", "Suite", "Contrairement"]. |

## Post-round checks
- pytest: 9/9 passed
- ruff: all checks passed

**Round verdict: B2 Slice 2 is sound.** 1 content bug found and fixed (issue 429 — ungrammatical MCQ distractors); all grammar keys verified correct across 9 new lessons; all comprehension sets grade correctly; unit gating, audio serving, writing bounds, vocab uniqueness, and regression all clean.
