import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, GrammarItem } from "../api";
import { useLevel } from "../level";

// A browsable reference of every grammar point taught in the current level's
// lessons, in path order and grouped by unit, with a quick client-side filter.
// Each entry links back to the lesson that teaches it.
export default function Grammar() {
  const nav = useNavigate();
  const { level } = useLevel();
  const [items, setItems] = useState<GrammarItem[] | null>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    setItems(null);
    setError("");
    api.grammar(level).then((r) => setItems(r.items)).catch((e) => setError(e.message));
  }, [level]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle || !items) return items ?? [];
    return items.filter(
      (i) =>
        i.grammar_point.toLowerCase().includes(needle) ||
        i.unit_title.toLowerCase().includes(needle) ||
        i.lesson_title.toLowerCase().includes(needle),
    );
  }, [items, q]);

  if (error) return <div className="card center">Couldn't load grammar: {error}</div>;
  if (!items) return <div className="muted">Loading…</div>;

  // group in encounter order (already path-ordered by the API)
  const units: { id: string; title: string; points: GrammarItem[] }[] = [];
  for (const it of filtered) {
    let u = units.find((x) => x.id === it.unit_id);
    if (!u) {
      u = { id: it.unit_id, title: it.unit_title, points: [] };
      units.push(u);
    }
    u.points.push(it);
  }

  return (
    <div>
      <h1>Grammar reference</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        Every grammar point taught in {level.toUpperCase()}, in order. Tap one to open its lesson.
      </p>
      <input
        className="text-input"
        placeholder="Search grammar…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      {units.length === 0 && <div className="muted">No grammar points match “{q}”.</div>}

      {units.map((u) => (
        <div className="unit" key={u.id}>
          <div className="unit-head">
            <div className="unit-icon">📚</div>
            <div className="unit-title">{u.title}</div>
          </div>
          {u.points.map((p) => (
            <button
              key={p.lesson_id}
              className="lesson-node"
              onClick={() => nav(`/lesson/${p.lesson_id}`)}
            >
              <span className="node-dot available">§</span>
              <span className="grow">
                <div className="node-title">{p.grammar_point}</div>
                <div className="node-sub">{p.lesson_title}</div>
              </span>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
