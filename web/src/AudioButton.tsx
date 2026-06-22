import { CSSProperties, useState } from "react";
import { fetchAudioUrl } from "./api";

// Plays an audio asset stored under a content storage key (e.g. "a1/audio/bonjour.mp3").
// Audio is auth-protected, so we fetch the bytes with the bearer token and play an
// object URL (same approach as the comprehension/speaking players).
export default function AudioButton({
  audioKey,
  label = "🔊 Play",
  className = "btn secondary",
  style,
}: {
  audioKey: string;
  label?: string;
  className?: string;
  style?: CSSProperties;
}) {
  const [loading, setLoading] = useState(false);
  const play = async () => {
    setLoading(true);
    try {
      const objUrl = await fetchAudioUrl(`/content/audio/${audioKey}`);
      await new Audio(objUrl).play();
    } catch {
      /* ignore playback errors — the clip just won't play */
    } finally {
      setLoading(false);
    }
  };
  return (
    <button type="button" className={className} style={style} onClick={play} disabled={loading}>
      {loading ? "…" : label}
    </button>
  );
}
