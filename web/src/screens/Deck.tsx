import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, VocabCard } from "../api";
import AudioButton from "../AudioButton";
import { shuffled } from "../shuffle";

// Flashcard study for one deck: show French (+ pronunciation), flip to the meaning,
// mark known / still-learning. "Known" is persisted per user; "Still learning" resets
// it. Free study — independent of the scheduled SRS review.
export default function Deck() {
  const { level = "", tag = "" } = useParams();
  const label = tag === "all" ? "all words" : tag;
  const [cards, setCards] = useState<VocabCard[] | null>(null);
  const [error, setError] = useState("");
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [knownIds, setKnownIds] = useState<Set<string>>(new Set());
  const [reviewIds, setReviewIds] = useState<Set<string>>(new Set());
  const [done, setDone] = useState(false);

  useEffect(() => {
    api
      .vocab(level, tag === "all" ? undefined : tag)
      .then((r) => {
        setCards(r.cards);
        setKnownIds(new Set(r.cards.filter((c) => c.known).map((c) => c.id)));
        setReviewIds(new Set(r.cards.filter((c) => c.in_review).map((c) => c.id)));
      })
      .catch((e) => setError(e.message));
  }, [level, tag]);

  // shuffle once per load so the deck isn't always in the same order
  const deck = useMemo(() => (cards ? shuffled(cards) : []), [cards]);

  if (error) return <div className="card center">Couldn't load deck: {error}</div>;
  if (!cards) return <div className="muted">Loading…</div>;
  if (deck.length === 0)
    return (
      <div className="card center stack">
        <p>No cards in “{label}”.</p>
        <Link className="btn" to="/vocab">Back to decks</Link>
      </div>
    );

  if (done)
    return (
      <div className="card center stack">
        <div style={{ fontSize: 40 }}>🎉</div>
        <h2>Deck complete</h2>
        <p className="muted">You know {knownIds.size} / {deck.length} in this deck.</p>
        <Link className="btn" to="/vocab">Back to decks</Link>
      </div>
    );

  const card = deck[idx];
  const isKnown = knownIds.has(card.id);
  const inReview = reviewIds.has(card.id);

  const addToReview = () => {
    setReviewIds((prev) => new Set(prev).add(card.id));
    api.addToReview(card.id).catch(() => {}); // best-effort; seeds a scheduled SRS card
  };

  const advance = (knew: boolean) => {
    setKnownIds((prev) => {
      const next = new Set(prev);
      if (knew) next.add(card.id);
      else next.delete(card.id); // "Still learning" resets a previously-known word
      return next;
    });
    api.setKnown(card.id, knew).catch(() => {}); // best-effort persistence
    setFlipped(false);
    if (idx + 1 < deck.length) setIdx(idx + 1);
    else setDone(true);
  };

  return (
    <div>
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <Link to="/vocab" className="link-btn">← Decks</Link>
        <span className="pill">✓ {knownIds.size} / {deck.length} known</span>
      </div>
      <div className="progress-bar"><div style={{ width: `${(idx / deck.length) * 100}%` }} /></div>

      <div className="card center stack" style={{ minHeight: 240, justifyContent: "center" }}>
        <div className="muted" style={{ textTransform: "capitalize" }}>
          {idx + 1} / {deck.length} · {label}{isKnown ? " · ✓ known" : ""}
        </div>
        <div style={{ fontSize: 34, fontWeight: 800 }}>{card.fr}</div>
        {card.audio && <AudioButton audioKey={card.audio} label="🔊" />}
        {flipped ? (
          <div style={{ fontSize: 20 }} className="muted">{card.en}</div>
        ) : (
          <button className="btn secondary" onClick={() => setFlipped(true)}>Show meaning</button>
        )}
      </div>

      <div className="btn-row" style={{ justifyContent: "center", marginTop: 12 }}>
        <button className="link-btn" disabled={inReview} onClick={addToReview}>
          {inReview ? "✓ In review" : "＋ Add to review"}
        </button>
      </div>

      {flipped && (
        <>
          <div className="btn-row" style={{ marginTop: 16, justifyContent: "center" }}>
            <button className="btn secondary" onClick={() => advance(false)}>Still learning</button>
            <button className="btn" onClick={() => advance(true)}>Knew it</button>
          </div>
          <p className="muted" style={{ textAlign: "center", fontSize: 13, marginTop: 8 }}>
            “Still learning” resets a word you'd marked known.
          </p>
        </>
      )}
    </div>
  );
}
