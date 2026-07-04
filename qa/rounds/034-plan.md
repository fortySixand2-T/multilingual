# QA round 034 — plan

- date: 2026-07-04
- app under test: backend + SPA at http://localhost:8080 (port 8080)
- scope: content/b2-expansion-4-final — B2 10th unit (alimentation/agriculture):
  1 vocab deck (18 cards: agriculture→denree), 3 lessons (alimentation-b2-01/02/03),
  2 comprehension sets (read-b2-food-system, listen-b2-food-market), 2 writing tasks
  (write-b2-food-letter Section A 120–200 w, write-b2-food-essay Section B 250–350 w),
  b2-mock-4, 19 TTS clips. B2 level is now COMPLETE (10 units, 30 lessons, 180 vocab).
  Regression on B2 u1–u9 and a1/a2/b1.

## Change surface (highest risk first)

One commit since round 033 (B2 Slice 3 — 2 content issues fixed, otherwise clean):

1. **B2 final slice — unit u10 alimentation**: entire content tree for the 10th unit added.
   - `path.yaml`: extended from 9 → 10 units; b2.u10 unlocks after b2.u9.
   - 3 lesson YAMLs: alimentation-b2-01/02/03 (condition, restriction, mise en relief).
   - 1 vocab deck: alimentation.yaml (18 cards).
   - 2 comprehension sets: read-b2-food-system (5-question reading), listen-b2-food-market
     (4-question listening, allow_replay=false, accent=qc).
   - 2 writing tasks: write-b2-food-letter (Section A, 120–200 w), write-b2-food-essay
     (Section B, 250–350 w).
   - 1 mock blueprint: b2-mock-4 (reading: read-b2-food-system, listening: listen-b2-food-market).
   - 19 audio files under content/b2/audio/ (18 vocab clips + listen-b2-food-market.mp3).

Pure content addition — no code changes. Risk is concentrated in:
(a) grammar key correctness for three B2-high grammar points (subjonctif structures, ne
    explétif, mise en relief), same defect class as issues 429/430/431;
(b) 10-unit path gating (u10 is the longest unlock chain in the system);
(c) listen-b2-food-market allow_replay=false (accent=qc is novel — all prior listening sets
    used metropolitan French).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | grammar — condition subjonctif (alimentation-b2-01) | e1 MCQ: « à condition que » requires subjonctif; « devienne » is the keyed 3rd-sing subj prés of « devenir » — correct. e4 word_bank: « j'achèterai bio pourvu que ça reste abordable » — « reste » is subj prés 3rd sing of « rester » (note: identical to indicatif prés 3rd sing — verify the teach point is clear even if both forms look the same). Distractor « restera » (futur) correctly excluded. Risk: word_bank distractor « restera » vs keyed « reste » — student might argue they're indistinguishable in isolation. | Read alimentation-b2-01; verify « devienne » subj prés morphology; verify « reste » is unambiguous in context; flag if distractor « restera » differs only by tense (acceptable) vs if « reste » alone is ambiguous | exam-crammer |
