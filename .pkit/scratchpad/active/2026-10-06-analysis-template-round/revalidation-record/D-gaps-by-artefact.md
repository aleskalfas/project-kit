Today's two parts as the earlier rounds' decisions shape them. Each record is shown whole, inside its own fence, as it would read on the default branch.

- **The parts:** *Outcomes* and *Gaps*, as A's, both present in every record.
- **`None.`:** a record with no gap reads `None.` under *Gaps*, by the rule for every kind, where today's stamp writes `None found.`. Neither example has one, since a regression always names its gap.
- **Each gap names its artefact:** a gap opens with the id of the artefact it was found in, as a bold label. That artefact's outcome is `code-regressed` or `gap-found`, and each such artefact has at least one gap. So a form can hold the two to each other, as the journey's decided `**Needs from step N (UC-xxx):**` lines hold each hand-over to its step.
- **What resolved it:** after the gap, under its own bold label, *Resolved*.
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

## Outcomes

- **ACT-adopter — analysis-stale.** #1346 moves it to a file of its own. *The setup*, *Comes* and *Brings* become *Setup*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-ai-agent — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *In the model* become *Role holders*, *Occasions* and *Place in the model*. It gains *Context*, which reads `None.`.
- **ACT-ci-pipeline — analysis-stale.** #1346 moves it to a file of its own. *Comes*, *Brings* and *In the model* become *Occasions*, *Context* and *Place in the model*. PRJ-002, which its *Note* cites, becomes an anchor.
- **ACT-component-author — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *Brings* become *Role holders*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-developer — analysis-stale.** #1346 moves it to a file of its own. *Comes* and *Brings* become *Occasions* and *Context*. ADR-061, which its *Core* cites, becomes an anchor.
- **ACT-merge-authoriser — gap-found.** #1346 moves it to a file of its own. *Always a person*, *Comes* and *Brings* become *Human role*, *Occasions* and *Context*, and DEC-028, which its *Note* cites, becomes an anchor. Its gap is below.
- **ACT-methodology-maintainer — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Does*, *Comes* and *Brings* become *Role holders*, *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Brings* cites, becomes a path anchor.
- **ACT-operator — analysis-stale.** #1346 moves it to a file of its own. *Does*, *Comes* and *Brings* become *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Note* cites, becomes a path anchor.

## Gaps

- **ACT-merge-authoriser:** the change check would ask for none of the eight answers the move needs (COR-050 point 3, and #1352's note, part 6). An entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6). So the merge authoriser would see none of them in the check's list. **Resolved:** #1359, which #1346 waits for.
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

## Outcomes

- **UC-xxx — code-regressed.** Step 4 still describes what is wanted: the merge authoriser is shown every answer word for word (COR-050 point 3). 3e9f1c2 cut each answer in the change check's list to its first line, and the test of the full answers failed at it. Defect #xxxx reported.
- **JRN-xxx — holds.** Its steps rely on the change check failing a merge on friction, not on how the check prints the answers, which is all 3e9f1c2 changed.

## Gaps

- **UC-xxx:** since 3e9f1c2 the change check's list shows each answer's first line only, so step 4 has no behaviour. **Resolved:** defect #xxxx reported.
````
