---
id: COR-073
title: A capability names the default paths its agent writes, and installing it writes them into the overlay
status: accepted
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an agent that a capability ships may be given paths to write, through a category of the agents overlay. A capability that knows where its agent works names a default for that category. Installing the capability writes the default into the overlay, so the agent works at once. The commands that fill missing overlay categories write it too, for a project that installed the capability earlier. The default comes from a query of the capability's own, so it follows the location the capability records. No write replaces a value the project set, and no category a capability's agent owns may point at what sync overwrites. A person who runs the install consents to the write, except over a path that already holds content, where the install asks.

## Context

An agent names, in `owns`, the paths whose changes it answers for ([COR-013](COR-013-agent-architecture.md) point 2). Where those paths are the project's, the agent names a category, and the project's overlay gives the category its paths (COR-013 point 5). The deploy derives nothing: it resolves a category only from what the overlay explicitly holds ([COR-049](COR-049-documentation-roots.md) point 3). An agent whose category in `owns` the overlay leaves undefined is skipped, as the agents area's README says under "An undefined category".

Only a few writers give the overlay a category:

- **The first install's seed,** for the categories core's own agents name.
- **The commands that fill missing overlay categories, and those that stamp a document** where its category is unset. A documentation category gets the folder they derive from the project's documentation roots (COR-049 points 3 to 5). A category that only the project can list gets an empty list, so its agent deploys owning nothing.
- **The project itself,** by editing the file.

The deploy also refuses an entry that would hand an agent content the next sync overwrites. It does so only for the few categories core declares as carrying writes, which the agents area's README lists.

A capability can ship an agent whose work lies in a location the capability itself records, in its own configuration. The capability knows the path its agent writes. Yet nothing lets it name that path, so the agent stays skipped until a person copies the path into the overlay by hand. Nor does the deploy's check reach a category a capability's agent owns.

## Decision

**A capability declares, under its own name, each overlay category its agents write, and may name a default that a query of its own answers. Its install and the commands that fill missing overlay categories write that answer, on a person's run, asking first over content already there. Nothing replaces a value the project set, and no category a capability's agent owns reaches what sync overwrites.**

### 1. A capability declares the categories it introduces for its agents' writes

- **A write grant.** A category an agent names in `owns` is its *write grant*: the paths the overlay gives that category are the agent's to write.
- **Declared in its package metadata.** A capability declares there each category it introduces that one of its agents names in `owns`. Its agents may also own a category for which no component declares an owner, such as one the project introduced.
- **Under the capability's name.** A declared category's name is the capability's name, a dot, then a name of its own. A dotted category name is a capability's alone: a component's name holds no dot, as a citation's namespace holds none ([COR-019](COR-019-schema-reference-form.md)). Neither core nor a project names a category with a dot.
- **Owned by one agent.** The declaration names the one agent of the capability that owns the category, since each path has one owning agent (COR-013 point 2). Any agent may name it among its reads.
- **Not core's other rules.** The agents area's README sets further rules for core's own categories that carry writes, such as their file granularity. They bind a declared category only where this record says so.

### 2. No grant of a capability's agent reaches what sync overwrites

- **What a grant may not reach:** content the methodology manages, which sync overwrites. A capability's copy pulled whole from an external source at a pin is among it ([COR-041](COR-041-external-source-distribution.md)). A folder the project owns inside the methodology's tree is not.
- **Which grants.** The check binds every category in the `owns` of a capability's agent, declared or not, whether the capability is shipped or authored in the project. It binds core's categories that carry writes as before. It binds no other category.
- **The deploy refuses** an entry that reaches such content, names it and skips the agent, whoever wrote the entry.
- **One test** decides what a grant may not reach. Every deploy primitive, and every writer of a default, uses it.

### 3. A capability may name a default, which its own query answers

- **What it names.** For a category it declares, a capability may name a default: the paths its agent works in. It names, in its package metadata, a query command of its own that answers them.
- **How the query answers.** It runs within a command filler's limits: bounded, read-only, with no network and no subject, and it fails closed ([COR-052](COR-052-slots.md) point 6). It answers from the location the capability records, or from the location it uses while it records none. It may answer no path, which is an answer, never a failure.
- **What it may answer.** Each path lies inside the repository once links are followed, and outside the files the capability ships. Those files are a synced copy wherever the capability is shipped, and a default must hold in every project that installs it.
- **So it follows the capability.** Each write asks the query afresh, so it writes the location the capability records by then.

### 4. Who writes the default

- **The capability's install,** registration in place of a capability the project authors included ([COR-031](COR-031-capability-origin.md)). Once the capability's files are in place, it asks the query, writes the answer, and only then deploys. So the agent deploys on its grant from the install on.
- **The commands that fill missing overlay categories,** each with the consent it already takes (COR-049 point 5). They serve a project that installed the capability before it named the default, or one that removed the line.
- **A capability pulled from an external source** is served by those commands, until a record places that capability's fetch among the writers.
- **Nothing else.** The deploy derives nothing (COR-049 point 3). No version transition writes the default ([COR-059](COR-059-version-transition.md)), so an upgrade does not either.
- **What is written.** The answer is written at the overlay's top level. Where the query answers no path, or the category has no default, the writer writes the empty list, so the agent deploys owning nothing. Where the query fails, it writes nothing and says so.

