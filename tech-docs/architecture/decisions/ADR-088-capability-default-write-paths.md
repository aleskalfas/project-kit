---
id: ADR-088
title: A capability declares its write categories in its package file, and install writes each default with a mark
status: accepted
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a capability may name where the agents it ships write ([COR-073](../../../.pkit/decisions/core/COR-073-capability-grant-defaults.md)), and this record says how project-kit builds that. A capability lists each such category in its package file, with its owning agent and a query that answers the default. Installing it asks the query, writes the answer into the agents overlay with a mark that repeats the value, and only then deploys, asking first where the answer names a folder that already holds files. For example, after `visual-communication.work: ["visual/"]  # pkit-written: ["visual/"]` is written, `pkit agents reconcile --write` may move the value to the query's newer answer while it still matches its mark; once a person edits it, it is the project's. The deploy checks every category a capability's agent names, whichever definition deploys, and refuses a grant that lies in, or holds, what the next sync overwrites, a copy pulled from an external source included.

## Context

COR-073, accepted on 8 November 2026, leaves five questions of its build to an architecture record: the declaration's layout, the form of the query's answer, how a writer keeps what it wrote, how install readies the query, and what a preview shows of a query not ready.

The maintainer decided the record's three choices on 10 November 2026, each as the record recommends:
- **Whether the deploy's test widens to a grant that holds what sync overwrites, for core's write-carrying categories too, with no migration:** "accept widening" ([the comment that records it](https://github.com/aleskalfas/project-kit/issues/2961#issuecomment-6781174085); point 7).
- **Whether only `pkit agents reconcile --write` moves a value still as written:** "yes" ([the comment that records it](https://github.com/aleskalfas/project-kit/issues/2961#issuecomment-6781226048); point 6).
- **Whether a default never lies in the capability's folder, its `project/` folder included:** "yes never inside capability folder" ([the comment that records it](https://github.com/aleskalfas/project-kit/issues/2961#issuecomment-6781305674); point 3).

## Decision

**A capability declares its write categories in its package file, install and the fill commands write each default's answer into the overlay with a mark that repeats it, and the deploy checks every category a capability's agent names with one test.**

### 1. A capability declares its write categories in its package file

A capability's *write categories* are the overlay categories it declares for its agents' writes (COR-073 point 1).

- **The block** is `write_categories`, an optional top-level key of `package.yaml` that only a capability holds.
- **Each key** is the category's whole name: the capability's name, a dot, then a word, `[a-z][a-z0-9-]*`. The same string is the placeholder in the owner's `owns` and the key in the overlay.
- **`owner`** is required. It names one agent the capability ships, whose `owns` ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 2) names the category's placeholder.
- **`default-query`** is optional. It names a leaf of the capability's `commands:` that declares the query contract and no `reads`. A category without it has no default.
- **Package validation fails,** as errors of its `packages` member, on:
  - a key that holds no dot, or whose part before the dot is not the capability's name
  - an `owner` the capability does not ship, or whose `owns` does not name the category
  - another agent of the capability that names the category in its `owns`
  - a `default-query` that names no leaf, or one without the query contract, or one with `reads`
- **The package schema** admits the block with its keys closed, and its `schema_version` does not move.
- **Overlay validation warns,** failing nothing, of a dotted category that no installed capability declares, at the top level or in an override. It warns where an unknown override is warned of.

### 2. The default query prints one document of paths

- **It runs** as a validator's command runs, through the runner the query commands share: from the project root, with `--json` alone, offline-marked and bounded. It takes no subject (COR-052 point 6).
- **It prints** one JSON document, `{"paths": [...]}`. An optional `note`, one line of text, says why, such as why it answers no path, and a writer prints it beside what it writes.
- **Each path** is relative to the repository's root, written with `/`, with no `..` segment and no glob character. A folder may end in `/`.
- **No answer** is an exit other than 0, a timeout, a command that did not start, or a document of another shape. A key the document does not define makes another shape. `{"paths": []}` is an answer, of no path.
- **Asked afresh.** Each writer, and the status report, runs the query each time, and nothing keeps an answer from one run to the next.

### 3. A writer checks the whole answer before it writes

A writer of a default checks each path of an answer (COR-073 points 3 and 5). Each path must pass all of these:

- **Inside the repository,** once links are followed.
- **Clear of the capability's folder,** its `project/` folder included: neither inside it nor holding it, whatever the capability's origin.
- **Not refused by point 7's test.**
- **No overlap with a path another agent owns,** read as the exactly-one-owner check reads overlap (ADR-051 point 3). The other agents' grants are read from the overlay as it stands, with the writes made earlier in the same run.

**One path that fails refuses the answer whole.** The writer writes nothing for that category, and names the path, the reason and, for an overlap, the agent that owns the path.

### 4. The line a writer writes ends with a mark that repeats its value

- **Where a writer writes.** A writer writes a write category only where neither the top level nor the owner's override gives it a value. A bare key at the top level gives none, so a writer rewrites that line. A commented stub gives none either, and a writer leaves it and adds the line.
- **The line** is at the top level, on one line, its value in flow form, each path a double-quoted string as JSON writes it. A category with no default, and a query that answers no path, get `[]`.
- **The written mark** ends that line: a comment, `# pkit-written:`, then the same value again.
- **A comment line above it** says that the value is the capability's default, and that an edit makes it the project's. It does not open with the category's name, so no reader takes it for a commented stub. Its wording is the build's.
- **Still as written** means that all of these hold:
  - the top-level key's own line holds its value in flow form
  - that line ends with the written mark
  - the value read from the line equals the value read from the mark, both read as YAML, in order
- **Every other state is the project's.** No writer writes or moves such a line.
- **A move** rewrites that one line, its value and its mark, as a text edit. Every other byte of the overlay stays as it was.
- **Neither the line nor its comment** holds a path into the capability's folder or a citation of the capability.
- **No reader of categories changes,** the deploy, the status report and validation among them.

### 5. Install provisions the query, writes the defaults, then deploys

`pkit capabilities install`, `pkit capabilities register`, and install in the methodology's source run these steps, in this order:

1. the gates and the collision flow
2. the copy or the registration in place, with the registry and the capability's manifest
3. the project rule set the capability declares (COR-017)
4. **provisioning** of the scripts the capability's `default-query` leaves name, and no other
5. **the defaults:** each write category, in the block's order, where point 4 lets a writer write
6. the tail install shares with `upgrade`: the rules index, the adapters' deploy, `.pkit/.gitignore`, and last the provisioning of the capability's query commands
7. the questions the capability's points declare (COR-061)

- **Of the commands that run the shared tail, only these three write a default,** so step 5 stays out of the tail they share with `pkit capabilities upgrade` and `pkit upgrade`. Those commands' deploy skips an owner whose category is undefined, and names the fill commands (point 6).
- **Over a path that is absent or holds nothing,** running install is the consent. A path holds content when it is a file, or a folder with any entry, which is `adopt`'s test with files added.
- **Over content, at a terminal,** install asks once for the run, listing each `category = paths` with its owner. It asks only where standard input and standard output are both terminals, ADR-065 point 4's test.
- **On a "no", or off a terminal,** install leaves each category over content undefined, and names the fill commands. It still writes the categories over absent or empty paths. Install takes no `--yes` for this.
- **A query with no answer, or a refused answer,** leaves its category undefined. Install says why, in the runner's reason or point 3's.
- **Install never fails on a default.** It reports each outcome, and the deploy skips the owner loudly.
- **A missing overlay** gets no default from install. Install names `pkit agents reconcile --write`.
- **Each write prints** the category, its paths, the overlay's path, and that an edit makes the value the project's.
- **The questions come after the defaults.** A question that moves the capability's location leaves the value written before it, still as written, to point 6. Install asks no query again.
- **`--plan`** shows the wiring the install would make (COR-053 point 8), and no default.
- **A dry run** asks no query and provisions nothing. It lists each write category in one of three states:
  - set by the project, and left as it is
  - to be written from its query once the capability is in place
  - to be written as `[]`, having no default

### 6. The fill commands write defaults, `reconcile` moves them, and `pkit agents` reports them

The *fill commands* are `pkit agents reconcile --write` and `pkit agents adopt`, the commands that fill missing overlay categories.

- **`pkit agents reconcile`,** without `--write`, asks the query of each write category of an installed capability that point 4 lets it write, or that is still as written. It shows:
  - each write, as `category = paths`, with the agents that reach it
  - each move, from the value written to the new answer
  - each refused answer, and each query with no answer, with why
- **`--write`** makes each write and each move the dry run shows, and writes nothing for a query with no answer or a refused answer. Over content, `--write` is its consent, as for a documentation folder (COR-049 point 5).
- **`reconcile` provisions nothing,** so a query whose environment is not provisioned gives it no answer.
- **A write category comes first** among `reconcile`'s states. It is neither one of core's write-carrying categories nor one with a conventional folder.
- **`pkit agents adopt <agent>`** writes each write category the agent owns that point 4 lets it write: the query's answer, or `[]`. It creates no folder for one. Over content, it takes `adopt`'s consent (COR-049 point 5). It moves nothing.
- **`pkit agents`** asks the query of each line still as written, and writes nothing. Where the answer differs, it shows the line, the answer and `pkit agents reconcile`. Where the query gives no answer, it says why.

### 7. The deploy checks every category a capability's agent names with one test

- **The test.** A grant may not reach content the lifecycle layer's test counts as managed by sync, nor a registered externally-sourced capability's folder outside its `project/` ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)).
- **Reach** means that either path holds the other, as ADR-051 point 3 reads overlap. A glob is read as the folder that holds its first glob character.
- **The categories it binds,** in any channel of any definition that names them:
  - each category core declares write-carrying
  - each category in the `owns` of an agent a capability ships, whatever the capability's origin, declared or not. A project's definition that wins by name is still bound, as is any other definition that names the category.
- **One home.** The lifecycle layer holds the test and which categories it binds. A resolver passes the category and asks, so no adapter derives either (ADR-051 point 3).
- **The deploy refuses** such an entry, names it with its category, and skips the agent, whoever wrote the entry (COR-073 point 2).

## Rationale

**Point 1.** The package file is where a capability declares what the backbone reads of it, such as its commands, validators and project rule set. An adapter ships no agent, so it has no category to declare. The whole name is the one string a reader searches for, the same in the package file, the agent's `owns` and the overlay; a key of the part after the dot would leave the backbone to add the prefix, and a reader to know that it does. An owner that names the placeholder makes the declaration and the agent's definition agree on who writes, so a mismatch fails validation and never reaches a deploy. The query answers from the location the capability records, which lies in the working tree (COR-073 point 3). At install, the settled state a `reads` names may not be readable, and a query that reads it would give no answer. The block is optional, so the schema's version need not move.

**Point 2.** The answer is a list of repository paths, which is what an anchor-kind resolver already prints. A data point's envelope carries a schema version because consumers merge and version a slot's value. Nothing merges this answer, and its shape has no schema of its own to version.

**Point 3.** Writing the paths that pass would grant a value no query answered: the agent would own some of the capability's paths and not others, with nothing in the overlay to say which were dropped. Uninstall leaves the line, yet deletes a shipped capability's whole folder, `project/` included ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)), so the agent would keep a grant over work that is gone. Uninstall also counts a path into the folder as a reference, and would refuse without `--force`. A default must hold wherever the capability is shipped, so its origin changes nothing.

