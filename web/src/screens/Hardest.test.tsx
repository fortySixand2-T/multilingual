import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Hardest from "./Hardest";
import { api } from "../api";

vi.mock("../api", () => ({
  api: { hardest: vi.fn() },
  fetchAudioUrl: vi.fn(),
}));

const renderHardest = () =>
  render(
    <MemoryRouter>
      <Hardest />
    </MemoryRouter>,
  );

beforeEach(() => vi.clearAllMocks());

describe("Hardest for you", () => {
  it("ranks cards with a difficulty band and reveals meaning on demand", async () => {
    const user = userEvent.setup();
    vi.mocked(api.hardest).mockResolvedValue({
      cards: [
        { card_key: "uv:quolibet", difficulty: 8.2, due: "2026-08-05T00:00:00", vocab: { fr: "quolibet", en: "gibe", personal: true, audio_url: "/vocab/personal/audio/uv:quolibet" } },
        { card_key: "chat", difficulty: 3.1, due: "2026-08-05T00:00:00", vocab: { fr: "chat", en: "cat", audio: "a1/audio/chat.mp3" } },
      ],
    });

    renderHardest();

    // hardest word + its band label render
    expect(await screen.findByText("quolibet")).toBeInTheDocument();
    expect(screen.getByText(/Tough · 8.2/)).toBeInTheDocument();
    expect(screen.getByText(/Getting there · 3.1/)).toBeInTheDocument();

    // meaning is hidden until asked
    expect(screen.queryByText("gibe")).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Show meaning" })[0]);
    expect(screen.getByText("gibe")).toBeInTheDocument();
  });

  it("shows an empty state when nothing has been reviewed yet", async () => {
    vi.mocked(api.hardest).mockResolvedValue({ cards: [] });
    renderHardest();
    expect(await screen.findByText(/Nothing here yet/)).toBeInTheDocument();
  });
});
