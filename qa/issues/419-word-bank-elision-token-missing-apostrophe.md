---
id: 419
title: Word_bank exercises split elision contractions as bare "l" token — reconstructed sentence missing apostrophe
severity: medium
area: content
persona: exam-crammer
status: fixed
found: 2026-07-03
---

## Steps to reproduce
1. GET /content/lessons/sciences-b2-02 (auth required).
2. Examine exercise `sciences-b2-02.e4` (word_bank type).
3. Observe tokens array: `["quoique", "l", "utilisateur", "soit", "prudent", "la", "cybersécurité", "reste", "fragile", "est"]`
4. The answer is: `["quoique", "l", "utilisateur", "soit", "prudent", "la", "cybersécurité", "reste", "fragile"]`
5. When the user places those tiles in order and the UI concatenates them with spaces, the result is:
   `"quoique l utilisateur soit prudent la cybersécurité reste fragile"`
   — the elision `l'utilisateur` is broken into `l utilisateur` (space instead of apostrophe).

Affected exercises (all verified via the YAML source):
- `sciences-b2-02.e4`: `l` + `utilisateur` → should be `l'utilisateur`
- `sciences-b2-03.e4`: `l` + `expérimentation` → should be `l'expérimentation`
- `economie-b2-02.e4`: `l` + `inflation` → should be `l'inflation`
- `societe-b2-03.e4`: `l` + `entraide` → should be `l'entraide`

## Expected
Each tile should either:
- Be authored as the complete elided form: `"l'utilisateur"` as a single tile, OR
- If split for pedagogical reasons, the tile should carry the apostrophe: `"l'"` as the tile token,
  so that the reconstructed sentence reads `l'utilisateur` (no space).

The built sentence shown to the user after they assemble the tiles should match correct written French.

## Actual
Tiles are: `["l", "utilisateur"]` producing output `"l utilisateur"` — a space where there should be an apostrophe. This is incorrect French and would confuse a learner who expects to see the word they just composed validated as correct French.

The YAML answer key values are plain strings: `"l"`, `"utilisateur"` — so any validation that checks the assembled string against a correct-French reference would also fail.

## Notes
- Verified across four separate word_bank exercises in sciences-b2-02, sciences-b2-03, economie-b2-02, societe-b2-03 — indicating this is a systematic authoring pattern, not a one-off typo.
- The same pattern appears in sciences-b2-01.e4 with `["cet", "algorithme"]` — but `cet algorithme` is correct French (determiner + noun, space is correct), so that case is fine.
- Fix options: (a) merge `l'` with the following noun into one tile, e.g. `"l'utilisateur"`; (b) add an apostrophe-bearing tile `"l'"` and keep the noun separate; (c) add frontend rendering logic that detects `l` + vowel-initial word and fuses them with an apostrophe. Option (a) is simplest for content authoring.
- Severity medium rather than high because the exercise is still understandable and the answer-checking logic (which compares tiles, not the reconstructed string) may still grade correctly; the user-visible assembled sentence is misleading/ugly but the grading may not be broken.
