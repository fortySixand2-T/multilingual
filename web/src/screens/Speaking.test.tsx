import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Speaking from "./Speaking";
import { api } from "../api";

// Regression test for qa-540: the Record button used to call getUserMedia
// unconditionally, so a learner would grant a real mic permission and record
// before ever learning the backend has no STT/TTS configured. The screen now
// checks /speech/status on mount and disables Record (with an upfront
// message) instead.
vi.mock("../api", () => ({
  api: { speechHistory: vi.fn(), speechStatus: vi.fn(), speakingTopics: vi.fn() },
}));

// Speaking reads the current level via useLevel; stub it so the test doesn't
// need the full LevelProvider (which touches localStorage + more endpoints).
vi.mock("../level", () => ({
  useLevel: () => ({ level: "a1", levels: ["a1"], setLevel: vi.fn() }),
}));

const renderSpeaking = () => render(<Speaking />);

beforeEach(() => {
  vi.mocked(api.speechHistory).mockResolvedValue({ turns: [] });
  vi.mocked(api.speakingTopics).mockResolvedValue({ topics: [] });
});

describe("Speaking preflight availability check (qa-540)", () => {
  it("disables Record and shows the unavailable message when speech isn't configured", async () => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: false });
    renderSpeaking();

    const recordBtn = await screen.findByRole("button", { name: /record/i });
    await waitFor(() => expect(recordBtn).toBeDisabled());
    expect(
      screen.getByText(/speaking practice isn't enabled on this server yet/i)
    ).toBeInTheDocument();
  });

  it("leaves Record enabled with no unavailable message when speech is configured", async () => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: true });
    renderSpeaking();

    const recordBtn = await screen.findByRole("button", { name: /record/i });
    await waitFor(() => expect(recordBtn).toBeEnabled());
    expect(
      screen.queryByText(/speaking practice isn't enabled on this server yet/i)
    ).not.toBeInTheDocument();
  });
});

describe("Speaking topic picker", () => {
  const topic = {
    id: "t-avion",
    section: "B" as const,
    title: "Les voyages en avion",
    prompt: "Faut-il limiter l'avion ?",
    points: ["environnement", "coût"],
  };

  beforeEach(() => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: true });
    vi.mocked(api.speakingTopics).mockResolvedValue({ topics: [topic] });
  });

  it("lists topics and shows the task card once one is picked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    renderSpeaking();

    const pick = await screen.findByRole("button", { name: /Les voyages en avion/i });
    await userEvent.setup().click(pick);

    // task prompt + development points are now shown
    expect(screen.getByText(/Faut-il limiter l'avion/)).toBeInTheDocument();
    expect(screen.getByText("environnement")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /change topic/i })).toBeInTheDocument();
  });
});
