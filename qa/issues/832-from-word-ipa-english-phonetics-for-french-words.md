---
id: 832
title: vocab/personal/from-word returns English-phonetics IPA for French words
severity: medium
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-25
---

## Steps to reproduce
1. Sign up (`friend-001`).
2. `POST /vocab/personal/from-word {"word":"horrible"}`
3. `POST /vocab/personal/from-word {"word":"amusant"}`
4. `POST /vocab/personal/from-word {"word":"intéressant"}`
5. Read the `ipa` field of each returned card.

## Expected
`ipa` should be French IPA for the French headword (e.g. "horrible" →
roughly `/ɔ.ʁibl/`).

## Actual
```
"horrible"     -> {"ipa":"hɒrəbəl", ...}
"amusant"      -> {"ipa":"eɪməsænt", ...}
"intéressant"  -> {"ipa":"in.ter.ste.ng", ...}
```
`ɒ`, `ə` (English schwa pattern), `eɪ`, and the ad-hoc "ste.ng" are English
pronunciation-guide phonetics, not French IPA — "horrible" and "amusant" are
literally the English words spelled the same as their French cognates, and
the lookup appears to have returned the *English* pronunciation. For
contrast, other words added in the same session got plausible French IPA
(e.g. "ébouriffant" → `eburifɑ̃`, "chuchoter" → `tʃuˈʃote` — the latter also
slightly off with the English-style `tʃ` for what should be a French `ʃ`,
but at least French-shaped).

## Notes
- This will mislead a learner using the IPA to learn pronunciation —
  "horrible" with English IPA teaches the English pronunciation under a
  French vocab card.
- Likely a dictionary/lookup-provider issue in the personal-vocab
  lookup/preview path rather than the raw-ChatML adapter change itself (not
  confirmed which provider backs `/vocab/personal/from-word`'s IPA field) —
  flagging as found incidentally while seeding cards for H1; worth checking
  whether it's LLM-generated (same `vocab_enrich` profile) or a static
  dictionary lookup that's cognate-confused.

## Triage
- Explanation: `/vocab/personal/from-word` shares `app/content/lookup.py`'s
  `fresh_lookup`, which calls the LLM (`vocab_enrich` profile, same
  `_ENRICH_SYSTEM` prompt in `app/content/enrich.py`) for a provisional
  `ipa` field, then — *if a TTS backend is wired* — overwrites it with
  Piper's own eSpeak-derived French IPA (`lookup.py`'s own module docstring:
  "IPA comes from Piper's own eSpeak phonemes rather than the LLM, which
  often guessed English IPA" — this override was already built specifically
  to work around this exact failure mode). This QA round's server reports
  `GET /speech/status` → `{"available": false}` (no STT/TTS backend
  configured, matching round 058's own plan note that no browser/speech
  testing was possible "on the Mac" for the same reason), so `tts is None`
  in `fresh_lookup`, the Piper override never runs, and the raw LLM-guessed
  `ipa` (English-phonetics-shaped for English/French cognates like
  "horrible", "amusant") passes straight through uncorrected. This path does
  not touch `app/ai/adapters/ollama_adapter.py`'s raw-ChatML rendering in any
  way that would change this behavior — the `vocab_enrich` LLM call itself
  would guess the same IPA whether rendered raw or via `/api/chat`.
- Against spec: unspecified beyond "IPA should be French pronunciation";
  the existing code comment shows this exact failure mode was already known
  and already had a real, deployed fix (Piper override) — it just doesn't
  apply when no TTS backend is present.
- Verdict: deferred
- Rationale: real and user-visible when it occurs, but (a) not caused by or
  related to PR #120's changes, and (b) specific to this QA sandbox's
  missing TTS backend — on the actual deployed box (which has Piper wired),
  the override in `lookup.py` should supply correct French IPA for these
  same words. Worth a quick live confirmation against the deployed box with
  TTS available before fully closing the loop, but out of scope for gating
  this round's PR.

## Critic
- Challenge: "Piper not wired locally" is a convenient excuse that needs
  checking against the actual deployed box, not just a code comment —
  maybe the override only partially fixes things, or the deployed box also
  lacks Piper, or the override itself has bugs that would surface even with
  Piper present.
- Holds up? Yes, on the evidence available. `GET /speech/status` on the
  live QA server returns `{"available": false}`, confirming `tts is None`
  on this box, matching the PM's claim. `app/content/lookup.py`'s own
  module docstring — predating this entire branch (last touched in #119,
  which itself predates #120's raw-ChatML commits) — documents that this
  exact failure mode (LLM guessing English IPA for French/English cognates)
  was already identified and already has a dedicated fix: Piper's
  eSpeak-derived IPA overwrites `row.ipa` in `fresh_lookup` whenever `tts`
  is not None. `enrich.py`'s `vocab_enrich` LLM call (which produces the
  provisional, wrong IPA) is also untouched by #119/#120's diffs, and the
  raw-ChatML rendering change is irrelevant here regardless — a model
  guessing wrong IPA produces the same wrong guess whether chat-rendered or
  raw-rendered, since IPA guessing isn't sensitive to the prompt-template
  mechanics this PR changed. The one gap is that nobody has confirmed the
  override actually works against the real deployed Piper-equipped box;
  the PM already flagged this explicitly as a follow-up rather than quietly
  closing it. That's the right amount of rigor for something this
  PR neither introduced nor can fix (the PR doesn't touch TTS wiring).
  Blocking PR #120 — which has nothing to do with TTS availability or the
  `vocab_enrich` prompt — on this would be gating on an unrelated,
  already-mitigated-by-design issue.
- Final verdict: deferred
