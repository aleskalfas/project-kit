---
id: UC-014
title: Keep my intermediate files in a workspace no commit carries
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/workspace.py
        - src/project_kit/install.py
        - src/project_kit/status.py
        - .pkit/permissions/decide.py
        - .pkit/permissions/profiles/*.yaml
        - .pkit/rules/core.md
      record:
        - ADR-005#5
        - ADR-060#1
        - ADR-060#2
        - ADR-060#3
        - ADR-060#4
        - ADR-060#6
        - ADR-060#7
        - ADR-060#9
      artefact:
        - ACT-ai-agent
        - ACT-operator
---

# UC-014 — Keep my intermediate files in a workspace no commit carries

**Goal:** Keep my intermediate files in a workspace that no commit carries and no confirmation guards.

**Other actors:**

- **Operator** (`ACT-operator`): commits the work, or has the agent commit it. No file the agent keeps in the agent workspace reaches that commit.

**Preconditions:** None.

**Assumptions:**

- The agent keeps its intermediate files in the agent workspace, and nowhere else outside the repository. Nothing at run time holds it to that (core rule 16).

**Trigger:** The agent needs a file only to get its work done, such as the body of a pull request.

**Main path:**

1. The agent writes the file with a file tool inside the agent workspace, `.agent-workspace/` at its checkout's root, such as `Write` on `.agent-workspace/pr-body.md`.
2. The permission hook finds the file tool's target inside the agent workspace, and allows the write with no prompt. Every shipped profile grants the `workspace` privilege to every agent (ADR-005 point 5 and ADR-060 point 1).
3. The agent passes the file to the command that needs it, such as `pkit pm open-pr <number> --body-file .agent-workspace/pr-body.md`.
4. The work is committed. Git leaves the folder out, since `pkit init` and `pkit sync` excluded it in the clone's local exclude file (ADR-060 point 9).
5. The agent removes the files it no longer needs (core rule 16).

**Variants:**

- **1a.** The agent works in a linked worktree. The worktree's own `.agent-workspace/` lies at its root, and the one exclude entry in the common git directory covers it too. The hook counts the worktree only where git registered it for the same repository (ADR-060 point 3).
- **1b.** The agent writes the file with a shell command, such as a redirect or a here-document into the folder. The hook judges such a command like any other shell write, so the harness may ask to confirm it (ADR-060 point 4).
- **1c.** The `workspace` grant does not cover the target, and the write is decided as it would be without the grant (ADR-060 points 1 and 3). The grant leaves out three targets:
  - one that leaves the folder once symlinks are resolved
  - one in a repository nested in the folder
  - an existing file with more than one link
- **1d.** A symlink named `.agent-workspace` sits where the folder belongs. It is never the agent workspace. `pkit sync` refuses to adopt it, and `pkit status` reports it (ADR-060 point 2).
- **2a.** The permission hook is not registered, or no profile is active. The harness's own approvals hold in its working directory. A read never prompts, and an edit prompts until the operator accepts edits for the session (ADR-060 point 6).
- **2b.** The hook defers on the file tool all the same. The diagnostic report lists the deferral as a defect, never as an allowlist gap (ADR-060 point 7).
- **4a.** The clone has run neither `pkit init` nor `pkit sync`, and the project's `.gitignore` lacks `/.agent-workspace/`. Git does not ignore the folder, so `git add -A` would stage its files. `pkit status` reports the folder `NOT excluded from git`, and `pkit init` recommends the `.gitignore` line (ADR-060 point 9).

**Postconditions:** The agent's intermediate files lie in `.agent-workspace/`, written with no prompt, and no commit carries them.

**Minimal guarantees:**

- The `workspace` grant reaches no file outside the folder, and has no opinion there (ADR-060 point 1).
- Another repository's agent workspace never counts as this checkout's (ADR-060 point 3).
- `pkit init` and `pkit sync` add the exclude entry once, and change no other line of the exclude file (`workspace.py`).
- A symlink in the folder's place is never adopted as the agent workspace (ADR-060 point 2 and `workspace.py`).
