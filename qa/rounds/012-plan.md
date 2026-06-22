# QA round 012 — frontend (SPA)

- date: 2026-06-21
- under test: the Vite + React SPA in `web/` (no browser automation available here, so:
  build/typecheck + a static contract audit against 11 rounds of backend changes).
- note: ran on branch `content/a1-bank` (parallel content-bank + SPA-audio work present).

## Change surface (highest risk first)
- The SPA predates the auth/validation hardening of rounds 1–7 (password min, display_name
  min/max, email normalize, 0–10 score). Most likely drift: how it **shows backend errors**.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | build | `npm run build` (tsc) fails | run it | edge-case-breaker |
| H2 | auth UX | Validation rejections render as raw pydantic JSON; the signup form lacks the new constraints | read api.ts + Login.tsx; check 422 rendering | edge-case-breaker |
| H3 | resilience | AI/error screens don't catch backend errors (blank/crash on 503) | grep screens for error handling | edge-case-breaker |
| H4 | contract | Lesson score scale / exam wiring drifted from the backend | read Lesson.tsx, Exam.tsx, api.ts | exam-crammer |

## Outcome
- **H1 — refuted.** `tsc && vite build` is clean.
- **H2 — confirmed → issue 200 (validated → fixed).** `api.ts` rendered a 422 as
  `JSON.stringify(detail)` → users saw raw pydantic JSON for every backend validation
  (short password, blank/oversized name, out-of-range score). Also the signup form's
  display-name field lacked `required`/`maxLength` and the password lacked `minLength`.
- **H3 — refuted.** Every error-prone screen (Drill/Writing/Speaking/Exam/Comprehension/
  Review) already catches and shows errors; with the H2 fix they now show readable text.
- **H4 — refuted.** Lesson sends `score = correct/total*10` (0–10, matches backend); the
  exam client (resume, sections, finish) matches the API shapes.

Net: 1 fix (200). Build + 107 backend tests green on the combined branch.