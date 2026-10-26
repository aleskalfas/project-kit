---
id: UC-060
title: File a Task under its parent, its title and body checked as it is filed
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-064]
  - [UC-063, UC-064]
shortfalls:
  - at: 6
    issue: "#1313"
    record: project-management:DEC-005
  - at: 8
    issue: "#1314"
    record: project-management:DEC-005
  - at: "6c"
    issue: "#1313"
    record: project-management:DEC-005
  - at: "6e"
    issue: "#1314"
    record: project-management:DEC-005
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/create-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/title_rules.py
        - .pkit/capabilities/project-management/scripts/_lib/body_parent_ref.py
        - .pkit/capabilities/project-management/scripts/_lib/body_rules.py
        - .pkit/capabilities/project-management/scripts/_lib/placeholder_detection.py
        - .pkit/capabilities/project-management/scripts/_lib/use_case_citations.py
        - .pkit/capabilities/project-management/scripts/_lib/decision_ids.py
        - .pkit/capabilities/project-management/scripts/_lib/containment.py
        - .pkit/capabilities/project-management/scripts/_lib/session_guard.py
        - .pkit/capabilities/project-management/schemas/issue-types.yaml
        - .pkit/capabilities/project-management/schemas/body-format.yaml
        - .pkit/capabilities/project-management/schemas/titles.yaml
        - .pkit/capabilities/project-management/schemas/classification.yaml
        - .pkit/capabilities/project-management/templates/Task.md
        - .pkit/capabilities/project-management/skills/pm/create-issue.md
      record:
        - project-management:DEC-036
        - project-management:DEC-004
        - project-management:DEC-005
        - project-management:DEC-010
        - project-management:DEC-011
        - project-management:DEC-012
        - project-management:DEC-014
        - project-management:DEC-018
        - project-management:DEC-031
        - project-management:DEC-039
        - project-management:DEC-041
        - project-management:DEC-054#4
        - COR-005
        - COR-013
        - COR-017
        - COR-021
        - COR-031
        - COR-039
        - ADR-034#1
      artefact:
        - REQ-040
        - REQ-041
---

# UC-060 — File a Task under its parent, its title and body checked as it is filed

