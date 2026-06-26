---
id: 392
title: Drill screen hardcodes A1 level, ignores level switcher
severity: medium
area: web
persona: edge-case-breaker
status: done
resolution: partial/by-design — drill backend is a1-only (drill_a1 profile); Drill now shows an explicit 'A1 only' note off-level. Full multi-level drill is a logged backend follow-up
found: 2026-06-25
---

## Steps to reproduce
1. Sign up / log in. Switch the level selector to A2.
2. Navigate to the Practice drill screen.
3. Observe the lesson dropdown only contains A1 lessons (greetings-01, cafe-01, etc.).
4. Switch the level selector between A1 and A2 while on the drill screen. Nothing changes.

## Expected
The Drill screen should read the current level from `useLevel()` and load lessons for that level. When the user switches level, the lesson dropdown should refresh with lessons from the new level.

## Actual
`Drill.tsx` line 12 hardcodes `api.path("a1")` and does not import or use `useLevel()`. The `useEffect` dependency array is empty (`[]`), so it loads once on mount and never reacts to level changes. A2 lessons are never available in the drill screen.

## Notes
Every other skill screen (Path, Comprehension, Writing, Exam) reads `level` from `useLevel()` and passes it to the appropriate API call. The Drill screen was presumably written before the level switcher was added and was not updated. The fix is to import `useLevel`, use `level` in the `api.path()` call, and add `level` to the `useEffect` dependency array.

## Triage
- Explanation: Drill.tsx hardcoded api.path("a1") and used an empty dependency array, so it never reacted to level changes. The backend drill endpoint only has content for A1 (drill_a1 profile), so multi-level drill is not yet possible. The fix imports useLevel() and shows an explicit "A1 only -- more levels coming soon" banner when the user is on a non-A1 level, while keeping the A1 lesson list functional. The path call itself still uses "a1" because that is all the backend supports.
- Against spec: Partially -- the drill being A1-only is a known backend limitation, but the UI gave no indication of this, which is a real UX deficiency. The fix is the correct partial resolution.
- Verdict: validated
- Rationale: Without the banner, users on A2 see A1 lessons with no explanation, creating confusion about whether the level switcher is broken. The fix correctly communicates the limitation while the backend catches up.

## Critic
- Challenge: The drill backend is A1-only by design (drill_a1 profile). The "bug" is that the UI did not communicate this. Is a missing informational banner really a bug, or just a UX enhancement? Verified Drill.tsx: it imports useLevel (line 3, 6) but still hardcodes api.path("a1") on line 14 with an empty dependency array -- the level is only used for the conditional banner on lines 41-45. The fix is appropriate: it does not pretend multi-level drill exists, it just tells the user. Without it, users on A2 see A1 content with zero explanation, which is confusing enough to qualify as a defect rather than a nice-to-have.
- Holds up? Yes -- the banner is the correct partial fix for a known backend limitation. Low complexity, real user confusion addressed.
- Final verdict: done
