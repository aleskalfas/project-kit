---
id: VIEW-classification-of-issues
title: Classification of issues
status: active
explains:
  - TERM-classification-axis
  - TERM-kind-of-work
  - TERM-workstream
  - TERM-substrate-map
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-012
        - project-management:DEC-016
        - project-management:DEC-018
        - project-management:DEC-011
        - project-management:DEC-036
        - project-management:DEC-062
      artefact:
        - TERM-classification-axis
        - TERM-kind-of-work
        - TERM-workstream
        - TERM-substrate-map
---

# VIEW-classification-of-issues — Classification of issues

Issues need classification beyond their type. Classification keeps the filing of issues the same each time, and lets a board filter and plan by it. Classification also aligns a [pull request](../../core/glossary.md#term-pull-request--pull-request)'s title with the work the pull request closes ([DEC-012](../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

A [classification axis](../glossary.md#term-classification-axis--classification-axis) is one dimension of that classification, on which every [issue](../glossary.md#term-issue--issue) takes one value. A [kind of work](../glossary.md#term-kind-of-work--kind-of-work) is one value of the `type` axis. A [workstream](../glossary.md#term-workstream--workstream) is one value of the `workstream` axis: a long-lived area of the work, which the [project](../../core/glossary.md#term-project--project) declares in a file of its own. A [substrate map](../glossary.md#term-substrate-map--substrate-map) says which part of GitHub carries each axis.

```mermaid
classDiagram
  accTitle: Classification of issues
  accDescr: Each issue takes one value on each of three classification axes. A kind of work is a value of the type axis, and a workstream is a value of the workstream axis. An EPIC's outcome lies within a workstream. A project's substrate map may bind each axis, and the issue's state, to a part of GitHub.
  class ClassificationAxis["Classification axis"] {
    values
    carried as a label or a board field
  }
  class KindOfWork["Kind of work"] {
    value
    title prefix
  }
  class Workstream {
    slug
    name
    status
  }
  class SubstrateMap["Substrate map"] {
    a binding for each axis
  }
  class Issue
  class EPIC
  Issue "*" --> "3" ClassificationAxis : takes one value on each
  ClassificationAxis "1" o-- "*" KindOfWork : the type axis's values
  ClassificationAxis "1" o-- "*" Workstream : the workstream axis's values
  EPIC "*" --> "1" Workstream : lies within
  SubstrateMap "0..1" --> "*" ClassificationAxis : binds
```

```mermaid
flowchart LR
  accTitle: How a workstream moves
  accDescr: A workstream is added as active. It may be renamed, merged into another or split into several, and the issues that carry it follow. It may be deprecated, and it is removed only once no issue carries it.
  added([Workstream added]) --> active[Active]
  active --> changed([Renamed, merged or split, its issues following])
  changed --> active
  active --> deprecated[Deprecated]
  active --> removed([Removed, once no issue carries it])
  deprecated --> removed
```

## Classification axis

Defined in [TERM-classification-axis](../glossary.md#term-classification-axis--classification-axis).

**Why:** Classification serves three jobs: consistent filing, a board's filters and plans, and pull-request titles aligned with their work. Each job needs every [issue](../glossary.md#term-issue--issue) to carry a value on each axis ([DEC-012](../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

A classification axis is one dimension along which every issue is classified. There are three: `type`, the [kind of work](../glossary.md#term-kind-of-work--kind-of-work), then `priority` and `workstream`. An issue carries one value on each, on a label or on a field of a board.

**Attributes:**

- its values: a fixed set for `type` and `priority`, and the [project](../../core/glossary.md#term-project--project)'s own for `workstream` (DEC-012)
- where it is carried: a label, or a field of a Projects v2 board where the project keeps one (DEC-012)

**Relations:**

- Each issue takes one value on each axis (DEC-012).
- The value on `type` sets a [Task](../glossary.md#term-task--task)'s title prefix, and the commit type of the [pull request](../../core/glossary.md#term-pull-request--pull-request) that closes it (DEC-012).

**States:** None.

**Always true:**

- The `type` axis is always carried as a label, and no issue carries two values on it (DEC-012).
- An [EPIC](../glossary.md#term-epic--epic), a [Feature](../glossary.md#term-feature--feature) and an [Umbrella](../glossary.md#term-umbrella--umbrella) always take the value `feature` on `type` (DEC-012).
- A [Milestone](../glossary.md#term-milestone--milestone) carries no classification axis (DEC-012).

## Kind of work

Defined in [TERM-kind-of-work](../glossary.md#term-kind-of-work--kind-of-work).

**Why:** A reader should see from a [Task](../glossary.md#term-task--task)'s title, and from the [pull request](../../core/glossary.md#term-pull-request--pull-request) that closes it, what sort of work it holds. One fixed set of values keeps each title prefix and each commit type in step with the work ([DEC-011](../../../../.pkit/capabilities/project-management/decisions/DEC-011-title-formats.md) and [DEC-012](../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).

A kind of work is the value an [issue](../glossary.md#term-issue--issue) takes on the `type` axis, such as `bug`, `docs` or `test`. A Task's kind of work sets the prefix its title opens with, such as `[Docs]`. It sets the commit type of the pull request that closes the Task too.

**Attributes:**

- its value, one of `feature`, `bug`, `docs`, `test`, `refactor` and `maintenance` (DEC-012)
- the prefix it gives a Task's title, such as `[Bug]` for `bug` (DEC-011)

**Relations:**

- Each issue takes one kind of work, on the `type` [classification axis](../glossary.md#term-classification-axis--classification-axis) (DEC-012).
- An [EPIC](../glossary.md#term-epic--epic), a [Feature](../glossary.md#term-feature--feature) and an [Umbrella](../glossary.md#term-umbrella--umbrella) always take `feature`. Every other kind of work is a Task's alone (DEC-012).

**States:** None.

**Always true:**

- A Task's title opens with its kind of work's prefix, since the [system](../../core/glossary.md#term-system--system) composes the title from that prefix (DEC-011).

## Workstream

Defined in [TERM-workstream](../glossary.md#term-workstream--workstream).

**Why:** A team invests in long-lived areas over many outcomes. Where each [project](../../core/glossary.md#term-project--project) improvises their names and their lifecycle, the names drift. One definition, kept in one file with fixed forms for the names, keeps every project's workstreams in one shape ([DEC-018](../../../../.pkit/capabilities/project-management/decisions/DEC-018-workstream-taxonomy-and-lifecycle.md)).

A workstream is a long-lived area of a project's work, such as `docs` or `cli`. It outlasts the [EPICs](../glossary.md#term-epic--epic) whose outcomes lie within it. The project declares its workstreams in a file of its own, and each one is a value of the `workstream` axis.

**Attributes:**

- its slug, which other files cite, and its name (DEC-018)
- its description, which may be empty (DEC-018)
- its status, `active` or `deprecated`, with the reason for a deprecation (DEC-018)

**Relations:**

- It is one value of the `workstream` [classification axis](../glossary.md#term-classification-axis--classification-axis) ([DEC-012](../../../../.pkit/capabilities/project-management/decisions/DEC-012-classification-axes.md)).
- An EPIC covers a single outcome inside a workstream (DEC-018).
- It groups issues, and is the parent of none ([DEC-016](../../../../.pkit/capabilities/project-management/decisions/DEC-016-time-bound-containers.md)).

**States:** A workstream is added as active, and may be deprecated. It may be renamed, merged into another or split into several, and the issues that carry it follow. It is removed only once no [issue](../glossary.md#term-issue--issue) carries it (DEC-018).

**Always true:**

- The project's file of workstreams is authoritative, and a board's field reflects it (DEC-018).
- Its slug is 2 to 40 lowercase letters, digits and single hyphens (DEC-018).

## Substrate map

Defined in [TERM-substrate-map](../glossary.md#term-substrate-map--substrate-map).

**Why:** Some projects cannot create the labels project-management writes, since their tracker already has conventions of its own. Such a [project](../../core/glossary.md#term-project--project) says where each axis already lives. Each check that needs an axis the project cannot carry then warns, rather than refusing ([DEC-036](../../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md)).

A substrate map is a file of the project's own. It binds each [classification axis](../glossary.md#term-classification-axis--classification-axis), and an [issue](../glossary.md#term-issue--issue)'s state, to one carrier on GitHub. The carrier may be project-management's own labels, or labels the project already has ([DEC-062 point 3](../../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md#3-the-map-can-name-the-kits-own-labels)). It may also be a title prefix, a field of the project's board, or whether the issue is open ([DEC-036 point 1](../../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md#1-a-dedicated-substrate-mapyaml-schema)).

**Attributes:**

- for each axis it binds, the carrier and how the axis's values map onto it (DEC-036 point 1)
- for an issue's state, its carrier, which may be the board ([DEC-062 point 5](../../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md#5-where-the-map-puts-state-on-the-board-the-boards-status-is-the-source-of-an-open-issues-position))

**Relations:**

- It binds each classification axis it names, and the state, to one carrier (DEC-036 point 1).
- An axis is on the project's board only where the map binds the axis there ([DEC-062 point 1](../../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md#1-the-flag-says-only-that-a-board-exists)).

**States:** None.

**Always true:**

- With no substrate map, every axis reads project-management's own labels ([DEC-036 point 2](../../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md#2-activation-is-emergent-not-a-global-mode-flag)).
- An axis that a present map leaves out, or marks unsupported, has no carrier. The checks that need it warn instead of refusing (DEC-036 point 2 and [DEC-062 point 2](../../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md#2-where-the-map-is-silent-an-axis-reads-as-it-does-with-no-board)).
- A map carries nothing beyond its bindings, and puts the project in no mode ([DEC-062 point 4](../../../../.pkit/capabilities/project-management/decisions/DEC-062-axes-chosen-in-the-map.md#4-a-map-carries-nothing-beyond-its-bindings)).
- project-management never creates, renames or deletes a label or a field the project owns ([DEC-036 point 5](../../../../.pkit/capabilities/project-management/decisions/DEC-036-substrate-pluggable-adoption.md#5-never-write-an-unmanaged-label)).

## What is built on these concepts

Each concept below lists the use cases, journeys and requirements whose text links its term.

**Classification axis:**

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/020-file-and-move/UC-060-file-task.md)
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/010-plan/UC-063-plan-intent.md)
- [JRN-012 — Take up my Task, and land its change](../use-case-model/journeys/JRN-012-take-up-and-land-task.md)

**Kind of work:**

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/020-file-and-move/UC-060-file-task.md)
- [UC-082 — Set up my project's topology in the project's committed configuration, so that every clone reads the same seats](../use-case-model/use-cases/040-work-in-parallel/UC-082-set-up-topology.md)
- [UC-087 — Hand the next piece of the work to the scope that does that piece](../use-case-model/use-cases/040-work-in-parallel/UC-087-hand-over-to-next-scope.md)

**Workstream:**

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/020-file-and-move/UC-060-file-task.md)
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/010-plan/UC-063-plan-intent.md)
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/010-plan/UC-064-define-milestones-and-workstreams.md)
- [UC-082 — Set up my project's topology in the project's committed configuration, so that every clone reads the same seats](../use-case-model/use-cases/040-work-in-parallel/UC-082-set-up-topology.md)
- [UC-083 — Plan an intent into Tasks that one agent can each finish](../use-case-model/use-cases/040-work-in-parallel/UC-083-plan-across-scopes.md)
- [UC-084 — Take my next ready Task, and build it up to its merge](../use-case-model/use-cases/040-work-in-parallel/UC-084-take-next-task.md)
- [UC-085 — Never work on a Task another agent already works on](../use-case-model/use-cases/040-work-in-parallel/UC-085-leave-task-to-its-owner.md)
- [UC-087 — Hand the next piece of the work to the scope that does that piece](../use-case-model/use-cases/040-work-in-parallel/UC-087-hand-over-to-next-scope.md)
- [JRN-004 — Set up the topology my project runs, and adjust the topology on what I measure](../use-case-model/journeys/JRN-004-set-up-and-adjust-topology.md)
- [JRN-013 — Build my next Task, and land it while other agents land theirs](../use-case-model/journeys/JRN-013-build-and-land-next-task.md)

**Substrate map:**

- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/020-file-and-move/UC-061-move-issue.md)
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/010-plan/UC-064-define-milestones-and-workstreams.md)
- [UC-084 — Take my next ready Task, and build it up to its merge](../use-case-model/use-cases/040-work-in-parallel/UC-084-take-next-task.md)
- [UC-090 — See which agent works on which issue, without visiting each agent](../use-case-model/use-cases/040-work-in-parallel/UC-090-see-who-works-on-what.md)
