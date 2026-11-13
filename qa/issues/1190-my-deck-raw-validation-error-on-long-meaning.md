---
id: 1190
title: My deck shows raw "en: String should have at most 255 characters" when the edited meaning is too long
severity: low
area: web
persona: absolute-beginner
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. Sign in, open My deck (/my-deck).
2. Look up "maire" (preview shows meaning "mayor").
3. In "Meaning (edit if it's not right)" paste or type a text longer than 255 characters (e.g. a long definition).
4. Press "Add to my deck".

## Expected
The meaning field limits input (maxlength) or a friendly message such as "Meaning is too long (max 255 characters)".

## Actual
A red banner above the preview reads the raw server validation text: "en: String should have at most 255 characters". The input is a single-line field with no maxlength or counter, so the learner cannot see the whole text they typed (it scrolls horizontally). Nothing is saved; preview stays open.

## Notes
Dictionary-supplied glosses are short (<30 chars sampled), so this only affects hand edits. Leaking the pydantic field name ("en") is jargon for a beginner.

## Triage
- Explanation: Confirmed in web/src/screens/MyDeck.tsx: the meaning input has no maxLength and errors are shown raw from the server ('en: String should have at most 255 characters'; AddBody en max_length=255).
- Against spec: UI should give learners readable messages (QA conventions).
- Verdict: validated
- Rationale: Low, hand-edit only. FIX LOCATION: UI (maxLength=255 on the meaning input and friendly message); optional runtime tweak to error text.

## Critic
- Challenge: Only reachable by pasting >255 characters into the meaning edit; dictionary glosses are short. Theoretical for learners; the error, while jargon-y, is still shown and nothing is lost.
- Holds up? No. Rare hand-edit path; not worth a change now.
- Final verdict: deferred
