import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, WritingFeedback, WritingGrade, WritingTaskSummary } from "../api";

function clbColor(clb: number): string {
  if (clb >= 7) return "var(--green)";
  if (clb >= 5) return "var(--gold)";
  return "var(--coral)";
}

export default function WritingTask() {
  const { id = "" } = useParams();
  const [task, setTask] = useState<(WritingTaskSummary & { level: string }) | null>(null);
  const [text, setText] = useState("");
  const [grade, setGrade] = useState<WritingGrade | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.writingTask(id).then(setTask).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="card center">Couldn't load task: {error}</div>;
  if (!task) return <div className="muted">Loading…</div>;

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const tooShort = words < task.min_words;
  const tooLong = task.max_words != null && words > task.max_words;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      setGrade(await api.submitWriting(task.id, text));
    } catch (e: any) {
      setError(
        e.status === 503 ? "The AI grader is temporarily unavailable. Try again shortly."
          : e.status === 502 ? "The grader returned an unexpected result. Please resubmit."
          : e.message
      );
    } finally {
      setBusy(false);
    }
  };

  if (grade && !grade.over_budget && grade.feedback) {
    return <Feedback task={task} grade={grade} feedback={grade.feedback} onEdit={() => setGrade(null)} />;
  }

  return (
    <div>
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{task.title}</h2>
        <span className="pill">Section {task.section}</span>
      </div>

      <div className="card" style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>{task.prompt}</div>

      <textarea
        className="text-input"
        style={{ marginTop: 14, minHeight: 200, resize: "vertical", fontFamily: "inherit" }}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Écrivez votre réponse ici…"
      />

      <div className="btn-row" style={{ justifyContent: "space-between", marginTop: 8 }}>
        <span className="muted" style={{ color: tooShort || tooLong ? "var(--coral)" : undefined }}>
          {words} words · target {task.min_words}{task.max_words ? `–${task.max_words}` : "+"}
        </span>
      </div>

      {grade?.over_budget && (
        <div className="feedback no" style={{ marginTop: 12 }}>
          You've reached today's writing-feedback limit. Try again tomorrow.
        </div>
      )}
      {error && <div className="feedback no" style={{ marginTop: 12 }}>{error}</div>}

      <button className="btn wide" style={{ marginTop: 14 }} disabled={busy || words === 0} onClick={submit}>
        {busy ? "Grading…" : "Submit for feedback"}
      </button>
    </div>
  );
}

function Feedback({
  task,
  grade,
  feedback,
  onEdit,
}: {
  task: WritingTaskSummary;
  grade: WritingGrade;
  feedback: WritingFeedback;
  onEdit: () => void;
}) {
  const clb = feedback.clb_estimate;
  return (
    <div>
      <div className="card center stack">
        <div style={{ fontSize: 14 }} className="muted">Estimated level</div>
        <div style={{ fontSize: 44, fontWeight: 800, color: clbColor(clb) }}>CLB {clb}</div>
        <div className="muted">{clb >= 7 ? "≈ B2 — target reached 🎯" : "target: CLB 7 (≈ B2)"}</div>
        <div className="btn-row center" style={{ justifyContent: "center" }}>
          <span className="pill">{grade.word_count} words</span>
          {grade.meets_min_words === false && <span className="pill" style={{ color: "var(--coral)" }}>below min length</span>}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Rubric</h2>
        {feedback.criteria.map((c) => (
          <div key={c.name} style={{ marginBottom: 12 }}>
            <div className="btn-row" style={{ justifyContent: "space-between" }}>
              <strong style={{ textTransform: "capitalize" }}>{c.name.replace(/_/g, " ")}</strong>
              <span className="muted">{c.score}/10</span>
            </div>
            <div className="progress-bar" style={{ margin: "6px 0" }}>
              <div style={{ width: `${c.score * 10}%` }} />
            </div>
            {c.comment && <div className="muted" style={{ fontSize: 14 }}>{c.comment}</div>}
          </div>
        ))}
      </div>

      {feedback.corrections.length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h2>Corrections</h2>
          {feedback.corrections.map((c, i) => (
            <div key={i} style={{ marginBottom: 14 }}>
              <div>
                <span style={{ textDecoration: "line-through", color: "var(--coral)" }}>{c.excerpt}</span>
                {"  →  "}
                <span style={{ color: "var(--green-dk)", fontWeight: 700 }}>{c.correction}</span>
              </div>
              <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>{c.explanation}</div>
              {c.reference && <span className="pill" style={{ marginTop: 6, fontSize: 12 }}>📘 {c.reference}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Overall</h2>
        <p style={{ margin: 0 }}>{feedback.overall}</p>
      </div>

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="btn secondary" onClick={onEdit}>Edit &amp; resubmit</button>
        <Link className="btn" to="/writing" style={{ display: "inline-block" }}>Back to writing</Link>
      </div>
    </div>
  );
}
