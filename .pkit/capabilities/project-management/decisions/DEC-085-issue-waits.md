---
id: DEC-085
title: An issue's waits are the tracker's blocked-by links, or typed lines where the project selects them
status: proposed
date: 2026-11-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an issue *waits* on another when it is not to start until the other's work has landed. Today the capability reads every issue number in an issue's `## Dependencies` section as such a wait. So a line that names the issue's own EPIC, or an issue that waits on this one, holds the issue back for good. This record has each wait recorded in a form a command reads without guessing:

- **The form.** The tracker's own "blocked by" links, by default, or a typed `Blocked by: #N` line in the body, where the project selects it.
- **The reader.** One reader gives every command that reckons what is ready the same waits. A Task waits on what its Feature, Umbrella or EPIC waits on too, which holds back its start but not its merge.
- **The checks.** A wait is checked when it is written: it names an issue that exists, not the issue itself or its ancestor, and closes no loop.
- **The prose.** The rest of the `## Dependencies` section explains, and no command reads it as a wait.
- **A wait left out.** Each Task states its waits, or that it waits for nothing. Text that hints at a wait with none is flagged. Starting a Task and merging its change are refused while a wait is open, and a change that rests on unfinished work waits on it.
- **The key.** The checks that refuse or hold a Task apply once the project turns them on with a key, and a new project starts with them on, as COR-066 point 4 turns its refusal on: the install asks, and offers them on only over a tracker with no open issue. A project that upgrades, or whose install leaves them off, keeps working as before until it turns them on: what is ready is read from each Task's `## Dependencies` section as it was, and nothing this record adds holds or refuses a Task. Waits are written and reported meanwhile.
- **The conversion.** A project's existing sections are converted through a proposal that a person reviews.

## Context

Two issues cannot be worked on at once when one needs the other's outcome. The record on parallel work calls this a conflict of sequence, read from each issue's dependencies ([project-management:DEC-025-parallelization-primitive]). The record on linking keeps those dependencies as prose, in an optional `## Dependencies` section of the issue's body ([project-management:DEC-005-linking-and-containment]). DEC-025 names a typed `Blocked by: #N` line as the form a command would read. It leaves the line unbuilt until lived evidence answers its open questions.

