import { useEffect, useState } from "react";
import { api, Drill as DrillT, PathView } from "../api";
import { useLevel } from "../level";

export default function Drill() {
  const { level } = useLevel();
  const [lessons, setLessons] = useState<string[]>([]);
  const [lessonId, setLessonId] = useState<string>("");
  const [result, setResult] = useState<DrillT | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.path("a1").then((p: PathView) => {
      const ids = p.units.flatMap((u) => u.lessons);
      setLessons(ids);
      setLessonId(ids[0] ?? "");
    }).catch((e) => setError(e.message));
  }, []);

  const generate = async () => {
    if (!lessonId) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.drill(lessonId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1>Practice drill</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        A short scaffolded drill — one model sentence, one small change.
      </p>

      {level !== "a1" && (
        <div className="feedback" style={{ marginTop: 0, marginBottom: 12 }}>
          Practice drills currently cover <strong>A1</strong> lessons only — more levels coming soon.
        </div>
      )}

      <div className="card stack">
        <div className="field">
          <label>Lesson</label>
          <select className="text-input" value={lessonId} onChange={(e) => setLessonId(e.target.value)}>
            {lessons.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </div>
        <button className="btn" onClick={generate} disabled={busy || !lessonId}>
          {busy ? "Thinking…" : "Give me a drill"}
        </button>
      </div>

      {error && <div className="feedback no" style={{ marginTop: 16 }}>{error}</div>}

      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          {result.over_budget ? (
            <div className="feedback no" style={{ margin: 0 }}>{result.drill}</div>
          ) : (
            <>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0, font: "inherit" }}>{result.drill}</pre>
              <div className="muted" style={{ marginTop: 12, fontSize: 13 }}>
                via {result.provider}/{result.model} · {result.tokens_used_today}/{result.daily_budget} tokens today
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
