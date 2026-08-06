import { useEffect, useState } from "react";
import { api, HardCard } from "../api";
import AudioButton from "../AudioButton";

// "Hardest for you" (Slice 2): the words the FSRS engine says keep tripping this
// learner up, ranked by difficulty (1–10). Only cards reviewed at least once appear.
const band = (d: number): { label: string; color: string } => {
  if (d >= 7) return { label: "Tough", color: "#c0392b" };
  if (d >= 4) return { label: "Tricky", color: "#b8860b" };
  return { label: "Getting there", color: "#2e7d32" };
};

export default function Hardest() {
  const [cards, setCards] = useState<HardCard[] | null>(null);
  const [error, setError] = useState("");
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.hardest().then((r) => setCards(r.cards)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load your hardest words: {error}</div>;
  if (!cards) return <div className="muted">Loading…</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>Hardest for you</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        The words you find trickiest, ranked by how often you stumble on them. Review them
        in your daily queue — these bubble up as you rate them.
      </p>

      {cards.length === 0 ? (
        <p className="muted">
          Nothing here yet — review some words first, and the ones you rate “Again” or
          “Hard” will show up.
        </p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {cards.map((c) => {
            const b = band(c.difficulty);
            const audioUrl = c.vocab?.audio_url;
            const audioKey = c.vocab?.audio;
            const open = revealed[c.card_key];
            return (
              <div key={c.card_key} className="card" style={{ flex: "1 1 220px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 700 }}>{c.vocab?.fr ?? c.card_key}</span>
                  <span
                    title={`FSRS difficulty ${c.difficulty} / 10`}
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: b.color,
                      border: `1px solid ${b.color}`,
                      borderRadius: 999,
                      padding: "1px 8px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {b.label} · {c.difficulty}
                  </span>
                </div>
                <div style={{ marginTop: 8, minHeight: 22 }}>
                  {open ? (
                    <span className="muted">{c.vocab?.en ?? "—"}</span>
                  ) : (
                    <button
                      className="link-btn"
                      onClick={() => setRevealed((r) => ({ ...r, [c.card_key]: true }))}
                    >
                      Show meaning
                    </button>
                  )}
                </div>
                {(audioUrl || audioKey) && (
                  <div style={{ marginTop: 6 }}>
                    <AudioButton audioUrl={audioUrl} audioKey={audioKey} label="🔊" slow />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
