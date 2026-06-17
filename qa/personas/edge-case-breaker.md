# Persona: Edge-Case Breaker

The friend who pokes everything. Not malicious — just curious and rough on inputs.
Wants to see what breaks.

**Goal:** find the rough edges and bad failure modes.

**Behaviour:** wrong/blank invite code; duplicate signup; empty or 5,000-word writing
submission; submits a lesson/section twice fast; requests a missing id; calls
endpoints out of order (finish a mock before recording sections); hammers the daily
budget; sends a malformed body; opens a protected page with no/expired token.

**Cares about / will flag:** stack traces or 500s instead of clean 4xx/503, silent
failures, inconsistent state after double-submits, missing ownership checks (seeing
someone else's data), unbounded inputs accepted, confusing or wrong error messages.
