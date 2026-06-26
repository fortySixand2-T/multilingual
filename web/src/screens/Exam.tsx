import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  ClbReport,
  ExamAttemptSummary,
  ExamBlueprint,
  ExamBlueprintSummary,
  ExamSection,
} from "../api";
import { useLevel } from "../level";

export default function Exam() {
  const { level } = useLevel();
  const [blueprints, setBlueprints] = useState<ExamBlueprintSummary[]>([]);
  const [history, setHistory] = useState<ExamAttemptSummary[]>([]);
  const [attempt, setAttempt] = useState<{ id: number; blueprint: ExamBlueprint } | null>(null);
  const [recorded, setRecorded] = useState<Record<string, number>>({});
  const [report, setReport] = useState<ClbReport | null>(null);
  const [error, setError] = useState("");

  const loadLists = () => {
    api.examBlueprints(level).then((r) => setBlueprints(r.blueprints)).catch((e) => setError(e.message));
    api.examHistory().then((r) => setHistory(r.attempts)).catch(() => {});
  };
  useEffect(loadLists, [level]);

  const start = async (id: string) => {
    setError("");
    try {
      const r = await api.examStart(id);
      setAttempt({ id: r.attempt_id, blueprint: r.blueprint });
      setRecorded({});
      setReport(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Save/resume: reopen an in-progress attempt where it was left off.
  const resume = async (attemptId: number) => {
    setError("");
    try {
      const d = await api.examAttempt(attemptId);
      setAttempt({ id: d.attempt_id, blueprint: d.blueprint });
      setRecorded(Object.fromEntries(d.recorded.map((s) => [s, 1])));
      setReport(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const finish = async () => {
    if (!attempt) return;
    setError("");
    try {
      const r = await api.examFinish(attempt.id);
      setReport(r.report);
      setAttempt(null);
      loadLists();
    } catch (e: any) {
      setError(e.message); // e.g. 409 if a section is still missing
    }
  };

  if (report) {
    return (
      <div>
        <h1>Mock results</h1>
        <ClbReportCard report={report} />
        <button className="btn" style={{ marginTop: 16 }} onClick={() => setReport(null)}>Done</button>
      </div>
    );
  }

  if (attempt) {
    const allRecorded = attempt.blueprint.sections.every((s) => recorded[s.skill] != null);
    return (
      <div>
        <h1>{attempt.blueprint.title}</h1>
        <p className="muted" style={{ marginTop: -10 }}>
          Practice each section (opens in a new tab), then record your result. Finish for your CLB estimate.
        </p>
        <div className="stack">
          {attempt.blueprint.sections.map((s) => (
            <SectionRow
              key={s.skill}
              section={s}
              recorded={recorded[s.skill] != null}
              onRecord={async (body) => {
                const r = await api.examSection(attempt.id, body);
                setRecorded((prev) => ({ ...prev, [s.skill]: r.clb }));
              }}
            />
          ))}
        </div>
        <button className="btn wide" style={{ marginTop: 16 }} disabled={!allRecorded} onClick={finish}>
          {allRecorded ? "Finish & see CLB report" : "Record every section to finish"}
        </button>
        {error && <div className="feedback no" style={{ marginTop: 12 }}>{error}</div>}
      </div>
    );
  }

  return (
    <div>
      <h1>Mock exam</h1>
      <p className="muted" style={{ marginTop: -10 }}>A timed four-section mock with a per-skill CLB estimate.</p>

      <div className="unit">
        <div className="unit-head"><div className="unit-icon">📝</div><div className="unit-title">Available mocks</div></div>
        {blueprints.map((b) => (
          <button key={b.id} className="lesson-node" onClick={() => start(b.id)}>
            <span className="node-dot available">▶</span>
            <span className="grow">
              <div className="node-title">{b.title}</div>
              <div className="node-sub">{b.sections} sections · start</div>
            </span>
          </button>
        ))}
        {blueprints.length === 0 && <div className="card muted">No mocks available yet.</div>}
      </div>

      {history.filter((a) => a.status === "in_progress").length > 0 && (
        <div className="unit">
          <div className="unit-head"><div className="unit-icon">⏸️</div><div className="unit-title">In progress</div></div>
          {history.filter((a) => a.status === "in_progress").map((a) => (
            <button key={a.attempt_id} className="lesson-node" onClick={() => resume(a.attempt_id)}>
              <span className="node-dot available">↻</span>
              <span className="grow">
                <div className="node-title">Resume mock</div>
                <div className="node-sub">started {new Date(a.started_at).toLocaleString()} · pick up where you left off</div>
              </span>
            </button>
          ))}
        </div>
      )}

      {history.filter((a) => a.clb_report).length > 0 && (
        <div className="unit">
          <div className="unit-head"><div className="unit-icon">📊</div><div className="unit-title">Score history</div></div>
          <div className="stack">
            {history.filter((a) => a.clb_report).map((a) => (
              <div className="card" key={a.attempt_id}>
                <div className="muted" style={{ fontSize: 13 }}>{new Date(a.started_at).toLocaleString()}</div>
                <ClbReportCard report={a.clb_report!} compact />
              </div>
            ))}
          </div>
        </div>
      )}
      {error && <div className="feedback no" style={{ marginTop: 12 }}>{error}</div>}
    </div>
  );
}

const PRACTICE_PATH: Record<ExamSection["skill"], (s: ExamSection) => string> = {
  reading: (s) => `/comprehension/${s.comprehension_set_id}`,
  listening: (s) => `/comprehension/${s.comprehension_set_id}`,
  writing: (s) => `/writing/${s.writing_task_ids?.[0] ?? ""}`,
  speaking: () => `/speaking`,
};

function SectionRow({
  section,
  recorded,
  onRecord,
}: {
  section: ExamSection;
  recorded: boolean;
  onRecord: (body: { skill: ExamSection["skill"]; correct?: number; total?: number; clb_estimate?: number }) => Promise<void>;
}) {
  const isComprehension = section.skill === "reading" || section.skill === "listening";
  const [correct, setCorrect] = useState("");
  const [total, setTotal] = useState("");
  const [clb, setClb] = useState("7");
  const minutes = Math.round(section.time_limit_seconds / 60);

  const record = () =>
    onRecord(
      isComprehension
        ? { skill: section.skill, correct: Number(correct), total: Number(total) }
        : { skill: section.skill, clb_estimate: Number(clb) }
    );

  const canRecord = isComprehension ? correct !== "" && Number(total) > 0 : true;

  return (
    <div className="card">
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ textTransform: "capitalize" }}>{section.skill}</strong>
        <span className="muted">{minutes} min{recorded ? " · ✓ recorded" : ""}</span>
      </div>
      <a className="btn secondary" style={{ marginTop: 10, display: "inline-block" }}
         href={PRACTICE_PATH[section.skill](section)} target="_blank" rel="noreferrer">
        Practice this section ↗
      </a>
      {!recorded && (
        <div className="btn-row" style={{ marginTop: 12, alignItems: "center" }}>
          {isComprehension ? (
            <>
              <input className="text-input" style={{ width: 80 }} placeholder="correct" value={correct} onChange={(e) => setCorrect(e.target.value)} />
              <span className="muted">/</span>
              <input className="text-input" style={{ width: 80 }} placeholder="total" value={total} onChange={(e) => setTotal(e.target.value)} />
            </>
          ) : (
            <label className="muted">CLB&nbsp;
              <select className="text-input" style={{ width: "auto", display: "inline-block" }} value={clb} onChange={(e) => setClb(e.target.value)}>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
          )}
          <button className="btn" disabled={!canRecord} onClick={record}>Record</button>
        </div>
      )}
    </div>
  );
}

function ClbReportCard({ report, compact = false }: { report: ClbReport; compact?: boolean }) {
  return (
    <div className={compact ? "" : "card stack center"}>
      {!compact && (
        <div style={{ fontSize: 40, fontWeight: 800, color: report.target_met ? "var(--green)" : "var(--gold)" }}>
          CLB {report.overall ?? "—"}
        </div>
      )}
      <div className="btn-row" style={{ justifyContent: compact ? "flex-start" : "center", flexWrap: "wrap", marginTop: 6 }}>
        {Object.entries(report.per_skill).map(([skill, band]) => (
          <span key={skill} className="pill" style={{ textTransform: "capitalize" }}>{skill}: CLB {band}</span>
        ))}
        {compact && <span className="pill" style={{ fontWeight: 800 }}>overall {report.overall ?? "—"}</span>}
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>{report.note}</div>
    </div>
  );
}
