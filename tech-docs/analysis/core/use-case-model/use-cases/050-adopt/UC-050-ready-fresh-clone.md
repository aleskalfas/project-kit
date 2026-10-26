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

- **From [UC-048](UC-048-install-cli.md):** The operator's machine has the [system](../../../glossary.md#term-system--system)'s CLI at a [release](../../../glossary.md#term-release--release), with that release's content.
- **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](UC-049-install-system.md):** The repository holds the system, committed. It is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it and shared with the team ([ADR-009 point 2](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#2-shared-default--pkit-is-committed-infoexclude-is-kept-clear)).

**Assumptions:**

- A fresh clone holds what the [project](../../../glossary.md#term-project--project) committed, and none of what each clone regenerates. That is the deployed [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition), the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace) and each query command's environment ([ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)).

**Trigger:** The operator clones the [project](../../../glossary.md#term-project--project)'s repository on a machine, or opens a clone whose regenerated state is missing.

**Main path:**

1. The operator runs `pkit sync` at the root of the clone.
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit sync` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the [backbone](../../../glossary.md#term-backbone--backbone) [version](../../../glossary.md#term-version--version) the [project](../../../glossary.md#term-project--project) records. It also checks that the last [version transition](../../../glossary.md#term-version-transition--version-transition) is complete ([REQ-010](../../../requirements/functional/REQ-010-stop-under-another-version.md)).
4. The system copies into `.pkit/` the [methodology](../../../glossary.md#term-methodology--methodology)'s content at the [release](../../../glossary.md#term-release--release) the project records. It also copies each installed [capability](../../../glossary.md#term-capability--capability) that the CLI ships at the version the project records ([COR-059 point 2](../../../../../../.pkit/decisions/core/COR-059-version-transition.md#2-reconciliation-runs-at-the-recorded-versions-and-moves-none)).
5. The system regenerates the state each clone derives from the project's own declarations ([ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)):
   - [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery), in its tier that asks nothing, into the files each [adapter](../../../glossary.md#term-adapter--adapter)'s [harness](../../../glossary.md#term-harness--harness) reads, such as `.claude/settings.json` and `CLAUDE.md`
   - the deployed [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition)
   - `.pkit/.gitignore`, rendered from the [components](../../../glossary.md#term-component--component)' declarations
   - the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace), with its line in `.git/info/exclude`
   - each registered query command's environment
6. The system prints `Sync complete.`.

**Variants:**

- **1a.** The operator passes `--dry-run`. The [system](../../../glossary.md#term-system--system) runs every check, says what it would copy and regenerate, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).
- **1b.** The clone holds no `.pkit/`, as where the adopter kept the system private ([ADR-009 point 3](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)). The system refuses with `<root>/.pkit/ does not exist. Run 'pkit init' first.`, and the use case ends.
- **1c.** The operator passes `--force`. The system says that it ignores the flag, and goes on ([ADR-065 point 10](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#10-sync---force-is-ignored-for-one-release-then-removed)).
- **1d.** The [project](../../../glossary.md#term-project--project) pins a [release](../../../glossary.md#term-release--release) other than the installed CLI's. The router runs the command at the [version pin](../../../glossary.md#term-version-pin--version-pin) ([UC-052](UC-052-run-at-pin.md)).
- **3a.** The project is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), run by its own code. The system copies nothing, regenerates the derived state, and prints `Self-host sync complete (deploy primitives re-run).` ([ADR-059](../../../../../architecture/decisions/ADR-059-methodology-source-repository.md)).
- **3b.** The running CLI is newer than the project's [recorded version](../../../glossary.md#term-recorded-version--recorded-version), and the project pins no [version](../../../glossary.md#term-version--version). The system stops and writes nothing ([REQ-010](../../../requirements/functional/REQ-010-stop-under-another-version.md)). Its message names `pkit upgrade` to move, `pkit pin` to stay, and in a pipeline a committed version pin or the project's version installed.
- **3c.** The running CLI is older than the project's content or its version pin. The system stops, writes nothing, and names the remedies for that state (REQ-010).
- **3d.** The last [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete. The system stops, writes nothing, and names `pkit upgrade`, which finishes the transition (REQ-010).
- **3e.** The router could not fetch the project's version pin, and runs the installed CLI instead (UC-052). The system stops only where its check finds another version, naming the remedies of the fallback ([ADR-065 point 8](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#8-each-stop-names-the-remedy-for-the-state-it-finds)).
- **4a.** A [capability](../../../glossary.md#term-capability--capability) the project records is shipped newer, older or not at all, or has no recorded version. The system copies none of these, and reports each ([ADR-065 point 1](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#1-syncs-propagation-step-has-two-callers)).
- **4b.** A folder of the project's own sits at `.pkit/lifecycle/`, where the core [area](../../../glossary.md#term-area--area) of that name would be copied. The system stops before it writes, and names how to move the project's area ([ADR-065 point 13](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#13-a-transition-and-sync-stop-on-a-clash-of-area-names-and-no-core-area-is-added-until-1600)).

**Postconditions:** The clone holds the [system](../../../glossary.md#term-system--system) at the [release](../../../glossary.md#term-release--release) the [project](../../../glossary.md#term-project--project) records, and no [recorded version](../../../glossary.md#term-recorded-version--recorded-version) moved. In the clone:

- the [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) are deployed where the [harness](../../../glossary.md#term-harness--harness) reads them
- the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace) exists
- each query command answers offline

**Minimal guarantees:**

- [Sync](../../../glossary.md#term-sync--sync) moves no [recorded version](../../../glossary.md#term-recorded-version--recorded-version), runs no [migration](../../../glossary.md#term-migration--migration), and creates no seed path ([COR-059 point 2](../../../../../../.pkit/decisions/core/COR-059-version-transition.md#2-reconciliation-runs-at-the-recorded-versions-and-moves-none)).
- Sync writes [project-owned content](../../../glossary.md#term-project-owned-content--project-owned-content) only through [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery), and removes no entry the [project](../../../glossary.md#term-project--project) wrote (COR-059 point 2 and [REQ-002](../../../requirements/functional/REQ-002-project-owned-writers.md)).
- Under another CLI [version](../../../glossary.md#term-version--version) than the project records, or over an incomplete transition, sync writes nothing, under `--dry-run` too ([REQ-010](../../../requirements/functional/REQ-010-stop-under-another-version.md)).
