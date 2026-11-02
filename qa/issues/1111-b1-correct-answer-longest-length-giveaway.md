---
id: 1111
title: Four B1 sets: the correct option is usually the longest (length giveaway)
severity: medium
area: comprehension
persona: returning-learner
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/read-b1-bien-s-installer (source: content/b1/comprehension/read-b1-bien-s-installer.yaml).
2. Read the passage/script and questions as a native French reviewer.

Also affects read-b1-cafe-philo, listen-b1-un-voisin-courageux, listen-b1-message-de-la-directrice.

## Expected
Options of comparable length so test-wise guessing fails.

## Actual
Correct answer is strictly the longest option in: bien-s-installer q2 (41 vs ~25/~29 chars), q3, q4; cafe-philo q1 (36 vs 23/22), q2 (41 vs 36/31), q3 (39 vs 31/32); un-voisin-courageux q1, q2, q3 (all by 4-10 chars); message-de-la-directrice q1 (37 vs 25/31), q2 (40 vs 22/24). 'Always pick the longest' scores about 12/17 questions across these sets. Lengthen distractors, e.g. bien-s-installer q4: « Rentrer en France chaque hiver » -> « Partir en voyage dans le sud chaque hiver ».



## Triage
- Explanation: Duplicate of 1120 (same length-giveaway pattern, B1 subset).
- Against spec: n/a (duplicate).
- Verdict: rejected
- Rationale: Consolidated into 1120, which covers all 7 new sets. See 1120 for the corpus baseline.

## Critic
- Challenge: Pure duplicate of 1120.
- Holds up? yes
- Final verdict: rejected
- Note: Duplicate of 1120.
