# QA round 030 — plan

- date: 2026-07-03
- app under test: backend + SPA at http://localhost:8080 (port 8080 this round)
- scope: content/b1-comprehension-challenge — 7 new harder B1 comprehension sets (4 reading + 3 listening)

## Change surface (highest risk first)

Two commits since last round (029, clean):

1. **`f6569f3` — TTS clips for 3 B1 challenge listening sets**: `listen-b1-consumer-podcast.mp3`,
   `listen-b1-remote-work-debate.mp3`, `listen-b1-newcomer-interview.mp3` added to
   `content/b1/audio/`. Audio serving depends on the storage interface resolving these paths.
2. **`e39939d` — harder B1 comprehension tier (challenge sets)**: 7 YAML files added to
   `content/b1/comprehension/`:
   - Reading: `read-b1-gig-economy`, `read-b1-screens-and-youth`, `read-b1-city-or-country`,
     `read-b1-why-volunteer` — 5 questions each, inference/attitude/implication-based
   - Listening: `listen-b1-consumer-podcast`, `listen-b1-remote-work-debate`,
     `listen-b1-newcomer-interview` — 4 questions each, `allow_replay: false` (exam mode)

Previously: 22 B1 comprehension sets. Now: 29 confirmed via API.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | reading answer-key defensibility | The 4 reading sets use inference/attitude questions with closer distractors — one or more answers may be arguable (correct option not clearly the best, or a distractor equally defensible) producing a misleading grade | Read each passage; for each question evaluate whether the marked answer is the only defensible one vs. whether a distractor is equally or more defensible | exam-crammer |
| H2 | new reading sets — grading API | The 4 new reading sets grade correctly: correct answer → score 1.0; wrong answer → partial/0.0; explain field present | POST /comprehension/sets/{id}/submit with correct answers, then wrong; check score + explain | exam-crammer |
| H3 | new listening audio serving | The 3 new .mp3 files (committed in f6569f3) are served at /comprehension/audio/{set_id} with HTTP 200 + audio/mpeg + non-zero bytes | GET /comprehension/audio/{id} for all 3 new sets | edge-case-breaker |
| H4 | allow_replay=false serving | The 3 new listening sets expose `allow_replay: false` in the set payload; the prior 11 listening sets still have `allow_replay: true` (no unintended flip) | GET /comprehension/sets/{id} for all 3 new + spot-check of existing listening sets | exam-crammer |
| H5 | remote-work-debate answer keys vs. script | The two-speaker debate (listen-b1-remote-work-debate) has 4 questions attributed to specific speakers; verify each answer key matches who actually said what in the YAML script | Cross-reference each question's answer and explain against the raw script; probe for speaker attribution errors | exam-crammer |
| H6 | new listening sets — grading API | The 3 new listening sets grade correctly: correct → 1.0; wrong → partial; explain present | POST /comprehension/sets/{id}/submit for all 3 with correct then wrong answers | exam-crammer |
| H7 | regression — existing 22 comprehension sets | Adding 7 new sets did not break grading or listing for the prior 22 sets; /comprehension/sets?level=b1 still returns all 29 | GET sets list; spot-submit on 2-3 pre-existing sets (different skill/theme) | edge-case-breaker |
| H8 | audio storage regression — existing listen sets | The 11 pre-existing B1 listening sets still serve audio after the new mp3s were committed | GET /comprehension/audio for 2-3 pre-existing sets | edge-case-breaker |
| H9 | newcomer-interview answer key plausibility | listen-b1-newcomer-interview is an interview format (single speaker: Amina); all 4 questions should be answerable from the transcript without ambiguity | Read script + question set; verify each answer is unambiguously supported and no distractor is equally plausible | exam-crammer |
| H10 | consumer-podcast inference question | listen-b1-consumer-podcast q3 asks "why is this not just about money" — an implication question; verify the answer is the only defensible reading and the explain cites the exact passage | Review script + Q3 + explain field; test wrong answer grading returns < 1.0 | edge-case-breaker |

## Coverage gaps

- None of the 7 new sets have ever been graded via the API (first round on this branch).
- `allow_replay: false` has never been tested in an actual backend payload for B1 (prior
  B1 listening sets were all `allow_replay: true`; issue 404 deferred because no B1 set
  had it). These sets are the first to exercise this path at B1.
- The two-speaker debate format (`listen-b1-remote-work-debate`) is novel — all prior
  listening sets use a single narrator. Speaker-attribution questions have no prior
  issue history.
