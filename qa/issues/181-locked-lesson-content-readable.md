---
id: 181
title: A locked lesson's content is readable (gating not enforced on read)
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-06-20
---

## Steps to reproduce
1. As a fresh user (u2 locked), `GET /content/lessons/cafe-01`.

## Actual
`200` with the full lesson, including exercise answers, even though the path shows the
unit `locked`. Completing it is still blocked (`POST .../result` → 409, qa-006). Found via
round-010 H3.

## Triage
- Explanation: `get_lesson` returns `lesson.data` for any existing id; gating is computed
  only for the path display and enforced on the result write (qa-006), not on read.
- Against spec: lessons aren't secret content; the progression control is *completion*.
- Verdict: borderline.

## Critic
- Challenge: reading ahead in a self-study app harms only the reader (a spoiler); the
  curriculum control that matters — earning completion/XP/unlocks — is enforced on write
  (qa-006). Same shape as qa-071 (no-replay): the path/UI gates presentation, the API
  serves content. Gating reads would block legitimate preview for no real benefit, and
  lesson answers are already exposed by design for offline grading (qa-050).
- Holds up? Yes — no protected resource, no integrity/shared-state harm.
- Final verdict: rejected — client/UI-enforced presentation by design. No change.
