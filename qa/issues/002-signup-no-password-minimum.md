---
id: 002
title: Signup accepts a trivially weak password (no minimum length)
severity: medium
area: auth
persona: edge-case-breaker
status: open
found: 2026-06-16
---

## Steps to reproduce
1. `POST /auth/signup` with `{"email":"x3@test.com","password":"1","invite_code":"friend-001","display_name":"X"}`

## Expected
422 rejecting a too-short password (e.g. minimum 8 chars), with a clear message.

## Actual
`HTTP 201` — account created with password `"1"`.

## Notes
`SignupRequest.password` has no constraint. Add `min_length` (pydantic
`Field(min_length=8)`) on the signup model. Low security bar for a shared login.
