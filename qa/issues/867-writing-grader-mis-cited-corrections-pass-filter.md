---
id: 867
title: Writing grader's curated-reference filter catches uncited hallucinations but lets mis-cited ones through
severity: medium
area: writing
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Same setup as issue 866 (signup, real task_ids, hand-written submissions mixing
   grammar + lexical errors, submitted via `POST /assessment/tasks/<task_id>/submit`).
2. Read every surviving `corrections` entry and check whether the cited `reference`
   key actually describes the grammatical phenomenon in the `excerpt`/`correction` pair.

   b1 (`write-b1-cover-letter`), submitted text (127 words) contains: "**Je suis très
   intéressant par ce poste**" (should be "intéressé(e)" — a classic
   intéressant/intéressé false-friend/adjective-choice mistake, not a subject-verb
   agreement issue — "je suis" already correctly agrees in person/number).
   Returned correction:
   ```json
   {
     "excerpt": "Je suis très intéressant par ce poste",
     "correction": "Je suis très intéressé(e) par ce poste",
     "explanation": "Agreement error; use 'intéressé(e)' to match gender.",
     "reference": "accord-sujet-verbe"
   }
   ```
   `accord-sujet-verbe` is the wrong curated key — this is not a subject/verb mismatch.

   b2 (`write-b2-ecology`), submitted text (267 words) contains the *same* intéressant/
   intéressé mistake. This time the grader cited `"reference": "accord-genre-nombre"`
   for the identical error type — a different (more defensible, though still debatable)
   key than the b1 submission got for the same linguistic phenomenon, showing the
   citation is not even internally consistent run-to-run.

   b1 (`write-b1-environment`), submitted text (206 words) contains "**les gouvernements
   doit** aussi agir" (plural subject + singular verb — a present-tense
   subject-verb-agreement error, not a tense error). Returned correction:
   ```json
   {
     "excerpt": "les gouvernements doit aussi agir",
     "correction": "les gouvernements doivent aussi agir",
     "explanation": "Use of the correct verb form 'doivent'.",
     "reference": "temps-passe"
   }
   ```
   `temps-passe` ("past tense") is clearly the wrong key — no tense is changing here
   (présent -> présent); the actual phenomenon is `accord-sujet-verbe`.

   b2 (`write-b2-health-letter`), submitted text (155 words) — the grader also proposed
   a correction for "postes d'infirmiers" -> "postes d'infirmières" citing
   `accord-genre-nombre`, but the original text did not actually contain a gender
   agreement error: "infirmiers" is a standard generic masculine plural for a mixed
   group of nurses, so this "correction" is itself a plausible-sounding but unneeded
   edit that nonetheless carries a technically-curated reference key and so survives
   the `_is_genuine` filter.

## Expected
A correction's cited `reference` should describe the actual grammatical rule being
applied. A learner shown "reference: accord-sujet-verbe" for an adjective-choice error,
or "reference: temps-passe" for a present-tense subject/verb mismatch, is given a
wrong mental model of what was fixed and why.

## Actual
3 of 6 real-LLM-call submissions produced at least one correction whose cited
`reference` key is in the curated set (so passes `_is_genuine`) but does not actually
match the grammatical phenomenon of the excerpt/correction pair, including one
instance of an apparently unneeded "fix" to text that wasn't actually wrong.

## Notes
This is the H6 hypothesis from `qa/rounds/059-plan.md`. Root cause (code-read,
`app/assessment/grader.py::_is_genuine`): the filter only checks `c.reference in
GRAMMAR_REFERENCES and c.correction.strip() != c.excerpt.strip()` — it has no way to
verify the cited reference actually matches the excerpt/correction pair, so a
plausible-sounding but wrong (or outright invented/unneeded) citation passes exactly
as easily as a correct one, as long as the model picks a key from the curated list.
This was flagged as a known residual risk in issue 831's own fix notes ("a rewrite
the model tags with a wrong rule still gets through") — this report supplies 3 fresh,
reproducible instances of that class in text none of which were the original 831
repro example.

