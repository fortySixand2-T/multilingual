import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Path from "./Path";
import { api } from "../api";

vi.mock("../api", () => ({ api: { path: vi.fn(), me: vi.fn() } }));
vi.mock("../level", () => ({ useLevel: () => ({ level: "a1" }) }));

const pathView = {
  level: "a1",
  units: [
    {
      id: "u1",
      title: "First contact",
      icon: "wave",
      lessons: ["l1"],
      unlock: { type: "always", requires: [] },
      status: "available" as const,
    },
  ],
  passed_lessons: [],
  waived_lessons: [],
};

beforeEach(() => {
  vi.mocked(api.path).mockResolvedValue(pathView as never);
  vi.mocked(api.me).mockRejectedValue(new Error("no me"));
});

const me = (over: Partial<Record<string, unknown>> = {}) => ({
  user_id: 1,
  level: "a1",
  xp: 120,
  streak: 3,
  last_active: null,
  xp_today: 12,
  daily_goal: 30,
  ...over,
});

describe("Path home hub (qa-490)", () => {
  it("shows a visible 'Practice & tools' heading above the tool grid", async () => {
    render(
      <MemoryRouter>
        <Path />
      </MemoryRouter>,
    );
    const heading = await screen.findByRole("heading", { name: "Practice & tools" });
    const nav = screen.getByRole("navigation", { name: "Practice & tools" });
    // The heading must be visible markup (not just the nav's aria-label).
    expect(heading.textContent).toBe("Practice & tools");
    expect(nav).toBeInTheDocument();
  });
});

describe("Daily goal ring", () => {
  it("shows progress toward the goal when unmet", async () => {
    vi.mocked(api.me).mockResolvedValue(me() as never);
    render(
      <MemoryRouter>
        <Path />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Daily goal")).toBeInTheDocument();
    expect(screen.getByText("12 / 30 XP today")).toBeInTheDocument();
  });

  it("celebrates when the goal is reached", async () => {
    vi.mocked(api.me).mockResolvedValue(me({ xp_today: 30 }) as never);
    render(
      <MemoryRouter>
        <Path />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Daily goal reached!")).toBeInTheDocument();
  });
});
