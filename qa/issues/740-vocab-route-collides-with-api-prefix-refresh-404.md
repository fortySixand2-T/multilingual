---
id: 740
title: Refreshing or deep-linking any /vocab* URL returns raw JSON 404 instead of the app
severity: high
area: web
persona: returning-learner
status: done
found: 2026-09-07
---

## Steps to reproduce
1. Sign in, go to Learn → Vocab (URL becomes `http://<host>/vocab`).
2. Open any new deck, e.g. B1 → Food (URL becomes `http://<host>/vocab/b1/food`).
3. Reload the page (F5 / hard refresh), or open that exact URL in a new tab, or
   `curl -i http://127.0.0.1:9101/vocab/b1/food`.

## Expected
Same as every other screen in the app (e.g. `/review`, which returns the SPA shell
with HTTP 200 `text/html` on a direct load) — the deck screen re-renders normally
after a refresh, or at minimum the SPA loads and client-side routing takes over.

## Actual
The server returns `HTTP/1.1 404 Not Found` with `Content-Type: application/json` and
body `{"detail":"Not Found"}` — a bare JSON error page, no app shell, nothing
clickable. This reproduces for the bare `/vocab` listing page too, not just deck
subpaths:

```
curl -sv http://127.0.0.1:9101/vocab/b1/food
< HTTP/1.1 404 Not Found
< content-type: application/json
{"detail":"Not Found"}

curl -sv http://127.0.0.1:9101/vocab
< HTTP/1.1 404 Not Found
< content-type: application/json
{"detail":"Not Found"}

curl -sv http://127.0.0.1:9101/review
< HTTP/1.1 200 OK
< content-type: text/html; charset=utf-8
```

I hit this navigating in the real browser too (not just curl): loading
`http://127.0.0.1:9101/vocab/b1/food` directly in a new tab renders a plain black
page with the literal text `{"detail":"Not Found"}` — no header, no nav, no way back
into the app except editing the URL.

## Notes
- Root cause (read for context, not to hand you the fix): `app/main.py`'s SPA
  catch-all (`_mount_spa`) computes `api_prefixes` as the set of first path segments
  owned by any registered API router, and returns JSON 404 for any request whose
  first segment matches one of those prefixes (so real API 404s don't get masked as
  HTML). The frontend's own client-side routes `/vocab` and `/vocab/:level/:tag`
  (`web/src/App.tsx`) collide with the backend's `/vocab` prefix (`GET /vocab`,
  `POST /vocab/known` in `app/content/api.py`, and `APIRouter(prefix="/vocab", ...)`
  in `app/content/vocab_extra_api.py` and `app/content/personal_api.py`). Any
  full-page load of `/vocab*` therefore never reaches `index.html`.
