---
id: UC-049
title: Install the system into my project with one command
status: active
actor: ACT-adopter
other-actors:
  - ACT-operator
requirements:
  - REQ-002
  - REQ-005
  - REQ-009
  - REQ-012
  - REQ-026
  - REQ-031
after:
  - [UC-048]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: "12f"
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/treecopy.py
        - src/project_kit/manifest.py
        - src/project_kit/visibility.py
        - src/project_kit/status.py
        - src/project_kit/provisioning.py
        - src/project_kit/workspace.py
      record:
        - COR-001
        - COR-002
        - COR-004
        - COR-010
        - ADR-009
        - ADR-033
        - ADR-065#4
        - ADR-065#11
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-002
        - REQ-005
        - REQ-009
        - REQ-012
        - REQ-026
        - REQ-031
---

# UC-049 — Install the system into my project with one command

**Goal:** Install the system with one command, committed for the team or kept out of the shared repository, and see its wiring into my project.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit init` or `pkit visibility` writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-048:** The adopter's machine has the system's CLI at a release, with that release's content.

**Assumptions:** None.

**Trigger:** The adopter wants a project to run the methodology.

**Main path:**

1. The adopter runs `pkit init` at the root of the project's git repository.
2. At its entry, before it reads anything, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit init` runs no such check, and writes in whatever repository its target names. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system names the install's target and why it chose it, as `pkit init -> <target>  (git repository root — your current directory)`.
4. The system checks that the target holds no `.pkit/`, and is not the methodology's source repository. It checks that the CLI's content is whole, and that no adapter it ships takes a reserved name.
5. The system writes `.pkit/manifest.yaml`, recording the CLI's backbone version as the target, before it copies anything (ADR-065 point 4 and REQ-026).
6. The system copies the methodology's areas from the content the CLI carries into `.pkit/` (COR-001 and ADR-033).
7. The system creates each seed path, such as each area's `project/` folder and the agents' overlay (COR-001 and ADR-065 point 11).
8. The system registers each adapter it copied, at the version it ships. Each adapter's scripts then merge the methodology's entries into the files its harness reads, and deploy its skills and agent definitions. For Claude Code those are `.claude/settings.json` and `CLAUDE.md` (COR-002 and REQ-002).
9. The system renders `.pkit/.gitignore`, creates the agent workspace, and provisions each registered query command (ADR-009 point 7).
10. The system records `completed_version` last, and prints `Install complete. Recommended next steps:`. The steps name the CLI's install at its own version (REQ-031), the project's settings files, lines for `.gitignore`, and `pkit visibility private`.
11. The adopter runs `pkit status`. The system shows how the methodology is wired into the project, and writes nothing (REQ-005). It shows the backbone's version, the agent workspace, the adapter, each capability, the rule sets and the connections.
12. The adopter commits `.pkit/` and the files the adapter deployed, so the team shares one methodology. The project's visibility stays `shared`, the default (ADR-009 point 2).

**Variants:**

- **1a.** The adopter passes `--dry-run`. The system runs every check, names each write it would make, and writes nothing (REQ-009).
- **1b.** The adopter runs `pkit init` in a subfolder of the repository. The system names the repository's root as the target, and asks `Install project-kit into <target>?`. With no terminal, or with `--yes`, it refuses, naming `pkit init --root <target>`.
- **1c.** The adopter runs `pkit init` in a folder that no git repository holds. The system asks to install there, and `--yes` accepts it.
- **1d.** The adopter passes `--root <path>`, as in a pipeline. The system installs at that path without asking, after the checks of step 4.
- **1e.** Git refuses to verify the repository, or cannot open its `.git`. The system refuses, naming the fix, or `pkit init --root <target>` to install there anyway.
- **1f.** An install lies between the working directory and the target. The system refuses to create a second one, and names `pkit init --root <target>`.
- **4a.** The target holds a `.pkit/` that is an install. The system refuses with `<target> is already a project-kit project.`, and names `pkit sync`, since first install runs once (COR-004). The use case ends.
- **4b.** The target holds a `.pkit/` that is no install. The system refuses, and names moving it aside. The use case ends.
- **4c.** The target is the methodology's source repository, or the CLI ships an adapter and a capability of one name. The system refuses and writes nothing. The use case ends.
- **8a.** The project already holds `.claude/settings.json`. Before the merge, the system backs it up to `.claude/settings.json.pre-pkit` (ADR-065 point 11).
- **10a.** The install stops before step 10, such as on a failing script. The manifest records the target and no completion, so the project reads as incomplete, and `pkit upgrade` finishes it (UC-051 and REQ-026).
- **12a.** The team has not adopted the system. The adopter runs `pkit visibility private`, and the system writes the footprint the installed components declare into `.git/info/exclude` (ADR-009 point 3).
- **12b.** On the path of 12a, files of the footprint are tracked already. The system lists them and asks `Proceed?`. On a yes, it removes them from git's index with `git rm --cached`, and keeps each working copy (ADR-009 point 4).
- **12c.** The adopter runs `pkit visibility`. The system shows the mode, `shared` or `private`, and the footprint, and writes nothing.
- **12d.** The adopter passes `--dry-run` to `pkit visibility private`, `shared` or `untrack`. The system shows what it would write and untrack, and changes nothing (REQ-009).
- **12e.** Later, the adopter runs `pkit visibility shared`. The system clears its region of `.git/info/exclude`, so the system is committed again the ordinary way.
- **12f.** At its entry, each mode of `pkit visibility` that writes checks the repository as step 2 does (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit visibility` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

**Postconditions:** The project holds the system at the CLI's release. Its `.pkit/` holds the methodology's content, and its manifest's target and completion name that release. Its adapters are registered, with their skills and agent definitions deployed. The system is committed for the team, or hidden from the shared repository in this clone.

**Minimal guarantees:**

- Every check comes before the first write, so a refused install leaves the project as it was (`install.py`).
- An install cut short reads as incomplete, and `pkit upgrade` finishes it (ADR-065 point 4 and REQ-026).
- The install writes project-owned content only through the writers ADR-065 point 11 names. Merge delivery adds the methodology's entries, and removes no entry the project wrote (COR-002 and REQ-002).
- `pkit visibility` writes no `.gitignore` the adopter owns, and its untrack keeps every working copy (ADR-009).
