import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WordDetail from "./WordDetail";
import { api, PersonalCard } from "../api";

vi.mock("../api", () => ({
  api: { personalForms: vi.fn(), personalExamples: vi.fn() },
}));

const card = (over: Partial<PersonalCard> = {}): PersonalCard => ({
  card_key: "uv:manger",
  fr: "manger",
  en: "to eat",
  gender: "",
  pos: "verb",
  ipa: "",
  source: "manual",
  audio_url: "/vocab/personal/audio/uv:manger",
  ...over,
});

beforeEach(() => vi.clearAllMocks());

describe("WordDetail", () => {
  it("is collapsed until expanded, then fetches forms for an inflecting word", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalForms).mockResolvedValue({
      forms: [
        { label: "présent", fr: "je mange" },
        { label: "passé composé", fr: "j'ai mangé" },
      ],
      cached: false,
    });

    render(<WordDetail card={card()} />);
    // nothing fetched on render
    expect(api.personalForms).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));

    expect(api.personalForms).toHaveBeenCalledWith("uv:manger");
    expect(await screen.findByText("je mange")).toBeInTheDocument();
    expect(screen.getByText("j'ai mangé")).toBeInTheDocument();
  });

  it("generates a fresh example on press and shows the returned history newest-first", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalForms).mockResolvedValue({ forms: [], cached: false });
    vi.mocked(api.personalExamples).mockResolvedValue({
      examples: [
        { fr: "Un chat noir.", en: "A black cat." },
        { fr: "Le chat dort.", en: "The cat sleeps." },
      ],
    });

    render(<WordDetail card={card({ card_key: "uv:chat", fr: "chat", pos: "noun", gender: "m" })} />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    await user.click(await screen.findByRole("button", { name: /Get examples/ }));

    expect(api.personalExamples).toHaveBeenCalledWith("uv:chat");
    expect(await screen.findByText("Un chat noir.")).toBeInTheDocument();
    expect(screen.getByText("Le chat dort.")).toBeInTheDocument();
    // once there's history, the button becomes "New example"
    expect(screen.getByRole("button", { name: /New example/ })).toBeInTheDocument();
  });

  it("does not offer forms for a non-inflecting part of speech", async () => {
    const user = userEvent.setup();
    render(<WordDetail card={card({ pos: "adverb", fr: "vite", card_key: "uv:vite" })} />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    expect(api.personalForms).not.toHaveBeenCalled();
    expect(screen.queryByText("Forms")).not.toBeInTheDocument();
  });

  it("shows a limit message when examples are over budget", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalForms).mockResolvedValue({ forms: [], cached: false });
    vi.mocked(api.personalExamples).mockResolvedValue({ examples: [], over_budget: true });

    render(<WordDetail card={card({ pos: "noun", gender: "m" })} />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    await user.click(await screen.findByRole("button", { name: /Get examples/ }));

    expect(await screen.findByText(/Daily limit reached/)).toBeInTheDocument();
  });
});
