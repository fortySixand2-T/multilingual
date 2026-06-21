# QA round 010 — plan

- date: 2026-06-20
- app under test: backend :9000 / SPA :5173
- scope: a **data-exposure / privacy audit** — comprehension is *server-graded*, so its
  answers must never reach the client; sweep the read endpoints for leaked answer keys,
  rubrics, or PII, and check whether content gating leaks on read.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | comprehension | A read endpoint (list/get) leaks the server-graded answer key | dump sets list + single set, grep for answers | edge-case-breaker |
| H2 | privacy | Some response leaks `password_hash`/salt or another user's PII | dump auth/me, assessment, exam, board | edge-case-breaker |
| H3 | content | Gating isn't enforced on **read** — a locked lesson's content (incl. answers) is fetchable | as a fresh user, GET a locked lesson | edge-case-breaker |
| H4 | comprehension | Submit **feedback reveals the answer key**, enabling a known-answer retry that earns XP | submit all-wrong, read `correct_answer`, retry | edge-case-breaker |

## Coverage gaps
No issue history: answer-key exposure across read paths, PII in responses, read-side
gating, retry-cheat via feedback.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 180–189): chase H1–H4.

## Don't re-file (already settled)
- 007, 030, 071, 102, 131 — rejected. 001, 050 — deferred.
- 006, 010, 040, 070, 100, 101, 130, 150, 170 — fixed.
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round) — 0 fixes; exposure surfaces sound, 2 by-design items logged
- **H1 — refuted.** Comprehension list/get hide answers (single-set hiding already has a
  test); no answer markers in assessment tasks or exam blueprints.
- **H2 — refuted.** `auth/me` returns id/email/display_name only — no hash/salt; by-id
  endpoints stay owner-scoped (round 4). No PII leak.
- **H3 — confirmed → issue 181 (rejected).** A locked lesson's content is readable, but
  content isn't secret, completion is gated on write (qa-006), and it's client-presentation
  like qa-071. No change.
- **H4 — confirmed → issue 180 (deferred).** Submit feedback reveals the answer key,
  enabling a known-answer retry that earns XP. Real, but the reveal is intended learning
  feedback and the stake is self-inflicted practice XP — any fix hurts pedagogy. Deferred.

Net: the data-exposure surfaces are sound; the two "exposures" found are by-design
learning/presentation choices, logged with the gate's reasoning so they aren't re-filed.