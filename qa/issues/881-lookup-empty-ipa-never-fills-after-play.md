---
id: 881
title: Lookup row with empty IPA and a cached clip never gets IPA; panel shows no pronunciation even after play/re-lookup
severity: medium
area: web
persona: absolute-beginner
status: rejected
found: 2026-10-27
---

## Steps to reproduce
1. My deck -> look up "horrible" (first lookup in the scratch container; it produced vocab_lookup row ipa='' with audio_key 'vocablookup/horrible.wav').
2. Panel shows only the word, two speaker buttons, meaning. No "/…/" line.
3. Press the speaker, wait, press Look up again, reopen My deck.

## Expected
IPA appears (at least after the word is voiced once), e.g. /ɔʁˈibl/.

## Actual
No IPA line at any point; DB still ipa=''. Piper --debug in the same container does emit "oʁˈibl", so the data is derivable. Because the clip already exists, the play path early-returns and never backfills (H6). Other words looked up later in the same session got IPA, so the empty row is a one-off that is permanent.

## Notes
Cause of the initial empty ipa not identified (possibly first/cold lookup). Fix: backfill when ipa=='' on preview/play.

## Triage
- Explanation: Duplicate of 869 (empty ipa + cached clip never backfilled). Origin of the initial empty IPA is unexplained (possibly cold first lookup) but the heal path is the same.
- Against spec: see 869
- Verdict: rejected
- Rationale: Reject as separate; 869's read-time re-derive and backfill must also cover ipa=='' rows. Add as acceptance test.


## Critic
- Challenge: The unexplained origin of ipa='' on a cold first lookup might be its own bug (synthesize_ipa returning empty although a clip was made).
- Holds up? Rejection stands: whatever produces an empty IPA, the remedy that matters to the learner is the 869 heal for ipa=='' + clip, which is explicitly in 869's scope. Chasing the cold-start cause without a repro is speculative. Acceptance test: ipa='' row with clip gets IPA after play/preview.
- Final verdict: rejected
