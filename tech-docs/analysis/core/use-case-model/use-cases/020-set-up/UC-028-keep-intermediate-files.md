---
id: UC-028
title: Keep my intermediate files in a workspace no commit carries
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
after:
  - [UC-014, UC-049]
requirements:
  - REQ-016
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/workspace.py
        - src/project_kit/workspace_remove.py
        - src/project_kit/status.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
        - .pkit/permissions/decide.py
        - .pkit/permissions/profiles/*.yaml
        - .pkit/schemas/privilege-catalog.yaml
        - .pkit/rules/core.md
      record:
        - ADR-005#5
        - ADR-060#1
        - ADR-060#2
        - ADR-060#3
        - ADR-060#4
        - ADR-060#5
        - ADR-060#7
        - ADR-060#9
        - ADR-060#10
        - ADR-065#11
      artefact:
        - ACT-ai-agent
        - ACT-operator
        - REQ-016
---

# UC-028 — Keep my intermediate files in a workspace no commit carries

**Goal:** Keep my intermediate files in a workspace that no commit carries and no confirmation guards.

**Other actors:**

- **Operator** (`ACT-operator`): commits the work, or has the agent commit it. No file the agent keeps in the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace) reaches that commit.

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The agent keeps its intermediate files in the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace), and nowhere else outside the repository. Nothing at run time holds it to that, and only core rule 16 asks it (`.pkit/rules/core.md`).

**Trigger:** The agent needs a file only to get its work done, such as the body of a [pull request](../../../glossary.md#term-pull-request--pull-request).

**Main path:**

1. The agent writes the file inside the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace), `.agent-workspace/` at the root of its checkout, with one of the [harness](../../../glossary.md#term-harness--harness)'s file tools. An example is Claude Code's `Write` on `.agent-workspace/pr-body.md`.
2. The [adapter](../../../glossary.md#term-adapter--adapter)'s [permission hook](../../../glossary.md#term-permission-hook--permission-hook) hands the write to the [backbone](../../../glossary.md#term-backbone--backbone)'s permission code, which needs only the [system](../../../glossary.md#term-system--system) `python3` ([REQ-016](../../../requirements/constraints/020-set-up/REQ-016-permissions-standard-library.md)). The code recognises the `workspace` [privilege](../../../glossary.md#term-privilege--privilege), since the target lies inside the folder ([ADR-060 point 1](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#1-recognition-from-the-target-path-for-the-file-tools-only)).
3. Every [profile](../../../glossary.md#term-profile--profile) the backbone ships grants that privilege to `all` ([ADR-060 point 5](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#5-granted-to-all-by-every-shipped-profile) and [ADR-005 point 5](../../../../../architecture/decisions/ADR-005-permission-profile-surface.md#5-shipped-tiers-nest-grants-are-over-catalog-privileges-shell-autonomy-rides-the-references)). So the code allows the write, and nobody is asked to confirm it.
4. The agent passes the file to the command that needs it, such as `gh pr create --body-file .agent-workspace/pr-body.md`.
5. The work is committed. Git leaves the folder out, since `pkit init`, `pkit sync` and `pkit upgrade` exclude it in the clone's local exclude file ([ADR-060 point 9](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#9-excluded-per-clone-the-committed-ignore-line-is-recommended-never-written) and [ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)).
6. The agent removes the files it wrote and no longer needs with `pkit workspace remove`, as core rule 16 asks. The command tests each path after the shell expanded it, and removes the files, which lie inside the agent workspace ([ADR-060 point 10](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#10-removal-through-a-backbone-command-that-tests-its-own-paths)).

**Variants:**

- **1a.** The agent works in a linked worktree. The worktree's own `.agent-workspace/` lies at its root, and the one exclude entry in the common git directory covers that folder too. The code counts the folder as an [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace) only where git registered the worktree for the same repository ([ADR-060 point 3](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#3-which-checkouts-count)).
- **1b.** The agent writes the file with a shell command, such as a redirect or a here-document into the folder. The code judges such a command like any other shell write, so the [harness](../../../glossary.md#term-harness--harness) may ask to confirm it ([ADR-060 point 4](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#4-no-bash-exception)).
- **1c.** The [privilege](../../../glossary.md#term-privilege--privilege) does not cover the target, so the code decides the write as it would without the privilege (ADR-060 points [1](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#1-recognition-from-the-target-path-for-the-file-tools-only) and [3](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#3-which-checkouts-count)). The privilege leaves out three targets:
  - one that leaves the folder once symlinks are resolved
  - one in a repository nested in the folder
  - an existing file with more than one link
- **1d.** A symlink named `.agent-workspace` sits where the folder belongs. It is never the agent workspace ([ADR-060 point 2](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#2-the-folder-is-the-checkouts-own)). `pkit init` and `pkit sync` refuse to adopt it, and `pkit status` reports `a symlink, never the workspace` ([ADR-060 point 9](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#9-excluded-per-clone-the-committed-ignore-line-is-recommended-never-written)).
- **1e.** A file named `.agent-workspace` stands where the folder belongs. The file tool cannot write inside it, and `pkit sync` reports `.agent-workspace exists and is not a folder — move it aside` (`workspace.py`).
- **2a.** The [permission hook](../../../glossary.md#term-permission-hook--permission-hook) is not registered. The harness decides the write by its own settings. Claude Code's [adapter](../../../glossary.md#term-adapter--adapter), for one, allows its file tools for the whole session, so nobody is asked.
- **3a.** No [profile](../../../glossary.md#term-profile--profile) is active, or the active one is the [project](../../../glossary.md#term-project--project)'s own and grants no `workspace` privilege. The code decides the write as it would without the privilege. Under the `lenient` posture it defers the write to the harness, and under `strict` it denies it.
- **3b.** The `read-only` profile is active, whose posture is `strict`. The code denies a file tool's write anywhere else, and allows it in the agent workspace under the `workspace` privilege ([ADR-060 point 5](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#5-granted-to-all-by-every-shipped-profile)).
- **3c.** The hook defers the write to the harness all the same. Where a diagnostic session is on, `pkit permissions diagnose report` lists the deferral in its `workspace` group ([UC-033](UC-033-find-why-prompted.md)). The group is a defect, never a gap to allow around ([ADR-060 point 7](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#7-a-prompt-there-is-a-defect)).
- **5a.** The clone has run none of `pkit init`, `pkit sync` and `pkit upgrade`, and the project's committed `.gitignore` lacks `/.agent-workspace/`. Git does not ignore the folder, so `git add -A` would stage its files. `pkit status` reports the folder `NOT excluded from git`, and `pkit init` recommends the `.gitignore` line ([ADR-060 point 9](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#9-excluded-per-clone-the-committed-ignore-line-is-recommended-never-written)).
- **5b.** The project lies in no git repository. No commit carries anything, and `pkit sync` reports that there is nothing to exclude the folder from (`workspace.py`).
- **6a.** The agent removes the files with a shell command, such as `rm`, not with `pkit workspace remove`. The `workspace` privilege covers no shell command, so the code decides it on the command's own grants, and the harness may ask ([ADR-060 point 4](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#4-no-bash-exception)).
- **6b.** The command refuses a path the agent gives, so it removes nothing and names each refused path and why ([ADR-060 point 10](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#10-removal-through-a-backbone-command-that-tests-its-own-paths)). It refuses three kinds of path:
  - one outside the folder, the folder itself, or one whose last part is `.` or `..`
  - one at or under a child of the folder named after a [capability](../../../glossary.md#term-capability--capability) the [manifest](../../../glossary.md#term-manifest--manifest) registers, where that capability keeps its lasting state
  - one in a repository or worktree nested in the folder, or a folder that holds one
- **6c.** The checkout lies in another repository than the [session anchor](../../../glossary.md#term-session-anchor--session-anchor)'s. The cross-repository guard asks the operator at a terminal, and a call the operator confirms goes on as step 6 says. A call the operator declines, or one with no terminal to ask, is refused, and nothing is removed ([ADR-060 point 10](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#10-removal-through-a-backbone-command-that-tests-its-own-paths)).
- **6d.** A path the agent gives lies inside the folder but names nothing. The command reports it, refuses nothing for it, and removes the other paths ([ADR-060 point 10](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#10-removal-through-a-backbone-command-that-tests-its-own-paths)).

**Postconditions:** The agent's intermediate files lie in `.agent-workspace/`, written with nobody asked to confirm them, and no commit carries them.

**Minimal guarantees:**

- The `workspace` [privilege](../../../glossary.md#term-privilege--privilege) reaches no file outside the folder, and has no opinion there ([ADR-060 point 1](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#1-recognition-from-the-target-path-for-the-file-tools-only) and `decide.py`).
- Another repository's [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace) never counts as this checkout's ([ADR-060 point 3](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#3-which-checkouts-count)).
- `pkit init`, `pkit sync` and `pkit upgrade` add the exclude entry once, with a comment line above it, and edit no other line of the exclude file (`workspace.py`).
- `pkit workspace remove` removes nothing unless every path given lies inside the agent workspace, and follows no symlink out of it ([ADR-060 point 10](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#10-removal-through-a-backbone-command-that-tests-its-own-paths) and `workspace_remove.py`).
- A symlink at the folder's path is never adopted as the agent workspace ([ADR-060 point 2](../../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#2-the-folder-is-the-checkouts-own) and `workspace.py`).
