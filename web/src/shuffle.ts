// Presentation variety for lessons: the content is authored once and static, but we
// vary the *order* each time a lesson is opened so practice stays fresh and learners
// can't game answers by position ("it's always the 2nd option").
//
// All exercise grading compares by VALUE, not index (e.g. Mcq checks `sel === answer`),
// so shuffling the presentation can never change what counts as correct.

import { Exercise } from "./api";

/** Fisher–Yates shuffle. Pure: returns a new array; RNG is injectable for tests. */
export function shuffled<T>(arr: readonly T[], rnd: () => number = Math.random): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Return a copy of an exercise with its presentation order varied, without changing
 * what counts as correct:
 *   - mcq        → shuffle `options`
 *   - word_bank  → shuffle the `tokens` tile bank (the `answer` order is the sentence
 *                  and is left untouched)
 * Other types (translate, match_pairs, listen_type) are returned unchanged —
 * match_pairs already shuffles its own column at render time.
 */
export function shuffleExercise(ex: Exercise, rnd: () => number = Math.random): Exercise {
  if (ex.type === "mcq" && Array.isArray(ex.options)) {
    return { ...ex, options: shuffled(ex.options as unknown[], rnd) };
  }
  if (ex.type === "word_bank" && Array.isArray(ex.tokens)) {
    return { ...ex, tokens: shuffled(ex.tokens as unknown[], rnd) };
  }
  return ex;
}

/** Shuffle the order of a lesson's exercises and each exercise's presentation. */
export function shuffleLesson(exercises: Exercise[], rnd: () => number = Math.random): Exercise[] {
  return shuffled(exercises, rnd).map((ex) => shuffleExercise(ex, rnd));
}
