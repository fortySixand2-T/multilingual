import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { api, Me, PathView } from "../api";
import { useLevel } from "../level";

const TOOLS = [
  { to: "/vocab", icon: "📗", label: "Vocab" },
  { to: "/grammar", icon: "📖", label: "Grammar" },
  { to: "/drill", icon: "🎯", label: "Drill" },
  { to: "/comprehension", icon: "🎧", label: "Read & Listen" },
  { to: "/writing", icon: "✍️", label: "Write" },
  { to: "/speaking", icon: "🎙️", label: "Speak" },
  { to: "/weak-spots", icon: "🩹", label: "Weak spots" },
  { to: "/readiness", icon: "📊", label: "Readiness" },
];

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

      {me && <DailyGoal today={me.xp_today} goal={me.daily_goal} />}

      <h2 className="section-label">Practice &amp; tools</h2>
      <nav className="tool-grid" aria-label="Practice & tools">
        {TOOLS.map((t) => (
          <NavLink key={t.to} to={t.to} className="tool-card">
            <span className="tool-icon">{t.icon}</span>
            <span className="tool-label">{t.label}</span>
          </NavLink>
        ))}
      </nav>

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

function DailyGoal({ today, goal }: { today: number; goal: number }) {
  const pct = goal > 0 ? Math.min(1, today / goal) : 0;
  const R = 20;
  const C = 2 * Math.PI * R;
  const done = goal > 0 && today >= goal;
  return (
    <div className={`daily-goal ${done ? "done" : ""}`}>
      <div className="daily-ring" aria-hidden="true">
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle className="ring-track" cx="26" cy="26" r={R} />
          <circle
            className="ring-fill"
            cx="26"
            cy="26"
            r={R}
            strokeDasharray={C}
            strokeDashoffset={C * (1 - pct)}
            transform="rotate(-90 26 26)"
          />
        </svg>
        <span className="ring-center">{done ? "🎉" : today}</span>
      </div>
      <div className="grow">
        <div className="daily-goal-title">{done ? "Daily goal reached!" : "Daily goal"}</div>
        <div className="daily-goal-sub">
          {done
            ? `${today} XP today — nice. Come back tomorrow to keep it going.`
            : `${today} / ${goal} XP today`}
        </div>
      </div>
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
