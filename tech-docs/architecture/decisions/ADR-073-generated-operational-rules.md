---
id: ADR-073
title: The rules file is generated from the backbone's loaded rule set, and validation keeps the two in step
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit builds [COR-068](../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md), under which the operational rules every session loads are kept as a loaded rule set.
- **The set:** core's rules are the backbone's set `OPS`, in a new propagated area, `.pkit/rule-sets/`.
- **The file a session loads** stays `.pkit/rules/core.md`, so the include, the adapter and `CLAUDE.md` do not change. It holds each accepted rule as `### N. Title (RS-OPS-0NN)` and its statement, and none of the set's data.
- **One function** turns the set into that file. A command of the `rule-sets` group, `pkit rule-sets generate`, writes the file with it. Validation's `rule-sets` member compares the file with its output, and fails a file out of step, only where the set is authored.
- **The `loaded` marker** in the set's front matter makes it a loaded set. Validation refuses a scope, an inheritance, an extension point, a fill or a declared check on one. It also refuses a set marked loaded that a capability keeps. A project may convert its own file into a loaded set. The reach walk routes through no loaded set.
- **Citations** such as "core rule 19" or `backbone:RS-OPS-019` are read by validation's `refs` member. A citation of a missing or retired rule is a warning.

## Context

COR-068 decides that operational rules are kept in loaded rule sets, and that the file a session loads is generated from its set where the set is authored. Its Implications leave to an architecture record where the generation and its check live. The maintainer decided three things for #2260 on 28 October:
- core's set is named `OPS`, and lives in `.pkit/rule-sets/`, the folder the location rule names for the backbone's method rule sets (the schemas README, "Rule-set files")
- that folder becomes a propagated core area, as an exception to the hold of [ADR-065](ADR-065-upgrade-runs-the-transition.md) point 13
- no guard stops the sync that brings `OPS` into a project whose own set has that name

Four records set the shape this one fits:
- **The engines ship in the binary,** one home for each computation, and a component's script reads their answers through reading commands ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) points 1 and 2).
- **Rule-set files are found by where they are** and checked by a schema the tree ships ([ADR-056](ADR-056-backbone-file-schemas-home.md) points 1 and 2).
- **Each validator is a member of `pkit validate`,** and `error` is the one severity that fails ([ADR-058](ADR-058-validator-registry.md) point 2).
- **A command does one operation** ([COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md)).

COR-068 leaves open:
- which command generates the loaded file, and what form the file takes
- where the check that the file matches its set runs, and how it tells where the set is authored from where it arrives by sync
- what the schema's marker refuses, and how the reach walk treats a loaded set
- where citations of operational rules are read, in which forms, and in which files
- what carries the new area to a project

## Decision

**Core's operational rules are the backbone's loaded set `OPS`, in the propagated area `rule-sets`. One function projects the set into `.pkit/rules/core.md`. `pkit rule-sets generate` writes the file with it, and validation's `rule-sets` member fails a file that differs from it, where the set is authored. The set's `loaded` marker refuses every part of a rule set that says where rules bind. Validation's `refs` member warns of a citation of a rule that is missing or retired.**

### 1. Core's set is `OPS`, in the propagated area `rule-sets`

- **The file:** one rule-set file in `.pkit/rule-sets/`, beside the area's `README.md`, cited `backbone:RS-OPS-0NN` (COR-068 point 6). Its rules keep the numbers they held, so core rule 19 is `RS-OPS-019`.
- **The area** holds the backbone's method rule sets, loaded or not, and nothing of a project's. It has no `project/` folder, since a project keeps its rule sets under its internal documentation root (COR-051 point 6). So seeding creates nothing in it.
- **It passes the hold** on new core areas, which keeps every other new area and adapter until #1600 (ADR-065 point 13).
- **The rules area keeps the loaded file.** The rules area's reference says where the set and its file live.
- **Its origins** cite a core record or give the decider's words, never an architecture or project record. The set is validated in every project that receives it, and an `ADR-` or `PRJ-` origin would resolve there against that project's own records, or to none.

### 2. One function projects a loaded set into its loaded file