### 5. What a write keeps

- **The project's value stands.** A value the project set for the category, at the overlay's top level or for the agent, is never written over. The project points the agent elsewhere with paths of its own. The empty list leaves the agent deployed, owning nothing.
- **A written value follows while it stays as written.** A value a writer wrote for a declared category is not yet one the project set. While it stays exactly as written, a fill command moves it to the default's current answer, with the consent it takes. Its preview shows each such move first. An empty list a writer wrote moves the same way.
- **What was written is kept with the line.** The writer keeps, beside the line in the overlay, the value it wrote. A line whose kept value is missing, or differs from the line's, counts as the project's, so nothing moves it.
- **Seen, not only moved.** The agents' status report shows a value still as written whose default now answers otherwise, and names the fill commands.
- **Once changed, it is the project's.** A value a person changed is the project's from then on, and nothing writes it again. Uninstalling the capability leaves the line in the overlay.
- **Nothing is written that cannot hold.** A writer writes no answer that reaches what point 2's test refuses, the files the capability ships or a place outside the repository. Nor does it write one that overlaps a path another agent owns (COR-013 point 2). So where two capabilities answer overlapping paths, the later write is refused, naming the agent that owns them. The project settles it in its overlay.

### 6. A person's run is the consent, except over content already there

- **Over a path that is absent or empty,** a person who runs the install, or a fill command with its consent, consents to the write. The writer says what it wrote and where to change it.
- **Over a path that already holds content,** the install asks once on a terminal. Off one, it writes nothing and names the fill commands. A fill command asks, or takes its option to write, as it does when it records a documentation folder over documents (COR-049 point 5).
- **An agent's run.** Whether an agent's run consents on a person's behalf is not decided here, as COR-049 point 5 leaves it.

## Rationale

**Why a capability may name its agent's default.** A capability that records where its work lies knows the paths its agent writes. Without a default, the agent is skipped until a person copies that path by hand. With one, the agent deploys at install. Its grant still stands, explicit, in the one file the project owns, where every grant is read.

**Why the default is written, and never resolved at deploy.** A deploy that read the default for an undefined category would give an agent paths no file shows. The grant would change with what is installed, unseen by a reader of the overlay (COR-049 point 3).

**Why a query of the capability's own.** The capability is the one home of its location's rules: the location it uses unrecorded, the location it records, and a folder it refuses. A query answers by those rules when the default is written. A project that recorded another location before the default existed is granted that location. A capability that refuses a folder holding files of another kind answers no path. The agent then deploys owning nothing until the capability has a location.

**Why a written value follows while it stays as written, unlike a documentation location.**
- **The grant is a copy.** The capability's recorded location says where its work lies, and the grant copies it. A documentation location stays put when its root changes, since documents were placed there (COR-049 point 6). A grant that stayed put after the capability's location moved would leave the agent a folder without its work.
- **An untouched value chose only where the capability works.** A value left as a writer wrote it records no path of the project's own choosing. A person who agreed to it over content already there agreed to the capability's location, so the grant follows that location. Each move is asked again: running the fill, which shows the move first, is the person's choice. A value a person changed records a choice of its own, so nothing moves it.
- **Kept with the line, failing safe.** The written value is kept in the overlay, the one file a reader opens, with nothing apart to drift. Where it is lost, the line counts as the project's, the safe direction. A person who types the very value back cannot be told from an untouched line, and a move is shown before it is made.

**Why the check binds every category a capability's agent owns.** The next sync overwrites what an agent writes into the methodology's content, which is never the project's to change. Binding every category in the `owns` of a capability's agent reaches each grant a capability gives, whether or not it declared the category. A grant its install writes is no safer than one a person types, so the deploy checks both. An external copy counts, since sync brings it back to its pinned content (COR-041).

**Why each category is declared under the capability's name, with one owner.**
- **Under the capability's name, with a dot,** so no two components can claim one category, and no project category can meet one. A line a project left behind meets only the capability that declared it. A capability's citations carry its name the same way ([COR-017](COR-017-capability-pattern.md)).
- **With one named owner,** since one path has one owner. Two agents granted the same paths would fail validation's check of owners.

**Why the run is the consent, and content already there still asks.**
- **Installing is the choice.** A person who installs a capability chooses its agents, and the capability's records say where they work. Over an empty or absent path, asking would protect nothing, as COR-049 found for documentation folders.
- **The answer is code.** It comes from the capability, which the project may pull from another repository and does not review line by line. It could name any folder of the project's, its source among them.
- **The grant steers the agent.** Nothing at run time stops an agent at the edge of its `owns`, but the agent works within that remit. Validation also keeps every other agent off those paths. A grant over files the project already holds therefore changes what an agent will edit. COR-049 point 5 asks before a write of that kind, and this record follows it.

