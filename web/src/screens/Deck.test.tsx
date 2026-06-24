import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Deck from "./Deck";
import { api } from "../api";

// Deck uses api.vocab / api.setKnown; AudioButton (for cards with audio) uses fetchAudioUrl.
vi.mock("../api", () => ({
  api: {
    vocab: vi.fn(),
    setKnown: vi.fn(() => Promise.resolve({})),
    addToReview: vi.fn(() => Promise.resolve({ added: true })),
  },
  fetchAudioUrl: vi.fn(),
}));

const cards = [
  { id: "bonjour", fr: "bonjour", en: "hello", audio: "a1/audio/bonjour.mp3", tags: ["greeting"] },
  { id: "salut", fr: "salut", en: "hi", tags: ["greeting"] },
];

const renderDeck = (path = "/vocab/a1/greeting") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/vocab/:level/:tag" element={<Deck />} />
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
    expect(screen.getByText(/You know 2 \/ 2/)).toBeInTheDocument();
  });

  it("the All-words deck fetches the whole level (no tag filter)", async () => {
    renderDeck("/vocab/a1/all");
    await screen.findByText(/^(bonjour|salut)$/);
    expect(vi.mocked(api.vocab)).toHaveBeenCalledWith("a1", undefined);
  });

  it("marks known, bumps the counter, and persists", async () => {
    const user = userEvent.setup();
    renderDeck();
    await screen.findByText(/^(bonjour|salut)$/);
    expect(screen.getByText("✓ 0 / 2 known")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show meaning" }));
    await user.click(screen.getByRole("button", { name: "Knew it" }));

    expect(screen.getByText("✓ 1 / 2 known")).toBeInTheDocument();
    expect(vi.mocked(api.setKnown)).toHaveBeenCalledWith(expect.any(String), true);
  });

  it("resets a word with 'Still learning' (persists known=false)", async () => {
    const user = userEvent.setup();
    renderDeck();
    await screen.findByText(/^(bonjour|salut)$/);

    await user.click(screen.getByRole("button", { name: "Show meaning" }));
    await user.click(screen.getByRole("button", { name: "Still learning" }));

    expect(vi.mocked(api.setKnown)).toHaveBeenCalledWith(expect.any(String), false);
  });

  it("adds a card to review and reflects it on the button", async () => {
    const user = userEvent.setup();
    renderDeck();
    await screen.findByText(/^(bonjour|salut)$/);

    await user.click(screen.getByRole("button", { name: /Add to review/ }));

    expect(vi.mocked(api.addToReview)).toHaveBeenCalledWith(expect.any(String));
    expect(screen.getByRole("button", { name: /In review/ })).toBeInTheDocument();
  });
});
