---
id: 1164
title: Speaking /from-word: plurals of course words make new cards with different gender/pos (livres mf, élèves no gender, sourds adjective)
severity: low
area: content
persona: exam-crammer
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/from-word {"word":"livres"}; {"word":"élèves"}; {"word":"personnes"}; {"word":"les enfants"}; {"word":"sourds"}.
2. Compare with preview of livre (course, m), élève (mf), enfant, sourd.

## Expected
Same pos/gender as the singular (livres -> livre noun m book, élèves -> élève mf) or the course word (no duplicate uv: card).

## Actual
- livres -> uv:livres noun gender "mf" "books, pounds" (course livre is m "book")
- élèves -> uv:eleves noun gender "" "students" (singular élève is mf)
- les enfants -> uv:enfants noun m "children"; personnes -> noun f "people"
- sourds -> adjective "deaf (pl.)"; grandes -> "large (f. pl.)" (fine)
- course words via bare/article forms: from-word 422 "word is already in the content bank" (consistent with preview in_course); but plurals bypass it and mint a second card for the same word.
Gender for livres is wrong for the book sense (mf comes from merging book m / pound f).

## Notes
find_content_match matches only exact lemma; the lookup does not lemmatise. Parity of from-word and preview itself is OK: both share the cached row (same pos/gender for any word).

## Triage
- Explanation: Reproduced by design: find_content_match matches the exact lemma only and the lookup does not lemmatise, so plurals mint separate uv: cards. Speaking's rich tier already extracts lemmas (resolve_new_words); /from-word with a raw plural is a direct-API edge.
- Against spec: Slice 3c intends lemmas as input; no lemmatiser in scope.
- Verdict: deferred
- Rationale: Real but low and out of PR #139 scope (needs lemmatisation). The 'livres -> mf books, pounds' gender is another instance of 1163. Defer until lemmatisation exists.

## Critic
- Challenge: Needs a lemmatiser; direct-API edge for plurals.
- Holds up? Deferral holds; out of scope for PR #139.
- Final verdict: deferred
