---
id: ADR-087
title: One picker in the agents area names which definition is an agent
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the project, a capability and core may each ship an agent of one name, and several parts of pkit each decide which of them is the agent, each in its own way. They disagree on which capabilities count, on the order between two capabilities, and on what an uninstall removes. One module in the agents area decides, and every part that picks asks it. It learns which capabilities are installed, and what the project chose between two of them, from one reader in the lifecycle area.

The rules are core's ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 8, and [COR-017](../../../.pkit/decisions/core/COR-017-capability-pattern.md)'s "Collision prevention" for capabilities). The deploy removes each copy it deployed from a definition that is no longer the agent, so an uninstall's own step removes no agents. Where the records cannot be read, the deploy changes nothing for the names they decide, and says so.

## Context

Which definition of a name is the agent is decided by rules core states: COR-013 point 8 for every place, COR-017 for capabilities. A capability counts while the component registry records it. A skip the project chose at a collision is recorded in the capability's per-component manifest, and the project's choice between two capabilities for an agent's name is recorded once, beside the registry. A capability authored in the project, or registered in the methodology's source, has no per-component manifest ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)).

Several parts pick a definition, and none reads the registry:

- The Claude Code adapter's deploy, in a shell script, takes every capability folder that holds agents, in the order the shell lists them, which follows the locale.
- The agent runner ([ADR-066](ADR-066-unattended-agent-runner.md)) takes every folder, hidden ones included, in code-point order.
- The command's listing of agents takes every folder, and its lookup of one agent only folders that hold a package manifest. Several commands read each.
- The reference graph's lookup of a storyboard's consumer reads core before the project.
- The install's collision check names the last capability by name, where the deploy takes the first.

So an unregistered capability whose files stay on disk keeps deploying, two capabilities that ship one agent name deploy whichever the locale lists first, and an override chosen at install against another capability's agent removes and records nothing.

The deploy keeps the copy it deployed before whenever it refuses a definition, but for its tool access ([ADR-086](ADR-086-tool-access-reader.md) point 3). Where a capability's definition of a core agent's name is refused, core's copy stays, and a session runs it while the command reads the capability's.

The adapter's uninstall step removes each deployed copy of a name the capability ships, sparing only a name the project ships, so it removes agents core or another capability ships. The deploy that runs after it then deploys an incubated capability's agents again from the folder left on disk.

The registry and the per-component manifests are read by the command, by the lifecycle area's ownership module ([ADR-051](ADR-051-process-author-edit-authority.md) point 3), and by narrow parsers in the adapter's shell scripts, each reading an unreadable file its own way. The ownership module, propagated neutral code at the lifecycle area's root, keeps only the standard library at module level and imports its YAML library inside the function that reads. The agent runner runs under the system's Python with only the standard library, and starts the adapter's resolver, which has the YAML library, for every confined run. A version transition settles collisions and records the project's choices before it copies the target release's files into the project (ADR-065 point 4).

## Decision

**One reader at the lifecycle area's root reads which capabilities are installed, their skips, and the project's choices between capabilities. One picker at the agents area's root names which definition is the agent of each name, from that reader and the places that ship definitions. Every part that picks a definition or lists where a name is shipped asks the picker. The deploy removes each copy that is not the agent's, so an uninstall's own step removes no agents, and it changes nothing for the names it cannot decide.**

### 1. The lifecycle's reader of capability records

The reader is `.pkit/lifecycle/capability_records.py`, propagated neutral code beside the ownership module, by the rule [ADR-003](ADR-003-permission-core-code-home.md) states. Its subject is the lifecycle's: the component registry, the project's choices beside it, and each per-component manifest's skips.

It answers, for a tree: each registered capability, its recorded skips of agents' names, and the project's choice for each agent's name. A per-component manifest that is absent records no skip. A registry, or a capability's manifest, that cannot be read is answered as unreadable, never as recording nothing, and each caller decides what an unreadable record means for it. The command's reading of a capability's skips and of the choices uses this reader, so the command and the picker read one file one way.

It keeps the ownership module's discipline: only the standard library at module level, and the YAML library imported inside the function that reads.

### 2. The picker

The picker is `.pkit/agents/definition_source.py`, propagated neutral code beside the reader of an agent's tool access. Each module's path is part of its interface.

It reads one tree, which its caller names: the tree the definition is read from. For the deploy and the command, that is the project's working tree. For a run, it is the tree ADR-066 point 3 and [ADR-073](ADR-073-builder-runs.md) point 2 read the definition from, never a working run's clone, so no commit on a Task's branch chooses which definition a later run takes.

