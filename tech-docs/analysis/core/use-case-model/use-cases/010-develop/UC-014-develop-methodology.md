---
id: UC-014
title: Develop the methodology in its source repository
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ai-agent
requirements:
  - REQ-008
  - REQ-009
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
        - REQ-008
        - REQ-009
    revalidated:
      at: 2026-10-24T19:00:43Z
      outcome: unchanged
      unchanged-because: "As #2003 asks, the unregister in the source now refuses an answer piped in, unless --yes is given. Its question, and the refusal of --purge, are as variant 2d says."
---

# UC-014 — Develop the methodology in its source repository

**Goal:** Develop the methodology in its source repository, where no sync copies over my work, and run what I ship there before any adopter does.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs `pkit` commands in the checkout for the maintainer, and gets the same code as the maintainer does, the checkout's own. Its sessions load the [skills](../../../glossary.md#term-skill--skill), [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) and [operational rules](../../../glossary.md#term-operational-rule--operational-rule) that [sync](../../../glossary.md#term-sync--sync) deployed from the [methodology](../../../glossary.md#term-methodology--methodology) as edited.

**Preconditions:** None.

**Assumptions:**

- The [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository) exists, and the maintainer works in a clone or a worktree of it, the checkout. Its root holds the methodology's tree, `.pkit/`, beside the package source, `src/project_kit/` (ADR-059 points 1 and 3).
- The methodology's tree holds an [adapter](../../../glossary.md#term-adapter--adapter) for the [harness](../../../glossary.md#term-harness--harness) the maintainer works in, under `.pkit/adapters/`, such as `claude-code` (COR-005).
- Python 3.11 or later and `uv` are installed on the machine. The dispatcher `.pkit/cli/pkit` runs the package with them (PRJ-003).

