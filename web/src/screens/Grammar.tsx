import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, GrammarItem } from "../api";
import { useLevel } from "../level";

// A browsable reference of every grammar point taught in the current level's
// lessons, grouped by grammatical family (category) rather than by theme, with
// category filter chips and a text search. Each entry links back to its lesson.

// Canonical display order of the families (mirrors GRAMMAR_CATEGORIES in
// app/content/models.py). Anything without a category falls under "Other".
const CATEGORY_ORDER = [
  "Verb conjugation & tenses",
  "Subjunctive",
  "Pronouns",
  "Articles & determiners",
  "Adjectives & comparison",
  "Logical connectors",
  "Sentence structures",
  "Expressions & communication",
];
const OTHER = "Other";

function catOf(it: GrammarItem): string {
  return it.grammar_category || OTHER;
}

export default function Grammar() {
  const nav = useNavigate();
  const { level } = useLevel();
  const [items, setItems] = useState<GrammarItem[] | null>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string | null>(null); // active category filter

  useEffect(() => {
    setItems(null);
    setError("");
    setCat(null);
    api.grammar(level).then((r) => setItems(r.items)).catch((e) => setError(e.message));
  }, [level]);

  // categories actually present in this level, in canonical order (+ Other last)
  const categories = useMemo(() => {
    const present = new Set((items ?? []).map(catOf));
    const ordered = CATEGORY_ORDER.filter((c) => present.has(c));
    if (present.has(OTHER)) ordered.push(OTHER);
    return ordered;
  }, [items]);

  const filtered = useMemo(() => {
    if (!items) return [];
    const needle = q.trim().toLowerCase();
    return items.filter((i) => {
      if (cat && catOf(i) !== cat) return false;
      if (!needle) return true;
      return (
        i.grammar_point.toLowerCase().includes(needle) ||
        i.grammar_category.toLowerCase().includes(needle) ||
        i.unit_title.toLowerCase().includes(needle) ||
        i.lesson_title.toLowerCase().includes(needle)
      );
    });
  }, [items, q, cat]);

  if (error) return <div className="card center">Couldn't load grammar: {error}</div>;
  if (!items) return <div className="muted">Loading…</div>;

  // group by category, in canonical order; items are already path-ordered within.
  // `categories` already includes "Other" when any lesson is uncategorized.
  const groups: { category: string; points: GrammarItem[] }[] = [];
  for (const c of categories) {
    const points = filtered.filter((i) => catOf(i) === c);
    if (points.length) groups.push({ category: c, points });
  }

  return (
    <div>
      <h1>Grammar reference</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        Every grammar point taught in {level.toUpperCase()}, grouped by type. Tap one to open
        its lesson.
      </p>

      <div className="chips" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <button
          className={`chip${cat === null ? " active" : ""}`}
          onClick={() => setCat(null)}
        >
          All
        </button>
        {categories.map((c) => (
          <button
            key={c}
            className={`chip${cat === c ? " active" : ""}`}
            onClick={() => setCat((prev) => (prev === c ? null : c))}
          >
            {c}
          </button>
        ))}
      </div>

      <input
        className="text-input"
        placeholder="Search grammar…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      {groups.length === 0 && <div className="muted">No grammar points match your filter.</div>}

      {groups.map((g) => (
        <div className="unit" key={g.category}>
          <div className="unit-head">
            <div className="unit-icon">📚</div>
            <div className="unit-title">{g.category}</div>
          </div>
          {g.points.map((p) => (
            <button
              key={p.lesson_id}
              className="lesson-node"
              onClick={() => nav(`/lesson/${p.lesson_id}`)}
            >
              <span className="node-dot available">§</span>
              <span className="grow">
                <div className="node-title">{p.grammar_point}</div>
                <div className="node-sub">
                  {p.lesson_title} · {p.unit_title}
                </div>
              </span>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
