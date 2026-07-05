---
id: 443
title: A1 grammar index omits 6 lessons — two units never synced to live DB
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-07-04
---

## Steps to reproduce
1. GET /content/grammar?level=a1 (with valid JWT)
2. Count items in the response
3. Compare against the lesson files in content/a1/lessons/ and the unit definitions in content/a1/path.yaml

## Expected
The grammar index for A1 should contain one item per A1 lesson that has a non-empty `grammar_point`. `content/a1/path.yaml` defines 12 units (36 lessons total); every lesson YAML in `content/a1/lessons/` has a `grammar_point`. Expected: 36 grammar items covering units a1.u1 through a1.u12.

## Actual
The response returned only 30 items — units a1.u1 through a1.u10. Units a1.u11 (Colours: couleurs-01/02/03) and a1.u12 (The body: corps-01/02/03) were completely absent. Confirming directly:
- `GET /content/lessons/couleurs-01` → 404 "lesson 'couleurs-01' not found"
- `GET /content/lessons/corps-01` → 404 "lesson 'corps-01' not found"
- `GET /content/path?level=a1` → 10 units (u1–u10 only), not 12

The YAML source files `content/a1/lessons/couleurs-01.yaml` through `couleurs-03.yaml` and `corps-01.yaml` through `corps-03.yaml` all exist and all have `grammar_point` set. The live database was never re-synced after these two units were added to path.yaml.

## Evidence
```
# Live grammar index — 30 items, stops at u10 (weather)
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:9000/content/grammar?level=a1" \
  | grep '"unit_id"' | sort -u
# Returns: a1.u1 through a1.u10 only

# path.yaml has 12 units:
grep "id: a1" content/a1/path.yaml
# a1.u1 ... a1.u10, a1.u11, a1.u12

# Lesson files exist:
ls content/a1/lessons/couleurs-01.yaml content/a1/lessons/corps-01.yaml
# both present, both have grammar_point

# Live lessons 404:
curl -s "http://127.0.0.1:9000/content/lessons/couleurs-01"
# {"detail":"lesson 'couleurs-01' not found"}
```

## Notes
The unit test (`test_grammar_endpoint_lists_points_in_path_order`) passes because it runs a fresh `sync_bundle` from the YAML source each test run — it sees all 12 units. The live server database was last synced when only 10 A1 units existed. A `content-sync a1` run is needed to bring the live DB up to date. The A2, B1, B2 levels appear consistent (A2: 12/12 units, B1: 10/10, B2: 10/10).

## Triage
- Explanation: The grammar endpoint (`GET /content/grammar`) reads `ContentUnit` and `ContentLesson` rows from the live SQLite DB. `content/a1/path.yaml` defines 12 units and all 12 unit directories exist with lesson YAML files, but the live DB was never re-synced after u11 (Colours) and u12 (The body) were added. The endpoint correctly serves what is in the DB; the DB is simply stale. The test passes because the test harness calls `sync_bundle` on every run against a fresh in-memory DB.
- Against spec: The spec mandates a content-sync step as part of go-live for any new content slice. Two A1 units were added to path.yaml without a corresponding `content-sync a1` run against the live DB.
- Verdict: validated
- Rationale: A learner who reaches unit 10 finds no further A1 content to unlock — units 11 and 12 are entirely absent from the API, the path, and the lesson endpoint. The fix is a `./start.sh content-sync a1` run against the live DB; no code change is needed, but the stale state must be corrected and the deploy checklist should require a sync step.

## Critic
- Challenge: The grammar endpoint and all surrounding code are correct — they faithfully serve whatever the DB contains. This is purely an ops/deploy omission: someone added content to YAML without running the sync command. One could argue this is out of scope for a code review because no line of code is wrong, and it is already detectable by anyone who looks at the live path endpoint (which shows 10 units) versus path.yaml (12 units). The code-review PR does not include a database artifact, so the PR itself is not broken.
- Holds up? Yes. The challenge collapses on a concrete user impact test: `GET /content/path?level=a1` returns 10 units and `GET /content/lessons/couleurs-01` returns 404 on the live server. I verified both the YAML source (12 units, all 6 new lesson files present with `grammar_point` set) and the test harness (calls `sync_bundle` on a fresh DB, so CI passes regardless of live DB state). The stale DB is a real, reproducible gap that blocks a learner from accessing 20% of the A1 curriculum. The tech plan explicitly names "a DB sync step" as part of content delivery (TEF_Platform_Technical_Plan.md line 175, 289). The fact that no code is wrong does not mean no action is needed — the sync is a required deploy artifact for this content slice.
- Final verdict: validated

## Fix
- Action: ran `/tmp/tef312/bin/python -m app.content.sync a1` against the live DB (round 035, 2026-07-04).
- Result: `synced level 'a1': 12 units, 36 lessons, 214 vocab, 238 audio files`
- Verification: `GET /content/grammar?level=a1` now returns 36 items; `GET /content/lessons/couleurs-01` returns 200; `GET /content/path?level=a1` shows 12 units.
- No code change required — the sync command was the fix.
