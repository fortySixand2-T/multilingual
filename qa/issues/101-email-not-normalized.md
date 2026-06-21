---
id: 101
title: Email isn't normalized — casing/whitespace creates duplicate accounts
severity: medium
area: auth
persona: returning-learner
status: done
found: 2026-06-19
---

## Steps to reproduce
1. `POST /auth/signup` with `email: "Casing@x.com"`.
2. `POST /auth/signup` with `email: "casing@x.com"`.

## Expected
The second is the same account → 409, and login works regardless of casing/whitespace.

## Actual
Both return 201 — two separate accounts. A learner who signs up as `Bob@x.com` but later
logs in as `bob@x.com` can't be found (login keys on the exact stored string). Found via
round-006 H3.

## Triage
- Explanation: `SignupRequest.email`/`LoginRequest.email` stored/looked-up verbatim — no
  case-fold or trim, so casing variants are distinct keys.
- Against spec: emails are identifiers for a closed group; they should be canonical.
- Verdict: validated
- Rationale: real account-fragmentation + login-failure for ordinary casing differences.

## Critic
- Challenge: do 5 friends really vary their email casing?
- Holds up? Yes — phones autocapitalize the first letter, and a trailing space is common.
  The fix is a one-line normalizer shared by both models. Cheap, clearly correct.
- Final verdict: validated

Fix: a shared `NormalizedEmail = Annotated[str, AfterValidator(strip+lower)]` applied to
both signup and login, so they key on the same canonical value (`app/api/auth.py`; test
`test_email_is_normalized_for_signup_and_login`). Verified live: cased re-signup → 409,
any-case login → 200.
