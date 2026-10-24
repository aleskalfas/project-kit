---
id: UC-054
title: Upgrade one capability on its own
status: active
actor: ACT-adopter
other-actors:
  - ACT-operator
requirements:
  - REQ-001
  - REQ-002
  - REQ-009
  - REQ-010
  - REQ-012
  - REQ-026
  - REQ-029
  - REQ-030
after:
  - [UC-023, UC-016]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/capabilities.py
        - src/project_kit/upgrade.py
        - src/project_kit/sync.py
        - src/project_kit/point_questions.py
      record:
        - COR-059#3
        - COR-017
        - COR-030
        - COR-031
        - COR-053#6
        - COR-061
        - ADR-065#1
        - ADR-065#4
        - ADR-065#6
        - ADR-065#7
        - ADR-065#12
        - ADR-059
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-001
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
        - REQ-026
        - REQ-029
        - REQ-030
    revalidated:
      at: 2026-10-24T03:45:18Z
      outcome: unchanged
      unchanged-because: The change rewords only the help of `pkit release merge` in cli.py, which this artefact does not describe.
---

# UC-054 — Upgrade one capability on its own

**Goal:** Upgrade one capability on its own to the version my project's release ships, without moving the backbone.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit capabilities upgrade` writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-023 or UC-016:** The project's manifest records the capability, with its version.

**Assumptions:** None.

**Trigger:** The CLI ships the capability at a newer version than the manifest records, at the backbone version the project records. An upgrade of the capability stopped before its end, or the CLI is an untagged install (ADR-065 points 1 and 12).

**Main path:**

1. The adopter runs `pkit capabilities upgrade <name>`.
2. At its entry, before it reads anything, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit capabilities upgrade` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the backbone version the project records, and that the last version transition is complete (REQ-010).
4. The system checks that the capability is installed, and finds it among the capabilities the CLI ships.
5. Before it writes anything, the system checks the new version against the recorded backbone, and against the capabilities installed. Its range, each capability it requires and each mandatory connection it marks must hold (COR-030, COR-053 point 6 and REQ-029).
6. The system finds no new name collision that the new version's skills or agent definitions bring (ADR-065 point 6).
7. The system moves the capability's manifest under its `project/` where it still lies at the root. It copies the new version, runs the capability's migrations after the copy, then records the new version (ADR-065 point 4).
8. The system prints `Refreshed capability '<name>' -> v<version> at .pkit/capabilities/<name>/`.
9. The system runs each adapter's scripts, which deploy the capability's skills and agent definitions. It provisions the capability's query commands, and renders `.pkit/.gitignore`.
10. Where a person can answer, the system runs in turn each question the capability's data points declare (COR-061).

**Variants:**

- **1a.** The adopter passes `--dry-run`. The system runs every check, says what it would refresh, and writes nothing (REQ-009).
- **3a.** The running CLI is at another version than the project records, or the last transition is incomplete. The system stops, names the remedy and writes nothing (REQ-010). The use case ends.
- **4a.** The capability is not installed. The system refuses, naming `pkit capabilities install <name>`. The use case ends.
- **4b.** The capability was authored in the project, so it is registered as incubated. The system deploys it again from the project's own tree, and copies nothing (COR-031).
- **4c.** The project is the methodology's source repository, run by its own code. The system deploys the capability again in place, since its subtree is its source, and copies nothing (ADR-059).
- **4d.** The CLI no longer ships the capability. The system refuses, naming `pkit capabilities uninstall`. The use case ends.
- **5a.** The CLI ships the capability older than the manifest records. The system refuses, names a CLI that ships that version or newer, and writes nothing (ADR-065 point 7). The use case ends.
- **5b.** The new version's range excludes the recorded backbone, or a capability it requires is missing or out of range. The system refuses, naming each, and writes nothing (REQ-029). The use case ends.
- **5c.** The new version falls outside a range an installed capability declares for it, or leaves that capability's mandatory connection unmet. The system warns, naming each, and refuses unless the adopter passes `--force` (COR-030).
- **6a.** The new version brings a new name collision, and the adopter passed no `--interactive`. The system lists each, refuses with `refusing to upgrade with unresolved collisions. Re-run with --interactive to resolve them.`, and writes nothing (REQ-030).
- **6b.** The adopter passed `--interactive`. For each new collision, the system asks override, skip or inspect, and records each skip in the manifest (COR-017).
- **7a.** A migration fails. The system stops, and the manifest keeps the capability's old version, so the next upgrade runs the migration again (REQ-026).
- **10a.** Nobody can answer. The system runs no question, and prints each question's command for a person to run later (COR-061).

**Postconditions:** The capability holds the version the running CLI ships, at the backbone version the project records. Its migrations have run, and its manifest records that version. Its skills and agent definitions are deployed. The backbone's recorded versions did not move.

**Minimal guarantees:**

- Every check of steps 3 to 6 comes before the first write (REQ-029).
- The capability's upgrade writes neither of the backbone's recorded versions (ADR-065 point 4).
- A recorded version never moves down (ADR-065 point 7).
- No new name collision is settled silently (REQ-030).
