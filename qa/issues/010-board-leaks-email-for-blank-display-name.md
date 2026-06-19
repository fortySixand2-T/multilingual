---
id: 010
title: Group board exposes a user's email when their display name is blank
severity: high
area: progress
persona: edge-case-breaker
status: done
found: 2026-06-19
---

## Steps to reproduce
1. `POST /auth/signup` with `display_name: ""` (accepted, 201).
2. `GET /progress/board`.

## Expected
The shared board never shows anyone's email address.

## Actual
The blank-name user appears on the board as their **email** (`noname@secret.com`),
visible to the whole group. Found via round-003 hypothesis H3.

## Notes
`get_board` rendered `u.display_name or u.email`, and `SignupRequest.display_name`
defaulted to `""` with no constraint — so any blank name leaked the email to everyone.

## Triage
- Explanation: two seams — signup accepts an empty `display_name` (`app/api/auth.py`),
  and the board falls back to email when it's empty (`app/progress/api.py` `get_board`).
- Against spec: the platform is a closed group, but emails are still PII and the board is
  its most-shared surface; data minimization is a stated value. Unintended disclosure.
- Verdict: validated
- Rationale: a real, reachable PII leak to every group member. High.

## Critic
- Challenge: it's 5 friends who already know each other's emails — is exposure real harm?
- Holds up? Yes. "They might already know" doesn't license the app to publish PII on a
  shared screen, and the fix is trivial. Two-line defense, no complexity added.
- Final verdict: validated

Fix: signup now requires a non-blank `display_name` (`StringConstraints(strip_whitespace,
min_length=1)`) and the board falls back to `"Learner"`, never email — so neither new nor
legacy blank rows can leak (`app/api/auth.py`, `app/progress/api.py`; tests
`test_signup_rejects_blank_display_name`, `test_board_never_exposes_email`). Verified live:
blank/whitespace/missing → 422, board shows no emails.
