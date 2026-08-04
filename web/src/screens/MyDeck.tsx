import { useEffect, useState } from "react";
import { api, PersonalCard, PersonalEnrichment } from "../api";
import AudioButton from "../AudioButton";

// "My deck": a learner's own vocab cards. Add a word → look it up (dictionary
// enrichment, Slice D) → confirm → it's stored and enters the normal review queue.
export default function MyDeck() {
  const [cards, setCards] = useState<PersonalCard[] | null>(null);
  const [error, setError] = useState("");
  const [word, setWord] = useState("");
  const [preview, setPreview] = useState<PersonalEnrichment | null>(null);
  const [status, setStatus] = useState<"idle" | "looking" | "adding" | "over_budget">("idle");

  const load = () => api.myDeck().then((r) => setCards(r.cards)).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const lookup = async () => {
    const w = word.trim();
    if (!w) return;
    setStatus("looking");
    setPreview(null);
    setError("");
    try {
      const r = await api.personalPreview(w);
      if (r.over_budget) {
        setStatus("over_budget");
        return;
      }
      setPreview(r.enrichment);
      setStatus("idle");
    } catch (e) {
      setError((e as Error).message);
      setStatus("idle");
    }
  };

  const add = async () => {
    if (!preview) return;
    setStatus("adding");
    try {
      await api.personalAdd({
        fr: preview.fr,
        en: preview.en,
        gender: preview.gender,
        pos: preview.pos,
        ipa: preview.ipa,
        source: "manual",
      });
      setPreview(null);
      setWord("");
      setStatus("idle");
      await load();
    } catch (e) {
      setError((e as Error).message);
      setStatus("idle");
    }
  };

  const genderTag = (g: string) => (g === "m" ? "(m)" : g === "f" ? "(fe)" : g === "mf" ? "(m/fe)" : "");

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>My deck</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Add any French word — we look up its meaning, gender, and pronunciation, and it
        joins your daily reviews.
      </p>

      <div className="card stack" style={{ gap: 10 }}>
        <div className="btn-row" style={{ gap: 8 }}>
          <input
            className="text-input"
            style={{ flex: 1 }}
            placeholder="e.g. épanouissement"
            value={word}
            onChange={(e) => setWord(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && lookup()}
          />
          <button className="btn" onClick={lookup} disabled={status === "looking" || !word.trim()}>
            {status === "looking" ? "…" : "Look up"}
          </button>
        </div>

        {status === "over_budget" && (
          <div className="muted">Daily word-lookup limit reached. Try again tomorrow.</div>
        )}

        {preview && (
          <div className="stack" style={{ gap: 8, borderTop: "1px solid var(--border,#333)", paddingTop: 10 }}>
            <div style={{ fontSize: 22, fontWeight: 800 }}>
              {preview.fr} <span className="muted" style={{ fontSize: 15 }}>{genderTag(preview.gender)}</span>
            </div>
            <div className="muted">{preview.en || "—"}</div>
            {preview.ipa && <div className="muted" style={{ fontSize: 13 }}>/{preview.ipa}/</div>}
            <div className="btn-row" style={{ gap: 8 }}>
              <button className="btn" onClick={add} disabled={status === "adding"}>
                {status === "adding" ? "Adding…" : "Add to my deck"}
              </button>
              <button className="btn secondary" onClick={() => setPreview(null)}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {error && <div className="card center" style={{ marginTop: 12 }}>Error: {error}</div>}

      <section style={{ marginTop: 20 }}>
        {!cards ? (
          <div className="muted">Loading…</div>
        ) : cards.length === 0 ? (
          <p className="muted">No personal cards yet — add your first word above.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {cards.map((c) => (
              <div key={c.card_key} className="card" style={{ flex: "1 1 200px" }}>
                <div style={{ fontWeight: 700 }}>
                  {c.fr} <span className="muted" style={{ fontSize: 13 }}>{genderTag(c.gender)}</span>
                </div>
                <div className="muted" style={{ fontSize: 14 }}>{c.en}</div>
                <div style={{ marginTop: 6 }}>
                  <AudioButton audioUrl={c.audio_url} label="🔊" slow />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
