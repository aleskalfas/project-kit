---
id: DEC-085
title: An issue's waits are the tracker's blocked-by links, or typed lines where the project selects them
status: proposed
date: 2026-11-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an issue *waits* on another when it is not to start until the other closes. Today the capability reads every issue number in an issue's `## Dependencies` section as such a wait. So a line that names the issue's own EPIC, or an issue that waits on this one, holds the issue back for good. This record has each wait recorded in a form a command reads without guessing:

- **The form.** The tracker's own "blocked by" links, by default, or a typed `Blocked by: #N` line in the body, where the project selects it.
- **The reader.** One reader gives every command that reckons what is ready the same waits.
- **The checks.** A wait is checked when it is written: it names an issue that exists, not the issue itself or its ancestor, and closes no loop.
- **The prose.** The rest of the `## Dependencies` section explains, and no command reads it as a wait.
- **The conversion.** A project's existing sections are converted through a proposal that a person reviews.

## Context

Two issues cannot be worked on at once when one needs the other's outcome. The record on parallel work calls this a conflict of sequence, read from each issue's dependencies ([project-management:DEC-025-parallelization-primitive]). The record on linking keeps those dependencies as prose, in an optional `## Dependencies` section of the issue's body ([project-management:DEC-005-linking-and-containment]). DEC-025 names a typed `Blocked by: #N` line as the form a command would read. It leaves the line unbuilt until lived evidence answers its open questions.

