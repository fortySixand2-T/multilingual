---
id: 340
title: "All 80 new A2 audio files return 404 -- not synced to data/assets"
status: done
severity: high
area: content
persona: edge-case-breaker
found: 2026-06-24
---

## Steps to reproduce
1. Sign up a user via `POST /auth/signup` with invite code `friend-001`.
2. Request any new A2 vocab audio file via the API:
   ```
   GET /content/audio/a2/audio/couper.mp3
   Authorization: Bearer <token>
   ```
3. Also try: `fievre.mp3`, `inquiet.mp3`, `frontiere.mp3`, `bouillir.mp3`, etc.

## Expected
200 with `audio/mpeg` content-type and the MP3 data, since the files exist in `content/a2/audio/` and the vocab cards reference them.

## Actual
404 `{"detail":"audio asset not found"}` for all 80 new A2 audio files.

The files exist in `content/a2/audio/` but were never copied to `data/assets/a2/audio/` where `LocalFileStorage` serves them from. Running `./start.sh content-sync a2` would fix it, but it was apparently not run for the A2 level after the PR landed.

A1 audio is fully synced (0 missing), so A1 new audio works fine.

## Evidence
```
$ curl -s -o /dev/null -w "%{http_code}|%{content_type}" \
    http://127.0.0.1:9000/content/audio/a2/audio/couper.mp3 \
    -H "Authorization: Bearer $TOKEN"
404|application/json

$ comm -23 <(ls content/a2/audio/ | sort) <(ls data/assets/a2/audio/ | sort) | wc -l
80
```

All 80 new A2 cards are affected. The `GET /content/vocab?level=a2` endpoint returns `audio: "a2/audio/couper.mp3"` keys that resolve to 404.

## Notes
The content-sync script defaults to `a1` (`./start.sh content-sync` without a level argument). The deployment apparently ran sync for A1 but not A2. This is a deployment/sync gap rather than a code bug, but it means every new A2 vocab card's pronunciation playback is broken for users.

## Triage (self, round 021 cut short by session limit)
- **Root cause:** `app/content/sync.py` writes DB rows only — it does **not** upload audio. *All* level audio (vocab, listen_type, comprehension) is uploaded to object storage by `app/comprehension/sync.py::upload_audio`, which uploads every file under `content/<level>/audio/`. The 404s occurred because `comprehension-sync` was never run in the dev box after `gen_audio`. Running `python -m app.comprehension.sync a1 && … a2` uploaded all clips → `comm` diff went 80 → **0**; the previously-404 clips now serve (verified file presence in `data/assets/<level>/audio/`).
- **Pre-existing, not introduced by this PR:** vocab-audio upload has always ridden on `comprehension-sync`; PR #13 only added more clips that need the same step. The full sync flow runs it — the e2e harness `global-setup` runs `app.comprehension.sync` (so E2E audio serves), and a deploy runs every `*-sync` per level.
- **Content is correct:** the committed MP3s are valid and the `audio` keys resolve once the standard audio sync runs.
- **Verdict: deferred (not a PR #13 blocker).** Tracked as a follow-up code change: make `content-sync` upload its level's audio too (reuse `upload_audio`), so the natural command for vocab content is self-sufficient and this footgun can't recur. Severity downgraded from the tester's "high" — no production exposure given the standard sync flow.
- **Dev box remediated:** ran `comprehension-sync a1/a2`; audio now serves.

## Fix
`app/content/sync.py::_main` now uploads the level's audio via `upload_audio` + `build_storage` after the DB sync, so `content-sync <level>` is self-sufficient (no longer depends on `comprehension-sync` to publish vocab pronunciation). Verified: `content-sync a1` into a clean assets dir → "238 audio files" uploaded.

## Critic
- final_status: validated
- agree_with_pm: yes
- rationale: The PM's downgrade from "high" to "deferred/not-a-blocker" was correct at triage time given the standard sync flow covers it, but the underlying footgun — that `content-sync` silently omits audio and requires a separate `comprehension-sync` to actually serve vocab pronunciation — is a real structural defect, not mere documentation debt. Any developer or deployer running only `content-sync` after adding vocab YAML would ship silently broken audio for every new card. The fix (making `content-sync` self-sufficient) closes the footgun permanently and is the right scope. The fix has since been applied, confirming validated status. Status frontmatter already shows done.
- severity_check: too_low
