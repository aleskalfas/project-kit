---
id: UC-014
title: Develop the methodology in its source repository
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - .pkit/cli/pkit
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - src/project_kit/upgrade.py
        - src/project_kit/status.py
        - src/project_kit/cli.py
      record:
        - ADR-059
        - ADR-039#1
        - ADR-065#11
        - PRJ-003
        - COR-005
      artefact:
        - ACT-methodology-maintainer
        - ACT-ai-agent
---

# UC-014 — Develop the methodology in its source repository

**Goal:** Develop the methodology in its source repository, where no sync copies over my work, and run what I ship there before any adopter does.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs `pkit` commands in the checkout for the maintainer, and gets the same code as the maintainer does, the checkout's own. Its sessions load the skills, agent definitions and operational rules that sync deployed from the methodology as edited.

**Preconditions:** None.

**Assumptions:**

- The methodology's source repository exists, and the maintainer works in a clone or a worktree of it, the checkout. Its root holds the methodology's tree, `.pkit/`, beside the package source, `src/project_kit/` (ADR-059 points 1 and 3).
- The methodology's tree holds an adapter for the harness the maintainer works in, under `.pkit/adapters/`, such as `claude-code` (COR-005).
- Python 3.11 or later and `uv` are installed on the machine. The dispatcher `.pkit/cli/pkit` runs the package with them (PRJ-003).

**Trigger:** The maintainer sets out to change the methodology, such as a core record, a skill or the backbone's code.

**Main path:**

1. The maintainer edits the methodology in the checkout: its tree `.pkit/`, and the package source `src/project_kit/`.
2. The maintainer, or an AI agent working for the maintainer, runs a `pkit` command anywhere in the checkout. The command may come from the CLI installed on the machine, or from `uv run pkit`.
3. The system walks up from the working directory to the checkout's root, and finds the package source beside `.pkit/` there (`router.is_source_checkout`). So it hands the command to the checkout's own dispatcher, the script `.pkit/cli/pkit`, whatever release the installed CLI is (ADR-039 point 1).
4. The dispatcher runs the command with `uv run --quiet --project <root> python -m project_kit`. So the command runs the checkout's code as edited, and reads the methodology's files from the checkout's own `.pkit/` (`install.find_source_kit`). `pkit status` shows that tree on its line `Source kit:`.
5. After adding a skill, or editing an agent definition or the settings the methodology merges, the maintainer runs `pkit sync`. The harness then reads the edit.
6. The system recognises the source repository: the checkout's root holds the very tree that the running code reads (`install.is_self_host`, ADR-059 point 2). It prints `Syncing project-kit at <root> (self-host)` and `source == target: skipping propagation; running deploy primitives only.`, and copies no file.
7. The system runs each adapter's merge delivery into the files its harness reads, such as `claude-code`'s into `.claude/settings.json` and `CLAUDE.md`. Each adapter deploys the skills and agent definitions as edited. It also renders `.pkit/.gitignore`, makes the agent workspace `.agent-workspace/`, and sets up each command a capability registers (ADR-065 point 11).
8. The system prints `Self-host sync complete (deploy primitives re-run).`

**Variants:**

- **2a.** The maintainer runs the dispatcher `.pkit/cli/pkit` itself. The path goes on at step 4.
- **2b.** The maintainer runs `pkit init` in the checkout. The system refuses with `<root> is already a project-kit project.`, names `pkit sync` to refresh it, and writes nothing (`install.py`). The use case ends.
- **2c.** The maintainer runs `pkit pin <version>`. The system refuses with ``refusing to pin <root>: it is the methodology's source repository``, since the checkout's own code runs before any pin is read, and writes nothing. To move the checkout to another release, the maintainer updates it with git (ADR-059 point 3). The use case ends.
- **2d.** The maintainer runs `pkit capabilities install <name>` for a capability the tree authors. The system records the capability as `kit-shipped` in the manifest, copies nothing, and says that `nothing was copied (ADR-059)`. Uninstalling it later only takes it out of the manifest, after asking `Unregister '<name>' and keep .pkit/capabilities/<name>/?`, and the system refuses `--purge` there (ADR-059).
- **3a.** The installed CLI started the command, and the dispatcher `.pkit/cli/pkit` is missing or not executable. The system warns on standard error that it runs the installed CLI's code instead, `which is not this checkout's code`. The warning names the repair: restore the dispatcher with `git checkout`, or make it executable (ADR-059).

  The command runs with the installed CLI's code, and a sync meets 6a. Once the maintainer repairs the dispatcher, the path rejoins at step 2.
- **3b.** The installed CLI started the command with routing switched off, by `PKIT_NO_ROUTE=1` or by `PKIT_ROUTED=1` inherited from another run. The command runs with the installed CLI's code, with no warning, and a sync meets 6a. Once the maintainer clears the variable, the path rejoins at step 2.
- **5a.** The maintainer runs `pkit upgrade` instead. The system prints `Self-host: source is the installed state; no backbone upgrade needed.` and `Re-running deploy primitives via sync.`, and the path goes on at step 6.
- **6a.** The running code is not the checkout's own (3a, 3b). So the root does not hold the tree that code reads, while the package source beside `.pkit/` still marks the source repository. The system refuses, and its message gives these:
  - the refusal, ``refusing to run `sync` in <root>: it is the methodology's source repository, and the running pkit is not its own code.``
  - `Nothing was written, and no flag overrides this refusal.`
  - how the run got there
  - the remedy, running `.pkit/cli/pkit sync` from the root

  `pkit upgrade` refuses the same way (ADR-059 point 3). The use case ends.

**Postconditions:**

- Every `pkit` command run in the checkout runs the checkout's own code, and reads its own `.pkit/`. So what the source repository ships runs there before any adopter runs it.
- No sync has copied a file into the methodology's tree. There, sync only regenerates what derives from the tree.
- Each adapter the tree holds deploys the skills and agent definitions as edited, where its harness reads them. It also merges the operational rules into the harness's instruction file.
- The source repository runs the system as written, with no release and no install.

**Minimal guarantees:**

- Code other than the checkout's own never propagates its tree over the methodology's. Sync and upgrade refuse, and no flag overrides the refusal (ADR-059 point 3 and `install.refuse_propagation_into_source`).
- Where the checkout's dispatcher cannot run a command the installed CLI started, the system warns before it runs other code (ADR-059 and `router.py`).
- `pkit init` and `pkit pin` write nothing in the source repository (ADR-059 point 3 and `install.py`).
- No capability verb deletes a capability's subtree in the source repository, since that subtree is the capability's source (ADR-059 and `cli.py`).