Meanwhile the shared pool reckons which Tasks are ready from the prose ([project-management:DEC-059-topology-of-seats] point 7). Every `#N` the section names counts as a wait. So a section that names an issue waiting on this one, the issue's own EPIC, or an issue given for context, holds the issue back. #3548 and #2290 each read as waiting on the other, so neither will ever be ready. A ladder of the project's work, which orders its steps by what each waits on (#1548), needs waits it can read just as surely.

Trackers record this relation themselves too. GitHub records that one issue is blocked by another, shows it on both issues' pages, and answers it through its interfaces, as it does sub-issues. The record on containment settled the like question for a parent: the tracker's sub-issues where it has them, and a textual line where it does not or the project selects it ([project-management:DEC-039-containment-substrate-selection]). The maintainer chose the same shape for waits on 28 November 2026.

A wait that is written can be checked, but a wait left out leaves no trace. A Task whose wait was never recorded reads the same as a Task that waits on nothing, so the pool offers it, and its change can land before the work it rests on. The acceptance gate asks that work built on a proposed record reach the default branch no earlier than the change that proposes it ([COR-066] point 1). Nothing checks that order while only whoever built the change knows it. On the same day, the maintainer decided how a wait left out is made visible, how a project turns on the checks that do so, and that a wait recorded on a Feature, an Umbrella or an EPIC holds back the start of the Tasks under it, and holds no Task already started.

## Decision

**A wait is recorded in one of two forms: the tracker's own blocked-by links, which a project uses by default, or a typed `Blocked by: #N` line in the issue's `## Dependencies` section, where the project selects it. One reader gives every command that reckons readiness the waits of both forms, and a Task's waits are its own and its ancestors', though an ancestor's holds back only its start. The capability checks each wait it writes. The rest of the section is prose that no command reads as a wait. Each Task states its waits, or that it waits for nothing, and text that hints at a wait with none is flagged. Starting a Task and merging its change are refused while a wait is open, and a change that rests on unfinished work waits on it. The checks that refuse or hold a Task apply once the project turns them on with a key, which the install asks to write, offering them on only over a tracker with no open issue; until then, readiness is read from the prose as before. A project's existing sections are converted through a proposal a person reviews.**

### 1. A wait, and its two forms

A *wait* is a recorded relation between two issues: the *waiting issue* is not to start until the *awaited issue*'s work has landed. Until then the wait is *open*. An open wait holds work back once the project turns the checks on, and holds nothing until then (point 11). It orders work in sequence, the conflict DEC-025 names. Where another record speaks of an issue's dependencies, as where a Task names another among them, it means the issue's waits once the project turns the checks on, and the issues its `## Dependencies` section names until then (point 11).

- **It ends,** for each Task whose wait it is, once the awaited issue's work has landed on the default branch, or on the integration branch that the Task's own change merges into, where the Task's body names one ([project-management:DEC-013-branch-and-pr-conventions]).
  - **An issue's work lands** on the branch its change merges into once the issue closes as completed: its change merged, or its work done with no change to merge ([project-management:DEC-006-state-machine-and-cascade], its closure triggers).
  - **An issue whose body names an integration branch** closes on its merge into that branch. Its work lands on the default branch only once the issue that owns the branch closes as completed, the branch merged into the default branch. So a wait on it ends at its own close for a Task whose change merges into the same branch, and at the owning issue's close for any other.
  - **A change that closes both issues** lands the awaited issue's work with its own (point 8).
- **An awaited issue closed otherwise,** such as not planned, leaves its work unlanded, so the wait stays open. The reader reports it (point 3), and a person points the wait at the issue that carries the work, or removes it.

A parent is no wait. A child may start while its parent is open, and a parent reaches Done only once every child has ([project-management:DEC-006-state-machine-and-cascade]).

**A wait on a container is its Tasks' wait too, before they start.** Where a Feature, an Umbrella or an EPIC waits on an issue, every Task under it, at any depth, waits on that issue too, a Task filed under it later among them. So a Task's waits are its own and its ancestors', and the reader gives them all (point 3). An ancestor's wait holds back a Task that has not started: it counts in readiness and at the start (points 3 and 8). It holds no merge, and so holds nothing of a Task already started, one in In Progress or in Review (point 8).

- **The started Tasks are listed.** While a container's wait is open, the capability lists the Tasks under it that have started. The writer lists them to whoever writes the wait, and the reader lists them in its reports, which covers a wait written outside the capability.
- **A started Task whose work rests on the awaited issue** waits on it through a wait of its own, which holds its merge (points 8 and 9). Whoever finds that its work rests there records that wait.

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

The capability writes each wait in the selected form alone, never in both. It reports a wait it cannot write in that form, such as a link the tracker refuses. It never drops the wait in silence, nor writes it in the other form instead. Where the reader establishes that the tracker has no links (point 3), the report names the `textual` selection.

### 3. One reader reads both forms, for every command

Every command that reads waits reads them through one reader. Among them are the commands that reckon the shared pool and each seat's pools ([project-management:DEC-061-pools-of-workers]), and any later one that reckons readiness, such as a ladder of the work (#1548). No command reads a link, or a body, for waits itself. Once the project turns the checks on (point 11), a command that reckons readiness reckons it from what the reader gives, as this point says. Until then it reckons readiness from each Task's `## Dependencies` section, and the reader's answer holds nothing back.

The reader reads both forms, whichever the project selects. An issue waits on each issue either form names:

- **Both forms found.** The waits are the two forms' union, and a wait recorded in both counts once. The reader reports each wait recorded only in the form the project did not select. The report says how to record it in the selected form, or to remove it.
- **Neither form names a wait.** A Task whose body declares that it waits for nothing (point 6) is ready in sequence. Without that declaration, the Task's answer is *undeclared*: the reader reports it, a command that reckons readiness holds it back as not ready, and a view of the work shows its readiness as unknown. Any other kind of issue waits on nothing.
- **A form that could not be read,** such as links whose read failed or was cut short, makes the answer incomplete, and the reader says so. A command that reckons readiness holds the issue back as not ready. A view of the work shows its readiness as unknown, never as ready.
- **A tracker that has no links** gives a complete answer from the typed lines. That absence is one the reader establishes, as [pkit:ADR-035] establishes a tracker without sub-issues, never one inferred from a failure's status or text. A read it cannot attribute to the absence leaves the answer incomplete.
- **Where the reader cannot establish the absence,** a project that selects typed lines may declare that its tracker has no links. The reader still reads links there. A read that answers counts, even with no link, and the reader reports the declaration as false. Only a read it cannot attribute falls back to the declaration, and gives a complete answer from the typed lines.

The waits the reader gives a Task are its own and its ancestors' (point 1), each ancestor's read as above, and it tells the Task's own from its ancestors'. An ancestor whose waits it cannot read in full, or a parent it cannot tell, makes the answer on the ancestors' waits incomplete, and leaves the answer on the Task's own as it is.

### 4. A wait is checked when it is written

Every command of the capability that writes a wait writes it through one writer. The writer refuses a wait that:

- **names no issue of the waiting issue's repository,** such as a pull request, a number that is not there, or another repository's issue
- **names the waiting issue itself**
- **names the waiting issue's own ancestor,** each parent read as the parent links give it (DEC-005, DEC-039)
- **closes a loop of waits.** A loop counts open waits only. It counts each container as waiting on its children, since a container reaches Done only once they have, and each Task as waiting on what its ancestors wait on (point 1), whether or not the Task has started. A wait on an ancestor is the shortest such loop, and a container's wait on an issue under it is another.

The reader checks a wait written outside the capability, such as a link made on the tracker's page or a line typed into a body. It reports each that the writer would refuse. Once the project turns the checks on (point 11), each also holds its waiting issue back:

- **A wait on itself, its ancestor or in a loop** holds back for good each Task on it that has not started, since what such a Task awaits is open until after it.
- **A wait that names no issue of the repository** leaves its waiting issue's readiness unknown, so the issue is not ready. That includes a link to another repository's issue.

A person mends what the reader reports.

### 5. The prose of the `## Dependencies` section explains

The section stays optional ([project-management:DEC-010-issue-body-minimum-structure]). A Task that declares that it waits for nothing does so there (point 6). Beside any typed lines the section holds prose: why the issue waits, what it relates to, what waits on it. No command reads an issue number in that prose as a wait. Until the project turns the checks on, readiness is reckoned from the section instead, as before this record (point 11). The capability reads the prose otherwise only for hints of a wait, which it flags and never counts (point 7). In a project that selects links, the capability writes no typed line in the section.

### 6. A Task declares its waits, or that it waits for nothing

A Task *declares* its waits: it records at least one wait, in either form, or its `## Dependencies` section holds the line `Blocked by: nothing`. The capability never takes a Task that records no wait as waiting for nothing.

- **The declaration's line** takes a typed line's shape (point 1), with the word `nothing` in place of the number. It names no wait, whatever issue its words go on to name.
- **It is written in the body, whatever form the project selects.** The tracker's links say what an issue waits on, never that it waits on nothing.
- **Filing a Task asks for its waits or its declaration.** Once the project turns the checks on (point 11), it is refused where it is given neither, and so is an edit that would leave the Task with neither. Both refusals are hard rejects, as for a body that lacks a section its type requires ([project-management:DEC-014-validation-severity-model]).
- **A wait and the declaration do not stand together.** The writer removes the declaration when it writes the Task's first wait. Where the reader finds both, the waits count, and it reports the declaration.
- **An ancestor's wait** is the Task's wait all the same (point 1). It neither stands in for the Task's declaration nor stands against it: the Task still declares its own waits, or that it has none.
- **A Task found declaring neither,** such as one filed on the tracker's own page, is undeclared (point 3): the reader reports it, and once the project turns the checks on, it is not ready.

### 7. A hint of a wait with no wait is flagged

A *hint of a wait* is text in a Task's body that names an open issue as something the Task comes after, as in "after #N lands", "once #N" or "needs #N", or that names a record that is not accepted. Wherever the capability validates a Task's body (DEC-014), it flags each hint where no wait of the Task names the issue. For a record, that is the issue whose change proposes it.

- **The flag is a warning.** The filing or the edit goes on, and a person records the wait or rewords the text.
- **The whole body is read,** the prose of the `## Dependencies` section among it. A hint is never counted as a wait (point 5).
- **A record that is not accepted** is one the default branch does not hold as accepted, though its own change may have accepted it. A record the Task's own change proposes is no hint. Where the capability cannot tell which issue carries a record, it flags the record.

### 8. The lifecycle's gates read the waits

Once the project turns the checks on (point 11), the moves that start a Task and merge its change read its waits through the reader (point 3):

- **Starting a Task,** its move into In Progress, whichever command makes it, is refused while one of its waits is open, its own or an ancestor's. A person may bypass the refusal with an audited reason (DEC-014).
- **Merging a Task's change** is refused while one of its own waits is open, since the work it rests on has not landed. The refusal is a hard reject. An ancestor's wait holds no merge (point 1).
- **An answer that is not whole, or a Task that is undeclared** (points 3 and 6), refuses either move in the same way, since neither shows that no wait is open. For the merge, only the answer on the Task's own waits counts.
- **A wait on an issue the change itself closes** lands with the change, since its merge lands that issue's work too. So it holds no merge of that change. What a change closes is what its pull request names as closed ([project-management:DEC-013-branch-and-pr-conventions]).

### 9. A change that rests on unfinished work waits on it

A change *rests on unfinished work* where it rests on work of another issue that has not landed for its Task (point 1): a record that is not accepted (point 7), which that issue's change proposes, or that issue's own work as a Task, such as commits of its branch. Its Task then waits on that issue, through a wait of its own. Whoever finds that the change rests on such work records the wait through the writer, when the Task is filed or while it is built, for the merge gate to hold the change until that work lands (point 8). Work the change carries itself is its own, and needs no wait: a record it proposes, or the work of an issue it closes (point 8).

Once the project turns the checks on (point 11), the capability checks it where it puts a Task's change up for review, and again before it merges the change. It refuses the change, as a hard reject, where the change rests on another issue's work that has not landed for its Task, the change does not close that issue, and no wait of the Task's own is on that issue. The change rests on an issue's work where it:

- **cites** a record that is not accepted, which that issue's change proposes
- **holds** commits of that issue's branch, the issue being a Task, which the default branch does not hold

### 10. A project's existing sections are converted through a proposal a person reviews

A command reads each open issue's `## Dependencies` section, proposes the waits it means, and writes only those a person accepts. It sorts each issue the section names:

- **A proposed wait:** its line says that the issue waits on the issue named.
- **No wait:** the issue itself, its own ancestor, or an issue its line says waits on this one.
- **Unclear, and flagged:** any other, such as an issue named for context. It becomes a wait only where the person makes it one.

The proposal also flags each proposed wait the writer would refuse, such as one that closes a loop, with why. For each open Task that records no wait and is proposed none, whether or not it has a section, it proposes the declaration that the Task waits for nothing (point 6).

The person reviews the proposal and may change it. The command then writes the waits and the declarations the person accepted, waits in the selected form, through the writer. It leaves the prose as it stood. It proposes no wait already recorded, and no declaration a Task already makes, so it may run again.

A project that turns the checks on while open Tasks are undeclared finds none of them ready, and the gates of point 8 refuse to start or merge them. So a project converts its sections first, and then turns the checks on (point 11).

### 11. A project turns the checks on with a key

The checks that refuse or hold a Task apply once the project turns them on, with a key in the capability's project configuration:

- **at filing and at each edit,** the refusal of a Task that declares neither its waits nor that it waits for nothing (point 6)
- **in readiness,** readiness reckoned from the reader's answer: a Task's own waits and its ancestors', and the hold on an undeclared Task and on an answer that is not whole (points 1 and 3)
- **at the start and at the merge,** the gates of point 8
- **at review and at the merge,** the check of a change that rests on unfinished work (point 9)

With the key absent, they are off. A new project starts with them on, as [COR-066] point 4 turns its refusal on: an install of the capability, where the project holds no key, asks whether to turn them on, with consent as [COR-048] point 5 asks. The question shows what the install's read of the tracker found. Its default answer is on only where the install read the tracker in full and found no open issue. Elsewhere it is off, and the question points to the conversion (point 10). With nobody to ask, only an explicit flag turns them on, and without one the install writes no key, so the checks stay off. An upgrade never writes it. A person turns the checks on, or off, by a change they authorise. The key counts as the default branch holds it, so no change turns off a check that judges it.

**With the key off, a project works as it did before this record.** Every command that reckons readiness reckons it as the shared pool did: each open issue a Task's `## Dependencies` section names holds the Task back, and nothing else does.

- **No recorded wait holds a Task,** in place of the section or beside it, and no ancestor's wait holds it.
- **A read of waits that is not whole holds nothing back,** and an issue the section names holds nothing back once it is closed, however it closed.
- **Nothing this record adds refuses** a filing, an edit, a start, a review or a merge.

So DEC-025's promise, that a project that writes its dependencies as prose meets no breaking change, holds until the project turns the checks on. What applies with the key off is what holds and refuses no Task:

- **The writer and its checks** (points 2 and 4), which refuse a wait the capability would write, not a Task.
- **A wait the capability writes on a Task** is named in that Task's section too, since only the section holds the Task until the key is on. A typed line is in the section already.
- **The reader's reports** (points 1, 3, 4 and 6), and a report of each open wait of a Task, its ancestors' among them, whose issue the Task's section does not name, since that wait holds nothing until the key is on.
- **The flag on hints** (point 7) and **the conversion** (point 10).

Once the key is on, readiness reads the waits alone, and the section's prose holds nothing back (point 5). The conversion leaves the prose as it stood, so a project converts its sections first, and then turns the key on (point 10).

### 12. DEC-025's open questions 4, 8 and 10

- **Question 4, the typed line's shape,** is answered. A typed line names one issue of its own repository, as `#N` (points 1 and 4). A line of the same shape with `nothing` in place of the number declares that a Task waits for nothing (point 6). A wait is apart from containment: a child does not wait on its parent, and a wait on an ancestor is refused, since it would never end. A container's wait holds back the start of the Tasks under it (point 1).
- **Question 8, waits across repositories,** is narrowed. Until a record answers it, the writer refuses a wait on another repository's issue, and a found one leaves its waiting issue's readiness unknown.
- **Question 10, what evidence builds the primitive,** is answered for waits and stays open for lanes. Prose read as waits held Tasks back for good, and a view of the work needs waits it can read. That evidence is enough to build waits. Lanes still wait for the evidence the question asks for.

## Rationale

**Why the tracker's links by default.** They are the tracker's own record of the relation. Its pages show them, its interfaces answer them with nothing to parse, and a person adds one without learning a line's shape. A line in a body is read only by the capability. This is why containment prefers sub-issues (DEC-005, DEC-039).

**Why typed lines where the project selects them.** Not every tracker has the links. A project may also keep its waits in the body, where a diff, an export or a copy of the issue shows them. The typed line serves both, and is the shape DEC-025 named.

**Why one form is written, where containment writes two.** Containment writes the parent's first line in both modes. Where the two records disagree, the native parent wins, since an issue has one parent. Waits are a set. Kept in two places, each removal must be made in both, and no rule can tell a wait removed from one place from a wait missing from the other. So the capability writes one form. The reader reads both only so that no wait written by hand is lost.

**Why the reader takes the union and reports.** A wait missed lets work start too early, which costs a build thrown away or a conflict at the merge. A wait kept too long holds work back, which the report shows and a person ends. So the reader errs toward holding, and says where a wait lies outside the selected form.

**Why an answer that is not whole holds the issue back.** An answer cut short could miss the one open wait. A command that took the issue as ready would start work the project meant to wait. A view would show it ready when it cannot tell (#1548).

**Why a tracker without links is told from a failed read.** A project selects typed lines where its tracker has no links, and there every read of links fails. Taken as a failed read, it would leave every Task's answer incomplete, so none would be ready and every merge would be refused. Taken as no links, a read that truly failed would pass for an empty answer and miss a wait. So the reader establishes the absence, as containment's reader establishes a tracker without sub-issues ([pkit:ADR-035]), and never infers it from a failure's status or text.

**Why a project's declaration answers a read the reader cannot attribute.** Here this record departs from ADR-035. There a project's declaration governs only writes, and a read the reader cannot attribute stays incomplete, which holds only a container's close. Here an incomplete answer holds every Task, so a tracker whose absence the reader cannot establish would hold all work for good. So the declaration answers such a read. That accepts one case by name: where a project declares no links on a tracker that has them, a read that fails for a cause the reader cannot attribute, such as a token without the scope to read them, passes for no links, and a wait recorded as a link is missed. The reader narrows it: it still reads links, and a read that answers overrides the declaration, so a tracker that gains links is read. A project that selects links says by that that its tracker has them, so only one that selects typed lines declares that it has none. The reader selects no form by it: the project still selects the form (point 2).

**Why a wait on a container is its Tasks' wait too.** The tracker lets a person mark a Feature or an EPIC as blocked by another issue, the most natural use of the link. DEC-060 point 4 already gives weight to a wait on a Feature, so people write waits of Features too. A wait that held none of the container's Tasks would be written and do nothing, the mirror of a wait left out. Only Tasks are offered, started and merged, so a container's wait holds its work through them. A Task filed under it later is held too, since the wait says that the container's work comes after.

**Why a container's wait holds back only a Task's start.** A Task that has not started costs nothing to hold back. A Task already started was started on what was known then, and its work may not rest on the awaited issue at all. Holding its merge would strand work in progress for a wait that may not concern it, and only a person can tell whether it does. So the capability lists the started Tasks, and a person records a wait on each whose work rests on the awaited issue, which holds its merge. A Task started by the bypass while an ancestor's wait was open was started on purpose, with an audited reason, as any start the bypass lets through.

**Why the checks run when a wait is written.** A wait on itself, on an ancestor or in a loop holds back for good each Task on it that has not started, since what such a Task awaits closes only after it. Refused when written, it never holds work back. Found only when read, it already has. The reader still checks waits written elsewhere, since the capability checks no write it did not make.

**Why a loop counts each container's children.** A container reaches Done only once its children have. Say an issue waits on a container, and one of that container's children waits on the issue. Then the issue's wait never ends. The wait on an ancestor is the shortest such case. A Task waits on what its ancestors wait on too, so a container's wait on an issue under it holds back for good each Task under that issue that has not started, or the issue itself where it is a Task: they wait on it through the container.

**Why a loop counts an ancestor's wait on a Task already started.** Such a wait holds nothing of that Task (point 1), so a loop through it may end once the Task lands. The writer refuses the loop all the same. A started Task can be moved back to Backlog ([project-management:DEC-006-state-machine-and-cascade]), and a Task filed under the container later starts unstarted, and either would then be held for good. A check that read each Task's state would have to run again at every such move and filing. So a container whose other Tasks come after one of its own Tasks records the wait on each of those other Tasks, not on itself.

**Why the prose counts as no wait.** Prose says many things about other issues: what waits on this one, what it belongs to, what it follows from. A reader that counts every number in it reads each as a wait, as #3548 and #2290 show. A typed line or a link says one thing.

**Why a wait ends only when its work lands.** A wait orders work so that the waiting issue starts, and its change merges, after the work it rests on. An issue closed as not planned lands nothing, such as a record refused in its change, or work dropped. A wait that ended on that close would let the change land on a decision nobody accepted, or on code that never came. So the wait stays open for a person to mend, who knows whether the work moved to another issue, or whether the waiting issue rests on it at all.

**Why a wait ends on the default branch, or the Task's own integration branch.** The default branch is where a record counts as accepted, and where all work ends up. An issue under an integration branch closes on its merge into that branch, before its work reaches the default branch (DEC-013). A wait that ended at that close would let a Task outside the branch start, and merge into the default branch, before the work it rests on, which COR-066 point 1 forbids for a record. A Task under the same branch merges into that branch, and the branch reaches the default branch only once that Task has closed too. So for it the order holds at the awaited issue's own close, and a wait held until the branch merged would never end.

**Why a Task declares that it waits for nothing.** A check finds a wait that is wrong, but not one left out: a Task whose wait was never recorded reads the same as a Task that waits on nothing. The declaration has the filer say which, while they know what the Task rests on. It costs one line on a Task with no wait. The pool offers, starts and merges Tasks, so a Task alone declares.

**Why the declaration is a line in the body.** The tracker's links say only what an issue waits on. A line in a typed line's shape is read by the same reader, and a person learns one shape for both.

**Why an undeclared Task is not ready.** Taking it as ready would assume what the declaration exists to have stated. Held back and reported, it costs a line to mend. Taken as ready, it may start on work that has not landed.

**Why a hint is flagged, not refused.** No reading of prose is sure, as "Why the prose counts as no wait" says. A hint may be a false match, such as a sentence about an issue that comes after this one. A refusal on a false match would block the filing until the text was reworded to pass. A warning shows the hint to the filer, who knows.

**Why the gates read the waits.** Readiness decides only what the pool offers. A person can start a Task directly, and a wait found after the start (point 9) holds nothing back. The start gate stops a Task before work is spent on it, and the merge gate is the last point at which the order holds.

**Why the start may be bypassed and the merge may not.** The severity model keeps a bypass for a discipline a person may have reason to skip, and a hard reject for what later work rests on (DEC-014). A person may start a Task on another Task's branch on purpose, and the merge gate keeps the order: at worst the work is built again. A merge before the work it rests on lands the change on a record nobody accepted, or on code that is not there, which the acceptance gate forbids ([COR-066] point 1).

**Why a wait on an issue the same change closes holds none of its merge.** A pull request may close several Tasks of one parent where their work is tightly coupled (DEC-013), and that is where one Task waits on another. The awaited Task closes only when that merge lands, so a gate that read its wait as open would refuse the merge on every try. The one merge lands both Tasks' work, so the order the wait asks holds. At the start no change says yet what it closes, so a Task built in one change with the issue it waits on starts by the bypass, with that as its reason.

**Why a change that rests on unfinished work waits on it.** The acceptance gate asks that work built on a proposal land no earlier than the change that proposes it (COR-066 point 1). A wait is what the merge gate reads, so recording one makes that order a check. The check at review and at merge catches what the change itself shows: a record it cites, and a branch it holds. Any other way a change rests on unfinished work is recorded by whoever finds it.

**Why a person reviews the conversion.** Only the author of a section knows whether each number in it is a wait, and some sections do not say. A command can propose and flag. A wrong wait written unseen holds work back, and a missed one lets work start too early.

**Why the checks wait for a key.** A project that upgrades has open Tasks whose waits are prose, and so does one that installs the capability over a tracker it already uses ([project-management:DEC-036-substrate-pluggable-adoption]). Turned on at once, the checks would find each of them undeclared: none would be ready, and none could start or merge, before the project had converted its sections. So a project turns the checks on once it has converted. An install writes the key only with consent, as COR-066 point 4's does, and it asks, since the person knows what its read cannot, such as that a project whose tracker it cannot reach yet is new. Its default is on only over a tracker read in full with no open issue, since only there is nothing to convert. It counts issues, not Tasks, since a project that adopts a tracker it already uses maps its issues to Tasks only after the install ([project-management:DEC-037-adoption-ceremony] point 1). Held by the default branch, the key cannot be moved by the change it would judge.

**Why nothing this record adds holds a Task while the key is off.** DEC-025 promises a project that writes its dependencies as prose no breaking change. Waits read beside the prose would break it: a link made on the tracker's page, a wait on a container, or a read that failed would each hold work that nothing held before. Waits read in place of the prose would drop what the prose names, and let work start early. So readiness reads the section alone until the key is on. The reader reports meanwhile each wait the section does not name, so the project sees it before it turns the key on. A wait the capability writes is named in the section too, so that work filed the new way is held as before.

**Why waits stay within the repository for now.** The shared pool is the repository's own (DEC-059). A loop check across repositories would read each other repository's waits, and readiness would read its states. Holding a found wait on another repository's issue as unknown keeps its waiting issue from starting early, until a record decides how to read another repository.

### Alternatives considered

- **Typed lines alone, as DEC-025 named.** Rejected: the tracker's links show on its pages and need no parsing, and a person adds one without learning a shape. A project whose tracker has none selects typed lines.
- **Links alone.** Rejected: not every tracker has them, as not every tracker has sub-issues (DEC-039).
- **Write both forms, as containment does.** Rejected, as "Why one form is written" says.
- **Read only the selected form.** Rejected: a wait written by hand in the other form would be lost, and its issue would start early. Where the tracker has no links, the reader establishes it, or the project declares it (point 3).
- **Refuse a wait whose waiting issue is not a Task, and report one found.** Rejected, as "Why a wait on a container is its Tasks' wait too" says: it would refuse the link a person most naturally writes.
- **Hold the merge of each Task under a container whose wait is open, a Task already started among them.** Rejected, as "Why a container's wait holds back only a Task's start" says.
- **Count in a loop only the ancestors' waits of Tasks not yet started.** Rejected, as "Why a loop counts an ancestor's wait on a Task already started" says.
- **Keep reading the prose, and teach the reader to tell a wait from context.** Rejected: no reading of free prose is sure, and a wrong guess holds work back or lets it start early.
- **End a wait however its awaited issue closed.** Rejected, as "Why a wait ends only when its work lands" says.
- **End a wait once its awaited issue closes, on whichever branch its change merged into.** Rejected, as "Why a wait ends on the default branch, or the Task's own integration branch" says.
- **Take a Task that records no wait as waiting for nothing.** Rejected, as "Why a Task declares that it waits for nothing" says.
- **Refuse a Task whose text hints at a wait.** Rejected, as "Why a hint is flagged, not refused" says.
- **Hold work back through readiness alone.** Rejected, as "Why the gates read the waits" says.
- **Hold the start as firmly as the merge.** Rejected, as "Why the start may be bypassed and the merge may not" says.
- **Convert the sections without a person's review.** Rejected, as "Why a person reviews the conversion" says.
- **Turn the checks on with the release that brings them.** Rejected, as "Why the checks wait for a key" says.
- **While the key is off, read a Task's recorded waits in place of its prose, or beside it.** Rejected, as "Why nothing this record adds holds a Task while the key is off" says.
- **Answer question 8 here, and read another repository's waits and states.** Not taken: it needs reads of other repositories, which a record of their own decides.
- **Detect whether the tracker has links, rather than select by hand.** Deferred, as DEC-039 defers detecting sub-issues. A project knows its tracker, and the selection serves both cases now. The reader establishes only whether the tracker has links (point 3), and selects nothing by it.

## Implications

The edits this record makes to accepted records, once a person accepts it, each with a pointer to it:

- **DEC-025 is refined in place.**
  - **Its summary, its Context and its Decision's lead** then say that what an issue waits on is recorded and read as this record decides, and that lanes alone wait for lived evidence. Its summary says too that until a project turns this record's checks on, readiness is read from each issue's `## Dependencies` section.
  - **Its design table's row on the sequence conflict** then gives the tracker's links, or typed lines where the project selects them, as the substrate, decided by this record.
  - **Its section on the typed line** then says that a wait is a link or a typed line, that one reader reads both, that a Task waits on what its ancestors wait on too before it starts, that the section's prose explains, that readiness is reckoned from the section until a project turns this record's checks on, and that a Task declares its waits or that it waits for nothing.
  - **Its open questions** then give point 12's answers to questions 4 and 10, and question 8 its narrowing. Their lead then says that the record that builds lanes answers the rest.
  - **"Why the mechanisms wait for evidence" and "Why lanes and the typed line wait"** then say that lanes wait, and that waits had their evidence first.
  - **Its paragraph on the typed line keeping the prose** then says that the prose explains, and that existing sections are converted. It says too that until a project turns this record's checks on, readiness is reckoned from that prose, each open issue the section names holding a Task back, so its promise of no breaking change, for a project that writes its dependencies as prose, holds until then.
  - **Its alternatives "Build the full primitive now" and "Manual discipline only"** then say that this record builds waits, and that lanes wait.
  - **Its Implications** then say that a record of their own builds lanes, that this record overturns DEC-005's table in part, and that the build of waits is a surface change. Its source scratchpad then retires with the record that builds lanes.
- **DEC-005 is overturned in part.** Its top line then reads *Partially superseded by* this record: "blocked by" between issues is the tracker's own link, or a typed line where the project selects it. Its table stays as it stood, and containment, "follow-up to" and "see also" stand.
- **DEC-006 is refined in place.** Its "Authorisation gates" then say that, once a project turns this record's checks on, a Task's move into In Progress is refused while one of its waits is open, its ancestors' among them, while its waits cannot be read in full, or while it is undeclared, and that a person may bypass the refusal with an audited reason. Its Implications then say that the merge of a Task's change is refused, as a hard reject, beside the checkbox check, while one of the Task's own waits is open, while those cannot be read in full, or while the Task is undeclared, save for a wait on an issue the change itself closes.
- **DEC-010 is refined in place.**
  - **Its universal body rules** then add that, on a Task body, a hint of a wait is reported as a warning where no wait of the Task names its issue, for a record the issue whose change proposes it.
  - **Its optional sections** then say that a Task that records no wait declares in the `## Dependencies` section that it waits for nothing, which point 6 checks outside the floor its schema holds.
- **DEC-036 point 4** then lists waits beside containment: degradable to typed lines, by the `waits: native | textual` selector.
- **DEC-059 point 7** then defines a ready Task in Backlog as one that declares its waits and has none open, its ancestors' among them, and whose waits could be read in full, citing this record. It says too that until a project turns this record's checks on, such a Task is instead one whose `## Dependencies` section names no open issue.
- **DEC-060 is refined in place.**
  - **Its point 4** then says that, once a project turns the checks on, the pool holds a Task back until the foundation's Feature's work lands, not merely until the Feature closes (point 1).
  - **Its Implications** then say that its rule rests on dependencies as this record's point 1 defines them, where they say that dependencies stay prose. Their named question of how a Task In Progress waits for a change to the foundation then takes point 8's answer, that once a project turns the checks on, a wait recorded on the Task holds its change's merge.
- **DEC-066 point 1** then has the later of two Tasks that share a file say in its `## Dependencies` section that they share a file, where it says so in the dependency. Its Implications then say that point 1 rests on dependencies as this record's point 1 defines them, where they say that dependencies stay prose.
- **DEC-082 point 5** then has a Task that nothing blocks be ready in sequence as DEC-059 point 7 reckons it, citing this record, in place of restating that test.

Other implications:

- **The build** is a Task of its own (#3553), and rests on the architecture record below once it is accepted. It brings the reader and the writer, the selector in the substrate map's schema, the key of point 11 and the install's question of it, the declaration's check, the flag on hints, the gates on starting and merging, the check of a change that rests on unfinished work, the conversion command, the shared pool reading waits through the reader, and the pm skill's filing steps. It is a surface change of the capability, versioned under [pkit:PRJ-002]. With the key absent the checks are off, so a project that upgrades keeps working as before, and the release's notes point it to the conversion and the key.
- **The commands that start a Task and merge its change** take point 8's gates with the build, and the capability's README lists them among each command's gates.
- **An architecture record pins how waits are read and written** (#3562), as [pkit:ADR-035] pins containment's: the reader's and the writer's contract, how a project declares that its tracker has no links (point 3), and the key of point 11. It is the architect's to author.
- **The capability's README** says, where the shared pool reads dependencies, that this record decides how an issue records its waits. Its account of how the pool reads them changes with the build.
- **Other records** that speak of an issue's dependencies, such as DEC-060 where a Task names another among them, keep their words, read as point 1 defines an issue's dependencies.
- **The analysis of parallel work** and its glossary define a ready Task by the prose, and change with the build.
- **The scratchpad on parallel work** stays open for lanes, and retires when the record that builds lanes is accepted ([COR-012]).
- **No behaviour changes with this record.**
