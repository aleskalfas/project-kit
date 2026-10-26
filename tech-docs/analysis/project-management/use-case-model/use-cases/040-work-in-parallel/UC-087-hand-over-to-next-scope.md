---
id: UC-087
title: Hand the next piece of the work to the scope that does it
status: active
actor: ACT-worker-agent
other-actors:
  - ACT-planning-agent
requirements:
  - REQ-040
  - REQ-041
after:
  - [UC-084]
  - [UC-083]
shortfalls:
  - at: "1a"
    issue: "#521"
    record: project-management:DEC-035#4
  - at: "4a"
    issue: "#519"
    record: project-management:DEC-035#3
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/handoff-issue.py
      record:
        - project-management:DEC-005
        - project-management:DEC-026
        - project-management:DEC-035#3
        - project-management:DEC-035#4
        - COR-017
        - COR-021
        - COR-042
      artefact:
        - ACT-worker-agent
        - ACT-planning-agent
        - REQ-040
        - REQ-041
---

# UC-087 — Hand the next piece of the work to the scope that does it

**Goal:** Hand the next piece of the work to the scope that does it, with what that piece needs from mine.

**Other actors:** **Planning agent** (`ACT-planning-agent`): filed the next piece's [Task](../../../glossary.md#term-task--task) in its own [scope](../../../glossary.md#term-scope--scope), naming this piece's Task in its `## Dependencies` section (`batch-plan.md`).

**Preconditions:**

- **From UC-084:** The worker's [instance](../../../glossary.md#term-instance--instance) owns this piece's [Task](../../../glossary.md#term-task--task), which is In Progress (DEC-026).
- **From UC-083:** The next piece's Task is filed in its own [scope](../../../glossary.md#term-scope--scope), and names this piece's Task in its `## Dependencies` section (DEC-005).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).

**Trigger:** The worker finishes its piece of the work, such as an interface that another [scope](../../../glossary.md#term-scope--scope) builds on.

**Main path:**

1. The worker finishes its [Task](../../../glossary.md#term-task--task). What the next piece needs from it, such as an interface, lies in the work the Task lands.
2. The worker lands the Task, as `UC-089` describes, and the Task closes (DEC-026).
3. The next piece's Task now names no open [issue](../../../glossary.md#term-issue--issue) in its `## Dependencies` section (DEC-005).
4. The agent of the next piece's [scope](../../../glossary.md#term-scope--scope) takes that Task, as `UC-084` describes.

**Variants:**

- **1a.** The worker hands its [Task](../../../glossary.md#term-task--task) to another [instance](../../../glossary.md#term-instance--instance) before finishing it, such as when the [topology](../../../glossary.md#term-topology--topology) moves the Task's [workstream](../../../glossary.md#term-workstream--workstream) to another [scope](../../../glossary.md#term-scope--scope): `pkit pm handoff-issue <N> --to-instance <M> --reason "<R>"`. That instance becomes the [owner](../../../glossary.md#term-owner--owner), and the Task keeps its state (DEC-035 point 4 and DEC-026).

> [!WARNING]
> **Not built yet:** `handoff-issue` hands an [issue](../../../glossary.md#term-issue--issue) from one person to another only. DEC-035 point 4 decides the hand-over between instances, and #521 tracks it.

- **4a.** The next piece's agent finds a defect in this piece. That agent files a Task in this piece's scope, as `UC-060` describes, and that agent's instance owns the Task (DEC-035 point 3). This scope's agent takes the Task over, as `UC-084` variant 2a describes.

> [!WARNING]
> **Not built yet:** `create-issue` writes no owner. DEC-035 point 3 decides that the instance that files an issue owns it, and #519 tracks it.

**Postconditions:** What the next piece needs from this piece has landed on the [default branch](../../../../core/glossary.md#term-default-branch--default-branch), and the next piece's [Task](../../../glossary.md#term-task--task) can start.

**Minimal guarantees:**

- A hand-over to another [owner](../../../glossary.md#term-owner--owner) never moves the [Task](../../../glossary.md#term-task--task) in the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) (DEC-026).

## Open for the design

What the worker needs here that no accepted record decides yet:

- **A checked hand-over between stages,** so that the next piece starts only from what this piece declared done. The core's [processes](../../../../core/glossary.md#term-process--process) can declare a hand-over that a check reports on, which COR-042 calls a hand-off contract. None is declared between stages of the work.
- **How a scope names a discipline,** such as testing, for the [seat](../../../glossary.md#term-seat--seat) that does that stage of the work. The maintainer decided on 26 October that a seat's [scope](../../../glossary.md#term-scope--scope) may name a discipline, and its form is not decided yet (`UC-084`).
- **How the next piece's agent learns that its Task can start.** While `## Dependencies` is prose, that agent reads the section of each [Task](../../../glossary.md#term-task--task). Typed `Blocked by:` lines are DEC-025's, which is proposed.
