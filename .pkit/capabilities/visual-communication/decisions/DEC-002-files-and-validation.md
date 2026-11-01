---
id: DEC-002
title: A project's visual work lies in its own files, each file names its schema, and one check judges them within validation
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project keeps its libraries and its pieces in one place of its own tree, which it may choose. Each file says at its top which schema checks it. A content file holds only content, keeps a few keys and marks free for what may read it later, and lies apart from the files commands rewrite. The capability's check joins the project's one validation. It fails the project only for what the project can correct in its own files.

## Context

The founding record decides what the capability is for and the model every component follows. Every slice that builds on it reads and writes files: a piece's content in each language, its lock, the versions of its libraries, the records a renderer keeps. Each needs to know where those files lie, how each is checked, and what a finding costs a project.

Four facts shape the answer:
- **A project chooses where its work lies.** One project keeps its visuals beside its documentation, another at the top of its tree. A path fixed in a shipped schema, which is how the core binds a data file by its place (COR-023), cannot follow such a choice.
- **Not every file is the project's to correct.** The founding record makes every library copy the project's file, and never rewrites a copy that a lock names. A fault inside such a copy is its library owner's to fix. Validation fails a project only for what it can correct in its own files (COR-055 point 1).
- **What reads content may grow.** The founding record leaves to a later refinement whether a content file is an artefact, with rules and anchors on its parts. That refinement needs no change of the capability's format only if the format keeps room for it from its first version.
- **The prototype checked everything at once.** Its check printed every problem and failed on any, whether the piece, a library or the machine caused it ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)).

## Decision

**A project's libraries and pieces lie in one place of its own tree, a documentation location the capability declares. Each file of the capability's format names its schema at its top. Content files share one shape, keep free the keys and marks a later reading needs, and lie apart from what commands rewrite. The capability's check is one validator of the project's validation, and every finding of every check follows one severity policy.**

### 1. The capability's files and the project's work lie apart

- **The capability's own files** are its code, its plugins, its schemas and the libraries it ships. They lie in its folder, which the methodology ships, and the project never edits them (COR-001).
- **A project's work lies in one place** of its own tree, the capability's *place*: its libraries and its pieces. None of it lies in the capability's folder, as the founding record requires.
- **The place is a documentation location the capability declares** (COR-049 point 4). Its default lies under the project's internal documentation root, and a project may record another path. It is recorded when a command first writes there, so a later change of a root or of the default moves nothing (COR-049 point 5). Moving the work is an operation a person runs on purpose (COR-049 point 6). The place lies inside the repository, outside the methodology's own folder and outside any hidden folder, where the core's data validation reads.
- **Libraries** lie in one folder of the place, the *library folder*. The record of change over time decides what it holds.
- **Each piece's sources are one folder:** what the piece is, its content in each language, its local components and the pictures its content shows. So they are copied, archived or removed in one step. Where what a piece produces lies, such as an export or a figure a documentation page shows, the record of work outside the engine and outputs decides, with the rules of what shows it ([living-docs:DEC-002-visual-elements] point 5).
- **What a render makes only to be looked at,** such as a preview, lies in the methodology's own folder, under a path the capability declares local to each clone, which the core keeps out of version control. It is never committed.

### 2. The configuration holds only the project's choices as a whole

- **Where it lies:** in the capability's own project configuration, as other capabilities keep theirs. Its schema refuses an unknown key.
- **What it holds:** which plugins that reach a service are turned on (point 8). The place is recorded where the core records a capability's documentation locations (point 1).
- **What it never holds:** a look, a lock or a choice of one piece. Those lie in a library or a piece, so a piece copied to another project reads the same there.

### 3. Each file names its schema

- **At its top.** Every file of the capability's own format, a library's or a piece's, names its schema and its format number in the fields by which the core binds a data file (COR-023). The command that creates a file writes both, and a person who writes one by hand writes them too.
- **No path binds a file.** The capability's schemas declare no path pattern. A pattern fixed in a shipped schema cannot follow a place each project chooses. One wide enough to match any place would also claim files that are not the capability's.
- **A missing binding fails.** The core skips a file that names no schema. The check knows the place and the names of the capability's files (point 5), so it fails a file of the capability's format there whose binding is missing or names another schema, where the project can correct it (point 7). The commands that bring in a library version refuse one whose files lack it.
- **Strict.** A key that neither the file's schema nor the component it fills declares is refused, with the nearest known key named.
- **No editor line.** The core's authoring of a data file stamps a line that points an editor at the schema by its path (COR-023). The capability writes none, since that path breaks when the place moves or a piece is copied. The capability's README says how an editor finds the schemas.
- **Other formats carry no binding.** A brand's design-token files, fonts and pictures keep their own formats. The check reads each of them in that format.
- **What the number means,** and how it changes, is the record of change over time's.

### 4. One shape of content, with room kept for a later reading

