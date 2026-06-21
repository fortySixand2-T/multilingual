---
id: 130
title: display_name has no maximum length — a huge name floods the shared board
severity: medium
area: auth
persona: edge-case-breaker
status: done
found: 2026-06-20
---

## Steps to reproduce
1. `POST /auth/signup` with a 20,000-character `display_name`.
2. `GET /progress/board`.

## Expected
A sane cap (a display name is short); oversize input is rejected.

## Actual
`201`, and the board renders a 20,000-char name — bloating every member's board response
and breaking the leaderboard UI for the whole group. Found via round-007 H2.

## Notes
Earlier rounds added `min_length`/normalization to auth strings but never a `max_length`.

## Triage
- Explanation: `display_name` was `StringConstraints(strip_whitespace=True, min_length=1)`
  with no upper bound; the board echoes it to everyone.
- Against spec: it's a shared group surface; one member shouldn't be able to degrade it.
- Verdict: validated
- Rationale: cheap, reachable shared-surface abuse (UI break + response bloat for all).

## Critic
- Challenge: would a friend really paste a 20 KB name?
- Holds up? It's a one-line cap and the downside (a broken shared board) hits everyone, so
  bounding it is clearly right — same hygiene as the min_length we already enforce.
- Final verdict: validated

Fix: `max_length=80` on the `display_name` constraint (`app/api/auth.py`; test
`test_signup_rejects_oversized_display_name`). Verified live: 81 chars → 422, 80 → 201.
