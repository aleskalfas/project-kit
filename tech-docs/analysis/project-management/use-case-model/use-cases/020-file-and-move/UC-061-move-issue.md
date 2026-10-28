---
id: UC-061
title: Move my issue through its lifecycle, each move checked
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
  - REQ-042
after:
  - [UC-060, UC-063]
shortfalls:
  - at: 4
    issue: "#756"
    record: project-management:DEC-052
  - at: 7
    issue: "#1761"
    record: project-management:DEC-013
  - at: "1a"
    issue: "#1938"
    record: COR-004
  - at: "7a"
    issue: "#1215"
    record: project-management:DEC-007
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/promote-issue.py
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/review-work.py
        - .pkit/capabilities/project-management/scripts/move-issue.py
        - .pkit/capabilities/project-management/scripts/sync-board.py
        - .pkit/capabilities/project-management/scripts/_lib/board_status.py
        - .pkit/capabilities/project-management/scripts/close-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/composed_move.py
        - .pkit/capabilities/project-management/scripts/_lib/checkbox_gate.py
        - .pkit/capabilities/project-management/scripts/_lib/move_journal.py
        - .pkit/capabilities/project-management/scripts/_lib/audit.py
        - .pkit/capabilities/project-management/scripts/_lib/hooks.py
        - .pkit/capabilities/project-management/schemas/workflow.yaml
        - .pkit/capabilities/project-management/skills/pm/transition-state.md
      record:
        - project-management:DEC-013
        - project-management:DEC-006
        - project-management:DEC-007
        - project-management:DEC-061#5
        - project-management:DEC-061#6
        - project-management:DEC-061#9
        - project-management:DEC-008
        - project-management:DEC-014
        - project-management:DEC-024
        - project-management:DEC-026
        - project-management:DEC-031
        - project-management:DEC-033
        - project-management:DEC-034
        - project-management:DEC-046#1
        - project-management:DEC-049
        - project-management:DEC-052
        - COR-004
        - COR-017
        - COR-021
        - COR-033
        - COR-039
        - ADR-034#1
      artefact:
        - REQ-040
        - REQ-041
        - REQ-042
---

# UC-061 — Move my issue through its lifecycle, each move checked

