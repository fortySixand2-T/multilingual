---
id: 448
title: "WeakSpots: user's wrong pick is not highlighted after incorrect answer"
severity: high
area: web
persona: edge-case-breaker
status: done
found: 2026-07-05
---

## Steps to reproduce
1. Sign in and have at least one unresolved weak spot.
2. Navigate to `/weak-spots`.
3. Click a wrong option on any weak-spot card.

## Expected
The button the user clicked should turn red (apply CSS class `option wrong`). The correct answer button should turn green (`option correct`). The `wrong` class is already defined in `styles.css`:
```css
.option.wrong { border-color: var(--coral); background: #fdede9; }
```

## Actual
Only the **correct answer** button is highlighted green (via `isWrongPick` condition, which is misnamed — it marks the correct answer, not the user's wrong pick). The user's wrong selection receives no visual feedback whatsoever — it appears identical to an un-answered option. The `wrong` CSS class is never applied.

Relevant code in `web/src/screens/WeakSpots.tsx` lines 60–65:
```tsx
const isChosenCorrect = g?.correct && g.correct_answer === o;
const isWrongPick = g && !g.correct && g.correct_answer === o;  // highlights correct, NOT wrong pick
return (
  <button
    className={`option ${isChosenCorrect || isWrongPick ? "correct" : ""}`}
```
`isWrongPick` evaluates to true for `g.correct_answer === o`, which is the **correct** answer button, not the wrong one. The component never stores the chosen option locally, so it cannot apply `wrong` styling to the user's click.

## Notes
- The `wrong` CSS class exists in `styles.css` and is used in the Lesson screen, but is unused here.
- Fix requires: (1) store the chosen option in local state (`graded[id].chosen` or a separate `picked` state), then (2) apply class `wrong` when `o === picked && !g.correct`, and (3) rename `isWrongPick` to `isCorrectAnswer` or similar.
- Severity high: the learner cannot tell which option they clicked wrong, making targeted re-practice frustrating and unclear.

## Triage
- Explanation: In `WeakSpots.tsx` lines 60–65, `isWrongPick` is computed as `g && !g.correct && g.correct_answer === o` — this evaluates to true on the **correct answer button** (not the user's selection) when the user answered wrongly. Both `isChosenCorrect` and `isWrongPick` feed into `className={... "correct" : ""}`, so the correct answer is highlighted green but the user's wrong pick receives no class at all. The component never records which option the user actually clicked (`answer()` fires the API call but does not persist `chosen` in local state), so there is no basis to apply `.wrong` styling. The `.option.wrong` CSS rule exists at `styles.css` line 102 and is unused on this screen.
- Against spec: The spec (TEF_Platform_Technical_Plan.md Phase 2 ACs) requires "per-question explanations" but does not explicitly mandate red/green option highlighting for the WeakSpots re-practice screen. However, the Lesson screen already applies `.option.wrong` for the same interaction pattern, establishing a platform-wide UX convention. A learner re-practicing a missed question gets no indication of which button they clicked; the text "Not quite. Answer: X" appears but the visual affordance is absent. This is a real usability deficit, not just cosmetic polish.
- Verdict: validated
- Rationale: The user clicked an option and received zero visual confirmation of which one they chose — only the correct answer lights up. For a "targeted re-practice" feature this breaks the core learning loop: the learner cannot see their error, only the answer. The fix is small and confined to WeakSpots.tsx (store chosen in state, apply `.wrong` class). The bug is confirmed by reading the code; no further info needed.

## Critic
- Challenge: The "Not quite. Answer: X" text feedback is still shown (line 75), so the learner does know what the correct answer is. One could argue that on a re-practice screen — unlike a first-attempt lesson — seeing the correct answer is sufficient, and adding red highlighting is polish not a defect. Also the spec (TEF_Platform_Technical_Plan.md Phase 2 ACs) does not explicitly mandate option-level colour feedback for the WeakSpots screen specifically.
- Holds up? Yes — the challenge does not hold. The Lesson screen, which uses the exact same `.option.wrong` CSS class and the same answer-option rendering pattern, applies red highlighting to the user's chosen button. WeakSpots is a re-practice flow for the same question type; omitting the highlight here is an inconsistency in an established platform UX convention, not a missing spec requirement. More critically, the code attempts to implement this feedback (`isWrongPick` is clearly intended to highlight the wrong pick by name) but does so incorrectly — it highlights the correct answer button instead. This is a code bug, not a deliberate design choice. The learner who clicks option B and sees option A go green receives confusing and contradictory feedback, regardless of the text line below.
- Final verdict: validated

## Fix
Added `picked` state (`Record<number, string>`) to `web/src/screens/WeakSpots.tsx`. In `answer()`, `setPicked` records the chosen option before the API call. Button className logic replaced: `isCorrectAnswer` (green) when `g.correct_answer === o`; `isUserWrongPick` (red) when `!g.correct && picked[w.id] === o`. Old misnamed `isChosenCorrect`/`isWrongPick` variables removed.
