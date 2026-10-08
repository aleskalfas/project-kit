An architecture decision record's parts, after Michael Nygard, adapted only where pkit requires. Each record is shown whole, inside its own fence, as it would read on the default branch.

- **The title:** a short noun phrase, as Nygard asks. The stamp's heading already gives one, after the date.
- **The parts, in Nygard's order:** *Context*, *Decision*, *Status* and *Consequences*.
- **Context** holds the forces, in his words: here the change, the trigger and what the revalidation read.
- **Decision** holds each artefact's outcome with its reason, in the active voice he asks for, "We record …".
- **Status** is one of his four: proposed, accepted, deprecated or superseded. A record is history, so it is always accepted, and it names who accepted it.
- **Consequences** holds the gaps with what resolved each, as DEC-001 point 6 asks, beside what else follows.
- **Adapted:** Nygard numbers his records, and pkit names them by date and subject (DEC-001 point 6). One of his records holds one decision, and a revalidation record holds one for each artefact.
- **The examples:** A's two, with the same front matter, people and evidence.

## The planned record

`revalidations/2026-10-08-each-actor-in-a-file-of-its-own.md`:

````markdown
---
change: '#1346'
trigger: planned
date: '2026-10-08'
by: Alex
outcomes:
  ACT-adopter: analysis-stale
  ACT-ai-agent: analysis-stale
  ACT-ci-pipeline: analysis-stale
  ACT-component-author: analysis-stale
  ACT-developer: analysis-stale
  ACT-merge-authoriser: gap-found
  ACT-methodology-maintainer: analysis-stale
  ACT-operator: analysis-stale
---

# 2026-10-08 — Each actor in a file of its own

## Context

#1346 moves each of the eight core actors to a file of its own, and its code is not written yet. The template round gives the actors noun labels as they move, and turns five citations into anchors (PR #1374). Moving an artefact needs a revalidation in the same change (COR-050 point 3). Today an entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6, and #1352's note, part 6).

## Decision

We record each actor's outcome against #1346's design.

- **ACT-adopter — analysis-stale.** #1346 moves it to a file of its own. *The setup*, *Comes* and *Brings* become *Setup*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-ai-agent — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *In the model* become *Role holders*, *Occasions* and *Place in the model*. It gains *Context*, which reads `None.`.
- **ACT-ci-pipeline — analysis-stale.** #1346 moves it to a file of its own. *Comes*, *Brings* and *In the model* become *Occasions*, *Context* and *Place in the model*. PRJ-002, which its *Note* cites, becomes an anchor.
- **ACT-component-author — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *Brings* become *Role holders*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-developer — analysis-stale.** #1346 moves it to a file of its own. *Comes* and *Brings* become *Occasions* and *Context*. ADR-061, which its *Core* cites, becomes an anchor.
- **ACT-merge-authoriser — gap-found.** #1346 moves it to a file of its own. *Always a person*, *Comes* and *Brings* become *Human role*, *Occasions* and *Context*, and DEC-028, which its *Note* cites, becomes an anchor. Its first need has no behaviour for the move's answers, as the consequences say.
- **ACT-methodology-maintainer — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Does*, *Comes* and *Brings* become *Role holders*, *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Brings* cites, becomes a path anchor.
- **ACT-operator — analysis-stale.** #1346 moves it to a file of its own. *Does*, *Comes* and *Brings* become *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Note* cites, becomes a path anchor.

## Status

Accepted, by Alex, who performed it.

## Consequences

- **A gap:** the change check would ask for none of the eight answers the move needs. So the merge authoriser would see none of them in the check's list. **Resolved:** #1359 makes the check ask, and #1346 waits for it.
- **Eight answers:** when #1346 lands, each actor's file carries its revalidation, `updated`, for the merge authoriser to see.
- **Five new anchors:** a change to ADR-061, PRJ-002, DEC-028 or CONTRIBUTING.md flags the actors that cite it.
````

## The regression

`revalidations/2026-10-08-answers-cut-short.md`:

````markdown
---
change: 3e9f1c2
trigger: scheduled
date: '2026-10-08'
by: analysis-resolver
confirmed-by: Sam
outcomes:
  UC-xxx: code-regressed
  JRN-xxx: holds
evidence:
  - id: UC-xxx@3e9f1c2d8a7b6c5e4f30a1b2c3d4e5f607182930#project.test-friction-check.test-the-human-view-ends-with-every-answer-in-full
    artefact: UC-xxx
    commit: 3e9f1c2d8a7b6c5e4f30a1b2c3d4e5f607182930
    check: project.test-friction-check.test-the-human-view-ends-with-every-answer-in-full
    result: failed
    ran: tests/test_friction_check.py::test_the_human_view_ends_with_every_answer_in_full
    steps: ['4']
    by: CI pipeline
---

# 2026-10-08 — Answers cut short

## Context

The whole-repository check flagged UC-xxx and JRN-xxx, since 3e9f1c2 changed `friction_check.py`, which both anchor. 3e9f1c2 cut each answer in the change check's list to its first line, and the test of the full answers failed at it. Sam, who knows what the change was for, said it was not meant.

## Decision

We record UC-xxx as regressed, and JRN-xxx as holding.

- **UC-xxx — code-regressed.** Step 4 still describes what is wanted: the merge authoriser is shown every answer word for word (COR-050 point 3). 3e9f1c2 broke it. Defect #xxxx reported.
- **JRN-xxx — holds.** Its steps rely on the change check failing a merge on friction, not on how the check prints the answers, which is all 3e9f1c2 changed.

## Status

Accepted, by Sam, on analysis-resolver's proposal.

## Consequences

- **A regression:** since 3e9f1c2, step 4 of UC-xxx has no behaviour. **Resolved:** defect #xxxx reported. UC-xxx is not rewritten to match the code.
- **Open until fixed:** `pkit analysis validate` reports UC-xxx's regression until UC-xxx is revalidated against the fix.
````
