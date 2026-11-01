---
id: DEC-003
title: A released version never changes, an older format is read and never rewritten unasked, and a piece's state says who moves its lock
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** once a version of a library is released, it stays as it was, and a change is a new version. When the capability's file format changes in a way older files cannot follow, a converter reads the older files people wrote. Nothing rewrites them unless a person asks and reviews the diff. Under the core as it stands, though, validation would fail every such older file, so no such change ships until validation accepts them. A piece's state, draft, delivered, living or adapted, says who may move its lock. A component's status says what its library promises about it.

## Context

Libraries change. An owner fixes a component, adds a pattern or refreshes a brand. The capability changes too: a new tool of the engine, a new optional field, and now and then a shape that older files cannot follow. Pieces must live through both. A talk given again should look as it did. A figure in published documentation should change only when someone has looked. A draft should take an improvement at once.

The founding record decides that each piece names the exact versions of its libraries in its lock, and that a library names its bases by major version. It decides that every library copy is the project's file, and that a copy a lock names is never rewritten. It also decides that the engine and the renderers move with the capability.

The core sets the frame for change:
- **A version transition** moves the capability and runs its migrations, which may make the writes that the record owning the content allows (COR-059 point 3).
- **A rewrite of a project's own content** to follow a format change stays out of the transition, as an operation of its own whose diff a person reviews (COR-059 point 10).
- **A change that breaks against installed state** ships a migration in the same change, and a schema version raised on a change of shape is among such changes (COR-010).
- **The core's data validation** refuses a bound file whose schema version differs from its schema's (COR-023).

The capability's design review asked how a format change reaches files that no migration may rewrite, such as a library copy ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)).

## Decision

**A released version of a library stays as it was released, and a change is a new version. The capability's format grows by additions. A change that older files cannot follow carries over the files commands write, reads the files people wrote through a converter, and rewrites them only on request. None ships until validation accepts a file at an older format number. A piece's state says who moves its lock, and a component's status says what its library promises.**

### 1. Three numbers, each with one job

- **The format number** is one integer, shared by every schema of the capability. Each file of the capability's format carries it as its schema version (the record of files and validation). It rises only on a change that older files cannot follow. An addition, such as a new optional field or a new tool of the engine, leaves it as it is.
- **The release a library needs.** A library names the oldest release of the capability whose tools and fields it uses. The engine computes that release from what the library uses, and checks it against what the library names. An older engine refuses the library, and names the release it needs.
- **A library's own version** follows semantic versioning. A major release carries a breaking change (point 6), a minor one an addition or a change of look, and a patch a fix. For pictures the number is a signal, not a promise: the lock and the before-and-after protect each piece, whatever the number says.

### 2. A change of format carries over what commands write, and reads what people wrote

- **A converter for each change.** A change that raises the format number ships a converter from the number before it. Converters chain, so a file of any older number is read. No converter is ever retired, since a library copy can never be converted.
- **Shapes only.** A converter moves, renames and reshapes keys, and keeps every value as written. A value with no place in the new shape is reported, never dropped in silence.
- **The files commands write are carried over.** The same change ships a migration of the capability that brings each file a command rewrites to the new number. Such files are a piece's own file with its lock, a declaration of code to write with its lock, and each record a command keeps of what was drawn, exported or made while preparing. It acts only on a file whose binding names the capability at an older number, wherever in the repository it lies. It moves keys and keeps every value as written, which this record allows a migration to do (COR-059 point 3). A piece's own file and a declaration also hold what a person set, such as a piece's state, and the migration moves those keys too. It writes no content file, no local component and no library version.
- **A command reads its own file the same way.** A command that finds a file it rewrites at an older number reads it through the converters and writes it at the current number. The migration is that carry-over for every such file at once.
- **The files people write are read in memory.** The engine and the check read an older content file, local component or library version through the converters, and never write it.
- **A rewrite only on request.** A command of the capability rewrites the project's own files that people write, a delivered piece's included, to the new format when a person asks, as a diff that person reviews. It changes no value and moves no lock. It is an operation of its own, never part of a version transition (COR-059 point 10). It never rewrites a library copy, as the founding record states, nor a released version (point 6).
- **No other write into an older file.** Any other command that would write into a content file, a local component or a library version at an older number refuses, and names the rewrite. So a change of words and a change of format never share a diff.
- **Read is not drawn the same.** Today's engine may draw an older piece differently. A delivered piece's exports stay its freeze, as the founding record states.

