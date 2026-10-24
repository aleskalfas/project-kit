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
      at: 2026-10-24T20:58:31Z
      outcome: updated
---

# UC-054 — Upgrade one capability on its own

**Goal:** Upgrade one capability on its own to the version my project's release ships, without moving the backbone.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit capabilities upgrade` writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-023 or UC-016:** The [project](../../../glossary.md#term-project--project)'s [manifest](../../../glossary.md#term-manifest--manifest) records the [capability](../../../glossary.md#term-capability--capability), with its [version](../../../glossary.md#term-version--version).

**Assumptions:** None.

**Trigger:** The CLI ships the [capability](../../../glossary.md#term-capability--capability) at a newer [version](../../../glossary.md#term-version--version) than the [manifest](../../../glossary.md#term-manifest--manifest) records, at the [backbone](../../../glossary.md#term-backbone--backbone) version the [project](../../../glossary.md#term-project--project) records. An upgrade of the capability stopped before its end, or the CLI was installed from no tag (ADR-065 points 1 and 12).

**Main path:**

1. The adopter runs `pkit capabilities upgrade <name>`.
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit capabilities upgrade` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the [backbone](../../../glossary.md#term-backbone--backbone) [version](../../../glossary.md#term-version--version) the [project](../../../glossary.md#term-project--project) records, and that the last [version transition](../../../glossary.md#term-version-transition--version-transition) is complete (REQ-010).
4. The system checks that the [capability](../../../glossary.md#term-capability--capability) is installed, and finds it among the capabilities the CLI ships.
5. Before it writes anything, the system checks the new version against the recorded backbone, and against the capabilities installed. Its [range](../../../glossary.md#term-range--range), each capability it requires and each mandatory connection it marks must hold (COR-030, COR-053 point 6 and REQ-029).
6. The system finds no new name collision that the new version's [skills](../../../glossary.md#term-skill--skill) or [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) bring (ADR-065 point 6).
7. The system moves the capability's [manifest](../../../glossary.md#term-manifest--manifest) under its `project/` where it still lies at the root. It copies the new version, runs the capability's [migrations](../../../glossary.md#term-migration--migration) after the copy, then records the new version (ADR-065 point 4).
8. The system prints `Refreshed capability '<name>' -> v<version> at .pkit/capabilities/<name>/`.
9. The system runs each [adapter](../../../glossary.md#term-adapter--adapter)'s scripts, which deploy the capability's skills and agent definitions. It provisions the capability's query commands, and renders `.pkit/.gitignore`.
10. Where a person can reply, the system runs in turn each question the capability's [data points](../../../glossary.md#term-data-point--data-point) declare (COR-061).

**Variants:**

- **1a.** The adopter passes `--dry-run`. The [system](../../../glossary.md#term-system--system) runs every check, says what it would refresh, and writes nothing (REQ-009).
- **3a.** The running CLI is at another [version](../../../glossary.md#term-version--version) than the [project](../../../glossary.md#term-project--project) records, or the last transition is incomplete. The system stops, names the remedy and writes nothing (REQ-010). The use case ends.
- **4a.** The [capability](../../../glossary.md#term-capability--capability) is not installed. The system refuses, naming `pkit capabilities install <name>`. The use case ends.
- **4b.** The capability was authored in the project, so it is registered as incubated. The system deploys it again from the project's own tree, and copies nothing (COR-031).
- **4c.** The project is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), run by its own code. The system deploys the capability again in place, since its subtree is its source, and copies nothing (ADR-059).
- **4d.** The CLI no longer ships the capability. The system refuses, naming `pkit capabilities uninstall`. The use case ends.
- **5a.** The CLI ships the capability older than the [manifest](../../../glossary.md#term-manifest--manifest) records. The system refuses, names a CLI that ships that version or newer, and writes nothing (ADR-065 [point](../../../glossary.md#term-point--point) 7). The use case ends.
- **5b.** The new version's [range](../../../glossary.md#term-range--range) excludes the recorded [backbone](../../../glossary.md#term-backbone--backbone), or a capability it requires is missing or out of range. The system refuses, naming each, and writes nothing (REQ-029). The use case ends.
- **5c.** The new version falls outside a range an installed capability declares for it, or leaves that capability's mandatory connection unmet. The system warns, naming each, and refuses unless the adopter passes `--force` (COR-030).
- **6a.** The new version brings a new name collision, and the adopter passed no `--interactive`. The system lists each, refuses with `refusing to upgrade with unresolved collisions. Re-run with --interactive to resolve them.`, and writes nothing (REQ-030).
- **6b.** The adopter passed `--interactive`. For each new collision, the system asks override, skip or inspect, and records each skip in the manifest (COR-017).
- **7a.** A [migration](../../../glossary.md#term-migration--migration) fails. The system stops, and the manifest keeps the capability's old version, so the next upgrade runs the migration again (REQ-026).
- **10a.** Nobody can reply. The system runs no question, and prints each question's command for a person to run later (COR-061).

**Postconditions:** The [capability](../../../glossary.md#term-capability--capability) holds the [version](../../../glossary.md#term-version--version) the running CLI ships, at the [backbone](../../../glossary.md#term-backbone--backbone) version the [project](../../../glossary.md#term-project--project) records. Its [migrations](../../../glossary.md#term-migration--migration) have run, and its [manifest](../../../glossary.md#term-manifest--manifest) records that version. Its [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) are deployed. The backbone's [recorded versions](../../../glossary.md#term-recorded-version--recorded-version) did not move.

**Minimal guarantees:**

- Every check of steps 3 to 6 comes before the first write (REQ-029).
- The [capability](../../../glossary.md#term-capability--capability)'s upgrade writes neither of the [backbone](../../../glossary.md#term-backbone--backbone)'s [recorded versions](../../../glossary.md#term-recorded-version--recorded-version) (ADR-065 [point](../../../glossary.md#term-point--point) 4).
- A recorded version never moves down (ADR-065 point 7).
- No new name collision is settled silently (REQ-030).