- **The home:** one function, in a module beside the rule-set reader, takes a loaded set as read and gives its loaded file's text. The generator writes that text, and the check compares the file with it. No other code builds a loaded file, so the two never disagree on what the file should hold.
- **Where the file goes:** by the set's owner, not by a key in the set. The backbone's loaded set has its loaded file at `.pkit/rules/core.md`, the path the harness's include reads. One constant holds that path. A path in the data would let a set write any file, or two sets write one.
- **What it reads:** the set's body and its rules' statuses, through the one reading of a document's parts (ADR-057 point 2). It reads nothing else.

### 3. The loaded file holds each accepted rule as `### N. Title (RS-OPS-0NN)`, under the set's sections

- **The rules:** each accepted rule, in the set's order, under the heading `### N. Title (RS-OPS-0NN)`, such as `### 19. A session changes only its own repository (RS-OPS-019)`. N is the rule's number without its leading zeros, the title is the one its section heading gives, and the id closes the heading, so the heading names the rule's id and title (COR-068 point 3). The statement follows, as the set writes it, with its pointer to the record it rests on (COR-065 point 7).
- **What else carries over:** the set's prose before its first section, its italic preface, and its group headings with the prose under them, at the levels the set writes them.
- **What it leaves out:** the front matter, so every origin and status, and the section of each rule that is proposed, superseded or withdrawn.
- **No H1,** since the host file owns it (core rule 13). A loaded set's body holds none either (point 6).
- **Nothing added.** The function writes no text the set does not hold. The set's preface says where the set lives and which command writes the loaded file, in words true in both files, such as "The loaded file is generated from `.pkit/rule-sets/ops.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync edits neither (core rule 1)." A reader of either then knows where the rules are edited, and that a project which receives them edits neither.

### 4. `pkit rule-sets generate` writes the loaded file where the set is authored

- **What it does:** it writes the loaded file of each loaded set the repository authors, from point 2's function, and says for each whether the file changed. It writes no other file, and validates, syncs or merges nothing.
- **When it refuses,** before it writes anything:
  - where the set arrives by sync, by the test of point 5. A project neither generates nor edits a loaded file it receives (COR-068 point 3). The message says that the next sync brings the file.
  - where the set cannot be read, or its rules and sections do not join. The message names `pkit validate`.
- **Its group:** `rule-sets`, beside the reading commands `reach` and `altered`. The group shares its name with validation's member, one name for one functionality (ADR-057 point 2).
- **No `--dry-run`.** It writes only generated files, each the projection of a set authored beside it, and validation already fails a hand edit of one, so a preview would show nothing a person decides.
- **Its one operation** writes files of the repository from content authored there, and acts on no installed project's state. The `pkit new` commands are its precedent.

### 5. Validation fails a loaded file out of step, where the set is authored

- **The check:** a part of validation's `rule-sets` member. For each loaded set, it compares the loaded file with point 2's output, byte for byte once line endings are read as `\n`, so a checkout that converts them still passes. A file that differs, or is missing, is an `error`, since COR-068 point 3 makes it fail validation. The finding names the file, the set and `pkit rule-sets generate`.
- **Where the set is authored:** where the set's file is no synced copy. The check asks the tree's own predicate for a synced copy, in the lifecycle area's ownership module. That predicate decides by the component's origin and by whether the repository is the methodology's source, never by the path, and `pkit new` refusals and documentation places ask the same one.
- **Where the set arrives by sync** the check does not run. The project receives the set and its loaded file together, and edits neither.
- **A tree without the ownership module** cannot tell, so the check skips the set and reports that it did, as a tree without a schema skips its kind (ADR-056 point 1).

### 6. The `loaded` marker, and what validation refuses on a loaded set

- **The marker:** `loaded: true` at the top of a set's front matter. Without it, a set is an ordinary one.
- **The schema refuses, on a set marked loaded,** what the file alone shows:
  - `scope`, `inherits` and `checks`
  - `offers` or `fills` on any rule
- **The `rule-sets` member refuses** what needs other files:
  - a set whose `inherits` names a loaded set
  - a second loaded set in one component's folder (COR-068 point 1)
  - a set marked loaded in a capability's folder (COR-068 point 4)
  - an H1 in a loaded set's body
