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
  - at: "1a"
    issue: "#1938"
    record: COR-004
  - at: "8a"
    issue: "#1936"
    record: project-management:DEC-006
  - at: "8c"
    issue: "#1937"
    record: project-management:DEC-006
  - at: "8d"
    issue: "#1936"
    record: project-management:DEC-006
  - at: "8f"
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
        - .pkit/capabilities/project-management/scripts/close-issue.py
        - .pkit/capabilities/project-management/scripts/_lib/composed_move.py
        - .pkit/capabilities/project-management/scripts/_lib/checkbox_gate.py
        - .pkit/capabilities/project-management/scripts/_lib/move_journal.py
        - .pkit/capabilities/project-management/scripts/_lib/audit.py
        - .pkit/capabilities/project-management/scripts/_lib/hooks.py
        - .pkit/capabilities/project-management/schemas/workflow.yaml
        - .pkit/capabilities/project-management/skills/pm/transition-state.md
      record:
        - project-management:DEC-006
        - project-management:DEC-007
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

- **AI agent** (`core:ACT-ai-agent`): moves the issue for the developer, through the `pm` skill's `transition-state.md`. It makes on its own only the moves the issue lifecycle leaves to it (DEC-006).
- **Operator** (`core:ACT-operator`): is asked before a command moves an issue of a repository other than the session's own, so no such move happens silently (core:REQ-012).

**Preconditions:** **From UC-060, or UC-063:** The issue is filed.

**Assumptions:**

- The project has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).
- The backbone's process engine reads where the issue stands, checks each move against the issue lifecycle's definition, and journals the move (COR-033). Where the engine cannot run, the commands read the issue's labels instead, and warn that the move was not journaled (DEC-033).

**Trigger:** The developer takes up an issue that is filed, or decides that it will not be done.

**Main path:**

1. The developer schedules the issue: `pkit pm promote-issue <N> --reason "<R>"`, with `--milestone <M>` where the project uses Milestones (DEC-006 and DEC-026).
2. At its entry, the system checks the project's setup, and the developer's membership where the team keeps a list (REQ-041). It then checks that the repository it would change is the session's own, and asks the operator where it is another (core:REQ-012).
3. The system checks that the issue lifecycle declares the move from Todo to Backlog for the issue's type. It checks too that the issue's body holds no placeholder of its template (DEC-006 and DEC-031).
4. The system posts the reason in an audit comment that names the move, then moves the issue to Backlog and attaches the Milestone. It journals the move with its reason (DEC-014 and DEC-049).

> [!WARNING]
> **Not built yet:** the audit comment says who bypassed the rule and why, and names no move. DEC-052 decides that the comment of a move names the move it made, and #756 tracks it.

5. The system runs the cascade. Each issue above that is behind is brought forward one declared move at a time, and each move is journaled with its cause (DEC-006).
6. The developer starts the work: `pkit pm start-work <N>`. The system cuts the issue's branch, assigns the developer, and moves the issue to In Progress, a move the issue lifecycle leaves to the agent. The cascade runs as in step 5 (DEC-006 and DEC-026).
7. Once the change is ready, the developer runs `pkit pm review-work <N>`. The system opens the pull request, or marks a draft ready, and moves the Task to Review (DEC-026).
8. The Task moves to Done when its pull request merges, as `UC-062` describes (DEC-006).

**Variants:**

- **1a.** The developer passes `--dry-run` to any of these commands. The system makes its checks, names each move it would make, and writes nothing (COR-004). The use case ends.

> [!WARNING]
> **Not built yet:** the dry runs of `promote-issue`, `start-work`, `review-work` and `done-work` name neither the cascade's moves nor the hooks that would fire. COR-004 decides that a dry run names each edit a run would make, and #1938 tracks it.

- **1b.** The developer gives no reason. `promote-issue` refuses before it writes, and the use case ends (DEC-014).
- **1c.** The issue is past Todo already. The system says so, and changes nothing (`promote-issue.py`).
- **2a.** The project was never set up, the developer is no member, or the operator declines a move in another repository. The system refuses and writes nothing (REQ-041 and core:REQ-012). The use case ends.
- **3a.** The issue lifecycle declares no such move for the issue's type, such as Review for an EPIC. The system refuses, naming the moves it declares, and writes nothing (DEC-006). The use case ends.
- **3b.** The issue's body still holds a placeholder of its template. The system refuses the move until the body is written (DEC-031). The use case ends.
- **5a.** A move of the cascade fails part-way. The system warns, and names the issues it did not move. Running the same move again finishes the cascade, since a move already made is not made twice (DEC-006).
- **6a.** The issue is assigned to someone else. `start-work` refuses, and changes nothing (`start-work.py`).
- **6b.** The issue is still in Todo. `start-work` refuses, names the move to make first, and changes nothing (`composed_move.py`).
- **8a.** The developer decides the issue will not be done: `pkit pm close-issue <N> --reason "<R>"`. The system checks each checkbox, posts the reason, closes the issue as not planned and moves it to Done (DEC-006 and DEC-007). The developer authorises the close, at the terminal or with `--yes`.

> [!WARNING]
> **Not built yet:** with no terminal and no `--yes`, `close-issue` closes the issue unasked. DEC-006 decides that a won't-do close is made only on the person's authorisation, and #1936 tracks it.

- **8b.** A checkbox of the issue is unticked. `close-issue` refuses, listing each one. The developer ticks it, having checked its claim, or removes it, and the path rejoins at variant 8a (DEC-007).
- **8c.** The issue closed is the last open child of its parent. The system says that the parent is eligible to close, and asks the developer to authorise its close (DEC-006).

> [!WARNING]
> **Not built yet:** after every close, the system reports the parent as "eligible to close pending sibling check". It reads the parent's checkboxes alone, whether a child is still open or not. DEC-006 decides that a parent is offered for its close once its last open child closes, and #1937 tracks it.

- **8d.** The developer authorises a container's close: `pkit pm close-issue <N> --mode=cascade-eligibility-close`. The system checks the container's checkboxes, and that its children are all done, and closes it as completed (DEC-006 and DEC-034).

> [!WARNING]
> **Not built yet:** with no terminal and no `--yes`, `close-issue` closes the container unasked. DEC-006 decides that a container's close is made only on the person's authorisation, and #1936 tracks it.

- **8e.** The container still has an open child, or an unticked checkbox. The system refuses, naming what holds it, and closes nothing (DEC-034).
- **8f.** The developer moves the issue to Done directly: `pkit pm move-issue <N> --to done`. The system checks that each checkbox is ticked before it writes (DEC-007).

> [!WARNING]
> **Not built yet:** `move-issue` writes the Done label without checking the checkboxes, and leaves the issue open. DEC-007 decides that an issue with an unticked checkbox cannot move to Done, and #1215 tracks it.

**Postconditions:** The issue is in the state its last move took it to, and each move is journaled. No issue above it is further behind than the cascade allows.

**Minimal guarantees:**

- A move the issue lifecycle does not declare is never made (DEC-006).
- The cascade never moves a child because its parent moved, and never closes a parent (DEC-006).
- A move refused at its checks writes nothing (`move-issue.py`).
- The reason for a bypass is posted before the move it allows (DEC-014).
