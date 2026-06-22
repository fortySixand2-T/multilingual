---
id: 200
title: SPA shows raw pydantic JSON for backend validation errors
severity: medium
area: web
persona: edge-case-breaker
status: done
found: 2026-06-21
---

## Steps to reproduce
1. Sign up with a 3-char password (or a blank/over-long display name).

## Expected
A readable message ("password: must have at least 8 characters").

## Actual
The form showed the raw FastAPI body, e.g. `[{"type":"string_too_short","loc":["body",
"password"],...}]`. `api.ts` did `typeof detail === "string" ? detail :
JSON.stringify(detail)`, so every 422 (all the min/max/range checks added in rounds 1–7)
rendered as JSON. The signup form also lacked client-side constraints. Found via round-012
H2.

## Triage
- Explanation: the API client never handled FastAPI's `detail: [{loc,msg,type}]` array
  shape; the form fields had no `required`/`min`/`maxLength` matching the backend.
- Against spec: a learner-facing app must show human errors.
- Verdict: validated — user-facing, hit by ordinary signup mistakes.

## Critic
- Challenge: cosmetic?
- Holds up? It's the visible half of every validation rule we added server-side; raw JSON
  reads as a crash to a non-technical learner. Central, low-risk fix.
- Final verdict: validated

Fix: `api.ts` now parses the validation array into a readable sentence (shared
`readableError`/`errorFrom`, also applied to the speech upload); `Login.tsx` gains
`required`+`maxLength={80}` on display name and `minLength={8}` on the signup password.
Verified: `npm run build` clean; `readableError` over a real 422 body →
"password: String should have at least 8 characters" (string details for 409/403/503 pass
through unchanged).
