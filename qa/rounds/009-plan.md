# QA round 009 — plan

- date: 2026-06-20
- app under test: backend :9000 / SPA :5173
- scope: keep pressing **concurrency** into paths the earlier rounds didn't cover —
  specifically the exam `sections` JSON column (read-modify-write) and SRS writes — plus
  numeric query-param robustness.

## Change surface (highest risk first)
- `record_section` rewrites the whole `sections` JSON blob (`dict(attempt.sections)` →
  mutate → assign). That's a classic lost-update under concurrency, untested.
- SRS review is also read-modify-write on a card row; `srs/queue?limit` is unbounded.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | exam | Concurrent section records **lose updates** — the JSON blob is overwritten, dropping racing skills | start a mock, record all 4 sections in parallel, inspect `recorded` | exam-crammer |
| H2 | srs | `srs/queue?limit` mishandles negative / zero / huge values (error or nonsense) | hit the queue with limit=-1, 0, 999999999 | edge-case-breaker |
| H3 | srs | Concurrent reviews of one card **500 or corrupt** the schedule | 5 parallel reviews of the same card | edge-case-breaker |

## Coverage gaps
No issue history: exam section write atomicity, SRS write concurrency, query-param bounds.
H1 is the highest-value.

## Charters (per tester, with id blocks)
- `exam-crammer` (ids 170–179): chase H1.
- `edge-case-breaker` (ids 180–189): chase H2, H3.

## Don't re-file (already settled)
- 007, 030, 071, 102, 131 — rejected. 001, 050 — deferred.
- 006, 010, 040, 070, 100, 101, 130, 150 — fixed.
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round)
- **H1 — confirmed → issue 170 (validated → fixed).** 4 concurrent sections → only 1
  persisted (`['writing']`). Read-modify-write clobbered the JSON blob. Fixed with an
  atomic `json_set` UPDATE that patches one key; live re-test → all 4 persist.
- **H2 — refuted.** `limit=-1` returns all your cards (SQLite `LIMIT -1`), `0` → empty,
  huge → all. Harmless on a per-user, small set — no crash, no leak.
- **H3 — refuted.** 5 concurrent reviews of one card → all 200, no 500; last-write-wins
  on a single card's due date, no data loss.

Net: 3 hypotheses → 1 confirmed/fixed (170), 2 refuted. 170 is the concurrency class
(qa-070 / qa-100) striking a third path — now exam section writes are atomic too.