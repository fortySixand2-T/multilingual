import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import AudioButton from "./AudioButton";
import * as api from "./api";

// Regression guard for qa/issues/741-vocab-audio-play-button-stuck-loading-forever.md:
// audio.play() can hang forever (never resolve or reject) — the button must still
// recover to its idle label instead of being stuck on "…" indefinitely.
describe("AudioButton loading state", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(api, "fetchAudioUrl").mockResolvedValue("blob:fake");
    // A play() promise that never settles, simulating a hung clip.
    vi.stubGlobal(
      "Audio",
      vi.fn().mockImplementation(() => ({
        play: () => new Promise(() => {}),
        preservesPitch: true,
        playbackRate: 1,
      })),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("recovers from a hung audio.play() instead of staying stuck on the loading label", async () => {
    render(<AudioButton audioKey="a1/audio/bonjour.mp3" label="🔊" />);
    const button = screen.getByRole("button", { name: "🔊" });

    await act(async () => {
      fireEvent.click(button);
      // let the fetchAudioUrl microtask + Audio construction settle
      await Promise.resolve();
    });
    expect(screen.getByRole("button", { name: "…" })).toBeDisabled();

    // Advance past the fallback timeout even though play() never settles.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });

    expect(screen.getByRole("button", { name: "🔊" })).not.toBeDisabled();
  });
});
