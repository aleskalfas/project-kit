---
id: ADR-088
title: A capability declares its write categories in its package file, and install writes each default with a mark
status: proposed
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a capability may name where the agents it ships write ([COR-073](../../../.pkit/decisions/core/COR-073-capability-grant-defaults.md)). This record says how project-kit builds that. A capability lists each such category in its package file, with the agent that owns it and a query command that answers the default paths. Installing the capability readies that query, asks it, writes the answer into the agents overlay, and only then deploys the agents. Where an answer names a folder that already holds files, install asks the person first.

Each line a writer puts in the overlay ends with a comment that repeats the value written. While the line still matches that comment, `pkit agents reconcile --write` may move it to the query's newer answer. Once a person edits the line, it is the project's, and nothing moves it again. The deploy refuses a grant that lies in, or holds, what the next sync overwrites, a copy pulled from an external source included. It checks every category a capability's agent names, whichever definition deploys.

### The choices it makes

Each had two sound answers. The record takes the first, and its Rationale says why. Choices 5 and 6 narrow COR-073, which is edited to say the same (Implications).

1. **The key is the whole name.** `package.yaml` says `visual-communication.work:`, not `work:` with pkit adding the prefix.
2. **What was written stays on the line, as a comment:** `visual-communication.work: ["visual/"]  # pkit-written: ["visual/"]`, not a separate `written:` key.
3. **The query prints a plain list of paths,** `{"paths": ["visual/"]}`, not a versioned envelope such as `{"schema_version": 1, "value": [...]}`.
4. **A "no" to install's question holds back only the folders that hold files.** If `visual/` is empty and `slides/` holds files, install writes the first category and leaves the second undefined, rather than writing neither.
5. **Only `reconcile` moves a value.** *Narrows COR-073.* If the query now answers `["art/"]`, `pkit agents adopt designer` leaves `["visual/"]`, and `reconcile --write` moves it after its dry run showed the move.
6. **A default never lies in the capability's folder, its `project/` folder included.** *Narrows COR-073.* An answer of `.pkit/capabilities/visual-communication/project/work/` is refused, since uninstalling a shipped capability deletes that folder.
7. **A bare key counts as no value.** A line `visual-communication.work:` with nothing after it gets the default from the next writer, as the deploy already skips it as undefined.
8. **Install's dry run runs no query.** It lists the category as "to be written from its query", since the query's script is not in the project yet.

## Context

**What COR-073 decides.**
- **A capability declares the categories its agents write,** under its own name with a dot, each with one owning agent and an optional default. A query of the capability's own answers the default (points 1 and 3).
- **Install and the commands that fill missing overlay categories write the answer.** No write replaces a value the project set. A value still exactly as written follows the default (points 4 and 5).
- **The deploy refuses a grant of a capability's agent that reaches what sync overwrites,** a copy pulled from an external source included (point 2).
- **It leaves five things to an architecture record:**
  - the declaration's layout, and the form of the query's answer
  - how a writer keeps what it wrote
  - how install readies the query, and what a preview shows of a query not ready

**What the code has.**
- **The deploy's check.** The Claude Code adapter's resolver checks an entry only for core's write-carrying categories, in any channel. It asks the lifecycle layer, which holds the test and the category list once (ADR-051 point 3). It does not know whether an agent is a capability's.
- **The test.** The lifecycle layer's test of what sync manages reads an externally-sourced capability's folder as not the methodology's to manage. Only its test of a synced copy counts that folder as one.
- **The overlay's writers.** `pkit agents reconcile --write` and `pkit agents adopt` append blocks of text to the overlay, and never re-serialise it. The resolver reads every top-level key but `overrides` as a category.
- **Install's order.** `pkit capabilities install` copies and registers the capability, then creates its project rule set. Then it runs a tail it shares with `register` and `upgrade`: the rules index, the adapters' deploy, `.pkit/.gitignore`, and last its query commands' provisioning. The questions its points declare come after (COR-061).
- **Query commands.** One shared runner runs them from the project root, with `--json`, the offline marker set and a time bound. An anchor-kind resolver answers through it with `{"paths": [...]}` (the package schema, `friction.kinds`). An unprovisioned environment gives no answer, and the runner's reason names `pkit sync` as the fix.
- **The first consumer** is visual-communication's designer, granted the capability's visual-work location ([visual-communication:DEC-030-design-agents]).

## Decision

