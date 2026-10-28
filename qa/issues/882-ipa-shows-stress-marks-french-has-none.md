---
id: 882
title: IPA shown to learners carries eSpeak stress marks (ˈ) on the last syllable, which French does not have
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-10-27
---

## Steps to reproduce
1. My deck -> look up "paquet", "cacahuète", "horrible".
2. Read the "/…/" line under the word.

## Expected
Plain French IPA without lexical stress, e.g. /pakɛ/.

## Actual
Panel shows "/pakˈɛ/" (zoomed screenshot: stress mark before the final vowel). Other rows in the DB: kakayˈɛt, naˈiv, ˈut, ˈa, "pˈøtˈɛtʁ" (stress in every syllable group). A beginner will read this as "stress the last syllable / English-style stress" and the marks are noise for phonetic readers.

## Notes
H4 confirmed. Strip ˈ and ˌ in synthesize_ipa (or at display). Related to 875 (eSpeak IPA quality) but this is the systematic stress-mark defect.

## Triage
- Explanation: Piper --debug/eSpeak marks the final syllable with ˈ; synthesize_ipa keeps the marks.
- Against spec: PO: wanted - strip ˈ/ˌ for display (French has no lexical stress).
- Verdict: validated
- Rationale: Misleading to beginners. Fix in one shared normalize step (strip ˈ ˌ, trim whitespace) applied at synthesis and in the backfill. Overlaps 875 part (1); implement once.


## Critic
- Challenge: Stress marks are valid IPA; some learners may like them.
- Holds up? Holds: French has no lexical stress and eSpeak's final-syllable ˈ is misleading to beginners (PO wants them stripped). One shared normalize step (strip ˈ ˌ, trim, collapse spaces), applied at synthesis, at heal and in backfill; no separate code.
- Final verdict: validated

## Fix
`normalize_ipa` strips ˈ and ˌ and collapses whitespace; `lookup.voice_with_ipa` applies it at synthesis, `heal_ipa` and the backfill reuse that same path.
- Files: `app/content/ipa.py`, `app/content/lookup.py`
- Tests: `tests/test_ipa.py::test_normalize_strips_stress_and_collapses_spaces; tests/test_personal_vocab.py::test_lookup_is_cached_across_users_case_and_accents`
