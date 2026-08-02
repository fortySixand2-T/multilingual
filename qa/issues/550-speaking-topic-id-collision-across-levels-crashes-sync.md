---
id: 550
title: Speaking topic id collision across levels crashes sync_topics with unhandled IntegrityError
severity: medium
area: speech
persona: edge-case-breaker
status: deferred
found: 2026-08-01
---

## Steps to reproduce
1. `SpeakingTopicRow` (`app/speech/tables.py`) declares a bare global primary key:
   `id: Mapped[str] = mapped_column(String(64), primary_key=True)` — not scoped by
   `level`.
2. `sync_topics(session, content_root, level)` (`app/speech/topics.py`) does a
   delete-and-replace that is scoped to a single level only:
   `delete(SpeakingTopicRow).where(SpeakingTopicRow.level == level)`, then inserts
   all topics loaded for that level.
3. Author two topic YAML files under different levels that happen to share the
   same `id`, e.g.:
   - `<root>/a1/speaking/x.yaml`:
     ```yaml
     id: collide-topic
     level: a1
     section: A
     title: Test A1
     prompt: Prompt A1
     points: []
     ```
   - `<root>/a2/speaking/x.yaml`:
     ```yaml
     id: collide-topic
     level: a2
     section: A
     title: Test A2
     prompt: Prompt A2
     points: []
     ```
4. Against an isolated scratch SQLite DB (via `Base.metadata.create_all`, same
   pattern as `tests/test_speaking_topics.py`), call, in order:
   - `await sync_topics(session, root, "a1")` — succeeds, inserts 1 topic.
   - `await sync_topics(session, root, "a2")` — the a1 row for `collide-topic` is
     untouched (delete was scoped to `level == "a2"`), so the insert of the a2 row
     with the same `id` hits the primary-key uniqueness constraint.