**A capability declares its write categories in a block of its package file. Install provisions the default query, writes each answer into the overlay with a mark that repeats it, and only then deploys. The deploy checks every category a capability's agent names with one test, kept in the lifecycle layer.**

### 1. A capability declares its write categories in its package file

A capability's *write categories* are the overlay categories it declares for its agents' writes (COR-073 point 1). It declares them in `package.yaml`. The names below are an example, not the designer's:

```yaml
write_categories:
  visual-communication.work:
    owner: designer
    default-query: work-folder
```

- **The block** is `write_categories`, an optional top-level key. Only a capability holds it, since an adapter ships no agent.
- **Each key is the category's whole name:** the capability's name, a dot, then a word, `[a-z][a-z0-9-]*`. The same string is the placeholder in the owner's `owns` and the key in the overlay.
- **`owner`** is required. It names one agent the capability ships, whose `owns` ([COR-013](../../../.pkit/decisions/core/COR-013-agent-architecture.md) point 2) names the category's placeholder.
- **`default-query`** is optional. It names a leaf of the capability's `commands:` that declares the query contract and no `reads`. A category without it has no default.
- **Package validation fails on** each of these, as errors of its `packages` member:
  - a key that holds no dot, or whose part before the dot is not the capability's name
  - an `owner` the capability does not ship, or whose `owns` does not name the category
  - another agent of the capability that names the category in its `owns`
  - a `default-query` that names no leaf, or one without the query contract, or one with `reads`
- **The package schema** admits the block with its keys closed, as it closes every block. The key is optional, so `schema_version` does not move.
- **Overlay validation warns** of a dotted category that no installed capability declares, at the top level or in an override. It warns where an unknown override is warned of: in `pkit agents` and in the `refs` member of `pkit validate`. The warning fails nothing.

### 2. The default query prints one document of paths

- **How it runs:** as a validator's command runs, through the shared runner. It runs from the project root, with `--json` alone, offline-marked and bounded. It takes no subject (COR-052 point 6).
- **What it prints:** one JSON document, `{"paths": [...]}`. An optional `note`, one line of text, says why, such as why it answers no path. A writer prints the note beside what it writes.
- **Each path** is relative to the repository's root, written with `/`, with no `..` segment and no glob character. A folder may end in `/`.
- **No answer:** an exit other than 0, a timeout, a command that did not start, or a document of another shape. A key the document does not define makes another shape. `{"paths": []}` is an answer, of no path.
- **Asked afresh.** Each writer, and the status report, runs the query each time. Nothing keeps an answer from one run to the next.

### 3. A writer checks the whole answer before it writes

A writer of a default checks each path of an answer, as COR-073 points 3 and 5 require. Each path must pass all of these:

- **Inside the repository,** once links are followed.
- **Clear of the capability's folder,** its `project/` folder included: neither inside it nor holding it. This holds whatever the capability's origin, since a default must hold wherever the capability is shipped.
- **Not refused by point 7's test.**
- **No overlap with a path another agent owns,** read as the exactly-one-owner check reads overlap (ADR-051 point 3). The other agents' grants are read from the overlay as it stands, with the writes made earlier in the same run.

**One path that fails refuses the answer whole.** The writer writes nothing for that category. It names the path and the reason, and for an overlap, the agent that owns the path.

### 4. The line a writer writes ends with a mark that repeats its value

```yaml
# The capability's default for visual-communication.work. Edit the value to make it yours.
visual-communication.work: ["visual/"]  # pkit-written: ["visual/"]
```

- **Where a writer writes.** A writer writes a write category only where neither the top level nor the owner's override gives it a value. A bare key at the top level gives none, as the deploy reads it (ADR-051 point 1), so a writer rewrites that line. A commented stub gives none either; a writer leaves it and adds the line.
- **The line.** The writer writes the category at the top level, on one line, its value in flow form, each path a double-quoted string as JSON writes it. So a folder named `true`, `~` or `a, b` stays a string. A category with no default, and a query that answers no path, get `[]`.
- **The written mark** ends that line: a comment, `# pkit-written:`, then the same value again. A comment line above says that the value is the capability's default, and that an edit makes it the project's. That comment does not open with the category's name, so no reader takes it for a commented stub. Its wording is the build's.
- **Still as written** means that all of these hold:
  - the top-level key's own line holds its value in flow form
  - that line ends with the written mark
  - the value read from the line equals the value read from the mark, both read as YAML, in order
