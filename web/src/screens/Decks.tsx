import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, VocabCard } from "../api";

// Vocabulary across every level, grouped into themed decks (by tag), with an
// "All words" deck per level for one big study session.
export default function Decks() {
  const [cards, setCards] = useState<VocabCard[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.vocab().then((r) => setCards(r.cards)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load vocabulary: {error}</div>;
  if (!cards) return <div className="muted">Loading…</div>;

  // level -> { total, tag -> count }, preserving the order levels first appear
  const levels: { level: string; total: number; tags: [string, number][] }[] = [];
  for (const c of cards) {
    const lvl = c.level ?? "?";
    let entry = levels.find((l) => l.level === lvl);
    if (!entry) {
      entry = { level: lvl, total: 0, tags: [] };
      levels.push(entry);
    }
    entry.total += 1;
    for (const t of c.tags ?? []) {
      const tc = entry.tags.find((x) => x[0] === t);
      if (tc) tc[1] += 1;
      else entry.tags.push([t, 1]);
    }
  }
  for (const l of levels) l.tags.sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>Vocabulary</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Flip through a theme to memorize — {cards.length} words across {levels.length} levels.
      </p>

      {levels.map(({ level, total, tags }) => (
        <section key={level} style={{ marginTop: 20 }}>
          <h3 style={{ textTransform: "uppercase", margin: "0 0 8px" }}>{level}</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <Link
              to={`/vocab/${level}/all`}
              className="card"
              style={{ flex: "1 1 140px", textDecoration: "none", borderStyle: "dashed" }}
            >
              <div style={{ fontWeight: 700 }}>★ All words</div>
              <div className="muted" style={{ fontSize: 13 }}>{total} cards</div>
            </Link>
            {tags.map(([tag, count]) => (
              <Link
                key={tag}
                to={`/vocab/${level}/${encodeURIComponent(tag)}`}
                className="card"
                style={{ flex: "1 1 140px", textDecoration: "none" }}
              >
                <div style={{ fontWeight: 700, textTransform: "capitalize" }}>{tag}</div>
                <div className="muted" style={{ fontSize: 13 }}>{count} cards</div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
