---
id: ADR-086
title: One reader in the agents area reads an agent's tool access
status: accepted
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** several parts of pkit read which tools an agent's definition gives it, each in its own way, and they disagree. One module does that reading, and every part that needs it calls it. It is kept in the agents area of the `.pkit/` tree that sync copies into each project, so the scripts that run in a project and the `pkit` command reach the same code.

The module applies the rules the core agents record states (COR-013 point 7), such as that a definition holding both forms is refused. The Claude Code adapter keeps what is Claude Code's own: its keys, its tool names, and which withheld entries it can enforce. Each adapter declares these as data, so the validator refuses what the deploy and the runner refuse. A definition refused for its tool access deploys nothing, and the copy deployed before it is removed, so no agent keeps tools its definition no longer gives.

## Context

An agent's tool access is a grant, a withheld list, or neither, by rules the core agents record states ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 7). The Claude Code adapter writes it in Claude Code's keys, and every check reads it from the definition ([ADR-085](ADR-085-agent-tool-access.md) points 1 and 2).

Several parts read a definition's tools, among them the adapter's deploy, the agent runner ([ADR-066](ADR-066-unattended-agent-runner.md)), the reference validator's storyboard check, and a capability's check of a fixer's tools. Each parses and reads them its own way, and they disagree:

- The runner refuses `Agent(worker)` as a tool's name, while a capability's reader takes it as `Agent`.
- An empty `tools` reads as every tool to that reader, and as a list without `Read` to the validator.
- `tools:` with no value reads as an empty grant to the runner's own parser, and as absent to the parsers the other parts use.
- The validator skips its storyboard check on a grant written as one string.

A withheld list read wrongly fails open.

Measured with Claude Code 2.1.319, from the init message a session reports at its start, an agent whose `tools` is an empty list has no tools, whether it is given on the command line or by a file. Only a whole built-in tool in `disallowedTools` was measured to leave an agent's view.

Where shared code can live is settled for this tree ([ADR-003](ADR-003-permission-core-code-home.md)). Code the `pkit` command does not bundle, and that belongs to no adapter, is propagated neutral code: kept in the `.pkit/` tree, copied into each project by sync, and imported there by the scripts that run in the project. Those scripts cannot import the command's own code, and neither the command's code nor neutral code imports an adapter. The runner uses only the standard library, under the system's Python. The permission core and the lifecycle area's ownership module ([ADR-051](ADR-051-process-author-edit-authority.md) point 3) are kept this way.

## Decision

**One standard-library module of propagated neutral code, at the root of the agents area, reads an agent's tool access from its definition's text. Every part that reads a definition's tools calls it, and none reads them itself. The adapter keeps its harness's keys and names. A definition refused for its tool access is not deployed, and its earlier copy is removed.**

### 1. Where it lives

The module is `.pkit/agents/tool_access.py`, at the root of the agents area, beside the area's README and its other specification pages. Its path is part of its interface, so moving it is a change adopters can see. It does not sit under `core/` or `project/`, where every folder names an agent. It uses only the standard library, since the runner runs under the system's Python with nothing installed. This follows the rule for propagated neutral code that ADR-003 states: the root of the area whose subject it serves.

A caller loads it from its file, without adding the area to Python's import path and without writing bytecode into the tree, as the command loads the ownership module. The reader is part of the resolution of an agent, which ADR-066 point 3 and ADR-073 point 2 read from the pinned commit or the default branch's head, never from a working run's clone. A capability's script reaches it in the tree, as it reaches the ownership module, since it is propagated code, not one of the command's engines ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1).

### 2. What it reads and answers

It reads the two keys of tool access from the front matter's text itself, so no caller's parser decides what they hold. It refuses a front matter holding a top-level line it cannot read as a key, or a key written twice, so no key it misses reaches the harness. It reads a value written as a list, on one line or one entry to a line, or as one string whose entries are separated by commas outside parentheses. A key with no value holds no entries, and a value written any other way is refused. It applies COR-013 point 7's rules, and answers with the definition's form and its entries, each with any argument it carries, or with why the definition is refused. It answers both of ADR-085 point 2's readings, that an agent holds a tool and that it lacks one.

