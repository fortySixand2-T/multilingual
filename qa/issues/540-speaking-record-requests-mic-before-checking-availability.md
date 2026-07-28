---
id: 540
title: Speaking screen requests mic permission before checking if speech backend is available
severity: medium
area: speech
persona: absolute-beginner
status: validated
found: 2026-07-27
---

## Steps to reproduce
1. Sign up as a brand-new user (invite code `friend-001`), land at A1 on the Path
   screen.
2. Click the "Speak" hub card to open `/speaking`. Backend has STT/TTS disabled
   locally (`app.state.stt`/`.tts` are `None`), so `/speech/turn` is known to
   return a clean 503 for this deployment.
3. Observe the initial `/speaking` screen: title "Speaking", instructions, a
   card reading "Tap record and introduce yourself in French.", and a green
   "🎙 Record" button — no indication anywhere that speech isn't available in
   this environment.
4. Click "Record".
5. Confirmed via source read (`web/src/screens/Speaking.tsx` `start()`,
   line 46) and by invoking the same call directly in the page
   (`navigator.mediaDevices.getUserMedia({audio:true})`) that clicking Record
   unconditionally calls `getUserMedia` — no prior check against the backend's
   known-unavailable state. In a real browser this triggers the native
   mic-permission prompt immediately.

## Expected
Since the backend already knows (via `STT_BACKEND`/`app.state.stt`) that
speech isn't configured, the UI should not make the user go through a native
mic-permission prompt, record themselves, wait through "Transcribing…", and
only then discover (via the caught 503 in `upload()`) that "Speaking practice
isn't enabled on this server yet." At minimum, the initial screen should
surface the unavailable state upfront (e.g. a capability check on mount,
mirroring the `speechHistory()` call already made there) so a first-time
learner isn't prompted for microphone access for a feature that cannot
possibly work.

