---
id: ADR-087
title: One picker in the agents area names which definition is an agent
status: accepted
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the project, a capability and core may each ship an agent of one name, and several parts of pkit each decide which of them is the agent, each in its own way. They disagree on which capabilities count, on the order between two capabilities, and on what an uninstall removes. One module in the agents area decides, and every part that picks asks it. It learns which capabilities are installed, and what the project chose between two of them, from one reader in the lifecycle area.

The rules are core's ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 8, and [COR-017](../../../.pkit/decisions/core/COR-017-capability-pattern.md)'s "Collision prevention" for capabilities). The deploy removes each copy it deployed from a definition that is no longer the agent, so an uninstall's own step removes no agents. Where the records cannot be read, the deploy changes nothing for the names they decide, and says so.

## Context

Which definition of a name is the agent is decided by rules core states: COR-013 point 8 for every place, and COR-017 for capabilities. A capability counts while the component registry records it. A skip the project chose at a collision is recorded in the capability's per-component manifest, which a capability authored in the project, or registered in the methodology's source, does not have ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)). COR-017 records the project's choice between two capabilities once for each agent's name, in the backbone manifest beside the registry.

Several parts pick a definition, and none reads the registry:

- The Claude Code adapter's deploy, in a shell script, takes every capability folder that holds agents, in the order the shell lists them, which follows the locale.
- The agent runner ([ADR-066](ADR-066-unattended-agent-runner.md)) takes every folder, hidden ones included, in code-point order, and its unconfined form starts the harness with the agent's name, so the harness loads whatever copy of that name it finds first.
- The command's listing of agents takes every folder, and its lookup of one agent only folders that hold a package manifest. Several commands read each.
- The reference graph's lookup of a storyboard's consumer reads core before the project.
- The install's collision check names the last capability by name, where the deploy takes the first.

So an unregistered capability whose files stay on disk keeps deploying, two capabilities that ship one agent name deploy whichever the locale lists first, and an override chosen at install against another capability's agent removes and records nothing.

The deploy keeps the copy it deployed before whenever it refuses a definition, but for its tool access ([ADR-086](ADR-086-tool-access-reader.md) point 3). Where a capability's definition of a core agent's name is refused, core's copy stays, and a session runs it while the command reads the capability's.

The adapter's uninstall step removes each deployed copy of a name the capability ships, sparing only a name the project ships, so it removes agents core or another capability ships. The deploy that runs after it then deploys an incubated capability's agents again from the folder left on disk.

The registry and the per-component manifests are read by the command, by the lifecycle area's ownership module ([ADR-051](ADR-051-process-author-edit-authority.md) point 3), and by narrow parsers in the adapter's shell scripts, which find each capability by the list entries that name a kind. The ownership module, propagated neutral code at the lifecycle area's root, keeps only the standard library at module level and imports its YAML library inside the function that reads. The agent runner runs under the system's Python with only the standard library, and starts the adapter's resolver, which has the YAML library, for every confined run. A version transition settles collisions and records the project's choices before it copies the target release's files into the project (ADR-065 point 4).

## Decision

**One reader at the lifecycle area's root reads which capabilities are installed, their skips, and the project's choices between capabilities, for the picker and for the command's reading of skips and choices. One picker at the agents area's root names which definition is the agent of each name. Every part that picks a definition or lists where a name is shipped asks the picker. The deploy removes each copy that is not the agent's, so an uninstall's own step removes no agents, and it changes nothing for the names it cannot decide.**

### 1. The lifecycle's reader of capability records

The reader is `.pkit/lifecycle/capability_records.py`, propagated neutral code beside the ownership module, by the rule [ADR-003](ADR-003-permission-core-code-home.md) states. It keeps the ownership module's discipline: only the standard library at module level, and the YAML library imported inside the function that reads.

It answers, for a tree: each registered capability, its recorded skips of agents' names, and the project's choice for each agent's name. The choices are kept in the backbone manifest under the key `agent_choices`, a mapping from an agent's name to the name of the capability chosen, so a write that unregisters a capability drops its choices in the same file, and the shell parsers, which read only list entries that name a kind, never mistake a choice for a capability.

A per-component manifest that is absent records no skip. A file that cannot be read is answered as unreadable, never as recording nothing, and each caller decides what an unreadable record means for it: a backbone manifest that does not parse leaves the registry and the choices unreadable; one whose `agent_choices` does not read as that mapping leaves only the choices unreadable.

### 2. The picker

The picker is `.pkit/agents/definition_source.py`, propagated neutral code beside the reader of an agent's tool access. Each module's path is part of its interface.

