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
