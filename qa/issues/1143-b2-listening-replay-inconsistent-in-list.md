---
id: 1143
title: New B2 listening set allows replay while all other B2 listenings say "no replay"
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Set level to B2, open Comprehension, scroll to Listening.
2. Compare "Débat : les téléphones à l'école" (listen-b2-telephones-a-l-ecole) with the other 14 B2 listenings.

## Expected
Consistent exam-style treatment at B2 (or a visible reason), as the list labels sets "no replay".

## Actual
Every other B2 listening row reads "... · QC accent · no replay"; the new one reads "3 questions · 150s · QC accent" and opens with a free native audio control (replay/seek allowed). The new set also has only 3 questions and a 150s limit vs 180-240s for peers, so it sits unevenly in the list. The new B1 listenings (voisin courageux, directrice) are replayable too, which matches older B1 but not B2.

## Notes
content/b2/comprehension/listen-b2-telephones-a-l-ecole.yaml has allow_replay: true. Rendering itself is fine: audio loads (0:32), plays, no console errors.


## Triage
- Explanation: listen-b2-telephones-a-l-ecole.yaml has allow_replay: true while the other 14 B2 listenings are false (B1 mix is 16 true / 3 false, so the new B1 sets are consistent).
- Against spec: Models: allow_replay=False = exam mode; B2 convention.
- Verdict: validated
- Rationale: B2 is exam-style no-replay; the new set is the lone exception, almost certainly authoring oversight. One-line YAML fix to false. Low. (The 3-question/150s shape is a mild oddity, not part of this fix.)

## Critic
- Challenge: Could be intentional? Checked: 14 of 15 B2 listenings are allow_replay: false; the list labels them 'no replay' (exam mode). The new set (line 8: allow_replay: true) is the lone exception, introduced in abeed23; the plan lists no reason. B1 mix is mostly true so B1 sets are consistent. One-word YAML flip, no audio change, no effect on gate. UI itself renders correctly with the flag.
- Holds up? yes
- Final verdict: validated
- Note for dev-fixer: Flip only allow_replay to false in listen-b2-telephones-a-l-ecole.yaml; leave 3-question/150s shape.

Fix: content/b2/comprehension/listen-b2-telephones-a-l-ecole.yaml — allow_replay: false.