The founding record gives every kind of work one shape of content, and no kind a file format of its own. A content file's top holds its top component's fields. Each component the content places is a mapping of that component's fields, and a list in it holds items. Within that shape:
- **The methodology's container** (COR-053 point 10) keeps its key free at a content file's top and in every mapping that places a component, at any depth. No component declares a field of that name, and the capability reads and writes nothing under it.
- **Reserved keys.** Every mapping that places a component, an item included, reserves `id`, `use`, `concept`, `state` and `override`, the key that points one of its parts at another role. A file's top also reserves the fields that bind it (point 3). No component declares a field of these names, so each means the same everywhere. The names are fixed here because people write them in every content file.
- **An id** begins with a letter, and holds only letters, digits, `-` and `_`. So YAML never reads it as a number or a yes-or-no. It is unique in its list and the same in every language. Whatever names an item names its list too, or a list its own component declares. The record of the engine and its plugins decides how references read.
- **Names hold no path marks.** The name of a library, a component, a field, an option word, a layout or a slot holds no `/` or `#`, the marks that join and open a path to a part of a file. No library takes the word by which `use` names the piece itself.
- **`use` is read with its library.** It names a library and a component of it, or the piece itself for a local component. It never names a version: the lock alone says which version is read.

These keep a later refinement free to read a content file, or the components it places, as artefacts that carry the methodology's container, and to name a part by the keys and ids that lead to it. The capability's format then needs no change. What the core must add to read a content file so is the core's.

### 5. Content lies apart from what commands rewrite

- **A content file holds only content.** Nothing a command rewrites at a render, at a release or when a lock moves lies in one. The piece's own file with its lock and its state is such a file. So are each renderer's record of what it last drew, the record of exports, and the list of a project's libraries.
- **Their names tell them apart,** so a path can select a project's content files alone.

### 6. The check is one validator of the project's validation

- **Joined, not separate.** The capability registers its check as a validator (COR-055 point 3). The same check runs by itself as a command.
- **The files as they are.** It answers about the working tree, never about a change (COR-055 point 2). It computes from the project's files alone, with no network and no outside program, as the founding record requires of the engine. So it gives the same answer on every machine.
- **Inside validation's time.** The check finishes within the bound validation sets for a validator (COR-055 point 6). A result it keeps to save time is keyed by everything it was computed from, so the answer is the same with or without it. A check of the drawn scene that cannot finish within the bound is split among several validators, or reads what a render recorded, keyed the same way, as a fact about the files. The record of the engine and its plugins decides which.
- **Two levels.** The core's data validation checks each file against the schema it names (COR-023). The capability's check judges what crosses files: content against the components it fills, references, locks and what the drawn scene shows. Each record decides the checks it owns.

### 7. One severity policy for every finding

Each record of the capability sets the severity of each finding its checks raise (COR-055 point 4), under this policy:
- **What fails.** A finding fails when an invariant a record of the capability owns is broken in a file the project can correct, or when a check owed an answer and gave none (COR-055 points 5 and 6). The project can correct its pieces, its locks, its configuration and any version of its own libraries not yet released. It can also restore a library copy that no longer matches what was released. A fault that only a combination of versions shows sits at the lock that combines them, which the project chose.
- **What never fails.** A finding the project cannot correct in its own files never fails (COR-055 point 1). Examples are a fault inside a released library version, which only its owner corrects in a new release, a fault in content a piece reads from a file the project receives, what the machine lacks, what a service does, and what a renderer reports it could not draw.
- **A reading of taste never fails.** A finding read from a heuristic or a threshold that no record makes an invariant asks for attention.
- **A delivered piece is judged by its files and its lock.** The check never fails it on the scene today's engine computes for it, nor on its exports against today's engine. Its exports are its freeze, as the founding record states. Nor does a finding at its lock fail when only a move of the lock would mend it, since its state forbids that move. A version its lock names that the project no longer holds, or that no longer matches what was released, still fails: restoring the version mends it. A render shows what today's engine draws differently.
- **Attention or a fact.** A finding that never fails asks for attention when someone is expected to act, and names who. It states a fact when no act is expected, such as a piece that uses a component still marked experimental.
- **A comparison with an earlier version is a command,** never a validator, since validation answers about the files as they are (COR-055 point 2). Two examples are the before-and-after of a lock's move, and a release's comparison of a component with its previous version. Such a command may refuse, and validation never runs it.
- **A stale output is a fact about the files as they are.** An output carries a record of what it was made from, such as a picture made while preparing or an export. Whether that record still matches the files is read from the working tree alone, so a validator reports it. The record of work outside the engine and outputs sets its severity.
- **Each finding names its fix:** the file, the field or the item, and the command that mends it where one does.

### 8. Python run with uv, and no network to draw

