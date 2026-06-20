---
id: 071
title: "no-replay" listening audio can be re-fetched server-side
severity: low
area: comprehension
persona: edge-case-breaker
status: rejected
found: 2026-06-19
---

## Steps to reproduce
1. `GET /comprehension/audio/listen-greet-01` (the set has `allow_replay: false`).
2. GET it again.

## Expected (per the report)
A no-replay set's audio can't be fetched twice.

## Actual
Both GETs return `200` — the server streams the audio every time. `allow_replay` is a
flag in the set data; nothing server-side tracks plays. Found via round-005 H3.

## Notes
The SPA player honors `allow_replay` (single play, countdown). The endpoint is plain
content delivery.

## Triage
- Explanation: `allow_replay` is surfaced to the client, which enforces the single-play
  UX; the audio route streams the object on any GET with no per-attempt play counter.
- Against spec: Phase 3/5 mention no-replay listening, but as an exam-condition the client
  enforces.
- Verdict: validated (low) — server doesn't enforce the no-replay promise.

## Critic
- Challenge: replay grants nothing on its own — you still must answer, XP is gated on
  first pass and now on `not over_time` (qa-040), and the audio is fixed content. To
  enforce server-side you'd track play counts per user per set — real state + complexity
  for a practice tool, to stop a self-inflicted bypass that yields no advantage and
  corrupts no shared state.
- Holds up? No. Same rubric as over-time/section-redo: self-inflicted, no shared-state
  harm, fix disproportionate. The single-play experience is correctly the player's job.
- Final verdict: rejected — by design (client-enforced). No change.
