---
id: 1062
title: Typing 'la' returns 'là' (adverb, 'there') instead of the article
severity: medium
area: content
persona: edge-case-breaker
status: rejected
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"la"}

## Expected
fr "la" (article/pronoun, f. 'the'); at least not silently re-accented.

## Actual
{"enrichment":{"fr":"là","en":"there","pos":"adverb",...,"in_course":"a1"}} audio la_adv.mp3. The far more common unaccented word is unreachable via lookup.

## Notes
H1 confirmed. Also fires through course-word matching (in_course a1).

## Triage
- Explanation: Same site as 1063: the model proposed 'là' for 'la'; _headword accepts it. Caveat: Lexique merges forms, là (3186) is MORE frequent than la (2324), so the frequency rule that fixes sur does not fix la; needs a closed-class pin (la, le, les, ...) or preferring the typed spelling when typed is a known form and the model's gloss is an article sense.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real but medium; handle with 1063 in _headword, la needs the extra pin. Related to in_course a1 match to la_adv.

## Critic
- Challenge: PM validated but proposed a closed-class pin. Live preview shows fr là, en 'there', adverb: the 7B itself glossed the accented word, so headword and gloss agree. Lexique ranks là (3186) above la (2324), and learners legitimately type là without accent, so re-accenting is a defensible reading, not corruption. Pinning la to the article would make fr/en disagree with the model's own gloss or force a re-prompt. Respell itself returns 'la' (offline), so #133 respell is not the cause.
- Holds up? No. Ambiguous input, consistent card, model-quality; fix costs more than the bug (pin list plus gloss mismatch). The in_course a1 la_adv match is a consequence of the same ambiguity.
- Final verdict: rejected
