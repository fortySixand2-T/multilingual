import { useEffect, useState } from "react";
import { api, DueCard } from "../api";
import AudioButton from "../AudioButton";

const RATINGS: { key: "again" | "hard" | "good" | "easy"; label: string }[] = [
  { key: "again", label: "Again" },
  { key: "hard", label: "Hard" },
  { key: "good", label: "Good" },
  { key: "easy", label: "Easy" },
];

export default function Review() {
  const [cards, setCards] = useState<DueCard[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.queue().then((q) => setCards(q.due)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load reviews: {error}</div>;
  if (!cards) return <div className="muted">Loading…</div>;

  if (cards.length === 0 || idx >= cards.length)
    return (
      <div className="card center stack">
        <div style={{ fontSize: 40 }}>🎉</div>
        <h2>All caught up</h2>
        <p className="muted">No cards due right now. Finish a lesson to add new words.</p>
      </div>
    );

  const card = cards[idx];
  // vocab carries an optional `audio` storage key (most cards don't have one yet)
  const vocabAudio = (card.vocab as { audio?: string } | null)?.audio;
  const rate = async (rating: "again" | "hard" | "good" | "easy") => {
    try {
      await api.review(card.card_key, rating);
    } catch {
      /* keep moving even if a single review fails */
    }
    setRevealed(false);
    setIdx((i) => i + 1);
  };

  return (
    <div>
      <div className="progress-bar"><div style={{ width: `${(idx / cards.length) * 100}%` }} /></div>
      <div className="card center stack" style={{ minHeight: 240, justifyContent: "center" }}>
        <div className="muted">{idx + 1} / {cards.length}</div>
        <div style={{ fontSize: 34, fontWeight: 800 }}>{card.vocab?.fr ?? card.card_key}</div>
        {vocabAudio && <AudioButton audioKey={vocabAudio} label="🔊" />}
        {revealed ? (
          <div style={{ fontSize: 20 }} className="muted">{card.vocab?.en ?? "—"}</div>
        ) : (
          <button className="btn secondary" onClick={() => setRevealed(true)}>Show answer</button>
        )}
      </div>

      {revealed && (
        <div className="btn-row" style={{ marginTop: 16, justifyContent: "center" }}>
          {RATINGS.map((r) => (
            <button key={r.key} className="btn secondary" onClick={() => rate(r.key)}>{r.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
