import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, CompResult, CompSetView, fetchAudioUrl } from "../api";

export default function ComprehensionSet() {
  const { id = "" } = useParams();
  const [set, setSet] = useState<CompSetView | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [played, setPlayed] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<CompResult | null>(null);
  const [error, setError] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const submitting = useRef(false);

  useEffect(() => {
    api.comprehensionSet(id).then(setSet).catch((e) => setError(e.message));
  }, [id]);

  // fetch audio bytes (with auth) for listening sets
  useEffect(() => {
    if (set?.skill === "listening" && set.audio_url) {
      fetchAudioUrl(set.audio_url).then(setAudioUrl).catch(() => setError("Couldn't load audio"));
    }
  }, [set]);

  // tick the clock until submitted
  useEffect(() => {
    if (result) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [result]);

  const limit = set?.time_limit_seconds ?? null;
  const remaining = limit !== null ? Math.max(0, limit - elapsed) : null;

  const submit = async () => {
    if (submitting.current || result || !set) return;
    submitting.current = true;
    try {
      setResult(await api.submitComprehension(set.id, answers, elapsed));
    } catch (e: any) {
      setError(e.message);
      submitting.current = false;
    }
  };

  // auto-submit when the timer runs out
  useEffect(() => {
    if (remaining === 0 && !result) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining]);

  if (error) return <div className="card center">Couldn't load set: {error}</div>;
  if (!set) return <div className="muted">Loading…</div>;

  if (result) return <Results set={set} result={result} />;

  const allAnswered = set.questions.every((q) => answers[q.id]);

  return (
    <div>
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{set.title}</h2>
        {remaining !== null && (
          <span className="pill" style={{ color: remaining <= 10 ? "var(--coral)" : undefined }}>
            ⏱ {remaining}s
          </span>
        )}
      </div>

      {set.skill === "reading" && set.passage && (
        <div className="card" style={{ whiteSpace: "pre-wrap", marginTop: 14 }}>{set.passage}</div>
      )}

      {set.skill === "listening" && (
        <div className="card center stack" style={{ marginTop: 14 }}>
          {set.accent && <div className="muted">{set.accent.toUpperCase()} accent</div>}
          {!audioUrl ? (
            <div className="muted">Loading audio…</div>
          ) : set.allow_replay ? (
            <audio controls src={audioUrl} />
          ) : (
            <>
              <audio ref={audioRef} src={audioUrl} onEnded={() => setPlayed(true)} />
              <button className="btn" disabled={played} onClick={() => audioRef.current?.play()}>
                {played ? "Played" : "▶ Play once"}
              </button>
              <div className="muted" style={{ fontSize: 13 }}>No replay — exam mode</div>
            </>
          )}
        </div>
      )}

      <div className="stack" style={{ marginTop: 18 }}>
        {set.questions.map((q) => (
          <div className="card" key={q.id}>
            <div className="prompt">{q.prompt}</div>
            <div className="options">
              {q.options.map((o) => (
                <button
                  key={o}
                  className={`option ${answers[q.id] === o ? "selected" : ""}`}
                  onClick={() => setAnswers({ ...answers, [q.id]: o })}
                >
                  {o}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button className="btn wide" style={{ marginTop: 16 }} disabled={!allAnswered} onClick={submit}>
        Submit{allAnswered ? "" : " (answer all questions)"}
      </button>
    </div>
  );
}

function Results({ set, result }: { set: CompSetView; result: CompResult }) {
  const byId = Object.fromEntries(set.questions.map((q) => [q.id, q]));
  return (
    <div>
      <div className="card center stack">
        <div style={{ fontSize: 40 }}>{result.passed ? "🎉" : "💪"}</div>
        <h2>{result.passed ? "Passed" : "Keep practicing"}</h2>
        <p className="muted">
          {result.correct} / {result.total} correct
          {result.over_time ? " · over time" : ""}
        </p>
        {result.first_pass && <span className="pill">⭐ +15 XP</span>}
      </div>

      <div className="stack" style={{ marginTop: 16 }}>
        {result.results.map((r) => (
          <div className="card" key={r.question_id}>
            <div className="prompt" style={{ fontSize: 16 }}>{byId[r.question_id]?.prompt}</div>
            <div className={`feedback ${r.correct ? "ok" : "no"}`} style={{ marginTop: 8 }}>
              {r.correct ? "✓ " : "✗ "}
              Your answer: {r.your_answer ?? "—"}
              {!r.correct && ` · Correct: ${r.correct_answer}`}
            </div>
            {r.explain && <div className="muted" style={{ marginTop: 8 }}>{r.explain}</div>}
          </div>
        ))}
      </div>

      <Link className="btn wide" style={{ marginTop: 16, display: "inline-block", textAlign: "center" }} to="/comprehension">
        Back to comprehension
      </Link>
    </div>
  );
}
