# QA round 044 — plan

- date: 2026-07-27
- app under test: backend :9000 (uvicorn, sqlite) / SPA :5173 (vite) — feature branch `feat/daily-xp-goal` (PR #58), not yet merged to main
- scope: pre-merge QA of the daily-XP ledger — anti-farm on Review/Drill XP, streak coverage for the two activities that were previously silent, no-regression on the shared `record_activity` refactor, `xp_today`/daily-goal ring accuracy, and migration 0015.

## Change surface (highest risk first)
Two commits ahead of main (`ab19907` service+API, `f88af42` web ring), touching a
**shared write path** (`record_activity`) used by five call sites plus a new table:
- `app/progress/models.py` — new `DailyXp(user_id, day, source)` table, unique
  (user_id, day, source).
- `app/progress/service.py` — `record_activity` gained `source`/`once_per_day`;
  new `_claim_daily_xp` (atomic `on_conflict_do_nothing` claim for once/day sources,
  `on_conflict_do_update` accumulate for per-unit sources); new `xp_earned_today()`;
  new `DAILY_XP_GOAL = 30`.
- `app/srs/api.py` `POST /srs/review`, `app/tutor/api.py` `POST /tutor/drill` — newly
  award XP (10, once/day) and now return `xp/xp_today/streak/daily_goal`. This is the
  actual feature: two activities that never touched XP/streak before.
- `app/progress/api.py`, `app/comprehension/api.py`, `app/exam/api.py` — existing
  award sites, only added a `source=` tag; should be behaviorally identical.
- `migrations/versions/0015_daily_xp.py` — new additive table + 2 indexes.
- `web/src/screens/Path.tsx` + `styles.css` — new `DailyGoal` SVG ring on home,
  reading `me.xp_today`/`me.daily_goal`.

**Directly relevant history (recurring pattern — weight toward this):** this codebase
has twice shipped and then fixed concurrent-double-award bugs on this exact code
shape — issue `100` (comprehension XP double-award under concurrent submits) and
`390` (concurrent exam-finish XP multiplication), both fixed with the same
insert-on-conflict atomic-claim pattern this branch now reuses for review/drill.
That means the *pattern* is proven, but it's new to two *new* call sites — worth
re-verifying rather than assuming it transfers cleanly. Also relevant: `463`/`465`
(exam/comprehension responses were missing xp/streak fields — since fixed) — this
branch adds those fields to srs/tutor responses too; check they're actually present
and correct, not just added to the schema.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | srs/progress | Hammering `POST /srs/review` many times same day grants the +10 bonus exactly once; `xp` after N reviews == baseline + 10, not +10N | signup, seed/due a card (or add one via SRS add), review it 5-10x back-to-back same day, inspect returned `xp`/`xp_today` and `/progress/me` after | edge-case-breaker |
| H2 | progress | Concurrent near-simultaneous `POST /srs/review` calls (asyncio.gather / parallel curl) can't double-claim the daily bonus — direct re-test of the exact bug class fixed in #100/#390 for the *new* review/drill call sites | fire 5-10 concurrent review requests for the same user/day, sum awarded XP, must be exactly one bonus | edge-case-breaker |
| H3 | progress/srs | A day whose *only* activity is a Review advances the streak: `last_active` set to today, and streak +1 across two consecutive review-only days (no lesson/exam that day) | signup day 1, review only, check `/progress/me` streak/last_active; simulate day 2 review-only (via `today=` if testable at HTTP layer, else note as service-level-only) | returning-learner |
| H4 | progress | `record_activity` refactor didn't change existing behavior: lesson XP still first-pass-only, comprehension 15 once/set, exam 25 once, waive awards 0 but still bumps streak | repeat each activity twice same day via HTTP, confirm XP awarded only once each, response includes correct xp/streak (per #463/#465) | edge-case-breaker |
| H5 | progress/web | `/progress/me` `xp_today` sums correctly across mixed sources in one day (e.g. 2 lessons + 1 review ≈ 30) and resets to 0 the next day; the ring on Path.tsx renders proportional fill pre-goal and switches to the "reached" celebration at/over goal | drive a mixed sequence via HTTP for the data half; view Path in the real browser before/at/over goal for the render half | returning-learner (HTTP) + returning-learner (browser) |
| H6 | migration | 0015 applies cleanly on top of current head, is additive (no data loss / no lock-outs on existing rows), and a fresh `alembic upgrade head` from the pre-migration DB used by the e2e/pytest harness works | `alembic upgrade head` already implicitly exercised by the pytest/e2e harness — confirm clean run; spot check downgrade defined sanely | (covered by automated-suite check below, not a persona charter) |
| H7 | tutor | Drill's `over_budget` no-XP path doesn't crash when the user has no prior `UserProgress` row (`session.get(UserProgress, user.id)` after a not-recorded activity returns `None` → response still needs valid defaults) | box-gated (needs Ollama) — HTTP not testable locally; note as untested/box-only, or approximate via service-level test if feasible | (untested locally — see report) |

## Coverage gaps
- `/tutor/drill` HTTP path (award + response shape) is not exercisable locally — no
  Ollama here. Service-level logic (`record_activity` itself) is shared with review
  and is covered by H1-H4 through the SRS endpoint plus `tests/test_daily_xp.py`.
  If the tester has time/access, the box (`10.0.0.54`) can spot-check drill once,
  read-mostly, cleaning up any created rows/users.
- No prior issue history at all on `xp_today`/daily-goal ring or `DailyXp` — this is
  new surface, not a regression-hotspot area.

## Charters (per tester, with id blocks)
- `edge-case-breaker` as `qa-tester` (ids 550-559): chase **H1, H2, H4** — hammer
  `/srs/review` sequentially and concurrently for the anti-farm/concurrency claims;
  repeat lesson/comprehension/exam/waive submissions same-day to confirm no
  regression in existing award behavior; check response shapes match #463/#465 fix
  intent (xp/streak present on srs/tutor responses too). If time and box access
  allow, spot-check `/tutor/drill` on 10.0.0.54 read-mostly for H1/H2's drill half —
  otherwise report untested.
- `returning-learner` as `qa-tester` (ids 560-564): chase **H3, H5 (data half)** —
  review-only day streak advancement, `/progress/me` xp_today across mixed sources
  same day and reset next day (use the `tests/test_daily_xp.py` service-level pattern
  against a temp sqlite if the HTTP layer can't fake "yesterday" for the two-day
  streak check — note which layer each assertion was actually verified at).
- `returning-learner` as `qa-browser-tester` (ids 565-569): chase **H5 (UI half)** —
  drive the real Path screen in Chrome, confirm the ring renders progress
  proportionally under goal, the celebration state (text + visual) at/over goal, no
  console errors, ring layout doesn't collide with the tool grid/topbar at normal and
  narrow widths (topbar overflow was issue 530 — quick sanity only, not a re-test).

## Don't re-file (already settled)
- 100, 390 — comprebension/exam concurrent double-award — already fixed; this round
  re-tests the *new* review/drill call sites for the same bug class, not these.
- 463, 465 — exam/comprehension responses missing xp/streak — already fixed.
- 392 — drill screen hardcodes A1 level — unrelated pre-existing UI issue, done.
- 530 — topbar nav overflow at 320px — already fixed; only sanity-glance if the new
  ring visually interacts with it, don't re-litigate.
- Drill/Writing/Speaking 503 with no LLM provider locally — expected, not a bug.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
