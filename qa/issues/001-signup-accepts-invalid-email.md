---
id: 001
title: Signup accepts an invalid email format
severity: medium
area: auth
persona: edge-case-breaker
status: open
found: 2026-06-16
---

## Steps to reproduce
1. `POST /auth/signup` with `{"email":"not-an-email","password":"pw123456","invite_code":"friend-001","display_name":"X"}`

## Expected
422 with a clear "enter a valid email" message; the account is not created.

## Actual
`HTTP 201` — account created and a token issued for `not-an-email`.

## Notes
`SignupRequest.email` is typed `str` (EmailStr was dropped to avoid the
`email-validator` dep). Either add `email-validator` + `EmailStr`, or a light
regex check in the signup route. Login keys on email, so junk emails are now
valid accounts.
