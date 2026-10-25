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

**Preconditions:** **From UC-048:** The adopter's machine has the [system](../../../glossary.md#term-system--system)'s CLI at a [release](../../../glossary.md#term-release--release), with that release's content.

**Assumptions:** None.

**Trigger:** The adopter wants a [project](../../../glossary.md#term-project--project) to run the [methodology](../../../glossary.md#term-methodology--methodology).

**Main path:**

1. The adopter runs `pkit init` at the root of the [project](../../../glossary.md#term-project--project)'s git repository.
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit init` runs no such check, and writes in whatever repository its target names. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system names the [install](../../../glossary.md#term-install--install)'s target and why it chose it, as `pkit init -> <target>  (git repository root — your current directory)`.
4. The system checks that the target holds no `.pkit/`, and is not the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository). It checks that the CLI's content is whole, and that no [adapter](../../../glossary.md#term-adapter--adapter) it ships takes a reserved name.
5. The system writes `.pkit/manifest.yaml`, recording the CLI's [backbone](../../../glossary.md#term-backbone--backbone) [version](../../../glossary.md#term-version--version) as the target, before it copies anything ([ADR-065 point 4](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#4-a-transition-runs-in-cor-010s-order-with-seed-paths-after-the-migrations) and REQ-026).
6. The system copies the methodology's [areas](../../../glossary.md#term-area--area) from the content the CLI carries into `.pkit/` ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md) and [ADR-033](../../../../../architecture/decisions/ADR-033-official-install-bundles-content.md)).
7. The system creates each seed path, such as each area's `project/` folder and the agents' [overlay](../../../glossary.md#term-overlay--overlay) (COR-001 and [ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)).
8. The system registers each adapter it copied, at the version the adapter ships. Each adapter's scripts then merge the methodology's entries into the files its [harness](../../../glossary.md#term-harness--harness) reads, and deploy its [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition). For Claude Code those are `.claude/settings.json` and `CLAUDE.md` ([COR-002](../../../../../../.pkit/decisions/core/COR-002-merge-delivery.md) and REQ-002).
9. The system renders `.pkit/.gitignore`, creates the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace), and provisions each registered query command ([ADR-009 point 7](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#7-runtime-local-ignore-lines-ship-through-a-pkit-owned-pkitgitignore-rendered-wholesale)).
10. The system records `completed_version` last, and prints `Install complete. Recommended next steps:`. The first step names the CLI's install of the highest [release](../../../glossary.md#term-release--release), through the tag `latest` (REQ-031). The others name the project's settings files, lines for `.gitignore`, and `pkit visibility private`.
11. The adopter runs `pkit status`. The system shows how the methodology is wired into the project, and writes nothing (REQ-005). It shows the backbone's version, the agent workspace, the adapter, each [capability](../../../glossary.md#term-capability--capability), the [rule sets](../../../glossary.md#term-rule-set--rule-set) and the connections.
12. The adopter commits `.pkit/` and the files the adapter deployed, so the team shares one methodology. The project's visibility stays `shared`, the default ([ADR-009 point 2](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#2-shared-default--pkit-is-committed-infoexclude-is-kept-clear)).

**Variants:**

- **1a.** The adopter passes `--dry-run`. The [system](../../../glossary.md#term-system--system) runs every check, names each write it would make, and writes nothing (REQ-009).
- **1b.** The adopter runs `pkit init` in a subfolder of the repository. The system names the repository's root as the target, and asks `Install project-kit into <target>?`. With no terminal, or with `--yes`, it refuses, naming `pkit init --root <target>`.
- **1c.** The adopter runs `pkit init` in a folder that no git repository holds. The system asks to [install](../../../glossary.md#term-install--install) there, and `--yes` accepts it.
- **1d.** The adopter passes `--root <path>`, as in a pipeline. The system installs at that path without asking, after the checks of step 4.
- **1e.** Git refuses to verify the repository, or cannot open its `.git`. The system refuses, naming the fix, or `pkit init --root <target>` to install there anyway.
- **1f.** An install lies between the working directory and the target. The system refuses to create a second one, and names `pkit init --root <target>`.
- **4a.** The target holds a `.pkit/` that an earlier install wrote. The system refuses with `<target> is already a project-kit project.`, and names `pkit sync`, since first install runs once ([COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md)). The use case ends.
- **4b.** The target holds a `.pkit/` that no install wrote. The system refuses, and names moving it aside. The use case ends.
- **4c.** The target is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the CLI ships an [adapter](../../../glossary.md#term-adapter--adapter) and a [capability](../../../glossary.md#term-capability--capability) of one name. The system refuses and writes nothing. The use case ends.
- **8a.** The [project](../../../glossary.md#term-project--project) already holds `.claude/settings.json`. Before the merge, the system backs it up to `.claude/settings.json.pre-pkit` ([ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)).
- **10a.** The install stops before step 10, such as on a failing script. The [manifest](../../../glossary.md#term-manifest--manifest) records the target and no completion, so the project reads as incomplete, and `pkit upgrade` finishes the install (UC-051 and REQ-026).
- **12a.** The team has not adopted the system. The adopter runs `pkit visibility private`, and the system writes the footprint the installed [components](../../../glossary.md#term-component--component) declare into `.git/info/exclude` ([ADR-009 point 3](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)).
- **12b.** On the path of 12a, files of the footprint are tracked already. The system lists them and asks `Proceed?`. On a yes, it removes them from git's index with `git rm --cached`, and keeps each working copy ([ADR-009 point 4](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#4-going-private-always-runs-a-confirm-gated-untrack)).
- **12c.** The adopter runs `pkit visibility`. The system shows the mode, `shared` or `private`, and the footprint, and writes nothing.
- **12d.** The adopter passes `--dry-run` to `pkit visibility private`, `shared` or `untrack`. The system shows what it would write and untrack, and changes nothing (REQ-009).
- **12e.** Later, the adopter runs `pkit visibility shared`. The system clears its region of `.git/info/exclude`, so the system is committed again the ordinary way.
- **12f.** At its entry, each mode of `pkit visibility` that writes checks the repository as step 2 does (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit visibility` runs no such check. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

**Postconditions:** The [project](../../../glossary.md#term-project--project) holds the [system](../../../glossary.md#term-system--system) at the CLI's [release](../../../glossary.md#term-release--release). The project's `.pkit/` holds the [methodology](../../../glossary.md#term-methodology--methodology)'s content, and its [manifest](../../../glossary.md#term-manifest--manifest)'s target and completion name that release. Its [adapters](../../../glossary.md#term-adapter--adapter) are registered, with their [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) deployed. The system is committed for the team, or it is hidden from the shared repository in this clone.

**Minimal guarantees:**

- Every check comes before the first write, so a refused [install](../../../glossary.md#term-install--install) leaves the [project](../../../glossary.md#term-project--project) as it was (`install.py`).
- An install cut short reads as incomplete, and `pkit upgrade` finishes it ([ADR-065 point 4](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#4-a-transition-runs-in-cor-010s-order-with-seed-paths-after-the-migrations) and REQ-026).
- The install writes [project-owned content](../../../glossary.md#term-project-owned-content--project-owned-content) only through the writers [ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state) names. [Merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) adds the [methodology](../../../glossary.md#term-methodology--methodology)'s entries, and removes no entry the project wrote ([COR-002](../../../../../../.pkit/decisions/core/COR-002-merge-delivery.md) and REQ-002).
- `pkit visibility` writes no `.gitignore` the adopter owns, and its untrack keeps every working copy ([ADR-009](../../../../../architecture/decisions/ADR-009-git-footprint-visibility.md)).
