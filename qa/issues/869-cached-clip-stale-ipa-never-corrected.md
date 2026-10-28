---
id: 869
title: Rows with a cached clip but stale or empty IPA are never corrected (lookup, card, from-word)
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST $B/vocab/personal/preview {"word":"horrible"} -> ipa "oʁˈibl", audio_url set (clip stored).
2. In DB: UPDATE vocab_lookup SET ipa='hɒrəbəl' (simulates a pre-#121 row; audio_key + clip stay).
3. POST preview again; GET $B/vocab/personal/lookup-audio/horrible (200, 45216 B WAV); POST preview again.
4. Same with ipa='' (row looked up while TTS was down but clip exists).
5. Card: POST /vocab/personal {fr:horrible,...,ipa:"WRONG"}; GET /vocab/personal/audio/uv:horrible (200); GET /vocab/personal.
6. DELETE user_vocab, UPDATE vocab_lookup ipa='hɒrəbəl', POST /vocab/personal/from-word {"word":"horrible"}.

## Expected
Playing the clip (or the next preview) heals the IPA to Piper's phonemes (oʁˈibl); empty IPA gets filled; from-word never copies a non-Piper IPA.

## Actual
All stay stale forever: preview returns "hɒrəbəl" before and after playing the audio; ipa="" stays ""; card keeps "WRONG" after audio fetch; from-word creates a card with ipa "hɒrəbəl" (or ""). _serve_audio returns the cached clip before the IPA-overwrite line, so the #122 fix only covers the synthesis branch. No backfill exists, so every pre-#121 vocab_lookup row and every card copied from one keeps the wrong IPA. This is very likely the user's still-wrong pronunciation report.

## Notes
Fix idea: on cached-clip serve, if row.ipa empty/differs, re-derive IPA (cheap piper --debug, or store IPA at synthesis only) plus a one-off backfill script over vocab_lookup and user_vocab. Also derive IPA at read time in preview when ipa is empty.

## Triage
- Explanation: app/content/personal_api.py::_serve_audio returns the cached clip (if row.audio_key) before the IPA overwrite, and lookup.cached_lookup/lookup_payload serve row.ipa verbatim; no backfill exists. Code path read, matches reporter.
- Against spec: Rule from PO/#121: IPA must come only from Piper; nonsense IPA must never be shown.
- Verdict: validated
- Rationale: Primary fix for the user's complaint (cacahuetes -> pəˈnuːz). Fix scope: (a) idempotent backfill script over vocab_lookup and user_vocab re-deriving IPA via synthesize_ipa (NOT run on live DB); (b) read-time guard so empty/stale IPA on a clipped row is re-derived once (or on next play) rather than shown; (c) from-word copies the lookup row IPA only after it is Piper-derived. Apply the display transform (882) and override table (875) in the same single function so backfill and live path agree.


## Critic
- Challenge: Only pre-#121 rows are affected; a one-off backfill script alone fixes the live data, so read-time heal code is extra complexity; and re-deriving via Piper inside a GET preview adds latency.
- Holds up? Yes, narrowed. The user's live rows (cacahuetes pəˈnuːz, paquet pakɛ) are exactly this: clip present, IPA stale, early-return in _serve_audio, verbatim read in preview. Backfill alone is not enough because rows with ipa='' + clip (881: a cold Piper run returned no IPA) can recur after the fix, and any row written before the normalize fn changes would also stay stale. Constraints for the dev-fixer: heal ONLY when ipa is empty (preview/play) and in the cached-clip branch of _serve_audio (re-derive, run through the shared normalize fn, commit); never synthesize on every preview; no change to primary keys or audio_key; backfill defaults to dry-run, is idempotent, re-derives IPA only (no deletes except see 891), and is not run on the live DB by the fixer. from-word must copy the lookup row's IPA (already normalized/healed), not heal separately.
- Final verdict: validated

## Fix
`lookup.heal_ipa` re-derives IPA through the shared `normalize_ipa`: on the cached-clip branch of `personal_api._serve_audio` (every play) and on `/preview` when a cached row's IPA is empty. `scripts/backfill_ipa.py` (dry-run default, idempotent) re-derives every `vocab_lookup`/`user_vocab` IPA. from-word copies the (healed) lookup row's IPA.
- Files: `app/content/lookup.py`, `app/content/personal_api.py`, `scripts/backfill_ipa.py`
- Tests: `tests/test_personal_vocab.py::test_cached_clip_with_stale_ipa_heals_on_play, test_empty_ipa_with_a_clip_is_filled_on_next_preview; tests/test_ipa.py::test_backfill_dry_run_apply_and_idempotence`
