import { useEffect, useState } from "react";
import { api, WeakSpot, WeakSpotAnswer } from "../api";

// Targeted re-practice of comprehension questions the learner got wrong. Each
// card lets them re-answer inline: correct clears it from the queue, wrong keeps
// it (and bumps the miss count). "Got it" dismisses without re-answering.
export default function WeakSpots() {
  const [items, setItems] = useState<WeakSpot[] | null>(null);
  const [error, setError] = useState("");
  const [graded, setGraded] = useState<Record<number, WeakSpotAnswer>>({});
  const [picked, setPicked] = useState<Record<number, string>>({});

  const load = () =>
    api.weakSpots().then((r) => setItems(r.weak_spots)).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const answer = async (id: number, chosen: string) => {
    setPicked((p) => ({ ...p, [id]: chosen }));
    const res = await api.answerWeakSpot(id, chosen);
    setGraded((g) => ({ ...g, [id]: res }));
    if (res.correct) setTimeout(() => setItems((it) => (it || []).filter((w) => w.id !== id)), 900);
  };
  const dismiss = async (id: number) => {
    await api.dismissWeakSpot(id);
    setItems((it) => (it || []).filter((w) => w.id !== id));
  };

  if (error) return <div className="card center">Couldn't load weak spots: {error}</div>;
  if (!items) return <div className="muted">Loading…</div>;

  if (items.length === 0) {
    return (
      <div>
        <h1>Weak spots</h1>
        <div className="card center">
          <p>No weak spots right now. Questions you miss in Read &amp; Listen show up here for
            targeted re-practice.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1>Weak spots</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        {items.length} question{items.length > 1 ? "s" : ""} to re-practice — answer correctly to
        clear each one.
      </p>

      {items.map((w) => {
        const g = graded[w.id];
        return (
          <div className="card" key={w.id}>
            <div className="node-sub">
              {w.set_title} · {w.skill} · missed {w.times_missed}×
            </div>
            <div className="node-title" style={{ margin: "6px 0 10px" }}>{w.prompt}</div>
            {w.options.map((o) => {
              const isCorrectAnswer = !!g && g.correct_answer === o;
              const isUserWrongPick = !!g && !g.correct && picked[w.id] === o;
              return (
                <button
                  key={o}
                  className={`option${isCorrectAnswer ? " correct" : ""}${isUserWrongPick ? " wrong" : ""}`}
                  disabled={!!g?.correct}
                  onClick={() => answer(w.id, o)}
                >
                  {o}
                </button>
              );
            })}
            {g && (
              <div className="node-sub" style={{ marginTop: 8 }}>
                {g.correct ? "✅ Correct — cleared" : `❌ Not quite. Answer: ${g.correct_answer}`}
                {g.explain && <> — {g.explain}</>}
              </div>
            )}
            <button className="link-btn" style={{ marginTop: 8 }} onClick={() => dismiss(w.id)}>
              Got it — remove
            </button>
          </div>
        );
      })}
    </div>
  );
}
