---
id: VIEW-batch-planning
title: Batch planning
status: active
explains:
  - TERM-use-case-entry
  - TERM-batch-plan
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-029
        - project-management:DEC-054
        - project-management:DEC-060
        - project-management:DEC-061#6
      artefact:
        - TERM-use-case-entry
        - TERM-batch-plan
---

# VIEW-batch-planning — Batch planning

An intent becomes many issues, and slicing it well needs the [project](../../core/glossary.md#term-project--project)'s own account of what its software must do. That account is another [component](../../core/glossary.md#term-component--component)'s, so it comes through a [data point](../../core/glossary.md#term-data-point--data-point). Slicing is a judgement, so a person approves the whole outline before anything is filed ([DEC-029](../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md) and [DEC-054](../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md)).

A [use-case entry](../glossary.md#term-use-case-entry--use-case-entry) names one goal of that account. A [batch plan](../glossary.md#term-batch-plan--batch-plan) is the outline the agent drafts against the entries. The person approves the outline, revises it or cancels it.

Where the slices would share a choice that nothing settles yet, a first plan files only the work's foundation. A second plan files the slices once the foundation is done ([DEC-060](../../../../.pkit/capabilities/project-management/decisions/DEC-060-foundation-before-slices.md)).

```mermaid
classDiagram
  accTitle: Batch planning
  accDescr: A batch plan outlines the issues to file for one intent, each with its parent. It judges each choice the slices would share. It maps the intent onto use-case entries. A use-case entry names one goal by its id, title and status.
  class BatchPlan["Batch plan"] {
    intent
    rows
    shared choices
    gaps
  }
  class UseCaseEntry["Use-case entry"] {
    id
    title
    status
    path
  }
  class Issue
  BatchPlan "1" --> "1..*" Issue : outlines
  BatchPlan "*" --> "*" UseCaseEntry : maps the intent onto
```

```mermaid
flowchart LR
  accTitle: How a batch plan moves
  accDescr: A batch plan is drafted against the active use-case entries, then waits for a person. Approved, its issues are filed, parents first. Revised, it is drafted again. Cancelled, nothing is filed. Once a first plan's foundation is done, a second plan is drafted for the slices.
  drafted([Batch plan drafted against the active entries]) --> waits[Waits for the person]
  waits -->|approved| filed([Its issues filed, parents first])
  waits -->|revised| drafted
  waits -->|cancelled| nothing([Nothing filed])
  filed -->|a first plan's foundation done| drafted
```

## Use-case entry

Defined in [TERM-use-case-entry](../glossary.md#term-use-case-entry--use-case-entry).

**Why:** [Components](../../core/glossary.md#term-component--component) exchange what they know through [data points](../../core/glossary.md#term-data-point--data-point), without depending on each other. So project-management reads the [project](../../core/glossary.md#term-project--project)'s account of its software through one, never through another component's files. Whatever keeps that account, or the project itself, fills the data point ([DEC-054](../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md)).

A use-case entry is one item of that data point. It names one goal the project's software serves, by its id and its title, and says whether it is active or withdrawn. Where it can, it also gives the path of the document that describes the goal.

**Attributes:**

- its id, `UC-` and three digits or more, at version 1 ([DEC-054 point 1](../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#1-the-point))
- its title (DEC-054 point 1)
- its status, `active` or `withdrawn` (DEC-054 point 1)
- the path of its document, where the filler gives one (DEC-054 point 1)

**Relations:**

- One component fills the data point, and a file of the project's own replaces what that component gives, whole (DEC-054 point 1).
- A [Feature](../glossary.md#term-feature--feature)'s or a [Task](../glossary.md#term-task--task)'s body may cite it in a `## Use cases` section ([DEC-054 point 4](../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#4-the-rule)).

**States:** An entry is active or withdrawn (DEC-054 point 1).

**Always true:**

- The data point holds the entries settled on the [default branch](../../core/glossary.md#term-default-branch--default-branch) (DEC-054 point 1).
- An id names one entry for good, so a citation of a withdrawn one stays true (DEC-054).

## Batch plan

Defined in [TERM-batch-plan](../glossary.md#term-batch-plan--batch-plan).

**Why:** An intent becomes many issues, and slicing it is a judgement a person must check. One approval of the whole outline keeps the agent's speed without filing work nobody agreed to. Adversarial review before that approval catches bad slicing where it costs least ([DEC-029](../../../../.pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent-shape.md)).

A batch plan is the outline the project-manager agent drafts for an intent. It holds an [EPIC](../glossary.md#term-epic--epic) and its work, each [issue](../glossary.md#term-issue--issue) with its parent, classification and [use-case entries](../glossary.md#term-use-case-entry--use-case-entry). The person approves it, revises it or cancels it, and nothing is filed before they approve it.

**Attributes:**

- one row for each issue: its type, title, parent, [workstream](../glossary.md#term-workstream--workstream), [Milestone](../glossary.md#term-milestone--milestone), priority and use-case entries (DEC-029 and [DEC-054 point 5](../../../../.pkit/capabilities/project-management/decisions/DEC-054-use-case-validation.md#5-the-planning-step))
- the [pool](../glossary.md#term-pool--pool) of each issue's Milestone, where the [topology](../glossary.md#term-topology--topology) declares pools, so the person's approval covers each [Task](../glossary.md#term-task--task)'s pool ([DEC-061 point 6](../../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md#6-putting-work-into-a-pool-is-the-persons-act))
- the active entries the intent touches that no issue names, and the work that no entry describes (DEC-054 point 5)
- each choice the slices would share, judged settled, in hand by an open foundation, or open ([DEC-060 point 3](../../../../.pkit/capabilities/project-management/decisions/DEC-060-foundation-before-slices.md#3-the-first-plan-files-the-foundation-and-the-second-plans-the-slices))
- the [findings](../../core/glossary.md#term-finding--finding) of the [reviewers](../../core/glossary.md#term-reviewer--reviewer) run on it (DEC-029)

**Relations:**

- It outlines the issues for one intent, parents before children (DEC-029).
- It maps the intent onto the active use-case entries (DEC-054 point 5).
- A first plan files the EPIC, with an outline of the slices, and the [Feature](../glossary.md#term-feature--feature) of the work's foundation. A second plan files the slices under that EPIC, once the foundation's Feature has closed (DEC-060 point 3).

**States:** A batch plan is drafted, then waits for the person. Approved, its issues are filed, parents first. Revised, it is drafted again, and cancelled, nothing is filed (DEC-029). A first plan's slices wait for a second plan, drafted once the foundation's Feature closes (DEC-060 point 3).

**Always true:**

- None of its issues is filed before the person approves the whole plan (DEC-029).
- It cites only ids the [data point](../../core/glossary.md#term-data-point--data-point) holds, and never suggests one (DEC-054 point 5).
- A first plan files no slice (DEC-060 point 3).

## What is built on these concepts

Each concept below lists the use cases, journeys and requirements whose text links its term.

**Use-case entry:**

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/020-file-and-move/UC-060-file-task.md)
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/010-plan/UC-063-plan-intent.md)

**Batch plan:**

- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/010-plan/UC-063-plan-intent.md)
