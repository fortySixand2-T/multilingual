---
id: 1160
title: Typed article (le/la/un/une) is ignored by My deck lookup for course words and function words
severity: medium
area: content
persona: exam-crammer
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"la mémoire"}; then "le mémoire"; "la tour"; "le poêle"; "la livre"; "un critique"; "la collègue"; "le fou"; "le contre"; "le dessus"; "le plus".
2. Compare with the bare word.

## Expected
The typed article picks the noun reading and its gender: la mémoire = memory (f), la tour = tower (f), le poêle = stove (m), la livre = pound (f), un critique = critic (m), le dessus = the top (noun).

## Actual
The article is dropped: course words come straight from the course bank (find_content_match runs before any lookup), and function words stay function words.
- "la mémoire" -> mémoire noun m "thesis, dissertation" (in_course b1); same for "le mémoire"
- "la tour" -> tour noun m "turn; tour"; "le poêle" -> poêle noun f "frying pan"; "la livre" -> livre noun m "book"
- "un critique" -> critique noun f "review"; "la collègue" / "le collègue" -> collègue noun m (no mf); "le fou" -> fou adjective "crazy"
- "le contre" -> preposition "against"; "le dessus" -> adverb; "le plus" -> adverb "more, most" (src empty = model/dictionary, no noun)
- "un hors"/"le rien"/"un Français" -> noun '' / pronoun / adjective (article ignored)
Also the lookup cache is keyed on the lemma only, so whoever looks up the bare word first fixes the pos for everyone: after "pas", "un pas" returns adverb "step, pace, strait" and "un car" / "le car" return conjunction "as, since". lexicon.pos docstring promises "A typed article (le pas) says noun", but "le pas"/"un pas" give adverb.

## Notes
Course-bank words also lose mf/gender-by-meaning (enfant, collègue only m). Root causes: find_content_match short-circuit in personal_api.preview, lexicon.pos only honours article when model_pos in ('', 'noun'), shared cache ignores article.

## Triage
- Explanation: Reproduced: preview calls find_content_match first (accent- and article-folding) so a course word returns the course card whatever article was typed; lookup cache key is the lemma only, so the first looker fixes pos for all (confirmed: le vase, un page, bete). Course data itself (memoire only as m 'thesis') is a content question.
- Against spec: lexicon.pos docstring says a typed article means noun, honoured only when model_pos in ('', 'noun'); no spec requires article-aware homograph resolution.
- Verdict: deferred
- Rationale: Real but a design limitation: needs a cache key that includes the article/noun intent. Most of the learner harm (wrong pos/gender from bare lookups) is covered by 1161/1162/1163 which are validated. Revisit the 'un pas -> adverb' case after the 1161 fix; sub-issues about course words keeping one gender (enfant, collegue) are course-content, not My deck. Not FIXING NOW.

## Critic
- Challenge: Article-aware homograph resolution is a design change (cache key + course short-circuit); bare-word users get the usual reading.
- Holds up? Deferral holds. The learner-visible parts that matter are covered by 1161-1163; revisit after those.
- Final verdict: deferred