### 3. A change of the format number waits until validation accepts older files

- **Why it breaks nothing installed.** After such a change, its migration has carried over every file a command writes, as the core asks of a schema version raised on a change of shape (COR-010). Every other file still reads through the converters, and the check judges it the same way. So no command stops working. What stays at the older number is what this record lets no migration rewrite: what people wrote, for the reason its Rationale gives, and library copies, as the founding record states.
- **What breaks under the core as it stands.** The core's data validation refuses any difference between a bound file's schema version and its schema's (COR-023). Every file of the capability's format is bound through it (the record of files and validation). So every older file people wrote would fail the project's validation, a library copy among them, which the project cannot correct.
- **So it waits.** No change that raises the format number ships until validation accepts a bound file at an older number that the capability still reads. The first format number, and every change that only adds, need nothing. Until then the format changes only by additions that every file written before still meets: no field becomes required, and no value accepted before is refused. The ways there are named in the Implications.

### 4. The library folder keeps each version whole, as released

- **A folder for each version.** Each version of a library that a lock may name is a folder of its own in the library folder (the record of files and validation), holding the version whole, as it was released.
- **Committed.** So drawing needs no network, and continuous integration needs no sign-in.
- **One list.** The place keeps one list of the project's libraries: the source of each, the versions present, which of them are released, and a hash of each released one. So the check reads from the files alone whether a version is released, and whether its folder still holds what was released.
- **One library to a name.** A name ties a library to its source in the list. A second library of one name is refused, so a library built on a base finds it by name.
- **Kept while named.** A version stays while a lock names it. One that no lock names may be removed.
- **Pulled whole.** A version from another repository is fetched whole at its release, never merged, with no registry, as the core shares whole content between repositories (COR-041). It is fetched over the channel the project already uses for that repository, with the methodology's shared sign-in ([project-kit#2418](https://github.com/aleskalfas/project-kit/issues/2418)). Unlike that content, it is the project's file. The capability's commands keep it, and sync never touches it.

### 5. A shipped library reaches the project only through a command a person runs

- **One version shipped.** The capability ships the newest version of each library it ships, in its own folder.
- **Brought in by a command.** A command of the capability, run by a person, copies a shipped version into the library folder, the first time a piece needs one included. Running it is the consent for that copy (COR-001).
- **Never by a version transition.** A transition writes the methodology's content, derivable state, seed paths, recorded versions, and what its migrations write as the records owning that content allow (COR-059 point 3). A copy in the project's place is no content of the methodology, no derivable state and no seed path, and this record lets no migration write one.
- **So an upgrade restyles nothing.** A methodology upgrade brings a newer shipped version, which reaches a piece only once a person brings it in and the piece's state lets its lock move (point 8). The copy is then the project's file, as the founding record states of every library copy.

### 6. A released version never changes

- **Released means fixed.** Each released version stays as it was released, whoever owns the library, the project included. A change is a new version. Releasing a version runs the check on it first.
- **A project's own library** changes freely only in a version not yet released, which only a draft may lock (point 8). Releasing it fixes it, and the next change starts a new version.
- **What breaks.** A change breaks when it removes or renames anything that a piece, or a library built on it, names, or changes what that means. A component, its fields, its options and their words, its states, the parts it lets others read, a layout and its slots, and a role are such names. Moving to a new major of a base breaks too, since a piece cannot lock two majors of one library. A change of how something looks does not break, since the lock and the before-and-after protect each piece. What breaks a brand is the record of brands and notations'.

