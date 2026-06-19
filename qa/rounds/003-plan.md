# QA round 003 — plan

- date: 2026-06-19
- app under test: backend :9000 / SPA :5173
- scope: regression-test the new server-side gating, chase the recurring input-bounds
  class into untested endpoints, and probe the group board for PII leakage.

## Change surface (highest risk first)
- **Round 2 added write-side gating**: `submit_result` now 409s on locked lessons via
  `is_lesson_unlocked()` (`app/progress/api.py`, `app/content/api.py`). New conditional
  on a hot path → top regression risk.
- Earlier rounds added input bounds piecemeal (password, score, correct≤total) — the
  *pattern* recurs, so untouched inputs are suspect.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | progress | New gating **over-blocks** a legit case — e.g. re-completing an already-done lesson (unit now `complete`, not `locked`) gets wrongly 409'd, breaking SRS re-seed / streak | complete greetings-01, then POST its result again → expect **200**, not 409 | returning-learner |
| H2 | progress | A lesson **not owned by any unit** (or cross-level) is ungated and silently completable, or crashes `is_lesson_unlocked` | POST result for a lesson id absent from every unit's `lessons` | edge-case-breaker |
| H3 | progress | Board **leaks email**: `display_name or email` means a user with no display name exposes their email to the whole group | sign up with empty `display_name`, GET /progress/board → is an email rendered? | edge-case-breaker |
| H4 | assessment | The input-bounds class extends here — `assessment/tasks/{id}/submit` accepts empty/oversized/garbage payloads with a 200 | submit blank + 100KB body | edge-case-breaker |
| H5 | exam | Section can be **recorded twice / overwritten**, or two concurrent attempts of one blueprint corrupt the resume state | start blueprint twice; POST same section twice with different scores | exam-crammer |

## Coverage gaps
No issue history yet: `auth/me`, `speech/*`, `assessment/*`, `srs/review` reschedule
math, board ordering/privacy. H3 and H4 cover the two highest-value gaps.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 010–019): chase H2, H3, H4.
- `returning-learner` (ids 020–029): chase H1.
- `exam-crammer` (ids 030–039): chase H5.

## Don't re-file (already settled)
- 007 negative elapsed_seconds — rejected (no impact)
- 001 invalid email — deferred (product decision)
- 006 locked-lesson write — fixed in round 2 (H1/H2 are the *regression* check, not a re-file)
- Drill / Writing / Speaking 503 with no provider — expected

## Outcome (after the round)
- **H1 — refuted.** Re-completing a done lesson returns 200 (`first_time:false`); the
  round-2 gating doesn't over-block. Area sound.
- **H2 — refuted.** Every synced lesson belongs to a unit; an unknown id is a clean 404.
  The orphan-lesson branch isn't reachable with current content.
- **H3 — confirmed → issue 010 (validated → fixed).** Blank `display_name` leaked the
  user's email on the shared board. Highest-value find of the round.
- **H4 — refuted.** `assessment/submit` already rejects empty/whitespace/missing (422).
- **H5 — confirmed → issue 030 (rejected by the gate).** Re-recording a section
  overwrites last-write-wins, but the critic ruled it an intended redo with no
  shared-state harm. No change.

Net: 5 hypotheses → 2 confirmed, 3 refuted; 1 real bug fixed (010), 1 false positive
stopped at the gate (030).
