import { useEffect, useRef, useState } from "react";
import { SpeechTurnResult, api, fetchAudioUrl, postSpeechTurn } from "../api";

type Turn = { transcript: string; reply_text: string; reply_audio_url: string | null };

export default function Speaking() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [mode, setMode] = useState<"examiner" | "conversation">("examiner");
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // null = still checking; avoids flashing the "unavailable" message before the
  // status check resolves.
  const [available, setAvailable] = useState<boolean | null>(null);
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

  const upload = async (blob: Blob) => {
    setBusy(true);
    setError("");
    try {
      const res: SpeechTurnResult = await postSpeechTurn(blob, mode);
      if (res.over_budget) {
        setError("You've reached today's speaking-practice limit. Try again tomorrow.");
        return;
      }
      setTurns((t) => [...t, { transcript: res.transcript, reply_text: res.reply_text ?? "", reply_audio_url: res.reply_audio_url ?? null }]);
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
        {turns.length === 0 && <div className="card center muted">Tap record and introduce yourself in French.</div>}
      </div>

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

function PlayButton({ url }: { url: string }) {
  const [loading, setLoading] = useState(false);
  const play = async () => {
    setLoading(true);
    try {
      const objUrl = await fetchAudioUrl(url);
      await new Audio(objUrl).play();
    } catch {
      /* ignore playback errors */
    } finally {
      setLoading(false);
    }
  };
  return (
    <button className="btn secondary" style={{ marginTop: 10 }} onClick={play} disabled={loading}>
      {loading ? "…" : "🔊 Play reply"}
    </button>
  );
}
