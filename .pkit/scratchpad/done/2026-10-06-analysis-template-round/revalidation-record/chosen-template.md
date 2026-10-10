The maintainer's chosen shape, filled with both records. Each record is shown whole, inside its own fence, as it would read on the default branch.

- **The parts:** *Outcomes* and *Gaps*, both present in every record.
  - *Gaps* reads `None.` when there is none, in place of the stamp's `None found.`.
  - Neither example reads `None.`, since each finds a gap or a regression.
- **Each gap:** it starts with the ids of the artefacts it affects, taken from `outcomes`, as a bold label. Its *Resolution* follows under a label of its own.
- **The planned record:** its front matter names the design it reviewed in `reviewed-against`, one mapping for each source.
  - **Text in this repository:** part 6 of #1352's note, by its title and the commit on the default branch that holds it. It has no `url`.
  - **Text in the tracker:** #1346's body and three of the maintainer's comments on PR #1374. Each is named by its link and the time it was read.
- **The regression:** its trigger is `scheduled`, so its front matter has no `reviewed-against`.
- **The rest:** D's, with the same people, outcomes and evidence.

## The planned record

`revalidations/2026-10-08-each-actor-in-a-file-of-its-own.md`:

````markdown
---
change: '#1346'
trigger: planned
reviewed-against:
  - title: "#1346's body"
    url: https://github.com/aleskalfas/project-kit/issues/1346
    version: '2026-10-08T09:30:00Z'
  - title: "part 6 of #1352's note, the actors' layout"
    version: '0192e5fc'
  - title: the rule for every kind, the maintainer's decision of 7 October
    url: https://github.com/aleskalfas/project-kit/pull/1374#issuecomment-6046070594
    version: '2026-10-08T09:30:00Z'
  - title: the actor's questions 1 to 3, the maintainer's decisions of 7 October
    url: https://github.com/aleskalfas/project-kit/pull/1374#issuecomment-6046121141
    version: '2026-10-08T09:30:00Z'
  - title: the system and the methodology, the maintainer's decision of 8 October
    url: https://github.com/aleskalfas/project-kit/pull/1374#issuecomment-6052793986
    version: '2026-10-08T09:30:00Z'
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

- **ACT-merge-authoriser:** the change check would ask for none of the eight answers the move needs (COR-050 point 3, and #1352's note, part 6). An entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6). So the merge authoriser would see none of them in the check's list. **Resolution:** #1359, which #1346 waits for.
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

- **UC-xxx:** since 3e9f1c2 the change check's list shows each answer's first line only, so step 4 has no behaviour. **Resolution:** defect #xxxx reported.
````
