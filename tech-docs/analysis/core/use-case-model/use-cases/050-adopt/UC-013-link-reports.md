---
id: UC-013
title: Receive adopters' reports, and link each to its fix
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-adopter
  - ACT-operator
after:
  - [UC-012]
requirements:
  - REQ-005
  - REQ-012
shortfalls:
  - at: 5
    issue: "#1765"
    record: ADR-034#1
  - at: 7
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/report.py
        - src/project_kit/cli.py
      record:
        - PRJ-008
        - ADR-047#4
        - ADR-050#3
        - ADR-034#1
      artefact:
        - ACT-methodology-maintainer
        - ACT-adopter
        - ACT-operator
        - REQ-005
        - REQ-012
---

# UC-013 — Receive adopters' reports, and link each to its fix

**Goal:** Receive adopters' reports with their versions attached, and link each one to the issue that fixes it.

**Other actors:**

- **Adopter** (`ACT-adopter`): filed the [report](../../../glossary.md#term-report--report), and sees each tracked fix with that fix's state, from their own [project](../../../glossary.md#term-project--project) (UC-012).
- **Operator** (`ACT-operator`): is asked before a command changes the hosting service for a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-012:** Adopters' reports arrive as issues on the [report](../../../glossary.md#term-report--report) target, project-kit's own repository, each with its [versions](../../../glossary.md#term-version--version) attached.

**Assumptions:**

- `gh` is signed in, as a maintainer who may comment on and close the [report](../../../glossary.md#term-report--report) target's issues (PRJ-008).

**Trigger:** Adopters' reports arrive on the [report](../../../glossary.md#term-report--report) target, project-kit's own repository.

**Main path:**

1. The maintainer runs `pkit report inbox` in a clone of the [report](../../../glossary.md#term-report--report) target.
2. The [system](../../../glossary.md#term-system--system) lists the reports on the report target, by any author, newest first, with each one's number, kind, state and title. It reads at most the latest 100 issues of each search it runs (`report.py`). It writes nothing (REQ-005).
3. The maintainer reads a report on the hosting service, with the [versions](../../../glossary.md#term-version--version) its environment block gives.
4. The maintainer files the issue that will fix the report, or finds one that exists.
5. The maintainer runs `pkit report link <report> <fix>`. The system adds `- [ ] #<fix>` under the report's `## Tracked by` heading, which makes that issue one of the report's tracked fixes. The system prints `Linked #<fix> into #<report>'s Tracked by.`

> [!WARNING]
> **Not built yet:** `pkit report link` checks only that the repository of the working directory is the report target, never that it is the session's own. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes checks the session's own repository first, and #1765 tracks it.

6. Once the tracked fixes close, the maintainer runs `pkit report inbox --resolved`. The system lists each open `feedback` or `change-request` report whose tracked fixes are all closed.
7. For each listed report, the system asks `Post a closing comment on #<n> and close it?`. On a yes, the system comments that all the report's tracked fixes are closed, and closes the report.

> [!WARNING]
> **Not built yet:** `pkit report inbox --resolved` checks only that the repository of the working directory is the report target, never that it is the session's own. ADR-034 point 1 decides that every `pkit` command that writes checks the session's own repository first, and #1765 tracks it.


**Variants:**

- **1a.** The maintainer runs the command outside a clone of the [report](../../../glossary.md#term-report--report) target. The [system](../../../glossary.md#term-system--system) refuses with `the maintainer side (inbox/link/unlink) runs only inside the report target repo (<target>). Cd into it and retry.` The use case ends.
- **1b.** The maintainer passes `--kind <kind>` to see one kind of report. Or the maintainer passes `--group-by project`, to group the reports by the [project](../../../glossary.md#term-project--project) each one names (ADR-050 [point](../../../glossary.md#term-point--point) 3).
- **5a.** The maintainer linked the wrong issue. `pkit report unlink <report> <fix>` removes that issue from the report's tracked fixes.
- **5b.** The issue is one of the report's tracked fixes already. The system changes nothing, and still prints `Linked #<fix> into #<report>'s Tracked by.`
- **5c.** One issue fixes several reports. The maintainer links that issue to each of them, since one issue may be a tracked fix of several reports (PRJ-008).
- **6a.** The report is of the `bug` kind, or has no tracked fix. `--resolved` never lists such a report, so the maintainer closes the report by other means.
- **6b.** The maintainer passes `--yes`. The system lists the reports and closes none, since closing needs a person to confirm each one.
- **7a.** The maintainer declines. The system prints `Skipped #<n>.`, and the report stays open.

**Postconditions:** Each [report](../../../glossary.md#term-report--report) the maintainer triaged lists its tracked fixes under `## Tracked by`. Each `feedback` or `change-request` report whose tracked fixes all closed is closed, with a comment saying so.

**Minimal guarantees:**

- No [report](../../../glossary.md#term-report--report) is closed unless the maintainer confirms it, one report at a time (PRJ-008).
- The maintainer's commands edit only issues of the report target, the repository the commands run in (ADR-047 [point](../../../glossary.md#term-point--point) 4).
