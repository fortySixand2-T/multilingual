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
