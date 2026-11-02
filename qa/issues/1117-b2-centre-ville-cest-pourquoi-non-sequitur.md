---
id: 1117
title: read-b2-centre-ville-sans-voitures: "C'est pourquoi j'ai décidé de prendre position" does not follow from the previous paragraph
severity: low
area: comprehension
persona: exam-crammer
status: done
found: 2026-11-01
---

## Steps to reproduce
1. GET /comprehension/sets/read-b2-centre-ville-sans-voitures, paragraphs 3-4.

## Expected
Logical connectors that match the argument.

## Actual
Paragraph 3 lists unresolved problems ("Tout n'est pas réglé pour autant ... Il importe que la ville écoute aussi ceux qui vivent loin du centre."). Paragraph 4 starts "C'est pourquoi j'ai décidé de prendre position publiquement en faveur du projet." Unresolved problems are not a reason to publicly back the project; the connector exists only to place "prendre position" (deck headword). At B2 (argumentative text) a coherence error like this is confusing for a test taker.

## Notes
Proposed replacement: "Malgré ces réserves, j'ai décidé de prendre position publiquement en faveur du projet."


## Triage
- Explanation: Paragraph 4 opens 'C'est pourquoi' after a paragraph of reservations, so the logical link is wrong.
- Against spec: Spec: B2 argumentative coherence.
- Verdict: validated
- Rationale: 'C'est pourquoi' signals consequence; unresolved problems do not cause a public endorsement. At B2 (argumentative text, connector comprehension is tested) this is a coherence defect. Fix: 'Malgré ces réserves, ...'. Low severity.

## Critic
- Challenge: 'C'est pourquoi' after a paragraph of unresolved problems is a genuine causal non sequitur; at B2 connector logic is exactly what is tested, and a swap to 'Malgré ces réserves' keeps 'prendre position'. Verified in YAML paragraphs 3-4.
- Holds up? yes
- Final verdict: validated
- Note for dev-fixer: Plain text edit in a reading set; no audio.

Fix: content/b2/comprehension/read-b2-centre-ville-sans-voitures.yaml — 'Malgré ces réserves, j'ai décidé de prendre position'.