**Point 4.**
- **The mark.** COR-073 keeps the written value beside the line, where a reader of the overlay sees it (point 5). A comment adds no key for a reader of categories to skip, the resolver of every adapter included. A reserved key would need each of them to skip it, and could take a name a project already uses.
- **The writer's own form.** COR-073 moves a value only while it stays exactly as written. A line in another form was touched by a person, even where its value reads the same, and treating it as the project's is the safe direction. A value held on one line also lets a move rewrite that line alone.
- **JSON strings.** An unquoted folder named `true` or `~` reads back as another type, and one holding `,` or ` #` breaks the line. A double-quoted string reads back as written, in the value and in the mark alike.
- **A bare key.** The deploy already reads it as undefined and names the fill commands (ADR-051 point 1). Were it the project's, those commands would write nothing there, and the agent would stay skipped with a remedy that does not work. It sets no paths, so no choice of the project's is written over (COR-073 point 5).
- **Nothing of the capability on the line.** Uninstall leaves the line (COR-073 point 5), and counts a path into the capability's folder or a citation of the capability as a reference.

**Point 5.**
- **The default queries provisioned early.** The query answers offline, under the query contract. Provisioned in the shared tail, after the deploy, its environment would not exist when install asks it. Moving only those scripts leaves the shared tail, and so `upgrade`, as it is. It keeps the wait before the deploy, up to the resolver's bound, to a capability that names a default. An install stopped there leaves the capability registered but not deployed, which `pkit sync` deploys and the fill commands complete.
- **The upgrades.** They are version transitions ([COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md)), and no transition writes a default (COR-073 point 4).
- **Content held back, the rest written.** COR-073 point 6 asks before a grant over content, and writes none off a terminal. The run is already the consent for the other categories, so holding them back would skip their owners for nothing. A grant of `[]` over the content instead would be a value nobody chose.
- **No `--yes`.** COR-073 sends a run off a terminal to the fill commands, which show what they would write. A flag on install would consent to paths nobody was shown.
- **No failure.** The capability is in place by step 5. A missing overlay is left to `reconcile --write`, which creates it from the seed (ADR-065 point 11).
- **The questions last.** COR-061 runs them once install has made every write.
- **The dry run.** Before the copy, neither the query's script nor its environment is in the project. Running the bundle's copy would run code the project has not installed.

