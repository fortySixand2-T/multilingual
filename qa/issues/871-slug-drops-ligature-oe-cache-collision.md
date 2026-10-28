---
id: 871
title: Lookup cache slug drops œ: looking up "il" returns the entry for "œil" (eye)
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST $B/vocab/personal/preview {"word":"œil"} -> eye, ipa ˈœj, audio_url .../lookup-audio/il
2. POST preview {"word":"il"}.
3. Also {"word":"bœuf"} -> slug b_uf; sœur -> sur-like, cœur -> cur.

## Expected
"il" is looked up as the pronoun; slug for œ is oe (or similar) so words never collide.

## Actual
Step 2 returns fr "œil", en "eye", ipa "ˈœj" for the word "il" (shared slug "il"). Order-dependent: whichever is looked up first poisons the other (wrong meaning, IPA and audio), for every learner since vocab_lookup is shared. bœuf gets slug b_uf.

## Notes
app/content/personal.py slugify (ASCII-fold drops œ/æ).

## Triage
- Explanation: slugify NFD-folds then replaces non [a-z0-9] with _, so œ/æ (no decomposition) are dropped: œil -> il, bœuf -> b_uf. lookup_slug uses it as the shared vocab_lookup PK.
- Against spec: unspecified; lookup cache is shared across learners so a collision is wrong meaning+IPA+audio for everyone.
- Verdict: validated
- Rationale: Real, wrong word shown with wrong IPA (same family as the user's complaint). Fix in lookup_slug only (map œ->oe, æ->ae before folding; do NOT change global slugify/content ids) and include in the backfill/cleanup: delete or re-derive poisoned vocab_lookup rows slug 'il' etc.


## Critic
- Challenge: Rare ligature words only (œil, bœuf, sœur, cœur, œuf).
- Holds up? Holds: these are common beginner words, the collision is shared across all learners and returns the wrong word (il -> eye). Fix confined to lookup_slug (map œ->oe, æ->ae before folding), not global slugify/content ids/personal_key. Existing rows with the old slug (b_uf, cur) simply become unreachable orphans; harmless. The poisoned row is detectable deterministically in backfill: new lookup_slug(row.fr) != row.slug -> delete that row (and its clip) so it regenerates. Also add() must use lookup_slug (see 870).
- Final verdict: validated

## Fix
`lookup_slug` spells ligatures out (oe/ae) before folding, so il and oeil no longer share a key; global `slugify`/content ids untouched. The backfill deletes rows with `lookup_slug(row.fr) != row.slug` and their clip.
- Files: `app/content/lookup.py`, `scripts/backfill_ipa.py`
- Tests: `tests/test_personal_vocab.py::test_ligature_words_do_not_share_a_cache_row; tests/test_ipa.py::test_backfill_dry_run_apply_and_idempotence`
