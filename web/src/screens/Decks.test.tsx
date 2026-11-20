import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Decks from "./Decks";
import { api } from "../api";

vi.mock("../api", () => ({ api: { vocab: vi.fn() } }));

describe("Vocabulary decks", () => {
  it("shows one TCF topic deck per reading set, counting its words across levels", async () => {
    const sante = [{ level: "b1", topic: "santé" }];
    vi.mocked(api.vocab).mockResolvedValue({
      cards: [
        { id: "pharmacie", fr: "pharmacie", en: "pharmacy", level: "a2", tags: ["sante"], tcf_decks: sante },
        { id: "vaccination", fr: "vaccination", en: "vaccination", level: "b1", tags: ["health"], tcf_decks: sante },
        { id: "chien", fr: "chien", en: "dog", level: "a1", tags: ["animals"] },
      ],
    } as never);
    render(
      <MemoryRouter>
        <Decks />
      </MemoryRouter>,
    );

    expect(await screen.findByText("TCF topics")).toBeInTheDocument();
    const tile = screen.getByText("santé").closest("a") as HTMLAnchorElement;
    expect(tile).toHaveAttribute("href", `/vocab/b1/tcf/${encodeURIComponent("santé")}`);
    expect(tile).toHaveTextContent("2 cards");
  });
});
