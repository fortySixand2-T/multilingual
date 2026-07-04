# QA round 031 — plan

- date: 2026-07-03
- app under test: backend + SPA at http://localhost:8080 (port 8080)
- scope: content/b2-mvp — B2 level MVP Slice 1 (3 units, 9 lessons, 54 vocab cards, 4
  comprehension sets, 2 writing tasks, 1 mock, 56 TTS clips). Also regression-tests
  that adding a 4th level left a1/a2/b1 intact.

## Change surface (highest risk first)

One commit since last round (030, clean):

1. **`530f083` — B2 vertical MVP**: entire `content/b2/` tree created from scratch.
   - `path.yaml`: 3 units (b2.u1 sciences, b2.u2 economie, b2.u3 societe), sequential
     unlock chain (u1 → u2 → u3).
   - 9 lesson YAMLs, each with 5 exercises (mcq/translate/listen_type/word_bank/match_pairs).
   - 3 vocab decks (sciences.yaml, economie.yaml, societe.yaml) — 18 cards each = 54 total.
   - 4 comprehension sets: `read-b2-ai-workplace`, `read-b2-globalization`,
     `listen-b2-tech-ethics-debate`, `listen-b2-media-interview`.
   - 2 writing tasks: `write-b2-open-letter` (Section A, 120–200 w),
     `write-b2-misinformation` (Section B, 250–350 w).
   - 1 mock blueprint: `b2-mock-1`.
   - 56 audio files under `content/b2/audio/`.

This is a pure content addition — no code changes. Risk is concentrated in:
- Data correctness (wrong grammar answer keys, arguable comprehension answers, broken
  audio refs).
- Level-surfacing correctness (b2 appearing in /content/levels, path unlock chain
  correct for a fresh user).