| H2 | grammar — restriction (alimentation-b2-02) + ne explétif | e1 MCQ: « à moins que » + subjonctif with ne explétif → « n'agisse » (subj prés 3rd sing of « agir »). Distractor « agit » (indicatif prés) and « agira » (futur) — both correctly excluded. e4 word_bank: « sauf si » + indicatif — « on mangera local sauf si c'est trop cher » — « mangera » is futur simple (not conditionnel), which is the idiomatic form after « sauf si »; verify « à » is the distractor token (excluded from answer). Risk: « n'agisse » — ne explétif is subtle; distractor « agit » without « ne » might confuse students (this is a teach point, not a defect, unless the MCQ option literally shows « n'agit » or similar confuser). | Read alimentation-b2-02; verify « n'agisse » correct subj prés of agir; check that the MCQ options are "n'agisse", "agit", "agira" (not "n'agit" — that would be a grammatical distractor blurring the ne explétif rule); verify word_bank answer excludes « à » and uses « on », « mangera », « local », « sauf », « si », « c'est », « trop », « cher » | exam-crammer |
| H3 | grammar — mise en relief (alimentation-b2-03) | e1 MCQ: « ___ compte, c'est la qualité des denrées » → « Ce qui » (subject cleft). Distractor « Ce que » incorrectly takes object position (requires a direct object after the verb). Distractor « Qu'est-ce qui » is a question form — wrong in declarative. e4 word_bank: « ce que les consommateurs veulent c'est la transparence » — object cleft (« veulent » takes direct object). Distractor « qui » token excluded from answer. Risk: these two exercises use the same cleft structure with different CE QUI vs CE QUE — this is the most linguistically subtle area; a student or content author might accidentally swap them. | Read alimentation-b2-03; verify e1 answer « Ce qui » (subject) and e4 answer « ce que » (object); cross-check the grammar point explanation covers both; flag if any token is missing from e4 answer | exam-crammer |
| H4 | comprehension grading — read-b2-food-system | 5-question reading set; all keys directly traceable to passage text. q3 is inference-adjacent (« les défenseurs du bio répondent que… ») — the passage says « une grande partie de la nourriture produite est aujourd'hui gaspillée, ou sert à nourrir du bétail » which is clearly the answer. q5 asks conclusion — answer is « pas de solution unique; il faut produire et consommer autrement » — directly quoted. All-correct → 1.0; one-wrong → 0.8. | POST /comprehension/sets/read-b2-food-system/submit all-correct → expect 1.0; one-wrong → expect 0.8; read each explain, flag any arguable key | exam-crammer |
| H5 | comprehension grading — listen-b2-food-market (accent=qc) | 4-question listening set; allow_replay=false; audio must serve; all 4 keys directly traceable to script text. q1 (circuit court benefits), q2 (no-intermediary advantage), q3 (real problem = gaspillage), q4 (advice = acheter de saison + cuisiner légumes abîmés). Risk: accent=qc is a first for this app — if the server reads the audio_ref path, it must resolve content/b2/audio/listen-b2-food-market.mp3 regardless of accent field. | GET /comprehension/sets/listen-b2-food-market; verify allow_replay=false; GET /comprehension/audio/listen-b2-food-market; verify 200 + audio/mpeg + Content-Length > 0; POST all-correct → 1.0; one-wrong → 0.75 | exam-crammer |
| H6 | 10-unit gating — fresh user | /content/path?level=b2 returns exactly 10 units (b2.u1–b2.u10); field named `status`; b2.u1 = available, b2.u10 = locked. POST lesson progress on alimentation-b2-01 (locked u10 lesson) → 409. 10 is the longest unlock chain in the system — verify the chain terminates correctly. | Sign up fresh user; GET /content/path?level=b2; verify 10 units; verify status field; check u1=available, u10=locked; POST progress alimentation-b2-01 → 409 | edge-case-breaker |
| H7 | writing tasks — food letter + food essay in assessment endpoint + word-count bounds | write-b2-food-letter (120–200 w) and write-b2-food-essay (250–350 w) present in /assessment/tasks?level=b2; 422 under min; 422 over max; target_vocab ids ([malbouffe, gaspillage_alimentaire, circuit_court, producteur] and [elevage, agriculture, souverainete_alimentaire, autosuffisance]) all resolve in-level. | GET /assessment/tasks?level=b2; confirm both tasks present; POST under/over/valid for each; verify status codes | edge-case-breaker |
| H8 | b2-mock-4 — end-to-end | b2-mock-4 starts; reading section (read-b2-food-system) accepts answers; listening section (listen-b2-food-market) accepts answers; writing section (write-b2-food-letter + write-b2-food-essay) accepts text within bounds; speaking section accepts clb_estimate; finish returns CLB report; entry in /exam/history. | Full mock run; verify CLB report; check history entry | exam-crammer |
| H9 | vocab-id global uniqueness — 18 new ids | 18 new vocab ids (agriculture, agriculteur, elevage, recolte, engrais, bio, circuit_court, gaspillage_alimentaire, malbouffe, souverainete_alimentaire, terroir, filiere, cheptel, semence, autosuffisance, etiquetage, producteur, denree) must not collide with any existing id across all levels. High-collision risk ids: bio (could be in a1/a2/b1 health/nature decks), agriculture/agriculteur (b1 environment?), terroir (b1?). | Run /tmp/tef312/bin/python -m pytest tests/test_all_levels.py -q | edge-case-breaker |
| H10 | audio — 19 TTS clips all serve 200 | 18 vocab clips + listen-b2-food-market.mp3 must all return 200 audio/mpeg. alimentation-b2-02.e3 references terroir.mp3 (already in audio dir?), alimentation-b2-01.e3 references agriculture.mp3, alimentation-b2-03.e3 references semence.mp3 — verify all 3 lesson listen_type refs serve. | GET /content/audio/b2/audio/{key}.mp3 for all vocab clips + lesson refs; GET /comprehension/audio/listen-b2-food-market | edge-case-breaker |
| H11 | regression — B2 u1–u9 + a1/a2/b1 | Adding u10 did not break earlier units: /content/path?level=b2 still lists all 10 units with u1 intact; a B2 lesson from u1 still loads; /content/levels lists all 4 levels; a B1 comprehension grade still works. | GET /content/path?level=b2 (10 units, u1 available); GET /content/levels; grade listen-b1-radio-news all-correct → 1.0 | edge-case-breaker |

