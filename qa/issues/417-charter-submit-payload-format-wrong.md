---
id: 417
title: QA charter documents wrong submit payload format — array vs dict causes 422
severity: medium
area: other
persona: exam-crammer
status: rejected
found: 2026-07-03
---

## Steps to reproduce
1. Open the QA charter (the instructions given to QA agents for round 030 comprehension testing).
2. Follow the documented payload format for POST /comprehension/sets/{set_id}/submit:
   ```json
   {
     "answers": [
       {"question_id": "read-b1-gig-economy.q1", "answer": "...", "elapsed_seconds": 45}
     ]
   }
   ```
3. Submit that payload to `POST http://localhost:8080/comprehension/sets/read-b1-gig-economy/submit`.
4. Receive HTTP 422 with `"msg": "Input should be a valid dictionary"`.

## Expected
The charter should document the actual API schema so that QA testers can reproduce test cases without debugging 422 errors. The correct format is a dict:
```json
{
  "answers": {
    "read-b1-gig-economy.q1": "Travailler librement, mais sans filet"
  },
  "elapsed_seconds": 120
}
```
(`elapsed_seconds` is a single top-level integer, not per-question; `answers` is a `{question_id: answer_string}` dict, not an array of objects.)

## Actual
The API returns HTTP 422:
```json
{"detail":[{"type":"dict_type","loc":["body","answers"],"msg":"Input should be a valid dictionary","input":[...]}]}
```
Any QA agent following the charter's example format verbatim will get a 422 and may not realise the format is wrong, wasting debugging time or falsely concluding grading is broken.

## Notes
- Confirmed via GET /openapi.json: `SubmitBody.answers` is `"type": "object"` with `"additionalProperties": {"type": "string"}`, not an array.
- `elapsed_seconds` is a nullable integer at the top level of `SubmitBody`, not inside each answer object.
- Fix: update the charter payload example to match the actual schema. This is a documentation/tooling issue, not a backend bug.

## Triage
- Explanation: `POST /comprehension/sets/{set_id}/submit` expects `SubmitBody` where `answers` is `"type": "object"` with `"additionalProperties": {"type": "string"}` (i.e. `{"question_id": "answer_string", ...}`) and `elapsed_seconds` is a nullable integer at the top level. The wrong example documented an array of per-question objects with an embedded `elapsed_seconds` per element. Submitting the array format returns HTTP 422 `"Input should be a valid dictionary"`. Confirmed via `GET /openapi.json` components/schemas/`app__comprehension__api__SubmitBody`.
- Against spec: The OpenAPI spec (the authoritative contract) unambiguously defines `answers` as an object, not an array. The round 030 charter (`qa/rounds/030-plan.md`) contains no payload example at all — it describes tests in prose only — so the wrong format was not introduced by any committed document. The bad example exists only in the tester's prompt or out-of-band instructions, which are ephemeral and not in the repo. However, the absence of any committed payload example is itself the gap: QA agents have no on-disk reference to copy from, making format errors likely on every comprehension-grading round.
- Verdict: validated
- Rationale: The wrong payload format is real and blocks correct execution of H2, H6, and H7 for any tester who relies on a provided example. The fix is low-effort and high-leverage — add a canonical correct payload snippet to `qa/rounds/TEMPLATE.md` (or an equivalent reference doc) so all future charters inherit it. User impact: without a fix, QA testers will continue hitting 422 errors and may misdiagnose grading as broken rather than recognising a documentation gap.

## Critic
- Challenge: The PM's own Triage notes concede the critical fact: the round 030 charter (`qa/rounds/030-plan.md`) contains no payload example at all — no wrong example was ever committed to the repo. The "bad example" lived only in an ephemeral, out-of-band tester prompt that is not tracked, not version-controlled, and not the application under test. This issue therefore describes a defect in oral/ephemeral QA instructions, not in any committed artifact. Three further points undercut the validated verdict. First, the issue tracker exists for application defects; this is a process/tooling complaint about how the planner briefed testers, which belongs in a retrospective note or a one-time planner correction, not a tracked issue. Second, the API itself behaves correctly: the 422 with an array payload is the right response per the OpenAPI contract, and the OpenAPI spec was always accurate. Nothing in the application is broken. Third, zero test cases were actually lost: both testers in round 030 still arrived at the correct payload format (one filed this issue after consulting the OpenAPI spec, which is exactly the intended fallback), and no hypothesis was left untested due to this gap. The PM's proposed fix — adding a payload example to `qa/rounds/TEMPLATE.md` — would not have prevented the problem either, because the wrong format appeared in an ephemeral planner prompt, not in a document derived from the template. Adding it to the template is a nice-to-have but it does not close the actual failure mode (planners writing their own ad-hoc payload examples in prompts).
- Holds up? No. The PM validated a meta/process issue as though it were an application defect. The application is working correctly; no committed document contained wrong information; no test was blocked; the 422 is by-design. The only genuine gap is an absence of a canonical reference in committed documents, which is a planner-discipline question, not a bug. Under the team rule ("fix only what is actually an issue"), this does not qualify.
- Final verdict: rejected
