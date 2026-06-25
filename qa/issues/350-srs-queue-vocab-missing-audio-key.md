---
id: 350
title: SRS queue returns empty audio field for all vocab cards
severity: high
area: srs
persona: returning-learner
status: done
found: 2026-06-24
---

## Steps to reproduce
1. Sign up and complete lessons through cafe-03 (which seeds 8 new vocab cards into SRS).
2. `GET /srs/queue?limit=100` with auth token.
3. Inspect the `vocab.audio` field on any returned card.

## Expected
Each card's `vocab.audio` should contain the pronunciation audio path, e.g. `"a1/audio/chocolat_chaud.mp3"`, matching what `GET /content/vocab?level=a1` returns.

## Actual
Every card in the SRS queue has `"audio": ""` (empty string). The vocab API (`GET /content/vocab`) correctly shows `"audio": "a1/audio/chocolat_chaud.mp3"` because it patches in the audio key at lines 176-177 of `app/content/api.py`. But the SRS queue endpoint (`app/srs/api.py` line 46) returns `r.data` directly from the DB without the same patching, so audio is always empty.

## Evidence
```
$ curl -s "http://127.0.0.1:9000/srs/queue?limit=100" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
for c in d['due']:
    if c['card_key'] == 'chocolat_chaud':
        print('SRS audio:', repr(c['vocab']['audio']))
"
SRS audio: ''

$ curl -s 'http://127.0.0.1:9000/content/vocab?level=a1' -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
for c in d['cards']:
    if c['id'] == 'chocolat_chaud':
        print('Vocab API audio:', repr(c['audio']))
"
Vocab API audio: 'a1/audio/chocolat_chaud.mp3'
```

## Notes
This affects all vocab cards in the SRS review queue, not just the new +160 cards. The audio key is generated dynamically by the vocab endpoint (`app/content/api.py:176-177`) but the SRS queue endpoint (`app/srs/api.py:46`) serves the raw `ContentVocab.data` JSON without the same fallback logic. Users reviewing flashcards cannot play pronunciation audio, which is a core feature of vocabulary review.

The fix should either: (a) store the audio key in the vocab YAML so it persists in the DB, or (b) apply the same `<level>/audio/<id>.mp3` fallback in the SRS queue endpoint.

## Triage (self, round 021 cut short by session limit)
- **Verdict: validated — real bug, but pre-existing and out of scope for the content PR #13.** `GET /srs/queue` (`app/srs/api.py` get_queue) builds `vocab = {r.id: r.data for r in rows}` and returns `r.data` raw, so it lacks the `<level>/audio/<id>.mp3` fallback that `GET /content/vocab` applies (`app/content/api.py:176-177`). Result: the Review (SRS) screen's `AudioButton` never renders for cards without an explicit `audio:` field — i.e. almost all of them. This is independent of PR #13 (the +160 cards just make it more visible); it predates this PR and is a code bug, not a content defect.
- **Fix (option b, in a follow-up code PR):** in `get_queue`, build each card as `{**r.data, "audio": r.data.get("audio") or f"{r.level}/audio/{r.id}.mp3"}` (mirrors the vocab endpoint), with a regression test. Folding it here would add unreviewed code to a content PR; doing it as a focused follow-up keeps #13 clean.
- Bundled with the [[340-a2-audio-not-synced-to-assets]] follow-up (both are audio-pipeline code fixes surfaced by this round).

## Fix
`app/srs/api.py::get_queue` now applies the same `<level>/audio/<id>.mp3` fallback the vocab endpoint uses, so review cards carry an `audio` key and the Review screen can play pronunciation. Regression: `tests/test_content_sync.py::test_srs_queue_attaches_audio_key`.
