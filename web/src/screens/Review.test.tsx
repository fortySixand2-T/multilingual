import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Review from "./Review";
import { api } from "../api";

vi.mock("../api", () => ({
  api: { queue: vi.fn(), review: vi.fn() },
}));

const dueCard = (key: string) => ({
  card_key: key,
  due: "2026-08-05T00:00:00",
  vocab: { fr: key, en: key },
});

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

// QA round 055 #773: api.queue() returns a capped batch (default limit=20), so
// exhausting the local array locally doesn't mean the server has no more due
// cards — Review must re-fetch and only show "All caught up" once a fresh
// fetch also comes back empty.
describe("Review queue exhaustion (issue 773)", () => {
  it("re-fetches before declaring 'all caught up' when more cards are due server-side", async () => {
    vi.mocked(api.queue)
      .mockResolvedValueOnce({ due: [dueCard("mot_un")] })
      .mockResolvedValueOnce({ due: [dueCard("mot_deux")] });
    vi.mocked(api.review).mockResolvedValue(undefined as never);

    renderReview();

    await screen.findByText("mot_un");
    fireEvent.click(screen.getByText("Show answer"));
    fireEvent.click(screen.getByText("Good"));

    // the first (1-card) batch is now exhausted — must fetch again rather than
    // immediately rendering the false-empty "All caught up" state
    await screen.findByText("mot_deux");
    expect(screen.queryByText("All caught up")).not.toBeInTheDocument();
    expect(api.queue).toHaveBeenCalledTimes(2);
  });

  it("shows 'All caught up' only once a fresh re-fetch also comes back empty", async () => {
    vi.mocked(api.queue)
      .mockResolvedValueOnce({ due: [dueCard("mot_un")] })
      .mockResolvedValueOnce({ due: [] });
    vi.mocked(api.review).mockResolvedValue(undefined as never);

    renderReview();

    await screen.findByText("mot_un");
    fireEvent.click(screen.getByText("Show answer"));
    fireEvent.click(screen.getByText("Good"));

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
    expect(api.queue).toHaveBeenCalledTimes(2);
  });
});
