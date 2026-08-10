import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WordDetail from "./WordDetail";
import { api } from "../api";

vi.mock("../api", () => ({
  api: { vocabExtra: vi.fn(), vocabForms: vi.fn(), vocabExamples: vi.fn() },
}));

beforeEach(() => {
  vi.clearAllMocks();
  // default: nothing stored yet
  vi.mocked(api.vocabExtra).mockResolvedValue({ forms: null, examples: [] });
});

describe("WordDetail", () => {
  it("is collapsed until expanded, then hydrates and generates forms for an inflecting word", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabForms).mockResolvedValue({
      forms: [
        { label: "présent", fr: "je mange" },
        { label: "passé composé", fr: "j'ai mangé" },
      ],
      cached: false,
    });

    render(<WordDetail cardKey="uv:manger" pos="verb" />);
    expect(api.vocabExtra).not.toHaveBeenCalled(); // nothing on render

    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));

    expect(api.vocabExtra).toHaveBeenCalledWith("uv:manger");
    expect(api.vocabForms).toHaveBeenCalledWith("uv:manger"); // forms were null → generate
    expect(await screen.findByText("je mange")).toBeInTheDocument();
    expect(screen.getByText("j'ai mangé")).toBeInTheDocument();
  });

  it("works for a content-bank card key (not just uv:)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabForms).mockResolvedValue({ forms: [{ label: "pluriel", fr: "les chats" }], cached: false });
    render(<WordDetail cardKey="chat_a1" pos="noun" />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    expect(api.vocabExtra).toHaveBeenCalledWith("chat_a1");
    expect(await screen.findByText("les chats")).toBeInTheDocument();
  });

  it("does not regenerate forms already stored (even when empty)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabExtra).mockResolvedValue({ forms: [], examples: [] }); // stored, empty
    render(<WordDetail cardKey="uv:vite" pos="adverb" />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    // adverb doesn't inflect → no Forms section, and never a generate call
    expect(api.vocabForms).not.toHaveBeenCalled();
  });

  it("shows stored example history on open, then a fresh one on press", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabExtra).mockResolvedValue({
      forms: [],
      examples: [{ fr: "Le chat dort.", en: "The cat sleeps." }],
    });
    vi.mocked(api.vocabExamples).mockResolvedValue({
      examples: [
        { fr: "Un chat noir.", en: "A black cat." },
        { fr: "Le chat dort.", en: "The cat sleeps." },
      ],
    });

    render(<WordDetail cardKey="chat_a1" pos="noun" />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    // stored history is shown immediately (button reads "New example", not "Get examples")
    expect(await screen.findByText("Le chat dort.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /New example/ }));
    expect(api.vocabExamples).toHaveBeenCalledWith("chat_a1");
    expect(await screen.findByText("Un chat noir.")).toBeInTheDocument();
  });

  it("shows a limit message when examples are over budget", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabExamples).mockResolvedValue({ examples: [], over_budget: true });

    render(<WordDetail cardKey="chat_a1" pos="noun" />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    await user.click(await screen.findByRole("button", { name: /Get examples/ }));

    expect(await screen.findByText(/Daily limit reached/)).toBeInTheDocument();
  });

  it("shows an error message when the examples request fails (e.g. 503)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.vocabExamples).mockRejectedValue(new Error("503"));

    render(<WordDetail cardKey="chat_a1" pos="noun" />);
    await user.click(screen.getByRole("button", { name: /Forms & examples/ }));
    await user.click(await screen.findByRole("button", { name: /Get examples/ }));

    expect(await screen.findByText(/Couldn't generate an example right now/)).toBeInTheDocument();
    // placeholder text must not silently reappear as if nothing happened
    expect(screen.queryByText("Press for a sentence using this word.")).not.toBeInTheDocument();
  });
});
