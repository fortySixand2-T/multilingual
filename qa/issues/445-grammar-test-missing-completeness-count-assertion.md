---
id: 445
title: Grammar test does not assert item count matches lessons-with-grammar-point in path
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-07-04
---

## Steps to reproduce
1. Open `tests/test_content_sync.py`, function `test_grammar_endpoint_lists_points_in_path_order`
2. Read what the test actually checks

## Expected
The grammar completeness test (H2) should verify that the count of items returned equals the number of lessons in the path that have a non-empty `grammar_point` field. This ensures the endpoint does not silently omit lessons.

## Actual
The test checked:
1. That items are non-empty (`assert items`)
2. That every returned item has a non-empty `grammar_point`
3. That returned items appear in unit-ordinal order

It did NOT check that the count of returned items equals the number of path-lessons with non-empty grammar_point. A bug that filters out some lessons (e.g., only returning the first lesson per unit, or skipping lessons whose IDs do not match some pattern) would cause the test to pass silently.

## Evidence
From `tests/test_content_sync.py` lines 151–167 (before fix):
```python
def test_grammar_endpoint_lists_points_in_path_order():
    body = client.get("/content/grammar", params={"level": "a1"}).json()
    ...
    items = body["items"]
    assert items and all(i["grammar_point"].strip() for i in items)
    # ordering check only; no count check
    seq = [order[i["unit_id"]] for i in items]
    assert seq == sorted(seq)
```

The running live server demonstrates the real-world impact: the live DB is stale (A1 has 10 units in the DB, 12 in path.yaml), so `len(items) == 30` rather than the expected 36. The test passes with 30 items because it has no count assertion (it runs against a fresh test DB that correctly has all 36, but even the test DB result of 36 is never asserted).

## Notes
This is a test coverage gap, not a behavior bug in the production code logic itself. The production logic at `app/content/api.py` is correct — it iterates `unit.lessons` and filters by `grammar_point`. The related live-server data bug is filed separately as issue 443.

## Triage
- Explanation: `test_grammar_endpoint_lists_points_in_path_order` in `tests/test_content_sync.py` (lines 151–167) checks that items are non-empty, that each has a non-empty `grammar_point`, and that they appear in unit-ordinal order. It does not assert `len(items) == <expected>`. Because the test DB is always freshly synced from YAML, it has all 36 A1 items and the test passes — but the test cannot detect a silent filtering regression (e.g., only first lesson per unit, or skipping lessons with certain ID patterns). This is directly evidenced by the live-DB stale-data situation in issue 443 going undetected at the test level.
- Against spec: The charter for round 035 required two grammar tests covering H1 (happy-path) and H2 (completeness). The H2 test as written does not actually assert completeness (item count). The count assertion is the load-bearing part of H2.
- Verdict: validated
- Rationale: Without a count assertion, any bug that silently drops a subset of grammar lessons (sync regression, filtering error) passes CI undetected; adding `assert len(items) == expected_count` is a small, safe change that closes the gap and makes issue 443 detectable in CI.

## Critic
- Challenge: The PM links this test gap directly to the issue-443 stale-DB situation, but that link is misleading. The test runs against a freshly-synced in-memory DB — it would return 36 items whether or not a count assertion exists, because `sync_bundle` correctly loads all YAML content. A count assertion in CI would NOT have caught the live-DB staleness in issue 443 (the test DB is always fresh). The gap the PM describes — "a bug that silently drops a subset of grammar lessons" — is a hypothetical code regression, not an observed defect. The existing checks (non-empty, all items have grammar_point, ordering is monotone) do catch the most likely regressions. The H2 charter hypothesis was about "lessons without grammar_point still appearing OR lessons WITH grammar_point being omitted" — the current test's `all(i["grammar_point"].strip() for i in items)` check addresses the former; the latter requires a count. However, the expected count would need to be hardcoded (36) or derived by parsing YAML from the test, both of which introduce brittleness. The PM also cited CLAUDE.md principles of simplicity — a count assertion is genuinely small, but the hardcoded 36 becomes a silent lie the moment a new lesson is added without updating the test.
- Holds up? Narrowly yes, but the PM overstates the case. The fix is real and worth making, but the expected_count should be computed dynamically (count lessons with grammar_point from the loaded content bundle) rather than hardcoded — otherwise the "fix" trades one class of silent failure for another. The core PM verdict is sound: the H2 charter explicitly named completeness/count as the probe, and the test does not assert it. The fact that the test DB is fresh means the count assertion will reliably pass in CI and will correctly fail if filtering logic regresses. The misleading framing around issue 443 does not undermine the underlying validity of the gap.
- Final verdict: validated

## Fix
- Added a count assertion to `test_grammar_endpoint_lists_points_in_path_order` in `tests/test_content_sync.py` (lines 168–176).
- The expected count is derived dynamically from `load_content(CONTENT_ROOT, "a1")` — not hardcoded — so the assertion stays correct as new lessons are added:
  ```python
  bundle = load_content(CONTENT_ROOT, "a1")
  expected = sum(
      1
      for unit in bundle.path.units
      for lid in unit.lessons
      if (lesson := bundle.lessons.get(lid)) and lesson.grammar_point.strip()
  )
  assert len(items) == expected
  ```
- Verification: `pytest tests/test_content_sync.py -q` → 23 passed, 1 warning. All tests green.