It reads one tree, which its caller names: the tree the definition is read from. For the deploy and the command, that is the project's working tree. For the runner's unconfined form, it is the project's tree the runner lies in. For a confined or a working run, it is the tree ADR-066 point 3 and [ADR-073](ADR-073-builder-runs.md) point 2 read the definition from, never a working run's clone, so no commit on a Task's branch chooses which definition a later run takes.

**Loading.** A caller loads each module from the project's tree, as it loads the tool-access reader (ADR-086 point 1), but for a command that changes which capabilities are installed. An install, a registration, an uninstall and a version transition load both modules from the release the command brings, so a project that predates the modules can still move to the release that ships them. Sync, which its guard runs only at the release the project records, loads them from that release too, so the sync that point 5 names can restore them. The runner has no YAML library. It asks the adapter's resolver for the agent's name, through an entry of the resolver that answers the picked file. The runner then checks that file lies in its tree, as it checks any definition.

**Its answer,** for every name some place ships, in one call:

- **the definition that is the agent,** its file and its place, a definition being its place and its name (COR-013 point 8);
- **whether it is refused before its text is read:** its place holds both layouts;
- **or why the name has none:** only definitions that do not count ship it;
- **every definition of the name,** each with whether it counts and why not;
- **each collision between two capabilities** no choice settles, with the capability that won it, and each choice that decides nothing, with why;
- **or that it cannot tell.** An unreadable registry leaves it unable to tell any name a capability's folder ships; unreadable choices, any name two or more counting capabilities ship; one capability's unreadable manifest, the names that capability's folder ships. A name the project ships is told in each case, since it wins whatever the records say.

It parses no definition: it reads which files exist, and the bytes of a canonical file for its digest. A definition it names as the agent, which the deploy or the runner then refuses, stays the agent (COR-013 point 8).

It also computes the digest a deploy's mark records: SHA-256 of the canonical file's bytes. So the deploy and every check compute it the same way.

### 3. Who asks it, and what each says

Every part that picks a definition, or lists where a name is shipped, asks the picker and keeps no order of its own. A part that stamps a new agent into a named place keeps its own check that the place exists.

The command records the project's choice for an agent's name outside an install. It refuses a choice that would decide nothing: of a capability that is not installed, that does not ship the name, or whose definition of it the project skipped. It takes no choice of the project's place or of core's, which COR-013 point 8 already orders.

The reference validator reports from the picker's answer and the definitions alone, never from deployed copies:

- as warnings, each collision no choice settles and each choice that decides nothing;
- as errors, each name whose winning place holds both layouts, each definition whose front matter gives another name than its file's, and each name the picker cannot tell.

The runner's unconfined form, for a name some place ships, passes the harness the agent's definition as the confined form resolves it, under a name unique to the run, as ADR-066 point 10 states. So the harness loads neither a person's own agent of that name, nor one its settings manage, nor a copy nearer the folder the run starts in, and the run refuses where the confined form refuses that definition. For a name no place ships, it starts the harness by name, which loads an agent the project wrote straight into the harness's own folder (COR-013 point 8).

### 4. What the deploy writes and removes

The deploy's mark on a copy keeps its text and its place in the copy's first lines, which other parts and shipped migrations match. Beside it, the deploy records three things: the definition the copy was written from, the digest of the text it read, and the tool access the tool-access reader read from that text.

The deploy writes the copy of each name's agent, and never writes over a file in the harness's folder that carries no mark. Where such a file takes a name a place ships, the deploy says the harness may run it in the agent's place. It removes, and names, each copy it marked that was written from a definition that is not the agent, or that is of a name with no agent (COR-013 point 8).

Where it refuses the agent's current text for its tool access, it removes the copy written earlier from that definition. For another cause, it keeps that copy only where the tool access its mark records gives nothing the current text's does not, each entry read whole with its argument, so a current entry with an argument never covers an earlier one without it. It then says the copy is not of the current text, and otherwise removes it. Where the refusal is that the winning place holds both layouts, there is no one current text, and it removes the copy. A copy whose mark records no definition is read as written from the agent where only one place ships the name, and as not the agent's where several do. A copy whose mark records no digest is never of the current text, and one whose mark records no tool access is not kept on a refusal.

For a name the picker cannot tell, the deploy writes and removes nothing, deploys the rest, and names the cause in an error line among its results. It exits without a failure, so the lifecycle command that ran it goes on, and the validator holds the error until the record is mended. The runner refuses a run of a name it cannot tell.

So the adapter's step that runs before an uninstall removes no agent. Once the capability is unregistered, the deploy that runs after it removes each copy written from that capability's definitions, and writes the definition that now wins for each name another place ships. A deploy that does not run there leaves those copies until the next sync's deploy removes them.