- **Every other state is the project's.** No writer writes or moves such a line. Among such states are a missing or unreadable mark, a changed value, and a value moved into block form.
- **A move** rewrites that one line, its value and its mark, as a text edit. Every other byte of the overlay stays as it was.
- **Uninstall leaves the line** (COR-073 point 5). So neither the line nor its comment holds a path into the capability's folder or a citation of the capability, which uninstall counts as references. Point 3 keeps such a path out of the value.
- **No reader of categories changes.** The deploy, the status report and validation read the line as YAML, where the mark is a comment.

### 5. Install provisions the query, writes the defaults, then deploys

`pkit capabilities install`, `pkit capabilities register`, and install in the methodology's source run these steps, in this order:

1. the gates and the collision flow
2. the copy or the registration in place, with the registry and the capability's manifest
3. the project rule set the capability declares (COR-017)
4. **provisioning** of the scripts the capability's `default-query` leaves name, and no other
5. **the defaults:** each write category, in the block's order, where point 4 lets a writer write
6. the tail install shares with `upgrade`: the rules index, the adapters' deploy, `.pkit/.gitignore`, and last the provisioning of the capability's query commands
7. the questions the capability's points declare (COR-061)

- **Only install and register write a default.** `pkit capabilities upgrade` and `pkit upgrade` are version transitions ([COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md)), and no transition writes one (COR-073 point 4). So step 5 stays out of the tail they share. Their deploy skips an owner whose category is undefined, and names the fill commands (point 6).
- **Consent.** Over a path that is absent or holds nothing, running install is the consent. A path holds content when it is a file, or a folder with any entry, which is `adopt`'s test with files added.
- **Over content, at a terminal,** install asks once for the run. The question lists each `category = paths` with its owner. Install asks only where standard input and standard output are both terminals, ADR-065 point 4's test.
- **On a "no", or off a terminal,** install leaves each category over content undefined, and names the fill commands. It still writes the categories over absent or empty paths. Install takes no `--yes` for this.
- **A query with no answer, or a refused answer,** leaves its category undefined. Install says why, in the runner's reason or point 3's.
- **Install never fails on a default.** The capability is in place by step 5, so install reports each outcome, and the deploy skips the owner loudly.
- **A missing overlay** gets no default from install. Install names `pkit agents reconcile --write`, which creates the overlay from the seed (ADR-065 point 11).
- **Each write prints** the category, its paths, the overlay's path, and that an edit makes the value the project's.
- **The questions come after the defaults,** since COR-061 runs them once install has made every write. A question that moves the capability's location leaves the value written before it behind. That value is still as written, so `pkit agents` shows it, and `reconcile --write` moves it. Install asks no query again.
- **`--plan`** shows the wiring the install would make (COR-053 point 8), and no default.
- **A dry run** asks no query and provisions nothing, since the capability's files are not yet in place. It lists each write category, in one of three states:
  - set by the project, and left as it is
  - to be written from its query once the capability is in place
  - to be written as `[]`, having no default

### 6. The fill commands write defaults, `reconcile` moves them, and `pkit agents` reports them

The *fill commands* are `pkit agents reconcile --write` and `pkit agents adopt`, the commands that fill missing overlay categories.

- **`pkit agents reconcile`,** without `--write`, asks the query of each write category of an installed capability that point 4 lets it write, or that is still as written. It shows:
  - each write, as `category = paths`, with the agents that reach it
  - each move, from the value written to the new answer
  - each refused answer, and each query with no answer, with why
- **`--write`** makes each write and each move the dry run shows. It writes nothing for a query with no answer, or for a refused answer. Over content, `--write` is its consent, as for a documentation folder (COR-049 point 5).
- **`reconcile` provisions nothing.** A query whose environment is not provisioned gives no answer, and its reason names `pkit sync`. So `--write` writes no answer its dry run could not show.
- **A write category comes first** among `reconcile`'s states. It is neither one of core's write-carrying categories nor one with a conventional folder.
- **`pkit agents adopt <agent>`** writes each write category the agent owns that point 4 lets it write: the query's answer, or `[]`. It creates no folder for one. Over content, it takes `adopt`'s consent: one question, or `--yes`, or a refusal off a terminal. It moves nothing.
- **`pkit agents`** asks the query of each line still as written. Where the answer differs, it shows the line, the answer and `pkit agents reconcile`. Where the query gives no answer, it says why. It writes nothing.

### 7. The deploy checks every category a capability's agent names with one test

