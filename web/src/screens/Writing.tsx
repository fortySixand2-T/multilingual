import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, WritingTaskSummary } from "../api";

const SECTION_LABEL: Record<string, string> = {
  A: "Section A · short response",
  B: "Section B · argumentative",
};

export default function Writing() {
  const nav = useNavigate();
  const [tasks, setTasks] = useState<WritingTaskSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.writingTasks("a1").then((r) => setTasks(r.tasks)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load writing tasks: {error}</div>;
  if (!tasks) return <div className="muted">Loading…</div>;

  return (
    <div>
      <h1>Writing</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        Write a response and get rubric feedback with a CLB estimate.
      </p>

      {(["A", "B"] as const).map((section) => {
        const items = tasks.filter((t) => t.section === section);
        if (items.length === 0) return null;
        return (
          <div className="unit" key={section}>
            <div className="unit-head">
              <div className="unit-icon">✍️</div>
              <div className="unit-title">{SECTION_LABEL[section]}</div>
            </div>
            {items.map((t) => (
              <button key={t.id} className="lesson-node" onClick={() => nav(`/writing/${t.id}`)}>
                <span className="node-dot available">✍️</span>
                <span className="grow">
                  <div className="node-title">{t.title}</div>
                  <div className="node-sub">
                    {t.min_words}{t.max_words ? `–${t.max_words}` : "+"} words
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
