---
id: 370
title: Four new writing tasks (shopping, seasons, doctor, public-transport) not synced to DB -- return 404
severity: high
area: writing
persona: absolute-beginner
status: rejected
found: 2026-06-25
---

## Steps to reproduce
1. Sign up with invite code `friend-001`.
2. `GET /assessment/tasks?level=a1` -- returns 6 tasks. `write-a-shopping` and `write-b-seasons` are absent.
3. `GET /assessment/tasks/write-a-shopping` -- returns `404 "task 'write-a-shopping' not found"`.
4. `GET /assessment/tasks/write-b-seasons` -- returns `404 "task 'write-b-seasons' not found"`.
5. `GET /assessment/tasks/write-a2-doctor` -- returns `404`.
6. `GET /assessment/tasks/write-a2-public-transport` -- returns `404`.

## Expected
All four tasks should appear in the task list and be individually accessible. The YAML files exist in `content/a1/writing/` and `content/a2/writing/` and pass validation (all `target_vocab` IDs exist in their respective level vocabs).

## Actual
The tasks are authored in YAML but were never synced to the `writing_tasks` DB table. The sync script (`app/assessment/sync.py`) must be run manually, and it was not re-run after these four files were added.

A1 serves 6 tasks instead of 8; A2 serves 6 tasks instead of 8.

## Notes
- The YAML content is valid and well-formed -- the loader would accept it.
- All `target_vocab` IDs (`magasin`, `acheter`, `pain`, `fromage`, `prix`, `argent`, `soleil`, `pluie`, `neige`, `chaud`, `froid`, `saison`, `medecin`, `rendez_vous`, `malade`, `fievre`, `ordonnance`, `bus`, `metro`, `voiture`, `train`, `circulation`) resolve in the vocab table.
- Fix: run `python -m app.assessment.sync a1 content` and `python -m app.assessment.sync a2 content` to pick up the new tasks.
- Consider adding content sync to the app startup or CI pipeline to prevent this class of bug.

## Triage
- Explanation: The tester observed 404s for the four new tasks, but this was a transient state. Content sync (`writing-sync`) is a manual CLI step per `qa/README.md` ("Seed content first if needed: ./start.sh migrate && ./start.sh content-sync a1"). Checking the live database (`data/tef.db`), all 16 writing tasks (including write-a-shopping, write-b-seasons, write-a2-doctor, write-a2-public-transport) are present in the `writing_tasks` table. The sync has already been run.
- Against spec: The spec does not mandate automatic sync on deploy. The README documents manual sync as expected operational procedure.
- Verdict: rejected
- Rationale: Not a code bug. Content sync is a documented manual step, and it has since been executed -- all four tasks are in the DB. The 404s the tester observed were from a stale DB state before sync was run, not from a defect in the application or the PR.

## Critic
- Challenge: Could this be a real process bug? Should the PR have auto-synced or at least documented that sync is required after adding new YAML files? A future contributor could repeat this mistake. However, `qa/README.md` already documents the manual sync step, and adding auto-sync would be a feature enhancement (added complexity), not a bug fix. The tester's suggestion to add sync to startup or CI is reasonable but out of scope for this PR's defect list. The 404s were a transient operational state, not a code defect, and they are already resolved.
- Holds up? Yes, the PM was right. No code change is warranted. The sync was run, all 16 tasks are confirmed present in the DB, and the manual sync workflow is documented.
- Final verdict: rejected