**Goal:** Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): moves the [issue](../../../glossary.md#term-issue--issue) for the developer, through the `pm` [skill](../../../../core/glossary.md#term-skill--skill)'s `transition-state.md`. It makes on its own only the moves the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) leaves to it ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
- **Operator** (`core:ACT-operator`): is asked before a command moves an issue of a repository other than the session's own, so no such move happens silently ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-060](UC-060-file-task.md), or [UC-063](../010-plan/UC-063-plan-intent.md):** The [issue](../../../glossary.md#term-issue--issue) is filed.

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, and the CLI registers `pkit pm` and its commands ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- The backbone's [process](../../../../core/glossary.md#term-process--process) engine reads where the [issue](../../../glossary.md#term-issue--issue) stands, checks each move against the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle)'s definition, and journals the move ([COR-033](../../../../../../.pkit/decisions/core/COR-033-process-substrate.md)). Where the engine cannot run, the commands read the issue's labels instead, and warn that the move was not journaled ([DEC-033](../../../../../../.pkit/capabilities/project-management/decisions/DEC-033-rebind-issue-lifecycle-onto-process-substrate.md)).

**Trigger:** The developer takes up an [issue](../../../glossary.md#term-issue--issue) that is filed, or decides that it will not be done.

**Main path:**

1. The developer schedules the [issue](../../../glossary.md#term-issue--issue): `pkit pm promote-issue <N> --reason "<R>"`, with `--milestone <M>` where the [project](../../../../core/glossary.md#term-project--project) uses [Milestones](../../../glossary.md#term-milestone--milestone) ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md) and [DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).
2. At its entry, the system checks the project's prerequisites, and the developer's membership where the team keeps a list ([REQ-041](../../../requirements/functional/REQ-041-gates-before-writing.md)). It then checks that the repository it would write in is the session's own, and asks the operator where it is another ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).
3. The system checks that the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) declares the move from Todo to Backlog for the issue's type. It checks too that the issue's body holds no placeholder of its template (DEC-006 and [DEC-031](../../../../../../.pkit/capabilities/project-management/decisions/DEC-031-reject-unauthored-placeholder-bodies.md)).
4. Unless the project turns [audit comments](../../../glossary.md#term-audit-comment--audit-comment) off, the system posts the reason in an audit comment that names the move, before the move ([DEC-014](../../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)). It then moves the issue to Backlog, and attaches the Milestone. Where the project keeps a journal, the move goes into it with its reason ([DEC-049](../../../../../../.pkit/capabilities/project-management/decisions/DEC-049-audit-journal-model.md)).

> [!WARNING]
> **Not built yet:** the audit comment says who bypassed the check and why, and names no move. [DEC-052](../../../../../../.pkit/capabilities/project-management/decisions/DEC-052-comment-house-style.md) decides that the comment of a move names the move it made, and #756 tracks it.

5. The system runs the [cascade](../../../glossary.md#term-cascade--cascade). Each issue above that is behind is brought forward, one declared move at a time (DEC-006). Where a journal is kept, each move goes into it with its cause.
6. The developer starts the work: `pkit pm start-work <N>`. The system cuts the issue's branch, assigns the developer, and moves the issue to In Progress, a move the issue lifecycle leaves to the agent. The cascade runs as in step 5 (DEC-006 and DEC-026).
7. Once the [change](../../../../core/glossary.md#term-change--change) is ready, the developer runs `pkit pm review-work <N>`. The system checks the [pull request](../../../../core/glossary.md#term-pull-request--pull-request)'s title against its conventions, and opens the pull request or marks a draft ready ([DEC-013](../../../../../../.pkit/capabilities/project-management/decisions/DEC-013-branch-and-pr-conventions.md)). It moves the [Task](../../../glossary.md#term-task--task) to Review (DEC-026).

> [!WARNING]
> **Not built yet:** `review-work` checks no title. DEC-013 decides that the title is checked as the pull request opens, and #1761 tracks it.

**Variants:**

- **1a.** The developer passes `--dry-run` to any of these commands. The system makes its checks, names each move it would make, and writes nothing ([COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md)). The use case ends.

> [!WARNING]
> **Not built yet:** the dry runs of `promote-issue`, `start-work` and `review-work` name neither the [cascade](../../../glossary.md#term-cascade--cascade)'s moves nor the hooks that would fire. That of `close-issue` lists no hook. COR-004 decides that a dry run names each edit a run would make, and #1938 tracks it.

- **1b.** The developer gives no reason. `promote-issue` refuses before it writes, and the use case ends ([DEC-014](../../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)).
- **1c.** The [issue](../../../glossary.md#term-issue--issue) is past Todo already. The system says so, and changes nothing (`promote-issue.py`).
- **2a.** The [project](../../../../core/glossary.md#term-project--project) does not meet the prerequisites, the developer is no member, or the operator declines a move in another repository. The system refuses and writes nothing ([REQ-041](../../../requirements/functional/REQ-041-gates-before-writing.md) and [core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)). The use case ends.
- **3a.** The [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) declares no such move for the issue's type, such as Review for an [EPIC](../../../glossary.md#term-epic--epic). The system refuses, naming the moves the issue lifecycle declares, and writes nothing ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). The use case ends.
- **3b.** The issue's body still holds a placeholder of its template. The system refuses the move until the body is written ([DEC-031](../../../../../../.pkit/capabilities/project-management/decisions/DEC-031-reject-unauthored-placeholder-bodies.md)). The use case ends.
- **4a.** The project keeps a Projects v2 board that does not carry the state. With each move, the system sets the card's Status to the issue's new state, and the cascade sets the Status of each issue above ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). A Status the system cannot write is one line, and the move stands. `pkit pm sync-board` sets the cards again from the issues' states.
- **5a.** A move of the cascade fails part-way. The system warns, and names the issues it did not move. Running the same move again finishes the cascade, since a move already made is not made twice ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
- **6a.** The issue is assigned to someone else. `start-work` refuses, and changes nothing (`start-work.py`).
- **6b.** The issue is still in Todo. `start-work` refuses, names the move to make first, and changes nothing (`composed_move.py`).
- **1d.** While the issue is in Todo or Backlog, the developer decides that it will not be done: `pkit pm close-issue <N> --reason "<R>"`. The system checks each [checkbox](../../../glossary.md#term-checkbox--checkbox), then asks the developer at the terminal to authorise the close, or takes `--yes` as that [authorisation](../../../glossary.md#term-authorisation--authorisation) ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md) and [DEC-007](../../../../../../.pkit/capabilities/project-management/decisions/DEC-007-checkbox-validation.md)). With no terminal and no `--yes`, the system refuses and writes nothing. Once the close is authorised, the system posts the reason, closes the issue as not planned and moves it to Done (DEC-006 and DEC-007).
- **1e.** A checkbox of the issue is unticked. `close-issue` refuses, listing each one. The developer ticks it, having checked its claim, or removes it, and the path rejoins at variant 1d ([DEC-007](../../../../../../.pkit/capabilities/project-management/decisions/DEC-007-checkbox-validation.md)).
- **1f.** The issue closed is the last open child of its parent. The system asks the [process](../../../../core/glossary.md#term-process--process) engine whether the parent has an open child left, and says that the parent has none ([DEC-034](../../../../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md)). A parent whose checkboxes are all ticked too is said to be eligible to close, with the command of variant 6c ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). That command asks the developer to authorise the close.
- **1g.** The developer schedules a [Task](../../../glossary.md#term-task--task) into a [Milestone](../../../glossary.md#term-milestone--milestone) in a [pool](../../../glossary.md#term-pool--pool) of workers, or moves it from one pool to another. The system asks the developer at the terminal, or takes `--yes` as that [consent](../../../../core/glossary.md#term-consent--consent), and with neither refuses and writes nothing ([DEC-061 point 6](../../../../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md#6-putting-work-into-a-pool-is-the-persons-act)). The [audit comment](../../../glossary.md#term-audit-comment--audit-comment) of step 4 records the consent. An `assign-milestone` hook that sets such a Milestone asks the same way.
- **6c.** The issue is a parent issue with no open child, and the developer authorises its close: `pkit pm close-issue <N> --mode=cascade-eligibility-close`. The system checks the parent issue's checkboxes, and that it has no open child ([DEC-034](../../../../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md)). The authorisation is the developer's yes at the terminal, or `--yes`, and with neither the system refuses and writes nothing ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)). Once the close is authorised, the system closes the parent issue as completed (DEC-006 and DEC-034).
- **6d.** The parent issue still has an open child, or an unticked checkbox. The system refuses, naming what holds it, and closes nothing ([DEC-034](../../../../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md)).
- **6e.** The developer's clone holds a [seat](../../../glossary.md#term-seat--seat), and its code cannot read the [topology](../../../glossary.md#term-topology--topology) in full. `start-work` makes no claim, says what it did not understand, and changes nothing ([DEC-061 point 9](../../../../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md#9-code-that-cannot-read-the-topology-in-full-uses-none-of-the-authority-it-grants)).
- **6f.** The topology declares pools, and the Task is in none of the pools the developer's seat serves. `start-work` warns, and starts the Task as directed, since the warning is never a gate ([DEC-061 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md#5-a-seat-that-builds-chooses-its-work-only-from-its-pools)).
- **7a.** The developer moves the Task to Done directly: `pkit pm move-issue <N> --to done`. The system checks that each checkbox is ticked before it writes ([DEC-007](../../../../../../.pkit/capabilities/project-management/decisions/DEC-007-checkbox-validation.md)).

> [!WARNING]
> **Not built yet:** `move-issue` writes the Done label without checking the checkboxes, and leaves the issue open. DEC-007 decides that an issue with an unticked checkbox cannot move to Done, and #1215 tracks it.

**Postconditions:** The [Task](../../../glossary.md#term-task--task) is in Review, its [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is open, and each [issue](../../../glossary.md#term-issue--issue) above it is in In Progress or later. An issue closed as won't do is in Done.

**Minimal guarantees:**

- A move the [issue lifecycle](../../../glossary.md#term-issue-lifecycle--issue-lifecycle) does not declare is never made ([DEC-006](../../../../../../.pkit/capabilities/project-management/decisions/DEC-006-state-machine-and-cascade.md)).
- The [cascade](../../../glossary.md#term-cascade--cascade) never moves a child because its parent moved, and never closes a parent (DEC-006).
- A move refused at its checks writes nothing (`move-issue.py`).
- Unless the [project](../../../../core/glossary.md#term-project--project) turns [audit comments](../../../glossary.md#term-audit-comment--audit-comment) off, the reason for a [bypass](../../../glossary.md#term-bypass--bypass) is posted before the move it allows ([DEC-014](../../../../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md) and [DEC-049](../../../../../../.pkit/capabilities/project-management/decisions/DEC-049-audit-journal-model.md)).
