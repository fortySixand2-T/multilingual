import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Readiness as ReadinessData } from "../api";

// Per-skill CLB readiness from finished mock exams: a bar per skill toward the
// CLB 7 goal, the weakest skill highlighted with a nudge to practise it, and each
// skill's trend across attempts. Empty until the learner finishes a mock.
const SKILLS: { key: string; label: string; to: string }[] = [
  { key: "reading", label: "Reading", to: "/comprehension" },
  { key: "listening", label: "Listening", to: "/comprehension" },
  { key: "writing", label: "Writing", to: "/writing" },
  { key: "speaking", label: "Speaking", to: "/speaking" },
];

export default function Readiness() {
  const nav = useNavigate();
  const [data, setData] = useState<ReadinessData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.readiness().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load readiness: {error}</div>;
  if (!data) return <div className="muted">Loading…</div>;

  if (data.attempts === 0) {
    return (
      <div>
        <h1>Exam readiness</h1>
        <div className="card center">
          <p>Finish a mock exam to see your per-skill CLB estimate and where to focus.</p>
          <button className="btn" onClick={() => nav("/exam")}>Go to Mock exams</button>
        </div>
      </div>
    );
  }

  const target = data.target_clb;
  const pct = (clb: number) => Math.min(100, Math.round((clb / target) * 100));

  return (
    <div>
      <h1>Exam readiness</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        Estimated from {data.attempts} finished mock{data.attempts > 1 ? "s" : ""} — best CLB per
        skill toward the CLB {target} goal. Estimate only, not an official TEF result.
      </p>

      <div className="card">
        <div className="node-title">
          {data.target_met ? `🎉 On target — overall CLB ${data.overall}` : `Overall CLB ${data.overall ?? "—"} / ${target}`}
        </div>
        {data.weakest_skill && !data.target_met && (
          <div className="node-sub">
            Weakest skill: <strong>{data.weakest_skill}</strong> — focus your practice there.
          </div>
        )}
      </div>

      {SKILLS.map((s) => {
        const r = data.per_skill[s.key];
        if (!r) return null;
        const weak = s.key === data.weakest_skill && !data.target_met;
        return (
          <div className="unit" key={s.key}>
            <div className="unit-head">
              <div className="unit-title">
                {s.label} {weak && <span className="pill">focus</span>}
              </div>
              <div className="grow" />
              <div className="node-sub">
                best CLB {r.best}
                {r.recent !== r.best && <> · recent {r.recent}</>}
                {r.trend.length > 1 && <> · trend {r.trend.join("→")}</>}
              </div>
            </div>
            <div
              style={{
                height: 10,
                borderRadius: 6,
                background: "var(--muted-bg, #eee)",
                overflow: "hidden",
                margin: "6px 0",
              }}
            >
              <div
                style={{
                  width: `${pct(r.best)}%`,
                  height: "100%",
                  background: r.best >= target ? "#3ca35a" : weak ? "#e0a03c" : "#4a7fe0",
                }}
              />
            </div>
            <button className="link-btn" onClick={() => nav(s.to)}>Practise {s.label.toLowerCase()} →</button>
          </div>
        );
      })}
    </div>
  );
}
