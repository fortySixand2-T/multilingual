import { useEffect, useState } from "react";
import {
  api,
  ExamAttemptSummary,
  ExamBlueprint,
  ExamBlueprintSummary,
  ExamReport,
  ExamSection,
  ExamSectionResult,
} from "../api";
import { useLevel } from "../level";

export default function Exam() {
  const { level } = useLevel();
  // The TEF Canada mock is one exam for every level; DELF + level practice are per level.
  const [tefMocks, setTefMocks] = useState<ExamBlueprintSummary[]>([]);
  const [blueprints, setBlueprints] = useState<ExamBlueprintSummary[]>([]);
  const [history, setHistory] = useState<ExamAttemptSummary[]>([]);
  const [attempt, setAttempt] = useState<{ id: number; blueprint: ExamBlueprint } | null>(null);
  const [recorded, setRecorded] = useState<Record<string, boolean>>({});
  const [outcome, setOutcome] = useState<{ report: ExamReport; xp: number; streak: number } | null>(
    null,
  );
  const [error, setError] = useState("");

  const loadLists = () => {
    api.examBlueprints("tef").then((r) => setTefMocks(r.blueprints)).catch((e) => setError(e.message));
    api.examBlueprints(level).then((r) => setBlueprints(r.blueprints)).catch((e) => setError(e.message));
    api.examHistory().then((r) => setHistory(r.attempts)).catch(() => {});
  };
  useEffect(() => {
    // A level switch must drop any in-progress attempt / report view from the
    // previous level, then reload that level's blueprints + history (qa-391).
    setAttempt(null);
    setRecorded({});
    setOutcome(null);
    setError("");
    loadLists();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level]);

  const start = async (id: string) => {
    setError("");
    try {
      const r = await api.examStart(id);
      setAttempt({ id: r.attempt_id, blueprint: r.blueprint });
      setRecorded({});
      setOutcome(null);
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
      setRecorded(Object.fromEntries(d.recorded.map((s) => [s, true])));
      setOutcome(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const finish = async () => {
    if (!attempt) return;
    setError("");
    try {
      const r = await api.examFinish(attempt.id);
      setOutcome({ report: r.report, xp: r.xp, streak: r.streak });
      setAttempt(null);
      loadLists();
    } catch (e: any) {
      setError(e.message); // e.g. 409 if a section is still missing
    }
  };

  if (outcome) {
    return (
      <div>
        <h1>Mock results</h1>
        <ReportCard report={outcome.report} />
        {/* Surface the XP/streak the finish awarded, like the comprehension result (qa-465). */}
        <div className="btn-row center" style={{ justifyContent: "center", marginTop: 12 }}>
          <span className="pill">🔥 {outcome.streak}</span>
          <span className="pill">⭐ {outcome.xp} XP</span>
        </div>
        <button className="btn" style={{ marginTop: 16 }} onClick={() => setOutcome(null)}>Done</button>
      </div>
    );
  }

  if (attempt) {
    const allRecorded = attempt.blueprint.sections.every((s) => recorded[s.skill]);
    const delf = attempt.blueprint.format === "delf";
    return (
      <div>
        <h1>{attempt.blueprint.title}</h1>
        <p className="muted" style={{ marginTop: -10 }}>
          Practice each section (opens in a new tab), then record your result.{" "}
          {delf
            ? "Each épreuve is marked /25 — you pass with 50/100 and at least 5/25 in every section."
            : "Finish for your CLB estimate."}
        </p>
        <div className="stack">
          {attempt.blueprint.sections.map((s) => (
            <SectionRow
              key={s.skill}
              section={s}
              delf={delf}
              recorded={!!recorded[s.skill]}
              onRecord={async (body) => {
                await api.examSection(attempt.id, body);
                setRecorded((prev) => ({ ...prev, [s.skill]: true }));
              }}
            />
          ))}
        </div>
        <button className="btn wide" style={{ marginTop: 16 }} disabled={!allRecorded} onClick={finish}>
          {!allRecorded
            ? "Record every section to finish"
            : delf
              ? "Finish & see DELF result"
              : "Finish & see CLB report"}
        </button>
        {error && <div className="feedback no" style={{ marginTop: 12 }}>{error}</div>}
      </div>
    );
  }

  const inProgress = history.filter((a) => a.status === "in_progress");
  const scored = history.filter((a) => a.clb_report);
  return (
    <div>
      <h1>Mock exam</h1>
      <p className="muted" style={{ marginTop: -10 }}>
        Timed four-section mocks: the TEF Canada exam, or a DELF diploma at your level.
      </p>

      <MockList
        icon="🍁"
        title="TEF Canada — full exam"
        sub="One exam for every level: each test climbs from A1 to B2 · CLB per skill"
        mocks={tefMocks}
        onStart={start}
      />
      <MockList
        icon="🎓"
        title={`DELF ${level.toUpperCase()}`}
        sub="Diploma format · each épreuve /25 · pass with 50/100"
        mocks={blueprints.filter((b) => b.format === "delf")}
        onStart={start}
      />
      <MockList
        icon="📝"
        title="Level practice"
        sub={`TEF-style sections using ${level.toUpperCase()} material · CLB estimate`}
        mocks={blueprints.filter((b) => b.format !== "delf")}
        onStart={start}
      />
      {tefMocks.length + blueprints.length === 0 && <div className="card muted">No mocks available yet.</div>}

      {inProgress.length > 0 && (
        <div className="unit">
          <div className="unit-head"><div className="unit-icon">⏸️</div><div className="unit-title">In progress</div></div>
          {inProgress.map((a) => (
            <button key={a.attempt_id} className="lesson-node" onClick={() => resume(a.attempt_id)}>
              <span className="node-dot available">↻</span>
              <span className="grow">
                <div className="node-title">Resume mock · {examLabel(a)}</div>
                <div className="node-sub">started {new Date(a.started_at).toLocaleString()} · pick up where you left off</div>
              </span>
            </button>
          ))}
        </div>
      )}

      {scored.length > 0 && (
        <div className="unit">
          <div className="unit-head"><div className="unit-icon">📊</div><div className="unit-title">Score history</div></div>
          <div className="stack">
            {scored.map((a) => (
              <div className="card" key={a.attempt_id}>
                <div className="muted" style={{ fontSize: 13 }}>{examLabel(a)} · {new Date(a.started_at).toLocaleString()}</div>
                <ReportCard report={a.clb_report!} compact />
              </div>
            ))}
          </div>
        </div>
      )}
      {error && <div className="feedback no" style={{ marginTop: 12 }}>{error}</div>}
    </div>
  );
}

function examLabel(a: ExamAttemptSummary) {
  if (a.level === "tef") return "TEF Canada";
  const lvl = a.level.toUpperCase();
  return a.blueprint_id.startsWith("delf-") ? `DELF ${lvl}` : lvl;
}

function MockList({
  icon,
  title,
  sub,
  mocks,
  onStart,
}: {
  icon: string;
  title: string;
  sub: string;
  mocks: ExamBlueprintSummary[];
  onStart: (id: string) => void;
}) {
  if (mocks.length === 0) return null;
  return (
    <div className="unit">
      <div className="unit-head"><div className="unit-icon">{icon}</div><div className="unit-title">{title}</div></div>
      <p className="muted" style={{ fontSize: 13, margin: "0 0 8px" }}>{sub}</p>
      {mocks.map((b) => (
        <button key={b.id} className="lesson-node" onClick={() => onStart(b.id)}>
          <span className="node-dot available">▶</span>
          <span className="grow">
            <div className="node-title">{b.title}</div>
            <div className="node-sub">{b.sections} sections · start</div>
          </span>
        </button>
      ))}
    </div>
  );
}

// One practice link per document / task: a TEF or DELF comprehension test is several
// short documents, not a single set.
function practiceLinks(s: ExamSection): { href: string; label: string }[] {
  if (s.skill === "speaking") return [{ href: "/speaking", label: "Practice speaking" }];
  const writing = s.skill === "writing";
  const ids = (writing ? s.writing_task_ids : s.comprehension_set_ids) ?? [];
  const noun = writing ? "Task" : "Document";
  return ids.map((id, i) => ({
    href: `/${writing ? "writing" : "comprehension"}/${id}`,
    label: ids.length > 1 ? `${noun} ${i + 1}` : "Practice this section",
  }));
}

function SectionRow({
  section,
  delf,
  recorded,
  onRecord,
}: {
  section: ExamSection;
  delf: boolean;
  recorded: boolean;
  onRecord: (body: ExamSectionResult) => Promise<void>;
}) {
  const isComprehension = section.skill === "reading" || section.skill === "listening";
  const [correct, setCorrect] = useState("");
  const [total, setTotal] = useState("");
  const [clb, setClb] = useState("7");
  const [score, setScore] = useState("");
  const minutes = Math.round(section.time_limit_seconds / 60);
  const scoreValid = score.trim() !== "" && Number(score) >= 0 && Number(score) <= 25;

  const record = () =>
    onRecord(
      isComprehension
        ? { skill: section.skill, correct: Number(correct), total: Number(total) }
        : delf
          ? { skill: section.skill, score: Number(score) }
          : { skill: section.skill, clb_estimate: Number(clb) }
    );

  const canRecord = isComprehension ? correct !== "" && Number(total) > 0 : !delf || scoreValid;

  return (
    <div className="card">
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ textTransform: "capitalize" }}>{section.skill}</strong>
        <span className="muted">{minutes} min{recorded ? " · ✓ recorded" : ""}</span>
      </div>
      {!!section.speaking_prompts?.length && (
        <ol style={{ margin: "10px 0 0", paddingLeft: 20 }}>
          {section.speaking_prompts.map((p) => <li key={p} style={{ whiteSpace: "pre-line", marginBottom: 6 }}>{p}</li>)}
        </ol>
      )}
      <div className="btn-row" style={{ marginTop: 10, flexWrap: "wrap" }}>
        {practiceLinks(section).map((l) => (
          <a key={l.href} className="btn secondary" href={l.href} target="_blank" rel="noreferrer">{l.label} ↗</a>
        ))}
      </div>
      {!recorded && (
        <div className="btn-row" style={{ marginTop: 12, alignItems: "center" }}>
          {isComprehension ? (
            <>
              <input className="text-input" style={{ width: 80 }} placeholder="correct" value={correct} onChange={(e) => setCorrect(e.target.value)} />
              <span className="muted">/</span>
              <input className="text-input" style={{ width: 80 }} placeholder="total" value={total} onChange={(e) => setTotal(e.target.value)} />
            </>
          ) : delf ? (
            <>
              <input className="text-input" style={{ width: 80 }} placeholder="points" inputMode="decimal" value={score} onChange={(e) => setScore(e.target.value)} />
              <span className="muted">/ 25</span>
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

function ReportCard({ report, compact = false }: { report: ExamReport; compact?: boolean }) {
  const delf = report.format === "delf";
  const good = delf ? report.passed : report.target_met;
  const headline = delf ? `${report.total} / ${report.max}` : `CLB ${report.overall ?? "—"}`;
  return (
    <div className={compact ? "" : "card stack center"}>
      {!compact && (
        <div style={{ fontSize: 40, fontWeight: 800, color: good ? "var(--green)" : "var(--gold)" }}>{headline}</div>
      )}
      {!compact && delf && (
        <div className="muted">
          {report.passed ? "Pass" : "Not yet — a pass needs 50/100 and at least 5/25 in every épreuve"}
        </div>
      )}
      <div className="btn-row" style={{ justifyContent: compact ? "flex-start" : "center", flexWrap: "wrap", marginTop: 6 }}>
        {Object.entries(report.per_skill).map(([skill, v]) => (
          <span key={skill} className="pill" style={{ textTransform: "capitalize" }}>
            {skill}: {delf ? `${v}/25` : `CLB ${v}`}
          </span>
        ))}
        {compact && (
          <span className="pill" style={{ fontWeight: 800 }}>
            {delf ? `${headline} · ${report.passed ? "pass" : "not yet"}` : `overall ${report.overall ?? "—"}`}
          </span>
        )}
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>{report.note}</div>
    </div>
  );
}
