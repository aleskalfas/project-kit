---
id: UC-013
title: Receive adopters' reports, and link each to its fix
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-adopter
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
      artefact:
        - ACT-methodology-maintainer
        - ACT-adopter
---

# UC-013 — Receive adopters' reports, and link each to its fix

**Goal:** Receive adopters' reports with their versions attached, and link each one to the issue that fixes it.

**Other actors:**

- **Adopter** (`ACT-adopter`): filed the report, and sees each issue linked to it, with that issue's state, from their own project (UC-012).

**Preconditions:** The maintainer works in a clone of the report target, project-kit's own repository, and `gh` is signed in there.

**Assumptions:** None.

**Trigger:** Adopters' reports arrive on the report target.

**Main path:**

1. The maintainer runs `pkit report inbox` in the report target's clone.
2. The system lists every report on the target, by any author, newest first, with its number, kind, state and title.
3. The maintainer reads a report, with the versions its environment block gives.
4. The maintainer files the issue that will fix the report, or finds one that exists.
5. The maintainer runs `pkit report link <report> <fix>`. The system adds `- [ ] #<fix>` under the report's `## Tracked by` heading, and prints `Linked #<fix> into #<report>'s Tracked by.`
6. Once the linked issues close, the maintainer runs `pkit report inbox --resolved`. The system lists each open feedback and change request whose linked issues are all closed.
7. For each of them, the system asks `Post a closing comment on #<n> and close it?`. On a yes, the system comments that all the tracked fixes are closed, and closes the report.

**Variants:**

- **1a.** The maintainer runs the command outside the report target's clone. The system refuses with `the maintainer side (inbox/link/unlink) runs only inside the report target repo (<target>). Cd into it and retry.` The use case ends.
- **1b.** The maintainer passes `--kind <kind>` to see one kind of report, or `--group-by project` to group the reports by the project each one names (ADR-050 point 3).
- **5a.** The maintainer linked the wrong issue. `pkit report unlink <report> <fix>` removes that issue from the report's `## Tracked by` list.
- **5b.** The issue is linked already. The system changes nothing, and reports the link done.
- **5c.** One issue fixes several reports. The maintainer links it to each of them, since any issue may stand in a report's list (PRJ-008).
- **6a.** The report is a bug, or links no issue. `--resolved` never lists such a report, so the maintainer closes the report by other means.
- **6b.** The maintainer passes `--yes`. The system lists the reports and closes none, since closing needs a person to confirm each one.
- **7a.** The maintainer declines. The system prints `Skipped #<n>.`, and the report stays open.

**Postconditions:** Each report the maintainer triaged lists, under `## Tracked by`, the issues that fix it. Each feedback or change request whose linked issues all closed is closed, with a comment saying so.

**Minimal guarantees:**

- No report is closed unless the maintainer confirms it, one report at a time (PRJ-008).
- The maintainer's commands change only issues of the report target, the repository the commands run in (ADR-047 point 4).
