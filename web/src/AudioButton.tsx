import { CSSProperties, useState } from "react";
import { fetchAudioUrl } from "./api";
import { useSlowRate } from "./speed";

// Plays an audio asset stored under a content storage key (e.g. "a1/audio/bonjour.mp3").
// Audio is auth-protected, so we fetch the bytes with the bearer token and play an
// object URL (same approach as the comprehension/speaking players).
//
// Pass `slow` to render an extra 🐢 button that replays the same clip slowed down —
// the pronunciation clips are baked at a fixed speed, so this gives learners an
// on-demand slow repeat without regenerating any audio.
export default function AudioButton({
  audioKey,
  label = "🔊 Play",
  slow = false,
  className = "btn secondary",
  style,
}: {
  audioKey: string;
  label?: string;
  slow?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  const [loading, setLoading] = useState(false);
  const { slowRate } = useSlowRate();
  const play = async (rate: number) => {
    setLoading(true);
    try {
      const objUrl = await fetchAudioUrl(`/content/audio/${audioKey}`);
      const audio = new Audio(objUrl);
      // Time-stretch instead of pitch-shifting so the slow replay stays natural.
      audio.preservesPitch = true;
      audio.playbackRate = rate;
      await audio.play();
    } catch {
      /* ignore playback errors — the clip just won't play */
    } finally {
      setLoading(false);
    }
  };
  return (
    <>
      <button
        type="button"
        className={className}
        style={style}
        onClick={() => play(1)}
        disabled={loading}
      >
        {loading ? "…" : label}
      </button>
      {slow && (
        <button
          type="button"
          className={className}
          style={style}
          onClick={() => play(slowRate)}
          disabled={loading}
          aria-label="Play slowly"
          title="Play slowly"
        >
          🐢
        </button>
      )}
    </>
  );
}