- **A project's own loaded set** (COR-068 point 7) is validated as any loaded set is, and gets a loaded file the same way: point 2's function, with the loaded file at `.pkit/rules/project.md`, the path the project's include reads. Converting the plain file is the project's own step: write the set under its internal documentation root, give each rule its origin, and run the generator. The rules area's reference says how.
- **What stays as for every set:** the schema's other keys, the join, ids, origins and successors (COR-068 point 1).
- **The shape carries no version.** The key is optional, so no file that passes today fails, and no migration is due (ADR-056 point 3).

### 7. The reach walk routes through no loaded set

- **The walk** (ADR-057 point 2) takes no loaded set as the start of a route or as a parent. So no loaded rule binds on an artefact in its answer, even for a set marked loaded that validation refuses for a scope (COR-068 point 2).
- **The reading commands:** `pkit rule-sets reach` and `pkit rule-sets altered` give the walk's answer, so neither names a loaded rule as binding. The rule-set reviewer, which reads them, judges no artefact against a loaded rule (COR-057).
- **A loaded rule stays an artefact** (COR-068 point 1). `altered` lists one a change alters, as it lists any artefact.

### 8. Validation's `refs` member warns of a citation of a missing or retired operational rule

- **Where it runs:** in the `refs` member, whose subject is citations, through one reader in the module that reads citations from prose. It reads the text files of the working tree's one listing (ADR-057 point 2), but the project's tests, and in Markdown it skips fenced code, as the other prose readers do. A test may cite a missing rule on purpose.
- **The forms it reads,** with any case of the first letter:
  - `core rule N`, `core.md rule N`, `rules/core.md #N` and `rules/core.md N`, a list after the plural, as in "core rules 3, 5 and 13", and a range, as in "core rules 14-15"
  - `backbone:RS-OPS-0NN` and `RS-OPS-0NN`
  - `project rule N`, only where the project's rules are a loaded set (COR-068 point 7). project-kit's own are not yet, so here the form is read and judged nowhere.
- **What it never reads:** a bare `rule N`, which may name a rule of any list.
- **The finding:** a `warning`, since it is read from prose (COR-055). It names a citation of a rule the set lacks, or of a superseded or withdrawn one, and a superseded rule's successor. A citation of a loaded set's rule is judged here alone, so the check of rule ids in agents' and skills' bodies leaves a loaded set's rules to it, and no citation is reported twice.
- **Which files:** where the set is authored, every file, so every citation. Where the set arrives by sync, the project's own files, so its own citations of the set's rules (COR-068 point 6). Either way it leaves out:
  - synced copies, by point 5's predicate
  - superseded records
  - answer files, by the answer reader's test (ADR-057 point 2)
  - what the project leaves out of anchoring (COR-050 point 7), such as generated files and working drafts. project-kit leaves out its scratchpad notes and its changelog there. A changeset is history once released, and the project leaves its folder out the same way.

### 9. Sync, install and the migration check carry the area

- **Propagation:** `rule-sets` is among the areas first install and the propagation step copy (ADR-065 point 1), and the copy carries its files as it carries any area's.
- **The bundle** carries the area: the packaging's list of trees it ships names `rule-sets` beside the other areas, and the test of the packaging's boundary holds it there.
- **The migration check** classifies a path under `.pkit/rule-sets/` as the backbone's tier, as it does `.pkit/rules/core.md`. A rename or a removal there is then caught as a change that needs a backbone migration (COR-010).
- **Ownership** needs no change: a path under `.pkit/` outside a project tier is sync-managed already, so the set is a synced copy in every project but the methodology's source.

## Rationale

**Why one function for the generator and the check.** Two pieces of code that each built the file could come to disagree, and then the check would fail a file the generator had just written. With one function, a file the generator writes always passes, and a file that passes is the one the generator would write (ADR-057, "one home per computation").

**Why `### N. Title (RS-OPS-0NN)`.** COR-068 point 3 asks for a heading that names the rule's id and title. People and agents cite these rules as "core rule N", and COR-068 point 6 keeps that citation valid, so a heading that opens with N lets a reader of the loaded file find "core rule 19" at a glance. The id closes the heading, so the rule's permanent name is there too, at the cost of a few characters on each of some twenty headings.

**Why the file's path is fixed by the set's owner.** The harness's include reads one path, and one loaded set to a component fills it (COR-068 point 1). A path in the data would add a choice nobody needs, and two ways to get it wrong.

