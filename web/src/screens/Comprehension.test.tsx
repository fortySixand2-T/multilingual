import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Comprehension from "./Comprehension";
import { api } from "../api";

vi.mock("../api", () => ({ api: { comprehensionSets: vi.fn() } }));
vi.mock("../level", () => ({ useLevel: () => ({ level: "b1" }) }));

const set = (id: string, title: string, exam: "tef" | "tcf", topic: string | null = null) => ({
  id, title, exam, topic, skill: "reading" as const, accent: null, time_limit_seconds: 360, allow_replay: true, questions: 4,
});

describe("Read & Listen", () => {
  it("groups TCF sets apart from TEF reading, with their topic", async () => {
    vi.mocked(api.comprehensionSets).mockResolvedValue({
      sets: [set("read-b1-x", "Un texte TEF", "tef"), set("tcf-b1-logement", "TCF · Se loger", "tcf", "logement")],
    });
    render(
      <MemoryRouter>
        <Comprehension />
      </MemoryRouter>,
    );

    const tcf = (await screen.findByText("TCF reading")).closest(".unit") as HTMLElement;
    expect(within(tcf).getByText("TCF · Se loger")).toBeInTheDocument();
    expect(within(tcf).getByText(/logement/)).toBeInTheDocument();
    expect(within(tcf).queryByText("Un texte TEF")).not.toBeInTheDocument();
    const tef = screen.getByText("Reading").closest(".unit") as HTMLElement;
    expect(within(tef).getByText("Un texte TEF")).toBeInTheDocument();
  });
});
