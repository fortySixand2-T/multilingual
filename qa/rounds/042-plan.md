# QA round 042 — plan

- date: 2026-07-26
- app under test: backend + built SPA, single-origin (each browser tester boots its own
  uvicorn per the qa-browser-tester runbook, e.g. :8123 / :8124)
- scope: **web-only nav redesign on `feat/web-home-hub-nav`** — "Home hub + slim nav".
  Purely presentational (no routes/logic changed): topbar cut from 12 pills to 4
  (Learn/Review/Mock/Group), the other 8 moved into a new "Practice & tools" grid on
  the Path (home) screen, and the old mobile nav-scroll CSS hack was removed in favor
  of a 2-up grid. Weight this round toward UX/visual/reachability, not backend.

## Change surface (highest risk first)
1. `web/src/screens/Path.tsx` — new `<nav className="tool-grid">` of 8 `NavLink` cards
   (Vocab, Grammar, Drill, Read & Listen, Write, Speak, Weak spots, Readiness), inserted
   between the streak/XP header and the unit list. This is the **only** way to reach
   those 8 screens now — a broken card = an unreachable feature.
2. `web/src/App.tsx` — topbar trimmed to 4 `NavLink`s (Learn `/`, Review `/review`,
   Mock `/exam`, Group `/board`). All 12 `<Route>` definitions are untouched, so any
   reachability break must come from the nav markup, not routing.
3. `web/src/styles.css` — new `.tool-grid`/`.tool-card` rules (4-up desktop → 2-up
   `@media (max-width:640px)`), and the prior nav horizontal-scroll hack was **deleted**.
   Mobile topbar now relies on `flex-wrap` + `.nav { order: 3; width: 100% }` instead.

## Pre-check done by planner (don't re-verify, already confirmed by reading source)
- `react-router-dom@6.26` `NavLink`: when `className` is a plain string (as both
  `App.tsx`'s and `Path.tsx`'s `NavLink`s use it), the library still auto-appends
  `active`/`pending` — confirmed in `node_modules/react-router-dom/dist/react-router-dom.development.js:888-898`.
  So "hub card never gets `.active` because className is a static string" is **refuted
  by source** — testers don't need to hunt this specific mechanism, just *visually*
  confirm the active highlight actually shows on the right card/topbar item (a mismatch
  could still exist for other reasons, e.g. `/vocab/:level/:tag` sub-routes not
  highlighting the `/vocab` card since the `NavLink` has no `end={false}` issue here —
  worth a quick look at H2).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | reachability | All 8 hub cards navigate to their intended, working screen. Highest risk: a copy/paste `to=` mismatch in the `TOOLS` array (`Path.tsx:6-14`) sends a card to the wrong route, or one of the 8 destination screens itself errors/blank-renders when entered via the new path (vs. the old topbar path — same route, so should be identical, but worth confirming no console error). | Click each of the 8 tool-grid cards from Path; confirm URL + screen match the label (Vocab→/vocab, Grammar→/grammar, Drill→/drill, Read & Listen→/comprehension, Write→/writing, Speak→/speaking, Weak spots→/weak-spots, Readiness→/readiness). Check for console errors on each. | returning-learner |
