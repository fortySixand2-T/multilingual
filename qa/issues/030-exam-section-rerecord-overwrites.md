---
id: 030
title: Re-recording an exam section silently overwrites the previous score
severity: low
area: exam
persona: exam-crammer
status: rejected
found: 2026-06-19
---

## Steps to reproduce
1. `POST /exam/start {"blueprint_id":"mock-1"}`.
2. `POST /exam/{id}/section {"skill":"reading","correct":5,"total":10}`.
3. `POST /exam/{id}/section {"skill":"reading","correct":10,"total":10}`.

## Expected (per the report)
Either reject the second submission or flag the section as already recorded.

## Actual
`HTTP 200`; the second value (10/10 → CLB 9) replaces the first, and `recorded` still
lists `["reading"]` once. Last-write-wins. Found via round-003 hypothesis H5.

## Notes
`record_section` upserts by skill. A learner could record a weak section, then re-record
a perfect one and inflate their own CLB.

## Triage
- Explanation: sections are keyed by skill, so a repeat submission updates in place. The
  attempt stays open until all sections are recorded (the issue-004 resume design).
- Against spec: Phase 5 treats the mock CLB as an **estimate, not official**; resume/redo
  of a section is part of the intended practice flow.
- Verdict: validated (low) — score self-inflation is possible.

## Critic
- Challenge: re-recording is a *feature* here, not a bug — a learner who fumbles a section
  mid-practice should be able to redo it, and last-write-wins is the natural semantics.
  The only "harm" is inflating your *own* practice estimate; the board shows xp/streak,
  not CLB, so nothing shared is corrupted. Per the 005/007 rubric (self-inflicted + no
  shared-state harm → reject), this is reject. Adding lock/append logic would also break
  the legitimate redo and add complexity against CLAUDE.md.
- Holds up? Yes — the PM's "inflation" concern has no real victim.
- Final verdict: rejected — working as intended (section redo). No change.
