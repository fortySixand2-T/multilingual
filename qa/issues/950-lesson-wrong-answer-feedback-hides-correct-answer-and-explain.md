---
id: 950
title: Lesson wrong-answer feedback shows only "Not quite" - correct answer and authored explain never shown
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Sign up (invite qa061-b), open any lesson, e.g. A1 People 01 (`/lesson/people-01`), 375px wide.
2. On the "Translate: What is your name? (formal)" exercise type a wrong answer (e.g. `comment vous appelez-vous`) and tap Check.
3. On the MCQ "« ___ garçon »" tap `une` then Check.

## Expected
After a wrong answer a beginner is told what the right answer is and why (the YAML carries an `explain` string per mcq, e.g. "garçon is masculine -> un garçon").

## Actual
Translate: red box "Not quite - keep going." and a Continue button; the expected French is never revealed, so the learner moves on having learned nothing. MCQ: the correct option is outlined green but the `explain` text is not rendered anywhere (`web/src/screens/Lesson.tsx` feedback block only prints "Correct!" / "Not quite - keep going."). The new vocab lessons (PRs #124-#129) carry `explain` strings on every mcq that are therefore dead content. Lesson then ended at "Almost there - 6 / 8" with no hint what to fix.

## Notes
Generic to all lessons but most painful for a zero-French learner. Weak spots screen does print `Answer: ...`, so the pattern exists.


## Triage
- Explanation: Lesson.tsx feedback block prints only 'Correct!' / 'Not quite — keep going.'; grep finds no use of the exercise's explain field or the correct answer on wrong translate/mcq.
- Against spec: Learner-facing feedback should show the correct answer and why; Weak spots already prints 'Answer: ...'.
- Verdict: validated
- Rationale: Every wrong answer teaches nothing and authored explain strings are dead content. Highest-value item in this batch: render explain (and expected answer on wrong translate) in the feedback block.

## Critic
- Challenge: Maybe a deliberate minimal UX.
- Holds up? Verified Lesson.tsx:99-102 shows only Correct!/Not quite; explain strings and expected answer never rendered. Real learner impact; highest value.
- Final verdict: validated

## Fix
Lesson.tsx feedback now shows 'Answer: ...' for wrong typed/built answers and the authored explain; tests in Lesson.test.tsx.
