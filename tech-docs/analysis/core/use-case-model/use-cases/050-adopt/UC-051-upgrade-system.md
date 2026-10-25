---
id: UC-051
title: Upgrade the system like a dependency
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
  - REQ-017
  - REQ-026
  - REQ-027
  - REQ-029
  - REQ-030
  - REQ-031
after:
  - [UC-014, UC-049]
  - [UC-008]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/upgrade.py
        - src/project_kit/sync.py
        - src/project_kit/manifest.py
        - src/project_kit/migrations.py
        - src/project_kit/point_questions.py
        - src/project_kit/router.py
      record:
        - COR-010
        - COR-059
        - PRJ-004
        - ADR-063
        - ADR-064
        - ADR-065#4
        - ADR-065#5
        - ADR-065#6
        - ADR-065#9
        - ADR-065#12
        - ADR-065#14
        - ADR-059
        - COR-061
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-001
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
        - REQ-017
        - REQ-026
        - REQ-027
        - REQ-029
        - REQ-030
        - REQ-031
    revalidated:
      at: 2026-10-25T14:39:35Z
      outcome: updated
---

# UC-051 — Upgrade the system like a dependency

**Goal:** Upgrade the system like a dependency, at a version the whole project pins, with its migrations run for me and my own files left alone.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit upgrade` writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-008:** The [release](../../../glossary.md#term-release--release) the upgrade moves to carries its tag on the [distribution](../../../glossary.md#term-distribution--distribution)'s repository. So the CLI can update to it, and a [version pin](../../../glossary.md#term-version-pin--version-pin) can name it (PRJ-004).

**Assumptions:**

- The CLI was installed from a tag on a [release](../../../glossary.md#term-release--release)'s commit, `latest` or the release's own. So its [version](../../../glossary.md#term-version--version) names one content, and the target names what the upgrade copies (ADR-065 [point](../../../glossary.md#term-point--point) 12).

**Trigger:** A newer [release](../../../glossary.md#term-release--release) of the [system](../../../glossary.md#term-system--system) ships, or the [project](../../../glossary.md#term-project--project)'s [recorded version](../../../glossary.md#term-recorded-version--recorded-version) is behind the CLI the operator runs.

**Main path:**

1. The adopter runs `pkit upgrade` in a [project](../../../glossary.md#term-project--project) that pins no [version](../../../glossary.md#term-version--version), at a terminal.
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit upgrade` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system asks the [distribution](../../../glossary.md#term-distribution--distribution)'s repository for its latest [release](../../../glossary.md#term-release--release), and finds the CLI current. It prints `pkit tool is current (v<version>).` (ADR-063 point 1).
4. The system checks that the CLI is not older than the project's [recorded versions](../../../glossary.md#term-recorded-version--recorded-version) or its [version pin](../../../glossary.md#term-version-pin--version-pin) (REQ-010). It prints `Upgrading backbone: <recorded> -> <target>`, and each [component](../../../glossary.md#term-component--component) the transition moves. The target is the [backbone](../../../glossary.md#term-backbone--backbone) version the CLI ships.
5. Before it writes anything, the system checks each component's [range](../../../glossary.md#term-range--range) against the target, and the dependency gates over what the transition leaves. It also checks for a new name collision of a [capability](../../../glossary.md#term-capability--capability)'s [skill](../../../glossary.md#term-skill--skill) or [agent definition](../../../glossary.md#term-agent-definition--agent-definition) (REQ-029 and REQ-030).
6. The system records the target as `backbone_version` in `.pkit/manifest.yaml`, before it writes anything else (REQ-026).
7. The system copies the target's content into `.pkit/`, with every [adapter](../../../glossary.md#term-adapter--adapter) and each shipped capability the project installed, and renders `.pkit/.gitignore` (ADR-065 point 4).
8. The system runs the backbone's [migrations](../../../glossary.md#term-migration--migration) from the recorded completion. It then runs each adapter's migrations, and each capability's, dependencies first, and records each component's version as its migrations finish (COR-010, REQ-001 and REQ-017).
9. The system creates each seed path that is missing, never over one that exists. It regenerates the derived state, [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) and deploy among it (COR-059 point 8). It reports each widening the merge brings to the project's settings (ADR-065 point 4).
10. The system records the completion as `completed_version`, and prints `(the transition is complete)` (REQ-026).
11. The system writes `.pkit/version-pin` at the target, last and whole, and prints `Upgrade complete.` (ADR-064 point 1 and REQ-027).
12. Where a person can reply, the system runs in turn each question the [data points](../../../glossary.md#term-data-point--data-point) declare (COR-061).

**Variants:**

- **1a.** The adopter passes `--dry-run`. The [system](../../../glossary.md#term-system--system) names the target, each [component](../../../glossary.md#term-component--component)'s move, each [migration](../../../glossary.md#term-migration--migration), any collision it would ask about and the [version pin](../../../glossary.md#term-version-pin--version-pin) it would write. It writes nothing, and runs no question (REQ-009).
- **1b.** The [project](../../../glossary.md#term-project--project) is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), run by its own code. The system runs [sync](../../../glossary.md#term-sync--sync)'s branch for that repository, which copies nothing and moves no [version](../../../glossary.md#term-version--version) (ADR-059). The use case ends.
- **1c.** A migration runs `pkit upgrade`. The system refuses before it reads anything, since a transition runs no transition inside it (ADR-065 [point](../../../glossary.md#term-point--point) 14).
- **3a.** The CLI is behind the latest [release](../../../glossary.md#term-release--release). The system updates the CLI and runs the upgrade again under it, as UC-048's steps 6 and 7 do, unless `--no-self-update` declines (ADR-063 and REQ-031).
- **3b.** The project pins a version. The system runs the upgrade under the version pin's code, and never updates the CLI. Where a newer release resolves, it hands over to that release's upgrade, then raises the version pin last (ADR-065 point 9).
- **3c.** The router could not fetch the project's version pin, and runs the installed CLI instead. The system refuses, writes nothing, and names reconnecting, the version pin run through `uvx`, or `pkit unpin` then `pkit upgrade` (ADR-065 point 9).
- **4a.** The CLI is older than the project's content or its version pin. The system refuses, writes nothing, and names the remedies (REQ-010). The use case ends.
- **4b.** The project is at the target already. The system prints `Already at backbone v<version>; nothing to upgrade.`. It writes the version pin at that version unless `--no-pin` declines it, and the use case ends (ADR-064 point 1).
- **4c.** The last transition is incomplete. The system says `The last transition is incomplete`, and runs the [backbone](../../../glossary.md#term-backbone--backbone)'s migrations from the recorded completion, so this upgrade finishes that transition (REQ-026).
- **4d.** No completion is recorded, or no [manifest](../../../glossary.md#term-manifest--manifest). The system says the project's migration history is unknown, and runs every backbone migration up to the target once (ADR-065 point 5 and REQ-026).
- **5a.** The system finds one of these conflicts, and refuses before it writes anything, naming each (REQ-029). The use case ends.
  - a component whose [range](../../../glossary.md#term-range--range) excludes the target
  - a component its [distribution](../../../glossary.md#term-distribution--distribution) ships older than the project records
  - a folder of the project's own that takes a core [area](../../../glossary.md#term-area--area)'s name
- **5b.** A dependency gate fails for a [capability](../../../glossary.md#term-capability--capability) that does not move. The system warns, naming each dependent, and refuses unless the adopter passes `--force` (ADR-065 point 6).
- **5c.** A capability's new version brings a new name collision. For each, the system asks override, skip or inspect, and records each skip before the copy, so it never asks again (ADR-065 point 6).
- **5d.** On the path of 5c, nobody can reply. The system refuses before it writes anything, naming a run at a terminal or a rename of the project's [artefact](../../../glossary.md#term-artefact--artefact) (REQ-030). The use case ends.
- **5e.** A moving capability needs a dependency that is missing, or one that does not move and falls outside its range. The system refuses, names what to [install](../../../glossary.md#term-install--install) or upgrade first, and writes nothing, whatever flag is passed (ADR-065 point 6).
- **8a.** A migration exits non-zero. The system stops, records no completion and writes no version pin. The next upgrade runs that migration again (REQ-026).
- **11a.** The adopter passed `--no-pin`. The system writes no version pin, and the project keeps following the installed CLI until its next upgrade (ADR-064 point 2).
- **12a.** Nobody can reply. The system runs no question, and prints each question's command for a person to run later (COR-061).

**Postconditions:** The [project](../../../glossary.md#term-project--project) holds the target [release](../../../glossary.md#term-release--release)'s content, with every [migration](../../../glossary.md#term-migration--migration) up to it run. Its [manifest](../../../glossary.md#term-manifest--manifest)'s target and completion name that release, and its [version pin](../../../glossary.md#term-version-pin--version-pin) names it too, unless `--no-pin` declined it. The project's own files hold what the project wrote, beside the entries [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) adds.

**Minimal guarantees:**

- Every refusal of step 5 comes before the first write (REQ-029).
- An upgrade cut short reads as incomplete, and the next one finishes it (REQ-026).
- A failed upgrade writes no [version pin](../../../glossary.md#term-version-pin--version-pin), and a version pin is never torn (REQ-027).
- No new name collision is settled silently (REQ-030).
- The upgrade writes [project-owned content](../../../glossary.md#term-project-owned-content--project-owned-content) only through the writers that ADR-065 [point](../../../glossary.md#term-point--point) 11 names (REQ-002).
