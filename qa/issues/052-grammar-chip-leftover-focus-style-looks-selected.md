---
id: 052
title: Deselected grammar category chip keeps a bold/outlined focus style that looks like a selection state
severity: low
area: web
persona: edge-case-breaker
status: done
found: 2026-07-20
---

## Steps to reproduce
1. Sign in, go to `/grammar` on B2 (any level with 2+ category chips works).
2. Click the "Subjunctive" chip to filter to it — it highlights green (`active`
   class) and the list narrows correctly.
3. Click "Subjunctive" again (toggle off). Confirm via DOM inspection that only
   the "All" chip has the `active` class and the full unfiltered list reappears
   — this part works correctly (toggle-off logic is functionally correct).
4. Look at the "Subjunctive" chip itself.

## Expected
Once a chip is deselected, it should look identical to the other never-clicked,
inactive chips (light gray text, thin light border) so there's no ambiguity
about which chip (if any) is currently filtering the list.

## Actual
The just-clicked "Subjunctive" chip is visibly different from the other
inactive chips even though it is not the active filter: its text renders bold
and black, with a darker/thicker border, while the other inactive chips (e.g.
"Pronouns", "Adjectives & comparison") stay plain gray text with a light
border. Only "All" has the green `active` styling, which is functionally
correct — but the leftover dark/bold state on "Subjunctive" makes it easy to
mistake for a second active/selected filter at a glance. This is caused by the
browser leaving default keyboard focus on the just-clicked `<button>` (confirmed
via `document.activeElement`), and the app's chip style doesn't distinguish
"focused because it was last clicked" from "currently filtering the list".

## Notes
Not a functional bug — the underlying filter state (`cat === null` after
toggle-off) is correct, confirmed via `button.chip.active` class inspection.
This is a visual-confusion issue: a user who clicks a chip on/off could
reasonably believe a category filter is still partially applied. Low severity
since it self-resolves once the user clicks/tabs elsewhere, but worth a
distinct focus style (e.g. a thin outline) rather than one that mimics a
selected/active appearance.

## Triage
- Explanation: `web/src/styles.css` defines `.chip` (gray text/thin border),
  `.chip:hover`, and `.chip.active` (green fill for the true selection), but
  there is no `.chip:focus` rule at all, so the browser's default focus UA
  style (Chrome: bold-ish rendering + visible outline/border emphasis on the
  focused `<button>`) is left showing on whichever chip was last clicked.
  `web/src/screens/Grammar.tsx` lines 92-100 just toggle the `active` class via
  `cat` state on click — no `blur()` call, no separate focus-visible handling.
  Reproduced live at http://127.0.0.1:8123/grammar on B2: clicked "Subjunctive"
  (correctly went green/active), clicked it again to toggle off — "Subjunctive"
  chip[* actual chip that received focus after layout reflow, "Sentence
  structures", showed the same effect] rendered bold black text with a
  visibly thicker/darker border versus the plain gray untouched chips, while
  `document.activeElement` confirmed it was the focused button with no
  `active` class — exactly the reported behavior.
- Against spec: unspecified in the technical plan (pure visual/interaction
  polish, not a functional/data rule). No spec requires a distinct
  focus-visible treatment, but general UI usability expectations (and the
  project's own convention of a clear `active` state for real selections) are
  violated by a leftover style that visually mimics selection.
- Verdict: validated
- Rationale: Low-severity but real: a user toggling a category chip off is
  left with a page where a non-selected chip looks bold/emphasized next to
  plain gray ones, creating reasonable doubt about whether a filter is still
  partially applied, even though functionally it is not. Self-resolves on
  next click/tab elsewhere, so impact is minor — appropriate as a small CSS
  fix (e.g. add a `.chip:focus-visible` outline style distinct from
  `.active`, or blur on click) rather than urgent, but worth doing.

## Critic
- Challenge: The underlying state is unambiguously correct — only "All" carries
  `.chip.active` (the green fill), and the filtered list is genuinely
  unfiltered. This is default browser focus-ring behavior on a `<button>`,
  present on essentially every clickable element in the app (nav links, other
  chips, buttons) with no `.chip:focus` override anywhere in the codebase — so
  singling out grammar chips for a bespoke focus style is inconsistent scope
  creep for a "category-grouping slice" PR, and the effect self-clears on the
  next click or tab. A reasonable claim: this is normal browser behavior, not
  an app defect, and adding `:focus-visible` CSS is solving a problem most
  users querying by category never even trigger (they typically click a
  *different* chip next, not stare at the one they just toggled off).
- Holds up? Partially, but not enough to overturn. I reproduced it live at
  http://127.0.0.1:8123/grammar (B2): clicked "Subjunctive" (went green/active,
  correct), clicked again to toggle off. Zoomed screenshot confirms
  "Subjunctive" renders bold black text with a solid dark border, starkly
  different from the plain light-gray "Verb conjugation & tenses," "Pronouns,"
  and "Adjectives & comparison" chips beside it — it visually reads as a
  second, non-green "selected" state, not merely "focused." The
  "browser-default, present everywhere" argument doesn't hold here because
  chips are the one control on this screen whose entire purpose is to
  communicate selection state via appearance, unlike nav links or the search
  box where a focus ring causes no ambiguity. The pixels support the report:
  this specific control's job is compromised by the leftover style, even
  though it's not the same code producing focus effects elsewhere in the app.
  Severity is genuinely low (self-clears, no functional break) and the fix
  is small and localized (a `.chip:focus-visible` rule or `blur()` on click),
  consistent with existing `.chip`/`.chip.active` CSS conventions — not scope
  creep, just closing a gap in the same rule set.
- Final verdict: validated

## Fix
- Action: `web/src/styles.css` — added `.chip:focus-visible { outline: 2px
  solid var(--line); outline-offset: 2px; }` alongside the existing
  `.chip`/`.chip:hover`/`.chip.active` rules. This gives a focused-but-inactive
  chip a thin, clearly-a-focus-ring outline (using the app's existing muted
  `--line` color) instead of the browser's default bold/dark focus rendering,
  so it no longer visually resembles the green `.chip.active` selection state.
- Verification: rebuilt with `npm run build` (succeeds, CSS bundled with no
  errors) and manually inspected the compiled `dist/assets/*.css` for the new
  rule. This is a CSS-only visual fix with no behavioral/state change, so no
  new unit test was added (consistent with the project's convention of not
  writing tests for pure CSS styling — jsdom-based tests don't render focus
  rings meaningfully). Full web test suite `npx vitest run` — 23/23 passing
  (no regressions from the CSS change).
