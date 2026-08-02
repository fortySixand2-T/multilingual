import { useEffect, useRef, useState } from "react";
import {
  SpeakingTopic,
  SpeechTurnResult,
  VocabCandidate,
  api,
  fetchAudioUrl,
  postSpeechTurn,
} from "../api";
import { useSlowRate } from "../speed";
import { useLevel } from "../level";

type Turn = { transcript: string; reply_text: string; reply_audio_url: string | null };

export default function Speaking() {
  const { level } = useLevel();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [mode, setMode] = useState<"examiner" | "conversation">("examiner");
  const [topics, setTopics] = useState<SpeakingTopic[]>([]);
  const [topic, setTopic] = useState<SpeakingTopic | null>(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // null = still checking; avoids flashing the "unavailable" message before the
  // status check resolves.
  const [available, setAvailable] = useState<boolean | null>(null);
  // One conversation = one session (topic = session; changing topic starts a new
  // one). The end-of-conversation vocab review is scoped to this id.
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [sessionTurns, setSessionTurns] = useState(0); // turns spoken *this* session
  // The learner's most recent *prior* conversation, to resurface its review words
  // if they left without reviewing. Refetched whenever a new session starts.
  const [priorSession, setPriorSession] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    api.speechHistory()
      .then((r) =>
        setTurns(r.turns.map((t) => ({ transcript: t.transcript, reply_text: t.reply_text, reply_audio_url: t.reply_audio_url })))
      )
      .catch((e) => setError(e.message));
    // Preflight: don't let a learner grant a real mic permission and record
    // only to discover afterwards that speech isn't configured here (qa-540).
    api.speechStatus()
      .then((r) => setAvailable(r.available))
      .catch(() => setAvailable(true)); // fail open — don't block Record on a flaky check
  }, []);

  // Find the last conversation (excluding this fresh one) so we can offer to
  // resurface its review words. Cheap (no LLM); re-runs when the session changes
  // (e.g. after switching topics), so a just-abandoned conversation shows up.
  useEffect(() => {
    api.speechLastSession(sessionId)
      .then((r) => setPriorSession(r.session_id))
      .catch(() => setPriorSession(null));
  }, [sessionId]);

  // Load the authored topics for the current level; a picked topic is level-
  // specific, so drop it when the level changes.
  useEffect(() => {
    api.speakingTopics(level)
      .then((r) => setTopics(r.topics))
      .catch(() => setTopics([]));
    setTopic(null);
  }, [level]);

  const upload = async (blob: Blob) => {
    setBusy(true);
    setError("");
    try {
      const res: SpeechTurnResult = await postSpeechTurn(blob, mode, topic?.id, sessionId);
      if (res.over_budget) {
        setError("You've reached today's speaking-practice limit. Try again tomorrow.");
        return;
      }
      setTurns((t) => [...t, { transcript: res.transcript, reply_text: res.reply_text ?? "", reply_audio_url: res.reply_audio_url ?? null }]);
      setSessionTurns((n) => n + 1);
    } catch (e: any) {
      setError(
        e.status === 503 ? "Speaking practice isn't enabled on this server yet (no speech models configured)."
          : e.message
      );
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    if (available === false) {
      setError("Speaking practice isn't enabled on this server yet (no speech models configured).");
      return;
    }
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => e.data.size > 0 && chunks.current.push(e.data);
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        void upload(new Blob(chunks.current, { type: mr.mimeType || "audio/webm" }));
      };
      recorder.current = mr;
      mr.start();
      setRecording(true);
    } catch {
      setError("Couldn't access the microphone. Check browser permissions.");
    }
  };

  const stop = () => {
    recorder.current?.stop();
    setRecording(false);
  };

  // Topic = session: switching topics starts a fresh conversation (new id, clean
  // transcript panel) so the vocab review that follows covers only this exchange.
  const pickTopic = (t: SpeakingTopic | null) => {
    setTopic(t);
    setSessionId(crypto.randomUUID());
    setSessionTurns(0);
    setTurns([]);
    setError("");
  };

  return (
    <div>
      <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Speaking</h1>
        <select className="text-input" style={{ width: "auto" }} value={mode} onChange={(e) => setMode(e.target.value as any)} disabled={recording || busy}>
          <option value="examiner">Examiner</option>
          <option value="conversation">Conversation</option>
        </select>
      </div>
      <p className="muted" style={{ marginTop: 6 }}>
        Speak in French; you'll get a transcript and a spoken reply. Feedback is on
        content and fluency — not pronunciation.
      </p>

      <TopicPicker
        topics={topics}
        topic={topic}
        onPick={pickTopic}
        disabled={recording || busy}
      />

      {/* Resurface the last conversation's review words if it was left unreviewed.
          Keyed by the prior session so it resets when that changes. */}
      {priorSession && priorSession !== sessionId && (
        <SessionReview
          key={`prior-${priorSession}`}
          sessionId={priorSession}
          visible
          dismissible
          label="Review words from your last conversation"
          blurb="From your last conversation — add any to your review deck."
        />
      )}

      <div className="stack" style={{ marginTop: 8 }}>
        {turns.map((t, i) => (
          <div key={i} className="stack">
            <div className="card" style={{ background: "#eaf6ee" }}>
              <div className="muted" style={{ fontSize: 12 }}>You said</div>
              <div>{t.transcript}</div>
            </div>
            <div className="card">
              <div className="muted" style={{ fontSize: 12 }}>Examiner</div>
              <div>{t.reply_text}</div>
              {t.reply_audio_url && <PlayButton url={t.reply_audio_url} />}
            </div>
          </div>
        ))}
        {turns.length === 0 && (
          <div className="card center muted">
            {topic
              ? `Tap record and start responding to "${topic.title}" above.`
              : "Tap record and introduce yourself in French."}
          </div>
        )}
      </div>

      {/* Keyed by session so it fully resets when the topic (session) changes. */}
      <SessionReview
        key={sessionId}
        sessionId={sessionId}
        visible={sessionTurns > 0}
        label="✓ Finish & review words"
        blurb="From this conversation — add any to your review deck."
      />

      {available === false && (
        <div className="feedback no" style={{ marginTop: 14 }}>
          Speaking practice isn't enabled on this server yet (no speech models configured).
        </div>
      )}
      {error && <div className="feedback no" style={{ marginTop: 14 }}>{error}</div>}

      <div className="center" style={{ marginTop: 18 }}>
        {busy ? (
          <button className="btn" disabled>Transcribing…</button>
        ) : recording ? (
          <button className="btn" style={{ background: "var(--coral)", boxShadow: "0 4px 0 #b23c28" }} onClick={stop}>
            ◼ Stop &amp; send
          </button>
        ) : (
          <button className="btn" onClick={start} disabled={available === false}>🎙 Record</button>
        )}
      </div>
    </div>
  );
}