A caller loads each module from the project's tree, as it loads the tool-access reader (ADR-086 point 1), but for an install and a version transition: before they copy the release's files into the project, they load both modules from the release they bring, so a project that predates the modules can still move to the release that ships them. The runner, which has no YAML library, asks the adapter's resolver, which it already starts for every confined run, through an entry that takes the agent's name and answers the picked file, which the runner then holds to its tree as for any definition.

It answers for every name some place ships, in one call:

- **the definition that is the agent,** its file and the place that ships it, a definition being its place and its name (COR-013 point 8);
- **or why the name has none:** only definitions that do not count ship it, or the place that would win holds both layouts;
- **every definition of the name,** each with whether it counts and why not;
- **each collision between two capabilities** that no recorded choice settles, with the capability that won it;
- **or that it cannot tell.** An unreadable registry or record of choices leaves it unable to tell any name a capability's folder ships, but for a name the project ships, which wins whatever capabilities are installed. One capability's unreadable manifest leaves it unable to tell the names that capability's folder ships, since its skips concern only those.

It does not read a definition's content. A definition it names as the agent, which the deploy or the runner then refuses, stays the agent (COR-013 point 8).

### 3. Who asks it, and what each says

Every part that picks a definition, or lists where a name is shipped, asks the picker and keeps no order of its own. A part that stamps a new agent into a named place keeps its own check that the place exists.

The reference validator reports from the picker's answer alone, never from deployed copies: each collision no recorded choice settles as a warning, and as errors each name whose winning place holds both layouts and each name the picker cannot tell.

The runner's unconfined form starts the harness with the agent's name, and the harness loads the deployed copy. It runs only where the project holds a copy the deploy marked, and otherwise refuses and says why, so the harness never loads a person's own agent of that name in the project's place.

### 4. What the deploy writes and removes

The deploy's mark on a copy keeps its text and its place in the copy's first lines, which other parts and shipped migrations match. Beside it, the deploy records the definition the copy was written from and a digest of the text it read, so a part that checks a definition can tell whether the copy that runs is of its current text.

The deploy writes the copy of each name's agent. It removes, and names, each copy it marked that was written from a definition that is not the agent, or that is of a name with no agent (COR-013 point 8). Where it refuses the agent's current text for a cause other than its tool access, it keeps the copy written earlier from that definition, and says the copy is not of the current text. A copy whose mark records no definition is read as written from the agent where only one place ships the name, and as not the agent's where several do.

For a name the picker cannot tell, the deploy writes and removes nothing, deploys the rest, and names the cause in a line that does not scroll past as a note. It does not fail, so the lifecycle command that ran it goes on, and the validator holds the error until the record is mended. The runner refuses a run of a name it cannot tell.

So the adapter's step that runs before an uninstall removes no agent. Once the capability is unregistered, the deploy that runs after it removes each copy written from that capability's definitions, and writes the definition that now wins for each name another place ships.

### 5. A command that cannot reach either module

A command that cannot find either module in a project's tree, or cannot find in it the function the command calls, refuses that step, as ADR-086 point 5 has a command that cannot reach the tool-access reader do, and names the side to bring up to date by the same comparison of backbone versions. A function of either module keeps its name and its answer.

## Rationale

**One picker, because separate pickers disagree.** The parts that pick each read a different set of capabilities in a different order, so the agent one part runs is not the one another checks. A check of a fixer's tools, or of an agent's storyboard, holds only if it reads the definition the runner runs.

**The records' reader in the lifecycle area.** The registry, the choices and the manifests are the lifecycle's subject. One reader there gives the command and the picker one reading. An unreadable record is answered as unreadable, so each caller chooses its own fail-safe, and none mistakes a broken file for an empty one.

**The YAML library, imported where it reads.** The lifecycle writes the records with a YAML library, which keeps comments and keys it does not know. A parser written for one shape would read a file the library wrote in another as something else, without a word. Importing the library inside the reading function keeps both modules loadable by a standard-library caller.

**The release's modules during a transition.** A transition reads the records before it copies the release in. Loaded from the project's tree, a module the release first ships would be missing exactly when the project moves to it, and the sync that could bring it refuses while the versions differ.

**"Cannot tell" changes nothing, scoped, and does not fail the command.** Read as no agent, a registry with a merge conflict would remove every capability's agent at the next deploy. Scoped to the names an unreadable record decides, one broken manifest touches only its own capability's agents. Changing nothing is already safe, so failing the command would only stop the rest of a sync or an install for a record the validator keeps reporting.

**The deploy removes by the mark's source, and records the text's digest.** A copy written from a definition that no longer wins is a stand-in, which COR-013 point 8 refuses. A kept copy of the agent's own definition runs an older text, and the digest lets a check say so rather than pass on a text that does not run.