## Coverage gaps

- `listen-b2-food-market` uses `accent: qc` (Quebec French) — no prior listening set used this
  field; verify the server ignores or handles it gracefully and still resolves the audio_ref.
- b2.u10 is the terminal node of the longest unlock chain in the system (u1→u2→…→u10);
  the gating logic has only been tested up to u9 before.
- The « reste » form in alimentation-b2-01.e4 is identical in subjonctif prés and indicatif
  prés (3rd sing of « rester ») — the content relies on context (« pourvu que ») to
  disambiguate. This is grammatically sound but worth noting for the critic: is the teaching
  value of this specific example compromised?
- `write-b2-food-essay` references `target_vocab: [elevage, agriculture, souverainete_alimentaire,
  autosuffisance]` — all in the alimentation deck. `write-b2-food-letter` references
  `[malbouffe, gaspillage_alimentaire, circuit_court, producteur]` — also alimentation. Both
  tasks draw from the same unit's vocab. Check the server resolves these in-level.
- The mock-4 blueprint ties reading and listening to the same unit's content — this is a first
  (prior mocks drew comprehension from different units). Confirm the exam engine treats this
  normally.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 432–441): chase H1, H2, H3, H4, H5, H8
  - Read alimentation-b2-01: verify « devienne » (subj prés of devenir, 3rd sing — not « devient »
    indicatif or « deviendra » futur); note that « reste » in e4 looks identical to indicatif —
    acceptable because « pourvu que » forces subjonctif context; verify distractor « restera » is
    correctly excluded from e4 answer tokens (H1)
  - Read alimentation-b2-02: verify MCQ options are exactly ["n'agisse", "agit", "agira"] (confirm
    ne explétif is in the keyed option, not in a distractor); verify e4 word_bank answer is
    ["on","mangera","local","sauf","si","c'est","trop","cher"] and distractor is « à » (H2)
  - Read alimentation-b2-03: verify e1 answer « Ce qui » (subject — « Ce qui compte »); verify e4
    answer is [ce, que, les, consommateurs, veulent, "c'est", la, transparence] — object cleft;
    verify distractor « qui » is excluded from e4 answer; check grammar explain covers both
    CE QUI (subject) and CE QUE (object) distinction (H3)
  - POST /comprehension/sets/read-b2-food-system/submit all 5 correct → expect 1.0; re-submit
    with q3 wrong → expect 0.8; read each explain, flag any inference key that is arguable (H4)
  - GET /comprehension/sets/listen-b2-food-market; verify allow_replay=false; GET
    /comprehension/audio/listen-b2-food-market; verify 200 + audio/mpeg + Content-Length > 0;
    POST all 4 correct → expect 1.0; POST q3 wrong → expect 0.75; evaluate every explain for
    script traceability (H5)
  - Run full b2-mock-4: POST /exam/start?blueprint=b2-mock-4; submit reading section (read-b2-
    food-system all 5 answers); submit listening section (listen-b2-food-market all 4 answers);
    submit writing section (120-word food-letter + 260-word food-essay within bounds); submit
    speaking section with clb_estimate; call finish; verify CLB report returned; check /exam/history
    for the new entry (H8)