- **One runtime.** The capability's code is Python, run with uv as the methodology's own code is. It needs the runtime of no other language.
- **Outside programs on the path that needs them.** A program of another tool, such as one that writes a PDF, is called only by the command that needs it. The methodology installs none, so that command checks for it and names what is missing. Validation needs none.
- **No network to draw.** Drawing a piece to a file needs no network. A plugin that reaches a service, such as a renderer for a whiteboard service, declares that service. It runs only where the project has turned it on in the configuration. Its sign-in and the hosts it reaches come through the methodology's shared sign-in, decided apart ([project-kit#2418](https://github.com/aleskalfas/project-kit/issues/2418)).

### 9. The commands sit in one group, and each says whether it writes

- **One group.** Every command of the capability sits in its one command group (COR-021), which its short alias reaches as `pkit visual`.
- **Reads or writes.** A command only reads, or writes the project's files. The CLI reference says which, command by command.
- **Named writers.** A command writes only the files a record of the capability names it the writer of, and running it is the consent for them (COR-001). Where a record asks for a person to review a diff, such as a rewrite to a new format, the command writes only on that request.
- **Never written:** the capability's own folder, and a library copy that a lock names, as the founding record states.

## Rationale

**Why one place, declared as a documentation location.** A project's work is its own, so it lies in its own tree. One place keeps a piece's libraries in reach of every piece, and keeps a project's visual work in one tree to copy, review or exclude. A deck or a poster is no page of the documentation. Yet the core's documentation location already gives a capability's folder all it needs: a default under a root, a value recorded at first use, a line in the status report, and the frame within which a component declares the places the change check reads (COR-049, COR-050 point 1). A setting of the capability's own would repeat it all.

**Why each file names its schema.** Bound by its place, a file would need a pattern that follows every project's place. A pattern cannot, and one that matches everywhere claims other tools' files. The field at the top makes the binding visible to a reader and to the methodology's tools (COR-023). The core skips a file that names no schema, so the capability's check catches one that should.

**Why room for a later reading is kept now.** A content file written today is read for years, and a library copy is never rewritten. Freeing the container's key, and keeping ids and names clear of the marks of a path, costs nothing now. Adding them after files exist would mean a new format and a rewrite of every piece. Holding ids to plain words also keeps YAML from reading `no` or `2` as something other than text.

**Why content lies apart from what commands rewrite.** A draft's lock moves at every render. If it lay in the content, every render would show as a change of content, and every check, rule or translation that follows content would wake for nothing.

**Why one validator, and one policy.** A check a project must remember to run is a check it forgets (COR-055). A finding must mean the same in every record that raises one, so one policy sets what fails. Failing a project for a library it cannot change, for a program its machine lacks, or for a talk it already gave, teaches people to bypass the gate.

**Why a comparison is a command.** A comparison needs a base, and the base differs from run to run. Validation answers about the files as they are, so the same files give the same answer (COR-055 point 2).

**Why Python and no network.** The methodology and the whiteboard tool the capability grew from are Python, and the methodology installs a capability's Python dependencies. Most drawing tools run on Node, which would put a second runtime on every machine. The engine reads no network, so a piece draws the same in continuous integration as on a laptop.

### Alternatives considered

- **A path pattern for each schema, or one for the default place beside the field.** Rejected. A pattern cannot follow a place each project chooses, and two ways to bind one file add a second answer to "which schema is this?".
- **Binding by place, through a refinement of the core that reads a pattern within a capability's location.** Rejected. It needs a core change before the first release, and a piece copied out of the place would lose its binding. The field travels with the file.
- **A setting of the capability's own for the place.** Rejected. It repeats the core's documentation location, and leaves a later reading of content no location to declare its places within.
- **Freeing the container's key once the later reading is decided.** Rejected. Every file written before would need a new format.
- **A piece's lock inside its content.** Rejected. Every render would change the content.
- **A check of its own, outside validation.** Rejected. A gate that calls one command forgets nothing registered (COR-055).
- **Failing on every fault, the libraries' and a delivered piece's included.** Rejected. A project would fail for what only a library's owner can correct, or for what a delivered piece may not change.
- **Node tools for drawing or measuring.** Rejected. A second runtime on every machine.

## Implications

- **The references hold the inventory:** the CLI reference lists the commands and which of them write. The capability's README names the place's default and the configuration's keys. The schemas hold the shapes.
- **The other records** set the severities of their own findings under point 7: change over time for locks and versions, brands and notations for contrast and fonts, the engine for overflow and references between elements, work outside the engine for stale pictures and exports.
- **The core's data validation keeps its own severity** on every file bound through it, a library copy included. A file its schema refuses fails the project, wherever it lies. The commands that bring in a library version refuse one the installed capability cannot read, so such a copy arrives only by hand. What a change of the format number asks of the core, the record of change over time says.
- **A later reading of content** can declare its places within the capability's location, and the library folder as held documents, so that no library copy is read as an artefact the project must keep up to date (COR-050 point 1).
- **The capability's name and its schemas' names are written in every file.** A library copy is never rewritten, so the capability keeps these names for good. A project that uninstalls the capability keeps its files, which then name a schema nothing installed holds. The core's data validation fails them until the capability is installed again or the files leave the project.
