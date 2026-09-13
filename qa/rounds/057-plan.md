# QA round 057 — plan

- date: 2026-09-12
- app under test: backend + SPA single-origin at `http://127.0.0.1:9200` (all four
  levels synced: a1 11 speaking topics, a2 6, b1 6, b2 6)
- scope: code range `78d0a74..a91dbe7` (#104, #105, #106) — every level now has both
  TEF speaking sections, A1 gets 5 new everyday-conversation topics with English
  clues, and a new on-demand English-subtitle endpoint for examiner replies. This
  round touches application code (model, migration, API, frontend), not just content.

## Change surface (highest risk first)

Per `git diff --stat 78d0a74..a91dbe7`:

1. **On-demand subtitles (#106)** — new `POST /speech/turn/{turn_id}/translate`
   (`app/speech/api.py`), new `speech_turns.reply_en` column (migration
   `0021_speech_reply_en`), a new cached `speech_translate` AI profile in both
   routing configs, and `/speech/history` now surfaces `reply_en`. Frontend:
   `Subtitle` component in `web/src/screens/Speaking.tsx` with a
   "Show English"/"Hide English" toggle. Biggest surface: a new endpoint that
   reads another table row by id and bills a shared budget — exactly the shape
   that leaks cross-user data or double-bills if ownership/budget checks are off.
2. **A1 everyday conversation topics + `section: "C"` (#105)** — `SpeakingTopic`
   gains `Literal["A","B","C"]` plus optional `prompt_en`/`points_en`;
   `framing()` grows a C branch with different examiner instructions (warm
   conversation partner, not examiner). 5 new a1 topics. b1/b2 deliberately carry
   no English fields — a regression here would leak English scaffolding to
   levels that shouldn't have it, or fail to show it at a1.
3. **e2e fix + speaking topics for every level (#104)** — `check_speaking_covers_both_sections`
   content-check rule added; already ran clean (`content OK`). Lower risk — this
   is the content-completeness half already verified structurally in-repo.

**Already found during this planning pass (concrete lead, not just a hypothesis):**
`Subtitle` in `web/src/screens/Speaking.tsx` (~line 674-690): `reveal()` calls the
endpoint, then `onTranslated(r.reply_en)` and `setShown(true)` unconditionally
(when not `over_budget`). But the render guard is `if (shown && replyEn)` — if
`reply_en` comes back as an **empty string** (which the API deliberately returns
for a turn with blank `reply_text`, or for the `authored=""` edge), `replyEn` is
falsy, so the component falls through to the "Show English" button again with no
visible change and no error message. A learner who presses "Show English" on such
a turn sees the button flicker/reset with zero feedback — looks like the click did
nothing. Testers should confirm whether any real turn can have blank `reply_text`
reachable from the UI (an opener has blank *transcript*, not blank *reply_text*,
so this may be unreachable in practice — worth checking rather than assuming).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | speech/translate ownership | `POST /speech/turn/{turn_id}/translate` correctly 404s (not 403, not another user's data) when `turn_id` belongs to a different user — a speech transcript is a private conversation, and the query filters by `user_id` in the same `select`, which is the right pattern, but confirm it live across two accounts. | curl: seed/discover the existing turn for user 1 (session `qa-seed`), sign up a second account (user 2), call the endpoint as user 2 against user 1's turn id, expect 404 and no leaked `reply_en`/`reply_text`. | edge-case-breaker |
| H2 | speech/translate caching | Second call to `/translate` on the same turn returns `cached: true` without re-billing/re-calling the LLM, and the cached value round-trips through `/speech/history`. | curl: call `/translate` once on a real turn (first call, expect `cached:false`, bills usage), call again (expect `cached:true`, identical `reply_en`, verify usage ledger didn't increase second time), then `GET /speech/history` and confirm the same `reply_en` appears for that turn. | edge-case-breaker |
| H3 | speech/translate edge inputs | Non-existent turn id → clean 404 (not 500); non-numeric turn id → clean 4xx (path converter); a turn with empty `reply_text` → `{reply_en:"", cached:true}` per the code (not a 500, not a hang). | curl: call `/translate/999999` (doesn't exist), `/translate/abc` (non-numeric), and a turn seeded directly in SQLite with `reply_text=''` — check each response code/body. | edge-case-breaker |
| H4 | speech/translate budget | Past the daily "speaking" token budget, `/translate` returns `{reply_en:"", over_budget:true}` rather than erroring or silently billing on. | curl: seed/consume the daily speaking budget (via repeated `/translate` calls on distinct un-cached turns, or by writing usage rows directly), then confirm the flagged response; also confirm a call for an *already-cached* turn still succeeds past budget (cache lookup happens before the budget check in the code — verify this live). | edge-case-breaker |
| H5 | section C content/API | `?section=C` filters correctly on `/speech/topics?level=a1`, returns exactly the 5 new topics with non-empty `prompt_en`/`points_en`; `/speech/topics?level=b1` and `b2` have zero topics with non-empty `prompt_en`/`points_en` (English must not leak to levels that shouldn't have it). | curl: `GET /speech/topics?level=a1` (11 total) and `&section=C` (5, all with English fields populated); `GET /speech/topics?level=b1` and `b2` — assert every topic has `prompt_en: ""` and `points_en: []`. | edge-case-breaker |
| H6 | web/speaking UI | The Speaking screen at level a1 labels section C topics as "Conversation" (not "Section C"), renders the French prompt with the English gloss and clues underneath, and the examiner framing feels like a chat partner not an exam grader when a C topic is picked. At b1/b2, no English ever appears (no stray empty subtitle button, no blank gloss row). | browser: sign up fresh (becomes user 1, or use existing session), go to Speaking, level a1, pick a "Conversation" (section C) topic, confirm the label and English clues render; switch to b1/b2 and confirm no English scaffolding appears anywhere in the topic picker. | absolute-beginner |
| H7 | web/subtitle toggle | The "Show English"/"Hide English" toggle under an examiner reply works end to end from the UI: pressing "Show English" on the seeded turn (which has real French text) reveals the English, toggling hides it again without re-fetching, and a second visit to the same conversation shows it already revealed (cached). Also chase the concrete lead above — does any reachable turn produce an empty-string `reply_en` that leaves the button in a dead-looking state? | browser: open Speaking history/conversation containing the seeded turn (or a fresh opener with a canned reply), press "Show English", verify text appears and button flips to "Hide English"; press again to hide; reload/reopen the conversation and confirm it's still shown without a fresh click. Note any turn where the button appears to do nothing. | absolute-beginner |
| H8 | regression | The migration and new column don't break anything for a1/a2/b1/b2 existing speaking flows, `check_content.py`, or unrelated app areas (Path, Vocab, Review) — a schema change + new AI profile is exactly the kind of edit that regresses config loading or DB access elsewhere. | curl: smoke a handful of unrelated endpoints (`/content/vocab?level=a1`, `/srs/review/queue`, `/path?level=b1`) to confirm no incidental regression; confirm `scripts/check_content.py` still runs clean (already done by planner — `content OK`). | edge-case-breaker |

## Coverage gaps
- `/speech/turn/{turn_id}/translate` has **zero prior issue history** — first pass
  on brand-new endpoint, ownership-sensitive (private transcript data).
- No prior round has looked at `canned_opener_en` exact-string matching in
  `app/speech/examiner.py` — if a canned opener's French text is ever mutated
  (e.g. trailing whitespace, template substitution) the match silently fails and
  falls through to a live LLM call that should have been free; worth a quick read
  even without a live opener endpoint (STT is off locally so `/speech/opener` 503s
  — don't file that, it's the known local-environment gap).
- No prior round has exercised `section: "C"` end-to-end through UI at all (new
  this round).

## Charters (per tester, with id blocks)
- `qa-tester` (curl, persona **edge-case-breaker**, ids **810–819**): chase H1
  (cross-user ownership on `/translate`), H2 (cache correctness + `/speech/history`
  round-trip), H3 (bad turn ids, empty reply_text), H4 (budget path), H5 (section C
  filter + English-field leakage check on b1/b2), and H8 (quick regression smoke).
  App base `http://127.0.0.1:9200`; invite token `GWqls74vaM7ZL7P4`; DB at
  `/private/tmp/claude-501/-Users-sirius-projects-multilingual/ed7a5caa-e0ba-41b4-9ba4-75595c78619c/scratchpad/qa/qa.db`
  (safe to seed rows into `speech_turns` directly for edge cases — e.g. a turn with
  `reply_text=''`, or a second user's turn). The first signup becomes user_id 1 and
  should already own the seeded `qa-seed` turn (session with reply "Très bien !
  Et qu'est-ce que vous aimez boire le matin ?") — check `/speech/history` after
  signup to confirm, then sign up a second account for the ownership check in H1.
  Do NOT hammer the LLM — H2/H4 need at most a couple of real `/translate` calls;
  don't loop calling it dozens of times.
- `qa-browser-tester` (persona **absolute-beginner**, ids **820–824**): chase H6
  (section C labeling/English rendering at a1, no leakage at b1/b2) and H7 (the
  subtitle toggle end-to-end, including the empty-string dead-button lead). App
  `http://127.0.0.1:9200`, SPA pre-built and served single-origin; sign up fresh
  with invite token `GWqls74vaM7ZL7P4` if no session exists, or reuse the account
  the curl tester created (coordinate on which becomes user 1 — either is fine, the
  seeded turn just needs to be reachable in *some* account's history for H7).
  Remember `POST /speech/turn` and `/speech/opener` 503 locally (no STT) — don't
  file that; if you need a fresh conversation with real French text to translate,
  the seeded `qa-seed` turn or a directly-seeded row is the way to get one, not a
  live recording.

## Don't re-file (already settled)
- Drill / Writing grading / Speaking 503 with no STT/TTS provider (`/speech/turn`,
  `/speech/opener` in this local environment) — expected; only file if the
  *handling* is poor, not the missing provider.
- `web/e2e/specs/vocab-deck.spec.ts:30` flaky on chromium — known, re-run don't
  investigate.
- Issues 800/801/802 (verb `accept`-list translation bugs, round 056) and all
  content/vocab issues below 810 — unrelated area, don't re-touch this round.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
