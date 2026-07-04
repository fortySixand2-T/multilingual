# QA round 033 — plan

- date: 2026-07-03
- app under test: backend + SPA at http://localhost:8080 (port 8080)
- scope: content/b2-expansion-3 — B2 Slice 3 (units u7 politique, u8 ville, u9 travail):
  3 vocab decks (54 new cards), 9 lessons, 3 comprehension sets, 2 writing tasks,
  b2-mock-3, ~55 TTS clips. Regression on B2 Slices 1–2 (u1–u6) and a1/a2/b1.

## Change surface (highest risk first)

One commit since round 032 (B2 Slice 2 — clean):

1. **B2 expansion Slice 3**: entire u7/u8/u9 content tree added.
   - `path.yaml`: extended from 6 → 9 units; u7 unlocks after u6, u8 after u7, u9 after u8.
   - 9 lesson YAMLs: politique-b2-01/02/03, ville-b2-01/02/03, travail-b2-01/02/03.
   - 3 vocab decks: politique.yaml (18 cards), ville.yaml (18 cards), travail.yaml (18 cards).
   - 3 comprehension sets: read-b2-democracy, read-b2-urban-life, listen-b2-work-future.
   - 2 writing tasks: write-b2-city-letter (Section A, 120–200 w), write-b2-work-essay (Section B, 250–350 w).
   - 1 mock blueprint: b2-mock-3 (reading: read-b2-democracy, listening: listen-b2-work-future).
   - ~55 audio files under content/b2/audio/.

