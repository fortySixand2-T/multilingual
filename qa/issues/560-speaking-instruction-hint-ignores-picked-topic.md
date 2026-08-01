---
id: 560
title: Speaking instruction hint stays generic ("introduce yourself") even after picking a topic
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-08-01
---

## Steps to reproduce
1. Sign up / log in, go to Learn, tap the "Speak" tile (or navigate to `/speaking`).
2. On the topic picker, tap one of the two topic cards, e.g. "Réserver une table"
   (A1, "book a table at a restaurant").
3. Look at the card below the task card, right above the Record button.

## Expected
Once a specific topic is picked, the hint/instruction text should relate to that
topic (e.g. something like "Tap record and start the conversation about the topic
above") — or at least not contradict the topic just chosen.

## Actual
The hint card still reads the generic, topic-agnostic copy: "Tap record and
introduce yourself in French." This text never changes regardless of which topic
is selected — verified with topics at A1, A2, and B2. For a beginner who just read
a task card that says "Vous voulez réserver une table au restaurant. Posez des
questions..." (about booking a table), being told to "introduce yourself" directly
underneath is confusing/contradictory about what they're actually supposed to do
once they tap Record.

Source: `web/src/screens/Speaking.tsx` line ~128 —
`{turns.length === 0 && <div className="card center muted">Tap record and introduce yourself in French.</div>}`
is a static string with no dependency on the picked topic.

## Notes
Low-risk/low-effort fix: swap the hint text based on whether a topic is picked,
e.g. "Tap record and start responding to the topic above" vs the current
free-conversation copy. Not blocking (Record is disabled anyway while STT is off
in this env), but will read as an actual bug once STT is enabled.

## Triage
- Explanation: Confirmed by reading `web/src/screens/Speaking.tsx` directly.
  Line 128: `{turns.length === 0 && <div className="card center muted">Tap
  record and introduce yourself in French.</div>}` is a bare static string
  gated only on `turns.length === 0` — it has no dependency on `topic` (the
  picked `SpeakingTopic | null` state, set by `TopicPicker`'s `onPick`). Also
  reproduced in the browser: with a topic picked, the `TopicPicker` renders
  correctly with the topic's title/prompt/points (lines 168-190), but the
  card directly below still shows the generic "introduce yourself" copy
  regardless of which topic (or none) is selected — matches the tester's
  report exactly at A1/A2/B2.
- Against spec: unspecified verbatim, but Phase 4's stated shape is "speaking
  practice = record → transcribe → examiner role-play" framed by the picked
  topic (`app/speech/topics.py`'s `framing()` already conditions the
  examiner's system prompt on the topic when one is picked) — the UI hint is
  the one place left that doesn't follow that same "topic changes the
  framing" principle its own sibling code already implements server-side.
- Verdict: validated
- Rationale: Small but real — a beginner who just read a French task card
  about reserving a restaurant table, then is told directly underneath to
  "introduce yourself," gets a self-contradictory instruction about what
  they're about to do when they hit Record. Low-risk, low-effort, one
  conditional string swap keyed off `topic` (already in scope in that
  component). Not currently blocking since Record is disabled with STT off
  in this env, but it's a real bug in the topic-aware framing this PR just
  added — it will read as broken the moment STT is enabled.

## Critic
- Challenge: is this even a live defect right now, or purely theoretical? Record is
  disabled in this environment ("Speaking practice isn't enabled on this server yet -
  no speech models configured"), so no learner can currently reach a state where they
  read the contradictory hint and then act on it by recording. Is fixing UI copy for a
  path that's presently unreachable worth carrying as validated rather than a backlog
  note to revisit when STT ships?
- Holds up? Yes. Drove it myself in Chrome at /speaking: picked "Louer un appartement"
  (Section A, A2) and the topic card correctly updates with title/prompt/points, but the
  card directly below it still reads "Tap record and introduce yourself in French" -
  confirmed on screen, not just in the diff. The "it's disabled so it doesn't matter"
  framing doesn't hold: this PR's own stated purpose is topic bank + faster STT wiring,
  i.e. to make Record live very soon - shipping copy that's already known to contradict
  itself the moment the gate lifts is exactly the kind of defect worth catching now,
  while it's cheap (one conditional string keyed off topic, already in scope, no added
  complexity). Real near-term user confusion, topic-conditioned framing is literally
  what this PR is about, and the fix is trivially simple - validating is correct.
- Final verdict: validated

Fix: the hint under Record is now topic-aware — `Tap record and start
responding to "{topic.title}" above.` when a topic is picked, keeping the
original "Tap record and introduce yourself in French." only for the
free-conversation (no topic) case (`web/src/screens/Speaking.tsx`). Test:
`web/src/screens/Speaking.test.tsx` — "shows the generic hint with no topic
picked, and a topic-aware hint once picked".