**Why a command of its own.** Validation never writes, so it cannot regenerate. Sync in the methodology's source copies nothing (ADR-059 point 2), and in a project it must not generate (COR-068 point 3). Generating inside it would add a second operation to sync. The release step runs after the change that accepts a rule, but the file must change in that same change (COR-068 point 3). A git hook binds only where someone installed it. A command does the one thing, and validation's check makes forgetting it fail.

**Why the check keys on the synced-copy predicate.** That predicate already answers "is this file authored here?" for the stamps and the documentation places, by origin and repository and never by path. A test of its own, say on the path or on the repository's name, would answer the same question a second way and could drift.

**Why `refs` reads the citations.** Its subject is citations, and it already resolves rule ids in agents' and skills' bodies. Putting the reader in the `rule-sets` member would split one subject across two members. A warning, not an error, because prose can use these words for something else, and a gate that fails on a reading of prose fails for the wrong reasons (COR-055, "Why exactly one fails").

**Why those files are left out.** A synced copy is checked where it is authored. Superseded records, answer files, changesets and the changelog record what was true when they were written, and COR-068 point 6 keeps them as written. Scratchpad notes are working drafts that retire (COR-012).

**Why a project converts its own file by its own step.** A project's rules are its own, and only the project knows who decided each rule and why, so only it can give each rule its origin (COR-051 point 5). A command or a migration that converted the file would have to invent those origins, or leave them out. So the project writes the set and the origins, and the same function, generator and check then serve its set as they serve core's, with its loaded file at the path its include reads. Until it converts, its rules stay a plain file, as COR-068 point 7 allows.

**Why no migration.** The area and the command are added, and the schema gains an optional key. The loaded file keeps its path, and only its content changes, as any refresh of a synced file does. No path in a tree the methodology ships is renamed or removed, and no command changes its signature, so none of COR-010's triggers applies.

### Alternatives considered

- **`### RS-OPS-0NN — Title` headings,** as the set's own sections are. Not taken: N, the number people cite, would be buried in the code.
- **`### N. Title` with no id.** Rejected: COR-068 point 3 asks the heading to name the rule's id.
- **The loaded file's path in the set's data.** Rejected: one owner, one path, and nothing to choose.
- **Regenerating inside `pkit validate`, or under a `--fix` flag.** Rejected: validation never writes (COR-055).
- **Generating in sync's self-host branch, or in the release step.** Rejected: one is a second operation inside sync, and the other comes after the change that must carry the file.
- **A pre-commit hook.** Rejected: it binds only where installed, and the check binds anyway.
- **A test of its own for where the set is authored.** Rejected: the synced-copy predicate answers the question already.
- **The citation reader in the `rule-sets` member.** Not taken: citations are the `refs` member's subject.
- **Citations of operational rules as errors.** Rejected by COR-068 point 6.
- **Reading a bare `rule N`.** Rejected: it may name any numbered list, a record's points among them.
- **A guard against a project's own set named `OPS`.** Not taken, as the maintainer decided (Implications).

## Implications

- **The build of #2260** realises this record. It writes `OPS` with each rule's origin, generates `.pkit/rules/core.md` from it, adds the area, the marker, the command, both checks and the classification. It updates the hold's test so its held areas include `rule-sets`, and its message and its account of itself name the exception (ADR-065 point 13).
- **ADR-065 point 13** names `rule-sets` as the one area that passes its hold.
- **References to update in the same change:**
  - the rules area's README: where the set and its loaded file live, that the file is generated, and how a project converts its own file into a loaded set
  - the schemas README, "Rule-set files": the `loaded` key and what it refuses
  - the CLI reference: `rule-sets generate`, the two checks, and the forms of citation
- **The friction checks run from a project's first install.** The set's folder is a place that holds rule sets, so every project has a place from the start. Each rule of `OPS` is anchored to a core record, or gives the reason it has none, so a project's measures count none of them. Under the default mode the checks report and fail nothing.
- **A project's own set named `OPS`** meets the finding that two sets share a name, after the sync that brings the backbone's. No guard stops that sync. The project renames its own set and its rule ids.
- **Changeset:** one backbone `minor`, for a new area, command, key and checks. No migration, as the Rationale says.
- **Stands on these records, all accepted:** COR-004, COR-010, COR-012, COR-051, COR-055, COR-057, COR-065 and COR-068, and ADR-056, ADR-057, ADR-058, ADR-059 and ADR-065.
