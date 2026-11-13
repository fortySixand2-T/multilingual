---
id: 1165
title: POST /vocab/personal stores gender on verbs/adjectives and accepts invalid gender values
severity: low
area: content
persona: exam-crammer
status: rejected
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal {"fr":"marcher","en":"to walk","gender":"m","pos":"verb"}
2. POST /vocab/personal {"fr":"rapide","en":"fast","gender":"zz","pos":"noun"}

## Expected
Gender only kept for nouns, and only m/f/mf (422 or normalised to '').

## Actual
1. 200 card {"fr":"marcher","gender":"m","pos":"verb"}
2. 200 card {"fr":"rapide","gender":"zz","pos":"noun"}
Gender shows on a verb card; garbage gender persisted. Lookup path (resolve_gender) enforces nouns-only, the manual add path does not.

## Notes
app/content/personal_api.AddBody has no validation on gender/pos values.

## Triage
- Explanation: Confirmed in code: personal_api.AddBody has only length limits on gender/pos; add_personal stores them as sent. The lookup path normalises via resolve_gender but manual add does not.
- Against spec: Plan: gender applies to nouns only; values m/f/mf.
- Verdict: validated
- Rationale: Low impact (needs a hand-crafted request, UI sends lookup values) but trivial integrity fix. FIX LOCATION: runtime, personal_api.AddBody validators (gender in {'', m, f, mf}, '' unless pos == noun; pos in known set).

## Critic
- Challenge: Only reachable by a hand-crafted POST; the UI sends values from the lookup/edit form (gender comes from lookup, pos fixed). It is self-inflicted, affects only that user's own card, and the fix adds validators for no learner-facing gain.
- Holds up? No. Impact is theoretical; closed without change.
- Final verdict: rejected