**Why no version transition writes it.** A transition brings the components the methodology ships to a version, often with nobody at a terminal to ask about content already there. A capability's project rule set may be created by its migration (COR-017), since a rule set grants no agent any path. A write grant does, so it waits for a command a person runs for it. Meanwhile the deploy's skip names the category and the fill commands.

### Alternatives considered

- **A person writes every grant into the overlay by hand.** Rejected: the agent is skipped until then, though its capability could have named the path.
- **The deploy resolves an undefined category from its capability's default.** Rejected: it gives an agent paths no file shows, which change with what is installed (COR-049 point 3).
- **A conventional folder of the capability's own,** filled as a documentation category's is (COR-049 point 4). Rejected: such a folder lies under a documentation root, and is filled only where it exists or a command creates it. The agent would not deploy at install, and a working folder outside the roots has none.
- **A fixed path in the package metadata.** Rejected: it cannot follow a location the project records.
- **A key of the capability's configuration, with a fixed path as its fallback.** Rejected: it would follow a recorded location without running any code. But the backbone would copy the capability's rules for its location. It would lose those a key cannot hold, such as refusing a folder of another kind.
- **A written default never moves.** Rejected: a location the person records after the install would leave the agent granted a folder without its work. A person would then copy the path by hand, the step this record removes.
- **The capability's own command moves the grant when it records a location.** Rejected: the overlay would gain a writer in each capability's code. The fill commands already show and write every category, one family of writers.
- **What a writer wrote is kept apart from the overlay,** in the capability's folder or the install's manifest. Rejected: it could drift from the line, and an uninstall would drop it while the line stays. A reader of the overlay could not see it.
- **A version transition, or the capability's migration, writes the default for an earlier install.** Rejected: it would grant an agent paths in a run nobody may be watching. The fill commands serve an earlier install once a person runs one.
- **The check binds every category any agent names in `owns`.** Rejected: it reaches past capabilities, to grants that core's agents and a project's own agents hold today. Their records chose those grants without the check, and widening it there is theirs to decide.
- **A capability's agents own only the categories it declares.** Rejected: a capability's agent may rightly own a category the project introduced, such as one listing the project's tests. Binding the check on every category its agents own reaches the same grants.
- **Category names that begin with the capability's name, or are free and checked at install.** Rejected: a name that begins with one component's name may begin with another's too. A free name a project or another component took first would still meet the capability. A line left behind would also hand its paths to whichever component next declares the name.
- **Running the install is the consent over any path.** Rejected: an answer from a capability's code could grant an agent files the project already holds, at a path no person typed.

## Implications

- **COR-013 point 5** gains a sub-section, *A capability's default for a category its agent writes (refinement per COR-073)*. Its sentences say this:
  - A capability declares the categories it introduces for its agents' writes, each under its name with a dot. It may name a default for each, which a query of its own answers. A dotted category name is a capability's alone.
  - The capability's install and the commands that fill missing categories write the default.
  - A written value moves with the default only while it stays as written.
  - A person's run is the consent, except over a path that already holds content.
  - The deploy's check against what sync overwrites binds every category a capability's agent owns, beside core's categories that carry writes. Deploy-time resolution stays unchanged.
- **COR-017** gains two paragraphs (refinement per COR-073):
  - **In "Manifest schema":** a capability's name holds no dot. A capability declares the overlay categories it introduces for its agents' writes. Each is under its name, with its one owning agent and an optional query that answers its default.
  - **In "Lifecycle: install, sync, uninstall", under install:** install writes each default's answer into the agents overlay where the category is undefined, before it deploys. Running install is the consent, except over a path that already holds content, where install asks. COR-073 says what every such write keeps.
- **COR-001's list of the writers of project-owned paths** gains a capability's install and the commands that fill missing overlay categories. Each writes into the agents overlay the default a capability declares (COR-073).
- **COR-052 point 6's list of query commands** gains the query that answers a default, which takes no subject (COR-073).
- **The package-metadata reference** gives the declaration's layout. Validation of a capability's package metadata refuses a category not under its capability's name, or one that names no owner among the capability's agents. Validation of the overlay warns of a dotted category no installed capability declares, such as one an uninstall left.
- **The one test of what a grant may not reach** counts a copy pulled from an external source. The deploy reads, beside core's categories that carry writes, every category a capability's agent owns. The writers of a default ask the same test.
- **The commands that fill missing overlay categories** write a default's answer, or the empty list. They move a value still as written, and their preview shows each write and move. The command that also creates a conventional folder writes a declared category's answer instead of refusing it, and creates no folder for it.
- **The agents' status report** shows a value still as written whose default now answers otherwise.
- **The agents area's README** states these rules beside the rules for core's categories that carry writes.
- **An architecture record realizes this record.** It decides the declaration's layout, the query's answer form, and how a writer keeps the value it wrote with the line. It also decides how install readies the query before it asks it, and what a preview shows of a query not yet ready.
- **No migration.** Nothing a project wrote is rewritten. Two kinds of grant stop deploying, each refused loudly at the deploy, naming its entry. One is a capability's agent granted what sync overwrites. The other is a category of core's that carries writes into a copy pulled from an external source. Each is a grant whose writes the next sync would lose. No shipped capability's agent owns a category yet, and none declares one.
