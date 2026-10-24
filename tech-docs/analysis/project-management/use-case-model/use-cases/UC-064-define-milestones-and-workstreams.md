---
id: UC-064
title: Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward
status: active
actor: ACT-planner
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
shortfalls:
  - at: 4
    issue: "#1939"
    record: project-management:DEC-016
  - at: 9
    issue: "#1939"
    record: project-management:DEC-016
  - at: "11a"
    issue: "#1939"
    record: project-management:DEC-016
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/create-milestone.py
        - .pkit/capabilities/project-management/scripts/close-milestone.py
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
        - .pkit/capabilities/project-management/scripts/edit-issue.py
        - .pkit/capabilities/project-management/scripts/add-workstream.py
        - .pkit/capabilities/project-management/scripts/edit-workstream.py
        - .pkit/capabilities/project-management/scripts/rename-workstream.py
        - .pkit/capabilities/project-management/scripts/merge-workstream.py
        - .pkit/capabilities/project-management/scripts/split-workstream.py
        - .pkit/capabilities/project-management/scripts/remove-workstream.py
        - .pkit/capabilities/project-management/scripts/_lib/workstreams.py
        - .pkit/capabilities/project-management/scripts/_lib/workstream_sync.py
        - .pkit/capabilities/project-management/schemas/time-containers.yaml
        - .pkit/capabilities/project-management/schemas/workstreams.schema.json
      record:
        - project-management:DEC-012
        - project-management:DEC-016
        - project-management:DEC-018
        - project-management:DEC-046
        - project-management:DEC-051
        - COR-017
        - COR-021
        - COR-039
        - ADR-034#1
      artefact:
        - ACT-planner
        - REQ-040
        - REQ-041
    revalidated:
      at: 2026-10-24T05:49:41Z
      outcome: updated
---

# UC-064 — Define the Milestones and workstreams the work falls into, and roll a date-based Milestone forward

**Goal:** Define the Milestones and long-lived workstreams the work falls into, and have a date-based Milestone roll its open work forward when it closes.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): runs the commands for the planner, and lists a Milestone's open issues for the planner to triage before its due date (DEC-016).
- **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:** None.

**Assumptions:**

- The project has project-management installed, and the CLI registers `pkit pm` and its commands (COR-017 and COR-021).

**Trigger:** The planner plans a window of work or a long-lived area of it, or a Milestone reaches its due date.

**Main path:**

1. The planner declares the project's Milestone categories in the capability's settings. Each has its title format, its default close trigger and what it means (DEC-016).
2. The planner creates a Milestone: `pkit pm create-milestone <category> --name "<name>" --due-on <date>`.
3. At its entry, the system checks the project's prerequisites, and the planner's membership where the team keeps a list (REQ-041). It then checks that the repository it would change is the session's own, and asks the operator where it is another (core:REQ-012).
4. The system checks that the category is declared, and builds the title from its format. Where the format holds a number, the system numbers the Milestone after the last of its category (DEC-016).

> [!WARNING]
> **Not built yet:** `create-milestone` refuses a format that holds no number. DEC-016 decides that a Milestone's number is optional, and #1939 tracks it.

5. The system creates the Milestone, its description opening with `Close trigger: <trigger>`, and prints `[ok] created: <url>` (DEC-016).
6. The planner adds a workstream: `pkit pm add-workstream <slug> --name "<name>" --description "<text>"`. The system runs the checks of step 3.
7. The system checks the slug and each attribute against what DEC-018 decides of their form, and writes the workstream into the project's workstreams file. It creates the label `workstream:<slug>`, or adds the workstream to the board's field where a board carries the axis (DEC-018).
8. Work is filed into the Milestone and the workstream, as `UC-060` and `UC-063` describe.
9. A few days before a date-based Milestone's due date, the agent lists its open issues for the planner to triage (DEC-016).

> [!WARNING]
> **Not built yet:** nothing reads `pre_close_triage_lead_days`, and nothing lists the open issues. DEC-016 decides that the triage is offered before the due date, and #1939 tracks it.

