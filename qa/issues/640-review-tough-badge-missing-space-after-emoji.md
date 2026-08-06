---
id: 640
title: Review screen "tough ones" badge is missing a space after the fire emoji
severity: low
area: web
persona: returning-learner
status: done
found: 2026-08-05
---

## Steps to reproduce
1. Seed a card to difficulty >= 7 (rate it "again" a few times via `POST /srs/review`)
   so it becomes due, or use any account with a due card whose difficulty >= 7.
2. Log into the UI, go to Review (`/review`).
3. Land on a due card with difficulty >= 7 (e.g. "à bientôt" at difficulty 9.9).
4. Look at the small red label above the French word.
5. Zoom into the label (screenshot region roughly x:650-910, y:190-215 at 1562px
   viewport width).

## Expected
Per the slice spec the badge copy should read "🔥 one of your tough ones" (emoji,
then a space, then lowercase "one of your tough ones").

## Actual
The rendered badge shows "🔥One of your tough ones" — no space between the fire
emoji and the text, and the first word is capitalized ("One" instead of "one").
The emoji and text visually run together. Confirmed via zoomed screenshot; text
extracted from page reads exactly `🔥One of your tough ones`.

## Notes
Purely cosmetic/copy issue — functionality (band gating at difficulty >= 7, showing
only on tough cards) works correctly. Likely a template literal missing a space,
e.g. `` `🔥${label}` `` instead of `` `🔥 ${label}` ``, plus the label string itself
being title-cased. Low severity, but a bit visually sloppy given the app is
otherwise clean.

## Triage
- Explanation: Reproduced in the browser exactly as reported. Loaded the built
  SPA at http://127.0.0.1:8091/review with an authenticated session and a card
  at difficulty 8.2 (mocked `/srs/queue` response via `fetch` override since no
  seeded card was naturally due yet), then client-navigated to Review. Zoomed
  screenshot confirms the badge renders visually as "🔥One of your tough ones" —
  no visible gap between the emoji and text, first word capitalized. Checking
  `web/src/screens/Review.tsx` line 59, the JSX text node is actually
  `` 🔥 One of your tough ones `` — there IS a literal U+0020 space character in
  the source between the emoji and "One" (not a missing-space bug in the string
  itself). The visual collapse is a font/emoji-rendering artifact: this fire
  emoji glyph (🔥, U+1F525) commonly swallows/overlaps a directly-following plain
  space in proportional-width rendering, a known cross-browser quirk with certain
  emoji + text spacing. So the *visible* defect the tester saw is real and
  correctly described, even though their guessed root cause (`` `🔥${label}` ``
  with no space) doesn't match the actual source. Separately, the capitalization
  is also off versus intent: the feature's own commit message (5e256e3) describes
  the copy as `"one of your tough ones"` (lowercase), but the implemented string
  is `"One of your tough ones"` (capitalized) — a real, small copy mismatch
  against the author's stated intent, independent of the spacing issue.
- Against spec: no formal spec string exists in TEF_Platform_Technical_Plan.md for
  this badge copy; the only stated intent is the slice's own commit message
  ("Review flags a card as \"one of your tough ones\""), which the shipped string
  doesn't match on casing, and which visually renders with no emoji/text gap.
- Verdict: validated
- Rationale: Purely cosmetic, but confirmed real in the actual rendered UI (not
  just guessed from JSX) — the badge looks visually broken/run-together for every
  learner who trips difficulty >= 7, which is the app's main mechanism for
  flagging trouble cards. Fix: insert a non-breaking space or an explicit `&nbsp;`
  (or a `<span>` gap) after the emoji rather than relying on a plain space next to
  it, and lowercase "one" to match the intended copy.

## Critic
- Challenge: There is no spec string in `TEF_Platform_Technical_Plan.md` for
  this badge — the only "intent" being cited is the author's own commit message,
  which is not a spec, just how the author happened to describe their own feature
  in one sentence. Emoji/text kerning is a font-rendering quirk of the reviewer's
  environment, not a code defect — a different OS/browser font stack might render
  the space fine, so is this "chasing a screenshot" rather than a real, portable
  UI bug? And is capitalization ("One" vs "one") really a defect at all, or just
  normal sentence-starting capitalization that most style guides would consider
  more correct than lowercase?
- Holds up? Mostly yes, on the visual-collapse half. I independently loaded the
  live `/review` tab (already authenticated, already showing a genuine due card
  at difficulty 9.9 — not a mocked fetch) and screenshotted it myself: the
  rendered badge reads "🔥One of your tough ones" with no visible gap, matching
  the PM's finding exactly, on the actual production build/font stack this app
  ships with (not a synthetic repro). Since this is the real rendering environment
  users hit (not a cherry-picked browser), "it might render differently elsewhere"
  doesn't rescue it — this is how it renders here, today, for every learner on
  this deployment. The fix (swap the plain space for `&nbsp;` or a flex gap) is a
  one-line, zero-risk change consistent with keeping the UI clean. On
  capitalization: weaker ground — "One of your tough ones" reads fine as
  a sentence-cased label and arguably needs no fix on its own. But the PM bundled
  it as a secondary, minor note under the same (real) spacing defect rather than
  the primary claim, so it doesn't need to be split out to validate the issue.
- Final verdict: validated

## Fix
`web/src/screens/Review.tsx`'s tough-card badge now wraps the emoji and label in
separate `<span>`s inside a `display: flex, gap: 4` container instead of relying on a
plain space character next to the emoji glyph (which visually collapsed in this app's
font stack), and the label text is lowercased to `"one of your tough ones"` to match
the feature's intended copy. Added `web/src/screens/Review.test.tsx`, asserting the
lowercase text renders and the old capitalized string does not. Files:
`web/src/screens/Review.tsx`, `web/src/screens/Review.test.tsx`.