### 7. A component's status says what its library promises

Each library component carries a status that its library's owner marks in the library. No count of uses decides it.
- **Experimental:** it may change in any release, renamed, reshaped or removed.
- **Stable:** it changes in a breaking way only in a major release of its library.
- **Deprecated:** its owner may mark it so in any release. It may be removed only in a major release.
- **The promise is checked.** When a version is released, a command compares each stable component with the previous release, and refuses a breaking change outside a major release. It compares with an earlier version, so it is a command and never part of validation (the record of files and validation).

### 8. A piece's state says who moves its lock

A piece's lock names one version of each library it uses, those they build on included, as the founding record states. A piece's state is its stage of life, which a person sets, and no state an item carries. It says who moves the lock:
- **Draft.** A new piece starts as a draft. Each render moves its lock to the newest versions the project holds that the installed capability reads and that fit together, within the majors the lock names. A new piece's first lock takes the newest such versions of the libraries it names. A new major is taken on purpose, since it may rename what the content names. A draft may lock a version not yet released.
- **Delivered.** The piece was handed out. A person marks it delivered, and names which version of its exports was handed out, as the record of work outside the engine and outputs keeps them. Its lock never moves, and those exports are its freeze, as the founding record states.
- **Living.** The piece stays in use where others rely on it, such as a figure in published documentation. Its lock moves only through a proposed change a person reviews, with a before-and-after of each page it changes. A newer released version in the project is the occasion for such a proposal.
- **Adapted.** A copy of a delivered piece, taken up again for a new audience. Its lock moves only when a person moves it on purpose, after a before-and-after. Once handed out, it is delivered.
- **Released versions only.** A delivered, living or adapted piece locks only released versions.
- **One version of each library.** Where the libraries a piece uses build on two majors of one library, no lock fits them all, and the piece cannot use them together.

### 9. The severities of these checks

Under the policy of the record of files and validation (COR-055 point 4):
- **These fail.** A lock that names a version the project does not hold, a version that needs a newer release or format than the installed capability reads, or libraries that build on two majors of one library. A lock of a delivered, living or adapted piece that names a version not yet released. A library version that no longer matches its released hash. A library of the project's own, not yet released, that names an older release of the capability than it needs. On a delivered piece, a finding at its lock that only a move of the lock would mend never fails (the record of files and validation).
- **These ask for attention.** A piece that uses a deprecated component, which its author is expected to replace. A released library that names an older release of the capability than it needs, which its owner is expected to correct.
- **These state a fact.** A piece that uses an experimental component. A living piece whose lock is behind a newer released version, naming the command that proposes the move.
- **The core keeps its own.** The core's data validation fails any bound file at a format number the capability's schemas do not carry (point 3), wherever it lies.
- **These are commands, not findings:** a release's comparison of its stable components, and the before-and-after of a lock's move.

## Rationale

**Why one format number, and the core's field.** The capability's files refer to each other, and a library names one number for all its files. So one number says which converters apply to a set of files. The core's field is checked by the core's validation. A field of the capability's own would be a second versioning system beside it. The cost is that a change to one kind of file raises the number of every kind, so a rewrite, when asked for, touches every file. The three numbers split the format's major, its minor and a library's content, as Rust splits its edition from the oldest compiler release a package needs.

**Why the files commands write are carried over, and the rest is read.** A command rewrites its own files at every render, so it must find them at the current number, and a migration that only moves keys changes nothing a person wrote. Content is what people wrote, and what checks, rules and translations follow. Carried over in a transition, it would wake all of them at an upgrade taken for another reason. Read through a converter, it changes when a person asks and reviews the diff (COR-059 point 10). A library copy can never be rewritten at all, so the converter is what reads it in any case.

**Why the change waits.** It owes no further migration only while nothing installed stops reading older files. The core's data validation would stop, on files the project cannot mend. Shipped first, the change would fail every project that holds an older library.

