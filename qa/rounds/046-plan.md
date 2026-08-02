# QA round 046 — plan

- date: 2026-08-01
- app under test: backend :9020 (local worktree; :9000 is occupied by an unrelated
  container on this box — server started via `uv`-equivalent venv, see note below)
- scope: Speaking "diction cleanup" slice (PR #63, commit cd418d0) — TTS text
  sanitizer (`piper_adapter._clean`), tightened examiner/conversation prompts, and
  the Piper voice swap (siwis → upmc-medium).

## Change surface (highest risk first)

1. `app/ai/adapters/piper_adapter.py::_clean` (renamed from `_one_line`) — new
   regex-based stripping of Markdown marks/links, emoji, and typographic-punctuation
   normalization, run before every TTS synthesis call. **Pure function, no model
   change** — highest-value place to look for correctness bugs (over-stripping
   French, under-stripping new junk).
2. `app/speech/prompts/examiner.md` + `conversation.md` — added "plain spoken
   French only" instructions to the LLM. Not directly testable without a live LLM,
   but the sanitizer is the safety net if the LLM ignores this — so gaps in
   `_clean` matter more given the model won't always comply.
3. `Dockerfile` / `docker-compose.yml` / `.env.example` — voice id swap
   `fr_FR-siwis-medium` → `fr_FR-upmc-medium`. Config-only; check for stale
   functional references (comments/CHANGELOG mentions are fine, don't flag).

Context: the immediately preceding slice (#62, "faster response — STT knobs + reply
cap") caps the LLM reply length. A length cap increases the odds of a reply being
truncated mid-token, e.g. mid-Markdown-link (`[texte](https://ex...` with no closing
`)`), which `_clean`'s link regex requires to match — a truncated link would sail
through unstripped and Piper would voice the raw URL fragment. Worth probing
directly since the two slices compose.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | speech/sanitizer | `_clean` preserves French elision/hyphenation (l'avion, qu'est-ce, peut-être, vas-y) untouched — the apostrophe/hyphen chars aren't in the strip sets, so this should hold; probe to confirm, not expecting a break | call `_clean` directly with each phrase | edge-case-breaker |
| H2 | speech/sanitizer | some common emoji fall outside the four covered Unicode ranges (`\U0001f300-\U0001faff`, `\U00002600-\U000027bf`, flags, arrows `\U00002190-\U000021ff`, variation selectors) — e.g. ⭐ U+2B50, ⬆ U+2B06 live in the Miscellaneous Symbols and Arrows block (2B00–2BFF), which isn't covered — so those would leak through and get voiced as literal glyphs/mis-synthesized | `_clean("Bravo ⭐ continue ⬆")` and check the star/arrow survive | edge-case-breaker |
| H3 | speech/sanitizer | a reply truncated mid-Markdown-link (plausible given the #62 reply cap) leaves `[label](https://incomple` unstripped since `_MD_LINK` requires a closing `)` — the raw bracket/URL fragment would be voiced | `_clean("Regarde [le site](https://example.com/lo")` (no closing paren) and inspect output | edge-case-breaker |
| H4 | speech/sanitizer | bare (non-markdown-link) URLs/emails in a reply aren't stripped or normalized at all (only `[label](url)` is unwrapped) — plausible if the LLM ever answers with a raw link despite the prompt | `_clean("Voir https://exemple.fr/page pour plus.")` | edge-case-breaker |
| H5 | speech/sanitizer | hyphen-bullet lists (`- item`, not `*`/`_`-based) aren't stripped by `_MD_MARKS` (only `* _ \` # > \| ~`) — if the LLM emits a plain `-` bulleted list despite the prompt, the dashes would be spoken as literal words/pauses | `_clean("- Bonjour\n- Ça va ?")` | edge-case-breaker |
| H6 | speech/sanitizer | empty/whitespace-only input degrades gracefully (empty string out, no crash) — regression-safety check on the whitespace-collapse rewrite | `_clean("")`, `_clean("   \n\t  ")` | edge-case-breaker |
| H7 | config | no lingering *functional* `siwis` reference outside comments/docs (Dockerfile, docker-compose.yml, .env.example, test default all consistently `upmc-medium`) | `grep -rn siwis` across non-doc files; already spot-checked in planning — only a Dockerfile comment + CHANGELOG/qa-doc mentions remain, so this is likely refuted, confirm with tester | edge-case-breaker |
| H8 | speech/flow | live `/speech/status` and `/speech/turn` still report "unavailable"/503 cleanly with STT/TTS disabled locally (regression check post-refactor — `_clean`'s rename could have broken an import elsewhere) | `curl` `/speech/status` (signed-in) and a `/speech/turn` POST with a tiny wav | edge-case-breaker |

Note: the flow-level regressions called out in the task (transcript stored not
audio, 422 no-speech, 413 oversized, budget gating) are already covered by
`tests/test_speech.py`, which is green (231 passed). H8 above is a shallow live
smoke check, not a re-test of that suite — no need to duplicate it by hand.

## Coverage gaps

- No automated check today that the four `_EMOJI` Unicode ranges are *complete*
  against emoji actually likely in casual LLM output (H2 targets this directly).
- No test for a malformed/truncated Markdown link surviving `_clean` (H3) — a
  realistic input shape now that replies are capped in length (#62).
- No test for bare URLs (H4) or hyphen-bullets (H5) in `_clean`.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 570–579): chase H1–H8. This is a backend-only slice
  (no `web/src` changes) — use `qa-tester` (curl/python), not the browser tester.
  For H1–H7, don't hit the network — run `_clean` directly, e.g.:
  `/tmp/tef312/bin/python -c "from app.ai.adapters.piper_adapter import _clean; print(repr(_clean('...')))"`
  from the worktree root (repo importable without installing). For H8, use
  `curl http://127.0.0.1:9020` (server already running in this worktree; JWT
  signup via invite code `qa-test-001`, see `.env` — sign up, log in, hit
  `/speech/status` and `/speech/turn`). Report each hypothesis's actual output.

## Don't re-file (already settled)

- 540 mic-before-availability-check — done, not this slice.
- 550 speaking topic id collision across levels — deferred (product decision on
  scoping), not this slice's surface.
- 560 instruction hint ignores picked topic — done, not this slice (web/UI).
- 561 no beginner support in topic prompts — deferred, not this slice.
- Drill / Writing / Speaking 503 with no provider configured — expected, don't
  file (STT/TTS are `disabled` in this environment by design).
- Live audio recording / RUN_SPEECH_INTEGRATION-gated tests — environment
  limitation (no Piper binary/voice installed here), not a bug.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