Meanwhile the shared pool reckons which Tasks are ready from the prose ([project-management:DEC-059-topology-of-seats] point 7). Every `#N` the section names counts as a wait. So a section that names an issue waiting on this one, the issue's own EPIC, or an issue given for context, holds the issue back. #3548 and #2290 each read as waiting on the other, so neither will ever be ready. A ladder of the project's work, which orders its steps by what each waits on (#1548), needs waits it can read just as surely.

Trackers record this relation themselves too. GitHub records that one issue is blocked by another, shows it on both issues' pages, and answers it through its interfaces, as it does sub-issues. The record on containment settled the like question for a parent: the tracker's sub-issues where it has them, and a textual line where it does not or the project selects it ([project-management:DEC-039-containment-substrate-selection]). The maintainer chose the same shape for waits on 28 November 2026.

## Decision

**A wait is recorded in one of two forms: the tracker's own blocked-by links, which a project uses by default, or a typed `Blocked by: #N` line in the issue's `## Dependencies` section, where the project selects it. One reader gives every command that reckons readiness the waits of both forms. The capability checks each wait it writes. The rest of the section is prose that no command reads as a wait, and a project's existing sections are converted through a proposal a person reviews.**

### 1. A wait, and its two forms

A *wait* is a recorded relation between two issues: the *waiting issue* is not ready to start while the *awaited issue* is open. The wait ends once the awaited issue closes, however it closed. It orders work in sequence, the conflict DEC-025 names.

A parent is no wait. A child may start while its parent is open, and a parent reaches Done only once every child has ([project-management:DEC-006-state-machine-and-cascade]).

A wait takes one of two forms:

- **A link:** the tracker's own record that one issue is blocked by another, such as GitHub's "blocked by".
- **A typed line** in the waiting issue's `## Dependencies` section: `Blocked by: #N`.
  - **Its words.** The line may open with a list marker. After the number it may go on with words that explain the wait, as in `- Blocked by: #42, whose record decides the form`.
  - **One issue a line.** A line records a wait on the issue it names first. An issue its words name after that is explanation, as in the rest of the section.
  - **Not a typed line:** a line inside an HTML comment, a fenced code block or a code span.

### 2. The project selects the form, and links are the default

A project selects the form of its waits by hand, in its substrate map ([project-management:DEC-036-substrate-pluggable-adoption]). The selector is a top-level key beside containment's (DEC-039 point D2): `waits: native | textual`.

- **`native`** is the default, where the key or the whole map is absent. The capability writes each wait as a link.
- **`textual`:** the capability writes each wait as a typed line. A project selects it where its tracker has no such links, or where it keeps its waits in the body by choice.

The capability writes each wait in the selected form alone, never in both. It reports a wait it cannot write in that form, such as a link the tracker refuses. It never drops the wait in silence, nor writes it in the other form instead. Where the tracker has no links, the report names the `textual` selection.

### 3. One reader reads both forms, for every command

Every command that reads waits reads them through one reader. Among them are the commands that reckon the shared pool and each seat's pools ([project-management:DEC-061-pools-of-workers]), and any later one that reckons readiness, such as a ladder of the work (#1548). No command reads a link, or a body, for waits itself.

The reader reads both forms, whichever the project selects. An issue waits on each issue either form names:

- **Both forms found.** The waits are the two forms' union, and a wait recorded in both counts once. The reader reports each wait recorded only in the form the project did not select. The report says how to record it in the selected form, or to remove it.
- **Neither form names a wait.** The issue waits on nothing, so it is ready in sequence.
- **A form that could not be read,** such as links whose read failed or was cut short, makes the answer incomplete, and the reader says so. A command that reckons readiness holds the issue back as not ready. A view of the work shows its readiness as unknown, never as ready.
- **A tracker found to have no links** gives a complete answer from the typed lines.

### 4. A wait is checked when it is written

Every command of the capability that writes a wait writes it through one writer. The writer refuses a wait that:

- **names no issue of the waiting issue's repository,** such as a pull request, a number that is not there, or another repository's issue
- **names the waiting issue itself**
- **names the waiting issue's own ancestor,** each parent read as the parent links give it (DEC-005, DEC-039)
- **closes a loop of waits.** A loop counts each container as waiting on its children, since a container reaches Done only once they have. A wait on an ancestor is the shortest such loop.

The reader checks a wait written outside the capability, such as a link made on the tracker's page or a line typed into a body. It reports each that the writer would refuse:

- **A wait on itself, its ancestor or in a loop** holds its waiting issue back already, since what it awaits is open.
- **A wait that names no issue of the repository** leaves its waiting issue's readiness unknown, so the issue is not ready. That includes a link to another repository's issue.

A person mends what the reader reports.

### 5. The prose of the `## Dependencies` section explains

The section stays optional ([project-management:DEC-010-issue-body-minimum-structure]). Beside any typed lines it holds prose: why the issue waits, what it relates to, what waits on it. No command reads an issue number in that prose as a wait. In a project that selects links, the capability writes no typed line in the section.

### 6. A project's existing sections are converted through a proposal a person reviews

A command reads each open issue's `## Dependencies` section, proposes the waits it means, and writes only those a person accepts. It sorts each issue the section names:

- **A proposed wait:** its line says that the issue waits on the issue named.
- **No wait:** the issue itself, its own ancestor, or an issue its line says waits on this one.
- **Unclear, and flagged:** any other, such as an issue named for context. It becomes a wait only where the person makes it one.

The proposal also flags each proposed wait the writer would refuse, such as one that closes a loop, with why.

The person reviews the proposal and may change it. The command then writes the waits the person accepted, in the selected form, through the writer. It leaves the prose as it stood. It proposes no wait already recorded, so it may run again.

A project's existing sections hold nothing back once the reader stops reading the prose, until the project converts them. So the capability's release that brings the reader changes how a project's state reads. Its migration points each project whose open issues carry such sections to the conversion ([COR-010]).

### 7. DEC-025's open questions 4, 8 and 10

- **Question 4, the typed line's shape,** is answered. A typed line names one issue of its own repository, as `#N` (points 1 and 4). A wait is apart from containment: a child does not wait on its parent, and a wait on an ancestor is refused, since it would never end.
- **Question 8, waits across repositories,** is narrowed. Until a record answers it, the writer refuses a wait on another repository's issue, and a found one leaves its waiting issue's readiness unknown.
- **Question 10, what evidence builds the primitive,** is answered for waits and stays open for lanes. Prose read as waits held Tasks back for good, and a view of the work needs waits it can read. That evidence is enough to build waits. Lanes still wait for the evidence the question asks for.

## Rationale

**Why the tracker's links by default.** They are the tracker's own record of the relation. Its pages show them, its interfaces answer them with nothing to parse, and a person adds one without learning a line's shape. A line in a body is read only by the capability. This is why containment prefers sub-issues (DEC-005, DEC-039).

**Why typed lines where the project selects them.** Not every tracker has the links. A project may also keep its waits in the body, where a diff, an export or a copy of the issue shows them. The typed line serves both, and is the shape DEC-025 named.

**Why one form is written, where containment writes two.** Containment writes the parent's first line in both modes. Where the two records disagree, the native parent wins, since an issue has one parent. Waits are a set. Kept in two places, each removal must be made in both, and no rule can tell a wait removed from one place from a wait missing from the other. So the capability writes one form. The reader reads both only so that no wait written by hand is lost.

**Why the reader takes the union and reports.** A wait missed lets work start too early, which costs a build thrown away or a conflict at the merge. A wait kept too long holds work back, which the report shows and a person ends. So the reader errs toward holding, and says where a wait lies outside the selected form.

**Why an answer that is not whole holds the issue back.** An answer cut short could miss the one open wait. A command that took the issue as ready would start work the project meant to wait. A view would show it ready when it cannot tell (#1548).

**Why the checks run when a wait is written.** A wait on itself, on an ancestor or in a loop never ends, since what it awaits closes only after it. Refused when written, it never holds work back. Found only when read, it already has. The reader still checks waits written elsewhere, since the capability checks no write it did not make.

**Why a loop counts each container's children.** A container reaches Done only once its children have. Say an issue waits on a container, and one of that container's children waits on the issue. Then the issue's wait never ends. The wait on an ancestor is the shortest such case.

**Why the prose no longer counts.** Prose says many things about other issues: what waits on this one, what it belongs to, what it follows from. A reader that counts every number in it reads each as a wait, as #3548 and #2290 show. A typed line or a link says one thing.

**Why a person reviews the conversion.** Only the author of a section knows whether each number in it is a wait, and some sections do not say. A command can propose and flag. A wrong wait written unseen holds work back, and a missed one lets work start too early.

**Why waits stay within the repository for now.** The shared pool is the repository's own (DEC-059). A loop check across repositories would read each other repository's waits, and readiness would read its states. Holding a found wait on another repository's issue as unknown keeps its waiting issue from starting early, until a record decides how to read another repository.

### Alternatives considered

- **Typed lines alone, as DEC-025 named.** Rejected: the tracker's links show on its pages and need no parsing, and a person adds one without learning a shape. A project whose tracker has none selects typed lines.
- **Links alone.** Rejected: not every tracker has them, as not every tracker has sub-issues (DEC-039).
- **Write both forms, as containment does.** Rejected, as "Why one form is written" says.
- **Read only the selected form.** Rejected: a wait written by hand in the other form would be lost, and its issue would start early.
- **Keep reading the prose, and teach the reader to tell a wait from context.** Rejected: no reading of free prose is sure, and a wrong guess holds work back or lets it start early.
- **Convert the sections without a person's review.** Rejected, as "Why a person reviews the conversion" says.
- **Answer question 8 here, and read another repository's waits and states.** Not taken: it needs reads of other repositories, which a record of their own decides.
- **Detect whether the tracker has links, rather than select by hand.** Deferred, as DEC-039 defers detecting sub-issues. A project knows its tracker, and the selection serves both cases now.

## Implications

The edits this record makes to accepted records, once a person accepts it, each with a pointer to it:

- **DEC-025 is refined in place.**
  - **Its summary, its Context and its Decision's lead** then say that what an issue waits on is recorded and read as this record decides, and that lanes alone wait for lived evidence.
  - **Its design table's row on the sequence conflict** then gives the tracker's links, or typed lines where the project selects them, as the substrate, decided by this record.
  - **Its section on the typed line** then says that a wait is a link or a typed line, that one reader reads both, and that the section's prose explains.
  - **"Readiness is reckoned once"** then says that every command reads waits through that one reader.
  - **Its open questions** then give point 7's answers to questions 4 and 10, and question 8 its narrowing. Their lead then says that the record that builds lanes answers the rest.
  - **"Why the mechanisms wait for evidence" and "Why lanes and the typed line wait"** then say that lanes wait, and that waits had their evidence first. Its paragraph on the typed line keeping the prose then says that the prose explains, and that existing sections are converted.
  - **Its alternatives "Build the full primitive now" and "Manual discipline only"** then say that this record builds waits, and that lanes wait.
  - **Its Implications** then say that a record of their own builds lanes, that this record refines DEC-005's table, and that the build of waits is a surface change. Its source scratchpad then retires with the record that builds lanes.
- **DEC-005 is refined in place.** Its table's row for "Blocked by" then gives the tracker's own link, or a typed line where the project selects it. "Follow-up to" and "see also" stay textual, in a body section.
- **DEC-036 point 4** then lists waits beside containment: degradable to typed lines, by the `waits: native | textual` selector.
- **DEC-059 point 7** then defines a ready Task in Backlog as one that waits on no open issue, citing this record.
- **DEC-060's Implications** then say that its rule rests on waits as this record records them, where they say that dependencies stay prose.
- **DEC-066 point 1** then has the later of two Tasks that share a file wait on the earlier, with the prose of its `## Dependencies` section saying that they share a file. Its Implications then say that point 1 rests on waits as this record records them, where they say that dependencies stay prose.

Other implications:

- **The build** is a Task of its own (#3553). It brings the reader and the writer, the selector in the substrate map's schema, the conversion command, the shared pool reading waits through the reader, and the pm skill's filing steps. It converts project-kit's own open issues through a proposal the maintainer reviews. It is a surface change of the capability, versioned under [pkit:PRJ-002], with the migration of point 6.
- **An architecture record** may pin the reader's and the writer's contract, as [pkit:ADR-035] pins containment's. It is the architect's to author.
- **The capability's README** says, where the shared pool reads dependencies, that this record decides how an issue records its waits. Its account of how the pool reads them changes with the build.
- **Other records** that say a Task names another among its dependencies stay true of a wait in either form, and keep their words.
- **The analysis of parallel work** and its glossary define a ready Task by the prose, and change with the build.
- **The scratchpad on parallel work** stays open for lanes, and retires when the record that builds lanes is accepted ([COR-012]).
- **No behaviour changes with this record.**
