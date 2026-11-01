---
id: 1051
title: Docteur/docteure card: second slow-audio button wraps onto its own line
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-10-31
---

## Steps to reproduce
1. Sign in, level A1, open Vocab -> People (/vocab/a1/people), desktop width (~1470px).
2. Advance to card 5/11 "docteur (m) / docteure (fe)".

## Expected
Both forms with their two audio buttons (normal + slow) laid out cleanly, e.g. each form grouped with its own buttons.

## Actual
Line 1 shows `docteur (m) [speaker] [turtle] / docteure (fe) [speaker]`, and docteure's turtle (slow) button wraps alone onto a second centered line, above the IPA `/dɔktœʁ/ · /dɔktœʁ/`. Looks broken/misaligned and it is unclear which form the orphaned button belongs to. All four buttons do play (0.87s clip each, no errors).

## Notes
Probably a flex-wrap on the card header for mf cards. Check also at mobile width.

## Triage
- Explanation: VocabWord.tsx Headword (mf branch) renders siblings in .vocab-word: span, AudioButton(slow pair), '/', span, AudioButton, with no grouping per form, so a flex-wrap breaks between the two buttons of docteure. Confirmed in JSX; not rendered in Chrome here (layout reasoned from code, reporter's observation consistent).
- Against spec: unspecified; 922 added the second form.
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Cosmetic and low severity; all four buttons work. But the layout genuinely breaks: .vocab-word is flex-wrap with gap 10, and the mf branch (VocabWord.tsx:51-64) has no per-form grouping, so on narrower widths the turtle button orphans. Fix is small, frontend only. I did not render it in Chrome; judged from JSX/CSS and the reporter's observation.
- Holds up? Yes. Fixer scope: wrap each form (name + gender mark + its AudioButton pair) in a span with white-space nowrap / display inline-flex gap, keeping the '/' separator between groups, so wrapping happens between forms, not inside one. Check at ~390px width.
- Final verdict: validated

## Fix
Each mf form (name, gender mark, its audio button) is wrapped in a .vocab-form inline-flex nowrap span (web/src/VocabWord.tsx, web/src/styles.css), so wrapping happens between forms only. Test: web/src/VocabWord.test.tsx. Not visually checked at 390px (no browser).