**Why a released version never changes, and its mark lies in the files.** A lock names a version so that a piece draws the same until a person moves it. A version changed after its release would move every piece that names it, delivered pieces included, with nobody looking. Validation reads the files as they are (COR-055 point 2), so whether a version is released is written in them, not read from history.

**Why a shipped library arrives by a command.** A version transition's consent is the choice of a release of the methodology. Which look a project's pieces may take is a choice about its own work, which that consent does not cover. So a methodology upgrade taken for another reason restyles nothing.

**Why four states.** Work differs in who must see a change before it shows. A draft's author sees every render. A handed-out piece must look as it was handed out. A published figure must not change unseen, yet should keep up with the current look, and an old release of the documentation should still draw as it was: a reviewed proposal at each library release gives both. A render of a living piece never moves its lock, so a text edit and a library change stay apart. A piece taken up again needs a person's choice. A project that grows its own brand beside its documentation releases a version before a living figure takes it, which is intended.

**Why a draft stays within its majors.** A new major may rename what the content names, so a render that followed it would break the draft's content, not only its look.

**Why the owner marks a status, and the promise is checked at release.** The team that owns a component decides when it is ready, as GOV.UK's and Carbon's design systems do. A count of uses would make a wide library wait for pieces that do not exist yet. An experimental component that could change only in a major release would make every component built ahead of need a promise from its first day. At release the owner can still choose a major one. Afterwards every piece may have taken the change.

### Alternatives considered

- **One version of each library for the whole project.** Rejected. All pieces would move together, and a delivered piece would draw with today's libraries.
- **A migration that carries over content too.** Rejected. It would wake every check, rule and translation that follows content at an upgrade taken for another reason, and it still could not reach a library copy.
- **A format field of the capability's own, outside the core's binding.** Rejected as the default. It is a second versioning system, without the core's validation. It would remove the wait of point 3, so it stays among the ways named below.
- **No format number until the first breaking change.** Rejected. That change would have to guess which files are old.
- **Shipped libraries copied by the version transition.** Rejected. Every draft would take a new look with an upgrade taken for another reason, and a transition writes no such file (COR-059 point 3).
- **Experimental components changed only in a minor release, with a note.** Rejected. Each component built ahead of need would cost its owner from its first day.
- **A draft that follows a new major.** Rejected. A render could break its content.

## Implications

- **The ways to the first change of the format number** (point 3). Nothing is needed before it. Which way is taken is not decided yet:
  1. **A refinement of the core** (recommended). A capability's schema declares the older versions it still reads, and keeps their schemas. The core's data validation then checks a file at such a version against that version's schema, and states the older version as a fact. It refines COR-023's handling of a version that differs, and COR-010's example of a raised schema version, which then reads a change that keeps a reader for every older version as no break. The work on conversions, a project's content following a format change, already lets a project keep files in an older format, and needs the same ([project-kit#1927](https://github.com/aleskalfas/project-kit/issues/1927)). It must accept such a file for as long as the capability reads its number, not for a window, since a library copy can never be converted. The rewrite of point 2 would then be one of its conversions, optional for good.
  2. **A schema for each format number.** Each number ships as a schema of its own name, and the older ones stay. A file names the schema of its number, so the core's exact match holds with no change. It serves if a change is needed before the core has the first way. Its cost: a rewrite changes each file's binding, and the schemas grow with every change.
  3. **The capability binds its own files.** Its check binds each file by its place, and reads every number it has a converter for. The files leave the core's binding. No core change, but the founding record's two levels of checking change, and the core's data validation no longer sees these files.
  4. **No change of the number, ever.** The format grows by additions only, and keeps every shape it ever had.
- **The commands** that fetch, list, release, move and remove versions, and that propose and preview a lock's move, follow these principles. The CLI reference names them, and the capability's README names the fields.
- **A first release of the capability** writes the first format number and needs no converter.
- **The library folder grows** with each version a lock names, its fonts and pictures included. Removing the versions no lock names keeps it in check (point 4).
