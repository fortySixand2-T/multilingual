---
id: 300
title: POST /content/vocab/known accepts string values for boolean field
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-06-23
---

## Steps to reproduce
1. Sign up and obtain an auth token.
2. POST /content/vocab/known with `{"card_key":"bonjour","known":"yes"}` (string, not boolean).
3. Observe the response.
4. Repeat with `{"card_key":"eau","known":"no"}`.

## Expected
A 422 validation error, since `known` should be a boolean (`true`/`false`), not a string.

## Actual
- `"yes"` is silently coerced to `true` and returns HTTP 200.
- `"no"` is silently coerced to `false` and returns HTTP 200.
- Meanwhile `""`  and `42` correctly return 422.

This is Pydantic's default `bool` coercion (accepts "yes"/"no"/"true"/"false"/"on"/"off"/"1"/"0" as strings). Using `StrictBool` would enforce only actual JSON booleans.

## Notes
- Not a security issue or data-corruption risk since the coercion is predictable.
- Inconsistent: strings like "yes" are accepted while integer 42 is rejected, which could confuse API consumers.
- Fix: change the Pydantic model field from `bool` to `StrictBool`.

## Triage
- Explanation: The `KnownBody` Pydantic model at `app/content/api.py:181` declares `known: bool`. Pydantic v2's default `bool` validator accepts truthy/falsy strings ("yes"/"no"/"true"/"false"/"on"/"off"/"1"/"0") and coerces them to `True`/`False`. This is standard, documented Pydantic behavior, not a bug in our code.
- Against spec: The spec (`TEF_Platform_Technical_Plan.md`) selects Pydantic v2 as the validation layer but says nothing about requiring StrictBool or strict type coercion on boolean fields. No strictness policy is defined for request body types.
- Verdict: rejected
- Rationale: Working as designed. The only real consumer (the SPA at `web/src/api.ts:264`) already sends proper JSON booleans. The coercion is deterministic and harmless -- no data corruption, no security risk, no user-facing confusion. Adding StrictBool would be unnecessary strictness with no real-world benefit and would risk breaking any future lenient clients for zero gain.

## Critic
- Challenge: Could a real user or legitimate API consumer actually hit this? The SPA is the sole consumer (TypeScript-typed `known: boolean` at `web/src/api.ts:264`, serialized via `JSON.stringify`), so string booleans are unreachable through normal use. The spec defines no public API contract and no strict-typing policy. Pydantic v2 bool coercion is documented, deterministic behavior -- "yes" always becomes `true`, "no" always becomes `false`. The stored data is correct either way. Adopting StrictBool here would set an unjustified precedent requiring Strict variants on every field across the API, adding complexity with zero user-facing benefit.
- Holds up? Yes. The PM's rejection survives. This is a type-purity concern reachable only by API tampering, with no impact on real users, no data risk, and no spec violation. The conservative default (no change) applies.
- Final verdict: rejected