- `edge-case-breaker` (ids 442–451): chase H6, H7, H9, H10, H11
  - Sign up fresh user; GET /content/path?level=b2; verify exactly 10 units; verify field is
    `status` (not `state`); verify b2.u1 status=available and b2.u10 status=locked; POST lesson
    progress for alimentation-b2-01 → expect 409 (H6)
  - GET /assessment/tasks?level=b2; confirm write-b2-food-letter (min=120, max=200, section=A)
    and write-b2-food-essay (min=250, max=350, section=B) present; POST write-b2-food-letter with
    10-word body → 422; 201-word body → 422; 150-word valid body → 200 or 503; POST
    write-b2-food-essay with 100-word body → 422; 351-word body → 422; 280-word valid body →
    200 or 503; confirm target_vocab ids all present in /content/vocab?level=b2 (H7)
  - Run /tmp/tef312/bin/python -m pytest /Users/sirius/projects/multilingual/tests/test_all_levels.py -q;
    confirm passes including test_vocab_ids_globally_unique_across_levels (H9)
  - GET /content/audio/b2/audio/agriculture.mp3; terroir.mp3; semence.mp3 (the 3 lesson
    listen_type refs) → all expect 200 audio/mpeg; GET /comprehension/audio/listen-b2-food-market
    → 200 audio/mpeg + Content-Length > 0 (H10)
  - GET /content/audio/b2/audio/{vocab}.mp3 for remaining vocab clips (agriculteur, elevage,
    recolte, engrais, bio, circuit_court, gaspillage_alimentaire, malbouffe, souverainete_alimentaire,
    filiere, cheptel, autosuffisance, etiquetage, producteur, denree) → all expect 200 (H10)
  - GET /content/levels; confirm "b2" listed; GET /content/path?level=b2 (10 units, u1 details
    intact); POST /comprehension/sets/listen-b1-radio-news/submit all-correct → 1.0 (H11)

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
- 404 / 071 comprehension no-replay not enforced — deferred
- 405 mock-3 writing tasks duplicated — rejected
- 416 exam blueprints/{id} SPA catch-all — rejected
- 417 charter submit payload format — rejected
- 418 mock exam stuck when LLM unavailable — rejected (self-scored by design)
- 419 word_bank elision split as bare l token — done (fixed)
- 428 lesson fail first_time always false — deferred (pre-existing, all levels)
- 429 culture-b2-02.e1 MCQ distractors — done (fixed round 032)
- 430 ville-b2-01.e4 d'autant plus without que clause — done (fixed round 033)
- 431 travail-b2-02.e1 de façon de ungrammatical distractor — done (fixed round 033)
- Drill / Writing / Speaking 503 with no AI provider — expected (by-design)
- word_bank elisions as single tiles (j'achèterai, c'est, on, etc.) — intentional
- 418 mock "stuck" without LLM — rejected; exams self-scored by design
- comprehension model has no "difficulty" field — intentional (extra=forbid)
- « reste » identical in subj prés and indicatif prés for « rester » 3rd sing — linguistically
  expected; the surrounding conjunction (pourvu que) disambiguates; do NOT file

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcome (round 034 — completed)

B2 final slice (u10 alimentation) exercised end-to-end. 1 content/API issue found and fixed. All grammar, comprehension, gating, audio, and regression checks clean.

| # | area | result |
|---|------|--------|
| H1 | condition subjonctif (alimentation-b2-01): « devienne », « reste », distractor « restera » | REFUTED — keys correct; ne explétif in MCQ option confirmed; distractor correctly excluded |
| H2 | restriction + ne explétif (alimentation-b2-02): « n'agisse », sauf-si word_bank | REFUTED — « n'agisse » is the full option (ne explétif present); distractor « à » excluded from answer |
| H3 | mise en relief (alimentation-b2-03): ce qui (subject) vs ce que (object) | REFUTED — e1 uses « Ce qui » (subject, correct); e4 uses « ce que » (object, correct); no swap |
| H4 | read-b2-food-system comprehension grading | REFUTED — all-correct → 1.0; one-wrong → 0.8; all explains passage-traceable |
| H5 | listen-b2-food-market: allow_replay=false, audio, grading, accent=qc | REFUTED — allow_replay=false; 200 audio/mpeg; 1.0/0.75 scores; accent=qc returned in GET |
| H6 | 10-unit gating — fresh user | REFUTED — 10 units; status field correct; u1 available, u10 locked; locked POST → 409 |
| H7 | writing tasks present + word-count bounds enforced | PARTIALLY CONFIRMED → issue 442 (target_vocab absent from list response); word-count bounds correctly enforce 422 |
| H8 | b2-mock-4 end-to-end | REFUTED — all 4 sections accepted; CLB report returned; history entry present |
| H9 | vocab-id global uniqueness — 18 new ids | REFUTED — 9 pytest passes including uniqueness test |
| H10 | audio — 19 TTS clips serve 200 | REFUTED — all 19 audio files (18 vocab + comprehension mp3) return 200 audio/mpeg |
| H11 | regression — B2 u1–u9 + a1/a2/b1 | REFUTED — 4 levels listed; 10-unit B2 path intact; b1 comprehension grade → 1.0 |

## Issues filed and gate results

| id | title | severity | verdict |
|----|-------|----------|---------|
| 442 | GET /assessment/tasks list omits target_vocab field | medium | **validated → fixed** — added `"target_vocab": r.data.get("target_vocab", [])` to list_tasks() in app/assessment/api.py; 20 assessment tests pass |

## pytest + ruff (final)
- pytest tests/test_all_levels.py: 9 passed
- ruff check .: All checks passed

**Round verdict: B2 final slice sound.** 1 real API gap found and fixed. All grammar keys correct, all comprehension sets gradeable, 10-unit gating correct, audio complete, no regressions. B2 level (10 units, 30 lessons, 180 vocab) is ready for PR.
