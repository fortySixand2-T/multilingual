import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Review from "./Review";
import { api } from "../api";

vi.mock("../api", () => ({
  api: { queue: vi.fn(), review: vi.fn() },
}));

const renderReview = () =>
  render(
    <MemoryRouter>
      <Review />
    </MemoryRouter>,
  );

beforeEach(() => vi.clearAllMocks());

describe("Review tough-card badge", () => {
  it("renders 'one of your tough ones' lowercase with a visible gap after the fire emoji", async () => {
    vi.mocked(api.queue).mockResolvedValue({
      due: [
        { card_key: "a_bientot", due: "2026-08-05T00:00:00", difficulty: 9.9, vocab: { fr: "à bientôt", en: "see you soon" } },
      ],
    });

    renderReview();

    // QA round 051 #640: must read "one of your tough ones" (lowercase), and the emoji
    // and text must be separate nodes (flex + gap) rather than one collapsing string.
    expect(await screen.findByText("one of your tough ones")).toBeInTheDocument();
    expect(screen.queryByText(/One of your tough ones/)).not.toBeInTheDocument();
    expect(screen.getByText("🔥")).toBeInTheDocument();
  });
});
