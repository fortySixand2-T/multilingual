import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Lesson from "./Lesson";
import { api } from "../api";

// Mock the API module: Lesson uses `api.lesson` / `api.submitResult`; AudioButton
// (imported transitively) uses `fetchAudioUrl`.
vi.mock("../api", () => ({
  api: { lesson: vi.fn(), submitResult: vi.fn() },
  fetchAudioUrl: vi.fn(),
}));

const mcqLesson = {
  id: "greetings-01",
  title: "Saying hello",
  est_minutes: 4,
  exercises: [
    {
      id: "greetings-01.e1",
      type: "mcq",
      prompt: "Which is a formal greeting?",
      options: ["salut", "bonjour", "coucou"],
      answer: "bonjour",
      explain: "bonjour is formal.",
    },
  ],
};

const renderLesson = () =>
  render(
    <MemoryRouter initialEntries={["/lesson/greetings-01"]}>
      <Routes>
        <Route path="/lesson/:id" element={<Lesson />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.mocked(api.lesson).mockResolvedValue(mcqLesson as never);
});

describe("Lesson — MCQ grading is unaffected by option shuffling", () => {
  it("renders all options and marks the correct one right (wherever shuffle placed it)", async () => {
    const user = userEvent.setup();
    renderLesson();

    // prompt + all three options render regardless of shuffled order
    expect(await screen.findByText("Which is a formal greeting?")).toBeInTheDocument();
    for (const o of ["salut", "bonjour", "coucou"]) {
      expect(screen.getByRole("button", { name: o })).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "bonjour" }));
    await user.click(screen.getByRole("button", { name: "Check" }));

    expect(screen.getByText("Correct!")).toBeInTheDocument();
  });

  it("marks a wrong choice incorrect", async () => {
    const user = userEvent.setup();
    renderLesson();

    await screen.findByText("Which is a formal greeting?");
    await user.click(screen.getByRole("button", { name: "salut" }));
    await user.click(screen.getByRole("button", { name: "Check" }));

    expect(screen.getByText(/Not quite/)).toBeInTheDocument();
  });
});

const typedLesson = (ex: Record<string, unknown>) =>
  vi.mocked(api.lesson).mockResolvedValue({ id: "l", title: "T", exercises: [{ id: "l.e1", ...ex }] } as never);

describe("Lesson — typed answers and feedback", () => {
  it("accepts an unspaced question/exclamation mark", async () => {
    typedLesson({ type: "translate", prompt: "Stop!", answer: "arrête !" });
    const user = userEvent.setup();
    renderLesson();
    await user.type(await screen.findByPlaceholderText("traduisez…"), "Arrête!");
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(screen.getByText("Correct!")).toBeInTheDocument();
  });

  it("shows the expected answer after a wrong translation", async () => {
    typedLesson({ type: "translate", prompt: "Name?", answer: "quel est votre nom ?" });
    const user = userEvent.setup();
    renderLesson();
    await user.type(await screen.findByPlaceholderText("traduisez…"), "nope");
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(screen.getByText("quel est votre nom ?")).toBeInTheDocument();
  });

  it("shows the authored explain after a wrong mcq", async () => {
    typedLesson({ type: "mcq", prompt: "___ garçon", options: ["un", "une"], answer: "un", explain: "garçon is masculine." });
    const user = userEvent.setup();
    renderLesson();
    await user.click(await screen.findByRole("button", { name: "une" }));
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(screen.getByText("garçon is masculine.")).toBeInTheDocument();
  });
});
