---
id: 873
title: IPA for long phrases is hard-truncated at 64 chars mid-word, with trailing space
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST preview {"word":"je voudrais un grand café crème avec un croissant au beurre s'il vous plaît"} (<=80 chars allowed).

## Expected
Full IPA, or a clean cut at a word boundary, or no IPA display for phrases.

## Actual
ipa = 'ʒə vudʁˈɛz œ̃ ɡʁˈɑ̃ kafˈe kʁˈɛm avˌɛk œ̃ kʁwasˈɑ̃ o bˈœʁ sil vu ' (exactly 64 chars, ends mid-phrase with a trailing space) while the audio (3.97 s) says the whole sentence.

## Triage
- Explanation: lookup.py stores ipa[:64] (column/field cap), cutting mid-phrase.
- Against spec: Nonsense/partial IPA must not be shown.
- Verdict: validated
- Rationale: Cosmetic-ish but violates 'never show wrong IPA'. Fix: cut at the last whole word within 64 chars (or skip IPA for phrases over the cap). Tiny; fold into the shared IPA-normalize function.


## Critic
- Challenge: Only long phrases; IPA display of a phrase is rarely used.
- Holds up? Holds, marginally: a half-IPA ending mid-word is the 'nonsense IPA' class and the fix is a few lines inside the shared normalize fn (cut at last space within the cap, rstrip). Do not widen the DB column or skip IPA for phrases.
- Final verdict: validated

## Fix
`normalize_ipa` caps at 64 chars on a word boundary (rstrip, hard cut only when there is no space); the column and phrase IPA are unchanged.
- Files: `app/content/ipa.py`
- Tests: `tests/test_ipa.py::test_long_phrase_is_cut_on_a_word_boundary`
