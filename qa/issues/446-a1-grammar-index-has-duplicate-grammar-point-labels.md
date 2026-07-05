---
id: 446
title: A1 grammar index shows identical grammar_point labels for consecutive lessons
severity: low
area: content
persona: edge-case-breaker
status: deferred
found: 2026-07-04
---

## Steps to reproduce
1. GET /content/grammar?level=a1 with a valid JWT
2. Scan the returned items for duplicate `grammar_point` values

## Expected
A grammar reference index is meant to help users find where each grammar topic is taught. Duplicate labels make the index ambiguous — a user cannot distinguish which lesson to open for each topic.

## Actual
Three grammar_point values appear twice each in the A1 grammar index:

| Duplicated grammar_point | Lesson 1 | Lesson 2 |
|---|---|---|
| "cardinal numbers" | numbers-01 | numbers-02 |
| "« combien ça coûte ? »" | shopping-01 | shopping-02 |
| "« il fait… » for weather" | weather-01 | weather-03 |

## Evidence
```
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:9000/content/grammar?level=a1"

# In the response:
# numbers-01: "grammar_point":"cardinal numbers"
# numbers-02: "grammar_point":"cardinal numbers"   ← duplicate
# shopping-01: "grammar_point":"« combien ça coûte ? »"
# shopping-02: "grammar_point":"« combien ça coûte ? »"  ← duplicate
# weather-01: "grammar_point":"« il fait… » for weather"
# weather-03: "grammar_point":"« il fait… » for weather"  ← duplicate
```

Also present in A2: "« prendre » + transport" for both transport-a2-01 and transport-a2-02, and "« je pense que… »" for sentiments-a2-01 and sentiments-a2-03.

## Notes
This is a content-authoring issue, not a system bug. The endpoint correctly returns what is in the YAML. The `grammar_point` fields in the lesson YAML files for the duplicate pairs should be differentiated (e.g., numbers-02 could say "cardinal numbers 6–10" to match its lesson scope). Low severity because the index still functions; the duplicate entries are unhelpful but not broken.

## Triage
- Explanation: The endpoint reads `grammar_point` verbatim from the lesson YAML data stored in the DB. The duplicate strings originate in the YAML source files: `numbers-02.yaml`, `shopping-02.yaml`, and `weather-03.yaml` each carry the exact same `grammar_point` string as their unit-sibling lessons. The endpoint has no deduplication logic and is not expected to have any — it exposes what the content authors wrote.
- Against spec: Unspecified. The spec describes the grammar index as "every grammar point taught," which implies distinct topics. Two lessons teaching the same named grammar point is not a system defect; it is a content quality issue. The endpoint behaviour is correct.
- Verdict: deferred
- Rationale: Real but out of scope for this slice; the fix is purely editorial — differentiate the `grammar_point` labels in the YAML source files (e.g., "cardinal numbers 1–5" vs "cardinal numbers 6–10"). No code change needed. Deferring to a content-polish pass rather than blocking the current grammar endpoint work.

## Critic
- Challenge: The strongest push toward validating this: the Grammar.tsx screen is a "browsable reference" that groups by unit but shows grammar_point as the primary label. If two consecutive entries in the same unit show the same label text ("cardinal numbers" / "cardinal numbers"), a learner has no way to distinguish which lesson to open. This is the UI's primary use-case — lookup by topic — and duplicates directly break that use-case. It is not merely cosmetic. Furthermore, fixing three YAML files is a genuinely small change: s/"cardinal numbers"/"cardinal numbers 1–5"/ in numbers-01 and s/"cardinal numbers"/"cardinal numbers 6–10"/ in numbers-02, with similar edits for shopping and weather. This costs less than 15 minutes and would prevent the PR from shipping a reference tool that is confusing at first use. The PM called it "content quality"; one could equally call it an authoring defect that makes the feature less useful than its charter goal.
- Holds up? Yes, with one important caveat: I confirmed the duplicates are real (numbers-01.yaml and numbers-02.yaml both have `grammar_point: "cardinal numbers"`; same pattern for shopping and weather). However, the severity is correctly assessed as low. The grammar index is still usable — both entries link to different lesson_ids (numbers-01 vs numbers-02), so a learner who clicks either link reaches the correct lesson. The disambiguation is at lesson_id level, not label level. The feature is not broken; it is merely imprecise. Deferral is appropriate: the cost of making this blocking is that an editorial-only change delays a code-correct PR. The PM's deferred verdict and rationale are sound. The graver concern (issue 443 stale DB) is already validated and will likely be synced together with these files anyway, so a content-polish pass is the right vehicle.
- Final verdict: deferred
