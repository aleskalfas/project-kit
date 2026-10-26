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
---

# UC-032 — Be asked before an agent changes another repository

**Goal:** Be asked before an agent changes a repository other than the session's own, so it never happens silently.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): the agent whose command would write in the other repository. The agent makes no such write silently, and asks the operator whether to go on (core rule 19).

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The [harness](../../../glossary.md#term-harness--harness) records a [session anchor](../../../glossary.md#term-session-anchor--session-anchor) as a session starts, and the session anchor does not move with `cd`. The [system](../../../glossary.md#term-system--system) reads Claude Code's from `CLAUDE_PROJECT_DIR` (ADR-034 [point](../../../glossary.md#term-point--point) 1).
- An agent routes no write around the system's own commands. Nothing checks such a route, and only core rule 19 asks it of the agent (COR-039 point 3).

**Trigger:** An agent runs a command of the [system](../../../glossary.md#term-system--system) that changes a repository's state on its hosting service, such as merging a [pull request](../../../glossary.md#term-pull-request--pull-request). It runs the command from a working directory in a repository other than the [session anchor](../../../glossary.md#term-session-anchor--session-anchor)'s.

**Main path:**

1. The agent runs the command, such as `pkit pull-request merge <number> --subject "<title>"`.
2. Before the command reads or sends anything, the cross-repository guard compares two repositories, from git alone (ADR-034 [point](../../../glossary.md#term-point--point) 1). They are the working directory's and the [session anchor](../../../glossary.md#term-session-anchor--session-anchor)'s.
3. The two are different repositories, and no terminal can be asked. So the [system](../../../glossary.md#term-system--system) refuses and changes nothing, as COR-039 point 1 asks. It exits with status `1` (`cli.py`). It names two ways on: `Run it from a session rooted in <target>, or pass --allow-foreign-repo to confirm the change there.`
4. The agent stops, and asks the operator whether to write in that repository (core rule 19).
5. The operator confirms the write.
6. The agent runs the command again with `--allow-foreign-repo`.
7. The system says on standard error that the write goes ahead, `confirmed by --allow-foreign-repo`, and makes the write.

**Variants:**

- **1a.** The command is one that an installed [capability](../../../glossary.md#term-capability--capability) ships. COR-039 [point](../../../glossary.md#term-point--point) 2 puts the check in that capability's own code too, and the capability's analysis states it.
- **1b.** The agent writes a file with a file tool at an absolute path outside the [session anchor](../../../glossary.md#term-session-anchor--session-anchor)'s directory. An [adapter](../../../glossary.md#term-adapter--adapter)'s [permission hook](../../../glossary.md#term-permission-hook--permission-hook) may ask the operator to confirm such a write, naming both paths (ADR-034 point 2). Claude Code's hook asks for `Edit` and `Write` where no [grant](../../../glossary.md#term-grant--grant) decides the call, and compares paths, so it asks for a linked worktree too. Without the hook, nothing asks.
- **1c.** The agent changes the other repository around the [system](../../../glossary.md#term-system--system)'s commands, such as with `git -C <path> push` or `gh -R <repository>`. No guard sees the write (ADR-034 point 5). The permission code allows `cd <path> && git commit` wherever `vcs` is granted, since it strips the leading `cd` (ADR-025 point 1).
- **1d.** The command changes files rather than the hosting service, such as `pkit new decision` or `pkit sync`. At its entry, before it reads anything, the command compares the two repositories as step 2 does ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)). The path goes on at step 3.

> [!WARNING]
> **Not built yet:** only the commands that write to the hosting service run the guard. So a command that only writes files changes the other repository with no question. The guarded commands are these:
>
> - the `pkit pull-request` verbs that write
> - `pkit version tag` and `untag` with `--push`
> - `pkit release apply` with `--tag --push`
> - `release merge`
> - `release publish-notes`
>
> ADR-034 point 1 decides that every `pkit` command that writes runs the guard, and #1765 tracks it.

- **1e.** The command is `pkit report`, which files a [report](../../../glossary.md#term-report--report) on the repository of the [distribution](../../../glossary.md#term-distribution--distribution). That write lies outside the guard by its kind. It is confirmed at a terminal, and with nobody to ask it is only drafted (ADR-047 points 1 and 2).
- **2a.** The working directory lies in a linked worktree of the session's repository, or in another clone whose `origin` matches the session's. The system counts it as the session's own repository. The write goes ahead with no question, and the use case ends.
- **2b.** The system finds no session anchor, or one side lies in no git repository. It reads only Claude Code's, so under another [harness](../../../glossary.md#term-harness--harness) it finds none. The guard has nothing to compare, so the write goes ahead. Its verdict says `undetermined`, never that the target is the session's own (ADR-061 point 6).
- **2c.** git cannot be asked, such as when it does not respond in time. The system warns that the guard `could not compare`, and the write goes ahead.
- **2d.** `GH_REPO` is set in the environment, so `gh` acts on a repository the working directory does not hold. The guard compares directories alone, so it does not see the write (`session_guard.py`).
- **3a.** A terminal is at hand on standard input and standard error, as when the operator runs the command. The system asks `Make the change there anyway? [y/N]` (ADR-034 point 4). A yes makes the write, and the use case ends. Any other reply refuses it.
- **3b.** The command is a dry run, which `pkit pull-request land`, `pkit release merge` and `release publish-notes` offer. The system asks nothing and refuses, saying that a run at a terminal would ask. With `--allow-foreign-repo`, it previews the confirmed run.
- **5a.** The operator declines, or chooses to open a session rooted in the other repository. The agent writes nothing there, and the use case ends.

**Postconditions:** A write lands in the other repository only with the operator's confirmation, and the command's output says it was confirmed.

**Minimal guarantees:**

- A write the [backbone](../../../glossary.md#term-backbone--backbone)'s guard refused makes no request of the hosting service (ADR-061 [point](../../../glossary.md#term-point--point) 6 and `session_guard.py`).
- Where the target is another repository, a command with no terminal never asks. It refuses unless the call carries the confirmation (COR-039 point 1 and `session_guard.py`).
- Where the guard cannot compare, its verdict says so, and never reads the target as the session's own (ADR-061 point 6).
- A command writes only in the directory the guard cleared (`session_guard.py`).