**The deploy removes, the uninstall does not.** The deploy knows every place that ships a name. The uninstall knew only its own capability and the project's.

### Alternatives considered

- **Read the folders on disk, not the registry.** Rejected: an incubated capability's folder stays on disk after it is uninstalled, so its agents would keep deploying.
- **Record an override on the capability that made it, or the one it displaced.** Rejected: records on several capabilities can disagree, clearing another's takes a second write that an interruption can split, and a capability without a manifest of its own could hold none.
- **A standard-library parser of the records, with the YAML library where present,** as the permission core reads its YAML, held equal by a conformance test. Rejected: two parsers agree only where the test reaches, and the lifecycle adds keys to the records over time.
- **Keep the uninstall's own removal, and teach it the other places.** Rejected: it would be a second picker.
- **Merge the picker into the tool-access reader.** Rejected: the reader answers what a definition gives, not which definition is the agent.
- **Remove a refused agent's earlier copy whatever the cause.** Rejected: a gap in the project's configuration, the commonest cause, would remove a working agent at each release that adds a category, and the digest already keeps checks honest.

## Implications

- **COR-013,** refined in place in the change that proposes this record, gains point 8. It says that at most one definition of a name is the agent, and every part that deploys, runs, checks or names an agent takes it. The project's place wins, core's yields, and a record that adds a place says where it falls. A definition is its place and its name, in one of COR-015's two layouts, and a winning place that holds both leaves the name with no agent. A refused winner stays the agent, and no other definition stands in. An adapter keeps no copy that is not the agent's; it removes a refused agent's earlier copy for its tool access and may keep it for another cause, and the checks say when the copy that runs is not the current text. A part that cannot tell changes nothing for those names, and each part says why a name has no agent or a refused text. Point 1 says an agent may be its canonical file alone, and the Rationale says why.
- **COR-017,** refined in place in the same change, says in "Collision prevention" that a capability counts while the registry records it, whatever its folder holds; that an absent per-component manifest records no skip; that the project's choice between capabilities is recorded once for each name beside the registry, by an override at install or upgrade or at any other time, and dropped with an uninstalled capability; that the first capability by name wins otherwise, and the reference validator reports each collision no choice settles; and that an uninstall removes no agent another place ships. Its Install paragraph says an override of another capability's agent removes nothing and records the choice, and its Rationale says why each holds.
- **COR-026** says a capability's definition of a core agent's name wins over core's, and points to COR-017 for two capabilities. **COR-059 point 7** says an override of another capability's agent records the component being moved as the project's choice. **ADR-065 points 4 and 6** record it in step 2, beside the registry.
- **This change's build:** the deploy and the runner of the Claude Code adapter, the command's listing and lookup of agents with every command that reads them, the reference graph, the install's and the transition's collision checks, and the status report ask the picker. The command gains a way to record the project's choice for an agent's name outside an install. The adapter's uninstall step stops removing agents.
- **Not yet moved to the lifecycle's reader:** the ownership module's own reading of the registry, and the adapter's shell parsers of it, which the skills' deploy uses. [project-kit#2956](https://github.com/aleskalfas/project-kit/issues/2956) moves the skills' deploy when it decides the skills' rules.
- **The agents area's README** states these rules in "Name-collision precedence", and its claims about the deploy, a skip's earlier copy and the undeploy follow them. "The definition that deploys" reads "the definition that is the agent".
- **The adapters area's README**, in "Primitives the lifecycle calls", says that a deploy primitive removes copies that are not the agent's and leaves names it cannot decide unchanged, and that the uninstall step removes no agents, keeping its role for skills until #2956 decides theirs. The Claude Code adapter's README says the unconfined runner runs only a copy the deploy marked.
- **Skills keep their own pick** until #2956 decides. Their order today puts core before a capability, the reverse of agents', and an override of another capability's skill still replaces it, so bringing them under these rules changes both.
- **An agent that stops deploying,** each removal named by the deploy: one shipped only by a capability folder the registry does not record; core's copy of a name whose capability definition is refused; a name whose winning place holds both layouts; and a copy whose mark records no definition, of a name several places ship, where the deploy refuses the agent.
- **The fixers' check** ([project-kit#2953](https://github.com/aleskalfas/project-kit/issues/2953)) asks the picker which definition the runner would run, then the tool-access reader what it gives, and fails where the deployed copy is not of its current text. The project-management capability's other readers of a deployed copy follow there.
- **ADR-066 point 3 and ADR-073 point 2,** which read "the file the deploy picks", read it from the picker.
- **Sync** copies both modules, and the lifecycle's manifest lists them.
- **Changesets:** the backbone and the `claude-code` adapter each declare a `minor` change, the adapter's with a `requires_backbone` of this release, since its scripts load the modules.