Pure content addition — no code changes. Risk is concentrated in grammar key correctness
(B2 structures are complex) and level surfacing for the 9-unit path.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | grammar — concession (u7 politique) | politique-b2-01: « malgré » + nom is correct; « bien que » (distractor) correctly rejected. politique-b2-02.e1: « ont beau » — "ont" is the answer but the word_bank (e2.e4) uses third-person singular "elle a beau essayer" — verify agreement. politique-b2-03: « quand bien même » + conditionnel (changerait, resterait — both conditional — correct). Check e1.e4 word_bank answer tokens include only "malgré l'abstention le scrutin est valable" (not "bien"). | Read all 9 exercises in 3 politique lessons; verify each answer against grammar rule; check word_bank token vs answer alignment; flag any mismatch | exam-crammer |
| H2 | grammar — d'autant plus / plus…plus / au fur et à mesure (u8 ville) | ville-b2-01.e1: "d'autant" is the answer; distractor "aussi" plausible — verify « d'autant plus … que » is unambiguously the only correct pattern here. ville-b2-01.e4 word_bank answer missing "que" — prompt says "all the more so in the city centre" which is a truncated form, « d'autant plus au centre-ville » — no « que » needed if clause is elided; check this is intentional. ville-b2-02.e4 word_bank: « d'espaces » token used — verify apostrophe elision is a single token (not split). ville-b2-03.e4: word_bank answer only uses 6 of 7 tokens (cyclable excluded — correctly a distractor). | Read all 9 ville exercises; verify proportional/gradation patterns; check e1.e4 grammar and token set | exam-crammer |
| H3 | grammar — but subjonctif / futur antérieur (u9 travail) | travail-b2-01.e1: « pour qu' » answer — the full prompt ends with « ils soient », confirming subjonctif is keyed; the MCQ options include « afin de » (same-subject infinitive) as a distractor — verify it's wrong because there are two different subjects. travail-b2-01.e4 word_bank: answer is « j'explique pour que tout le monde comprenne » — "comprenne" is subj. prés. 3rd sing. of comprendre — correct. travail-b2-02.e1: "de sorte" MCQ answer — note the connective is "de sorte QUE"; does the prompt include "que" already? Check the MCQ prompt: "…___ que les employés restent motivés" — yes, "que" is in the prompt, so the blank is only "de sorte" — correct answer. travail-b2-03: futur antérieur "auront terminé" and "aura signé" — both are avoir + PP — morphologically correct. | Read all 9 travail exercises; verify subjonctif forms (soient, comprenne); verify futur antérieur morphology; check de-sorte-que MCQ prompt structure | exam-crammer |
| H4 | comprehension grading — read-b2-democracy + read-b2-urban-life | Both reading sets: server-side grading; all-correct → 1.0; one-wrong → partial (0.8 for 5-question sets). All keys traceable to passage text. read-b2-democracy.q1 asks what central question the text poses — answer is traceable to "Faut-il y voir un rejet de la démocratie elle-même ?". q5 conclusion key "Redonner confiance se construit dans la durée" is directly quoted — not arguable. read-b2-urban-life.q3 "ville du quart d'heure" is directly quoted. q5 conclusion similarly direct. | POST /comprehension/sets/read-b2-democracy/submit all-correct → 1.0; one-wrong → ~0.8; POST /comprehension/sets/read-b2-urban-life/submit similarly; evaluate each explain for passage traceability | exam-crammer |
| H5 | comprehension grading — listen-b2-work-future | Listening set: allow_replay=false; audio serves; all 4 questions grade correctly. q4 asks Nadia's final position: answer is "Le progrès dépend des règles que nous choisissons" — directly quoted from script ("tout dépend des règles que nous choisissons") — defensible, not arguable. | GET /comprehension/sets/listen-b2-work-future (verify allow_replay=false); GET /comprehension/audio/listen-b2-work-future; POST all-correct → 1.0; one-wrong → 0.75; evaluate q4 key | exam-crammer |
| H6 | unit gating — 9 units, fresh user | /content/path?level=b2 returns exactly 9 units; response uses field `status` (not `state`); u1 = available, u2–u9 = locked for fresh user. POST lesson progress on a locked u7 lesson (politique-b2-01) → 409. | GET /content/path?level=b2; verify 9 units; check status field name; POST to locked lesson | edge-case-breaker |
| H7 | writing tasks — new tasks present, word-count bounds enforced | write-b2-city-letter (120–200 w) and write-b2-work-essay (250–350 w) present in /assessment/tasks?level=b2; 422 under min; 422 over max; target_vocab ids (espace_vert, cyclable, amenagement, mobilite, flexibilite, reconnaissance, competitivite, penibilite) all resolve. | GET /assessment/tasks?level=b2; confirm both tasks present; POST under/over/valid for each; verify status codes | edge-case-breaker |
| H8 | b2-mock-3 — end-to-end | b2-mock-3 starts (POST /exam/start?blueprint=b2-mock-3); reading section (read-b2-democracy) accepts answers; listening section (listen-b2-work-future) accepts answers; writing section (write-b2-city-letter + write-b2-work-essay) accepts text within bounds; speaking section accepts clb_estimate; finish returns CLB report; appears in /exam/history. | Full mock run end-to-end; verify CLB report returned; check history entry | exam-crammer |
| H9 | audio serving — comprehension + 9 lesson clips | listen-b2-work-future.mp3 serves HTTP 200 audio/mpeg with non-zero Content-Length. All 9 lesson listen_type audio_refs (justice, scrutin, pouvoir, embouteillage, infrastructure, voirie, management, reconnaissance, rendement) serve 200. | GET /comprehension/audio/listen-b2-work-future; GET /content/audio/b2/audio/{key} for all 9 refs | edge-case-breaker |
| H10 | vocab id uniqueness — 54 new ids | 54 new vocab ids across politique/ville/travail decks must not collide with any existing id. Semantically-generic ids like "justice", "loi", "droit", "liberte", "election", "corruption", "gouvernement", "constitution" are high-collision risk — these common civic words could plausibly exist in b1 or a2 decks. | Run /tmp/tef312/bin/python -m pytest tests/test_all_levels.py -q | edge-case-breaker |
| H11 | regression — B2 u1–u6 + other levels | Adding u7/u8/u9 did not break earlier units: /content/path?level=b2 still lists all 9 units with u1 intact; a B2 lesson from u1 still loads; /content/levels lists all 4 levels; a b1 comprehension grade still works. | GET /content/path?level=b2 (9 units, u1 details); GET /content/levels; grade listen-b1-radio-news | edge-case-breaker |

