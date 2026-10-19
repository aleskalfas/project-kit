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
    revalidated:
      at: 2026-10-19T06:40:57Z
      outcome: unchanged
      unchanged-because: cli.py changed only in migrations check-diff, which also fails a script whose number its folder holds. The report commands this use case describes are untouched.
---

# UC-013 — Receive adopters' reports, and link each to its fix

**Goal:** Receive adopters' reports with their versions attached, and link each one to the issue that fixes it.

**Other actors:**

- **Adopter** (`ACT-adopter`): filed the report, and sees each tracked fix with that fix's state, from their own project (UC-012).

**Preconditions:** None.

**Assumptions:** None.

**Trigger:** Adopters' reports arrive on the report target, project-kit's own repository.

**Main path:**

1. The maintainer runs `pkit report inbox` in a clone of the report target.
2. The system lists the reports on the report target, by any author, newest first, with each one's number, kind, state and title. It reads at most the latest 100 issues of each search it runs (`report.py`).
3. The maintainer reads a report on the hosting service, with the versions its environment block gives.
4. The maintainer files the issue that will fix the report, or finds one that exists.
5. The maintainer runs `pkit report link <report> <fix>`. The system adds `- [ ] #<fix>` under the report's `## Tracked by` heading, which makes that issue one of the report's tracked fixes. The system prints `Linked #<fix> into #<report>'s Tracked by.`
6. Once the tracked fixes close, the maintainer runs `pkit report inbox --resolved`. The system lists each open feedback and change request whose tracked fixes are all closed.
7. For each listed report, the system asks `Post a closing comment on #<n> and close it?`. On a yes, the system comments that all the report's tracked fixes are closed, and closes the report.

**Variants:**

- **1a.** The maintainer runs the command outside a clone of the report target. The system refuses with `the maintainer side (inbox/link/unlink) runs only inside the report target repo (<target>). Cd into it and retry.` The use case ends.
- **1b.** The maintainer passes `--kind <kind>` to see one kind of report. Or the maintainer passes `--group-by project`, to group the reports by the project each one names (ADR-050 point 3).
- **5a.** The maintainer linked the wrong issue. `pkit report unlink <report> <fix>` removes that issue from the report's tracked fixes.
- **5b.** The issue is one of the report's tracked fixes already. The system changes nothing, and still prints `Linked #<fix> into #<report>'s Tracked by.`
- **5c.** One issue fixes several reports. The maintainer links that issue to each of them, since one issue may be a tracked fix of several reports (PRJ-008).
- **6a.** The report is of the `bug` kind, or has no tracked fix. `--resolved` never lists such a report, so the maintainer closes the report by other means.
- **6b.** The maintainer passes `--yes`. The system lists the reports and closes none, since closing needs a person to confirm each one.
- **7a.** The maintainer declines. The system prints `Skipped #<n>.`, and the report stays open.

**Postconditions:** Each report the maintainer triaged lists its tracked fixes under `## Tracked by`. Each feedback or change request whose tracked fixes all closed is closed, with a comment saying so.

**Minimal guarantees:**

- No report is closed unless the maintainer confirms it, one report at a time (PRJ-008).
- The maintainer's commands change only issues of the report target, the repository the commands run in (ADR-047 point 4).
