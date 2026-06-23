import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Deck from "./Deck";
import { api } from "../api";

// Deck uses api.vocab; AudioButton (rendered for cards with audio) uses fetchAudioUrl.
vi.mock("../api", () => ({
  api: { vocab: vi.fn() },
  fetchAudioUrl: vi.fn(),
}));

const cards = [
  { id: "bonjour", fr: "bonjour", en: "hello", audio: "a1/audio/bonjour.mp3", tags: ["greeting"] },
  { id: "salut", fr: "salut", en: "hi", tags: ["greeting"] },
];

const renderDeck = () =>
  render(
    <MemoryRouter initialEntries={["/vocab/greeting"]}>
      <Routes>
        <Route path="/vocab/:tag" element={<Deck />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.mocked(api.vocab).mockResolvedValue({ level: "a1", cards } as never);
});

describe("Deck flashcards", () => {
  it("hides the meaning until the card is flipped", async () => {
    const user = userEvent.setup();
    renderDeck();

    // a French word from the deck shows (order is shuffled — match either)
    expect(await screen.findByText(/^(bonjour|salut)$/)).toBeInTheDocument();
    expect(screen.queryByText(/^(hello|hi)$/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show meaning" }));
    expect(screen.getByText(/^(hello|hi)$/)).toBeInTheDocument();
  });

  it("advances through every card to a completion summary", async () => {
    const user = userEvent.setup();
    renderDeck();
    await screen.findByText(/^(bonjour|salut)$/);

    for (let i = 0; i < cards.length; i++) {
      await user.click(screen.getByRole("button", { name: "Show meaning" }));
      await user.click(screen.getByRole("button", { name: "Knew it" }));
    }

    expect(await screen.findByText("Deck complete")).toBeInTheDocument();
    expect(screen.getByText(/You knew 2 \/ 2/)).toBeInTheDocument();
  });
});
