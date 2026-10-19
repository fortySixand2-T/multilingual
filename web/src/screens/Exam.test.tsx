import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Exam from "./Exam";
import { api } from "../api";

vi.mock("../api", () => ({
  api: {
    examBlueprints: vi.fn(),
    examHistory: vi.fn(),
    examStart: vi.fn(),
    examSection: vi.fn(),
    examFinish: vi.fn(),
    examAttempt: vi.fn(),
  },
}));
vi.mock("../level", () => ({ useLevel: () => ({ level: "a1" }) }));

const groupTitles = (container: HTMLElement) =>
  Array.from(container.querySelectorAll(".unit-title")).map((n) => n.textContent);

const delfBlueprint = {
  id: "delf-a1-1",
  level: "a1",
  title: "DELF A1 — examen blanc 1",
  format: "delf" as const,
  sections: [
    { skill: "reading" as const, time_limit_seconds: 1800, comprehension_set_ids: ["read-a", "read-b"] },
    { skill: "speaking" as const, time_limit_seconds: 1020, speaking_prompts: ["Entretien dirigé", "Dialogue simulé"] },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  // the TEF Canada mock is fetched once for every level; the level fetch holds DELF + practice
  vi.mocked(api.examBlueprints).mockImplementation(async (level) => ({
    blueprints:
      level === "tef"
        ? [{ id: "tef-1", title: "TEF Canada — examen blanc 1", sections: 4, format: "tef" }]
        : [
            { id: "delf-a1-1", title: "DELF A1 — examen blanc 1", sections: 4, format: "delf" },
            { id: "mock-1", title: "Level practice — A1", sections: 4, format: "tef" },
          ],
  }));
  vi.mocked(api.examHistory).mockResolvedValue({ attempts: [] });
});

describe("Exam", () => {
  it("separates the cross-level TEF exam from the per-level DELF and practice mocks", async () => {
    const { container } = render(<Exam />);
    await screen.findByText("TEF Canada — examen blanc 1");
    expect(groupTitles(container)).toEqual(["TEF Canada — full exam", "DELF A1", "Level practice"]);
    expect(api.examBlueprints).toHaveBeenCalledWith("tef");
    expect(api.examBlueprints).toHaveBeenCalledWith("a1");
  });

  it("runs a DELF mock: a link per document, the speaking tasks, /25 scores and a pass/fail result", async () => {
    const user = userEvent.setup();
    vi.mocked(api.examStart).mockResolvedValue({ attempt_id: 7, blueprint: delfBlueprint });
    vi.mocked(api.examSection).mockResolvedValue({ skill: "x", clb: null, score: 1, recorded: [] });
    vi.mocked(api.examFinish).mockResolvedValue({
      attempt_id: 7,
      xp: 25,
      streak: 1,
      report: {
        format: "delf",
        per_skill: { reading: 20, speaking: 4 },
        total: 24,
        max: 50,
        passed: false,
        note: "Estimate only — not an official DELF result.",
      },
    });

    render(<Exam />);
    await user.click(await screen.findByText("DELF A1 — examen blanc 1"));

    expect(screen.getByRole("link", { name: /Document 1/ })).toHaveAttribute("href", "/comprehension/read-a");
    expect(screen.getByRole("link", { name: /Document 2/ })).toHaveAttribute("href", "/comprehension/read-b");
    expect(screen.getByText("Dialogue simulé")).toBeInTheDocument();

    const [readingRecord, speakingRecord] = screen.getAllByRole("button", { name: "Record" });
    await user.type(screen.getByPlaceholderText("correct"), "8");
    await user.type(screen.getByPlaceholderText("total"), "10");
    await user.click(readingRecord);

    // speaking takes points on the DELF grid, not a CLB band; out-of-range can't be recorded
    const points = screen.getByPlaceholderText("points");
    await user.type(points, "26");
    expect(speakingRecord).toBeDisabled();
    await user.clear(points);
    await user.type(points, "4");
    await user.click(speakingRecord);
    expect(api.examSection).toHaveBeenLastCalledWith(7, { skill: "speaking", score: 4 });

    await user.click(screen.getByRole("button", { name: "Finish & see DELF result" }));
    expect(await screen.findByText("24 / 50")).toBeInTheDocument();
    expect(screen.getByText(/Not yet/)).toBeInTheDocument();
    expect(screen.getByText("speaking: 4/25")).toBeInTheDocument();
  });
});
