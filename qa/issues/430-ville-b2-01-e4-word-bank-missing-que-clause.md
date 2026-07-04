# Issue 430 — ville-b2-01.e4 word_bank teaches truncated "d'autant plus" without "que" clause

- status: fixed
- severity: medium
- persona: exam-crammer
- area: content / grammar
- round: 033

## Steps to reproduce
Read `/Users/sirius/projects/multilingual/content/b2/lessons/ville-b2-01.yaml`, exercise e4.

Prompt: "Build: 'Housing is expensive, all the more so in the city centre.'"
Tokens: [le, logement, est, cher, "d'autant", plus, au, centre-ville, aussi]
Answer: [le, logement, est, cher, "d'autant", plus, au, centre-ville]

Resulting French sentence: **"Le logement est cher, d'autant plus au centre-ville."**

## Expected
The grammar point taught in ville-b2-01 is **"d'autant plus … que"** — a two-part structure where the second member introduces the cause: "d'autant plus X **que** Y". A complete example would be "Le logement est cher, d'autant plus **au centre-ville que** la demande y est forte." or the canonical form "Le logement est d'autant plus cher **que** la demande est forte."

The target sentence should include a "que" clause, or the answer should be explicitly flagged as an elided/anaphoric variant with a note explaining when truncation is acceptable.

## Actual
The word_bank omits "que" entirely, producing a sentence where "d'autant plus" hangs without a cause clause. This is colloquially acceptable in spoken French when the cause is implicit from prior discourse, but at B2 level the exercise should teach the full canonical structure "d'autant plus … que" rather than the truncated form, especially since ville-b2-01.e1 correctly demonstrates the full structure ("d'autant plus fréquents **que** la ville est dense").

There is also no `explain` field on the word_bank exercise to alert the learner to this nuance.

## Evidence
```yaml
# ville-b2-01.yaml, exercise e4
type: word_bank
prompt: "Build: "Housing is expensive, all the more so in the city centre.""
tokens: [le, logement, est, cher, "d'autant", plus, au, centre-ville, aussi]
answer: [le, logement, est, cher, "d'autant", plus, au, centre-ville]
# → "Le logement est cher, d'autant plus au centre-ville."
# Missing "que <cause>" — contradicts the grammar point of the lesson.
```

## Triage

- verdict: validated
- rationale: The YAML confirms that e4's answer produces "Le logement est cher, d'autant plus au centre-ville" — with no "que" clause. The elliptic anaphoric use of "d'autant plus" (without "que") is grammatically acceptable in French when the cause is recoverable from discourse context, and the English prompt "all the more so in the city centre" is itself an elliptic form with no explicit "because", so the two sentences are structurally parallel. However, the lesson's declared grammar_point is "d'autant plus … que" and e1 teaches the full two-part structure with an explicit explain field. Presenting the truncated form in e4 without any explain note creates a genuine pedagogical inconsistency: a B2 exam crammer learning this lesson could reasonably conclude that "que" is optional in all contexts, which would cost marks on a TEF writing task where the full structure is expected. The severity rating of medium is appropriate. The minimum fix is to add an explain field to e4 noting that this is the anaphoric/elided variant acceptable when the cause is contextually implicit; an alternative fix is to extend the token set and answer to include a "que" clause, fully modelling the canonical structure in at least one productive exercise.

## Critic

- final_status: deferred
- rationale: The YAML is confirmed: e4 produces "Le logement est cher, d'autant plus au centre-ville" — no "que" clause, no explain field. The core concern is real: the lesson's declared grammar_point is "d'autant plus … que" (the two-part causal intensifier), e1 correctly drills the full structure with an explicit explain, and e4 then silently uses the elided form without flagging the deviation. The English prompt is itself anaphoric ("all the more so"), so the translation is not wrong — but the problem is pedagogical framing, not grammatical correctness. However, I part from the Triage verdict of validated and instead defer this issue. The reason: the two fixes proposed (add an explain field, or rewrite e4 to include a "que" clause) pull in opposite directions — one normalises the truncated form, the other replaces it — and neither is a trivially safe one-liner. Extending the token set to add a full "que <cause>" clause requires inventing a plausible cause phrase not currently in the exercise, which risks introducing new content that needs independent review. Adding an explain field that says "truncation is acceptable when context is implicit" is accurate, but it may actually compound the risk for an exam crammer who then generalises too freely. This issue needs a content author decision on which form e4 should teach, not a mechanical fix. It should be reopened with a specific authorial directive before the dev-fixer touches it.

