# QA round 038 — plan

- date: 2026-07-06
- app under test: backend :8080 / SPA :8080
- scope: Drill tutor extended to A2/B1/B2 (student-help slice 4) — prompt level gates,
  level derivation from lesson.level, unsupported-level 400, A1 regression, frontend

## Change surface (highest risk first)

Branch feat/tutor-all-levels, touching:

- `app/tutor/prompts/{a2,b1,b2}_drill.md` — three new scaffolded drill prompts. Level
  gate must hold (one bounded drill, no open conversation, no free-form/essay/opinion
  production). B2 is the riskiest level since it involves "precise structural
  transformation" language that could drift toward open essay if not carefully worded.
- `app/tutor/orchestrator.py` — `_PROMPT_BY_LEVEL` / `_PROFILE_BY_LEVEL` now cover
  a1..b2 via the `_LEVELS` tuple. Levels beyond b2 (c1 etc.) must still raise ValueError.
- `app/tutor/api.py` — derives `level` from `lesson.level` (was hardcoded "a1");
  unsupported level → 400 (was 500). The `post_drill` docstring still says "A1" but
  the behavior is now multi-level.
- `app/config/ai_routing.yaml` — four `drill_a2/b1/b2` profiles added; all mirror
  drill_a1. Route resolution must find these profiles at runtime.
- `web/src/screens/Drill.tsx` — loads current level's lessons (`api.path(level)` not
  hardcoded "a1"); "A1 only" notice removed; subtitle copy updated.
- `tests/test_tutor_levelgate.py` — 2 new tests:
  `test_every_level_has_a_scaffolded_gated_prompt` and
  `test_drill_endpoint_derives_level_from_lesson`.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | level gate — B2 prompt | B2 prompt might allow essay/opinion because it says "precise structural transformation" without explicitly forbidding paragraphs or open questions | Read b2_drill.md; verify "not a conversation", "not a free-form essay/opinion/discussion", "one sentence", "no open-ended prompts" all appear | edge-case-breaker |
| H2 | level gate — A2/B1 prompts | A2 and B1 prompts might be less explicit about the gate than A1 — "one targeted production" or "one guided change" could be interpreted as multiple items if the banning language is softer | Read a2_drill.md and b1_drill.md; compare gate language against a1; verify "not a conversation" and "free-form" ban both present | edge-case-breaker |
| H3 | level derivation — routing | POST /tutor/drill with a b1 lesson routes to drill_b1 profile; with an a1 lesson still routes drill_a1; with a b2 lesson routes drill_b2; each degrades to clean 503 (not 400/500) because no provider available | Curl /tutor/drill with lesson_id=travail-b1-01, greetings-01, sciences-b2-01; verify 503 each time | edge-case-breaker |
| H4 | unsupported level → 400 | A lesson whose level maps to no prompt (e.g. a fictional "c1" lesson) must yield 400, not 500; the ValueError from Tutor() must be caught and mapped properly | Confirm via unit test test_unsupported_level_rejected; also verify API maps it to 400 via test_drill_endpoint_derives_level_from_lesson style | edge-case-breaker |
| H5 | unknown lesson → 404 | POST /tutor/drill with a non-existent lesson_id must return 404 | Curl with lesson_id="no-such-lesson" | edge-case-breaker |
| H6 | A1 regression | The a1 path (greetings-01) still gets profile drill_a1 and degrades to 503 cleanly; budget gate, over_budget field, and graceful message still work; existing AC1.3/1.4/1.5 tests still pass | Run pytest test_tutor_levelgate.py; curl greetings-01 drill endpoint | edge-case-breaker |
| H7 | routing profile resolution | drill_a2, drill_b1, drill_b2 profiles are registered in ai_routing.yaml and recognized by the health endpoint; the health endpoint lists them | Check /health response for profiles list | edge-case-breaker |
| H8 | frontend level switching | Drill.tsx loads level-appropriate lessons; switching to b1 loads b1 lessons (not a1); "A1 only" text is gone; a b2 lesson can be selected and submitted (returns 503 gracefully, not crash) | Web build; npm test | edge-case-breaker |
| H9 | full suite | pytest -q (all tests incl. 2 new tutor tests), ruff check, ruff format --check, web build, npm test all pass | Run full suite | edge-case-breaker |

## Coverage gaps

- The three new endpoints (A2/B1/B2 routing) have no live-HTTP issue history — all prior
  drill issues were A1-only.
- B2 prompt is the first prompt to use "transformation" framing rather than
  "manipulation/guided change" — has not been under the critic's eye before.
- The `ai_routing.yaml` profile registration has no dedicated test; health endpoint
  coverage is the only signal.
