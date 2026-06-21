# The frontend SPA is untested by the QA rounds

## Short version

The QA rounds test the **backend HTTP API**, not the app the user actually touches.
The `qa-tester` agent only has Bash/Read/Write/Grep/Glob — no browser, no Playwright.
So all 10 rounds drove the API with curl-style calls (`POST /exam/start`,
`POST /exam/{id}/section`, …). Every issue file shows it: the repro steps are JSON
request/response, never "click this, see that."

The personas are *written* as people on a phone — "taps the most obvious thing,"
"double-taps when nothing happens," "gives up if a screen is blank or unlabeled."
But nothing in the loop ever renders `web/` — ~1,750 lines of React across 13 screens
(`Exam`, `Lesson`, `Drill`, `Speaking`, `Writing`, `GroupBoard`, …). So the rounds
validate the contract the SPA *depends on*, but never the SPA itself.

## The three blind spots

### 1. Real user flows
The multi-step paths that only exist in the client. The backend tells you
`POST /exam/{id}/section` upserts correctly; it can't tell you that a beginner tapping
through `Path → Lesson → result` understands where to go next, or that a button gives
feedback before they double-tap it. That's literally what the `absolute-beginner`
persona "cares about / will flag" — and exactly what API-level tests can't reach.

### 2. Error states
`api.ts` throws `ApiError` on every non-2xx, and each screen does
`.catch((e) => setError(e.message))`, rendering the raw backend `detail` string into a
red div. The rounds confirm the backend *returns* 400s with good messages; nobody has
checked what those look like rendered to a confused user (e.g. a Pydantic 422 blob
dumped straight into the UI), or which `.catch(() => {})` swallows errors silently
(`Exam.tsx:22` does exactly that for history).

### 3. The resume UI (sharpest example)
Rounds 007 and 009 hardened the *server* side of resume: in-progress attempts stay
open, sections upsert, the lost-update fix. But the **resume affordance is pure
frontend** — `Exam.tsx:122-126` filters `history` for `status === "in_progress"` and
renders a button per attempt calling `resume(a.attempt_id)`, which re-fetches and
rehydrates `recorded` state. None of that filtering/rehydration logic has ever been
exercised. Questions the backend rounds structurally *cannot* answer:
- Does a learner with two stale in-progress attempts see two confusing buttons?
- After resume, does the section UI correctly show which skills are already recorded
  (the `recorded` map at `Exam.tsx:16`)?

The server-side correctness is solid; whether the user can actually find and use resume
is untested.

## Why this isn't a knock on the QA work

The backend coverage is genuinely thorough. The point is that the test surface stops at
the API boundary, and the entire layer the user actually sees and touches is on the
other side of it.

## Closing the gap

The cleanest option is a browser-driven persona — give a tester the `/verify` or `/run`
path (it can launch the Vite SPA + drive a browser) so the same persona charters get
exercised against the real screens instead of curl.