- Vocab id uniqueness (b2 ids must not collide with a1/a2/b1 primary keys).
- Global regression (existing levels unaffected by content expansion).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | grammar answer keys — subjonctif | sciences-b2-01/02/03 use subjonctif présent/passé; a fill-in-the-blank answer key may be wrong or the wrong conjugation accepted (e.g. se soit produite vs se soit produit; ait réussi agreement) | Read each exercise; verify answer and explain against the grammar rule; probe for agreement errors in pronominal constructions | exam-crammer |
| H2 | grammar answer keys — si-clauses | economie-b2-01 (si+imparfait→cond. présent) and economie-b2-02 (si+PQP→cond. passé) and economie-b2-03 (regret/reproach) — any wrong answer or misleading distractor | Read each exercise; check options set includes only grammatically plausible distractors | exam-crammer |
| H3 | grammar answer keys — discours rapporté / voix passive | societe-b2-01 (discours rapporté: passé composé→PQP) and societe-b2-02 (passive voice: a été + pp); societe-b2-03 (connecteurs + c'est…qui) | Verify concordance des temps in e1; check passive participle agreement in e4; check c'est…qui structure | exam-crammer |
| H4 | B2 level surfacing & path | /content/levels now includes "b2"; /content/path?level=b2 returns 3 units; fresh user sees b2.u1 available, b2.u2/u3 locked; POST progress on a locked b2 lesson returns 409 | GET /content/levels, GET /content/path?level=b2; verify status field per unit; attempt to progress locked lesson | edge-case-breaker |
| H5 | comprehension grading — reading | read-b2-ai-workplace and read-b2-globalization grade correctly (all-correct → 1.0; one-wrong → 0.8); explain fields present; answer keys defensible and not arguable | POST /comprehension/sets/{id}/submit with all-correct, then one-wrong; evaluate each answer's defensibility against passage | exam-crammer |
| H6 | comprehension grading — listening | listen-b2-tech-ethics-debate and listen-b2-media-interview grade correctly; allow_replay=false confirmed in payload; speaker attribution in debate correct; answer keys defensible | POST correct/wrong submissions; verify score; cross-reference debate Q&A against Camille/Thomas lines | exam-crammer |
| H7 | listening audio serving | The 2 listening comprehension mp3s (listen-b2-tech-ethics-debate.mp3, listen-b2-media-interview.mp3) serve HTTP 200, audio/mpeg, non-zero Content-Length | GET /comprehension/audio/{id} for both sets | edge-case-breaker |
| H8 | lesson listen_type audio refs | Each of the 9 lessons has a listen_type exercise with an audio_ref like b2/audio/X.mp3; if any audio file is missing the exercise breaks silently | GET /content/audio/{key} for each listen_type audio_ref across all 9 lessons (9 files to check) | edge-case-breaker |
| H9 | writing tasks — word-count bounds | write-b2-open-letter enforces 120–200 w (422 below 120, 422 above 200); write-b2-misinformation enforces 250–350 w (422 below 250, 422 above 350); target_vocab resolves | POST /assessment/writing/{id}/submit with under/over-length bodies; check 422 returned | edge-case-breaker |
| H10 | B2 mock — end-to-end | b2-mock-1 starts (POST /exam/start?blueprint=b2-mock-1), accepts reading/listening sections, accepts writing section, returns CLB report, appears in exam history | Full mock run; verify each section records; verify history entry | exam-crammer |
| H11 | vocab id uniqueness | B2 vocab ids (54 cards) must not collide with any a1/a2/b1 vocab id — collision corrupts SRS | Run `pytest tests/test_all_levels.py -q` | edge-case-breaker |
| H12 | regression — a1/a2/b1 unaffected | Adding b2 content did not break the existing three levels: /content/levels still lists all 4, path + comprehension grading + a b1 mock all work normally | GET /content/path?level=a1; grade one b1 comprehension set; start/finish a b1 mock | returning-learner |

## Coverage gaps

- B2 is brand new — every endpoint, exercise, and piece of content is untested.
- The b2-mock-1 blueprint is the first time the reading section uses `read-b2-ai-workplace`
  and the listening section uses `listen-b2-tech-ethics-debate` — mock section wiring
  is unverified.
- The `si + PQP → conditionnel passé` grammar path (economie-b2-02) has not appeared
  in any prior round; same for discours rapporté concordance (societe-b2-01).
- 54 new vocab ids — id uniqueness has not been tested yet on this branch.
- Two-speaker debate format (`listen-b2-tech-ethics-debate`) is novel at B2 level (B1
  had one; but B2 is a new level so it has no prior history here).

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 418–427): chase H1, H2, H3, H5, H6, H10
  - For sciences-b2-01/02/03: read every exercise; verify subjonctif présent/passé
    answer keys; flag any agreement error (especially se soit produite, ait réussi) (H1)
  - For economie-b2-01/02/03: verify si-clause conditional answers; verify cond. passé
    distractor set is not misleading (H2)
  - For societe-b2-01/02/03: verify discours rapporté concordance (passé composé→PQP);
    verify passive participle agreement; check c'est…qui sentence structure (H3)
  - POST /comprehension/sets/{id}/submit for both reading sets: all-correct → 1.0, one-wrong
    → 0.8; read each question's explain field; flag any arguable answer (H5)
  - GET /comprehension/sets/{id} for both listening sets; verify allow_replay=false in
    payload; POST correct then wrong submissions; verify scores; for listen-b2-tech-ethics-
    debate trace each Q back to Camille or Thomas in script (H6)
  - Run full b2-mock-1: POST /exam/start?blueprint=b2-mock-1; POST reading section
    (submit comprehension); POST listening section; POST writing section (minimal
    valid word-count); POST speaking section; call finish; verify CLB report; check
    exam history entry (H10)