**Point 6.**
- **No provisioning.** `reconcile`'s dry run is what the person consents to with `--write` (COR-049 point 5). A write that provisioned first could record an answer its dry run could not show.
- **Moves by `reconcile` alone.** COR-073 point 5 shows each move in a preview before it is made. `reconcile` is the fill command that only shows what it would write until it is told to write, while `adopt` writes on its run and lists what it would write only where it asks, over content.

**Point 7.**
- **Reach both ways.** A grant of `.pkit/` or `.` lets the agent write everything below it, the content sync overwrites included. COR-073 point 2 refuses any grant that reaches that content, and its Rationale warns that a query's answer could name any folder. A test of "inside" alone would let the widest grants through.
- **Core's categories too.** One test decides what a grant may not reach (COR-073 point 2), and a grant of `.` in one of core's write-carrying categories hands its agent every core file as surely. So ADR-051 point 2, which refused only an entry inside managed content, widens for them too. No migration can narrow such a grant, since only the project knows which paths it meant. Such a grant already breaks the file granularity core asks of those categories (the agents README, "Write-carrying categories"), and each ships as `[]`.
- **An externally-sourced copy.** Sync brings it back to its pin (COR-041).
- **Every definition.** COR-073 point 2 binds every category in the `owns` of a capability's agent. A project's copy of that agent, winning by name, still writes the category's paths, so checking only the definition that deploys would let the copy write what sync overwrites. Core's write-carrying categories are bound the same way, in any definition.
- **The lifecycle layer.** ADR-051 point 3 keeps the test in one place, so that a second harness cannot skip it. Which categories the test binds is a rule of the same kind, and a resolver that decided it alone would fork it.

