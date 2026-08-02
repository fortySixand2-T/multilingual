---
id: 602
title: "Stop & send" recording button renders literal text "&amp;" instead of "&"
severity: low
area: web
persona: returning-learner
status: rejected
found: 2026-08-02
---

## Steps to reproduce
1. Open `/speaking` and start a recording (button reads "🎙 Record").
2. While recording, the button switches to a stop state.
3. Inspect the button's JSX source: `web/src/screens/Speaking.tsx` line ~205:
   ```jsx
   <button ... onClick={stop}>
     ◼ Stop &amp; send
   </button>
   ```

## Expected
The button should display "◼ Stop & send" with a real ampersand character, matching
the pattern used correctly elsewhere on the same screen (e.g. `label="✓ Finish &
review words"` and the nudge's own label, which are JS string props and render
correctly).

## Actual
Because `&amp;` here sits directly in JSX text content (not inside a JS string
literal/prop), JSX does not decode HTML entities in text children — React renders
it as the literal 4-character sequence `&amp;`, so the button would visually read
"◼ Stop &amp; send" instead of "◼ Stop & send" whenever a recording is active.

## Notes
- Not directly part of the Slice 3b nudge diff under test, but found on the same
  screen while chasing H7 (label/blurb rendering regression) and worth flagging
  since it's the same class of bug (entity-escaping in JSX text vs. props) this
  round is specifically checking for.
- Could not get a full live screenshot of the "recording" state in this
  environment: `GET /speech/status` returns `{"available": false}` here, so the
  Record button is disabled and clicking it (even after forcibly removing the
  `disabled` attribute via devtools) does not transition into the recording UI —
  `getUserMedia`/mic access does not proceed to the `recording` state client-side.
  This finding is derived from direct source inspection of the exact JSX being
  shipped, not a live screenshot; flagging with lower confidence given that, but
  the JSX literal is unambiguous.
- Fix: wrap in a JS expression, e.g. `{"◼ Stop & send"}`, or move to a `label`
  prop like the other two buttons on this screen.

## Triage
- Explanation: this claim is factually incorrect about JSX semantics. Unlike
  JS string literals/props, JSX *text children* are parsed with HTML-entity
  decoding at compile time (a documented JSX quirk, distinct from how the
  `label`/`blurb` string props elsewhere on this screen work) — `&amp;`
  written directly in JSX text compiles to a literal `&` character, not the
  four-character sequence `&amp;`. Confirmed directly against what's actually
  shipped: `grep -o "Stop[^\"']*send" web/dist/assets/*.js` on the built SPA
  bundle for this exact commit returns `Stop & send` — a real ampersand, not
  an escaped entity. The button will render "◼ Stop & send" correctly.
- Against spec: unspecified/not applicable — this is a JS/JSX language
  semantics question, not a design or spec question, and the built output
  settles it directly.
- Verdict: rejected
- Rationale: not reproducible even in principle — the issue was filed from
  source-reading alone (correctly noted as lower-confidence in its own notes,
  since the recording UI state couldn't be reached live) and the underlying
  assumption (JSX text doesn't decode entities) is wrong. The compiled bundle
  confirms correct rendering; no fix needed.


## Resolution
Rejected. JSX *text children* decode HTML entities at compile time (unlike string props), so `◼ Stop &amp; send` compiles to a real `&`. Verified in the shipped bundle: `grep -o 'Stop [^"']* send' web/dist/assets/*.js` → `Stop & send`. No fix.
