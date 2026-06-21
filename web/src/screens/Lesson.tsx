import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Exercise, Lesson as LessonT, LessonResult } from "../api";
import AudioButton from "../AudioButton";

const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, " ");

export default function Lesson() {
  const { id = "" } = useParams();
  const [lesson, setLesson] = useState<LessonT | null>(null);
  const [error, setError] = useState("");
  const [idx, setIdx] = useState(0);
  const [correct, setCorrect] = useState(0);
  const [checked, setChecked] = useState<boolean | null>(null);
  const [result, setResult] = useState<LessonResult | null>(null);

  useEffect(() => {
    api.lesson(id).then(setLesson).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="card center">Couldn't load lesson: {error}</div>;
  if (!lesson) return <div className="muted">Loading…</div>;

  const total = lesson.exercises.length;

  if (result) {
    return (
      <div className="card center stack">
        <div style={{ fontSize: 44 }}>{result.passed ? "🎉" : "💪"}</div>
        <h2>{result.passed ? "Lesson complete!" : "Almost there"}</h2>
        <p className="muted">You got {correct} / {total} right.</p>
        {result.passed && (
          <div className="btn-row center" style={{ justifyContent: "center" }}>
            <span className="pill">🔥 {result.streak}</span>
            <span className="pill">⭐ {result.xp} XP</span>
            {result.first_time && <span className="pill">🆕 new words added to Review</span>}
          </div>
        )}
        <Link className="btn" to="/">Back to path</Link>
      </div>
    );
  }

  const ex = lesson.exercises[idx];
  const onChecked = (ok: boolean) => {
    setChecked(ok);
    if (ok) setCorrect((c) => c + 1);
  };

  const next = async () => {
    if (idx + 1 < total) {
      setIdx(idx + 1);
      setChecked(null);
      return;
    }
    const score = (correct / total) * 10; // 0–10 scale
    try {
      setResult(await api.submitResult(lesson.id, score));
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div>
      <div className="progress-bar"><div style={{ width: `${(idx / total) * 100}%` }} /></div>
      <h2 className="muted" style={{ fontWeight: 600 }}>{lesson.title}</h2>

      <div className="card">
        <ExerciseView key={ex.id} ex={ex} disabled={checked !== null} onChecked={onChecked} />
        {checked !== null && (
          <div className={`feedback ${checked ? "ok" : "no"}`}>
            {checked ? "Correct!" : "Not quite — keep going."}
          </div>
        )}
      </div>

      {checked !== null && (
        <button className="btn wide" style={{ marginTop: 16 }} onClick={next}>
          {idx + 1 < total ? "Continue" : "Finish"}
        </button>
      )}
    </div>
  );
}

function ExerciseView({
  ex,
  disabled,
  onChecked,
}: {
  ex: Exercise;
  disabled: boolean;
  onChecked: (ok: boolean) => void;
}) {
  switch (ex.type) {
    case "mcq":
      return <Mcq ex={ex} disabled={disabled} onChecked={onChecked} />;
    case "word_bank":
      return <WordBank ex={ex} disabled={disabled} onChecked={onChecked} />;
    case "listen_type":
      return <ListenType ex={ex} disabled={disabled} onChecked={onChecked} />;
    case "translate":
      return <Translate ex={ex} disabled={disabled} onChecked={onChecked} />;
    case "match_pairs":
      return <MatchPairs ex={ex} disabled={disabled} onChecked={onChecked} />;
    default:
      return <div className="muted">Unsupported exercise: {ex.type}</div>;
  }
}

type SubProps = { ex: Exercise; disabled: boolean; onChecked: (ok: boolean) => void };

function Mcq({ ex, disabled, onChecked }: SubProps) {
  const [sel, setSel] = useState<string | null>(null);
  return (
    <div className="exercise">
      <div className="prompt">{ex.prompt}</div>
      <div className="options">
        {(ex.options as string[]).map((o) => {
          const cls = disabled
            ? o === ex.answer ? "correct" : o === sel ? "wrong" : ""
            : sel === o ? "selected" : "";
          return (
            <button key={o} className={`option ${cls}`} disabled={disabled} onClick={() => setSel(o)}>{o}</button>
          );
        })}
      </div>
      {!disabled && (
        <button className="btn wide" style={{ marginTop: 16 }} disabled={sel === null} onClick={() => onChecked(sel === ex.answer)}>
          Check
        </button>
      )}
    </div>
  );
}

function WordBank({ ex, disabled, onChecked }: SubProps) {
  const tokens = ex.tokens as string[];
  const answer = ex.answer as string[];
  const [build, setBuild] = useState<number[]>([]);
  const used = new Set(build);
  const check = () => onChecked(JSON.stringify(build.map((i) => tokens[i])) === JSON.stringify(answer));

  return (
    <div className="exercise">
      <div className="prompt">{ex.prompt}</div>
      <div className="build-line">
        {build.map((i, pos) => (
          <button key={pos} className="tile" disabled={disabled} onClick={() => setBuild(build.filter((_, p) => p !== pos))}>
            {tokens[i]}
          </button>
        ))}
      </div>
      <div className="tiles">
        {tokens.map((t, i) =>
          used.has(i) ? null : (
            <button key={i} className="tile" disabled={disabled} onClick={() => setBuild([...build, i])}>{t}</button>
          )
        )}
      </div>
      {!disabled && (
        <button className="btn wide" style={{ marginTop: 16 }} disabled={build.length === 0} onClick={check}>Check</button>
      )}
    </div>
  );
}

function ListenType({ ex, disabled, onChecked }: SubProps) {
  const [val, setVal] = useState("");
  return (
    <div className="exercise">
      <div className="prompt">Type what you hear</div>
      <AudioButton audioKey={ex.audio_ref} label="🔊 Play" style={{ marginBottom: 12 }} />
      <input className="text-input" value={val} disabled={disabled} onChange={(e) => setVal(e.target.value)} placeholder="écrivez ici…" />
      {!disabled && (
        <button className="btn wide" style={{ marginTop: 16 }} disabled={!val.trim()} onClick={() => onChecked(norm(val) === norm(ex.answer))}>Check</button>
      )}
    </div>
  );
}

function Translate({ ex, disabled, onChecked }: SubProps) {
  const [val, setVal] = useState("");
  const accept = [ex.answer as string, ...((ex.accept as string[]) ?? [])];
  return (
    <div className="exercise">
      <div className="prompt">{ex.prompt}</div>
      <input className="text-input" value={val} disabled={disabled} onChange={(e) => setVal(e.target.value)} placeholder="traduisez…" />
      {!disabled && (
        <button className="btn wide" style={{ marginTop: 16 }} disabled={!val.trim()} onClick={() => onChecked(accept.some((a) => norm(a) === norm(val)))}>Check</button>
      )}
    </div>
  );
}

function MatchPairs({ ex, disabled, onChecked }: SubProps) {
  const pairs = ex.pairs as [string, string][];
  const rights = useMemo(() => pairs.map((p) => p[1]).sort(() => Math.random() - 0.5), [ex.id]);
  const [pickL, setPickL] = useState<number | null>(null);
  const [matched, setMatched] = useState<Set<number>>(new Set());

  const tapRight = (rightVal: string) => {
    if (pickL === null) return;
    if (pairs[pickL][1] === rightVal) {
      const m = new Set(matched).add(pickL);
      setMatched(m);
      setPickL(null);
      if (m.size === pairs.length) onChecked(true);
    } else {
      setPickL(null);
    }
  };

  return (
    <div className="exercise">
      <div className="prompt">Match the pairs</div>
      <div className="btn-row" style={{ justifyContent: "space-between" }}>
        <div className="stack" style={{ flex: 1 }}>
          {pairs.map((p, i) => (
            <button key={i} className={`option ${matched.has(i) ? "correct" : pickL === i ? "selected" : ""}`}
              disabled={disabled || matched.has(i)} onClick={() => setPickL(i)}>{p[0]}</button>
          ))}
        </div>
        <div className="stack" style={{ flex: 1 }}>
          {rights.map((r) => {
            const done = pairs.some((p, i) => matched.has(i) && p[1] === r);
            return (
              <button key={r} className={`option ${done ? "correct" : ""}`} disabled={disabled || done} onClick={() => tapRight(r)}>{r}</button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
