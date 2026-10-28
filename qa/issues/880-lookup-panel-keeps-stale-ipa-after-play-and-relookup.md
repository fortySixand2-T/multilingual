---
id: 880
title: My deck lookup panel keeps showing the stale (wrong) IPA after playing audio and re-looking-up
severity: medium
area: web
persona: absolute-beginner
status: rejected
found: 2026-10-27
---

## Steps to reproduce
1. Sign up (qa060-c), open Learn -> My deck. Look up "cacahuète" so a real Piper clip exists (vocab_lookup.audio_key set).
2. Seed a pre-#121 style wrong IPA: UPDATE vocab_lookup SET ipa='kakawɛt' WHERE slug='cacahuete' (audio_key left in place).
3. In My deck, look up "cacahuète" again. Panel shows "/kakawɛt/". Press the speaker button (clip plays), then press Look up again.
4. Add to my deck; re-check DB.

## Expected
Once the word is voiced by Piper the panel/IPA should be the Piper-derived IPA (kakayˈɛt-style), not the old value.

## Actual
Panel still shows "/kakawɛt/" after playing and after re-looking-up; vocab_lookup.ipa still 'kakawɛt' in the DB. Cached-clip branch in `_serve_audio` returns before the IPA overwrite, and /preview returns the cached row verbatim. A learner sees pronunciation that does not match the audio, with no way to correct it.

## Notes
H1 confirmed from the UI. Pre-#121 rows with LLM IPA + a clip are stuck forever; needs a backfill or re-derive on preview.

## Triage
- Explanation: Duplicate of 869 (cached-clip branch in _serve_audio + verbatim preview).
- Against spec: see 869
- Verdict: rejected
- Rationale: Reject as a separate fix; keep as the UI acceptance test for 869 (stale kakawɛt with clip must heal or be re-derived on preview/play).


## Critic
- Challenge: Could be a distinct UI bug (panel not refreshing after play).
- Holds up? Rejection stands: the panel shows what the API returns; the data is stale server-side. Duplicate of 869. Keep as 869's UI acceptance test (stale IPA + clip -> heals on play/next lookup).
- Final verdict: rejected