**Goal:** File a Task under its parent, with its title and the sections its body needs checked as it is filed.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): files the [Task](../../../glossary.md#term-task--task) for the developer, through the `pm` [skill](../../../../core/glossary.md#term-skill--skill)'s `create-issue.md`, which runs the same command.
- **Operator** (`core:ACT-operator`): is asked before `pkit pm create-issue` writes in a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:**

- **From UC-064:** The [project](../../../../core/glossary.md#term-project--project) declares the [workstreams](../../../glossary.md#term-workstream--workstream) its work falls into (DEC-018).
- **From UC-063, or UC-064:** The [issue](../../../glossary.md#term-issue--issue) the [Task](../../../glossary.md#term-task--task) goes under is filed, or the [Milestone](../../../glossary.md#term-milestone--milestone) it goes straight under is created (DEC-004).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, or registered in place where project-management is developed (COR-017 and COR-031). The CLI registers `pkit pm` and its commands from the [capability](../../../../core/glossary.md#term-capability--capability)'s package metadata (COR-021). The adapter deploys the `pm` [skill](../../../../core/glossary.md#term-skill--skill) (COR-005 and COR-013).
- Where the body cites [use-case entries](../../../glossary.md#term-use-case-entry--use-case-entry), the backbone resolves the [data point](../../../../core/glossary.md#term-data-point--data-point) that holds them (DEC-054 point 4).
- Where the body cites a decision id, the backbone looks up the decision record that holds it (DEC-010).

**Trigger:** The developer has a unit of work to track, such as a bug found while working on a [Feature](../../../glossary.md#term-feature--feature).

**Main path:**

1. The developer chooses the [Task](../../../glossary.md#term-task--task)'s parent, its title, its kind of work, its priority and its [workstream](../../../glossary.md#term-workstream--workstream) (DEC-004 and DEC-012).
2. The developer writes the body in a file, opening with the [parent reference](../../../glossary.md#term-parent-reference--parent-reference), or leaves the body to the Task's template (DEC-010).
3. The developer runs `pkit pm create-issue --type task --title "<title>" --parent <N>`, with `--kind`, `--priority`, `--workstream` and, where they wrote one, `--body-file`.
4. At its entry, the system checks the [project](../../../../core/glossary.md#term-project--project)'s prerequisites, and the developer's membership where the team keeps a list (REQ-041). It then checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (core:REQ-012).
5. The system composes the title from the kind's prefix and `<title>`, such as `[Bug] <title>`, and checks it against the title formats the [capability](../../../../core/glossary.md#term-capability--capability) declares (DEC-011).
6. The system reads the parent's type, and checks that a Task may sit under it: a [Feature](../../../glossary.md#term-feature--feature), an [Umbrella](../../../glossary.md#term-umbrella--umbrella) or an [EPIC](../../../glossary.md#term-epic--epic) (DEC-005).

> [!WARNING]
> **Not built yet:** `create-issue` reads the parent's type only to label the body's first line, and checks no containment. DEC-005 decides that a filing that breaks the containment graph is refused, and #1313 tracks it.

7. The system checks that the Task takes a value on each [classification axis](../../../glossary.md#term-classification-axis--classification-axis), from the values the project allows. Its workstream must be one that the project's workstreams file holds as active (DEC-012 and DEC-018).
8. The system composes the body: its first line is the parent reference, such as `Feature: #12`, then the Task's sections (DEC-010). Where the developer gave a file, the system checks that the file's first line is a Task's parent reference, naming the parent of `--parent` (DEC-005).

> [!WARNING]
> **Not built yet:** the template opens with a comment, and the composed body puts the parent reference below it. So the body's first line names no parent. DEC-005 decides that every body opens with its parent reference, and #1314 tracks it.

9. The system checks that the body holds each section a Task requires: `## What`, `## Acceptance criteria` and `## Doc impact`. It checks too that the body holds no heading of the first level, since the title is that heading. It warns of what a body should not hold, such as a reference to a line of a file (DEC-010).

10. The system reports each placeholder of the template left in the body, and each [use-case entry](../../../glossary.md#term-use-case-entry--use-case-entry) the body cites that the [data point](../../../../core/glossary.md#term-data-point--data-point) lacks. It reports too each decision id the body cites that no decision record holds (DEC-010). None of these stops the filing (DEC-031 and DEC-054 point 4).
11. The system prints the Task it is about to file, with its title, type, kind, priority, workstream, parent and labels. At a terminal, without `--yes`, it asks before it writes.
12. The system files the Task, with its labels and its assignee, and prints `[ok] created: <url>`. It posts a comment that records the versions it was filed under (DEC-041).
13. The system links the Task to its parent as a GitHub sub-issue, and prints `[ok] linked #<n> as a native sub-issue of #<N>` (DEC-005 and DEC-039).

**Variants:**

- **1a.** An AI agent files the [Task](../../../glossary.md#term-task--task) for the developer, through the `pm` [skill](../../../../core/glossary.md#term-skill--skill)'s `create-issue.md`. It infers the kind and the [workstream](../../../glossary.md#term-workstream--workstream) from the request, and asks where it is unsure (DEC-012). The path goes on at step 3.
- **3a.** The developer passes `--dry-run`. The system makes the checks of steps 4 to 10, prints the Task as step 11 does, and writes nothing. The use case ends.
- **4a.** The [project](../../../../core/glossary.md#term-project--project) does not meet the prerequisites, or the developer is no member of a team that keeps a list. The system refuses, names the cause, and writes nothing (REQ-041). The use case ends.
- **4b.** The repository is another, and the operator declines, or nobody can reply and the developer passed no `--allow-foreign-repo`. The system refuses and writes nothing. The use case ends.
- **5a.** The composed title fails a check that blocks, such as one on a conventional-commits prefix. The system refuses, naming the check, and writes nothing (DEC-011). A check that only warns, such as one on a short title, is printed, and the path goes on.
- **6a.** No parent is given. The system refuses, naming the types a Task may sit under, and writes nothing (DEC-004). The use case ends.
- **6b.** The developer passes `--milestone <M>` in place of a parent, since the project skips the [EPIC](../../../glossary.md#term-epic--epic) for that [Milestone](../../../glossary.md#term-milestone--milestone) (DEC-004). The [parent reference](../../../glossary.md#term-parent-reference--parent-reference) names the Milestone, as `Milestone: [#<M>](../milestone/<M>)`, and the Task is filed in it. The path goes on at step 7.
- **6c.** The parent is of a type a Task may not sit under, such as another Task. The system refuses, naming the types a Task may sit under, and writes nothing (DEC-005). The use case ends.

> [!WARNING]
> **Not built yet:** `create-issue` warns at most, and files the Task under that parent. DEC-005 decides that the filing is refused, and #1313 tracks it.

- **6d.** The project declares its hierarchy advisory, since its tracker cannot carry one (DEC-036). With no parent, the system warns, and files the Task. The path goes on at step 7.
- **6e.** The developer passes both `--parent <N>` and `--milestone <M>`. The parent reference names `<N>`, and the Task is filed in the Milestone as well (DEC-005).

> [!WARNING]
> **Not built yet:** `create-issue` writes the Milestone into the body's first line, while it links the Task under `<N>`. DEC-005 decides that the first line names the parent, and #1314 tracks it.

- **7a.** A label carries the workstream, none is given, and the project's settings give no default. The system refuses, and writes nothing (DEC-012). The use case ends.
- **7b.** The workstreams file lacks the given workstream, or holds it as deprecated. The system refuses, naming the active workstreams, and writes nothing (DEC-012 and DEC-018). The use case ends.
- **8a.** The file's first line is no parent reference of a Task's forms, or it names a parent other than `--parent`. The system refuses, quoting the forms, and writes nothing (DEC-005). The use case ends.
- **9a.** The body lacks a section a Task requires, or holds a heading of the first level. The system refuses, naming what is wrong, and writes nothing (DEC-010). The use case ends.

- **10a.** The body still holds a placeholder of the template. The system warns, and files the Task. Its first move of the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) is then refused until the body is written (DEC-031).
- **11a.** The developer answers no at the terminal. The system writes nothing, and the use case ends.
- **12a.** GitHub refuses the filing. The system says so and exits `3`, and nothing is filed. The use case ends.
- **13a.** The link to the parent fails. The system warns that the Task is filed under its parent by its body alone, and names `pkit pm link-parent <n>`, which makes the link (DEC-005). The use case ends with the Task filed.
- **13b.** The project keeps containment as text, where its GitHub has no sub-issues. The system makes no link, and rewrites the comment on the parent that lists its children (DEC-039).

**Postconditions:**

- The [Task](../../../glossary.md#term-task--task) is open, under its parent as a GitHub sub-issue and in its body's first line, wherever the [project](../../../../core/glossary.md#term-project--project)'s hierarchy is not advisory.
- The Task's title carries its kind's prefix.
- The Task takes a value on each [classification axis](../../../glossary.md#term-classification-axis--classification-axis).
- The Task's body holds each section a Task requires.

**Minimal guarantees:**

- A refusal before step 12 files nothing (`create-issue.py`).
- The system never files the [Task](../../../glossary.md#term-task--task) in another repository without the operator's yes, or a confirmation passed with the call (core:REQ-012).
- A comment of the versions that fails to post never stops the filing (DEC-041).
