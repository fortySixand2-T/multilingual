---
id: 1131
title: Comprehension audio endpoint ignores Range requests (no Accept-Ranges, always 200 full body)
severity: low
area: comprehension
persona: edge-case-breaker
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Log in; `curl -s -D- -o /dev/null -H "authorization: Bearer $T" -H "Range: bytes=0-99" http://127.0.0.1:9304/comprehension/audio/listen-b2-telephones-a-l-ecole`
2. Same for listen-b1-un-voisin-courageux and listen-b1-message-de-la-directrice.

## Expected
`206 Partial Content` with `Content-Range`, and `Accept-Ranges: bytes` on the 200 response, so browsers (notably Safari/iOS, which require Range for media) can seek/replay and start playback.

## Actual
`200 OK`, whole body (e.g. 272217 bytes), headers only `content-length` and `content-type: audio/mpeg`; no `Accept-Ranges`. Applies to every listening set (app/comprehension/api.py get_audio returns a plain Response). Auth (401 without token), content-type and byte-identity with content/*/audio/*.mp3 are fine.

## Notes
Replay/seek in Safari-class browsers may fail or restart; untested in a real browser by this persona.


## Triage
- Explanation: By design: the SPA fetches the mp3 with the bearer token and plays a blob: URL (ComprehensionSet.tsx fetchAudioUrl -> <audio src={blobUrl}>).
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: The browser never issues Range requests to /comprehension/audio, so Accept-Ranges is irrelevant; seek/replay run from the in-memory blob. Reporter did not test in a real browser; the audio loaded and played in qa-browser-tester's run (see 1143). Reopen only if audio is ever served by direct <audio src> URL.

## Critic
- Challenge: Verified: web/src/api.ts fetchAudioUrl fetches with the bearer token and createObjectURL(blob); AudioButton and comprehension player use the blob, so browsers never issue Range requests to /comprehension/audio. Safari concern does not apply to blob URLs. Reporter did not test in a browser; the browser tester played and replayed fine (1143).
- Holds up? yes - dismissal survives; not a missed real defect
- Final verdict: rejected
- Note: Reopen only if audio is ever served via direct <audio src>.
