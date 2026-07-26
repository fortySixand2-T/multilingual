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

## Fixtures to add
Not committed yet — generate these before the round. Keep them **short (2–6 s)**
so turns are cheap.

| filename | content | probes |
|---|---|---|
| `hello-fr.wav` | clean, correct French, e.g. *"Bonjour, je m'appelle Claire et j'habite à Montréal."* | baseline happy path |
| `hello-fr.webm` | **same utterance**, recorded from Chrome `MediaRecorder` (webm/Opus) | H1 — format decode parity vs the `.wav` |
| `broken-fr.wav` | deliberately halting / mispronounced beginner French with real errors | H6 — does the transcript show the errors, or does Whisper "fix" them? |
| `accent-question-fr.wav` | asks in French *"Comment était ma prononciation ?"* | H7 — examiner must not fabricate accent/phoneme scores |
| `english-speech.wav` | English speech (wrong language for `lang="fr"`) | H9 — graceful handling, no 500/hang |
| `silence.wav` | 3 s of silence | H9 — empty transcript must not bill a blank LLM turn |
| `empty.bin` | 0 bytes | H9 — reject cleanly (4xx), not 500 |
| `not-audio.bin` | random bytes with an audio extension | H9 — reject cleanly |

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
