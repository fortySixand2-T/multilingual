---
id: 490
title: Practice & tools grid on home screen has no heading, reads as part of "Your path"
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-07-26
---

## Steps to reproduce
1. Sign up as a brand-new user (invite code `friend-001`), select level A1.
2. Land on the home/Path screen (`/`).
3. Look at the area between the "Your path · A1" heading and the "First contact" unit
   section: the 8-icon grid (Vocab, Grammar, Drill, Read & Listen, Write, Speak, Weak
   spots, Readiness).
4. Inspect the DOM: `document.querySelectorAll('body *')` filtered for text matching
   `/practice|tools/i` returns zero elements — there is no "Practice & tools" (or any
   other) label anywhere on the page introducing the grid.

## Expected
As a first-time user, the 8-icon grid should be visually/semantically identifiable as
a distinct "quick tools" navigation area, separate from the structured learning path
(units/lessons) below it — e.g. via its own heading such as "Practice & tools".

## Actual
The page has exactly one heading, "Your path · A1", which sits directly above the
8-icon grid. The grid is immediately followed (after a plain whitespace gap, no
heading/divider/label) by "First contact" and the "Greetings 01" / "Greetings 02" /
"Greetings 03" lesson rows — the actual structured path.

Because "Your path · A1" is the only heading on screen and it sits right above the
grid, a genuine first-time user has no textual cue that the grid is NOT "the path" —
it visually reads as if the 8 icons are the first row of "your path", with the real
unit list underneath being a second, unlabeled section. Confirmed via screenshot: the
grid appears immediately under "Your path · A1" with nothing between them but a card
border, and nothing between the grid and "First contact" but vertical spacing.

## Notes
This does not ask to revert the topbar simplification (out of scope per round 042
plan H5) — only that the new grid needs its own label so users can tell "quick tools"
apart from "your structured path" at a glance. Likely fix: add a small section heading
(e.g. "Practice & tools") above the 8-card grid in the Path/home view (web/src/pages
Path or Home component under web/src/App.tsx routing for `/`).

## Triage
- Explanation: `Path.tsx` renders `<h1>Your path · {level}</h1>`, immediately followed by
  `<nav className="tool-grid" aria-label="Practice & tools">` (the 8 tool cards), then a
  `.tool-grid { margin: 4px 0 26px }` gap, then the unit list starting with "First
  contact". There is an `aria-label` on the `<nav>` — so a screen-reader user does get
  "Practice & tools, navigation" announced — but there is no *visible* text anywhere
  identifying the grid; the tester's DOM query (`textContent` match) correctly missed
  it because `aria-label` isn't part of rendered text. Reproduced live in the browser at
  `http://127.0.0.1:8201/`: the only heading on the page is "Your path · A1", positioned
  directly above the 8-icon grid with no visible divider, label, or heading between the
  grid and "First contact" below it — confirms the screenshot evidence in the issue.
- Against spec: `qa/rounds/042-plan.md` H5 (discoverability, absolute-beginner persona)
  anticipated exactly this risk: "are the 8 icons+labels legible/self-explanatory enough
  that the persona doesn't get stuck" and explicitly instructs testers to "file only if
  genuinely confusing... not a taste preference." The round's own change-surface notes
  call the grid a distinct "Practice & tools" concept (see `styles.css:166` comment:
  "home hub: shortcuts to the tools that aren't in the slim topbar") — confirming the
  grid was designed as its own labeled section, but that label only made it into the
  (invisible-to-sighted-users) `aria-label`, not the markup.
- Verdict: validated
- Rationale: For the absolute-beginner persona this round targeted, a single ambiguous
  heading sitting above two visually undifferentiated sections (quick-tool shortcuts vs.
  the actual graded lesson path) is a real first-run comprehension cost, not a taste
  preference — matches the exact failure mode H5 was written to catch. Fix is small
  (add a visible section heading, e.g. reusing the existing `aria-label` text as visible
  copy) and in scope since it only touches `Path.tsx` markup, not the topbar trim.

## Critic
- Challenge: Reproduced live at `http://127.0.0.1:8201/` (screenshot taken). The 8
  tool-cards and the "First contact"/lesson-row section are not actually styled
  identically: the tool-grid is a 2-column grid of square cards (emoji centered above
  a bold label, nothing else), while the unit section below uses a completely
  different pattern — a full-width unit-head row with an "available" status pill,
  followed by full-width lesson rows with a circular icon, title, and a "Tap to start"
  subtitle. A learner scanning the page sees two visually distinct layouts, not one
  continuous list — arguably enough of a shape/rhythm break that a heading, while
  nice, isn't load-bearing for comprehension. One could argue this is closer to a
  taste preference than the "genuinely confusing" bar H5 sets, and that the aria-label
  already gives screen-reader users the label they need — the only real gap is
  cosmetic (missing heading for sighted users), which is what H5 was told to filter
  out ("not a taste preference").
- Holds up? Yes, on balance. Even granting the two sections are shape-differentiated,
  the issue's core claim is narrower and correct: there is zero visible text anywhere
  identifying what the 8-icon grid *is* — not even a repeated instance of "Practice &
  tools" that a sighted first-time user could read. Shape alone tells a beginner
  "these two things are different" but not "this one is a shortcuts grid, that one is
  your graded path" — which matters specifically for the absolute-beginner persona
  this round targeted (someone without the pattern-recognition experience returning
  users have). The fix is trivial (promote the existing `aria-label` string to a
  visible `<h2>`), touches only `Path.tsx`, carries no architectural risk, and doesn't
  reopen the topbar-trim decision. Low cost, plausible real benefit for the intended
  persona — clears the bar.
- Final verdict: validated

## Fix
Added a visible `<h2 className="section-label">Practice &amp; tools</h2>` heading
above the tool grid `<nav>` in `web/src/screens/Path.tsx`, reusing the existing
`aria-label` text as real on-screen copy. Added a `.section-label` style in
`web/src/styles.css` (small, bold, uppercase, muted — consistent with the existing
`.field label` treatment) so it reads as a lightweight section divider, not another
`<h1>`. Added a regression test in `web/src/screens/Path.test.tsx` asserting the
heading is rendered as visible text (not just the nav's `aria-label`).
