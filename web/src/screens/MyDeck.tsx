import { useEffect, useState } from "react";
import { api, PersonalCard, PersonalEnrichment } from "../api";
import AudioButton from "../AudioButton";
import WordDetail from "./WordDetail";

// "My deck": a learner's own vocab cards. Add a word → look it up (meaning, gender,
// IPA, pronunciation — cached server-side, so repeats are instant) → hear it, fix the
// meaning if needed → add; it's stored and enters the normal review queue.
export default function MyDeck() {
  const [cards, setCards] = useState<PersonalCard[] | null>(null);
  const [error, setError] = useState("");
  const [word, setWord] = useState("");
  const [preview, setPreview] = useState<PersonalEnrichment | null>(null);
  const [inCourse, setInCourse] = useState("");
  const [added, setAdded] = useState("");
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
    setInCourse("");
    setAdded("");
    setError("");
    try {
      const r = await api.personalPreview(w);
      if (r.over_budget) {
        setStatus("over_budget");
        return;
      }
      setPreview(r.enrichment);
      setInCourse(r.in_course ?? "");
      setStatus("idle");
    } catch (e) {
      setError((e as Error).message || "Lookup failed — please try again.");
      setStatus("idle");
    }
  };

  const add = async () => {
    if (!preview?.en.trim()) return;
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
      setAdded(preview.fr);
      setPreview(null);
      setWord("");
      setStatus("idle");
      await load();
    } catch (e) {
      setError((e as Error).message);
      setStatus("idle");
    }
  };

  const ipaLine = (ipa: string) => (ipa ? <div className="muted" style={{ fontSize: 13 }}>/{ipa}/</div> : null);
  const genderTag = (g: string) => (g === "m" ? "(m)" : g === "f" ? "(fe)" : g === "mf" ? "(m/fe)" : "");

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>My deck</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Your own French words. They join your daily reviews alongside the course vocab.
      </p>

      <div className="card stack" style={{ gap: 10 }}>
        <h3 style={{ margin: 0 }}>➕ Add a word to my deck</h3>
        <div className="muted" style={{ fontSize: 13 }}>
          1. Type a French word · 2. Check its meaning and hear it · 3. Press <b>Add to my deck</b>
        </div>
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
            {status === "looking" ? "Looking up…" : "Look up"}
          </button>
        </div>

        {status === "looking" && (
          <div className="muted">
            Looking up “{word.trim()}”… a new word takes a few seconds; one looked up before is instant.
          </div>
        )}
        {status === "over_budget" && (
          <div className="muted">Daily word-lookup limit reached. Try again tomorrow.</div>
        )}
        {error && <div style={{ color: "var(--red, #c0392b)" }}>⚠️ {error}</div>}
        {added && <div style={{ color: "var(--green-dk)" }}>✅ Added “{added}” — it’s in your reviews now.</div>}

        {preview && (
          <div className="stack" style={{ gap: 8, borderTop: "1px solid var(--border,#333)", paddingTop: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 22, fontWeight: 800 }}>{preview.fr}</span>
              <span className="muted" style={{ fontSize: 15 }}>{genderTag(preview.gender)}</span>
              {preview.audio_url && <AudioButton audioUrl={preview.audio_url} label="🔊" slow />}
            </div>
            {ipaLine(preview.ipa)}
            {inCourse ? (
              <>
                <div className="muted">{preview.en}</div>
                <div>
                  ✅ Already in your course vocab ({inCourse.toUpperCase()}) — it’s in your reviews, no
                  need to add it.
                </div>
              </>
            ) : (
              <>
                <label className="muted" style={{ fontSize: 12 }}>
                  Meaning (edit if it’s not right)
                  <input
                    className="text-input"
                    style={{ width: "100%" }}
                    value={preview.en}
                    onChange={(e) => setPreview({ ...preview, en: e.target.value })}
                  />
                </label>
                <div className="btn-row" style={{ gap: 8 }}>
                  <button className="btn" onClick={add} disabled={status === "adding" || !preview.en.trim()}>
                    {status === "adding" ? "Adding…" : "Add to my deck"}
                  </button>
                  <button className="btn secondary" onClick={() => setPreview(null)}>Cancel</button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

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
                {ipaLine(c.ipa)}
                <div className="muted" style={{ fontSize: 14 }}>{c.en}</div>
                <div style={{ marginTop: 6 }}>
                  <AudioButton audioUrl={c.audio_url} label="🔊" slow />
                </div>
                <WordDetail cardKey={c.card_key} pos={c.pos} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
