---
id: 1100
title: My deck lookup of "du" shows and saves the headword "dû" with gloss "of"
severity: medium
area: web
persona: absolute-beginner
status: rejected
found: 2026-10-31
---

## Steps to reproduce
1. Sign up (invite qa063-c), go to /my-deck (level B1).
2. Type `du` in "Add a word to my deck", press Enter, wait for the real 7B lookup.
3. Observe the result card, press "Add to my deck", look at the saved card in the list.

## Expected
Headword `du` (the very common contraction), gloss like "of the" / "some". No accent added to an unaccented function word.

## Actual
Result card headword is **dû** (past participle of devoir), IPA /dy/, no gender, meaning prefilled as "of". The saved card in the My deck grid is the same: "dû / dy / of". Headword (dû = owed) and gloss (of) disagree; a beginner would learn the wrong spelling of a top-10 word.

## Notes
Confirms H1 (lexicon.respell re-accents accentless input to the rarer homograph). Screenshot observed after lookup: "dû" in bold next to speaker and turtle buttons, Meaning field "of".

## Triage
- Explanation: Duplicate of 1060 via the My deck UI path (same /vocab/personal lookup; respell du -> dû). Not reproduced in browser; the API path is identical and the offline respell reproduces it.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Duplicate of 1060; UI shows the same wrong headword. No separate UI work.

## Critic
- Challenge: A UI defect? No: the My deck lookup calls the same /vocab/personal lookup; the wrong headword is lexicon.respell du->dû. Nothing in web/ to change.
- Holds up? Duplicate of 1060; closed. Verify in browser after the 1060 fix if desired.
- Final verdict: rejected (duplicate of 1060)
