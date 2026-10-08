The output an inspection leaves under IEEE 1028-2008, clause 6.7, adapted only where pkit requires. Each record is shown whole, inside its own fence, as it would read on the default branch.

- **The front matter:** A's, unchanged. It is the data a tool reads (the design's Decided 2), so the standard's items that repeat it sit in the body as well.
- **The parts, in the clause's order:** *Team* (its item b), *Product* (d), *Inputs* (f), *Objectives* (g), *Anomaly list* (h), *Disposition* (i), *Waivers* (j) and *Anomaly summary* (m).
- **Adapted:** each anomaly gains what resolved it, which DEC-001 point 6 asks of a gap. Each disposition is an outcome of DEC-001 point 5, with its reason, in place of the standard's accept, accept with rework verification or reinspect.
- **Left out:** the project (a), the meeting's duration (c), the size of the materials (e), the preparation and rework times (k and l), the rework estimate (n) and the savings (o). A revalidation has no meeting, and pkit measures none of these.
- **The examples:** A's two, with the same front matter, people and evidence.
- **Not verified:** the clause's items after the preparation time, and every item's letter, rest on no source the round could read (the note's "Sources").

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

## Team

Alex, who wrote #1346's design, alone. No agent took part.

## Product

The eight core actors as the default branch holds them (`tech-docs/analysis/use-case-model/actors.md`), reviewed against #1346's design before code.

## Inputs

- #1346, and part 6 of #1352's note (`2026-10-05-analysis-kind-structure.md`)
- the template round's decisions on the actor, in comments on PR #1374
- COR-050 points 3 and 6, on a moved artefact and a new one

## Objectives

Find what in each actor the move makes untrue, and what the move needs that the system does not do. Both were met.

## Anomaly list

- **ACT-merge-authoriser, its first need:** the change check would ask for none of the eight answers the move needs (COR-050 point 3, and #1352's note, part 6). An entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6). So the merge authoriser would see none of them in the check's list.
  - **Classification:** a gap, a description with no behaviour.
  - **Resolved:** #1359, which #1346 waits for.

## Disposition

- **ACT-adopter — analysis-stale.** #1346 moves it to a file of its own. *The setup*, *Comes* and *Brings* become *Setup*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-ai-agent — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *In the model* become *Role holders*, *Occasions* and *Place in the model*. It gains *Context*, which reads `None.`.
- **ACT-ci-pipeline — analysis-stale.** #1346 moves it to a file of its own. *Comes*, *Brings* and *In the model* become *Occasions*, *Context* and *Place in the model*. PRJ-002, which its *Note* cites, becomes an anchor.
- **ACT-component-author — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Comes* and *Brings* become *Role holders*, *Occasions* and *Context*, and every item keeps its words.
- **ACT-developer — analysis-stale.** #1346 moves it to a file of its own. *Comes* and *Brings* become *Occasions* and *Context*. ADR-061, which its *Core* cites, becomes an anchor.
- **ACT-merge-authoriser — gap-found.** #1346 moves it to a file of its own. *Always a person*, *Comes* and *Brings* become *Human role*, *Occasions* and *Context*, and DEC-028, which its *Note* cites, becomes an anchor. The anomaly list holds its gap.
- **ACT-methodology-maintainer — analysis-stale.** #1346 moves it to a file of its own. *Can be*, *Does*, *Comes* and *Brings* become *Role holders*, *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Brings* cites, becomes a path anchor.
- **ACT-operator — analysis-stale.** #1346 moves it to a file of its own. *Does*, *Comes* and *Brings* become *Activities*, *Occasions* and *Context*. CONTRIBUTING.md, which its *Note* cites, becomes a path anchor.

## Waivers

None.

## Anomaly summary

One gap, and no regression.
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

## Team

- analysis-resolver, which proposed the outcomes
- Sam, who said that 3e9f1c2's change was not meant, and confirmed the outcomes

## Product

UC-xxx and JRN-xxx, which the whole-repository check flagged once 3e9f1c2 changed `friction_check.py`, reviewed against the default branch at 3e9f1c2.

## Inputs

- `pkit friction explain` for each, naming 3e9f1c2
- 3e9f1c2's message, and Sam's answer that the change was not meant
- the evidence the front matter copies

## Objectives

Say for each flagged artefact whether its description still holds. Met.

## Anomaly list

- **UC-xxx, step 4:** since 3e9f1c2 the change check's list shows each answer's first line only.
  - **Classification:** a regression.
  - **Resolved:** defect #xxxx reported.

## Disposition

- **UC-xxx — code-regressed.** Step 4 still describes what is wanted: the merge authoriser is shown every answer word for word (COR-050 point 3). 3e9f1c2 cut each answer in the change check's list to its first line, and the test of the full answers failed at it. Defect #xxxx reported.
- **JRN-xxx — holds.** Its steps rely on the change check failing a merge on friction, not on how the check prints the answers, which is all 3e9f1c2 changed.

## Waivers

None.

## Anomaly summary

One regression, and no gap.
````