// Confirm-to-add vocab review over one speaking session's transcript. Used two
// ways: the end-of-conversation debrief for the *current* session ("Finish &
// review words"), and a resurface nudge for the learner's *last* conversation if
// they skipped it. Never auto-seeds — the review deck stays the learner's own.
function SessionReview({
  sessionId,
  visible,
  label,
  blurb,
  dismissible = false,
}: {
  sessionId: string;
  visible: boolean;
  label: string;
  blurb: string;
  dismissible?: boolean;
}) {
  const [phase, setPhase] = useState<"idle" | "loading" | "done">("idle");
  const [candidates, setCandidates] = useState<VocabCandidate[]>([]);
  const [overBudget, setOverBudget] = useState(false);
  const [added, setAdded] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [dismissed, setDismissed] = useState(false);

  if (!visible || dismissed) return null;

  const finish = async () => {
    setPhase("loading");
    setError("");
    try {
      const res = await api.speechVocabReview(sessionId);
      setCandidates(res.candidates);
      setOverBudget(!!res.over_budget);
      setPhase("done");
    } catch (e: any) {
      setError(e.message || "Couldn't fetch review words.");
      setPhase("idle");
    }
  };

  const add = async (key: string) => {
    setAdded((a) => ({ ...a, [key]: true })); // optimistic; idempotent server-side
    try {
      await api.addToReview(key);
    } catch {
      setAdded((a) => ({ ...a, [key]: false }));
    }
  };

  if (phase === "idle") {
    return (
      <div className="center" style={{ marginTop: 14 }}>
        <button className="btn secondary" onClick={finish}>
          {label}
        </button>
        {dismissible && (
          <button className="link-btn" style={{ marginLeft: 10 }} onClick={() => setDismissed(true)}>
            Not now
          </button>
        )}
        {error && <div className="feedback no" style={{ marginTop: 10 }}>{error}</div>}
      </div>
    );
  }

  if (phase === "loading") {
    return (
      <div className="card center muted" style={{ marginTop: 14 }}>
        Picking out words to review…
      </div>
    );
  }

  if (overBudget) {
    return (
      <div className="card center muted" style={{ marginTop: 14 }}>
        You've reached today's speaking-practice limit. Come back tomorrow to review these words.
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="card center muted" style={{ marginTop: 14 }}>
        No new words to review — nice work!
      </div>
    );
  }

  const allAdded = candidates.every((c) => added[c.card_key]);
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div style={{ fontWeight: 700 }}>Words to review</div>
      <div className="muted" style={{ fontSize: 13, margin: "2px 0 10px" }}>
        {blurb}
      </div>
      <div className="btn-row" style={{ flexWrap: "wrap", gap: 8 }}>
        {candidates.map((c) => (
          <button
            key={c.card_key}
            className={`btn ${added[c.card_key] ? "" : "secondary"}`}
            onClick={() => add(c.card_key)}
            disabled={added[c.card_key]}
            title={`${c.en} · ${c.level.toUpperCase()}`}
          >
            {added[c.card_key] ? "✓ " : "+ "}
            {c.fr}
          </button>
        ))}
      </div>
      {!allAdded && (
        <button
          className="link-btn"
          style={{ marginTop: 10 }}
          onClick={() => candidates.forEach((c) => !added[c.card_key] && add(c.card_key))}
        >
          Add all
        </button>
      )}
    </div>
  );
}