## Coverage gaps

- `read-b2-democracy` is the first political-participation reading set at B2 — never tested
  before; q1 and q5 are conclusion/inference type — probe defensibility.
- `listen-b2-work-future` is the first work-themed listening set at B2; allow_replay=false
  is critical to verify (listen-b2-culture-radio from Slice 2 confirmed, but new set is fresh).
- The three-hop unlock chain u7→u8→u9 (three new links after an already-long chain u1→…→u6)
  is the longest unlock chain in the system; gating on politique-b2-01 against a fresh user
  exercises a new terminal-of-chain scenario.
- `write-b2-work-essay` references `target_vocab: [flexibilite, reconnaissance, competitivite,
  penibilite]` — all in the travail deck. `write-b2-city-letter` references `[espace_vert,
  cyclable, amenagement, mobilite]` — all in the ville deck. This cross-unit vocab targeting
  is new; check the server resolves these in-level (not just in-deck).
- travail-b2-02.e1 MCQ: "de sorte" is the keyed answer but the prompt already contains "que"
  — this structure is easy to author wrong (putting "que" in both prompt and option). Confirm
  server-side the MCQ payload is valid and produces a sensible exercise.

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 430–439): chase H1, H2, H3, H4, H5, H8
  - Read all 9 politique lessons; verify « malgré » (nom, no subj), « avoir beau » (ont/a/avons),
    « quand bien même » (conditionnel); verify politique-b2-02.e4 word_bank answer tokens
    (elle a beau essayer…) — 9 tokens, answer uses 9 of 10 (distractor "est" excluded) (H1)
  - Read all 9 ville lessons; verify « d'autant plus … que » — confirm ville-b2-01.e4 word_bank
    answer « le logement est cher d'autant plus au centre-ville » is grammatically acceptable
    (elided clause); confirm ville-b2-02.e4 « d'espaces » is a single token; confirm ville-b2-03.e4
    uses 6 of 7 tokens (cyclable excluded as distractor) (H2)
  - Read all 9 travail lessons; verify « pour qu' » vs « afin de » distinction (different subjects
    → pour que + subj); verify travail-b2-01.e4 word_bank answer has "comprenne" (subj prés.
    3rd sing); verify travail-b2-02.e1 prompt includes "que" so blank is only "de sorte";
    verify travail-b2-03 futur antérieur "auront terminé" and "aura signé" (H3)
  - POST /comprehension/sets/read-b2-democracy/submit all 5 correct → expect 1.0; then
    one-wrong → expect 0.8; read each explain, flag any arguable key (H4)
  - POST /comprehension/sets/read-b2-urban-life/submit all-correct → 1.0; one-wrong → 0.8;
    evaluate q4 (gentrification/renovation) and q5 (conclusion) keys (H4)
  - GET /comprehension/sets/listen-b2-work-future; verify allow_replay=false; POST all-correct
    → 1.0; POST one-wrong → 0.75; evaluate q4 final-position key (H5)
  - Run full b2-mock-3: POST /exam/start?blueprint=b2-mock-3; submit reading section
    (read-b2-democracy answers); submit listening section (listen-b2-work-future answers);
    submit writing section (120-word city-letter + 250-word work-essay within bounds);
    submit speaking section with clb_estimate; call finish; verify CLB report; check /exam/history (H8)

