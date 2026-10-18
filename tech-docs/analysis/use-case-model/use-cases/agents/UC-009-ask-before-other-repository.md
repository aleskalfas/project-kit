---
id: UC-009
title: Be asked before an agent changes another repository
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/session_guard.py
        - src/project_kit/cli.py
        - .pkit/capabilities/project-management/scripts/_lib/session_guard.py
        - .pkit/adapters/claude-code/permission-hook.py
        - .pkit/rules/core.md
      record:
        - COR-039#1
        - COR-039#2
        - COR-039#3
        - ADR-034#1
        - ADR-034#2
        - ADR-034#4
        - ADR-034#5
        - ADR-061#6
      artefact:
        - ACT-operator
        - ACT-ai-agent
---

# UC-009 — Be asked before an agent changes another repository

**Goal:** Be asked before an agent changes a repository other than the session's own, so it never happens silently.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): the agent whose command would change the other repository. It makes no such change silently, and asks the operator whether to go on (core rule 19).

**Preconditions:** None.

**Assumptions:**

- The harness gives each session a session anchor, which does not move with `cd`. Claude Code names it in `CLAUDE_PROJECT_DIR` (ADR-034 point 1).
- An agent routes no change around the methodology's commands. Nothing checks such a route, and only core rule 19 asks it of the agent (COR-039 point 3).

**Trigger:** An agent runs a methodology command that changes a repository's hosting service, from a working directory in another repository than the session anchor's.

**Main path:**

1. The agent runs the command, such as `pkit pull-request merge <number>`.
2. Before the command reads or sends anything, the system's cross-repository guard compares two repositories, from git alone: the working directory's and the session anchor's.
3. The two are different repositories, and the command runs with no terminal. So the system refuses, and changes nothing. It says why, and names two ways on: `Run it from a session rooted in <target>, or pass --allow-foreign-repo to confirm the change there.`
4. The agent stops, and asks the operator whether to make the change in that repository (core rule 19).
5. The operator confirms the change.
6. The agent runs the command again with `--allow-foreign-repo`.
7. The system says that the change goes ahead in another repository, confirmed by `--allow-foreign-repo`, and makes the change.

**Variants:**

- **1a.** The command is a project-management verb, such as `pkit pm open-pr`. The capability's own guard compares the same two repositories, and refuses or asks in the same way. A verb that hands its change on to the backbone passes the operator's confirmation on, so nobody is asked twice (ADR-061 point 6).
- **1b.** The agent writes a file with `Edit` or `Write` at an absolute path outside the session anchor, while the permission hook is registered. The hook asks the operator to confirm the write, naming both paths. Without the hook, the system asks nothing, and the harness's own flow applies (ADR-034 point 2).
- **1c.** The agent routes the change around the methodology's commands, such as with `git -C <path> commit`, `gh -R <repository>`, or `gh` with `GH_REPO` set. No check sees the change (ADR-034 point 5).
- **2a.** The working directory lies in a linked worktree of the session's repository, or in another clone of its `origin`. The system counts it as the session's own repository. The change goes ahead with no question, and the use case ends.
- **2b.** The harness gives no session anchor, or one side lies in no git repository. The guard has nothing to compare, so the change goes ahead. Its verdict says `undetermined`, never that the target is the session's own (COR-039 point 3).
- **2c.** git cannot be asked, such as when it does not answer in time. The system warns that the guard could not compare, and the change goes ahead.
- **3a.** The command runs at a terminal, as when the operator runs it. The system asks `Make the change there anyway? [y/N]`. A yes makes the change, and the use case ends. Any other answer refuses it.
- **3b.** The command is a dry run. It asks nothing, and refuses as a run with no terminal would. With `--allow-foreign-repo`, it previews the confirmed run.
- **5a.** The operator declines, or chooses to open a session rooted in the other repository. The agent makes no change there, and the use case ends.

**Postconditions:** The change lands in the other repository only with the operator's confirmation, and the command's output says it was confirmed.

**Minimal guarantees:**

- A change the guard refused makes no request of the hosting service (ADR-061 point 6 and `session_guard.py`).
- A command with no terminal never asks. It refuses unless the call carries the confirmation (COR-039 point 1 and `session_guard.py`).
- Where the guard cannot compare, its verdict says so, and never reads the target as the session's own (COR-039 point 3).
- A command makes its change only in the directory the guard cleared (`session_guard.py`).
