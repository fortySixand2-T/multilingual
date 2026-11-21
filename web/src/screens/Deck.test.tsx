import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Deck from "./Deck";
import { api } from "../api";

// Deck uses api.vocab / api.setKnown; AudioButton (for cards with audio) uses fetchAudioUrl.
// On flip it also renders <WordDetail defaultOpen>, which hydrates via api.vocabExtra
// (and, for inflecting words, api.vocabForms) — mock them so that auto-load resolves.
vi.mock("../api", () => ({
  api: {
    vocab: vi.fn(),
    setKnown: vi.fn(() => Promise.resolve({})),
    addToReview: vi.fn(() => Promise.resolve({ added: true })),
    vocabExtra: vi.fn(() => Promise.resolve({ forms: null, examples: [] })),
    vocabForms: vi.fn(() => Promise.resolve({ forms: [], cached: true })),
    vocabExamples: vi.fn(() =>
      Promise.resolve({ examples: [{ fr: "Bonjour, ça va ?", en: "Hello, how are you?" }] }),
    ),
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
        <Route path="/vocab/:level/verbs/:group" element={<Deck />} />
        <Route path="/vocab/:level/tcf/:topic" element={<Deck />} />
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

  it("auto-opens the forms & examples panel on flip — no separate expander click", async () => {
    const user = userEvent.setup();
    renderDeck();
    await screen.findByText(/^(bonjour|salut)$/);

    // collapsed toggle is not shown before flipping…
    expect(screen.queryByRole("button", { name: /Forms & examples/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show meaning" }));

    // …and still not shown after: the panel is already open, hydrated directly, and
    // an example is auto-generated — no expander and no "Get examples" press.
    expect(screen.queryByRole("button", { name: /Forms & examples/ })).not.toBeInTheDocument();
    expect(await screen.findByText("Bonjour, ça va ?")).toBeInTheDocument();
    expect(vi.mocked(api.vocabExtra)).toHaveBeenCalled();
    expect(vi.mocked(api.vocabExamples)).toHaveBeenCalled();
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

  it("a verb deck holds its group's verbs and shows the present tense on flip", async () => {
    const user = userEvent.setup();
    const aller = {
      id: "aller",
      fr: "aller",
      en: "to go",
      pos: "verb",
      verb_group: "irregular",
      conjugation: [["je", "vais"], ["tu", "vas"], ["il / elle / on", "va"]],
    };
    const parler = { ...aller, id: "parler", fr: "parler", en: "to speak", verb_group: "regular" };
    vi.mocked(api.vocab).mockResolvedValue({ cards: [aller, parler] } as never);
    renderDeck("/vocab/a1/verbs/irregular");

    expect(await screen.findByText("aller")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 1 · irregular verbs/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show meaning" }));
    expect(screen.getByRole("rowheader", { name: "il / elle / on" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "vais" })).toBeInTheDocument();
    expect(api.vocabForms).not.toHaveBeenCalled(); // the checked table, not the model's
  });

  it("a TCF topic deck gathers its words from every level", async () => {
    const tcf = [{ level: "b1", topic: "santé" }];
    vi.mocked(api.vocab).mockResolvedValue({
      cards: [
        { id: "pharmacie", fr: "pharmacie", en: "pharmacy", level: "a2", tcf_decks: tcf },
        { id: "vaccination", fr: "vaccination", en: "vaccination", level: "b1", tcf_decks: tcf },
        { id: "loyer", fr: "loyer", en: "rent", level: "a2", tcf_decks: [{ level: "b1", topic: "logement" }] },
        { id: "chien", fr: "chien", en: "dog", level: "a1" },
      ],
    } as never);
    renderDeck(`/vocab/b1/tcf/${encodeURIComponent("santé")}`);

    expect(await screen.findByText(/1 \/ 2 · TCF · santé/)).toBeInTheDocument();
    expect(api.vocab).toHaveBeenCalledWith(); // every level, not just b1
  });

  it("a theme deck leaves its verbs to the Verbs decks", async () => {
    vi.mocked(api.vocab).mockResolvedValue({
      cards: [
        { id: "maison", fr: "maison", en: "house", pos: "noun", tags: ["house"] },
        { id: "habiter", fr: "habiter", en: "to live", pos: "verb", verb_group: "regular", tags: ["house"] },
      ],
    } as never);
    renderDeck("/vocab/a1/house");
    expect(await screen.findByText(/1 \/ 1 · house/)).toBeInTheDocument();
    expect(screen.getByText("maison")).toBeInTheDocument();
  });

  it("the All words deck still has the verbs", async () => {
    vi.mocked(api.vocab).mockResolvedValue({
      cards: [
        { id: "maison", fr: "maison", en: "house", pos: "noun", tags: ["house"] },
        { id: "habiter", fr: "habiter", en: "to live", pos: "verb", verb_group: "regular", tags: ["house"] },
      ],
    } as never);
    renderDeck("/vocab/a1/all");
    expect(await screen.findByText(/1 \/ 2 · all words/)).toBeInTheDocument();
  });
});
