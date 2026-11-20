import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MyDeck from "./MyDeck";
import { api } from "../api";

vi.mock("../api", () => ({
  api: { myDeck: vi.fn(), personalPreview: vi.fn(), personalAdd: vi.fn() },
  fetchAudioUrl: vi.fn(),
}));

const entry = (fr: string, en: string) => ({
  fr,
  en,
  pos: "noun",
  gender: "f",
  ipa: "",
  gender_source: "dictionary",
  audio_url: "",
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.myDeck).mockResolvedValue({ cards: [] });
});

describe("My deck", () => {
  it("offers the other accented word an accentless lookup could be (QA 1181)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalPreview)
      .mockResolvedValueOnce({ enrichment: entry("pêche", "peach, fishing"), also: [{ fr: "péché", en: "sin" }] })
      .mockResolvedValueOnce({ enrichment: entry("péché", "sin"), also: [] });
    render(<MyDeck />);

    await user.type(screen.getByPlaceholderText(/épanouissement/), "peche{Enter}");
    await user.click(await screen.findByRole("button", { name: /péché/ }));

    expect(api.personalPreview).toHaveBeenLastCalledWith("péché");
    expect(await screen.findByDisplayValue("sin")).toBeInTheDocument();
    expect(screen.queryByText(/Did you mean/)).not.toBeInTheDocument();
  });

  it("caps the meaning at the server's 255 characters (QA 1190)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.personalPreview).mockResolvedValue({ enrichment: entry("maire", "mayor") });
    render(<MyDeck />);

    await user.type(screen.getByPlaceholderText(/épanouissement/), "maire{Enter}");
    const meaning = await screen.findByDisplayValue("mayor");
    expect(meaning).toHaveAttribute("maxLength", "255");
  });
});
