import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Me, PathView } from "../api";
import { useLevel } from "../level";

export default function Path() {
  const nav = useNavigate();
  const { level } = useLevel();
  const [path, setPath] = useState<PathView | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setPath(null);
    setError("");
    api.path(level).then(setPath).catch((e) => setError(e.message));
    api.me().then(setMe).catch(() => {});
  }, [level]);

  if (error) return <div className="card center">Couldn't load your path: {error}</div>;
  if (!path) return <div className="muted">Loading…</div>;

  const passed = new Set(path.passed_lessons);
  const waived = new Set(path.waived_lessons);

  return (
    <div>
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h1>Your path · {path.level.toUpperCase()}</h1>
        {me && (
          <div className="btn-row">
            <span className="pill">🔥 {me.streak}</span>
            <span className="pill">⭐ {me.xp} XP</span>
          </div>
        )}
      </div>

      {path.units.map((u) => (
        <div className="unit" key={u.id}>
          <div className="unit-head">
            <div className="unit-icon">{iconFor(u.icon)}</div>
            <div className="grow">
              <div className="unit-title">{u.title}</div>
            </div>
            <span className={`badge ${u.status}`}>{u.status}</span>
          </div>

          {u.lessons.map((lessonId) => {
            const locked = u.status === "locked";
            const isPassed = passed.has(lessonId);
            const isWaived = waived.has(lessonId);
            const dot = isPassed ? "⭐" : isWaived ? "⚠️" : locked ? "🔒" : "★";
            const sub = locked
              ? "Finish the previous unit to unlock"
              : isPassed
                ? "Passed — tap to review"
                : isWaived
                  ? "Marked for review — retry to earn ⭐"
                  : "Tap to start";
            return (
              <button
                key={lessonId}
                className={`lesson-node ${locked ? "locked" : ""}`}
                disabled={locked}
                onClick={() => !locked && nav(`/lesson/${lessonId}`)}
              >
                <span className={`node-dot ${isWaived ? "waived" : u.status}`}>{dot}</span>
                <span className="grow">
                  <div className="node-title">{prettyLesson(lessonId)}</div>
                  <div className="node-sub">{sub}</div>
                </span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function iconFor(name: string): string {
  const map: Record<string, string> = { wave: "👋", coffee: "☕️" };
  return map[name] ?? "📘";
}
function prettyLesson(id: string): string {
  return id.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
