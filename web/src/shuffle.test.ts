import { describe, it, expect } from "vitest";
import { shuffled, shuffleExercise, shuffleLesson } from "./shuffle";
import { Exercise } from "./api";

// A deterministic RNG that yields the given values in order (then repeats the last).
const mkRng = (vals: number[]) => {
  let i = 0;
  return () => vals[Math.min(i++, vals.length - 1)];
};

describe("shuffled", () => {
  it("is a permutation — same elements, same length", () => {
    const a = [1, 2, 3, 4, 5];
    const s = shuffled(a, mkRng([0.9, 0.1, 0.5, 0.3]));
    expect([...s].sort((x, y) => x - y)).toEqual(a);
    expect(s).toHaveLength(a.length);
  });

  it("does not mutate its input", () => {
    const a = [1, 2, 3];
    const copy = [...a];
    shuffled(a, mkRng([0.5, 0.5]));
    expect(a).toEqual(copy);
  });

  it("is deterministic given a fixed RNG", () => {
    // Fisher–Yates with rnd()===0 swaps each element with index 0.
    expect(shuffled([1, 2, 3, 4], () => 0)).toEqual([2, 3, 4, 1]);
  });
});

describe("shuffleExercise — never changes what's correct", () => {
  it("shuffles mcq options but keeps the answer in the set", () => {
    const ex = {
      id: "e1",
      type: "mcq",
      prompt: "p",
      options: ["un café", "une café", "un eau"],
      answer: "un café",
    } as unknown as Exercise;
    const out = shuffleExercise(ex, mkRng([0.99, 0.01]));
    expect([...(out.options as string[])].sort()).toEqual([...ex.options].sort());
    expect(out.answer).toBe("un café");
    expect(out.options).toContain(out.answer);
  });

  it("shuffles word_bank tokens but leaves the answer sequence intact", () => {
    const ex = {
      id: "e2",
      type: "word_bank",
      prompt: "p",
      tokens: ["Le", "menu", "merci"],
      answer: ["Le", "menu"],
    } as unknown as Exercise;
    const out = shuffleExercise(ex, mkRng([0.5, 0.2]));
    expect([...(out.tokens as string[])].sort()).toEqual([...ex.tokens].sort());
    expect(out.answer).toEqual(["Le", "menu"]);
    // every answer token is still available in the (shuffled) bank
    for (const t of out.answer as string[]) expect(out.tokens).toContain(t);
  });

  it("returns other exercise types unchanged", () => {
    const ex = { id: "e3", type: "translate", prompt: "p", answer: "x" } as unknown as Exercise;
    expect(shuffleExercise(ex)).toBe(ex);
  });
});

describe("shuffleLesson", () => {
  it("keeps the same exercises (by id), only varies order/presentation", () => {
    const exercises = [
      { id: "a", type: "mcq", prompt: "p", options: ["1", "2"], answer: "1" },
      { id: "b", type: "translate", prompt: "p", answer: "x" },
      { id: "c", type: "mcq", prompt: "p", options: ["3", "4"], answer: "4" },
    ] as unknown as Exercise[];
    const out = shuffleLesson(exercises, mkRng([0.1, 0.8, 0.4, 0.6]));
    expect(out).toHaveLength(3);
    expect(out.map((e) => e.id).sort()).toEqual(["a", "b", "c"]);
    // each mcq still contains its own answer
    for (const e of out) {
      if (e.type === "mcq") expect(e.options).toContain(e.answer);
    }
  });
});