### Alternatives considered

- **Keys of the part after the dot, with the backbone adding the prefix.** Rejected: the declaration would not show the string the overlay and the definition hold.
- **A data point's envelope, `{schema_version, value}`.** Not taken: nothing merges or versions this answer.
- **Writing the paths of an answer that pass, and dropping the rest.** Rejected: the agent would hold a grant no query gave.
- **A default in the capability's `project/` folder, with marked lines left out of uninstall's scan of references.** Rejected: uninstall would then delete the folder the line still grants.
- **A reserved overlay key, such as `written:`, holding each written value.** Rejected: every reader of categories would skip it, in each adapter, and a project's category of that name would clash.
- **A bare key as the project's, with the deploy's remedy telling it apart.** Not taken: it keeps the agent skipped over a line that sets nothing.
- **Provisioning all the capability's query commands ahead of the deploy.** Not taken: it would lengthen the wait before every capability's deploy, and change the tail `upgrade` shares.
- **The default written in the tail install shares with `upgrade`.** Rejected: `upgrade` is a transition, and no transition writes a default (COR-073 point 4).
- **Install writes no default in a run with any path over content.** Not taken: the run is already the consent for the other categories.
- **`--yes` on install.** Rejected: it would consent to paths nobody was shown.
- **Install's dry run runs the bundle's query.** Not taken: it would run code the project has not installed.
- **A fill command that provisions before it asks.** Rejected: its write could record an answer its dry run could not show.
- **`adopt` moves values still as written.** Not taken: `adopt` has no preview to show a move first.
- **The check binds only the definition that deploys.** Rejected: a project's copy of a capability's agent would write what sync overwrites unchecked (COR-073 point 2).
- **Each resolver decides alone whether an agent is a capability's.** Rejected: a second harness would derive the rule again (ADR-051 point 3).

## Implications

