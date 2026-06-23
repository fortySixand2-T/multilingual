import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, VocabCard } from "../api";

// Lists the level's vocabulary grouped into themed decks (by tag) to study/memorize.
export default function Decks() {
  const [cards, setCards] = useState<VocabCard[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.vocab("a1").then((r) => setCards(r.cards)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load vocabulary: {error}</div>;
  if (!cards) return <div className="muted">Loading…</div>;

  const counts: Record<string, number> = {};
  for (const c of cards) for (const t of c.tags ?? []) counts[t] = (counts[t] ?? 0) + 1;
  const decks = Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>Vocabulary</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Flip through a theme to memorize — {cards.length} words.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 16 }}>
        {decks.map(([tag, count]) => (
          <Link
            key={tag}
            to={`/vocab/${encodeURIComponent(tag)}`}
            className="card"
            style={{ flex: "1 1 140px", textDecoration: "none" }}
          >
            <div style={{ fontWeight: 700, textTransform: "capitalize" }}>{tag}</div>
            <div className="muted" style={{ fontSize: 13 }}>{count} cards</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
