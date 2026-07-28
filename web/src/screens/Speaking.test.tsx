import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Speaking from "./Speaking";
import { api } from "../api";

// Regression test for qa-540: the Record button used to call getUserMedia
// unconditionally, so a learner would grant a real mic permission and record
// before ever learning the backend has no STT/TTS configured. The screen now
// checks /speech/status on mount and disables Record (with an upfront
// message) instead.
vi.mock("../api", () => ({ api: { speechHistory: vi.fn(), speechStatus: vi.fn() } }));

beforeEach(() => {
  vi.mocked(api.speechHistory).mockResolvedValue({ turns: [] });
});

describe("Speaking preflight availability check (qa-540)", () => {
  it("disables Record and shows the unavailable message when speech isn't configured", async () => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: false });
    render(<Speaking />);

    const recordBtn = await screen.findByRole("button", { name: /record/i });
    await waitFor(() => expect(recordBtn).toBeDisabled());
    expect(
      screen.getByText(/speaking practice isn't enabled on this server yet/i)
    ).toBeInTheDocument();
  });

  it("leaves Record enabled with no unavailable message when speech is configured", async () => {
    vi.mocked(api.speechStatus).mockResolvedValue({ available: true });
    render(<Speaking />);

    const recordBtn = await screen.findByRole("button", { name: /record/i });
    await waitFor(() => expect(recordBtn).toBeEnabled());
    expect(
      screen.queryByText(/speaking practice isn't enabled on this server yet/i)
    ).not.toBeInTheDocument();
  });
});
