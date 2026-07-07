---
id: 451
title: app/tutor/api.py module docstring still says "A1 drill" after multi-level extension
severity: low
area: tutor
persona: edge-case-breaker
status: fixed
found: 2026-07-06
---

## Steps to reproduce
1. Open `app/tutor/api.py`.
2. Read line 1: `"""Tutor API: generate a scaffolded A1 drill for a lesson."""`
3. Note that the implementation now supports levels a1, a2, b1, and b2.

## Expected
The module docstring should accurately describe the current scope — i.e., that it
generates a scaffolded drill for lessons at levels a1 through b2, deriving the
correct prompt/profile from the lesson's own level.

## Actual
The docstring reads:

```
"""Tutor API: generate a scaffolded A1 drill for a lesson."""
```

This is copy-paste residue from before the multi-level extension. A developer
reading this file cold will conclude the endpoint only handles A1 and may not
realise that the level derivation logic now covers a2/b1/b2. The mismatch
between docstring and implementation increases the maintenance risk (e.g.
someone mistakenly re-hardcodes to a1 thinking the docstring is authoritative).

## Notes
- File: `app/tutor/api.py`, line 1.
- Change summary says "derives level from lesson (was hardcoded a1)" — the
  docstring was never updated to match.
- Fix: replace the docstring with something like:
  `"""Tutor API: generate a scaffolded drill for a lesson at any supported level (a1–b2)."""`

## Triage

- status: validated
- severity: low
- investigator: qa-pm

### Finding
Confirmed: `app/tutor/api.py` line 1 reads `"""Tutor API: generate a scaffolded A1 drill for a lesson."""` while the implementation at line 46 derives level dynamically via `Tutor(ai_router, level=lesson.level)` supporting a1, a2, b1, and b2. This is not a user-visible bug — the API behaves correctly — but the stale docstring is a genuine maintainability risk: a developer reading the file cold could conclude the endpoint is A1-only and re-hardcode it, introducing a real regression. The fix is a one-line docstring change with zero risk of breakage, making the cost-benefit clearly in favour of fixing.

## Critic

- status: rejected
- critic: qa-critic

### Assessment
The PM's "re-hardcoding" risk is theoretical and not supported by the file's actual content. Lines 43-44 of `api.py` carry an explicit inline comment — "Level-gated drills for every shipped level — the lesson's own level picks the scaffolded prompt/profile" — that any developer reading past line 1 would encounter before acting on the module docstring. The stale module-level string is cosmetic residue; it does not mislead a careful reader, and it has zero runtime impact. Validating a pure cosmetic comment fix as a maintainability hazard conflates documentation hygiene with an actionable defect. By the project's own CLAUDE.md rule of simplicity and DRY, this issue is better handled via a general "clean up stale docstrings" pass rather than a targeted fix that implies higher risk than exists. Verdict: rejected — the existing inline comment makes the PM's hypothetical regression path implausible, and the issue does not meet the bar for a dev-fixer ticket.
