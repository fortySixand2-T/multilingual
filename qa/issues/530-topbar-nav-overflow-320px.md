---
id: 530
title: Topbar nav strip (Learn/Review/Mock/Group) overflows viewport at 320px width, clipping "Group"
severity: low
area: web
persona: edge-case-breaker
status: done
found: 2026-07-27
---

## Steps to reproduce
1. Load the app at a 320×568 viewport (e.g. iPhone SE) on any authenticated
   screen — reproduced on `/path`, `/vocab`, and `/speaking` (shared topbar
   component, so it's global, not page-specific).
2. Look at the second row of the topbar, where `.nav` (Learn / Review / Mock /
   Group) sits below the brand/level/logout row per the `1971333` phone-nav
   fix.
3. Inspect/measure: `document.documentElement.scrollWidth` (328px) vs
   `clientWidth` (312px) — a 16px horizontal overflow. The `.nav` element's
   own bounding rect is 280px wide with `right: 296px` against a 312px
   viewport, and `getComputedStyle(nav).flexWrap` is `"nowrap"`.

## Expected
At 320px the four nav items should fit within the viewport width (wrap to a
second line, shrink, or scroll horizontally within their own row) with no
horizontal overflow of the page and no visual clipping of any tab label. The
043 plan's H7 charter describes this row as "full-width 4-item nav" that
should render without overflow at both 375px and 320px.

## Actual
At 375px the row renders correctly (all four labels fully visible, no
overflow: `scrollWidth === clientWidth`). At 320px, the "Group" label's tail
end is visually cut off at the right edge of the screen, and the whole
document gets a ~16px horizontal overflow (`scrollWidth=328` vs
`clientWidth=312`). Root cause: `.nav { display: flex; gap: 6px; }` in
`web/src/styles.css` has no `flex-wrap` set (defaults to `nowrap`), and the
`@media (max-width: 640px)` block added in `1971333` only sets `.nav { order:
3; width: 100%; margin-left: 0; }` — it never adds `flex-wrap: wrap` or an
`overflow-x: auto` fallback for widths where the four items don't fit their
own row unshrunk.

Screenshots (rendered via a same-origin iframe workaround at exact 320×568
CSS px, since `resize_window` did not affect this shared browser session's
actual viewport):
- Path @ 320px: "Group" tab clipped at right edge.
- Vocab @ 320px: same clipping (confirms it's the shared topbar, not page-specific).
- Speaking @ 320px: same clipping.

At 375px, all three screens render the nav row cleanly with no overflow.

## Notes
- Affected file: `web/src/styles.css`, `.nav` rule (~line 29) and the
  `@media (max-width: 640px)` block (~lines 187-192).
- Likely fix: add `flex-wrap: wrap` to `.nav` inside the media query (or a
  narrower `@media (max-width: 340px)` tier), or reduce the nav items' font
  size/padding at very small widths, or make `.nav` `overflow-x: auto` with
  `white-space: nowrap` if a horizontally-scrollable strip is the intended
  design (matching the `1971333` commit message's own description of "a
  single horizontally scrollable strip").
- Testing note: the shared Chrome tab-group session in this environment did
  not respond to `resize_window` (viewport stayed pinned at ~1470×801
  regardless of requested size, likely due to another concurrent QA agent
  sharing the same browser window/tab group). Worked around this by
  rendering the app in a fixed-size same-origin `<iframe>` inside a blank
  page, which correctly triggers the CSS media queries and gives an accurate
  `window.innerWidth`/layout for the iframe's content document. Flagging in
  case this instructs future rounds to expect the same `resize_window`
  limitation in a busy shared session.

## Triage
- Explanation: Independently reproduced (not just re-reading the tester's
  screenshots). `resize_window` was confirmed still broken in my own session
  too (requested 320×568, actual `document.documentElement` came back
  606×635) — same shared-tab-group limitation the tester hit, so I used the
  same same-origin `<iframe>` technique myself, but cross-checked the result
  with direct `getBoundingClientRect()` geometry rather than trusting
  `scrollWidth`/`clientWidth` alone (which could in principle be an
  iframe/scrollbar artifact). At a true 320px content width, `/path`'s
  `.nav` "Group" link's own bounding rect right edge sits at x=328.6 CSS px
  — 8.6px past the 320px right boundary — while `getComputedStyle(nav).flexWrap`
  is `"nowrap"`, confirming the last ~8.6px of the "Group" label (and the
  whole row) is genuinely clipped, not a screenshot/rendering artifact. At
  375px the same link's right edge is comfortably inside the viewport (well
  under 375), matching the tester's claim that 375px is clean. Root cause is
  exactly as diagnosed: `web/src/styles.css` `.nav { display:flex; gap:6px; }`
  (line 29) has no `flex-wrap`, and the `1971333` `@media (max-width: 640px)`
  block (lines 187-192) only moves `.nav` to its own row (`order:3; width:100%`)
  without adding `flex-wrap: wrap` or a horizontal-scroll fallback, so widths
  narrower than the four items' unshrunk combined width (~296px content +
  32px page padding = ~328px, matching the measured overflow almost exactly)
  overflow the viewport.
- Against spec: unspecified in `TEF_Platform_Technical_Plan.md` (no explicit
  breakpoint requirements), but the 043 plan's own H7 charter states the
  full-width 4-item nav "should render without overflow at both 375px and
  320px" — this is the round's own stated acceptance bar, and 320px (iPhone
  SE) is a standard, still-supported small-viewport target, not an
  unreasonably extreme edge case.
