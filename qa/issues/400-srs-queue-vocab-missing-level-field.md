---
id: 400
title: SRS queue vocab entries missing level field
severity: medium
area: srs
persona: returning-learner
status: done
found: 2026-06-25
---

## Steps to reproduce
1. Sign up, complete lessons from both A1 and A2 (e.g. greetings-01 and routine-a2-01) to seed vocab cards into the SRS queue.
2. `GET /srs/queue?limit=10` with auth token.
3. Inspect the `vocab` object on each returned card.

## Expected
Each card's `vocab` object should include a `level` field (e.g. `"level": "a1"` or `"level": "a2"`), consistent with `GET /content/vocab` which does include it.

## Actual
The `level` field is absent from all vocab objects in the SRS queue response. Cards from both A1 and A2 appear, but the only way to infer the level is to parse the `audio` path (e.g. `a1/audio/bonjour.mp3` vs `a2/audio/se_lever.mp3`), which is fragile and not a proper API contract.

## Evidence
```
GET /srs/queue?limit=10
  card=bonjour level=MISSING audio=a1/audio/bonjour.mp3
  card=se_lever level=MISSING audio=a2/audio/se_lever.mp3

GET /content/vocab?level=a1 (first card):
  {"id":"a_bientot","fr":"a bientot","level":"a1", ...}
```

## Notes
The root cause is in `app/srs/api.py` line 51: the vocab dict is built as `{**r.data, "audio": ...}` but does not add `"level": r.level`, unlike `app/content/api.py` which explicitly adds `"level": r.level` to each card. With both A1 and A2 content now active, users doing SRS reviews see a mix of levels but the UI cannot distinguish them. The fix is to add `"level": r.level` to the dict comprehension on line 51, mirroring what was done for the audio key (issue 350).

## Triage
- Explanation: In `app/srs/api.py` line 51, the vocab dict is built as `{**r.data, "audio": r.data.get("audio") or f"{r.level}/audio/{r.id}.mp3"}`. The `level` column is a separate DB column on ContentVocab (not part of `r.data` JSON blob), so it must be explicitly added to the output dict. The `/content/vocab` endpoint does this correctly on line 186 of content/api.py with `{**r.data, "level": r.level}`, but the SRS queue endpoint was never updated to include it. This became visible once A2 content was added alongside A1, creating mixed-level review queues.
- Against spec: yes -- the spec (AC1.2) ties SRS to vocab review; with multi-level content active, the queue response should identify which level each card belongs to so the UI can display it consistently with the vocab browser.
- Verdict: validated
- Rationale: Real gap with user impact. A returning learner reviewing mixed A1/A2 cards has no reliable way to identify which level a card belongs to. The fix is a one-line addition of `"level": r.level` to the dict comprehension in srs/api.py, mirroring content/api.py.

## Critic
- Challenge: Is the level field actually needed in the SRS queue response? The SRS review screen shows a vocab card for the user to practice -- does it need to know the level? Verified: srs/api.py line 51 builds `{**r.data, "audio": ...}` but `r.level` is a separate DB column (content/tables.py line 23), not part of the `r.data` JSON blob, so it is genuinely missing from the output. Meanwhile content/api.py line 186 does `{**r.data, "level": r.level}` -- the inconsistency is clear. With A1 and A2 content both active, the frontend has no way to determine the level of a review card except by parsing the audio path, which is fragile. The fix is a single key addition to a dict comprehension -- zero complexity cost.
- Holds up? Yes -- real data omission, one-line fix, consistent with how content/api.py already handles it.
- Final verdict: validated

## Fix
Added `"level": r.level` to the vocab dict comprehension in `app/srs/api.py` line 51, mirroring how `app/content/api.py` already includes the level field. The SRS queue response now includes the `level` key on every vocab object.
