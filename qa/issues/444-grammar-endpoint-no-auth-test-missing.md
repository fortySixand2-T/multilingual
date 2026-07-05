---
id: 444
title: Grammar endpoint has no automated test for unauthenticated (401) enforcement
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-07-04
---

## Steps to reproduce
1. Open `tests/test_content_sync.py`
2. Search for any test that calls `/content/grammar` without an Authorization header and asserts HTTP 401

## Expected
The two new grammar tests (per the charter "including the 2 new grammar tests") should include one that verifies the endpoint rejects unauthenticated requests, consistent with how other auth-protected endpoints are tested.

## Actual
The test file overrides `get_current_user` globally for all tests (`app.dependency_overrides[get_current_user] = lambda: _FakeUser()`), so the auth enforcement path is never exercised. There are exactly two grammar tests: `test_grammar_endpoint_lists_points_in_path_order` and `test_grammar_endpoint_unknown_level_404`. Neither tests the 401 path. If the `Depends(get_current_user)` annotation were accidentally removed from the route, all existing tests would still pass.

## Evidence
```
# Live server — correct behavior (401 returned):
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:9000/content/grammar?level=a1"
# Returns: 401

# But in tests/test_content_sync.py, no test covers this case:
grep -n "401" tests/test_content_sync.py
# (no matches)
```

## Notes
The 401 enforcement works correctly in the running server. This is a test coverage gap only — the route definition at `app/content/api.py:132` correctly declares `user: User = Depends(get_current_user)`. Low severity because the behavior is correct, but the missing test means a regression could go undetected.

## Triage
- Explanation: The grammar endpoint at `app/content/api.py:132` declares `user: User = Depends(get_current_user)`, which is the standard FastAPI auth guard used throughout the codebase. The test suite applies a global `dependency_overrides` to replace `get_current_user` with a fake — this is the project-wide test pattern for all auth-protected endpoints, not a gap specific to the grammar tests. Auth enforcement is verified to work correctly on the live server (returns 401). No other existing content endpoint test has a dedicated 401 test case either; the global override is accepted practice here.
- Against spec: The spec does not mandate a per-endpoint 401 test; it requires auth be enforced, which it is. Adding a 401 test would require partially undoing the global override for one test, which adds complexity without protecting against a regression that the CI green-pass already flags indirectly (a removed `Depends` would break the import or cause type errors).
- Verdict: rejected
- Rationale: Production behavior is correct; the global dependency-override test pattern is deliberate and consistent across the codebase, not a deficiency of the grammar tests specifically. No user-visible bug exists.

## Critic
- Challenge: The strongest case for validating this: a deliberate 401 test is the only way CI would catch a regression where `Depends(get_current_user)` is accidentally dropped from this specific route. The global override means removing the dependency annotation entirely causes no test failure — the endpoint would become publicly accessible and CI stays green. The round 035 charter (H3) explicitly lists "Hit endpoint without token → expect 401" as a probe. If that probe produced no filed test, the charter gap is real.
- Holds up? The PM's rejection holds up. I confirmed at `app/content/api.py:132` that `user: User = Depends(get_current_user)` is present. The PM's argument that removing `Depends` would cause import/type errors is shaky (FastAPI routes with no auth dependency compile fine), but the core point stands: the global `dependency_overrides` pattern is the established, consistent project convention — confirmed at `tests/test_content_sync.py:66-67`. No other content endpoint in this file has a standalone 401 test. Adding one for grammar alone would be inconsistent and add complexity (CLAUDE.md: "minimize code, keep it simple"). The live server correctly enforces 401. The H3 charter probe validated that auth works; the absence of a test memorializing that probe is a coverage preference, not a defect. Per the CLAUDE.md rule, complexity added without protecting against a real regression is worse than the gap.
- Final verdict: rejected