- Verdict: validated
- Rationale: Real, reproducible, low-cost regression from the `1971333`
  phone-nav fix — at 320px width a nav label is visually clipped and the
  page gains genuine horizontal overflow (not clamped to the viewport). Low
  severity (cosmetic, one breakpoint, all four routes share the fix), so
  correctly filed as `low`, but it is an in-scope, real defect against this
  round's own explicit 320px acceptance criterion.

## Critic
- Challenge: The strongest case for "no change needed" is (1) a true 320px
  iPhone SE is a discontinued form factor — current iPhones start at 375px,
  so this could be an unreasonably narrow target nobody actually uses; (2)
  both the tester's and PM's `resize_window` was broken in their shared
  session, and their iframe workaround could plausibly be measuring
  something the real browser chrome (scrollbars, zoom, viewport meta
  quirks) wouldn't reproduce; (3) at ~12px of overflow on one label, this
  could be a rounding/font-metric artifact rather than a real regression.
  Independently reran the exact same `resize_window` call myself on this
  session (tab 1644020714, requested 320×568) and got `innerWidth: 606`,
  confirming the tool is genuinely broken here too, not just for the prior
  two agents — so I couldn't dismiss this as a stale/session-specific claim.
  Built my own same-origin iframe (not copy-pasting the tester's or PM's
  numbers) at a true 320px CSS width and re-measured from scratch.
- Holds up? Yes. My independent measurement: `clientWidth`/`innerWidth`
  316px, `scrollWidth` 328px, `.nav a[Group]` bounding-rect `right: 328.6`,
  `getComputedStyle(nav).flexWrap: "nowrap"` — matching the PM's own
  independently-taken numbers (328.6, `nowrap`) to a tenth of a pixel from
  a completely separate iframe instance. That level of agreement across
  three independent measurements (tester, PM, critic) rules out a
  session-specific rendering fluke. A screenshot of the same iframe shows
  "Group" rendered without a literal cropped/truncated glyph (worth noting:
  "clipping" in the title slightly overstates it — nothing sets
  `overflow: hidden` on the row, so the real symptom is the row/page
  gaining unwanted horizontal scroll, with the last several px of "Group"
  pushed off the visible edge, not text literally cut mid-letter). That's a
  real but modest cosmetic bug, correctly filed as `low`. On the "is 320px
  a reasonable target" point: I don't need to independently defend that
  choice, because the round's own H7 charter (`qa/rounds/043-plan.md`)
  explicitly set 320px as this round's acceptance bar for this exact nav
  row — overturning that as "unreasonable" isn't the critic's call to make
  unilaterally against the round's own stated scope. The fix is also
  low-risk (one `flex-wrap` or narrow-breakpoint tweak to existing CSS, no
  new abstractions), so there's no "fix is worse than the bug" case here.
- Final verdict: validated

## Fix
Matched the design intent stated in the original `1971333` commit message
("the tabs become a single horizontally scrollable strip on their own row")
which never actually got implemented: added `overflow-x: auto; flex-wrap:
nowrap; -webkit-overflow-scrolling: touch;` to `.nav` and `flex: none` to
`.nav a` inside the `@media (max-width: 640px)` block in
`web/src/styles.css`. This contains any overflow within the nav row itself
(scrollable) instead of letting it leak into the page (`scrollWidth` growing
past `clientWidth`), so "Group" is no longer clipped and the page gains no
horizontal scroll at 320px. Added `web/src/styles.test.ts`, a regression
test asserting the phone media query's `.nav` rule sets either
`flex-wrap: wrap` or `overflow-x: auto` so this can't silently regress back
to the unguarded `nowrap` default.
