# Speech test fixtures (QA round 041)

Audio inputs for exercising the speaking loop directly over HTTP, without a
microphone. The `qa-tester` HTTP charter POSTs these to `/speech/turn`; the
`qa-browser-tester` uses a real mic instead (that's the point of H1 — see
`qa/rounds/041-plan.md`).

## Why both a `.wav` and a `.webm`
`Speaking.tsx` records with `MediaRecorder`, which on Chrome emits **`audio/webm`
(Opus)**. faster-whisper decodes via ffmpeg/libav — if that path isn't present,
a clean `.wav` transcribes fine while the real browser blob fails. Testing only
a `.wav` is a false green. Always test the pair and compare (H1).

## How the fixtures are used
```
curl -sS -X POST http://localhost:9000/speech/turn \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@qa/fixtures/speech/hello-fr.wav;type=audio/wav" \
  -F "mode=examiner"
```
The endpoint takes multipart `audio` (required) + `mode` form field
(`examiner` | `conversation`). Transcription language is hard-coded to `fr`
(`app/speech/examiner.py`), so spoken content should be French except where a
fixture deliberately isn't (see `english-*`, for H9).

## What's here now
Generated locally with macOS `say` (via the same path as `scripts/gen_audio.py`)
— our own synthetic audio, no downloads, no licensing. All wavs are 16 kHz mono
PCM16 (what Whisper prefers), 3–5 s.

| filename | content | probes |
|---|---|---|
| `hello-fr.wav` | clean Québécois French (voice Amélie): *"Bonjour, je m'appelle Claire et j'habite à Montréal…"* | baseline happy path |
| `hello-fr-france.wav` | clean France French (voice Jacques): a restaurant reservation | baseline + fr_FR vs fr_CA accent |
| `broken-fr.wav` | grammatically broken beginner French (*"moi je aller au magasin… je acheter du pain"*) | H6 — does the transcript preserve the errors, or does Whisper "fix" them? |
| `accent-question-fr.wav` | *"Comment était ma prononciation et mon accent ?"* | H7 — examiner must not fabricate accent/phoneme scores |
| `passage-fr-baseline.mp3` | 20 s multi-sentence listening passage (copied from `content/b1/audio/`, our own TTS) | multi-sentence baseline; mp3-decode path |
| `silence.wav` | 3 s of silence | H9 — empty transcript must not bill a blank LLM turn |
| `empty.bin` | 0 bytes | H9 — reject cleanly (4xx), not 500 |
| `not-audio.bin` | 4 KB random bytes | H9 — reject cleanly |

Regenerate the synthetic ones with the script in the session scratchpad
(`make_fixtures.py`) or by hand — see "Generating them" below.

### Still needed (can't be synthesized)
- **`hello-fr.webm`** — the **same utterance as `hello-fr.wav`, captured from Chrome
  `MediaRecorder`** (webm/Opus). This is the whole point of **H1**; a transcoded
  wav→webm won't do — record it through the app's Speaking screen and save the blob.
- **A real human "broken French" clip** for the *pronunciation* half of H6. `say`
  pronounces `broken-fr.wav` fluently, so that fixture only tests broken **grammar**,
  not mispronunciation — Whisper's "auto-correct" of a real learner's accent needs a
  human recording.
- **`english-speech.wav`** (English audio, for the wrong-language H9 case) — grab any
  short English clip you already have, or record one.

## Generating them
- **`.wav`** (from any recording, normalized to what Whisper likes — 16 kHz mono PCM):
  `ffmpeg -i in.m4a -ar 16000 -ac 1 -c:a pcm_s16le hello-fr.wav`
- **`.webm`** — capture the *same* utterance in Chrome so it's a genuine
  `MediaRecorder` blob (don't transcode a wav → webm; that hides the real codec
  quirks). Easiest: record it through the app's own Speaking screen and save the
  uploaded blob, or use a tiny `MediaRecorder` snippet and download the Blob.
- **`silence.wav`**: `ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 3 silence.wav`
- **`empty.bin`**: `: > empty.bin` · **`not-audio.bin`**: `head -c 4096 /dev/urandom > not-audio.bin`

## Notes
- These are **inputs only.** Reply audio comes back as `audio/wav` from Piper and
  is fetched from `/speech/audio/{turn_id}` — don't commit generated replies here.
- Real human voice recordings of an identifiable person are personal data (R10);
  prefer your own voice or synthetic/neutral clips, and keep them short. Don't
  commit anything you wouldn't want in the repo's history.