- **The test.** A grant may not reach content the lifecycle layer's test counts as managed by sync. Nor may it reach a registered externally-sourced capability's folder outside its `project/`, since sync brings that copy back to its pin ([COR-041](../../../.pkit/decisions/core/COR-041-external-source-distribution.md)).
- **Reach** means that either path holds the other, as ADR-051 point 3 reads overlap. So `.pkit/` and `.` reach such content, since each holds some. A glob is read as the folder that holds its first glob character, so `**` reaches the whole repository.
- **The categories it binds,** in any channel of any definition that names them:
  - each category core declares write-carrying
  - each category in the `owns` of an agent a capability ships, whatever the capability's origin, declared or not. A project's definition that wins by name is still bound, as is any other definition that names the category.
- **One home.** The lifecycle layer holds the test and which categories it binds. A resolver passes the category and asks, so no adapter derives either (ADR-051 point 3).
- **The deploy refuses** such an entry, names it with its category, and skips the agent, whoever wrote the entry (COR-073 point 2).
- **Every writer of a default** asks the same test (point 3).

## Rationale

**Why a block in the package file, keyed by the whole name.** The package file is where a capability declares what the backbone reads of it, such as its commands, validators and project rule set. The whole name is the one string a reader searches for, the same in the package file, the agent's `owns` and the overlay. A key of the part after the dot would leave the backbone to add the prefix, and a reader to know that it does.

**Why the owner must name the placeholder in its `owns`.** The declaration and the agent's definition then agree on who writes. A mismatch fails validation, so it never reaches a deploy.

**Why the default query names no `reads`.** The query answers from the location the capability records, which lies in the working tree (COR-073 point 3). At install, settled state may not be readable, and a query that reads it would give no answer.

**Why `{"paths": [...]}`.** The answer is a list of repository paths, which is what an anchor-kind resolver already prints. A data point's envelope carries a schema version because consumers merge and version a slot's value. Nothing merges this answer, and its shape has no schema of its own to version.

**Why the mark is a comment on the line.** COR-073 keeps the written value beside the line, where a reader of the overlay sees it (point 5). A comment adds no key, so no reader of categories changes, the resolver of every adapter included. A reserved key would need each of them to skip it, and could take a name a project already uses.

**Why "still as written" asks for the writer's own form.** COR-073 moves a value only while it stays exactly as written. A line in another form was touched by a person, even where its value reads the same, and treating it as the project's is the safe direction. A value held on one line also lets a move rewrite that line alone.

**Why paths are written as JSON strings.** An unquoted folder named `true` or `~` reads back as another type, and one holding `,` or ` #` breaks the line. A double-quoted string reads back as written, in the value and in the mark alike.

**Why a bare key counts as no value.** The deploy already reads it as undefined and names the fill commands (ADR-051 point 1). Were it the project's, those commands would write nothing there, and the agent would stay skipped with a remedy that does not work. A bare key sets no paths, so no choice of the project's is written over (COR-073 point 5).

**Why one failing path refuses the whole answer.** Writing the rest would grant a value no query answered. The agent would own some of the capability's paths and not others, with nothing in the overlay to say which were dropped.

**Why a default stays out of the capability's `project/` folder.** Uninstall leaves the line, yet deletes a shipped capability's whole folder, `project/` included ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)), so the agent would keep a grant over work that is gone. Uninstall also counts a path into the folder as a reference, and would refuse without `--force`. The reason is core's own rule, so COR-073 states the narrowing itself.

**Why only the default queries are provisioned early.** The query answers offline, under the query contract. Provisioned in the shared tail, after the deploy, its environment would not exist when install asks it. Moving only those scripts leaves the shared tail, and so `upgrade`, as it is. It keeps the wait before the deploy, up to the resolver's bound, to a capability that names a default. An install stopped there leaves the capability registered but not deployed, which `pkit sync` deploys and the fill commands complete.

**Why install leaves a category over content undefined, and writes the rest.** COR-073 point 6 asks before a grant over content, and writes none off a terminal. The run is already the consent for the other categories, so holding them back would skip their owners for nothing. A grant of `[]` over the content instead would be a value nobody chose.

**Why install takes no `--yes`.** COR-073 sends a run off a terminal to the fill commands, which show what they would write. A flag on install would consent to paths nobody was shown.

**Why `reconcile` provisions nothing.** Its dry run is what the person consents to with `--write` (COR-049 point 5). A write that provisioned first could record an answer its dry run could not show.

**Why `adopt` moves nothing.** COR-073 point 5 shows each move in a preview before it is made. `reconcile` is the fill command that only shows what it would write until it is told to write. `adopt` writes on its run, and lists what it would write only where it asks, over content.

