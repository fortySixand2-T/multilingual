---
id: 470
title: Practice & tools grid "active" highlight can never render (dead code)
severity: low
area: web
persona: returning-learner
status: rejected
found: 2026-07-26
---

## Steps to reproduce
1. Sign in, land on the Path/home screen (`/`).
2. Inspect `web/src/screens/Path.tsx`: the tool-grid `<nav className="tool-grid">` with its 8
   `NavLink` cards (Vocab, Grammar, Drill, Read & Listen, Write, Speak, Weak spots, Readiness) is
   rendered only inside `Path`, which is mounted exclusively at route `/` (`<Route path="/"
   element={<Path />} />` in `web/src/App.tsx`).
3. None of the tool-grid card targets (`/vocab`, `/grammar`, `/drill`, `/comprehension`,
   `/writing`, `/speaking`, `/weak-spots`, `/readiness`) equal `/`, so `NavLink`'s `isActive` is
   always `false` for every card while `Path` is mounted.
4. Because none of the 8 destination screens (Decks, Grammar, Drill, Comprehension, Writing,
   Speaking, WeakSpots, Readiness) re-render the tool-grid themselves (confirmed: no `tool-grid`/
   `NavLink` usage in `Decks.tsx` or `Deck.tsx`, and the other screens don't import it either),
   there is no route at which a tool-grid card can ever show the `.tool-card.active` style.
5. Verified in the browser: from Path, every card renders unhighlighted; navigating into any of
   the 8 tools and back to Path never shows a highlighted card, confirming the CSS rule is dead.

## Expected
`web/src/styles.css` defines `.tool-card.active { border-color: var(--green); background:
#eaf6ee; }`, implying the intent (matching the H2 "active card" hypothesis for this round) is that
the card for whichever tool you're currently on should be visually highlighted — e.g. so a user
who is on `/vocab` and navigates back sees which hub they came from, or so the grid gives "you are
here" feedback consistent with the topbar pills.

## Actual
The highlight can never appear under any navigation path, because the component that owns the
grid (`Path`) is unmounted the instant the user leaves `/`. The `.tool-card.active` CSS rule and
NavLink `isActive` plumbing are effectively unreachable dead code — not a crash, but a
presentational feature that silently does nothing per design/implementation mismatch.

## Notes
Not a regression from the nav slim-down itself (topbar's 4 pills highlight correctly, verified: Learn/Review/Mock/Group each highlight only when active, and none are stale-highlighted on hub-only screens like /vocab). This is specific to the new tool-grid added in the redesign. Low severity since it's cosmetic/inert rather than broken navigation — reachability (H1) and routing all work correctly. Fix would require either moving the grid into a persistent layout shell (so it stays mounted across routes) or removing the unused `.tool-card.active` CSS if no highlight was actually intended.

## Triage
- Explanation: `Path.tsx` renders `<nav className="tool-grid">` with 8 `NavLink`s, mounted
  only at `App.tsx`'s `<Route path="/" element={<Path />} />`. React Router v6.26's
  `NavLink` (verified directly in `node_modules/react-router-dom/dist/react-router-dom.development.js`,
  the `isActive` computation) auto-appends `active` when `classNameProp` is a static
  string — so the round-042 plan's pre-check that this mechanism *isn't* broken is
  correct. But that's not what's happening here: `isActive` is computed by comparing
  `location.pathname` against each card's own `to`. Since Path only ever renders while
  `location.pathname === "/"`, and none of the 8 `to` values (`/vocab`, `/grammar`, …)
  equal `/`, every card's `isActive` is `false` for as long as the grid exists in the
  DOM. Confirmed empirically in-browser: `document.querySelectorAll('.tool-card')` on
  `/` returns `className: "tool-card"` for all 8 (no `active` suffix ever appended),
  and the grid is entirely absent from the DOM on `/vocab` (`Path` unmounted, nothing
  else renders `.tool-grid`). So `.tool-card.active` in `styles.css:177` is genuinely
  unreachable CSS — not the specific "static className kills auto-active" theory the
  round-042 plan pre-refuted, but a distinct, real architectural gap (grid only mounted
  where none of its own links can be active).
- Against spec: `qa/rounds/042-plan.md` H2 explicitly asks whether "the active card
  highlights on its own screen and un-highlights elsewhere" — this is exactly the
  behavior that fails. The CSS comment/rule was clearly intended to give "you are here"
  feedback consistent with the topbar pills (which do work, since Learn/Review/Mock/Group
  stay mounted across all routes via the persistent `header/topbar`). Not addressed by
  round-042's "don't re-file" list, which only refutes the unrelated className-string
  theory.
- Verdict: validated
- Rationale: Low-severity but real — a shipped, styled `.active` state that can never
  render under any navigation path is dead code masquerading as a feature; a returning
  learner gets no "you are here" cue from the hub grid the way they do from the topbar,
  a minor but genuine inconsistency in the redesign's own stated goal (H2). Fix is
  architectural (persist the grid outside `Path`, e.g. in a layout shell, or drop the
  unused CSS) — leaving as a low-priority follow-up is reasonable.

## Critic
- Challenge: The grid is a launcher that renders *only* on `/`, by design — it's never
  shown on `/vocab`, `/grammar`, etc. That means there is no user flow, ever, in which
  someone views the grid while "on" one of its own destinations and notices the
  highlight missing. Reproduced live: clicking the Vocab card navigates to `/vocab` and
  the entire `.tool-grid` disappears from the DOM (confirmed via screenshot) — Path is
  gone, not just unhighlighted. Deleting `.tool-card.active` from `styles.css` today
  would change the rendered output in exactly zero pixels, on every possible click
  path, forever. That's a stronger claim than "cosmetic" — it's provably
  behavior-invariant dead code, not a degraded feature a learner can ever perceive the
  absence of. The topbar's active state matters because the topbar persists across
  every route; the hub grid's "active" state cannot matter by the very design that
  makes it a home-only shortcut launcher (same pattern as, e.g., a bookmarks-page
  tile grid — no one expects "current page" highlighting on a launcher that vanishes
  the moment you leave it). H2 in the round-042 plan appears to have assumed the grid
  persists like the topbar; that premise is false, and the "expected" behavior in this
  issue inherits that same false premise.
- Holds up? No, on the merits. The PM's "validated" correctly establishes the CSS is
  unreachable (verified independently: code read + live click-through confirms the
  grid unmounts entirely on navigation), but doesn't weigh that "unreachable" here
  means *impact-free* — not merely low-severity-but-real. There is no learner-facing
  gap to close, because there's no moment where a learner would ever look for or miss
  this feedback. The two proposed fixes are either genuine scope creep (restructuring
  the grid into a persistent layout shell for a home-only launcher, adding real
  complexity for zero perceptible benefit — the CLAUDE.md "fix worse than the bug"
  case) or a no-op cleanup (deleting one CSS rule with no rendering consequence,
  which isn't a "fix" in the bug-tracking sense so much as housekeeping).
- Final verdict: rejected — dead CSS with an unreachable trigger by design (home-only
  launcher, not a persistent nav element); zero observable impact on any real user
  flow. Not a QA-tracked defect; if desired, drop the unused `.tool-card.active` rule
  as ordinary cleanup outside this pipeline, not as a "fix."
