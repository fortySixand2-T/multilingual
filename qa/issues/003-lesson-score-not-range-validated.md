---
id: 003
title: Lesson result accepts out-of-range scores (5.0 "passes", -1 accepted)
severity: medium
area: progress
persona: edge-case-breaker
status: done
found: 2026-06-16
---

## Steps to reproduce
1. Sign up / log in, get a token.
2. `POST /progress/lessons/greetings-01/result` with `{"score": 5.0}`
3. Also try `{"score": -1}`

## Expected
`score` validated to the 0.0–1.0 range → 422 on 5.0 and -1.

## Actual
`score: 5.0` → `{"passed": true, ...}` (trivially passes, awards XP, unlocks gating).
`score: -1` → processed as a fail. Both return 200.

## Notes
`LessonResultBody.score` is an unbounded float. Constrain it
(`Field(ge=0.0, le=1.0)`). A client bug or tampering can fake completion/XP.
Same pattern likely applies to comprehension `elapsed_seconds` (negative?).
