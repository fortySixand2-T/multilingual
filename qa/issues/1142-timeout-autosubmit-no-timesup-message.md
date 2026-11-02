---
id: 1142
title: Timer expiry auto-submits silently; results show "Your answer: –" with no "time's up" notice
severity: low
area: web
persona: absolute-beginner
status: deferred
found: 2026-11-01
---

## Steps to reproduce
1. Open listen-b1-un-voisin-courageux (120s timer starts at page load, before audio is played).
2. Answer nothing; wait for the countdown to reach 0.

## Expected
Learner is told the time ran out (banner like "Time's up - submitted automatically"), and ideally the timer starts or is explained relative to the audio.

## Actual
The quiz instantly turns into the results screen: "Keep practicing, 0 / 3 correct", each question showing "Your answer: – · Correct: ...". No message says why. The timer is also only in a non-sticky pill at the top, so it scrolls out of view while answering lower questions (first reading screen: pill at y=113, gone after scrolling), so the sudden jump is surprising. Results also show "0 XP / 0 streak" with no explanation.

## Notes
web/src/screens/ComprehensionSet.tsx auto-submit effect; no console errors.


## Triage
- Explanation: Auto-submit effect calls submit() at remaining===0; Results shows 'over time' only when the server flags it and nothing explains a timeout.
- Against spec: Unspecified.
- Verdict: deferred
- Rationale: Real UX gap (no 'time's up' banner, non-sticky timer) but polish on shared screen code affecting all timed sets, not tied to the new content; needs a small design call (sticky timer, banner). Not worth blocking this round's content fixes.

## Critic
- Challenge: Polish on shared screen code, not tied to this round's content.
- Holds up? yes
- Final verdict: deferred
- Note: Backlog.
