---
id: 447
title: "focus" pill appears on weakest-skill bar even when target_met=true
severity: medium
area: web
persona: edge-case-breaker
status: done
found: 2026-07-05
---

## Steps to reproduce
1. Sign up a user (invite code `friend-001`).
2. Finish TWO mock exams so that all four skills' best CLBs are ≥ 7:
   - Mock 1: reading 6/10 → CLB 6, listening 7/10 → CLB 7, writing clb_estimate=7, speaking clb_estimate=8
   - Mock 2: reading 8/10 → CLB 8, listening 7/10 → CLB 7, writing clb_estimate=7, speaking clb_estimate=5
3. GET /exam/readiness → returns `{"target_met":true,"weakest_skill":"listening","overall":7,...}`
4. Navigate to /readiness in the browser.

## Expected
When `target_met` is true, the page header shows "On target — overall CLB 7" and no skill bar should show a confusing "focus" pill (the goal is already met; there is nothing to focus on urgently).

## Actual
The listening skill bar renders `<span class="pill">focus</span>` next to the label, even though the header simultaneously announces "🎉 On target — overall CLB 7". Two contradictory messages appear on the same screen.

The card-level weakest-skill nudge text is correctly suppressed by the `!data.target_met` guard on line 54, but the per-skill "focus" pill (line 64–69 of Readiness.tsx) has no such guard:

```tsx
const weak = s.key === data.weakest_skill;   // true for "listening"
...
{s.label} {weak && <span className="pill">focus</span>}  // no target_met check
```

## Notes
Fix: add `&& !data.target_met` to the pill condition:
```tsx
{s.label} {weak && !data.target_met && <span className="pill">focus</span>}
```
Alternatively, the backend could set `weakest_skill: null` when `target_met` is true, but the frontend fix is narrower in scope.
File: web/src/screens/Readiness.tsx line 69.

## Triage
- Explanation: In Readiness.tsx, the card-level weakest-skill nudge (line 54) is correctly guarded with `data.weakest_skill && !data.target_met`, but the per-skill "focus" pill (line 69) only checks `s.key === data.weakest_skill` with no `!data.target_met` guard. The backend intentionally returns a non-null `weakest_skill` even when `target_met=true`, so when all four skills reach CLB 7, the pill still renders on the lowest-scoring skill bar — producing contradictory UI: "On target" in the header and "focus" on a skill bar simultaneously.
- Against spec: The spec states the card-level nudge is "correctly guarded" by `!data.target_met` and notes the per-skill pill has "no target_met guard" — characterising the current pill behaviour as a description of what the code does, not as intentional design. There is no spec statement that the pill should remain visible after target_met=true. The asymmetry between the two guarded nudges (one guarded, one not) is unintentional, not a deliberate product decision.
- Verdict: validated
- Rationale: A learner who has met their CLB 7 goal sees contradictory signals on the same screen — celebration and an urgent practice directive — undermining clarity about their status. The one-line fix (`&& !data.target_met` on line 69) is narrow, low-risk, and aligns the pill with the already-correct card-nudge guard.

## Critic
- Challenge: The strongest case against this fix is that "focus" could be intentionally informational — even after the CLB 7 goal is met, a learner might benefit from knowing which skill is comparatively weakest so they can improve further. Under that reading the pill is a feature, not a bug, and the asymmetry with line 54 is a deliberate choice to show the card nudge only urgently (pre-goal) while the pill persists as a general indicator. I checked `TEF_Platform_Technical_Plan.md` exhaustively — it says nothing either way about pill persistence post-target. I also checked the bar color logic at line 91: `r.best >= target ? "#3ca35a" : weak ? "#e0a03c" : "#4a7fe0"` — when `target_met=true` every skill's `r.best >= target`, so the amber "weak" color is already suppressed correctly. Only the text pill is inconsistent.
- Holds up? Yes. The "informational" argument fails because the pill text is "focus" — an action directive — not "weakest" or "lowest." Rendering an action directive alongside "On target — overall CLB 7" is a genuine contradiction in messaging, not a useful nuance. The card nudge (line 54) and the pill (line 69) are two halves of the same weakest-skill signaling system; the card guard was deliberately added and the pill guard was simply missed. No spec entry or design note mandates asymmetric behavior. The affected moment — a learner's success screen — is the worst place for confusing signals. The fix (`&& !data.target_met` on line 69) is one logical operator mirroring the existing pattern, adds no complexity, and is consistent with the CLAUDE.md DRY/simple principle. The bar color already handles the success state correctly at line 91, so no color regression risk exists.
- Final verdict: validated

Fix: add `&& !data.target_met` to the `weak` variable definition (web/src/screens/Readiness.tsx line 65)
