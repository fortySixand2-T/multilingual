---
id: 1130
title: check_content coverage gate fails without naming the missing deck words
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Copy the repo (incl. content/**/audio) to a temp dir; `PYTHONPATH=$PWD python scripts/check_content.py` -> "content OK" (b1/b2 at 100%).
2. In the copy, `rm content/b1/comprehension/listen-b1-un-voisin-courageux.yaml`.
3. Re-run the script.

## Expected
Gate fails (b1 is locked at 100) and names the deck words no longer covered, so the author can fix them.

## Actual
It fails correctly, but only with a count:
`b1: comprehension uses 545/552 = 98% of the vocab bank, below the 100% floor — add sets, or author them from the theme files`
Seven words are missing and none is listed. With the floor now at 100 for a2/b1/b2, any later edit to a passage/script needs a manual hunt for the dropped word(s).

## Notes
Fix: in check_comprehension_covers_vocab (scripts/check_content.py) append the sorted list of uncovered `strip_article(w.fr)` headwords to the message (at least when pct < floor).


## Triage
- Explanation: check_comprehension_covers_vocab reports only hit/total/pct.
- Against spec: Plan hypothesis H8; gate behavior should be actionable.
- Verdict: validated
- Rationale: With floors at 100 for a2/b1/b2, any passage edit that drops one headword leaves the author hunting a bare count. This round's fixes (1106-1108, 1115 etc.) all risk that. Fix: list the sorted uncovered headwords in the message. Dev tooling, cheap, correct.

## Critic
- Challenge: Dev-tooling only, no learner impact. Counter: the floor is now 100 for a2/b1/b2, so this round's own content edits (1104-1121) can silently drop a deck word and the gate prints only a percentage. Fix is a few lines in check_comprehension_covers_vocab (append sorted missing headwords) and fully contained.
- Holds up? yes
- Final verdict: validated
- Note for dev-fixer: Keep minimal: append the sorted uncovered headwords to the existing message.

Fix: scripts/check_content.py — coverage message lists uncovered headwords; test in tests/test_content_invariants.py.
