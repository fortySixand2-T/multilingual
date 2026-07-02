---
id: 416
title: GET /exam/blueprints/{id} not registered — SPA catch-all returns HTTP 200 HTML
severity: high
area: exam
persona: edge-case-breaker
status: rejected
found: 2026-07-01
---

## Steps to reproduce
1. Sign up and get a valid auth token.
2. `GET /exam/blueprints/b1-mock-1` with `Authorization: Bearer <token>`.
3. Observe HTTP status code and Content-Type.

Alternatively (no auth):
1. `GET /exam/blueprints/nonexistent-id` with no auth header.
2. Observe HTTP status code and Content-Type.

```
# With valid auth, real blueprint ID:
curl -s -o /dev/null -w "HTTP=%{http_code} CT=%{content_type}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:9000/exam/blueprints/b1-mock-1"
# => HTTP=200 CT=text/html; charset=utf-8

# With valid auth, nonexistent blueprint ID:
curl -s -o /dev/null -w "HTTP=%{http_code} CT=%{content_type}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:9000/exam/blueprints/nonexistent-id"
# => HTTP=200 CT=text/html; charset=utf-8

# No auth, no such blueprint:
curl -s -o /dev/null -w "HTTP=%{http_code} CT=%{content_type}\n" \
  "http://127.0.0.1:9000/exam/blueprints/nonexistent-id"
# => HTTP=200 CT=text/html; charset=utf-8
```

## Expected
- `GET /exam/blueprints/{id}` with auth and a valid ID should return HTTP 200 with the blueprint JSON (`application/json`).
- With auth and an invalid ID, should return HTTP 404 JSON.
- Without auth, should return HTTP 401 JSON (the route exists, auth check fires first).

## Actual
All three cases return HTTP 200 with `Content-Type: text/html; charset=utf-8` containing the SPA's `index.html`. The backend has no `GET /exam/blueprints/{id}` route registered. The only blueprint-related route is `GET /exam/blueprints` (list, requires `?level=` query param). Any request to `GET /exam/blueprints/<anything>` bypasses all API handlers and falls through to the SPA catch-all (`GET /{full_path:path}` → `index.html`).

Confirmed via OpenAPI spec — `/exam/blueprints/{id}` is absent:
```
/exam/attempts/{attempt_id}
/exam/blueprints               ← list only
/exam/history
/exam/start
/exam/{attempt_id}/finish
/exam/{attempt_id}/section
```

## Notes
- API clients that try to fetch a blueprint by ID (e.g. to show its title/description before starting) get HTTP 200 with HTML. A JSON parser will throw; an HTML-aware client will silently display a blank page.
- This also means auth is never checked for this path: an unauthenticated request to `/exam/blueprints/b1-mock-1` gets 200 HTML instead of 401.
- The fix is to add a `GET /exam/blueprints/{id}` route in the exam router that looks up the blueprint by id and returns it, or a 404 if not found. The frontend SPA routes may already be linking to this path expecting it to resolve.
- Contrast with `GET /comprehension/sets/{set_id}` which IS registered and returns proper 404 JSON for missing IDs.

## Triage
- Explanation: `GET /exam/blueprints/{id}` is not registered in `app/exam/api.py`. The only blueprint route is `GET /blueprints` (list, requires `?level=`). When a request arrives for `/exam/blueprints/<anything>`, no API handler matches, so the SPA catch-all in `app/main.py` (`GET /{full_path:path}`) fires and returns `index.html` with HTTP 200 and `text/html` — confirmed by live reproduction.
- Against spec: The spec (`TEF_Platform_Technical_Plan.md` Phase 5) never specifies a `GET /exam/blueprints/{id}` detail endpoint. The designed flow is: list blueprints (`GET /blueprints?level=`) → start exam via `POST /start` (which returns the full blueprint object inline). The frontend (`web/src/api.ts`) follows this exact flow and never calls a detail endpoint. No client code is broken.
- Verdict: rejected
- Rationale: Working as designed — the spec does not require a blueprint detail route, `POST /exam/start` returns blueprint data inline, and no current client calls this path. The SPA catch-all returning HTML for an unregistered path is the intended fallback behavior for client-side routing, not a bug.

## Critic
- Challenge: The reporter labeled this "high severity" and raises a real observation: any HTTP client probing `GET /exam/blueprints/<id>` gets HTTP 200 with HTML instead of a meaningful API error. The auth bypass angle (unauthenticated request gets 200 HTML instead of 401) could be read as a security gap, and the SPA catch-all silently masking missing routes is a pattern that could hide future regressions. One could argue "deferred" is more honest than "rejected" — acknowledge the gap exists even if it is not urgent. Against this: (1) `GET /exam/blueprints/{id}` is absent from the TEF_Platform_Technical_Plan.md spec at every phase, including Phase 5 where exam simulation is defined. (2) Independent verification confirms the frontend (`web/src/api.ts`, `web/src/screens/Exam.tsx`) never calls this path — it uses the list endpoint then POST /exam/start, which returns the full blueprint inline. No client code, planned or existing, calls a detail route. (3) The SPA catch-all at `app/main.py:72` is explicitly documented as intentional client-side routing fallback. The "auth bypass" framing is misleading: auth is not bypassed on a route that does not exist and is not required to exist — there is nothing to protect. (4) The platform is a closed system for ~5 users on a private Tailscale network; the "third-party API client" scenario the issue implies is not a realistic concern and was not an architectural target. (5) The severity label "high" is self-inflicted by the edge-case-breaker persona — it reflects the QA testing posture, not actual user impact. No learner workflow is broken or degraded.
- Holds up? Yes. The PM's rejection stands on all three axes: spec alignment (never required), code verification (no caller exists), and design intent (SPA catch-all is documented behavior). "Deferred" would be wrong here because deferred implies a planned feature that is postponed — this route was never planned. The distinction between "missing feature" and "unregistered route" only matters if there is a consumer; there is none. The rejection is accurate and conservative.
- Final verdict: rejected
