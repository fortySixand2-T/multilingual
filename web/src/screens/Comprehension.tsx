import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, CompSetSummary } from "../api";

export default function Comprehension() {
  const nav = useNavigate();
  const [sets, setSets] = useState<CompSetSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.comprehensionSets("a1").then((r) => setSets(r.sets)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load comprehension: {error}</div>;
  if (!sets) return <div className="muted">Loading…</div>;

  const groups: { skill: "reading" | "listening"; label: string; icon: string }[] = [
    { skill: "reading", label: "Reading", icon: "📖" },
    { skill: "listening", label: "Listening", icon: "🎧" },
  ];

  return (
    <div>
      <h1>Read &amp; Listen</h1>
      <p className="muted" style={{ marginTop: -10 }}>Timed comprehension sets — graded with explanations.</p>

      {groups.map((g) => {
        const items = sets.filter((s) => s.skill === g.skill);
        if (items.length === 0) return null;
        return (
          <div className="unit" key={g.skill}>
            <div className="unit-head">
              <div className="unit-icon">{g.icon}</div>
              <div className="unit-title">{g.label}</div>
            </div>
            {items.map((s) => (
              <button key={s.id} className="lesson-node" onClick={() => nav(`/comprehension/${s.id}`)}>
                <span className="node-dot available">{g.icon}</span>
                <span className="grow">
                  <div className="node-title">{s.title}</div>
                  <div className="node-sub">
                    {s.questions} questions
                    {s.time_limit_seconds ? ` · ${s.time_limit_seconds}s` : ""}
                    {s.accent ? ` · ${s.accent.toUpperCase()} accent` : ""}
                    {!s.allow_replay ? " · no replay" : ""}
                  </div>
                </span>
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}
