import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Grammar from "./Grammar";
import { api } from "../api";

vi.mock("../api", () => ({ api: { grammar: vi.fn() } }));
vi.mock("../level", () => ({ useLevel: () => ({ level: "b2" }) }));

const item = (id: string, category: string, point: string) => ({
  unit_id: "u1",
  unit_title: "Unit One",
  lesson_id: id,
  lesson_title: `Lesson ${id}`,
  grammar_point: point,
  grammar_category: category,
});

const items = [
  item("l1", "Subjunctive", "le subjonctif présent"),
  item("l2", "Verb conjugation & tenses", "le futur simple"),
  item("l3", "Subjunctive", "le subjonctif passé"),
  item("l4", "", "un point sans catégorie"), // uncategorized → "Other"
];

const renderGrammar = () => {
  const utils = render(
    <MemoryRouter>
      <Grammar />
    </MemoryRouter>,
  );
  const groupTitles = () =>
    Array.from(utils.container.querySelectorAll(".unit-title")).map((n) => n.textContent);
  return { ...utils, groupTitles };
};

beforeEach(() => {
  vi.mocked(api.grammar).mockResolvedValue({ level: "b2", items } as never);
});

describe("Grammar reference", () => {
  it("groups points by category in canonical order, bucketing uncategorized under Other", async () => {
    const { groupTitles } = renderGrammar();
    await screen.findByText("le subjonctif présent");
    // Verb conjugation precedes Subjunctive in canonical order; Other is last; no dupes.
    expect(groupTitles()).toEqual(["Verb conjugation & tenses", "Subjunctive", "Other"]);
  });

  it("filters to a single category when its chip is clicked", async () => {
    const user = userEvent.setup();
    const { groupTitles } = renderGrammar();
    await user.click(await screen.findByRole("button", { name: "Subjunctive" }));
    expect(groupTitles()).toEqual(["Subjunctive"]);
    expect(screen.getByText("le subjonctif présent")).toBeInTheDocument();
    expect(screen.queryByText("le futur simple")).not.toBeInTheDocument();
  });

  it("text search narrows alongside the active category filter", async () => {
    const user = userEvent.setup();
    const { groupTitles } = renderGrammar();
    await user.click(await screen.findByRole("button", { name: "Subjunctive" }));
    await user.type(screen.getByPlaceholderText("Search grammar…"), "passé");
    expect(groupTitles()).toEqual(["Subjunctive"]);
    expect(screen.getByText("le subjonctif passé")).toBeInTheDocument();
    expect(screen.queryByText("le subjonctif présent")).not.toBeInTheDocument();
  });
});