- **Edits to accepted records,** made in this pull request once this record is accepted. Accepting this record accepts them (COR-066 point 5). COR-073's edits cite no architecture record and take no refinement pointer, since each rests on a rule of core's own (COR-031; COR-073 points 2 and 5) and a core record cites no project's record. ADR-051's and ADR-065's each cite this record as a refinement.
  - **COR-073 point 3, "What it may answer"** (point 3 here) will say: "Each path lies inside the repository once links are followed, and outside the capability's folder. That holds for a folder the project owns inside the methodology's tree too, where it lies in the capability's folder, though point 2 lets a grant reach it. The files the capability ships are a synced copy wherever the capability is shipped, and a default must hold in every project that installs it. Uninstalling a shipped capability removes its whole folder, while the value written for it stays in the overlay ([COR-031](COR-031-capability-origin.md)). A default there would leave the agent a grant over work that is gone."
  - **COR-073 point 5, "Nothing is written that cannot hold," its first sentence** (point 3 here) will say: "A writer writes no answer that reaches any of three: what point 2's test refuses, the capability's folder, or a place outside the repository."
  - **COR-073 point 5, "A written value follows while it stays as written"** (point 6 here) will say: "A value a writer wrote for a declared category is not yet one the project set. While it stays exactly as written, the fill command that only shows what it would write until it is told to write moves it to the default's current answer, with the consent it takes. Its preview shows each such move first. An empty list a writer wrote moves the same way. No other writer moves a value."
  - **COR-073 point 5, "Seen, not only moved"** (point 6 here) will say: "The agents' status report shows a value still as written whose default now answers otherwise, and names the fill command that moves it."
  - **COR-073's Implications bullet on the fill commands** (point 6 here) will say: "The commands that fill missing overlay categories write a default's answer, or the empty list. The one that only shows what it would write until it is told to write also moves a value still as written, and its preview shows each write and move. The command that also creates a conventional folder writes a declared category's answer instead of refusing it, creates no folder for it, and moves no value."
  - **COR-073's Implications bullet "No migration"** (point 7 here) will say: "No migration. Nothing a project wrote is rewritten. Three kinds of grant stop deploying, each refused loudly at the deploy, naming its entry. One is a capability's agent granted what sync overwrites. Another is a category of core's that carries writes into a copy pulled from an external source. The third is a category of core's that carries writes, granted a folder that holds what sync overwrites, such as the repository's root. Each hands an agent writes the next sync would lose. No migration can narrow the third, since only the project knows which paths it meant. No shipped capability's agent owns a category yet, and none declares one."
  - **ADR-051 point 2's first sentence** (point 7 here) will say: "No path in the category may lie inside sync-managed content, or hold any of it — the no-shared-files invariant applied at the agent surface, from COR-044's mechanical layer (refinement per ADR-088). This binds every category the check binds (point 3), core's write-carrying categories included, and the check refuses a path that reaches a registered externally-sourced capability's folder outside its `project/` alike (COR-073 point 2); ADR-088 point 7 holds the test."
  - **ADR-051's Summary** (point 7 here): "**no path in the category may be sync-managed**" will say "**no path in the category may be sync-managed, or hold sync-managed content**".
  - **ADR-051 point 3** (point 7 here) gains, after its sentence on the predicate implemented once in the lifecycle layer: "The check binds core's write-carrying categories and every category in the `owns` of an agent a capability ships, in any definition that names it. The lifecycle layer decides which categories it binds, beside the predicate, and every writer of a capability's default asks the same predicate (refinement per ADR-088)."
  - **ADR-051 point 7** (point 1 here) gains: "A category a capability declares has one owner by its declaration, which validation checks, and its dotted name is never the project's. The single-consumer convention stays for core's categories (refinement per ADR-088)."
  - **ADR-065 point 11's row for `.pkit/agents/project/overlay.yaml`** (point 5 here) will name as its writers "also `pkit agents reconcile --write`, where the overlay is missing (COR-013), and a capability's install and register, and the install in the methodology's source, writing the defaults the capability declares (refinement per ADR-088)", and as its consent "its own `--write`; for a default, the run, or over a path that holds content, a person's answer at a terminal". The fill commands stay unlisted for these writes, as point 11 leaves writers outside the lifecycle unlisted, and no other point of ADR-065 changes.
- **Task [project-kit#2961](https://github.com/aleskalfas/project-kit/issues/2961)** builds points 1 to 7, in this pull request once this record is accepted; its body names the code, documents and tests.
- **Versioning (PRJ-002).** A capability that declares the block needs a backbone whose package schema admits it, and its changeset declares that floor.
- **No migration** (COR-073). The package schema gains an optional key. The backbone's changeset note names the deploy's refusal of the third kind of grant COR-073's edited "No migration" names, and its fix.
