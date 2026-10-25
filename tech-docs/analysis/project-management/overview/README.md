# Overview of the analysis of project-management

<!-- pkit:overview reads=4 fingerprint=sha256:acc2eef51fb1773e9640a98f97d80eeea9150a2a246ef6dc04f4b45f9162912e -->

[project-management exists so a team runs its projects' work on GitHub by one rulebook, which agents carry out on a person's authority](../../../../.pkit/capabilities/project-management/decisions/DEC-057-purpose.md).

This analysis describes what project-management does: who uses it, what they do with it, and what it must meet. It builds on the analysis of core.

## Use cases

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/UC-060-file-task.md) ([not built yet](#not-built-yet): step 6, step 8, variant 6c, variant 6e)
- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/UC-061-move-issue.md) ([not built yet](#not-built-yet): step 4, step 7, variant 1a, variant 7a)
- [UC-062 — Have the reviewers my change requires review my pull request, and land it](../use-case-model/use-cases/UC-062-review-and-land.md) ([not built yet](#not-built-yet): variant 1b)
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/UC-063-plan-intent.md) ([not built yet](#not-built-yet): step 8, step 9)
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/UC-064-define-milestones-and-workstreams.md) ([not built yet](#not-built-yet): step 4, step 9, variant 11a)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| [ACT-planner — Planner](../use-case-model/actors/ACT-planner.md) | The person who plans a project's work at the level of its outcomes. | [the use cases](#use-cases) |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-ci-pipeline — CI pipeline | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-merge-authoriser — Merge authoriser | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-operator — Operator | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [010 — Issues and their hierarchy](../domain-model/010-issues-and-their-hierarchy.md)
- [020 — Classification of issues](../domain-model/020-classification-of-issues.md)
- [030 — The issue lifecycle](../domain-model/030-the-issue-lifecycle.md)
- [040 — Reviews and the merge](../domain-model/040-reviews-and-the-merge.md)
- [050 — Batch planning](../domain-model/050-batch-planning.md)

### Requirements

- [REQ-040 · Constraint · project-management works on GitHub alone, through an authenticated gh](../requirements/constraints/REQ-040-github-and-gh.md)
- [REQ-041 · Functional · A command that writes checks the project's prerequisites and the person's membership first](../requirements/functional/REQ-041-gates-before-writing.md)
- [REQ-042 · Functional · A move a person holds is made only on that person's authorisation](../requirements/functional/REQ-042-held-moves-authorised.md)

### Not built yet

What the use cases describe and the system does not do yet, each with the record that decides it and the issue that tracks it (software-analysis DEC-001 point 1):

- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/UC-060-file-task.md): step 6, decided by `project-management:DEC-005`, tracked in `#1313`
- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/UC-060-file-task.md): step 8, decided by `project-management:DEC-005`, tracked in `#1314`
- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/UC-060-file-task.md): variant 6c, decided by `project-management:DEC-005`, tracked in `#1313`
- [UC-060 — File a Task under its parent, its title and body checked as it is filed](../use-case-model/use-cases/UC-060-file-task.md): variant 6e, decided by `project-management:DEC-005`, tracked in `#1314`
- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/UC-061-move-issue.md): step 4, decided by `project-management:DEC-052`, tracked in `#756`
- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/UC-061-move-issue.md): step 7, decided by `project-management:DEC-013`, tracked in `#1761`
- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/UC-061-move-issue.md): variant 1a, decided by `COR-004`, tracked in `#1938`
- [UC-061 — Move my issue through its lifecycle, each move checked](../use-case-model/use-cases/UC-061-move-issue.md): variant 7a, decided by `project-management:DEC-007`, tracked in `#1215`
- [UC-062 — Have the reviewers my change requires review my pull request, and land it](../use-case-model/use-cases/UC-062-review-and-land.md): variant 1b, decided by `COR-004`, tracked in `#1938`
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/UC-063-plan-intent.md): step 8, decided by `project-management:DEC-014`, tracked in `#1761`
- [UC-063 — Plan an intent into an EPIC and its work, filed once I approve the plan](../use-case-model/use-cases/UC-063-plan-intent.md): step 9, decided by `project-management:DEC-029`, tracked in `#1761`
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/UC-064-define-milestones-and-workstreams.md): step 4, decided by `project-management:DEC-016`, tracked in `#1939`
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/UC-064-define-milestones-and-workstreams.md): step 9, decided by `project-management:DEC-016`, tracked in `#1939`
- [UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward](../use-case-model/use-cases/UC-064-define-milestones-and-workstreams.md): variant 11a, decided by `project-management:DEC-016`, tracked in `#1939`

### Diagrams

`pkit analysis diagram --analysis project-management` prints this analysis's diagrams from the working tree. Its subjects are `use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's id.

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
