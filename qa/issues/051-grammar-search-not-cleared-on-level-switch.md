---
id: 051
title: Grammar reference search box not cleared on level switch, causes silent empty state
severity: medium
area: web
persona: edge-case-breaker
status: done
found: 2026-07-20
---

## Steps to reproduce
1. Sign in, go to `/grammar`, set Level to B2 (via the Level dropdown in the top nav).
2. Type a search term into the "Search grammar…" box that matches something on B2
   but is specific to a category only present at B2, e.g. `subjonctif` (matches
   Subjunctive-category entries; B2 is the only level with a Subjunctive category).
   Confirm results narrow correctly (4 subjunctive grammar points shown).
3. Without touching the search box, switch Level to A1 using the same Level
   dropdown (no full page reload — just the in-app selector).
4. Observe the grammar reference screen after the level switch completes.

## Expected
Either the search text is cleared when the level changes (since a search term
scoped to the old level's content is no longer meaningful), or, if it's kept,
the UI should make it obvious that a leftover search term is filtering an empty
result set for the new level (e.g. a visible "clear search" affordance is
strongly hinted at, or a message referencing the search term).

## Actual
After switching from B2 to A1 with "subjonctif" still typed in the search box:
- The category chip filter correctly resets to "All" (chips render fresh for A1:
  Verb conjugation & tenses / Articles & determiners / Adjectives & comparison /
  Expressions & communication).
- The search box still shows the stale text "subjonctif" from the B2 session.
- Since A1 has no Subjunctive category/content, the list renders only:
  "No grammar points match your filter."
- There is no console error, no visual distinction from a legitimately-empty
  category, and nothing on screen ties the empty result to the leftover search
  text. A learner who just wanted to browse A1 grammar would see a page that
  looks broken/empty immediately after switching levels, with no clue that
  clearing the search box (which they may not even remember they used) would
  fix it.

## Notes
Root cause (from reading `web/src/` for context only, not fixing): the
level-change effect resets `items`/`error`/`cat` state but not the search query
`q`. This is the same class of bug already filed for other screens at
`qa/issues/391-exam-screen-stale-state-on-level-switch.md` and
`qa/issues/392-drill-screen-hardcodes-a1-ignores-level-switcher.md` — level
switches inconsistently reset local UI state across the app. Confirmed via
direct DOM/localStorage manipulation of the level `<select>` (dispatching a
`change` event), not just a full page reload, so this is not an artifact of the
test method.

## Triage
- Explanation: `web/src/screens/Grammar.tsx` line 36-41: the `useEffect(() =>
  {...}, [level])` that fires on level change resets `items`, `error`, and
  `cat`, but never resets `q` (the search string state). Reproduced live at
  http://127.0.0.1:8123/grammar: set level to B2, typed "subjonctif" (narrows
  correctly to 5 Subjunctive entries), then dispatched a `change` event on the
  level `<select>` to switch to A1 without reload. Result matches the report
  exactly — chips correctly reset to A1's set (Verb conjugation & tenses /
  Articles & determiners / Adjectives & comparison / Expressions &
  communication) and "All" is active, but the search box still shows
  "subjonctif" and the page silently renders only "No grammar points match
  your filter." with zero indication that a stale, level-scoped search term is
  the cause.
- Against spec: unspecified in `TEF_Platform_Technical_Plan.md` at this level
  of UI detail, but this is the same class of bug already validated/fixed
  elsewhere in the app (391, 392) — level switches are expected to reset
  screen-local filter/search state, and this screen only did it partially.
- Verdict: validated
- Rationale: A learner switching levels to browse a different level's grammar
  reference lands on what looks like a broken/empty page with no visible cause
  — they'd have to notice and manually clear a search box they may not
  remember filling in. Simplest correct fix is clearing `q` alongside `cat` in
  the existing level-change effect (same pattern as the referenced sibling
  fixes), which is a small, low-risk, real UX bug worth fixing now.

## Critic
- Challenge: This screen is a reference tool, not a form — the search box
  stays visibly non-empty right above the empty-state message, so a learner
  glancing at the screen has a fair chance of noticing the leftover text
  themselves. Unlike 391/392 (exam/drill screens, where stale state silently
  corrupts a graded session), the "damage" here is self-recoverable with one
  click + delete. One could argue this is working as designed — search
  persisting until manually cleared is a common pattern — and that mandating
  "clear every filter on every navigation" everywhere in the app risks
  over-engineering a low-severity annoyance.
- Holds up? No. Reproduced live at http://127.0.0.1:8123/grammar: set level to
  B2, typed "subjonctif" (narrows correctly to Subjunctive entries), then
  flipped the level `<select>` to A1 without reload via a dispatched `change`
  event. Screenshot confirms chips reset cleanly to A1's categories, but the
  search box still reads "subjonctif" and the only content on screen is "No
  grammar points match your filter." — no label, placeholder, or highlight
  ties the empty state to the search box. Because the chip filter *does* reset
  automatically, the app has already trained the user to expect a clean slate
  on level switch, making the surviving stale search doubly confusing (partial
  reset is worse than no reset). The fix is a one-line addition (`setQ("")`)
  to the effect that already resets `cat` — trivial, no added complexity, and
  consistent with the existing pattern.
- Final verdict: validated

## Fix
- Action: `web/src/screens/Grammar.tsx` — added `setQ("")` to the level-change
  `useEffect` (alongside the existing `setItems(null)`, `setError("")`,
  `setCat(null)`), so switching levels now clears the search box in addition to
  the category filter.
- Test: added `Grammar.test.tsx` case "clears the search box when the level
  changes (qa-051)" — types a search term, changes the mocked level and
  re-renders, and asserts the search input's value resets to `""` once the new
  level's items load.
- Verification: `npx vitest run src/screens/Grammar.test.tsx` — 4/4 passing
  (was 3/4 before the new test existed). Full web suite `npx vitest run` —
  23/23 passing. `npm run build` succeeds with no type errors.