- Inference/attitude questions (q1 and q5 of each reading set) have more subjective
  "correct" answers than literal-lookup sets — this class of question has never been
  QA'd for defensibility.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 417–424): chase H1, H2, H4, H5, H6, H9
  - For all 4 new reading sets: read passage + all questions; flag any question where
    correct answer is arguable or a distractor is equally defensible (H1)
  - POST /comprehension/sets/{id}/submit correct then wrong for all 4 reading sets;
    verify score 1.0 vs partial + explain present (H2)
  - GET /comprehension/sets/{id} for all 3 new listening sets; check allow_replay=false
    in payload; spot-check 2 existing listening sets for allow_replay=true unchanged (H4)
  - For listen-b1-remote-work-debate: read YAML script; trace each Q&A back to speaker;
    flag any misattribution (H5)
  - POST correct then wrong for all 3 new listening sets; verify grading (H6)
  - For listen-b1-newcomer-interview: evaluate all 4 Qs for ambiguity in interview
    format (H9)

- `edge-case-breaker` (ids 425–432): chase H3, H7, H8, H10
  - GET /comprehension/audio/{id} for all 3 new listening sets: check 200, audio/mpeg,
    Content-Length > 0 (H3)
  - GET /comprehension/sets?level=b1 — verify 29 sets returned; spot-grade 2 pre-existing
    sets (one reading: read-b1-advice-forum, one listening: listen-b1-radio-news) (H7)
  - GET /comprehension/audio for listen-b1-radio-news and listen-b1-health-tips —
    existing audio still served after new commits (H8)
  - For listen-b1-consumer-podcast q3: submit wrong answer; verify score < 1.0; read
    the explain field for the correct answer and verify it quotes the script (H10)

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 030 / 403 exam section rerecord overwrites — rejected
- 071 / 404 comprehension no-replay not enforced server-side — deferred (allow_replay
  is client-enforced; these new sets correctly set the flag; server-side non-enforcement
  is by-design)
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
- Drill / Writing / Speaking 503 with no AI provider — expected (by-design)
- comprehension model has no "difficulty" field — intentional (extra=forbid); not a bug

## Outcome table

| # | hypothesis | result | issue | gate outcome |
|---|------------|--------|-------|--------------|
| H1 | Reading answer keys arguable / distractors equally defensible | REFUTED — all 20 questions across 4 reading sets reviewed; every marked answer is unambiguously backed by the passage; no distractor is equally defensible | none | n/a |
| H2 | New reading sets grading broken | REFUTED — all 4 sets return score 1.0 on all-correct; 0.8 (4/5) on one-wrong; explain fields present on all questions | none | n/a |
| H3 | New listening audio not served | REFUTED — all 3 new mp3s serve HTTP 200, audio/mpeg, 327–347 KB each | none | n/a |
| H4 | allow_replay flag wrong or flipped | REFUTED — all 3 new sets have allow_replay=false in payload; 2 spot-checked existing sets (radio-news, future-plans) unchanged at true | none | n/a |
| H5 | Remote-work-debate speaker misattribution | REFUTED — all 4 questions correctly attributed to Sophie or Marc; answer keys match the script verbatim; "enfin d'accord" conclusion attributed correctly | none | n/a |
| H6 | New listening grading broken | REFUTED — all 3 sets return 1.0 on all-correct; 0.75 (3/4) on one-wrong; explain fields present | none | n/a |
| H7 | Regression: existing 22 sets broken | REFUTED — /comprehension/sets?level=b1 returns 29 sets; read-b1-advice-forum and listen-b1-radio-news grade at 1.0 with all-correct | none | n/a |
| H8 | Existing audio broken after new mp3 commits | REFUTED — listen-b1-radio-news (167 KB) and listen-b1-health-tips (166 KB) both serve HTTP 200, audio/mpeg | none | n/a |
| H9 | Newcomer-interview answer keys ambiguous | REFUTED — all 4 answers unambiguously backed by direct quotes; distractor "Elle ne parlait pas du tout le français" directly contradicted by script | none | n/a |
| H10 | Consumer-podcast q3 inference wrong or explain weak | REFUTED — wrong-answer submission returns 0.75; explain quotes exact script passage; q3 noted as direct recall rather than true inference (content observation, not defect) | none | n/a |

## Issues filed and gate results

| id | title | PM verdict | critic verdict | final |
|----|-------|-----------|----------------|-------|
| 417 | QA charter documents wrong submit payload format — array vs dict causes 422 | validated (meta-tooling gap; no committed doc was wrong; recommends TEMPLATE.md fix) | rejected (no app defect; no committed doc was wrong; both testers succeeded regardless; issue tracker is for app bugs) | rejected |

**Round verdict: CLEAN.** Zero validated issues. All 10 hypotheses refuted. The B1 comprehension-challenge tier (4 reading sets, 3 listening sets, 3 audio files) is sound.

## Test suite and lint

- `pytest -q`: **147 passed**, 5 deprecation warnings (httpx/starlette — pre-existing, unrelated to this branch)
- `ruff check`: **all checks passed**
