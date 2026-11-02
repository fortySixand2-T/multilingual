---
id: 1141
title: Guillemets and colons use normal spaces, so « or : can be stranded at a line end
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Open read-b1-cafe-philo in a ~375px viewport.
2. Look at the third paragraph, the quote of the elderly lady.

## Expected
Opening guillemet stays attached to the following word (non-breaking space after « and before » and before ":" / "?").

## Actual
Line ends with "... ne l'a pas quittée : «" and the quote starts on the next line ("L'amour ne peut pas disparaître..."). Passage data has 0 NBSP characters: read-b1-cafe-philo has 6 plain-space guillemets, read-b1-bien-s-installer 2, and all " :" use regular spaces. A beginner may not understand that « is an opening quote left dangling.

## Notes
Content-level (use U+00A0 / U+202F in the YAML) or render-time replace of "« " / " »" / " :" with NBSP variants.


## Triage
- Explanation: Content has plain spaces around « » and before ':'; no NBSP handling anywhere.
- Against spec: French typography convention.
- Verdict: validated
- Rationale: Real typographic defect (French requires non-breaking space; opening « stranded at line end confuses beginners). Cheapest fix is the same render-time transform as 1140 (replace '« ' / ' »' / ' :' / ' ?' / ' !' with NBSP forms) so all 89 passages and scripts benefit without editing content. Low severity; ship with 1140.

## Critic
- Challenge: Cosmetic and low. Counter: stranded opening guillemet (« at line end) is a genuine reading-comprehension hazard for beginners and French typography requires NBSP; since 1140 reflows text, stranding will persist or move, and a tiny shared render-time regex fixes all passages without content edits.
- Holds up? yes, low severity
- Final verdict: validated
- Note for dev-fixer: Apply in the same render helper as 1140, passage only: NBSP after « , before » and before : ; ! ?. Keep it a few lines; don't touch YAML.

Fix: web/src/passageParagraphs.ts — non-breaking spaces around « » and before : ; ? !.