- Drill.tsx's `useEffect` re-fetch on level change is new behavior with no prior test.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 451–469): Chase H1–H9 in full. This tester owns the entire
  surface.

  **Sequencing**:
  1. Prompt gate audit (H1+H2): Read all four prompts; for each verify:
     - Contains "exactly one" (or "exactly ONE") drill
     - Contains "not a conversation"
     - Contains "free-form" ban
     - Does NOT contain open-ended instructions ("give your opinion", "write a paragraph",
       "discuss", "argue")
     - B2 specifically: verify "not a free-form essay, opinion, or discussion task" present
     Flag any deviation.
  2. Health check profiles (H7): GET /health and confirm drill_a2, drill_b1, drill_b2
     all appear in the profiles list.
  3. Auth setup: POST /auth/signup with friend-001; store token.
  4. Level derivation — live HTTP (H3):
     - POST /tutor/drill {lesson_id: "greetings-01"} → expect 503 (a1, no provider)
     - POST /tutor/drill {lesson_id: "travail-b1-01"} → expect 503 (b1)
     - POST /tutor/drill {lesson_id: "sciences-b2-01"} → expect 503 (b2)
     If any returns 400 or 500, that is a bug.
  5. Unknown lesson → 404 (H5): POST /tutor/drill {lesson_id: "no-such-lesson"} → 404.
  6. Unsupported level → 400 (H4): Verify unit test test_unsupported_level_rejected passes;
     also confirm API test test_drill_endpoint_derives_level_from_lesson passes.
  7. A1 regression (H6): curl greetings-01; verify 503 not 400/500; run pytest on
     test_tutor_levelgate.py to confirm all AC1.x tests pass.
  8. Full suite (H9): `/tmp/tef312/bin/python -m pytest -q`; `ruff check .`;
     `ruff format --check .`; `cd /Users/sirius/projects/multilingual/web && VITE_API_BASE="" npm run build`; `npm test`.
  9. Frontend (H8): verify web build succeeds; npm test passes; inspect Drill.tsx for
     absence of "A1 only" text and presence of `api.path(level)`.

  **Auth**: POST /auth/signup with invite_code friend-001. Bearer token for drill calls.

  **Lessons to use**: greetings-01 (a1), travail-b1-01 (b1), sciences-b2-01 (b2).
  Verify these exist via GET /content/path/{level} or GET /tutor/drill 404 signal.

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 071 comprehension no-replay not enforced server-side — deferred
- 131 password no max length — deferred
- 181 locked lesson content readable — deferred
- 394 level-filtered endpoints accept empty string — deferred
- 418 mock exam stuck when LLM unavailable — deferred (503 expected)
- 428 lesson fail first_time → first_pass — done
- 447 focus pill shows when target_met — done
- 448 weakspots wrong pick not highlighted — done
- 449 weakspots answer resolves but no filter on resolved — deferred
- 450 weakspots no tests for unanswered/ordering/404 — deferred
- Drill / Writing / Speaking 503 with no AI provider — EXPECTED (healthy outcome)
- Self-scored writing/speaking (user supplies clb_estimate) — by design

## Outcome

Round complete — 9 hypotheses, 7 refuted outright, 2 produced issues that were rejected
or deferred by the gate. Zero validated issues. Dev-fixer not run.

### Hypothesis results

| # | verdict | notes |
|---|---------|-------|
| H1 | refuted | B2 prompt explicitly contains "not a free-form essay, opinion, or discussion task"; "one sentence"; "no open-ended prompts". Gate is sound. |
| H2 | refuted | A2 and B1 prompts each contain "not a conversation", "free-form" ban, and "exactly ONE". Gate language is comparably tight to A1 at every level. |
| H3 | refuted | greetings-01 (a1) → 503; travail-b1-01 (b1) → 503; sciences-b2-01 (b2) → 503. All three degrade cleanly; no 400 or 500. |
| H4 | refuted | test_unsupported_level_rejected passes; Tutor(level="c1") raises ValueError; API maps it to 400 via the try/except in post_drill. |
| H5 | refuted | POST /tutor/drill {lesson_id: "no-such-lesson-xyz"} → 404 with correct detail message. |
| H6 | refuted | greetings-01 → 503 (not regressed); all 10 tests in test_tutor_levelgate.py pass including AC1.3/1.4/1.5. Full suite: 158 passed. |
| H7 | refuted | /health returns profiles: ["drill_a1","drill_a2","drill_b1","drill_b2","examiner_roleplay","grammar_explain","writing_feedback"]. All four drill profiles registered. |
| H8 | refuted | Drill.tsx uses api.path(level) on line 15; no "A1 only" text anywhere; subtitle reads "Scaffolding eases as the level rises." Web build clean; 19 npm tests pass. |
| H9 | refuted | 158 pytest passed; ruff check clean (112 files); ruff format clean; web build succeeds; npm test 19/19. |

### Issues filed

| id | title | final verdict |
|----|-------|---------------|
| 451 | api/tutor/api.py docstring still says "A1 drill" | rejected — inline comment at lines 43-44 neutralises the re-hardcoding risk; cosmetic only |
| 452 | test_drill_endpoint_derives_level_from_lesson omits a2/b2 HTTP coverage | deferred — derivation is level-agnostic; PM's risk scenario (missing level: field) is structurally impossible per Pydantic model; hygiene gap only |

### Level-gate verdict (per prompt)

| prompt | "exactly ONE" | "not a conversation" | free-form ban | no open-ended invite | verdict |
|--------|--------------|---------------------|---------------|---------------------|---------|
| a1_drill.md | yes | yes | yes | yes | PASS |
| a2_drill.md | yes | yes | yes | yes | PASS |
| b1_drill.md | yes | yes | yes | yes | PASS |
| b2_drill.md | yes | yes | yes ("not a free-form essay, opinion, or discussion task") | yes | PASS |

**The level gate holds at every level, including B2.** The "precise structural transformation" framing in the B2 prompt does not weaken the gate — it is surrounded by explicit bans on essays, opinions, paragraphs, and open-ended prompts.

**Verdict: sound. 0 validated, 1 rejected, 1 deferred. Slice is ready for PR.**