10. Once the due date has passed, the planner closes the Milestone: `pkit pm close-milestone <M>`. The system runs the checks of step 3.
11. The system reads the close trigger, and finds the Milestone's issues. A date-based Milestone closes whether issues are still open or not (DEC-016).
12. The system finds where the open issues roll forward to. That is the Milestone the description names as `Rollforward target:`, or else the next open one of its category (DEC-016).
13. The system closes the Milestone, with a line that records its trigger and what rolled forward. It moves each open issue to the target, each with an audit comment, and keeps each issue's state. It prints `[ok] rolled <n> open child issue(s) forward to <target>` (DEC-016).

**Variants:**

- **2a.** The planner passes `--dry-run` to any of these commands. The system makes its checks, prints what it would create, change or move, and writes nothing. The use case ends.
- **3a.** The project does not meet the prerequisites, the planner is no member, or the operator declines a write in another repository. The system refuses and writes nothing (REQ-041 and core:REQ-012). The use case ends.
- **4a.** The category is not declared, or the project declares none. The system refuses, names the declared categories, and creates nothing (DEC-016). The use case ends.
- **4b.** A Milestone of that title exists. The system refuses, and asks for `--number` (`create-milestone.py`). The use case ends.
- **7a.** The slug is malformed, or a workstream of that slug exists. The system refuses, and writes nothing (DEC-018). The use case ends.
- **7b.** The planner renames a workstream: `pkit pm rename-workstream <old> <new>`. The system checks the new slug, and the old and the new label or board option, before it changes anything. Where both exist, it refuses and changes nothing. Otherwise it renames the label or board option first, then renames the entry, so the workstream's issues carry the new label or board option (DEC-018).
- **7c.** The planner merges workstreams: `pkit pm merge-workstream --survivor <S> <L>`. The system counts the issues of each workstream it removes, and moves them to the survivor. It rewrites the references to the removed workstreams, and deletes their labels or board options (DEC-018).
- **7d.** The planner splits a workstream: `pkit pm split-workstream --source <S> --into <A> --into <B>`. The system adds the new workstreams, and asks of each issue of the source which one it moves to (DEC-018). Where the system cannot ask, it takes the answers `--assign` and `--default` give, and refuses while an issue has none (`split-workstream.py`).
- **7e.** The planner removes a workstream: `pkit pm remove-workstream <slug>`. The system refuses while any issue carries it, on whatever substrate carries the axis. Otherwise it asks the planner to type the slug, removes the entry and deletes the label (DEC-018).
- **11a.** The Milestone's description holds no close trigger. The system infers one, date-based where the Milestone has a due date, and warns. It offers to write the trigger into the description (DEC-016).

> [!WARNING]
> **Not built yet:** `close-milestone` prints `(inferred)` beside the trigger, and neither warns nor offers to write it. DEC-016 decides that it warns and offers, and #1939 tracks it.

- **11b.** A content-based Milestone, or one marked `either` before its due date, still holds open issues. The system refuses to close it, and closes nothing (DEC-016). The use case ends.
- **11c.** The planner passes `--force` on such a Milestone. The system warns, and closes it, with its open issues left in it (DEC-046).
- **11d.** No issue under the Milestone is open. The system closes it, and rolls nothing forward (DEC-016). The use case ends.
- **12a.** No Milestone of the category comes next, or more than one could. The system refuses, moves and closes nothing, and asks for `--target` (`close-milestone.py`). The planner runs the command again with it, and the path rejoins at step 10.
- **13a.** A move of an issue fails. The system has closed the Milestone, names the issues it did not move, and exits `4`. Running the command again finishes the moves, to the target it recorded (`close-milestone.py`).

**Postconditions:** The Milestones and workstreams the planner defined exist, and the project's workstreams file holds each workstream. A closed date-based Milestone holds its closed issues, and its open ones are in the next.

**Minimal guarantees:**

- A Milestone whose close trigger has not fired never closes with open issues, unless the planner passes `--force` (DEC-016 and DEC-046).
- Rolling an issue forward never changes its state in the issue lifecycle (`edit-issue.py`).
- A rollforward that stops part-way is finished by running the same command again (`close-milestone.py`).