## Actual
The Record button is fully interactive from the first render with no
preflight capability check. Clicking it immediately calls
`navigator.mediaDevices.getUserMedia({audio:true})`, which in a live browser
raises the OS/browser microphone permission dialog — a real, consequential
prompt — before the app has any evidence the backend can process the
resulting audio. Only after granting permission, recording, stopping, and
waiting through the "Transcribing…" busy state does the app finally show the
(otherwise well-written) error "Speaking practice isn't enabled on this
server yet (no speech models configured)." For an absolute-beginner persona
in particular, being asked to "introduce yourself in French" (a language they
don't speak yet) and grant mic access, only to be told afterward the feature
doesn't work, is confusing and wastes their effort.

No console errors were observed and the eventual 503 message text itself is
clear — this is purely about the missing preflight/misleading control, not a
crash or blank screen.

## Notes
`web/src/screens/Speaking.tsx`: `useEffect` on mount only calls
`api.speechHistory()`; there's no equivalent "is speech configured" probe.
The `upload()` function already has clean 503 handling
(`e.status === 503 ? "Speaking practice isn't enabled on this server yet..."`)
— reusing that same signal proactively (e.g. a lightweight `GET` that 200s
even with an empty turn list vs. a dedicated capability flag) before enabling
the Record button would fix this without needing a new endpoint if the
history call's 200 response already implies STT is at least reachable
end-to-end; otherwise a small `/speech/status` style check would suffice.

## Triage
- Explanation: Confirmed by reading `web/src/screens/Speaking.tsx` `start()`
  (line 46) — it unconditionally calls
  `navigator.mediaDevices.getUserMedia({audio:true})` with no preflight
  check of any kind, and the mount `useEffect` (line 16) only calls
  `api.speechHistory()`, storing/displaying past turns. On the backend,
  `app/speech/api.py::speech_turn` (line 78-81) is the only place that reads
  `request.app.state.stt`/`.tts` and returns 503 — `app.state.stt`/`.tts`
  are set once at startup from config (`app/main.py:74-75`,
  `build_stt(settings)`/`build_tts(settings)`) and never re-checked
  elsewhere. Critically, `GET /speech/history` (api.py line 168) does **not**
  check `app.state.stt` at all — it just queries the `SpeechTurn` table for
  the user and returns 200 with an empty list regardless of whether STT/TTS
  are configured, so the issue's own suggested mitigation ("reusing the
  history call's 200 as an implied signal") would not actually work; a real
  fix needs a dedicated capability signal (e.g. a small `/speech/status`
  check, or having `speechHistory()` surface `app.state.stt is None` some
  other way) — that's a note for the dev-fixer, not a reason to reject.
  There is no existing config/features/capabilities endpoint anywhere in
  `app/` that the frontend is failing to call; this genuinely doesn't exist
  yet. So the reported sequence is accurate: Record → native mic-permission
  prompt → record → "Transcribing…" → only then a 503 caught in `upload()`
  (line 33-37), with zero prior signal to the learner.
- Against spec: `qa/README.md`'s scope note explicitly carves this in:
  "Drill, Writing grading, and Speaking need an LLM/STT/TTS provider
  configured. With none set, a clean 503 there is expected — testers only
  file it if the *handling* is poor, not for the missing provider itself."
  This issue is precisely about the handling (an unconditional, consequential
  native permission prompt and a full record/transcribe round-trip before
  the already-clean 503 surfaces), not about the missing provider — squarely
  in scope per this carve-out. The technical plan's Phase 4 AC only commits
  to "transcript shown (R1); content-only feedback... voice data discarded
  post-transcription (R10)" for the *configured* case; it's silent on
  preflight UX for the *unconfigured* case, so there's no explicit spec
  requirement being violated — this is a persona-realism judgment call under
  the README's own stated bar, not a spec breach.
- Verdict: validated
- Rationale: For the `absolute-beginner` persona in particular, being asked
  to "introduce yourself in French" (a language they don't speak yet),
  granting a real OS-level mic permission, going through a record → stop →
  "Transcribing…" wait, only to be told afterward the feature isn't
  available at all, is a real, avoidable cost — not a hypothetical one; a
  brand-new user has no way to know in advance that this environment has
  speech disabled. This is exactly the "handling is poor" case the QA
  scope note anticipates as in-scope, distinct from Drill/Writing's simpler
  immediate-503-on-submit pattern (no consequential OS permission dialog or
  multi-step effort sunk before the failure surfaces). Medium severity is
  appropriate: it doesn't block any workflow, but it wastes a real user
  action (mic grant) and is misleading for exactly the persona least
  equipped to shrug it off.

## Critic
- Challenge: The strongest case for "no change needed" is that this whole
  scenario is an artifact of the *local, unconfigured* deployment, not
  something a real learner ever hits. The round plan itself confirms the
  self-host box that actually serves real users has `STT_BACKEND=faster-whisper`
  / `TTS_BACKEND=piper` configured — on that deployment, clicking Record and
  granting mic access is normal, necessary, and works. The mic-permission
  prompt itself is unavoidable UX for *any* recording feature (Zoom, Google
  Meet, voice-memo apps all request permission at point of use, not after a
  server-health preflight) — asking for permission before verifying
  business logic will succeed is the standard pattern across the web, not
  "poor handling" by any unusual definition. Structurally this is the same
  shape as the round's own "Don't re-file" carve-out for Drill/Writing: "503
  with no LLM provider — expected local limitation, not in scope." Speaking's
  variant is only "worse" because recording requires an OS permission
  dialog as an inherent step, not because the app's *handling* of the
  disabled state is uniquely bad — the existing `upload()` catch already
  produces the same clear, well-written 503 message Drill/Writing use. A
  genuine fix also isn't free: the PM's own triage confirms `/speech/history`
  returning 200 does **not** imply STT is configured, so a real fix needs a
  brand-new `/speech/status`-style endpoint plus a new frontend preflight
  call — real surface area added to work around a scenario (unconfigured
  local backend) the README explicitly says not to chase.
- Holds up? Partially, but doesn't fully overturn. Two things keep this on
  the "validated" side of the line rather than "reject as scope creep":
  (1) the round's own H8 charter (`qa/rounds/043-plan.md`) explicitly
  planned to check "mic-permission UI doesn't appear misleadingly if the
  backend already reports unavailable" — this isn't the PM stretching the
  README's carve-out after the fact, the planner pre-authorized exactly
  this check as its own hypothesis before any tester ran; (2) the cost
  asymmetry with Drill/Writing is real, not cosmetic — Drill/Writing fail at
  submit-time with zero preceding user commitment, while here the user
  grants a real OS-level, trust-carrying permission and sits through a
  record + "Transcribing…" round trip before learning it was pointless.
  That is a materially worse "handling" experience for the identical
  underlying "not configured" condition, which is the exact distinction the
  README's carve-out language ("handling," not "the missing provider
  itself") is drawing. Verified `Speaking.tsx` myself: `start()` (the
  Record handler) unconditionally calls `getUserMedia` with no preflight of
  any kind, and the mount effect only calls `speechHistory()` — matches the
  PM's read exactly, no discrepancy to relitigate. I'd flag one thing for
  the dev-fixer to keep this proportionate: the fix should be the smallest
  possible signal (e.g. a single boolean on an existing/cheap call, not a
  new subsystem) — anything heavier would tip into "fix worse than the bug"
  territory for what remains, at bottom, a local/dev-only rough edge.
- Final verdict: validated