- `edge-case-breaker` (ids 440–449): chase H6, H7, H9, H10, H11
  - Sign up a fresh user; GET /content/path?level=b2; verify exactly 9 units returned; verify
    field is named `status` (not `state`); verify b2.u1 status=available and b2.u7 status=locked;
    POST lesson progress for politique-b2-01 → expect 409 (H6)
  - GET /assessment/tasks?level=b2; confirm write-b2-city-letter (min=120, max=200) and
    write-b2-work-essay (min=250, max=350) present; POST write-b2-city-letter with 5-word body
    → 422; with 201-word body → 422; valid 150-word body → 200 or 503; POST write-b2-work-essay
    with 200-word body → 422; with 351-word body → 422; valid 300-word body → 200 or 503 (H7)
  - GET /comprehension/audio/listen-b2-work-future; verify 200 + audio/mpeg + Content-Length > 0 (H9)
  - GET /content/audio/b2/audio/justice.mp3; scrutin.mp3; pouvoir.mp3; embouteillage.mp3;
    infrastructure.mp3; voirie.mp3; management.mp3; reconnaissance.mp3; rendement.mp3 — all
    expect 200 (H9)
  - Run /tmp/tef312/bin/python -m pytest /Users/sirius/projects/multilingual/tests/test_all_levels.py -q;
    confirm passes including test_vocab_ids_globally_unique_across_levels (H10)
  - GET /content/levels; confirm "b2" listed; GET /content/path?level=b2 (9 units, u1 intact);
    POST /comprehension/sets/listen-b1-radio-news/submit all-correct → 1.0 (H11)

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
- 429 culture-b2-02.e1 MCQ distractors ungrammatical — done (fixed in round 032)
- Drill / Writing / Speaking 503 with no AI provider — expected (by-design)
- comprehension model has no "difficulty" field — intentional (extra=forbid)
- word_bank elisions as single tiles (l'œuvre, c'est, j'explique, qu'elle, l'entreprise) — correct
- 418 mock "stuck" without LLM — rejected; exams self-scored by design

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcome (round completed manually — qa-planner hit a session limit after testing + filing)

B2 Slice 3 (u7 politique, u8 ville, u9 travail) exercised end-to-end; 2 content issues filed, both fixed by hand.

| # | area | result |
|---|------|--------|
| H1 | concession keys (u7: malgré / avoir beau / quand bien même) | REFUTED — keys correct |
| H2 | comparison/proportion keys (u8: d'autant plus que / plus…plus / au fur et à mesure) | issue 430 (e4 taught the truncated « d'autant plus » without a « que » clause) → fixed |
| H3 | purpose + futur antérieur keys (u9) | issue 431 (« de façon de » distractor ungrammatical) → fixed; subjunctive & futur antérieur forms otherwise correct |
| H4 | new comprehension grading (democracy/urban/work-future) | REFUTED — grade 1.0/partial; keys traceable |
| H5 | listening allow_replay=false + audio serving | REFUTED |
| H6 | 9-unit gating (fresh user) | REFUTED — 9 units; u1 available, u2–u9 locked (status field); locked write → 409 |
| H7 | writing bounds + target_vocab | REFUTED |
| H8 | b2-mock-3 end-to-end | REFUTED |
| H9 | global vocab-id uniqueness | REFUTED — 148 pytest incl. uniqueness |
| H10 | regression (b2 u1–u6, a1/a2/b1) | REFUTED |

## Issues filed and gate results

| id | title | verdict |
|----|-------|---------|
| 430 | ville-b2-01.e4 « d'autant plus » without « que » clause | **fixed** — reworked e4 to model the full canonical structure (« ce quartier est d'autant plus recherché qu'il attire les familles »), consistent with e1 and the grammar_point (authorial decision the critic asked for) |
| 431 | travail-b2-02.e1 distractor « de façon de » ungrammatical | **fixed** — replaced distractors with « bien »/« parce » (valid connectors before « que » but semantically wrong: concession/cause vs the purpose « de sorte que »), so elimination requires rule application |

**Round verdict: B2 Slice 3 sound.** 2 real content polish issues found and fixed; all other grammar/comprehension keys correct. 148 pytest, ruff clean.