## Triage
- Explanation: confirmed by code read — `_is_genuine` (new in 686cebd) checks only
  `c.reference in GRAMMAR_REFERENCES and c.correction.strip() != c.excerpt.strip()`;
  it has no semantic check that the cited key actually matches the excerpt/correction
  pair, so a plausible-but-wrong citation (intéressant/intéressé tagged
  `accord-sujet-verbe` or `accord-genre-nombre` inconsistently; "doit"→"doivent"
  tagged `temps-passe` instead of `accord-sujet-verbe`) passes exactly as easily as a
  correct one. The "infirmiers"→"infirmières" example is slightly different in kind —
  it's a correction on text that wasn't wrong at all (generic masculine plural),
  which is actually a recurrence of 831's *original* bug class (inventing a
  correction on correct French) that happens to land on a technically-curated key, not
  purely a mis-citation of a real error.
- Against spec: 831's own Fix section explicitly disclosed this exact residual
  ("a rewrite the model tags with a wrong rule still gets through") and recorded it
  as unresolved after trying and rejecting three mitigations (telling the model
  uncited corrections are discarded, a second correct-text anchor, a judge-only
  verifier pass) — none shipped because benched results showed they didn't help
  enough (one kept 7/22 fakes while losing 6/22 real corrections, and added 2.3s of
  latency). The reported bench numbers (spurious corrections 12→4 per sample) imply a
  non-zero residual rate was known and accepted at ship time, not believed fixed.
- Verdict: deferred
- Rationale: real, reproducible, learner-trust-damaging — a learner shown a
  plausible-sounding wrong rule for a real error (or an invented "fix" to correct
  text) gets a wrong mental model. But this report is confirming the known,
  explicitly-disclosed residual with fresh instances in new text (which the round
  plan explicitly permits refiling), not a new class of defect — and the PR's own Fix
  section shows three concrete mitigation attempts were already tried and benched
  before shipping, concluding that fully closing this gap "needs a stronger grader
  model." That's a larger undertaking than a surgical rule patch (850/851/866's fixes
  are a few lines each); `_is_genuine` can't gain semantic verification of a citation
  without another model call or a materially better model. Route to a dedicated round
  scoped to grader-model quality (e.g. evaluate a bigger/different model for the
  `writing_feedback` profile) rather than attempting another quick patch to the
  curated-reference filter.

## Critic
- Challenge: is the line pm drew between 866 (validated) and 867 (deferred)
  principled, or just convenient? Both are symptoms of the same `_is_genuine`
  filter being too blunt (checks membership, not meaning) — worth checking
  whether 867 deserves the same "add a key" style of surgical fix rather than
  being waved off as "needs a stronger grader model."
- Holds up? Yes, the line is real, not just convenient. 866's fix is mechanical:
  add a `vocabulaire` key to a set and a prompt list — zero model-quality
  improvement required, since the filter only ever checked *membership*, and a
  lexical correction currently has no legal member to cite. 867's defect is
  categorically different: the model already picks a key that IS in the set, so
  no key addition changes anything — fixing it requires the model (or an
  additional LLM call) to correctly judge *which* curated rule actually matches
  the excerpt/correction pair, which is a semantic-verification problem, not a
  membership-set gap. Checked 831's own Fix section (read above): it explicitly
  tried and benched three mitigations aimed at exactly this problem (telling the
  model uncited corrections are discarded, a second correct-text anchor, a
  judge-only verifier pass) and rejected all three because they didn't help
  enough (one kept 7/22 fakes while losing 6/22 real corrections, +2.3s latency)
  — this is real, already-spent engineering effort on this exact issue, not an
  untried hand-wave. The "infirmiers"→"infirmières" example in this report is
  correctly flagged by pm as a recurrence of 831's *original* bug class (a
  plausible-sounding correction on already-correct text) rather than a pure
  mis-citation — that distinction holds on inspection and doesn't change the
  overall verdict either way, since both sub-classes point at the same
  "needs better judgment, not a bigger list" root cause.
- Final verdict: deferred

## Fix
Hid the curated-reference pill (📘 accord-sujet-verbe…) from the Corrections list in `web/src/screens/WritingTask.tsx`. The key still drives the `_is_genuine` filter, but it's no longer shown to the learner as "the rule", which is where a mis-cited key did the harm. Residual: the model's free-text `explanation` can still mis-state the rule (e.g. "Agreement error" for intéressant→intéressé), and an invented fix on correct text that cites a curated key still gets through. Closing that needs a stronger grader model (see 831).