// Lets the learner pick an authored TEF topic to develop. Nothing picked = free
// conversation. When one is picked, its task card stays visible while they speak.
function TopicPicker({
  topics,
  topic,
  onPick,
  disabled,
}: {
  topics: SpeakingTopic[];
  topic: SpeakingTopic | null;
  onPick: (t: SpeakingTopic | null) => void;
  disabled: boolean;
}) {
  if (topics.length === 0) return null;

  if (topic) {
    return (
      <div className="card" style={{ marginTop: 12, borderLeft: "4px solid var(--accent, #2e7d5b)" }}>
        <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
          <div className="muted" style={{ fontSize: 12 }}>
            Topic · Section {topic.section}
          </div>
          <button className="link-btn" onClick={() => onPick(null)} disabled={disabled}>
            Change topic
          </button>
        </div>
        <div style={{ fontWeight: 700, marginTop: 2 }}>{topic.title}</div>
        <div style={{ whiteSpace: "pre-line", marginTop: 4 }}>{topic.prompt}</div>
        {topic.points.length > 0 && (
          <ul className="muted" style={{ fontSize: 13, marginTop: 8, paddingLeft: 18 }}>
            {topic.points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
        Pick a topic to develop, or just start talking for a free conversation.
      </div>
      <div className="btn-row" style={{ flexWrap: "wrap", gap: 8 }}>
        {topics.map((t) => (
          <button
            key={t.id}
            className="btn secondary"
            style={{ textAlign: "left" }}
            onClick={() => onPick(t)}
            disabled={disabled}
            title={t.prompt}
          >
            <span className="muted" style={{ fontSize: 11 }}>Section {t.section}</span>
            <br />
            {t.title}
          </button>
        ))}
      </div>
    </div>
  );
}

function PlayButton({ url }: { url: string }) {
  const [loading, setLoading] = useState(false);
  const { slowRate } = useSlowRate();
  const play = async (rate: number) => {
    setLoading(true);
    try {
      const objUrl = await fetchAudioUrl(url);
      const audio = new Audio(objUrl);
      // Time-stretch instead of pitch-shifting so the slow replay stays natural.
      audio.preservesPitch = true;
      audio.playbackRate = rate;
      await audio.play();
    } catch {
      /* ignore playback errors */
    } finally {
      setLoading(false);
    }
  };
  return (
    <>
      <button
        className="btn secondary"
        style={{ marginTop: 10 }}
        onClick={() => play(1)}
        disabled={loading}
      >
        {loading ? "…" : "🔊 Play reply"}
      </button>
      <button
        className="btn secondary"
        style={{ marginTop: 10 }}
        onClick={() => play(slowRate)}
        disabled={loading}
        aria-label="Play reply slowly"
        title="Play reply slowly"
      >
        🐢
      </button>
    </>
  );
}
