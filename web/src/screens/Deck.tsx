import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, VocabCard } from "../api";
import AudioButton from "../AudioButton";
import { shuffled } from "../shuffle";

// Flashcard study for one themed deck: show French (+ audio), flip to the meaning,
// self-rate, advance. Free study — independent of the scheduled SRS review.
export default function Deck() {
  const { level = "", tag = "" } = useParams();
  const label = tag === "all" ? "all words" : tag;
  const [cards, setCards] = useState<VocabCard[] | null>(null);
  const [error, setError] = useState("");
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [known, setKnown] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api
      .vocab(level, tag === "all" ? undefined : tag)
      .then((r) => setCards(r.cards))
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
        <p className="muted">You knew {known} / {deck.length}.</p>
        <Link className="btn" to="/vocab">Back to decks</Link>
      </div>
    );

  const card = deck[idx];
  const advance = (knew: boolean) => {
    if (knew) setKnown((k) => k + 1);
    setFlipped(false);
    if (idx + 1 < deck.length) setIdx(idx + 1);
    else setDone(true);
  };

  return (
    <div>
      <div className="progress-bar"><div style={{ width: `${(idx / deck.length) * 100}%` }} /></div>
      <div className="card center stack" style={{ minHeight: 240, justifyContent: "center" }}>
        <div className="muted" style={{ textTransform: "capitalize" }}>
          {idx + 1} / {deck.length} · {label}
        </div>
        <div style={{ fontSize: 34, fontWeight: 800 }}>{card.fr}</div>
        {card.audio && <AudioButton audioKey={card.audio} label="🔊" />}
        {flipped ? (
          <div style={{ fontSize: 20 }} className="muted">{card.en}</div>
        ) : (
          <button className="btn secondary" onClick={() => setFlipped(true)}>Show meaning</button>
        )}
      </div>

      {flipped && (
        <div className="btn-row" style={{ marginTop: 16, justifyContent: "center" }}>
          <button className="btn secondary" onClick={() => advance(false)}>Still learning</button>
          <button className="btn" onClick={() => advance(true)}>Knew it</button>
        </div>
      )}
    </div>
  );
}
