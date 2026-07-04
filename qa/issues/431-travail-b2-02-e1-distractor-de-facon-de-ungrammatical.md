# Issue 431 — travail-b2-02.e1 MCQ distractor "de façon de" is ungrammatical French

- status: fixed
- severity: low
- persona: exam-crammer
- area: content / grammar
- round: 033

## Steps to reproduce
Read `/Users/sirius/projects/multilingual/content/b2/lessons/travail-b2-02.yaml`, exercise e1.

MCQ prompt: "« Il faut reconnaître le travail ___ que les employés restent motivés. »"
Options: ["de sorte", "de façon de", "afin de"]
Answer: "de sorte"

## Expected
All distractors should be grammatically possible in isolation (wrong only because of context), so that elimination requires applying the rule — not simply spotting a non-existent form. Standard French uses:
- "de façon **à**" + infinitive (same subject)
- "de façon **que**" + subjonctif (different subjects)

"De façon **de**" + infinitive does not exist in French grammar.

## Actual
"De façon de" is a non-existent construction in French. A test-taker can eliminate it purely by recognising it as ungrammatical — without ever applying the lesson's grammar point about "de sorte que" vs "de manière à". This leaks knowledge of elimination by surface form rather than by rule application.

The settle note for issue 429 covers MCQ distractors of a similar type (ungrammatical cause preposition). This issue covers a parallel case in travail-b2-02 which was not part of that fix.

## Evidence
```yaml
# travail-b2-02.yaml, exercise e1
type: mcq
prompt: "« Il faut reconnaître le travail ___ que les employés restent motivés. »"
options: ["de sorte", "de façon de", "afin de"]
answer: "de sorte"
explain: "« De sorte que » + subjonctif exprime le résultat que l'on cherche à obtenir."
# "de façon de" is not a valid French construction.
# Should be replaced with "de façon que" (valid but requires subjonctif — a plausible distractor)
# or "de manière de" can remain if kept as a clearly wrong choice, but "de façon que"
# would be a stronger distractor that requires rule knowledge to reject.
```

## Triage

- verdict: validated
- rationale: The YAML confirms the three MCQ options are ["de sorte", "de façon de", "afin de"]. "De façon de" is not a valid French construction — standard French uses "de façon à" + infinitive (same subject) or "de façon que" + subjonctif (different subjects). "De façon de" does not exist. This is the same class of defect identified and fixed in issue 429: an ungrammatical distractor that can be eliminated by surface recognition alone, bypassing the lesson's actual grammar point ("de sorte que" vs "de manière à"). The existing distractor "afin de" is a legitimate near-miss (valid construction, same-subject infinitive, wrong here because subjects differ), so the MCQ already has one strong distractor. Replacing "de façon de" with "de façon que" would give a second strong distractor — a learner must know that "de façon que" takes the subjonctif and that both "de sorte que" and "de façon que" are grammatically possible here, requiring genuine rule application to choose the correct fill-in. The fix is a one-line YAML change. Severity low is appropriate given the MCQ remains answerable via the valid "afin de" distractor, but the ungrammatical option is still a content quality issue that should be corrected before the lesson ships.

## Critic

- final_status: validated
- rationale: I verify the YAML directly: travail-b2-02.e1 options are ["de sorte", "de façon de", "afin de"]. "De façon de" is not a French construction — the language has "de façon à" (+ infinitive, same subject) and "de façon que" (+ subjonctif, different subjects); "de façon de" does not appear in any register of French. This is precisely the issue-429 defect class: an ungrammatical filler that a test-taker eliminates by surface form recognition rather than by applying the target grammar rule. Unlike issue 430, the fix here is unambiguous: replace "de façon de" with "de façon que". That produces a strong distractor — "de façon que" is grammatically valid, takes the subjonctif like "de sorte que", and is wrong in this slot only because the prompt's blank is followed by "que" already (making "de façon que" produce "de façon que que"), which requires the learner to notice the structural clash. Alternatively, "de façon à" would work as a distractor testing the subject-coreference rule. Either replacement is a one-token YAML change with no downstream ambiguity. The Triage verdict, severity, and proposed fix are all sound. I sign off: clear for dev-fixer.