The validator reports as a warning each key of an agent's definition that is none of a definition's fields, as the agents README's frontmatter schema names them under COR-013 points 2 and 7 and [COR-016](../../../.pkit/decisions/core/COR-016-scripted-scenario-storyboards.md). A harness's own key is among them, and a confined run refuses it (ADR-066 point 3).

### 3. What a writer writes

The deploy and the runner write a definition's tool access from the reader's answer, as a list of whole entries with their arguments, an empty grant as an empty list, never from the author's text.

A definition refused for its tool access is not written. The deploy names the cause, and removes the earlier copy that carries its mark, as it removes such a copy whose source is gone, so no earlier copy gives tools the definition no longer gives (COR-013 point 7). The agent is missing until its definition is mended. A run of a refused definition is refused.

### 4. The harness's keys and names stay in the adapter

The map from the methodology's forms to a harness's keys is kept in that harness's adapter, in its declaration of tool access below, which both its resolver and its runner read. The resolver keeps the methodology's form in what it gives the runner, and writes the harness's keys only in what it gives the deploy.

The adapter refuses what its harness cannot enforce or translate (COR-013 point 7):

- **A withheld name it does not know** as one of its harness's built-in tools. The adapter keeps its harness's known tool names in its declaration of tool access, below.
- **A withheld entry its harness was not measured to withhold.** An entry measured to be withheld where the harness runs the agent as a whole session's agent is admitted, and the requirement for a helper stays unanswered until it is measured (ADR-085 point 3). Its declaration of tool access says which entries it admits, and its support declaration what was measured.
- **A tool's name in a form its harness does not take.**
- **A harness's own key held beside the form that translates to it,** such as Claude Code's `disallowedTools` beside `withheld`.

The adapter's refusals are made by the reader, against the adapter's declaration of tool access: a data file of a fixed name, `tool-access.json`, in the adapter's folder, whose presence is the declaration. Everything those refusals read is declared there as data: the map to the harness's keys, its known tool names, the forms a tool's name may take, and the withheld entries it admits, which may be none. Its shape is the reader's contract, owned by the backbone with a schema beside the other schemas it owns. The file carries a schema version, and the reader refuses a declaration whose version or keys it does not know, naming which side is behind. A change of shape takes a new version and ships its migration. A pattern a declaration gives is in Python's dialect and matches a whole name, and the reader's own grammar of an entry bounds what any harness can declare. So the adapter's deploy and runner, which give the reader their own adapter's declaration, and the reference validator refuse alike.

An adapter that deploys agents declares its tool access. The validator reads the declaration of every registered adapter that deploys agents, and refuses a definition any of them would refuse, naming the adapter and the cause. So a definition passes only where every such adapter takes it, and registering a second harness's adapter can refuse definitions that passed before. It reports as an error an adapter that deploys agents and declares none, or whose declaration cannot be read. It also reports an adapter that admits a withheld entry while its support declaration does not answer the requirement for a session's agent withheld tools as achievable for some version (ADR-085 point 3).

### 5. A command that cannot reach the reader

A command loads the reader only where it has a definition to read. Where it finds no reader in a project's tree, or not the function it calls, it refuses that step. Inside the validator, the refusal is an error finding, not the end of the run.

The command tells which side is behind by comparing the project's backbone version with the one it bundles. Where the project's is older or the same, the project needs a sync; where it is newer, the command needs an upgrade.

A function of the reader keeps its name and its answer. A function whose answer changes takes a new name, so an older command never reads a newer reader's answer as its own.

## Rationale

**One reader, because separate readers disagree.** Each part that keeps its own reading drifts from the others, as the Context shows, and a withheld list read wrongly fails open. The reader parses the two keys itself because parsing is where some of the disagreement sits.

**At the root of the agents area.** Propagated neutral code is the one home both the scripts in a project and the command reach (ADR-003). The module serves the agents area's subject and is read with its specification, as the ownership module is read with the lifecycle's.

**The rules are core's, the reader applies them.** The reader is copied into every project, so what it refuses binds every project's agents. Those rules are stated where every project receives them, in COR-013 point 7.

**The adapter keeps what is its harness's.** Neutral code carries no knowledge of one harness's keys or tool names (ADR-003). Only the adapter knows which names its harness has and which withheld entries it was measured to enforce, so a second adapter brings its own.

