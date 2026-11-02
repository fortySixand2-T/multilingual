---
id: 1140
title: Reading passages keep source hard line breaks, giving ragged orphan lines on narrow screens
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Sign in, open Comprehension, open "Le café-philo du jeudi" (read-b1-cafe-philo) in a ~375px wide viewport (phone).
2. Read the passage.
3. Repeat for read-b1-bien-s-installer and read-b2-centre-ville-sans-voitures (all new readings except read-b2-semaine-de-quatre-jours look fine only because they happen to be short enough at desktop width).

## Expected
Paragraphs reflow to the container width; blank lines separate paragraphs only.

## Actual
The passage string contains single "\n" inside paragraphs (about 11-15 per set; JSON of /comprehension/sets/<id> confirms) and the card uses `white-space: pre-wrap`. On a 375px card, lines break twice: once at the container edge and once at the stored newline, leaving one or two word orphan lines ("mois-ci,", "tombe pas", "sa", "change", "l'autre de"). Even on desktop (1470px) read-b1-bien-s-installer shows a short first line "...il faut d'abord se renseigner : sur le quartier, les" then "prix, ..." mid-sentence. For a beginner it reads as broken sentences.

## Notes
Affects older readings too (read-b1-chercher-un-emploi has 18 single newlines). Fix either by stripping single newlines when building passage (YAML folded `>` / join lines) or by rendering paragraphs split on "\n\n" without pre-wrap. Web: web/src/screens/ComprehensionSet.tsx (whiteSpace pre-wrap).


## Triage
- Explanation: Passages in YAML are `|` blocks hard-wrapped at about 85 columns; ComprehensionSet.tsx line 74 renders them with white-space: pre-wrap, so every stored single newline becomes a visible break.
- Against spec: Mobile/learner readability; no spec exception for hard breaks.
- Verdict: validated
- Rationale: Real and corpus-wide: I checked all 89 reading passages; none uses short, intentional line structure, so collapsing single newlines is safe. On phones every reading shows ragged orphan lines. Cheapest correct fix is render-time: split on blank lines into paragraphs (or replace single \n with a space) and drop pre-wrap. App-code fix, small. Medium for mobile readability.

## Critic
- Challenge: Challenge: render change vs content change; is pre-wrap intentional? I scanned all 89 reading passages: single newlines are only ~85-col source wrapping; the only line-initial 'Label :' hits are inline prose ('Mon conseil :', 'Dernier conseil :'), no lists, headers or verse relying on line breaks. Blank-line paragraphs are preserved by the fix. ComprehensionSet.tsx line 74 uses whiteSpace: pre-wrap, confirming the cause. A single render-time change beats editing 89 YAMLs.
- Holds up? yes - real, corpus-wide mobile readability defect
- Final verdict: validated
- Note for dev-fixer: Fix at render only: split on /\n\s*\n/ into paragraphs and collapse single \n to a space (or equivalent); do not touch content YAML. Update/add a ComprehensionSet test.

Fix: web/src/passageParagraphs.ts + screens/ComprehensionSet.tsx — passages render as paragraphs split on blank lines, wrapped lines rejoined; test passageParagraphs.test.ts.

Follow-up (review): joining every single newline merged menus, timetables, letters and itineraries (11 older A1/A2 sets) into run-on lines. passageParagraphs now joins a line break only when the next line starts lowercase, or the line is 70+ chars and the next is not a "Label :" item; other breaks render via pre-line. Checked against all 165 passages.