- This is pre-existing routing logic (not part of this round's content diff), but it
  directly breaks the exact screens this round is exercising at new scale (83 decks).
  A returning learner who bookmarks a deck, shares a deck link with a study buddy, or
  simply hits refresh mid-session while on Vocab/Deck lands on a dead JSON page and
  has to know to manually navigate back to `/` — a beginner would likely think the
  site is broken.
- Contrast: `/review`, `/learn` (root), `/mock`, `/group` all load fine on direct
  navigation since their first path segment isn't an API prefix.
- Filed as `high` (not blocker) because in-app client-side navigation to Vocab/Deck
  works perfectly — this only bites on refresh/deep-link/bookmark, not the primary
  click-through flow — but it's a real, easily-hit dead end for exactly the feature
  under test this round.

## Triage
- Explanation: Confirmed exactly as reported — `curl -i http://127.0.0.1:9101/vocab/b1/food`, `/vocab`, and (also verified live) `/vocab/b2/justice` all return `404` with `{"detail":"Not Found"}` and `content-type: application/json`, while `/review` returns `200 text/html`. Browser reproduction confirmed the same: navigating directly to `/vocab/b2/justice` or `/vocab` via the URL bar (full page load, not client-side routing) renders the raw JSON, not the app shell. Root cause matches the reporter's own read of `app/main.py`'s `_mount_spa`: `api_prefixes` is derived from every registered API router's first path segment, and `/vocab` is a real, distinct API prefix (`GET /vocab`, `POST /vocab/known` in `app/content/api.py`; `APIRouter(prefix="/vocab", ...)` in `app/content/vocab_extra_api.py` and `app/content/personal_api.py`). The SPA catch-all correctly treats any unmatched `/vocab/*` path as a genuine API 404 rather than falling through to `index.html`, because the frontend's client-side route `/vocab` and `/vocab/:level/:tag` happen to share the same first path segment as the backend's real `/vocab` API prefix.
- Against spec: Unspecified in the technical plan (routing/SPA-serving mechanics predate this content round entirely), but it directly contradicts the app's own established behavior for every other screen — `/review`, `/learn` (root), `/mock`, `/group` all correctly serve the SPA shell on a direct load specifically because their first path segment isn't also an API prefix. `/vocab` is the one frontend route that collides.
- Verdict: validated
- Rationale: Pre-existing routing bug (not introduced by the vocab-expansion content commit, confirmed — no app code changed in 810b992), but it's a real, easily-triggered dead end (refresh, deep link, bookmark, share) hitting exactly the surface this round put in front of users at new scale (83 decks now actively encouraging exploration). A returning learner who refreshes mid-deck or shares/bookmarks a deck link lands on a raw JSON page with no way back except editing the URL — that's a genuine UX break, not a cosmetic one, so `high` is appropriate. Fix belongs in `app/main.py` (e.g. carve out an exception for `/vocab` and `/vocab/:level/:tag` full-page GETs specifically, or namespace the frontend/backend prefixes apart) — out of scope for this triage to prescribe, but real and worth fixing.

## Critic
- Challenge: This is "pre-existing routing logic" per the reporter's own notes — is it possibly already a known, accepted limitation elsewhere in the app that this round is just re-discovering under a new name, in which case filing it against `/vocab` specifically (and marking it `high`) overstates both the novelty and the severity?
- Holds up? Partially — the novelty claim doesn't hold, but the underlying bug does. Cross-checking every frontend route (`web/src/App.tsx`) against every registered API prefix (`grep -rn "APIRouter(prefix" app/`) shows this collision isn't unique to `/vocab` at all: `/comprehension` and `/exam` are both first-class SPA routes *and* real API prefixes, so they have the identical defect. Live-curled to confirm: `GET /comprehension` and `GET /exam` both return `404 application/json` on this running instance, exactly like `/vocab`. `git log` shows the `comprehension` and `exam` API routers have existed since Phase 1/2 (months before this round), and round 029's plan explicitly tested the SPA catch-all's "shadows API 404s" behavior (H7) and found only the *opposite* problem at the time (an unregistered nested path serving HTML 200 instead of JSON 404, filed as #416, rejected as by-design) — meaning the `api_prefixes`-based JSON-404 guard in `_mount_spa` was added *after* round 029, specifically to close that gap, and this refresh-breaks-the-page regression is very likely an unintended side effect of that later fix. No prior round ever filed a `/comprehension` or `/exam` refresh-404 issue despite the bug existing on those routes the whole time, which shows real-world impact has stayed low for months on a small, mostly-click-through user base — but "nobody hit it" is not the same as "accepted by design": there's no code comment, plan note, or prior triage saying full-page loads of `/comprehension`/`/exam`/`/vocab` are intentionally excluded from the SPA shell, and the browser repro here (`/vocab/b2/justice` full navigation renders raw `{"detail":"Not Found"}`, no header, no nav) confirms it's a real, visible break for a learner, not a theoretical one. That the same defect quietly affects two other pre-existing routes actually strengthens the case for a fix — one routing-layer change (e.g. matching against registered frontend routes, or only 404-ing paths with no matching SPA route) fixes three screens at once, and vocab's newly-expanded surface makes it more likely to be hit now than it was on the older routes. `high` remains defensible given the direct, unrecoverable dead-end for a real navigation pattern (refresh/bookmark/share); it is not overstated by the fact that it's shared with two other routes — if anything, three broken deep-linkable feature areas argues against downgrading.
- Final verdict: validated

## Fix
Fix: `app/main.py`'s `_mount_spa` catch-all now carves out the exact shapes of
the frontend SPA routes that collide with an API prefix (`/vocab`,
`/vocab/:level/:tag`, `/comprehension`, `/comprehension/:id`, `/exam`) and
serves the SPA shell for those before falling back to the original
first-segment `api_prefixes` check — so a genuinely unmatched/deeper path
under an API prefix (e.g. `/exam/blueprints/does-not-exist`, QA #416) still
404s as JSON. Verified live: `/vocab`, `/vocab/b1/food`, `/comprehension`,
`/comprehension/xyz`, `/exam` all now return `200 text/html` with the SPA
shell, while `/exam/blueprints/does-not-exist` still returns `404
application/json`. Regression test added in `tests/test_spa_serving.py`
(`test_spa_route_colliding_with_api_prefix_serves_shell`); full backend
suite green (326 passed, 1 skipped).
