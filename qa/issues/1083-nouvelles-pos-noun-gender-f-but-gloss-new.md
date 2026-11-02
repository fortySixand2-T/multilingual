---
id: 1083
title: "nouvelles" comes back as noun, gender f, gloss "new" (adjective sense, noun tag)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"nouvelles"}
2. Control: {"word":"vieilles"}, {"word":"cheres"}, {"word":"heureuses"}.
3. POST $B/vocab/personal/from-word {"word":"nouvelles"}; GET $B/vocab/personal.

## Expected
Consistent entry: either adjective "new (f. pl.)" with no gender (as vieilles, cheres, heureuses give), or noun "news" with gender f.

## Actual
{"fr":"nouvelles","en":"new","pos":"noun","gender":"f","gender_source":"table"} and the saved card is identical (pos noun, gender f, en "new"). The learner sees a noun labelled "new" with a gender tag, the 1000 pattern for this word only.

## Notes
1000 regression-adjacent: other inflected adjectives are fixed. Here the gender table (nouvelle -> f, noun) wins over the gloss, so pos noun + en "new" disagree.

## Triage
- Explanation: Offline pos('nouvelles','noun') stays noun (Lexique pos empty); the gender table lists nouvelle as f noun, so resolve_gender yields f. The 7B glossed the adjective sense 'new'. 'nouvelles' (news) as a feminine noun is a legitimate reading, so only the gloss is off.
- Against spec: Not a #133 regression of 1000 (adjective pos fix cannot know the sense).
- Verdict: deferred
- Rationale: Model-quality gloss/pos ambiguity, low; defer.

## Critic
- Challenge: Could be a 1000 regression. nouvelles (news, f) is a legitimate noun reading and Lexique has no pos for it, so the code cannot know the sense; only the 7B gloss is off.
- Holds up? Deferral confirmed.
- Final verdict: deferred

## Fix
The prompt asks what the exact form given means, and says a plural noun with a meaning of its own gets that meaning (lunettes -> glasses). Real 7B, 3 runs: nouvelles -> "news" every time (was "new"). The adjective form note now comes from Lexique (fr_forms.tsv.gz note column), not the model, so a noun never carries one. Tests: test_adjective_form_note_comes_from_lexique, test_senses_list_is_joined.
