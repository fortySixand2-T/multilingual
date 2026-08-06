"""FSRS engine wrapper — the ONLY module that imports the `fsrs` library.

Same discipline as the AI adapters: the vendor lib stays confined here so it's
swappable (plan §4.1: "don't hand-roll FSRS; wrap the lib behind srs/"). Domain
code uses `FSRSEngine` + plain `CardState`, never `fsrs` types.

State is the library's serializable card dict (persisted as JSON); `due` is
denormalized out so the review queue can query it without deserializing FSRS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import fsrs

_RATINGS = {
    "again": fsrs.Rating.Again,
    "hard": fsrs.Rating.Hard,
    "good": fsrs.Rating.Good,
    "easy": fsrs.Rating.Easy,
}
RATINGS = tuple(_RATINGS)  # ("again", "hard", "good", "easy")


@dataclass(frozen=True)
class CardState:
    state: dict  # opaque, JSON-serializable FSRS card dict
    due: datetime  # next review time (tz-aware UTC)


def difficulty(state: dict) -> float | None:
    """FSRS difficulty for a card: 1 (easiest) .. 10 (hardest). `None` until the card's
    first review — a brand-new card has no difficulty signal yet. Kept here so FSRS-state
    shape stays confined to this module (domain code asks for a number, not a dict key)."""
    d = state.get("difficulty")
    return float(d) if d is not None else None


class FSRSEngine:
    def __init__(self) -> None:
        self._scheduler = fsrs.Scheduler()

    def new(self, *, now: datetime | None = None) -> CardState:
        card = fsrs.Card()
        if now is not None:
            card.due = now
        return CardState(state=card.to_dict(), due=card.due)

    def review(self, state: dict, rating: str, *, now: datetime | None = None) -> CardState:
        if rating not in _RATINGS:
            raise ValueError(f"unknown rating {rating!r}; use one of {RATINGS}")
        card = fsrs.Card.from_dict(state)
        card, _log = self._scheduler.review_card(card, _RATINGS[rating], now)
        return CardState(state=card.to_dict(), due=card.due)
