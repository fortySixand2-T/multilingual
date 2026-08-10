import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import MyDeck from "./MyDeck";
import { api } from "../api";

// MyDeck uses api.myDeck / personalPreview / personalAdd; AudioButton uses fetchAudioUrl.
vi.mock("../api", () => ({
  api: {
    myDeck: vi.fn(),
    personalPreview: vi.fn(),
    personalAdd: vi.fn(),
    // WordDetail (rendered under each card) uses these; collapsed on render so unused here
    vocabExtra: vi.fn(),
    vocabForms: vi.fn(),
    vocabExamples: vi.fn(),
  },
  fetchAudioUrl: vi.fn(),
}));

const renderMyDeck = () =>
  render(
    <MemoryRouter>
      <MyDeck />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.myDeck).mockResolvedValue({ cards: [] });
});

describe("MyDeck — add a word", () => {
  it("looks up a word, then confirms it into the deck", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalPreview).mockResolvedValue({
      enrichment: { fr: "silence", en: "quietness", pos: "noun", gender: "m", ipa: "silɑ̃s", gender_source: "table" },
    });
    vi.mocked(api.personalAdd).mockResolvedValue({
      card: { card_key: "uv:silence", fr: "silence", en: "quietness", gender: "m", pos: "noun", ipa: "silɑ̃s", source: "manual", audio_url: "/vocab/personal/audio/uv:silence" },
      added: true,
      review_seeded: true,
    });

    renderMyDeck();
    await screen.findByText(/No personal cards yet/);

    await user.type(screen.getByPlaceholderText(/épanouissement/), "le silence");
    await user.click(screen.getByRole("button", { name: "Look up" }));

    // preview shows the enrichment (gender rendered as (m))
    expect(await screen.findByText("silence")).toBeInTheDocument();
    expect(screen.getByText("(m)")).toBeInTheDocument();
    expect(api.personalPreview).toHaveBeenCalledWith("le silence");

    // confirming adds it and reloads the deck (now containing the card)
    vi.mocked(api.myDeck).mockResolvedValue({
      cards: [{ card_key: "uv:silence", fr: "silence", en: "quietness", gender: "m", pos: "noun", ipa: "silɑ̃s", source: "manual", audio_url: "/vocab/personal/audio/uv:silence" }],
    });
    await user.click(screen.getByRole("button", { name: "Add to my deck" }));

    expect(api.personalAdd).toHaveBeenCalledWith(
      expect.objectContaining({ fr: "silence", en: "quietness", gender: "m" }),
    );
    // the card appears in the list; the empty-state message is gone
    expect(await screen.findByText("silence")).toBeInTheDocument();
    expect(screen.queryByText(/No personal cards yet/)).not.toBeInTheDocument();
  });

  it("shows a limit message when over the daily budget", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalPreview).mockResolvedValue({ enrichment: null, over_budget: true });

    renderMyDeck();
    await screen.findByText(/No personal cards yet/);

    await user.type(screen.getByPlaceholderText(/épanouissement/), "chat");
    await user.click(screen.getByRole("button", { name: "Look up" }));

    expect(await screen.findByText(/Daily word-lookup limit reached/)).toBeInTheDocument();
    expect(api.personalAdd).not.toHaveBeenCalled();
  });
});
