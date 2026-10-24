---
id: UC-032
title: Be asked before an agent changes another repository
status: active
actor: ACT-operator
other-actors:
  - ACT-ai-agent
after:
  - [UC-014, UC-049]
requirements:
  - REQ-012
shortfalls:
  - at: "1d"
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/session_guard.py
        - src/project_kit/cli.py
        - .pkit/permissions/decide.py
        - .pkit/rules/core.md
      record:
        - COR-039#1
        - COR-039#2
        - COR-039#3
        - ADR-034#1
        - ADR-034#2
        - ADR-034#4
        - ADR-034#5
        - ADR-025#1
        - ADR-061#6
        - ADR-047#1
        - ADR-047#2
      artefact:
        - ACT-operator
        - ACT-ai-agent
        - REQ-012
    revalidated:
      at: 2026-10-24T04:45:32Z
      outcome: unchanged
      unchanged-because: The guard before a change to another repository and the hook ask on a foreign file write are as before. The new ask concerns a deferred Bash call that may hide a guardrail, which is not about another repository.
---

# UC-032 — Be asked before an agent changes another repository

**Goal:** Be asked before an agent changes a repository other than the session's own, so it never happens silently.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): the agent whose command would change the other repository. The agent makes no such change silently, and asks the operator whether to go on (core rule 19).

**Preconditions:** **From UC-014 or UC-049:** The project runs the system: it is the methodology's source repository, or the system is installed in it.

**Assumptions:**

- The harness records a session anchor as a session starts, and the anchor does not move with `cd`. The system reads Claude Code's from `CLAUDE_PROJECT_DIR` (ADR-034 point 1).
- An agent routes no change around the system's own commands. Nothing checks such a route, and only core rule 19 asks it of the agent (COR-039 point 3).

**Trigger:** An agent runs a command of the system that changes a repository's state on its hosting service, such as merging a pull request. It runs the command from a working directory in a repository other than the session anchor's.

**Main path:**

1. The agent runs the command, such as `pkit pull-request merge <number> --subject "<title>"`.
2. Before the command reads or sends anything, the cross-repository guard compares two repositories, from git alone (ADR-034 point 1). They are the working directory's and the session anchor's.
3. The two are different repositories, and no terminal can be asked. So the system refuses and changes nothing, as COR-039 point 1 asks. It exits with status `1` (`cli.py`). It names two ways on: `Run it from a session rooted in <target>, or pass --allow-foreign-repo to confirm the change there.`
4. The agent stops, and asks the operator whether to make the change in that repository (core rule 19).
5. The operator confirms the change.
6. The agent runs the command again with `--allow-foreign-repo`.
7. The system says on standard error that the change goes ahead, `confirmed by --allow-foreign-repo`, and makes the change.

**Variants:**

- **1a.** The command is one that an installed capability ships. COR-039 point 2 puts the check in that capability's own code too, and the capability's analysis states it.
- **1b.** The agent writes a file with a file tool at an absolute path outside the session anchor's directory. An adapter's permission hook may ask the operator to confirm such a write, naming both paths (ADR-034 point 2). Claude Code's hook asks for `Edit` and `Write` where no grant decides the call, and compares paths, so it asks for a linked worktree too. Without the hook, nothing asks.
- **1c.** The agent changes the other repository around the system's commands, such as with `git -C <path> push` or `gh -R <repository>`. No guard sees the change (ADR-034 point 5). The permission code allows `cd <path> && git commit` wherever `vcs` is granted, since it strips the leading `cd` (ADR-025 point 1).
- **1d.** The command changes files rather than the hosting service, such as `pkit new decision` or `pkit sync`. At its entry, before it reads anything, the command compares the two repositories as step 2 does (REQ-012). The path goes on at step 3.

> [!WARNING]
> **Not built yet:** only the commands that change the hosting service run the guard. So a command that only writes files changes the other repository with no question. The guarded ones are the `pkit pull-request` verbs that write, `pkit version tag` and `untag` with `--push`, `pkit release apply` with `--tag --push`, `release merge` and `release publish-notes`. ADR-034 point 1 decides that every `pkit` command that writes runs the guard, and #1765 tracks it.

- **1e.** The command is `pkit report`, which files a report on the repository of the distribution. That write lies outside the guard by its kind. It is confirmed at a terminal, and with nobody to ask it is only drafted (ADR-047 points 1 and 2).
- **2a.** The working directory lies in a linked worktree of the session's repository, or in another clone whose `origin` matches the session's. The system counts it as the session's own repository. The change goes ahead with no question, and the use case ends.
- **2b.** The system finds no session anchor, or one side lies in no git repository. It reads only Claude Code's, so under another harness it finds none. The guard has nothing to compare, so the change goes ahead. Its verdict says `undetermined`, never that the target is the session's own (ADR-061 point 6).
- **2c.** git cannot be asked, such as when it does not answer in time. The system warns that the guard `could not compare`, and the change goes ahead.
- **2d.** `GH_REPO` is set in the environment, so `gh` acts on a repository the working directory does not hold. The guard compares directories alone, so it does not see the change (`session_guard.py`).
- **3a.** A terminal is at hand on standard input and standard error, as when the operator runs the command. The system asks `Make the change there anyway? [y/N]` (ADR-034 point 4). A yes makes the change, and the use case ends. Any other answer refuses it.
- **3b.** The command is a dry run, which `pkit pull-request land`, `pkit release merge` and `release publish-notes` offer. The system asks nothing and refuses, saying that a run at a terminal would ask. With `--allow-foreign-repo`, it previews the confirmed run.
- **5a.** The operator declines, or chooses to open a session rooted in the other repository. The agent makes no change there, and the use case ends.

**Postconditions:** The change lands in the other repository only with the operator's confirmation, and the command's output says it was confirmed.

**Minimal guarantees:**

- A change the backbone's guard refused makes no request of the hosting service (ADR-061 point 6 and `session_guard.py`).
- Where the target is another repository, a command with no terminal never asks. It refuses unless the call carries the confirmation (COR-039 point 1 and `session_guard.py`).
- Where the guard cannot compare, its verdict says so, and never reads the target as the session's own (ADR-061 point 6).
- A command makes its change only in the directory the guard cleared (`session_guard.py`).