| H2 | active state | Topbar active highlight still correct for the 4 remaining items (Learn/Review/Mock/Group), including that visiting a hub-only screen (e.g. `/vocab`) correctly shows **none** of the 4 topbar items as active (no stale highlight held over). Hub grid: the active card highlights on its own screen and un-highlights elsewhere; check a nested route like `/vocab/:level/:tag` (Deck) still highlights the `/vocab` card (NavLink default `end=false` should keep it active — confirm it does, not just assume). | Navigate through Learn→Review→Mock→Group and observe topbar highlight moves correctly each time and never shows 2 active or 0 active incorrectly. From Path, click into a vocab deck (drill into `/vocab/:level/:tag`) and check the Vocab card would still read active if you navigated back to a grid (can't see grid while inside the deck — instead confirm returning to `/vocab` highlights correctly, and check via browser back button). | returning-learner |
| H3 | responsive/mobile | The whole point of this redesign was decluttering; a regression here defeats the purpose. Resize to a phone viewport (~375×812 and a narrower 320×568) and check: topbar wraps to brand+level-switcher+logout on row 1, full-width 4-item nav on row 2, no horizontal overflow/scrollbar anywhere (the old scroll hack is gone — if anything still overflows, there's no more fallback). Tool grid drops to 2 columns; check the longer labels ("Read & Listen", "Weak spots") don't clip/overflow their card, and the emoji+label stay centered and legible. | Use browser device emulation / resize to 375px and 320px widths on the Login, Path (home hub), and one hub destination screen. Screenshot each; look for clipped text, overlapping controls, horizontal scrollbars, or cards that break out of the 2-col grid. | edge-case-breaker |
| H4 | regression | Path screen still renders correctly around the new grid: unit list, streak (🔥) and XP (⭐) pills in the header, lesson locked/passed/waived states, and the grid doesn't push/overlap the unit list oddly. Also confirm nothing else on the home screen (loading state, error state when `api.path` fails) broke by the insertion. | Load Path as a learner with some progress; confirm header pills show real streak/XP, grid renders above the units, units below render normally (locked/passed/waived icons), and scrolling the page feels normal (grid doesn't overlap or push units off oddly at 4-up or 2-up). | returning-learner |
| H5 | discoverability (soft) | A first-time / beginner user lands on Path and must find features via cards, not topbar text — not a code bug, but worth a UX read: are the 8 icons+labels legible/self-explanatory enough that the persona doesn't get stuck, and is there any dead click (card looks clickable but isn't, or vice versa e.g. a `.unit` row now visually confused with a `.tool-card`)? | As a beginner landing on Path, describe first impression: is the hub grid obviously separate from the unit path, are labels enough without needing the old flat nav for orientation? File only if genuinely confusing (e.g. cards indistinguishable from decoration), not as a taste preference. | absolute-beginner |

## Coverage gaps
- No prior issue history touches `Path.tsx`'s new grid or the topbar trim — this is the
  first round exercising the hub-nav design at all.
- `qa/FRONTEND_TEST_GAP.md` (if present) already flags the SPA as under-covered by
  automated tests generally — this round is browser-driven QA, not a substitute for
  the missing Vitest/Playwright coverage of `Path.tsx`'s new markup.

## Charters (per tester, with id blocks)
Both browser-driven — this is a pure UI change; no HTTP/curl tester needed (no route,
gating, or data-shape changes to probe below the UI).
- **`qa-browser-tester` as `returning-learner`** (ids 470–479): H1 (all 8 hub-card
  destinations reachable + no console errors), H2 (active-state correctness, topbar
  and hub card, including the `/vocab` nested-route case), H4 (Path regression check —
  streak/XP header + unit list intact around the new grid).
- **`qa-browser-tester` as `edge-case-breaker`** (ids 480–489): H3 (375px and 320px
  viewport check across Login/Path/a hub destination — overflow, wrapping, broken
  2-col grid, since the old scroll-hack fallback is gone).
- **`qa-browser-tester` as `absolute-beginner`** (ids 490–499): H5 (first-look
  discoverability/clarity of the new hub grid) — light-touch, file only real confusion,
  not preference.

Each spins its own uvicorn per the standard runbook (pick a free port, avoid 9000);
they all rebuild the same `web/src/` sources so a stale/incomplete `npm run build` isn't
a false positive — if a tester sees something that looks like a build artifact issue,
it should rebuild once and recheck before filing.

## Don't re-file (already settled)
- Drill / Writing grading / Speaking 503 with no LLM/STT/TTS provider configured —
  expected known limitation, not in scope for this round.
- `NavLink` string-className losing the `active` class — refuted by reading
  `react-router-dom` source (see pre-check above); don't file this specific theory.
- Any backend/API/data issue unrelated to `web/src/App.tsx`, `Path.tsx`, or
  `styles.css` — out of scope for this purely presentational round.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