**Trigger:** The maintainer sets out to edit the [methodology](../../../glossary.md#term-methodology--methodology), such as a core record, a [skill](../../../glossary.md#term-skill--skill) or the [backbone](../../../glossary.md#term-backbone--backbone)'s code.

**Main path:**

1. The maintainer edits the [methodology](../../../glossary.md#term-methodology--methodology) in the checkout: its tree `.pkit/`, and the package source `src/project_kit/`.
2. The maintainer, or an AI agent working for the maintainer, runs a `pkit` command anywhere in the checkout. The command may come from the CLI installed on the machine, or from `uv run pkit`.
3. The [system](../../../glossary.md#term-system--system) walks up from the working directory to the checkout's root, and finds the package source beside `.pkit/` there (`router.is_source_checkout`). So it hands the command to the checkout's own dispatcher, the script `.pkit/cli/pkit`, whatever [release](../../../glossary.md#term-release--release) the installed CLI is (ADR-039 [point](../../../glossary.md#term-point--point) 1).
4. The dispatcher runs the command with `uv run --quiet --project <root> python -m project_kit`. So the command runs the checkout's code as edited, and reads the methodology's files from the checkout's own `.pkit/` (`install.find_source_kit`). `pkit status` shows that tree on its line `Source kit:`.
5. After adding a [skill](../../../glossary.md#term-skill--skill), or editing an [agent definition](../../../glossary.md#term-agent-definition--agent-definition) or the settings the methodology merges, the maintainer runs `pkit sync`. The [harness](../../../glossary.md#term-harness--harness) then reads the edit.
6. The system recognises the [source repository](../../../glossary.md#term-source-repository--source-repository): the checkout's root holds the very tree that the running code reads (`install.is_self_host`, ADR-059 point 2). It prints `Syncing project-kit at <root> (self-host)` and `source == target: skipping propagation; running deploy primitives only.`, and copies no file.
7. The system runs each [adapter](../../../glossary.md#term-adapter--adapter)'s [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) into the files its harness reads, such as `claude-code`'s into `.claude/settings.json` and `CLAUDE.md`. Each adapter deploys the skills and agent definitions as edited. The system also does these (ADR-065 point 11):
   - it renders `.pkit/.gitignore`
   - it makes the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace), `.agent-workspace/`
   - it sets up each command a [capability](../../../glossary.md#term-capability--capability) registers
8. The system prints `Self-host sync complete (deploy primitives re-run).`

**Variants:**

- **2a.** The maintainer runs the dispatcher `.pkit/cli/pkit` itself. The path goes on at step 4.
- **2b.** The maintainer runs `pkit init` in the checkout. The [system](../../../glossary.md#term-system--system) refuses with `<root> is already a project-kit project.`, names `pkit sync` to refresh it, and writes nothing (`install.py`). The use case ends.
- **2c.** The maintainer runs `pkit pin <version>`. The system refuses with ``refusing to pin <root>: it is the methodology's source repository``, since the checkout's own code runs before any pin is read, and writes nothing. To move the checkout to another [release](../../../glossary.md#term-release--release), the maintainer updates it with git (ADR-059 [point](../../../glossary.md#term-point--point) 3). The use case ends.
- **2d.** The maintainer runs `pkit capabilities install <name>` for a [capability](../../../glossary.md#term-capability--capability) the tree authors. The system records the capability as `kit-shipped` in the [manifest](../../../glossary.md#term-manifest--manifest), copies nothing, and says that `nothing was copied (ADR-059)`. Uninstalling it later only takes it out of the manifest, after asking `Unregister '<name>' and keep .pkit/capabilities/<name>/?`, and the system refuses `--purge` there (ADR-059).
- **3a.** The installed CLI started the command, and the dispatcher `.pkit/cli/pkit` is missing or not executable. The system warns on standard error that it runs the installed CLI's code instead, `which is not this checkout's code`. The warning names the repair: restore the dispatcher with `git checkout`, or make it executable (ADR-059). Once the maintainer repairs the dispatcher, the path rejoins at step 2.
- **3b.** The installed CLI started the command with routing switched off, by `PKIT_NO_ROUTE=1` or by `PKIT_ROUTED=1` inherited from another run. The command runs with the installed CLI's code, with no warning, and a [sync](../../../glossary.md#term-sync--sync) meets 6a. Once the maintainer clears the variable, the path rejoins at step 2.
- **5a.** The maintainer runs `pkit upgrade` instead. The system prints `Self-host: source is the installed state; no backbone upgrade needed.` and `Re-running deploy primitives via sync.`, and the path goes on at step 6.
- **6a.** The running code is not the checkout's own (3a, 3b), so the root does not hold the tree that code reads. The package source beside `.pkit/` still marks the [source repository](../../../glossary.md#term-source-repository--source-repository). The system refuses, and its message gives these:
  - the refusal, ``refusing to run `sync` in <root>: it is the methodology's source repository, and the running pkit is not its own code.``
  - `Nothing was written, and no flag overrides this refusal.`
  - how the run got there
  - the remedy, running `.pkit/cli/pkit sync` from the root

  `pkit upgrade` refuses the same way (ADR-059 point 3), and the use case ends.

**Postconditions:**

- Every `pkit` command run in the checkout runs the checkout's own code, and reads its own `.pkit/`. So what the [source repository](../../../glossary.md#term-source-repository--source-repository) ships runs there before any adopter runs it.
- No [sync](../../../glossary.md#term-sync--sync) has copied a file into the [methodology](../../../glossary.md#term-methodology--methodology)'s tree. There, sync only regenerates what derives from the tree.
- Each [adapter](../../../glossary.md#term-adapter--adapter) the tree holds deploys the [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) as edited, where its [harness](../../../glossary.md#term-harness--harness) reads them. It also merges the [operational rules](../../../glossary.md#term-operational-rule--operational-rule) into the harness's instruction file.
- The source repository runs the [system](../../../glossary.md#term-system--system) as written, with no [release](../../../glossary.md#term-release--release) and no [install](../../../glossary.md#term-install--install).

**Minimal guarantees:**

- Code other than the checkout's own never propagates its tree over the [methodology](../../../glossary.md#term-methodology--methodology)'s. [Sync](../../../glossary.md#term-sync--sync) and upgrade refuse, and no flag overrides the refusal (ADR-059 [point](../../../glossary.md#term-point--point) 3 and `install.refuse_propagation_into_source`).
- Where the checkout's dispatcher cannot run a command the installed CLI started, the [system](../../../glossary.md#term-system--system) warns before it runs other code (ADR-059 and `router.py`).
- `pkit init` and `pkit pin` write nothing in the [source repository](../../../glossary.md#term-source-repository--source-repository) (ADR-059 point 3 and `install.py`).
- No [capability](../../../glossary.md#term-capability--capability) verb deletes a capability's subtree in the source repository, since that subtree is the capability's source (ADR-059 and `cli.py`).
