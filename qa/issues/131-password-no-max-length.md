---
id: 131
title: Password has no maximum length (suspected PBKDF2 CPU DoS)
severity: low
area: auth
persona: edge-case-breaker
status: rejected
found: 2026-06-20
---

## Steps to reproduce
1. `POST /auth/signup` with a 500 KB password, timing the request.

## Expected (per the report)
A multi-hundred-KB password makes PBKDF2 burn CPU on every signup/login → cheap DoS.

## Actual
`201` in ~0.07s vs ~0.05s for a normal password. No meaningful CPU cost. Found via
round-007 H1.

## Triage
- Explanation: `password` has `min_length=8` but no `max_length`.
- Against spec: hygiene only.
- Verdict: borderline — could cap for tidiness.

## Critic
- Challenge: the feared DoS doesn't exist. PBKDF2 cost is set by the iteration count; a
  long password is HMAC-hashed once into a fixed-size key, so length barely matters
  (measured 0.07s vs 0.05s). Nothing is stored oversized (only the fixed-size hash). The
  only residual is generic request-body size, which is an infra/proxy concern, not
  password-specific.
- Holds up? Yes — there's no real impact, so adding a validator is tidiness, not a fix,
  and we don't add code for non-issues (CLAUDE.md).
- Final verdict: rejected — no measurable DoS. No change. (A global request-size limit, if
  ever wanted, belongs at the server/proxy layer, not on this field.)