Minimal repro script used (run with the project's Python env against a scratch
tempdir DB and content root — does **not** touch the live app's shared DB):

```python
import asyncio, tempfile
from pathlib import Path
import yaml
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import app.speech.tables  # noqa: F401
import app.usage.models  # noqa: F401
from app.speech.topics import sync_topics
from app.users.models import Base

DB_URL = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/topics_collision.db"
engine = create_async_engine(DB_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)

def write_topic(root, level, name, doc):
    d = root / level / "speaking"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    root = Path(tempfile.mkdtemp())
    write_topic(root, "a1", "x", {"id": "collide-topic", "level": "a1", "section": "A",
                                   "title": "Test A1", "prompt": "Prompt A1", "points": []})
    write_topic(root, "a2", "x", {"id": "collide-topic", "level": "a2", "section": "A",
                                   "title": "Test A2", "prompt": "Prompt A2", "points": []})
    async with Session() as session:
        n1 = await sync_topics(session, root, "a1")
        print(f"sync a1 ok: {n1} topics")
    async with Session() as session:
        n2 = await sync_topics(session, root, "a2")  # raises
        print(f"sync a2 ok: {n2} topics")

asyncio.run(main())
```

## Expected
Either: (a) topic ids are enforced/validated to be globally unique at
load/sync time with a clean, actionable error (e.g. `TopicError`, the way
`load_keyed_yaml`'s `duplicate_error` already handles in-level duplicates), or
(b) the schema allows the same `id` to exist independently per level (e.g. a
composite primary key `(id, level)`), so authoring a same-named id in two
levels doesn't crash the sync job.

## Actual
The second `sync_topics` call raises an unhandled
`sqlalchemy.exc.IntegrityError` (`UNIQUE constraint failed:
speaking_topics.id`), which propagates out of `sync_topics` uncaught. Actual
traceback tail from the repro run:

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: speaking_topics.id
[SQL: INSERT INTO speaking_topics (id, level, section, data) VALUES (?, ?, ?, ?)]
[parameters: ('collide-topic', 'a2', 'A', '{"id": "collide-topic", "level": "a2", "section": "A", "title": "Test A2", "prompt": "Prompt A2", "points": []}')]
  File "app/speech/topics.py", line 85, in sync_topics
    await session.commit()
```

`sync a1 ok: 1 topics` printed first, confirming the a1 sync succeeded and its
row was left in place (not deleted) when the a2 sync ran and collided with it.

## Notes
- This is a **medium**-severity latent authoring-time trap, not active data
  corruption: today's real content under `content/<level>/speaking/*.yaml` is
  safe because every authored id happens to be level-prefixed by convention
  (e.g. `speak-a1-a-restaurant`), so no collision currently occurs against the
  live DB. This was verified against an isolated scratch SQLite DB + scratch
  content root, not the shared/live database.
- Root cause: `SpeakingTopicRow.id` (`app/speech/tables.py:20`) is a bare
  global primary key, but `sync_topics`'s delete-and-replace
  (`app/speech/topics.py:78`) is scoped only by `level`, so it can never clean
  up a same-id row that belongs to a different level before the conflicting
  insert runs.
- Suggested fix direction (any one of):
  1. Make the primary key composite: `(id, level)`, so ids are naturally
     namespaced per level and cross-level collisions can't crash the sync.
  2. Validate id-uniqueness across *all* levels (not just within one) at
     sync/load time and raise a clean `TopicError` (mirroring the existing
     `duplicate_error` used by `load_keyed_yaml` for in-level duplicates)
     instead of letting the DB throw.
  3. At minimum, explicitly document the id-namespacing convention (e.g.
     "prefix every speaking topic id with the level, `speak-<level>-...`") in
     `app/speech/topics.py`'s docstring/`SpeakingTopic` field docs, and/or add
     a lint/CI check over `content/**/speaking/*.yaml` that enforces global
     id-uniqueness so a future author can't accidentally reintroduce this.

## Triage
- Explanation: Reproduced the reasoning by reading the code directly (no need
  to re-run the scratch script — the shape is unambiguous). `SpeakingTopicRow`
  (`app/speech/tables.py:20`) declares `id: Mapped[str] = mapped_column(String(64),
  primary_key=True)` with no `level` in the key. `sync_topics`
  (`app/speech/topics.py:76-86`) does `delete(SpeakingTopicRow).where(SpeakingTopicRow.level
  == level)` then inserts the freshly-loaded topics for *only* that level — so a
  same-`id` row belonging to a different level is never deleted before the
  insert, and the second level's sync hits the global PK's `UNIQUE constraint
  failed` inside `session.commit()`, propagating an unhandled
  `sqlalchemy.exc.IntegrityError` out of `sync_topics`. The tester's repro
  script is a faithful, minimal demonstration of this; I didn't need to
  re-execute it to confirm the defect exists — the delete-predicate vs.
  PK-scope mismatch is visible directly in the two files.
- Against spec: unspecified for this exact case, but the *pattern itself* is
  not new or speaking-specific. `app/assessment/sync.py:20` (`sync_tasks` for
  `writing_tasks`) has the byte-for-byte identical shape: a bare global string
  PK (`app/assessment/tables.py:16`) combined with a delete scoped only to
  `WritingTaskRow.level == level`. `exam_blueprints`, `content_units`,
  `content_lessons`, `content_vocab`, and `comprehension_sets` all use the
  same bare-string-PK convention too. This is an established, repo-wide
  content-sync convention (ids namespaced by authoring discipline, e.g.
  `speak-a1-...`, `write-a2-...`), not a defect introduced by the speaking
  topic-bank PR. Nothing in `TEF_Platform_Technical_Plan.md` specifies
  composite keys or cross-level id validation for any content table.
- Verdict: deferred
- Rationale: This is a real, well-diagnosed latent trap — I confirm the
  crash mechanism is exactly as described, and would recommend either fix
  direction (composite PK, or a clean `TopicError` mirroring `duplicate_error`)
  as good hardening. But it isn't a regression this PR introduced, isn't
  reachable today (today's authored `content/*/speaking/*.yaml` ids are
  already level-prefixed by convention, verified), and isn't unique to
  speaking — the identical shape exists in at least the writing-tasks sync
  path and arguably every other content-sync table. Fixing `speaking_topics`
  in isolation while leaving `writing_tasks` etc. with the same latent
  footgun would be inconsistent, narrow-scope churn on a code path this PR
  didn't create. Recommend a follow-up backlog item to harden the *shared*
  content-sync convention (composite PK and/or a lint/CI check over all
  `content/**/*.yaml` id-uniqueness) across all content tables at once,
  rather than a one-off patch to `speech/tables.py` now.

## Critic
- Challenge: pm's "pre-existing, repo-wide, not a regression" claim is the load-bearing
  argument for deferring — if it's wrong, this becomes a one-off speech-only defect this
  PR should fix now. Also worth asking: is this even reachable, i.e. is it a real bug or
  a self-inflicted one requiring an author to violate the id-prefix convention?
- Holds up? Yes on both counts, verified independently rather than taking pm's word.
  Read `app/assessment/tables.py` and `app/assessment/sync.py` directly: `WritingTaskRow`
  has the identical bare `String(64) primary_key=True` id with no `level` in the key, and
  `sync_tasks` does the identical `delete(...).where(WritingTaskRow.level == level)`
  scoped-delete-then-insert. This is byte-for-byte the same shape as `speaking_topics`/
  `sync_topics`, confirming it predates and is untouched by this PR — `speech/tables.py`
  and `speech/topics.py` just followed an established (flawed) convention, they didn't
  invent it. Also confirmed the "not reachable today" claim: `grep '^id:' content/*/speaking/*.yaml`
  shows every authored id is already level-prefixed (`speak-a1-a-restaurant`, `speak-a2-a-voyage`,
  etc.), so no live collision exists; triggering the crash requires an author to actively
  violate the naming convention across two level directories, which is a self-inflicted
  authoring-time trap rather than something a learner or a normal content edit can hit.
  Given it's neither a regression nor currently reachable, and identical latent risk
  exists across every other content-sync table, fixing `speaking_topics` alone would be
  narrow, inconsistent churn on code this PR didn't create — a cross-cutting follow-up is
  the right scope, not a one-off patch now.
- Final verdict: deferred