**The validator reads the adapter's declaration, not its code.** Neutral code and the command import no adapter, and harness knowledge reaches them as data, not as code (ADR-003). A declaration lets the validator refuse what the deploy and the runner refuse, before either runs, without running adapter code or keeping a second copy of the names. A fixed name lets every reader find it the same way, as the adapter's other declarations are found. JSON, because the runner reads it under the system's Python. A schema version, because three parts meet at the file at their own versions, and a reader that misread a newer declaration's admitted entries would fail open.

**Writers write the reader's answer.** The harness then sees only the forms the reader settled, never an author's text the harness might read another way.

**A refused definition removes its earlier copy.** Leaving the earlier copy would run an agent with tools its definition no longer gives, which COR-013 point 7 refuses. A missing agent is visible, and its cause is named.

**A key the methodology does not define is a warning.** Agents written with a harness's own keys deploy today, and a warning reaches their authors without stopping them. Its cost is named: a harness's own key that withholds a tool is invisible to the reader, so a check may find a tool the harness then withholds.

**A command refuses rather than guesses.** A skipped check that let the command succeed would pass as satisfied.

### Alternatives considered

- **State the rules once, and implement them in each part.** One table of definitions and outcomes, loaded by every part's tests. Rejected: the parts stay copies that agree only where the tests reach.
- **Let the reader also pick which definition of an agent runs.** Deferred to its own Task ([project-kit#2954](https://github.com/aleskalfas/project-kit/issues/2954)): it is a question of its own, on which capabilities count as installed and what an uninstall removes. The fixers' check moves to the reader only after that Task, so it adds no picker of its own.
- **A shared library folder for propagated neutral code.** Rejected: it would group modules by their language, not their subject. ADR-003 and ADR-020 state the rule this record follows.
- **Keep a refused definition's earlier copy,** as the deploy keeps one for every other skip. Rejected: the earlier copy may give tools the definition no longer gives.
- **Read a harness's key for a withheld list as the methodology's.** Rejected: neutral code would carry one harness's key.
- **Refuse a harness's key in a definition.** Rejected for now: agents written with one would stop deploying. To be revisited when a second harness's adapter deploys agents, since one harness's key in a definition then deploys wrongly to the other. The declarations' maps then give the validator every registered harness's keys, so its warning can name the harness a key belongs to.
- **The validator runs a check the adapter provides,** as a hook the adapter's package manifest names. Rejected: validation would run adapter code, and a declaration in data can be read, diffed and tested where a check cannot.
- **Name the declaration's path in the adapter's package manifest.** Rejected: the runner reads no YAML, so it would find the file by a name of its own, and two sources of one path can drift.
- **Fold the declaration into the adapter's support declaration.** Rejected: the support declaration detects and never drives (COR-047), and the runner cannot read it. The validator's cross-check keeps the two agreeing.
- **A copy of the adapter's names in the command's code.** Rejected: two lists of one harness's names, which drift.
- **Number the reader's interface.** Rejected: nothing would own the number. A function's name is its version, owned by whoever changes the function.

## Implications

- **COR-013 point 7,** refined in place in the change that proposes this record, states the rules the reader applies, and that an adapter leaves no earlier copy of a definition it refuses for its tool access.
- **ADR-003 and ADR-020,** refined in place in the same change, state the rule for where propagated neutral code lives, in place of a shared library folder.
- **ADR-085 point 2's two readings** are the reader's. ADR-085 cites this record.
- **The agents README** documents the reader, its place in the area's layout, the warning on other keys, and the deploy's removal of a refused definition's copy, as an exception to its rule that a skip leaves the earlier copy.
- **Sync** copies the module, as it copies the ownership module, and the lifecycle's manifest lists it. The runner gains its first import from the tree, as the permission hook has.
- **A capability whose script loads the reader** declares the backbone release that ships it.
- **The adapters README** gains a section on what an adapter declares as data, its declaration of tool access beside its support and enforcement declarations, and says under "Adding a new harness" that an adapter that deploys agents declares its tool access. The agents README's "Tool access" says the validator makes the adapter's refusals too. The Claude Code adapter keeps its declaration as data, in place of a constant in its code. [project-kit#2949](https://github.com/aleskalfas/project-kit/issues/2949) decides whether its probed table writes the known names into the declaration, held equal by a check, or keeps them apart. Until then they are written by hand.
- **An agent that stops deploying.** One whose tool access breaks a rule is removed, and the deploy names the cause.