**Why install's dry run asks no query.** Before the copy, neither the query's script nor its environment is in the project. Running the bundle's copy would run code the project has not installed.

**Why reach counts a grant that holds managed content.** A grant of `.pkit/` or `.` lets the agent write everything below it, the content sync overwrites included. COR-073 point 2 refuses any grant that reaches that content, and its Rationale warns that a query's answer could name any folder. A test of "inside" alone would let the widest grants through. Core's write-carrying categories take the same test, since one test decides what a grant may not reach (COR-073 point 2). A grant of `.` in one of them hands its agent every core file as surely, so ADR-051 point 2, which refused only an entry inside managed content, widens for them too.

**Why the category is bound wherever it is named.** COR-073 point 2 binds every category in the `owns` of a capability's agent. A project's copy of that agent, winning by name, still writes the category's paths, so checking only the definition that deploys would let the copy write what sync overwrites. Core's write-carrying categories are bound the same way, in any definition.

**Why the lifecycle layer decides which categories the check binds.** ADR-051 point 3 keeps the test in one place, so that a second harness cannot skip it. Which categories the test binds is a rule of the same kind, and a resolver that decided it alone would fork it.

### Alternatives considered

- **A reserved overlay key, such as `written:`, holding each written value.** Rejected: every reader of categories would skip it, in each adapter, and a project's category of that name would clash.
- **Keys of the part after the dot, with the backbone adding the prefix.** Rejected: the declaration would not show the string the overlay and the definition hold.
- **A data point's envelope, `{schema_version, value}`.** Not taken: nothing merges or versions this answer.
- **Writing the paths of an answer that pass, and dropping the rest.** Rejected: the agent would hold a grant no query gave.
- **A default in the capability's `project/` folder, with marked lines left out of uninstall's scan of references.** Rejected: uninstall would then delete the folder the line still grants.
- **A bare key as the project's, with the deploy's remedy telling it apart.** Not taken: it keeps the agent skipped over a line that sets nothing.
- **Install writes no default in a run with any path over content.** Not taken: the run is already the consent for the other categories.
- **`--yes` on install.** Rejected: it would consent to paths nobody was shown.
- **The default written in the tail install shares with `upgrade`.** Rejected: `upgrade` is a transition, and no transition writes a default (COR-073 point 4).
- **A fill command that provisions before it asks.** Rejected: its write could record an answer its dry run could not show.
- **`adopt` moves values still as written.** Not taken: `adopt` has no preview to show a move first.
- **Install's dry run runs the bundle's query.** Not taken: it would run code the project has not installed.
- **Provisioning all the capability's query commands ahead of the deploy.** Not taken: it would lengthen the wait before every capability's deploy, and change the tail `upgrade` shares.
- **The check binds only the definition that deploys.** Rejected: a project's copy of a capability's agent would write what sync overwrites unchecked (COR-073 point 2).
- **Each resolver decides alone whether an agent is a capability's.** Rejected: a second harness would derive the rule again (ADR-051 point 3).

## Implications

- **ADR-051 is refined in place** (refinement per ADR-088):
  - **Its Summary and point 2, widened:** an entry may neither lie in nor hold what sync overwrites, where point 2 refused only an entry inside it. This binds every grant the check binds, core's write-carrying categories included. What sync overwrites counts a registered externally-sourced capability's folder outside its `project/` (COR-073 point 2). The test is ADR-088 point 7's.
  - **Point 3:** the resolver's check binds core's write-carrying categories and every category in the `owns` of an agent a capability ships, in any definition that names it. The lifecycle layer decides which categories the check binds, beside the test. Every writer of a default asks the same test.
  - **Point 7:** a category a capability declares has one owner by its declaration, which validation checks, and its dotted name is never the project's. The single-consumer convention stays for core's categories.