- `edge-case-breaker` (ids 428–437): chase H4, H7, H8, H9, H11, H12
  - GET /content/levels (after auth); confirm "b2" present (H4)
  - GET /content/path?level=b2; verify b2.u1 status=available, b2.u2/u3 status=locked;
    attempt to POST lesson progress for a locked b2 lesson → expect 409 (H4)
  - GET /comprehension/audio/listen-b2-tech-ethics-debate and
    /comprehension/audio/listen-b2-media-interview; check 200, audio/mpeg, Content-Length > 0 (H7)
  - GET /content/audio/{key} for each of the 9 listen_type audio_refs across 9 B2 lessons:
    algorithme, surveillance, logiciel, engagement, militant, mobilisation, concurrence,
    investissement, exportation (H8)
  - POST /assessment/writing/write-b2-open-letter/submit with 5-word body → expect 422;
    with 201-word body → expect 422; with valid 150-word body → expect 200 or 503 (no
    provider). Repeat for write-b2-misinformation (250/350 bounds) (H9)
  - Run `/tmp/tef312/bin/python -m pytest tests/test_all_levels.py -q`; confirm passes
    including test_vocab_ids_globally_unique_across_levels (H11)
  - GET /content/path?level=a1 (check 200, units listed); POST one b1 comprehension
    grade (listen-b1-radio-news correct → 1.0); start then finish a b1 mock → check
    CLB report returns (H12)

- `returning-learner` is not selected — H12 regression is covered by edge-case-breaker.

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 030 / 403 exam section rerecord overwrites — rejected
- 071 / 404 comprehension no-replay not enforced server-side — deferred (allow_replay is
  client-enforced; flag is correctly set in payload)
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
- 405 mock-3 writing tasks duplicated — rejected
- 416 exam blueprints/{id} SPA catch-all — rejected
- 417 charter submit payload format — rejected
- Drill / Writing / Speaking 503 with no AI provider — expected (by-design)
- comprehension model has no "difficulty" field — intentional (extra=forbid)

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcome (round completed manually — qa-planner hit a session limit after testing + filing)

Testers exercised the B2 MVP end-to-end and filed 3 issues; triage/gate completed by hand.

| # | area | result |
|---|------|--------|
| H1–H3 | grammar answer keys (subjonctif / si-clauses / discours rapporté + passive) | REFUTED — keys verified correct; no grammar-key defect filed |
| H4 | B2 surfacing & gating | REFUTED — /content/levels lists b2; path shows u1 available, u2/u3 locked |
| H5 | reading grading | REFUTED — all-correct→1.0, one-wrong→0.8 (verified live on read-b2-globalization) |
| H6 | listening grading + allow_replay | REFUTED — grades correctly; both listening sets allow_replay=false |
| H7 | listening audio serving | REFUTED — both mp3s serve |
| H8 | lesson listen_type audio refs | REFUTED — 56 clips synced; refs resolve |
| H9 | writing word-count bounds | REFUTED — bounds enforced; target_vocab resolves |
| H10 | B2 mock end-to-end | see issue 418 (rejected — self-scored exam is completable) |
| H11 | vocab id uniqueness | REFUTED — test_all_levels passes (148 pytest) |
| H12 | regression a1/a2/b1 | REFUTED — all 4 levels list; b1 grading/mock unaffected |

## Issues filed and gate results

| id | title | verdict | rationale |
|----|-------|---------|-----------|
| 419 | word_bank elision split as bare `l` token | **fixed** | Real polish bug in 4 B2 word_banks; switched to the dominant single elided-tile convention (`l'utilisateur`, `l'inflation`, `l'expérimentation`, `c'est`/`l'entraide`), matching existing `l'actualité`/`l'argent` tiles |
| 418 | mock exam "stuck" when LLM unavailable | **rejected** | False positive — the exam is composition/self-scored; `clb_estimate` for writing/speaking is user-supplied (dropdown in the Exam UI), independent of the AI grader. Tester posted `null`; a real user selects a value. Not B2-specific |
| 428 | failed-lesson `first_time` always false | **deferred** | Real but pre-existing in `app/progress/api.py` (all levels), minor, out of scope for the B2 content MVP — track for a separate progress-API fix |

**Round verdict: B2 MVP sound.** 1 real content bug found and fixed (419); 1 false positive rejected (418); 1 pre-existing non-B2 nit deferred (428). 148 pytest, ruff clean.