### 5. A command that cannot reach either module

A command that loads either module from a project's tree, and does not find it there, or finds it without the function the command calls, refuses that step and names the side to bring up to date, by the comparison of backbone versions ADR-086 point 5 uses for the tool-access reader. A function of either module keeps its name and its answer.

## Rationale

**One picker, because separate pickers disagree.** The parts that pick each read a different set of capabilities in a different order, so the agent one part runs is not the one another checks. A check of a fixer's tools holds only if it reads the definition the runner runs.

**The records' reader in the lifecycle area.** The registry, the choices and the manifests are the lifecycle's subject. One reader there gives the picker and the command one reading of skips and choices. An unreadable record is answered as unreadable, so each caller chooses its own fail-safe, and none mistakes a broken file for an empty one.

**The choices in the backbone manifest.** One mapping for each name cannot disagree with itself, and one write records a choice or drops a capability's choices with its registration. The backbone manifest's writer keeps keys it does not know, so a command older than this record leaves the choices in place.

**The YAML library, imported where it reads.** The lifecycle writes the records with a YAML library, which keeps comments and keys it does not know. A parser written for one shape would read a file the library wrote in another as something else, without a word. Importing the library inside the reading function keeps both modules loadable by a standard-library caller.

**The release's modules where a command changes what is installed.** A transition reads the records before it copies the release in. Loaded from the project's tree, a module the release first ships would be missing exactly when the project moves to it, and the sync that could bring it refuses while the versions differ.

**"Cannot tell" changes nothing, scoped, and does not fail the command.** Read as no agent, a registry with a merge conflict would remove every capability's agent at the next deploy. Scoped to the names an unreadable record decides, one broken file touches only the agents it decides. Changing nothing is already safe, so failing the command would only stop the rest of a sync or an install for a record the validator keeps reporting.

**A kept copy only where it gives no tool the current text withholds.** A gap in the project's configuration, the commonest refusal, should not remove a working agent at each release that adds a category. But a copy with a tool its current text took away is the stand-in COR-013 point 7 refuses. The tool access recorded in the mark compares the two without reading the harness's keys, and the digest lets a check say the copy that runs is not the current text.

**The unconfined form passes the definition.** A harness that loads an agent by name searches several places, the person's own and those its settings manage among them, and nothing outside it can say which copy it took. Passing the definition, under a name only the run uses, is what the confined form already does.

**The deploy removes, the uninstall does not.** The deploy knows every place that ships a name. The uninstall knew only its own capability and the project's.

### Alternatives considered

- **Read the folders on disk, not the registry.** Rejected: an incubated capability's folder stays on disk after it is uninstalled, so its agents would keep deploying.
- **Record an override on the capability that made it, or the one it displaced.** Rejected: records on several capabilities can disagree, clearing another's takes a second write that an interruption can split, and a capability without a manifest of its own could hold none.
- **Take the folder as the record of skips,** since a copy leaves a skipped artefact out, and read the manifests' skips only in the validator. Rejected: a skipped file can come back on disk, and COR-017 says a skipped definition does not count, which only the recorded skip shows.
- **A standard-library parser of the records, with the YAML library where present,** as the permission core reads its YAML, held equal by a conformance test. Rejected: two parsers agree only where the test reaches, and the lifecycle adds keys to the records over time.
- **Keep the uninstall's own removal, and teach it the other places.** Rejected: it would be a second picker.
- **Merge the picker into the tool-access reader.** Rejected: the reader answers what a definition gives, not which definition is the agent.
- **Remove a refused agent's earlier copy whatever the cause.** Rejected: a gap in the project's configuration would remove a working agent at each release that adds a category, and the recorded tool access already keeps a copy from running with tools its text withdrew.
- **Have the unconfined form check the copy the harness will load.** Rejected: which copy a harness loads depends on places outside the project and on its settings, so the check could pass on one copy while the harness loads another.

## Implications

- **COR-013,** refined in place in the change that proposes this record, gains point 8. Under it:
  - At most one definition of a name is the agent, and every part that deploys, runs, checks or names an agent takes it. The project's place wins, core's yields, and a record that adds a place says where it falls.
  - A definition is its place and its name, in one of COR-015's two layouts. A folder without its canonical file ships none. An agent's name is its file's name, and a definition whose front matter names another is refused, as is a winning place that holds both layouts.
  - A refused winner stays the agent, and no other definition stands in. An adapter keeps no copy that is not the agent's. It removes a refused agent's earlier copy for its tool access, and keeps it for another cause only where it gives no tool the current text does not. The checks say when the copy that runs is not the current text.
  - A part that cannot tell changes nothing for those names, and each part says why a name has no agent or a refused text.

  Point 1 says an agent may be its canonical file alone, by COR-015. An agent written straight into a harness's own folder is no place's definition, and the deploy names one that takes a shipped name. The Rationale says why point 8 holds.