- **ADR-065 point 11 is refined in place** (refinement per ADR-088). The overlay's row also names a capability's install and register, and the install in the methodology's source, writing the defaults the capability declares. Their consent is the run, or over a path that holds content, a person's answer at a terminal. The fill commands stay unlisted for these writes, as point 11 leaves writers outside the lifecycle unlisted. Nothing else in ADR-065 changes: no transition writes a default, and point 14's marker already refuses install, `adopt` and `reconcile --write` inside a migration.
- **COR-073 is edited in place,** in its points 3 and 5 for choices 6 and 5, and in its Implications for those choices and for the third kind of grant that stops deploying (No migration, below). Each edit rests on a rule of core's own: uninstall removes a shipped capability's whole folder ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)), a move is shown in a preview before it is made (COR-073 point 5), and one test decides what a grant may not reach (COR-073 point 2). So each cites no architecture record and takes no refinement pointer, since a core record cites no project's record. Its sentences say this:
  - **Point 3, "What it may answer":** "Each path lies inside the repository once links are followed, and outside the capability's folder. That holds for a folder the project owns inside the methodology's tree too, where it lies in the capability's folder, though point 2 lets a grant reach it. The files the capability ships are a synced copy wherever the capability is shipped, and a default must hold in every project that installs it. Uninstalling a shipped capability removes its whole folder, while the value written for it stays in the overlay ([COR-031](COR-031-capability-origin.md)). A default there would leave the agent a grant over work that is gone."
  - **Point 5, "Nothing is written that cannot hold," its first sentence:** "A writer writes no answer that reaches any of three: what point 2's test refuses, the capability's folder, or a place outside the repository."
  - **Point 5, "A written value follows while it stays as written":** "A value a writer wrote for a declared category is not yet one the project set. While it stays exactly as written, the fill command that only shows what it would write until it is told to write moves it to the default's current answer, with the consent it takes. Its preview shows each such move first. An empty list a writer wrote moves the same way. No other writer moves a value."
  - **Point 5, "Seen, not only moved":** "The agents' status report shows a value still as written whose default now answers otherwise, and names the fill command that moves it."
  - **The Implications bullet on the fill commands:** "The commands that fill missing overlay categories write a default's answer, or the empty list. The one that only shows what it would write until it is told to write also moves a value still as written, and its preview shows each write and move. The command that also creates a conventional folder writes a declared category's answer instead of refusing it, creates no folder for it, and moves no value."
  - **The Implications bullet "No migration":** "No migration. Nothing a project wrote is rewritten. Three kinds of grant stop deploying, each refused loudly at the deploy, naming its entry. One is a capability's agent granted what sync overwrites. Another is a category of core's that carries writes into a copy pulled from an external source. The third is a category of core's that carries writes, granted a folder that holds what sync overwrites, such as the repository's root. Each hands an agent writes the next sync would lose. No migration can narrow the third, since only the project knows which paths it meant. No shipped capability's agent owns a category yet, and none declares one."
- **Code the build changes:**
  - the lifecycle layer's ownership test: point 7's test, with reach both ways and an externally-sourced copy counted, and which categories it binds. The deploy's remedy for an undefined dotted category names the fill commands, told by the dot alone.
  - the Claude Code adapter's resolver, which passes the category alone
  - the package schema and package validation (point 1)
  - the overlay's commands: `reconcile`, `adopt`, the status report, the written mark and the overlay warning. Whether a write category is defined at the top level or in the owner's override is read from the parsed overlay. The overlay's line pattern also matches an indented key.
  - the CLI's install, register and in-source install, with the default queries provisioned ahead of the deploy
- **Documents the build updates:** the agents README's "Write-carrying categories", "`pkit agents reconcile [--write]`" and `adopt`'s section, the lifecycle reference's manifest schema for the block, and the CLI reference for each command above.
- **Versioning (PRJ-002).** The backbone's changes are a surface change, declared in a changeset. A capability that declares the block needs a backbone whose package schema admits it, so its changeset says `requires_backbone: release`.
- **No migration** (COR-073). The package schema gains an optional key. Three kinds of grant stop deploying, each refused at the deploy with its entry named: the two COR-073 names, and a grant of a core write-carrying category that holds what sync overwrites, such as `.`, which point 7's reach adds and COR-073's edited Implications name (above). A migration cannot narrow that third kind, since only the project knows which paths it meant. Such a grant already breaks the file granularity core asks of those categories (the agents README, "Write-carrying categories"), and each ships as `[]`. The backbone's changeset note names the refusal and its fix.
- **Tests** cover at least these:
  - a fresh install that deploys an agent on its capability's default
  - a project that set its own value, kept by install and by `reconcile`
  - a value still as written, moved by `reconcile`, and one a person edited, left alone
  - a bare key, filled; a path named `true`, read back as a string
  - a path over content, asked at a terminal and left undefined off one
  - a capability's agent granted a sync-managed path, `.pkit/`, or an externally-sourced copy, each refused at the deploy, and a project's copy of that agent refused alike
- **Every record this one cites is accepted.**
