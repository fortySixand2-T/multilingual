---
id: 892
title: IPA for accentless input is nonsense or truncated (ete -> ˈiːt, tres -> tʁ, cacahuetes -> kakayˈət)
severity: high
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-27
---

## Steps to reproduce
Env: B=http://127.0.0.1:9300; T=<bearer from POST /auth/signup, invite qa060-b>. P(w) = curl -s $B/vocab/personal/preview -H "authorization: Bearer $T" -H 'content-type: application/json' -d '{"word":"w"}'
1. P(ete) -> ipa "ˈiːt" ; GET $B/vocab/personal/lookup-audio/ete returns 200 audio/wav (the voiced clip).
2. P(tres) -> ipa "tʁ"; P(cacahuetes) -> "kakayˈət"; P(eleve) -> "elˈɛv"; P(francais) -> "fʁɑ̃kˈɛ"; P(deja) -> "dəʒˈa".

## Expected
IPA matches the real word (e.g. ete -> ete / été "ete", très "tʁɛ", cacahuètes "kakawɛt", déjà "deʒa"), complete, no English phonemes.

## Actual
Piper/eSpeak reads the unaccented spelling as typed: "ete" gets the English-like long vowel ˈiːt (sounds like "eat"); "tres" is cut to "tʁ" (the e is dropped); cacahuetes gets "ayət"; "deja" gets schwa "dəʒa". Learner hears and sees a pronunciation that makes no sense, which is the original complaint. Singular cacahuète correctly gives kakawɛt, so the plural/accentless row is the broken one.

## Notes
Root cause is 891 (voice the corrected headword), filed separately because the symptom is also reproducible for words with no accent ambiguity once the wrong spelling is cached.

## Triage
- Explanation: Downstream symptom of 891/890. `fresh_lookup` voices the typed/cached unaccented `fr` through `voice_with_ipa`; eSpeak reads "ete"/"tres" as English-like or truncated and the IPA is stored verbatim (then `ipa[:64]`, see 873). The IPA engine is behaving as fed; the input word is wrong.
- Against spec: Same PO requirement as 891: nonsense IPA for a mis-spelled stored form must not be shown.
- Verdict: validated
- Rationale: Duplicate-in-cause of 891 (fix is the headword voicing + cache-hit headword check + backfill that drops/re-derives such rows); no separate code change beyond a regression test asserting that after the fix preview of "ete"/"cacahuetes" voices the accented headword and IPA is derived from it (use fake TTS recording the text passed). Keep open as the acceptance test for 891, do not fix twice. Genuine eSpeak misreads of correctly-spelled words (e.g. fils) stay in 875 scope.


## Critic
- Challenge: Pure downstream symptom of 891/890; the triage itself says 'do not fix twice' and no separate code change. Keeping it validated sends a no-op work item to the fixer, inconsistent with rejecting 880/881 as duplicates.
- Holds up? Overturned to duplicate: reject as a separate fix and keep its repro as a regression test attached to 891 (fake TTS records the text passed: preview of 'ete'/'cacahuetes' voices the accented headword and IPA derives from it). Genuine eSpeak misreads of correct spellings stay in 875.
- Final verdict: rejected
