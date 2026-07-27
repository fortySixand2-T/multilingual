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
| `hello-fr.webm` | **same utterance as `hello-fr.wav`**, captured through the Speaking screen (Chrome `MediaRecorder`, webm/Opus) | **H1** — real browser blob decodes (PyAV/opus, no system ffmpeg) + transcribes |
| `hello-fr-france.wav` | clean France French (voice Jacques): a restaurant reservation | baseline + fr_FR vs fr_CA accent |
| `broken-fr.wav` | grammatically broken beginner French (*"moi je aller au magasin… je acheter du pain"*) | H6 — does the transcript preserve the errors, or does Whisper "fix" them? |
| `accent-question-fr.wav` | *"Comment était ma prononciation et mon accent ?"* | H7 — examiner must not fabricate accent/phoneme scores |
| `passage-fr-baseline.mp3` | 20 s multi-sentence listening passage (copied from `content/b1/audio/`, our own TTS) | multi-sentence baseline; mp3-decode path |
| `silence.wav` | 3 s of silence | H9 — empty transcript must not bill a blank LLM turn |
| `empty.bin` | 0 bytes | H9 — reject cleanly (4xx), not 500 |
| `not-audio.bin` | 4 KB random bytes | H9 — reject cleanly |

Regenerate the synthetic ones with the script in the session scratchpad
(`make_fixtures.py`) or by hand — see "Generating them" below.

## Graded utterances (llama3.1 + Piper)
Real French audio generated end-to-end on the self-host box: the running
**llama3.1** wrote one candidate-style sentence per CEFR level, then the deployed
**Piper** voice (`fr_FR-siwis-medium`) synthesized each; resampled to 16 kHz mono
PCM16 (`afconvert … -d LEI16@16000 -c 1 -f WAVE`). France French — Piper has no
fr_CA voice. Our own synthetic audio, no licensing.

| filename | level | source sentence (Piper input) | probes |
|---|---|---|---|
| `graded-a1-fr.wav` | A1 | *"Je m'appelle Pierre et je suis venu ici pour apprendre l'anglais."* | simple STT baseline |
| `graded-a2-fr.wav` | A2 | *"Je suis étudiant et j'ai besoin d'un logement à Paris."* | short everyday sentence |
| `graded-b1-fr.wav` | B1 | *"J'ai passé mon bac en France, mais maintenant je cherche un emploi en Angleterre."* | longer; proper nouns |
| `graded-b2-fr.wav` | B2 | *"Bien que j'aie des connaissances solides en marketing, je suis intéressé par les nuances de la communication interculturelle dans le cadre professionnel."* | dense subjunctive — stresses the STT model |

Observed with `WHISPER_MODEL=small` (CPU int8 — the deployed config): A1/A2
transcribe verbatim; B1 slips a proper noun (*Angleterre → "embleterre"*); B2's
dense opening clause garbles (*"j'aie des connaissances solides" → "je déconnece ce
lit"*) — an honest marker of the small model's ceiling on complex French. Bump
`WHISPER_MODEL` to `medium` if those need to land cleanly.

### Done: `hello-fr.webm` (H1)
Captured through the real Speaking screen in headless Chromium (Playwright): the
screen's own `getUserMedia → MediaRecorder → postSpeechTurn` path runs, with the
"mic" fed `hello-fr.wav` decoded through Web Audio into a `MediaStream` (deterministic,
unlike Chrome's flaky `--use-file-for-fake-audio-capture`). The blob is grabbed at the
upload boundary — a genuine `audio/webm;codecs=opus` MediaRecorder blob, not a
transcoded wav. Verified: the deployed whisper decodes and transcribes it to the same
sentence as `hello-fr.wav`. (`tests/test_speech_integration.py::test_whisper_transcribes_browser_webm`.)

### Still needed (can't be synthesized)
- **A real human "broken French" clip** for the *pronunciation* half of H6. `say`
  pronounces `broken-fr.wav` fluently, so that fixture only tests broken **grammar**,
  not mispronunciation — Whisper's "auto-correct" of a real learner's accent needs a
  human recording.
- **`english-speech.wav`** (English audio, for the wrong-language H9 case) — sourced
  from Tatoeba (see below), or record one.

## Third-party clips (Tatoeba — CC-BY, attribution required)
Natural human-voice clips sourced from [Tatoeba](https://tatoeba.org). **Not CC0:**
Tatoeba sentence text is CC-BY 2.0 FR and the per-recording audio is contributor-
licensed (the API does not expose a per-clip license), so we treat these as **CC-BY
and attribute them.** Downloaded via `https://audio.tatoeba.org/sentences/{lang}/{id}.mp3`.

Do **not** re-license these as our own; keep this block with the files.

| target fixture | source (Tatoeba) | sentence | contributor | probes |
|---|---|---|---|---|
| `natural-fr-1.wav` | [fra/373429](https://audio.tatoeba.org/sentences/fra/373429.mp3) | *"Je voudrais réserver un vol pour Vancouver."* | see sentence page 373429 | natural-voice baseline (real human, not TTS) |
| `natural-fr-2.wav` | [fra/139756](https://audio.tatoeba.org/sentences/fra/139756.mp3) | *"Je voudrais un plan de la ville."* | see sentence page 139756 | natural-voice baseline #2 |
| `english-speech.wav` | [eng/9414249](https://audio.tatoeba.org/sentences/eng/9414249.mp3) | *"I would like to participate."* | see sentence page 9414249 | H9 — wrong language (STT lang is `fr`) |

> Attribution, verbatim for the commit / README: *"Audio clips `natural-fr-1`,
> `natural-fr-2`, `english-speech` are from Tatoeba (tatoeba.org), sentences
> 373429, 139756, 9414249, licensed CC-BY. Confirm each contributor's name on the
> sentence page and list here before publishing."*

Contributor names must be filled in from each sentence page (e.g.
`https://tatoeba.org/en/sentences/show/373429`) before this is considered complete —
CC-BY requires crediting the author, not just the source.

## Generating them
- **`.wav`** (from any recording, normalized to what Whisper likes — 16 kHz mono PCM):
  `ffmpeg -i in.m4a -ar 16000 -ac 1 -c:a pcm_s16le hello-fr.wav`
  — ffmpeg-free path (this box has no ffmpeg): `afconvert in.mp3 out.wav -d LEI16@16000 -c 1 -f WAVE`
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
