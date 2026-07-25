---
id: 466
title: Invalid/expired token renders a broken app shell instead of redirecting to login
severity: medium
area: web
persona: returning-learner
status: done
found: 2026-07-25
---

## Steps to reproduce
1. Sign in, so a JWT is stored in `localStorage` under `tef_token`.
2. Invalidate that token without clearing it — e.g. let the **7-day expiry** pass, or
   point the same browser at a server signed with a different `JWT_SECRET` (observed
   live while testing the new build against a local instance).
3. Load `/` (or any in-app route).

## Expected
An invalid/expired token should drop the learner to the **login screen** (a clean
"please sign in again"), the way a normal session timeout behaves.

## Actual
The SPA renders the **full app shell** (top nav: Learn / Vocab / … / Log out) with a
data pane reading **"Couldn't load your path: invalid or expired token"**. The learner
is stuck in a half-rendered, non-functional app: every screen 401s, but nothing sends
them to login. Clicking "Log out" is the only way out (and even that did not always
re-render to the login view on the first click during testing).

## Notes
- Pre-existing; unrelated to the escape-hatch feature — surfaced incidentally during
  the qa/live-round browser testing (the stale funnel-session token failed against a
  local server with a different `JWT_SECRET`).
- Real-user impact: everyone's session is a **stateless 7-day JWT** (no refresh), so
  every learner hits this on day 8 — they'll see a broken shell rather than a login
  prompt.
- Likely fix (frontend): on a `401`/"invalid or expired token" API response, clear
  `tef_token` and route to the login view. Central place: the shared `req()` error
  path in `web/src/api.ts` and/or the auth guard in `web/src/auth.tsx`. A single
  interceptor that treats 401 as "log out + go to /login" fixes it everywhere.
- Related: the 7-day TTL itself (`app/users/auth.py`) — a longer TTL or a sliding
  refresh would reduce how often this is hit, but the redirect should be fixed
  regardless.

Fix: `req()`/`fetchAudioUrl` clear the token and fire a `tef:unauthorized` event on a
401 for an authenticated request; `AuthProvider` listens and drops to the login view
(web/src/api.ts, web/src/auth.tsx; tests web/src/api.test.ts).