- **COR-017,** refined in place in the same change, says in "Collision prevention":
  - a capability's definition counts while the registry records the capability, whatever its folder holds, and the project has not skipped that definition, and an absent per-component manifest records no skip;
  - the project's choice between capabilities is recorded once for each name, in the backbone manifest beside the registry, and counts only while it names an installed capability whose definition counts;
  - an override at install or upgrade records the choice, the project may record one at any other time, and an uninstall drops a capability's choices in the same write;
  - the first capability by name, by code points, wins otherwise, and the reference validator reports what no choice settles and each choice that decides nothing;
  - an uninstall removes no agent another place ships.

  Its Install paragraph says an override removes only the project's own artefact, recording the choice against another capability's agent and removing nothing against core's artefact or another capability's skill. Its Rationale says why each holds.
- **COR-026** says a capability's definition of a core agent's name wins over core's, and points to COR-017 for two capabilities, rewriting its implication on collision precedence. **COR-059 point 7** reads an artefact already in the project as the project's own or another component's, and records an override of another capability's agent as the project's choice. **ADR-065 points 4 and 6** record it in step 2 of both transitions, in the backbone manifest. **ADR-066 point 10** has the unconfined form pass the resolved definition, under a name unique to the run, for a name some place ships, and load by name one no place ships. ADR-066 point 3 and ADR-073 point 2 do not change: the file the deploy picks is the picker's.
- **This change's build:** the deploy and the runner of the Claude Code adapter, the command's listing and lookup of agents with every command that reads them, the reference graph, the install's and the transitions' collision checks, and the status report ask the picker. The command gains its way to record a choice. The adapter's uninstall step stops removing agents. The command's reading of skips and choices moves to the lifecycle's reader.
- **Not moved to the lifecycle's reader:** the command's other readings of the registry, the ownership module's, and the adapter's shell parsers of it for settings and skills. [project-kit#2956](https://github.com/aleskalfas/project-kit/issues/2956) takes up the skills' deploy when it decides the skills' rules.
- **The lifecycle area's component registry page** says where the choices are kept and their shape, that an uninstall drops a capability's choices, and that the deploy, not the uninstall step, removes a capability's agents, so a deploy that fails after the registry write leaves them until the next sync's deploy.
- **The agents area's README** states these rules in "Name-collision precedence", and its claims about the deploy, a skip's earlier copy and the undeploy follow them. "The definition that deploys" reads "the definition that is the agent".
- **The adapters area's README**, in "Primitives the lifecycle calls", says that a deploy primitive removes copies that are not the agent's and leaves names it cannot decide unchanged, and that the uninstall step removes no agents, keeping its role for skills until #2956 decides theirs. The Claude Code adapter's README says the unconfined runner passes the resolved definition for a name some place ships, and loads by name one no place ships.
- **Skills keep their own pick** until #2956 decides. Their order today puts core before a capability, the reverse of agents', so bringing them under these rules changes it.
- **An agent that stops deploying,** each removal named by the deploy: one shipped only by a capability folder the registry does not record; core's copy of a name whose capability definition is refused; a refused agent's earlier copy that gives a tool its current text does not, or whose mark records no tool access; a copy whose mark records no definition, of a name several places ship, where the deploy refuses the agent; a definition whose front matter gives another name than its file's; and a name whose winning place holds both layouts.
- **An agent that changes:** where two capabilities ship one name and no choice is recorded, the first by code points may differ from the first the locale listed, so the release's notes say the agent of such a name may change.
- **A review run that stops:** for a name some place ships, the review command's unconfined runs refuse where the confined form refuses the definition: for a gap in the project's configuration, and for any warning the resolver gives, such as a model or effort it drops or a key outside a definition's fields. Such a reviewer does not run until its definition is mended. A reviewer the project wrote straight into the harness's own folder runs as before.
- **The fixers' check** ([project-kit#2953](https://github.com/aleskalfas/project-kit/issues/2953)) asks the picker which definition the runner would run, then the tool-access reader what it gives, and fails where the deployed copy is not of its current text. The project-management capability's other readers of a deployed copy follow there.
- **An unreadable manifest's skips** are lost today when a refresh restamps it, which [project-kit#2958](https://github.com/aleskalfas/project-kit/issues/2958) takes up.
- **Sync** copies both modules, and the lifecycle's manifest lists them.
- **Changesets:** the backbone and the `claude-code` adapter each declare a `minor` change, the adapter's with a `requires_backbone` of this release, since its scripts load the modules.
