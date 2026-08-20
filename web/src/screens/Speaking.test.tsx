import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Speaking from "./Speaking";
import { api } from "../api";

// Regression test for qa-540: the Record button used to call getUserMedia
// unconditionally, so a learner would grant a real mic permission and record
// before ever learning the backend has no STT/TTS configured. The screen now
// checks /speech/status on mount and disables Record (with an upfront
// message) instead.
import { postSpeechOpener } from "../api";

vi.mock("../api", () => ({
  api: {
    speechHistory: vi.fn(),
    speechStatus: vi.fn(),
    speakingTopics: vi.fn(),
    speechLastSession: vi.fn(),
    speechVocabReview: vi.fn(),
    personalAddFromWord: vi.fn(),
  },
  postSpeechOpener: vi.fn(),
  fetchAudioUrl: vi.fn().mockResolvedValue("blob:audio"),
}));

// Speaking reads the current level via useLevel; stub it so the test doesn't
// need the full LevelProvider. The level is mutable so a test can simulate the
// learner switching levels and re-render.
let mockLevel = "a1";
vi.mock("../level", () => ({
  useLevel: () => ({ level: mockLevel, levels: ["a1", "a2"], setLevel: vi.fn() }),
}));

const renderSpeaking = () => render(<Speaking />);

beforeEach(() => {
  vi.clearAllMocks(); // reset call history so per-test opener counts don't accumulate
  mockLevel = "a1";
  vi.mocked(api.speechHistory).mockResolvedValue({ turns: [] });
  vi.mocked(api.speakingTopics).mockResolvedValue({ topics: [] });
  vi.mocked(api.speechLastSession).mockResolvedValue({ session_id: null });
  // Default: opener returns nothing so it stays out of the way of unrelated tests.
  vi.mocked(postSpeechOpener).mockResolvedValue({ over_budget: false, reply_text: "" });
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

  // Regression test for qa-560: the record hint used to always say "introduce
  // yourself in French", even after a topic was picked — contradicting the
  // task card shown right above it.
  it("shows the generic hint with no topic picked, and a topic-aware hint once picked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    renderSpeaking();

    expect(
      await screen.findByText(/tap record and say hello in french/i)
    ).toBeInTheDocument();

    const pick = await screen.findByRole("button", { name: /Les voyages en avion/i });
    await userEvent.setup().click(pick);

    expect(
      screen.queryByText(/tap record and say hello in french/i)
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/tap record and start responding to "les voyages en avion" above/i)
    ).toBeInTheDocument();
  });
});

describe("Speaking examiner opener (agent speaks first)", () => {
  beforeEach(() => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: true });
  });

  it("opens the conversation itself on a fresh session, as an examiner-only card", async () => {
    vi.mocked(postSpeechOpener).mockResolvedValue({
      over_budget: false,
      reply_text: "Bonjour ! Comment allez-vous aujourd'hui ?",
      reply_audio_url: null,
    });
    renderSpeaking();

    expect(
      await screen.findByText(/bonjour ! comment allez-vous/i)
    ).toBeInTheDocument();
    // No learner utterance yet — the "You said" bubble must not render.
    expect(screen.queryByText(/you said/i)).not.toBeInTheDocument();
  });

  it("does not open (or interrupt) when a returning learner already has history", async () => {
    vi.mocked(api.speechHistory).mockResolvedValue({
      turns: [
        { turn_id: 1, mode: "conversation", transcript: "Salut", reply_text: "Ça va ?", reply_audio_url: null },
      ],
    });
    renderSpeaking();

    expect(await screen.findByText("Salut")).toBeInTheDocument();
    await waitFor(() => expect(api.speechHistory).toHaveBeenCalled());
    expect(postSpeechOpener).not.toHaveBeenCalled();
  });

  it("starts a fresh conversation (and a new opener) when the level changes", async () => {
    vi.mocked(postSpeechOpener).mockResolvedValue({
      over_budget: false,
      reply_text: "Première question ?",
      reply_audio_url: null,
    });
    const { rerender } = renderSpeaking();
    await waitFor(() => expect(postSpeechOpener).toHaveBeenCalledTimes(1));

    mockLevel = "a2";
    rerender(<Speaking />);

    await waitFor(() => expect(api.speakingTopics).toHaveBeenCalledWith("a2"));
    // Level change resets the session, so the examiner opens the new conversation.
    await waitFor(() => expect(postSpeechOpener).toHaveBeenCalledTimes(2));
  });
});
