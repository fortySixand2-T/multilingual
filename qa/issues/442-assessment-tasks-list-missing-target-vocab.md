---
id: 442
title: "GET /assessment/tasks list omits target_vocab field"
status: done
severity: medium
area: writing
persona: edge-case-breaker
round: "034"
---

## Steps to reproduce
1. GET http://localhost:8080/assessment/tasks?level=b2 (with valid Bearer token)
2. Inspect each task object in the response for the `target_vocab` field.

## Expected
Each task object should include a `target_vocab` field (array of vocab IDs) matching what
is defined in the source YAML. For example:
- `write-b2-food-letter` → `["malbouffe", "gaspillage_alimentaire", "circuit_court", "producteur"]`
- `write-b2-food-essay` → `["elevage", "agriculture", "souverainete_alimentaire", "autosuffisance"]`

## Actual
The `target_vocab` field is absent from every task in the list response. Only the
individual-task endpoint (`GET /assessment/tasks/{task_id}`) returns it (along with
`target_vocab_fr`).

## Notes
Root cause is in `app/assessment/api.py` `list_tasks()` (lines 60–71): the dict
comprehension building the response does not include `target_vocab` or
`target_vocab_fr`. The data is present in `r.data` (sourced from YAML); it is just
not forwarded. The individual `get_task` handler returns `dict(row.data)` wholesale,
so it works correctly.

Fix: add `"target_vocab": r.data.get("target_vocab", [])` (and optionally
`target_vocab_fr` after DB resolution) to the list response dict.

## Triage
- Explanation: In `app/assessment/api.py`, `list_tasks()` (lines 59–71) builds each task dict by hand, naming only `id`, `section`, `title`, `prompt`, `min_words`, and `max_words`. The `target_vocab` key is stored in `r.data` (sourced from the YAML, e.g. `section-a-food-letter.yaml` line 13) but is never forwarded. By contrast, `get_task()` (line 83) returns `dict(row.data)` wholesale, so it includes `target_vocab` along with `target_vocab_fr` from the DB lookup. The asymmetry is a plain omission in the list handler, not a design choice.
- Against spec: The spec (`TEF_Platform_Technical_Plan.md`) does not document the shape of the list response, so there is no explicit list of required fields. However, `target_vocab` is a first-class authoring field defined in every writing task YAML and exposed by the model (`app/assessment/models.py` line 27). The individual-task endpoint treats it as required output, which establishes the intent. No existing test for `list_tasks` asserts `target_vocab` (line 186-190 in `test_assessment.py` only checks `id` membership), meaning the gap has gone unchecked.
- Verdict: validated
- Rationale: A client building a task-selection screen — e.g. showing which vocabulary a writing task targets before the learner commits — needs `target_vocab` from the list. Having it on the detail endpoint only forces an extra round-trip per task, and the data is already present in `r.data`; omitting it is a straightforward oversight with real UX cost.

## Critic
- Challenge: The strongest case against fixing this is that list endpoints commonly return a projection — a deliberate subset of fields for performance and bandwidth reasons. A client that needs `target_vocab` to build a selection screen can call `GET /assessment/tasks/{task_id}` for each task; that is a valid REST pattern. The tech plan (`TEF_Platform_Technical_Plan.md`) does not enumerate the list-response shape at all, which means there is no spec violation. The `WritingTask` model (`app/assessment/models.py` line 27) defines `target_vocab` as an authored field but does not mandate it appear in the list response. The omission could be intentional: `list_tasks` only does a single DB query with no `ContentVocab` join, keeping it cheap. Including `target_vocab_fr` (the resolved form the grader actually uses) would require the same join that `get_task` performs via `_resolve_vocab_fr`, so the list and detail handlers are architecturally asymmetric by design. The raw `target_vocab` IDs (without resolution) are a partial inclusion that could mislead a client expecting the French surface forms.
- Holds up? Yes, the validation holds up. The asymmetry is code-level, not design-level: `list_tasks` is a hand-rolled dict that simply did not enumerate `target_vocab`, whereas `get_task` uses `dict(row.data)` wholesale — that is not a documented projection choice, it is inconsistency in how the two handlers were written. The `target_vocab` IDs (not the resolved FR forms) require no extra DB query — the data sits in `r.data` already loaded — so there is no performance argument to omit them. The model comment ("shown as a hint") confirms the intent is to surface this field to callers. The test at line 184-190 checks only `id` membership, so the gap was never caught. The UX cost is concrete: a task-list screen cannot show vocab hints without N extra round-trips. Medium severity is correct — submission and grading are unaffected, but a defined display feature is silently missing.
- Final verdict: validated

## Fix
Added `"target_vocab": r.data.get("target_vocab", [])` to the per-task dict in `list_tasks()` in `/Users/sirius/projects/multilingual/app/assessment/api.py`. No extra DB query required — the data is already loaded in `r.data`. All 20 assessment tests pass; ruff clean.
