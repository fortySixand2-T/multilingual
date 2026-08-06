---
id: 622
title: GET /srs/queue exposes raw unrounded FSRS difficulty; renders as ugly long decimal in "tough card" tooltip
severity: low
area: srs
persona: edge-case-breaker
status: done
found: 2026-08-05
---

## Steps to reproduce
1. Seed and review a content card, e.g. `a_bientot`, to push its difficulty up
   (repeated `POST /srs/review {"card_key":"a_bientot","rating":"again"}`).
2. Compare the `difficulty` value for the same card across the two endpoints
   while it's due:
   - `GET /srs/hardest`
   - `GET /srs/queue`

## Expected
`/srs/hardest`'s spec explicitly says difficulty is "rounded to 1dp". For a
consistent user-facing number (and to avoid an ugly raw float leaking into the UI),
`/srs/queue`'s `difficulty` field should get the same 1dp rounding.

## Actual
`/srs/hardest` rounds:
```
"difficulty": 6.4
```
`/srs/queue` returns the raw, unrounded FSRS float for the very same card/state:
```
"difficulty": 6.4133
```
(In general this will be a long, ugly float straight out of the FSRS library —
not just one extra digit — since `app/srs/fsrs.py::difficulty()` does
`float(state.get("difficulty"))` with no rounding at all.)

This raw value is then used directly, unrounded, by the frontend in
`web/src/screens/Review.tsx`:
```tsx
{typeof card.difficulty === "number" && card.difficulty >= 7 && (
  <div title={`FSRS difficulty ${card.difficulty} / 10`} ...>
    🔥 One of your tough ones
  </div>
)}
```
So a learner hovering the "tough one" badge on the review screen would see a
tooltip like `FSRS difficulty 8.23417293847 / 10` instead of a clean
`FSRS difficulty 8.2 / 10`.

## Notes
Low severity — cosmetic/consistency only, no functional break, and the field is
tucked in a hover tooltip rather than prominent UI. Flagging because the two
endpoints (`/srs/queue`, `/srs/hardest`) now share the same underlying
`_resolve_vocab`/difficulty plumbing per this slice's description, so this looks
like a straightforward oversight (round in one call site, forgot the other)
rather than an intentional distinction.

## Triage
- Explanation: Confirmed at the code level (no live due card was needed to
  verify — the two call sites are unambiguous). `app/srs/fsrs.py::difficulty()`
  does `float(d)` with zero rounding — it's meant as the single source of
  FSRS-state-shape knowledge, not a presentation layer. `app/srs/api.py::get_hardest`
  (line 97) explicitly does `"difficulty": round(d, 1)`, while `get_queue`
  (line 74) passes the raw `difficulty(c.state)` straight through unrounded. Both
  endpoints now share `_resolve_vocab` for vocab resolution (confirmed by this
  slice's refactor), but rounding was only added at one of the two call sites in
  `api.py` — a straightforward one-line oversight, not an intentional distinction
  (there's no comment or test asserting `/queue`'s difficulty must stay raw).
  `web/src/screens/Review.tsx` line 56 then interpolates that raw value directly
  into the tooltip `title` string with no client-side rounding either, so the long
  float would reach the DOM as-is.
- Against spec: unspecified for `/srs/queue` specifically, but `/srs/hardest`'s own
  docstring/implementation establishes "1dp" as the intended user-facing precision
  for this exact same underlying FSRS value, so `/queue` returning a different,
  unrounded representation of the same signal is an inconsistency, not a
  documented distinction.
- Verdict: validated
- Rationale: Cosmetic and low-impact (a hover tooltip), but real and cheap to fix
  — round in `get_queue` the same way `get_hardest` already does, so a learner
  hovering the badge doesn't see a raw FSRS float leaking through what's meant to
  be a clean, human-readable number.

## Critic
- Challenge: This is a tooltip (`title` attribute) that requires a mouse hover
  to even see — most learners on touch devices will never encounter it at all,
  and on desktop it's a `title=` attribute, not rendered UI copy. Is a long float
  in a browser-native tooltip actually a defect worth a diff, or is this exactly
  the kind of theoretical/cosmetic nit this role exists to reject? Also worth
  checking: does the raw value break anything functionally (e.g. the `>= 7` badge
  gate in `Review.tsx`)? Confirmed it doesn't — `card.difficulty >= 7` is
  precision-agnostic, so there's no functional bug riding along with this.
- Holds up? Yes. Confirmed at `app/srs/api.py` lines 74 (`get_queue`, no
  rounding) vs. 97 (`get_hardest`, `round(d, 1)`) — both now resolve through the
  same `_resolve_vocab`/`difficulty()` plumbing per this slice's own commit, so
  the asymmetry is an oversight, not a deliberate choice with a comment or test
  backing it. It's genuinely low severity (PM already scored it "low," correctly)
  but the fix is a single `round(d, 1)` added at one call site — it doesn't add
  complexity, doesn't touch behavior, and prevents a real (if minor) leak of an
  ugly internal float into user-visible text. That clears the "fix is worse than
  the bug" bar easily. Not inflating to anything higher than the PM's already-low
  severity.
- Final verdict: validated

## Fix
`app/srs/api.py::get_queue` now rounds `difficulty` to 1dp the same way
`get_hardest` already does, while still passing `None` through untouched for
unreviewed cards (`d if (d := difficulty(c.state)) is None else round(d, 1)`).
Added `tests/test_personal_vocab.py::test_queue_difficulty_rounded_same_as_hardest`,
which reviews a card, forces it back due, and asserts `/srs/queue` and `/srs/hardest`
report the same rounded difficulty for it. Files: `app/srs/api.py`,
`tests/test_personal_vocab.py`.
