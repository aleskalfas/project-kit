---
id: UC-050
title: Get a fresh clone ready to work with one sync
status: active
actor: ACT-operator
other-actors: []
requirements:
  - REQ-002
  - REQ-009
  - REQ-010
  - REQ-012
after:
  - [UC-048]
  - [UC-014, UC-049]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - src/project_kit/treecopy.py
        - src/project_kit/provisioning.py
        - src/project_kit/workspace.py
      record:
        - COR-059#2
        - COR-059#9
        - ADR-065#1
        - ADR-065#7
        - ADR-065#8
        - ADR-065#10
        - ADR-065#11
        - ADR-065#13
        - ADR-059
        - ADR-009
        - ADR-034#1
      artefact:
        - ACT-operator
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
---

# UC-050 — Get a fresh clone ready to work with one sync

**Goal:** Get a fresh clone ready to work with one sync.

**Other actors:** None.

**Preconditions:**

- **From UC-048:** The operator's machine has the system's CLI at a release, with that release's content.
- **From UC-014 or UC-049:** The repository holds the system, committed. It is the methodology's source repository, or the system is installed in it and shared with the team (ADR-009 point 2).

**Assumptions:**

- A fresh clone holds what the project committed, and none of what each clone regenerates. That is the deployed skills and agent definitions, the agent workspace and each query command's environment (ADR-065 point 11).

**Trigger:** The operator clones the project's repository on a machine, or opens a clone whose regenerated state is missing.

**Main path:**

1. The operator runs `pkit sync` at the root of the clone.
2. At its entry, before it reads anything, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit sync` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the backbone version the project records. It also checks that the last version transition is complete (REQ-010).
4. The system copies into `.pkit/` the methodology's content at the release the project records. It copies each installed capability that the CLI ships at the version the project records too (COR-059 point 2).
5. The system regenerates the state each clone derives from the project's own declarations (ADR-065 point 11):
   - merge delivery, in its tier that asks nothing, into the files each adapter's harness reads, such as `.claude/settings.json` and `CLAUDE.md`
   - the deployed skills and agent definitions
   - `.pkit/.gitignore`, rendered from the components' declarations
   - the agent workspace, with its line in `.git/info/exclude`
   - each registered query command's environment
6. The system prints `Sync complete.`.

**Variants:**

- **1a.** The operator passes `--dry-run`. The system runs every check, says what it would copy and regenerate, and writes nothing (REQ-009).
- **1b.** The clone holds no `.pkit/`, as where the adopter kept the system private (ADR-009 point 3). The system refuses with `<root>/.pkit/ does not exist. Run 'pkit init' first.`, and the use case ends.
- **1c.** The operator passes `--force`. The system says that it ignores the flag, and goes on (ADR-065 point 10).
- **1d.** The project pins a release other than the installed CLI's. The router runs the command at the version pin (UC-052).
- **3a.** The project is the methodology's source repository, run by its own code. The system copies nothing, regenerates the derived state, and prints `Self-host sync complete (deploy primitives re-run).` (ADR-059).
- **3b.** The running CLI is newer than the project's recorded version, and the project pins no version. The system stops and writes nothing (REQ-010). Its message names `pkit upgrade` to move, `pkit pin` to stay, and in a pipeline a committed version pin or the project's version installed.
- **3c.** The running CLI is older than the project's content or its version pin. The system stops, writes nothing, and names the remedies for that state (REQ-010).
- **3d.** The last version transition is incomplete. The system stops, writes nothing, and names `pkit upgrade`, which finishes it (REQ-010).
- **3e.** The router could not fetch the project's version pin, and runs the installed CLI instead (UC-052). The system stops only where its check finds another version, naming the remedies of the fallback (ADR-065 point 8).
- **4a.** A capability the project records is shipped newer, older or not at all, or has no recorded version. The system copies none of these, and reports each (ADR-065 point 1).
- **4b.** A folder of the project's own sits at `.pkit/lifecycle/`, where the core area of that name would be copied. The system stops before it writes, and names how to move the project's area (ADR-065 point 13).

**Postconditions:** The clone holds the system at the release the project records. Its skills and agent definitions are deployed where the harness reads them, its agent workspace exists, and its query commands answer offline. No recorded version moved.

**Minimal guarantees:**

- Sync moves no recorded version, runs no migration, and creates no seed path (COR-059 point 2).
- Sync writes project-owned content only through merge delivery, and removes no entry the project wrote (COR-059 point 2 and REQ-002).
- Under another CLI version than the project records, or over an incomplete transition, sync writes nothing, under `--dry-run` too (REQ-010).
