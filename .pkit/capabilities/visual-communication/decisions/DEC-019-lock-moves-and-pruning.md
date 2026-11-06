---
id: DEC-019
title: A lock's proposed move is the diff one run leaves, and pruning removes only what lies behind
status: proposed
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** to move a published piece's lock, a person runs one command. It moves the lock, makes an export under it, and writes the piece's current copy as an export does. All of it stays in the working tree as a diff. That diff is the proposal, and the person lands it as the project lands any change. The copy's two sides in that diff show the figure before and after, and a read-only command draws each of the piece's pages both ways for any reviewer.

The run stops as an export stops, and on an edit of the piece since its copy, so no run folds in an edit nobody named. It runs no program. By default it moves within the lock's majors, to versions that fit. A person names a version to go further: to a new major, or past a clash or a lost end.

A second command lists what each lock could still take. A third removes library versions no lock names, but only one that lies behind: a newer one of its major stands, and no lock that moves can still reach it. It shows its list and asks first.

## Context

A published piece's lock moves only through a proposed change a person reviews ([visual-communication:DEC-003-change-over-time] point 8). An export refuses every other way ([visual-communication:DEC-017-final-and-published-states] point 5). The records leave open what that change is, and what removing versions spares ([project-kit#2701](https://github.com/aleskalfas/project-kit/issues/2701)).

Three words carry two senses here. A *version* that wrote a copy, or that an export made, is a numbered export run. Any other bare *version* is a *library version*, what a lock names (DEC-017, Context). A *page* alone is one of a piece's pages, and a *documentation page* is one that shows its copy. A copy's *two sides* are its files in a change, as they stood and as they stand, and the before-and-after's *drawings* are that command's own. Each has its before and its after.

What the records leave open:
- **What a proposal is.** The capability depends on no work tracker, and a project lands a change as it chose (the use case of putting a figure in a documentation page, UC-094). A command writes a diff for review only on request ([visual-communication:DEC-002-files-and-validation] point 9).
- **What it carries.** A moved lock changes what an export reads, so the check fails the current copy as stale ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 8). The gate reads the version that wrote that copy (DEC-017 point 5).
- **A picture the move makes stale.** No upgrade runs a program (DEC-006 point 1), and an export stops on a stale picture (DEC-006 point 7). A program reads its values under the piece's lock, so it cannot run for a lock not yet moved.
- **The before-and-after.** The records make it a command (DEC-002 point 7, DEC-003 point 9). A figure moves only through a change that shows it before and after (DEC-003 point 8, and UC-094's minimal guarantees). What lies in the clone's local folder never lands (DEC-002 point 1).
- **Versions that do not fit.** A person may move a lock to them, and each clash or lost end is a finding ([visual-communication:DEC-010-list-item-fields] point 2, [visual-communication:DEC-011-tie-ends] point 4). Nothing says how a person names them to a command.
- **How far a move reaches.** A new major is taken on purpose, and the fact that a lock is behind names no limit (DEC-003 points 8 and 9).
- **Removing versions.** One that no lock names may be removed (DEC-003 point 4). Several such versions still serve something, and one that only a kept fingerprint names is no lock's (DEC-017, Implications).
- **A move with no before.** A published piece may have none of its copy's files standing (DEC-017, Implications).
- **The writers.** A command writes only the files a record names it the writer of (DEC-002 point 9).

A copy's form is decided apart ([project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700)). Point 5 says what this record assumes of it.

## Decision

**A proposal is what one run of `pkit visual upgrade` leaves in the working tree: the moved lock, a new version, the current copy it wrote, and the findings record. The copy's two sides show the figure before and after, and the before-and-after stays a read-only command. The run stops on an edit since the copy and on what stops an export. It stays within the lock's majors, among library versions that fit, unless a person names one. `pkit visual outdated` looks across majors. `pkit visual prune` removes only what lies behind, after showing it and asking.**

### 1. A proposal is the diff one run leaves

A *proposal* is what `pkit visual upgrade <piece>` leaves in the working tree.
- **One run writes it.** Running the command is the request a review asks for (DEC-002 point 9).
- **Nothing beyond the diff.** The run commits nothing, makes no branch and opens nothing on a work tracker. No file or field names a proposal, since a hand could write one (DEC-017, Alternatives considered).
- **A person lands it,** through a pull request, or directly where one person works alone (COR-009). Landing it is the review's yes, much as a person reviews the diff of a rewrite that follows a format change (COR-059 point 10). Discarding the diff is its no, and leaves only a numbered version's files in the clone's local folder.
- **What may join it.** The change that lands a proposal may carry more, each by a person's own act: a library version brought in, a picture made again (point 4), or content mended (point 7).
- **One piece to a run.** Several moves may land in one change, and each piece's copy shows its own two sides.
- **A published piece alone.** The run refuses a piece in another state, or one final to every command (DEC-017 point 3). It names what moves that lock: a draft's render, a hand on a pinned lock, or nothing on a final piece.
- **From the lock as it stands.** It reads the lock in the piece's own file, whoever wrote it. So it serves a piece the gate stopped for a lock that differs, as after a lock written by hand.
- **Nothing to move.** Where it would propose the lock the piece holds, and the version that wrote the copy was made under that lock, it says so and writes nothing.
- **A dry run.** Its effect reaches past what a person names, so it offers the methodology's dry run (COR-004). That stops where the run would, says what it would write, and prints each page point 5's look ahead finds different. It keeps no drawing, so it changes nothing.

### 2. A proposal carries what the check and the gate read

The run is a lock move, a render, then an export run, as one change. Every stop comes before any write, and a failed write leaves each file as it was, or names each it could not put back.
- **The lock,** moved in the piece's own file.
- **A new version** in the record of exports, made under that lock. Its numbered files stay in the clone's local folder, as any version's do (DEC-006 point 7).
- **The current copy,** written from that version. The record names that version as the copy's writer, with each file's path and hash (DEC-017 point 7).
- **The findings record.** The run renders the piece under the moved lock, with the stand-ins ([visual-communication:DEC-016-what-an-export-reads] point 5). So the record's key reads that lock, and the render is one a person ran. It draws no preview, so that record is all it leaves.
- **Its export run** follows every rule of an export, its stops included. The gate alone does not hold it (DEC-017 point 5).
- **So no difference stays at the gate.** The version that wrote the copy was made under the lock the piece holds, so the next export runs.
- **So the move itself fails nothing.** The copy's fingerprint verifies, and the findings record needs no new render.
- **What the new library versions find is another matter.** Fit weighs what a lock can hold, not how a page draws. So a default move may bring a finding that fails, such as text that overflows ([visual-communication:DEC-005-engine-and-plugins] point 14). A copy made with a number or a date let through stays a finding too (DEC-006 point 8). The run names each, and point 7 says the mend.
- **No library version travels in it.** The run moves only to versions the library folder holds. Bringing one in is another command's act, which lands before the proposal or with it.

### 3. An edit since the copy stops the run, so no run folds one in unnamed

A text edit and a library change stay apart (DEC-003, Rationale), and a lock moves only through a change a person reviews (DEC-003 point 8). So no run folds into the copy an edit nobody named. It compares the piece with the version that wrote its copy.
- **What it reads.** It reads "changed" as DEC-016 point 1 does, with the lock put back, as DEC-017 point 1 reads it. It also leaves out the files of the lock's library versions. So the move counts for nothing, and a library version gone from the project stops nothing.
- **It stops before any write,** and names each input that changed.
- **The plain way on.** An export lands the edit under the lock the copy holds, and the run then finds none.
- **Where the edit needs the move,** the person who runs it names each input that changed, as for a stale output. Content may name a library the lock lacks, which no export can draw. An input nobody named still stops, and the run prints the line that names them all.
- **An edit added after the run** is a person's own act. The diff shows it, and a look back separates it, since both its drawings take the same content (point 5).
- **A fingerprint it cannot read** refuses, and names the record, as the gate does. The way out is that record as version control last held it. Where nothing wrote a copy, nothing compares (point 6).

### 4. A stale picture stops the run, which runs no program

- **The stop.** Under the new lock, an output of DEC-006 point 1 may read other values, and so go stale. The run stops before any write, and names each such output and what changed. It runs no program (DEC-006 point 1).
- **The way on.** The person names each output to use it as it is, as for an export (DEC-006 point 7). The proposal then carries that output, and a copy made over it. Both ask for attention until they are made again, and neither fails (DEC-006 point 8).
- **Making it again follows the run.** A program reads its values under the lock the piece holds, so it can run only once the lock has moved. The person runs it, then an export, which the gate lets through (point 2).
- **Those two acts go together.** Between them the copy is stale, which fails (DEC-006 point 8). So a proposal lands after the run, or after that export, and not between them.
- **By hand instead.** A person may write the lock, run the program, then run the command. That run names the versions the hand wrote (point 7), and the picture's record as an edit (point 3). No copy is then made over a stale output.
- **Never a lock alone.** No run writes the lock and stops.

### 5. The change shows the figure on its copy's two sides, and the before-and-after stays a command

- **What the change shows.** It holds each file of the current copy twice, as it stood and as it stands. A reviewer reads those two sides, so the change shows the figure before and after (UC-094). No other file lands for it.
- **How a file shows** is the review tool's. A format it cannot draw, such as a PDF, is opened on each side, or read through the before-and-after.
- **The before-and-after stays a command** (DEC-002 point 7). It reads only, draws each of the piece's pages before and after in the clone's local folder, and prints each page that differs. The change shows what a documentation page will show, and the command isolates why the figure moved. A person asks for one of two looks.
- **A look ahead, before a move.** Its before is the lock of the version that wrote a published piece's copy, read as DEC-017 point 1 reads it, and otherwise the lock the piece holds. Its after is what a run would propose, or the versions a person names in point 7's form. For a final piece, which no run moves, its after is the lock the piece holds.
- **A look back, at a change.** Its base is the backbone's answer for a comparison: where the branch left the default branch, or a base named for that look (COR-054 points 3 and 5). Its before is the lock of the version that wrote the copy at that commit, or the lock held there where no version did. Its after is the lock the piece holds now. So any reviewer runs it on a checkout of the change, with no work tracker.
- **The base.** One that resolves to nothing refuses (COR-054 point 4). The files at the base are read through the converters (DEC-003 point 2). A piece the base does not hold has no before, and it says so.
- **Where the two locks are one,** it says so, and stops nothing.
- **Who takes it.** The run looks ahead for whoever runs it, before it writes the proposal. A pinned draft takes a look ahead only with versions named, since no run proposes its lock, and those may include one not yet released (DEC-003 point 8). A final piece takes it too, as what only reads does (DEC-017 point 3), and a look ahead finds its two locks one.
- **What it isolates.** Both drawings take today's engine and one filling of an export's facts (DEC-016, Implications). So a number the piece shows drops out, and what differs is the locks'. Where a picture was made again, both drawings take the new one, so only the copy's two sides show the old one. Where the engine's release differs from the one the copy's version recorded, the command says so, since the copy's two sides then hold more than the move.
- **What it draws from.** The committed pictures, and it reports the stale ones (DEC-006, Implications). A drawing it cannot make stops nothing, as where a library version left the project.
- **What this assumes of a copy's form** ([project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700)):
  - A file's name stays through a move, so a diff pairs its two sides. A name that changed would leave the old file at its old place, unchanged and outside the diff, and show the new one as new. The run names what it leaves behind. What a name must hold is that record's, for a documentation page's link.
  - A file can be shown alone, as a picture. Where one file holds several modes, a review tool shows one of them, and the before-and-after draws the rest.
  - The run writes what an export run writes, so what the copy's files are changes no rule here.

### 6. A move with nothing to compare goes on, and shows only an after

- **The case.** A published piece none of whose copy's files stand, or whose record holds no current copy of its own (DEC-017 points 5 and 7).
- **The run goes on.** It writes the copy whole, and the record names its version as the writer. So the gate finds no difference. The run says no file stood.
- **What a reviewer sees.** Each file of the copy as a new one. Where some files stand, each of those shows its two sides, and each missing one its after alone. A file at a place the piece came to name since reads as new too, and the run names what it leaves behind (DEC-017 point 7).
- **Why it stops nothing.** A documentation page that links such a copy shows a dead image, so it holds no figure to move.
- **An edit still stops it** where a version wrote the copy, since the record keeps that version's inputs whether or not its files stand (point 3).
- **A before, where a person wants one.** Version control holds the files that went. The before-and-after draws the piece under the lock of the version that wrote them, where that lock's library versions stand.

### 7. A move stays within the lock's majors, and a person names what goes further

- **By default.** The run works out the lock as a draft's render does, among released versions alone (DEC-003 point 8). It stays within the lock's majors, takes versions the installed capability reads, and keeps to versions that fit.
- **What it held back.** It states each newer version it did not take, with why, as a render states one.
- **A version named.** A person names a version to the run in the form the command that brings a library in takes, and may name several. The run then moves what is named, and only what that needs, so a person moves one library and leaves the rest. A name may lie below the lock (DEC-011 point 4).
- **A new major** is taken only by a name, or by a lock written by hand, which names it too. A named version that needs a new major of another library refuses, naming that library. So no major moves unnamed.
- **A name goes past a clash or a lost end.** Neither holds a named version back. The run names each, and each stands as the finding those records decide (DEC-010 point 2, DEC-011 point 4).
- **A finding that fails holds the landing.** The person mends the content in the same change, and an export draws it, which the gate lets through. A person who will not mend it discards the proposal.
- **A name goes past nothing else.** The run refuses a version the project does not hold, one not released, and one the installed capability cannot read. It refuses libraries that build on two majors of one library. A published piece can hold none of these (DEC-003 point 9).

### 8. `pkit visual outdated` looks across majors, and the fact that a lock is behind names the way on

- **`pkit visual outdated`** reads only. It takes each lock a person moves: a published piece's, a pinned draft's and written code's. An unpinned draft's render moves its own, and a final piece's never moves.
- **It looks across majors.** For each library it names the newest version that fits within the lock's major. It names each other newer version too, with why a default move would not take it: a later major, a clash, a lost end, or a version the installed capability cannot read.
- **The fact that a lock is behind** (DEC-003 point 9) counts a newer released version the installed capability reads, of any major.
- **What the fact says.** Within the lock's majors, it names the command that proposes the move. Of a later major, it says a person takes that version on purpose, by naming it, since it may rename what the content names.
- **What it leaves out.** It says nothing of fit. Judging fit searches combinations of versions for each piece, a cost a fact does not earn within validation's bound (DEC-002 point 6). So it stays while a version stands that no default move takes, and it names `outdated` for why.

### 9. `pkit visual prune` removes only what lies behind

A library version *lies behind* where all of these hold:
- **No lock names it,** a piece's in any state or written code's. The lock of the version that wrote a current copy counts too. The gate reads it, and writing it back is a way past (DEC-017 point 5).
- **No lock that moves can still reach it.** The lock of a piece final to every command never moves (DEC-017 point 3), and a kept export's lock is only read. Each keeps what it names and no more. Every library version of its major that any other lock names is newer, or no such lock names that major.
- **A newer one serves in its place.** A newer version of its major stands that the installed capability reads. For a released version, that newer one is released too.
- **It holds no unreleased work.** It is no version of the project's own not yet released.

So the run spares each of these, though no lock names it:
- **A project's own version not yet released.** It holds work that lies nowhere else. A copy of a shipped version not yet released holds none, so it goes where it lies behind ([visual-communication:DEC-013-shipped-library-releases] point 5).
- **The release a comparison reads.** A release is compared with the library's newest earlier one (DEC-003 point 7). The newest release of each major stays.
- **A version no lock has taken yet,** while a lock that moves lies below it in its major, or it is the newest of its major. In a major no such lock names, only the newest stays.
- **A library's last version.** Nothing newer stands. Taking a library out of the project stays a person's act.
- **What a piece with no lock yet may take.** Its first lock takes the newest of each major that fits (DEC-003 point 8), and those stay. So the run need not read such pieces. An older version a person moves such a lock to by hand (DEC-011 point 4) may need restoring first.
- **What a library's `builds-on` needs.** It names a major, and a version of every major stays. The check of a version alone reads the newest of each major, so what it reads does not move (DEC-010 point 9).

The run reads no further:
- **A version only another kept fingerprint names is no lock's, and goes.** The run names each kept export under it. Marking that export final leaves a finding until the version is back (DEC-017 point 2).
- **A lock it cannot read stops it,** as on a conflicted merge, since that lock may name any version. So does a record of exports it cannot read, since it then cannot tell whether a lock moves. So does a fingerprint it cannot read of the version that wrote a current copy, since that lock counts too.
- **Locks as the working tree holds them.** A lock on another branch that names a removed version fails the check once merged, and restoring the version mends it.
- **The run takes no version by name.** A person who means to remove a spared one does it by hand (DEC-003 point 4), and the check reads what that leaves.
- **A later reader of a version no lock names** takes its absence as a fact to state, as point 3 and the before-and-after do.
- **What this rests on.** A lock's search goes below that lock only where nothing at or above it fits. An automated test holds that, so a later change to the search cannot break this point unseen.

### 10. `prune` shows its list and asks once

- **The list first.** It names each version it would remove, each it spares with why, and each kept export of point 9. The methodology's dry run shows that list, and removes nothing (COR-004).
- **Then one question.** A terminal is asked once, and a person may consent up front. A run with nobody to ask, and no consent given, refuses and removes nothing.
- **Why it asks.** Running a command is its consent (DEC-002 point 9), but a person who skips the dry run consents to a list nobody has seen. The question shows that list when it matters, and takes nothing from the rule.
- **A diff too.** It removes from the working tree alone, and stages nothing, so a reviewer reads the removal. That belongs in a change of its own, after any proposal lands, since a look back may draw its before from what it removes.
- **A way back.** A shipped version returns through the command that brings it in, and another repository's through its fetch, while that repository holds it. A project's own returns from version control, with its entry on the list.

### 11. The writers

Each command below is the writer of what it names (DEC-002 point 9).
- **`pkit visual upgrade`:**
  - `lock` in the piece's own file, as a render writes it
  - the piece's findings record
  - what an export run writes: the new version in the record of exports, the name of the version that wrote the current copy, the current copy, and the numbered files
  - the before-and-after's drawing, in the clone's local folder alone
- **`pkit visual prune`:** a version's folder in the library folder, which it removes, and that version's entry in the list of libraries.
- **`pkit visual outdated`** writes nothing.
- **The before-and-after** writes only its drawing, in the clone's local folder.

## Rationale

**Why a diff, and nothing beyond it.** The capability depends on no work tracker, and a project lands changes its own way. A diff is what every such way starts from, and the core already asks a person to review one, for a rewrite that follows a format change (COR-059 point 10). A command that made a branch or a commit would take over the project's flow. The gate sees no review (DEC-017, Rationale), so a mark would add no proof, and a hand could write one.

**Why one run writes it all.** A lock moved alone fails the copy, and the gate then refuses the export that would mend it. Carried whole, the proposal's files agree, so a reviewer reads one diff, and the check meets a current copy.

**Why an edit stops it, with a way past.** Without the stop, the run would fold into the copy an edit nobody named. Marking final says what changed and goes on, since its file already went out (DEC-017, Rationale). Here nothing has gone out, so a person can still choose, as before an export. With no way past, a piece would be stuck where an edit needs the move. An export refuses a lock that leaves out a library the piece uses, and the gate refuses a lock the copy was not made under.

**Why a stale picture moves on by a name.** A picture for the new lock needs that lock moved first, and the run may run no program. Writing the lock and stopping would leave what the check fails. So a name moves the lock with the picture as it is, and the person makes it again under that lock. A stop with no way past would leave the piece unable to move.

**Why the copy's two sides, and no drawing that lands.** The copy is what a documentation page shows, so its two sides are the figure before and after, with no second home. A drawing committed for review would stay in history for good (DEC-006, Rationale). A drawing in a pull request's text would need a work tracker. The command gives what a diff cannot, on any checkout, with nothing landed: a PDF's pages, each mode, and the move alone.

**Why a look back takes the backbone's base.** A comparison needs a base (DEC-002, Rationale). The capability's own files cannot give it. A lock, a copy's writer and a newer version read the same before a default run and after a named one, and the record of exports cannot say which of its runs lie inside a change. Where the branch left the default branch says it exactly, and the backbone computes that for every reader (COR-054 point 5).

**Why a move with no before goes on.** A stop would ask a person to bring a file back only to replace it. A documentation page that links such a copy shows a dead image, so a before guards no figure. The check fails a published piece with no whole copy (DEC-017 point 6), so removing the copy is no way round a review. The reviewer still reads every file of the after.

**Why a move stays within majors by default.** A new major may rename what the content names (DEC-003, Rationale), and a proposal that crossed one unasked would hand a reviewer a broken figure. Reading "fit" as a draft's render does keeps one search, and one meaning of the word.

**Why a named run moves only what is named.** A person who names one library asks what that library does to the figure. Moving the others too would bring back the question point 3 protects.

**Why a name passes a clash or a lost end, and nothing else.** A clash or a lost end is mended in the piece's own files, so a person may choose it (DEC-010, Rationale). The other refusals name a lock a published piece cannot hold, which no mend of the piece would cure.

**Why `outdated` looks across majors, and the run does not.** Knowing costs nothing, and a person should see a new major coming. Taking it may change what the content means, so that stays on purpose.

**Why "lies behind" is one rule.** A list of readers would miss the next one, so the rule asks what can still reach a version by itself. A final lock reaches nothing. A render or a default run takes the newest that fits, and goes below the lock only where nothing above it fits. So a version below every moving lock is one they almost never take. Whatever names only a major finds a newer version that stays. Where a search or a hand does reach lower, the cost is a restore.

**Why a kept fingerprint spares almost nothing.** A record of exports names nearly every library version a draft passed through. Sparing them would keep the folder growing, for a case that a restore mends. So the run shows that cost, and a person decides. The version that wrote a current copy differs: one lock for each such piece costs little, and the gate's way past needs it.

**Why `prune` asks, where the capability's other commands do not.** It takes files away, and a person cannot see which until it runs. A version not yet committed has no way back through version control. One question costs little, on a command run rarely.

**Choices of taste.** No design reason decides these, so each takes the plainest answer:
- One piece to a run, rather than every published piece at once.
- A major no moving lock names keeps its newest version for good, until a person removes it.
- The names `upgrade`, `outdated` and `prune`, which this record decides. No accepted record or command holds them, and each is the word a person knows from a package manager. `upgrade` also means a methodology's upgrade (DEC-003 point 5), and the command's `visual` group tells the two apart. The before-and-after's name is left to the change that builds it, since the records already decide that command by its role, and no point here turns on its word.

### Alternatives considered

- **A command that makes a branch, a commit or a pull request.** Rejected. It would bind the capability to one way of landing a change.
- **A proposal that moves the lock alone, with an export to follow.** Rejected. The gate refuses that export, and the check fails the copy.
- **A file or a field that marks a proposal.** Rejected, for the reasons above.
- **No stop on an edit, as marking final says what changed and goes on.** Rejected, for the reasons above.
- **A stop on an edit with no way past.** Rejected. A piece whose edit needs the move could not move.
- **One word that lets every edit through.** Rejected. An edit nobody saw would ride with those a person meant.
- **A run that writes the lock, stops on a stale picture, and goes on later.** Rejected. It leaves files that do not agree, between two runs of one command.
- **A run that runs the program.** Rejected. No such run may start one (DEC-006 point 1).
- **A drawing committed beside the copy.** Rejected, for the reasons above.
- **A drawing a command attaches to a pull request.** Rejected. The capability depends on no work tracker.
- **A before-and-after that works out its own base from the files or the record of exports.** Rejected. It cannot tell a move to come from one made, nor which export runs a change holds.
- **A base a person passes straight to version control.** Rejected. A branch's name would read the local branch, which can lag the shared one (COR-054 point 2).
- **A refusal of a move with no before.** Rejected, for the reasons above.
- **A move that crosses a major by default.** Rejected. It may rename what the content names.
- **A named run that moves every other library too.** Rejected, for the reasons above.
- **A word of its own that goes past a clash or a lost end, apart from naming the version.** Rejected. Naming the version already says which one, and a word would add nothing.
- **A fact that judges fit.** Rejected. It would search versions for each piece within validation.
- **A prune that counts a final piece's lock as one that moves.** Rejected. Its lock never moves, so the oldest talk would spare nearly every version above it.
- **A prune that spares every version a kept fingerprint names.** Rejected, for the reasons above.
- **A prune that takes a version a person names, whatever serves it.** Rejected. A hand already can, and the check then says what it left.
- **A prune that removes a major no moving lock and no `builds-on` names.** Left out. It needs a second reading for a small gain, and a later change may add it.
- **A prune that runs without asking.** Rejected, for the reasons above.

## Implications

- **Edits to accepted records,** each made once this record is accepted, and citing it. Accepting this record accepts them (COR-066 point 5).
  - **The record of change over time, point 4, "Kept while named".** A sentence ends the bullet: the command that removes such versions removes only what lies behind, and shows it first (refinement per [visual-communication:DEC-019-lock-moves-and-pruning] points 9 and 10).
  - **Its point 8, "Published".** Four sentences follow the one on a proposed change, which keeps its words. The proposed change is the diff one run of the command that proposes it leaves. The current copy's two sides in that diff show the figure before and after. The before-and-after of each of the piece's pages is a command any reviewer runs, and it lands nothing. A move none of whose copy's files stand shows only an after.
  - **Its point 9, "These state a fact".** The sentence on a published piece reads: a published piece whose lock is behind a newer released version the installed capability reads. Within the lock's majors it names the command that proposes the move. Of a later major, it says a person takes that version on purpose, by naming it. It says nothing of fit, and names the command that does.
  - **The record of final and published states, point 8.** A bullet follows "An export": the command that proposes a move of the lock writes the current copy too, under the same rules.
  - **Its Implications, "A proposed move of a lock".** It reads: [visual-communication:DEC-019-lock-moves-and-pruning] decides what a proposal carries, which leaves no difference at point 5's gate. Until its command exists a published lock cannot move, which fails closed.
  - **Its Implications, the bullet on the issue's record.** It reads: [visual-communication:DEC-019-lock-moves-and-pruning] names that command a writer of the copy, and decides a move of a piece none of whose copy's files stand.
  - **Its Implications, "What removing a library version no lock names spares".** It reads: that is decided by [visual-communication:DEC-019-lock-moves-and-pruning] point 9. A library version named only by kept fingerprints, other than that of the version that wrote a current copy, is no lock's, so marking final an export made under it leaves a finding until it is back.
- **These need no edit:**
  - The record of files and validation's point 9. This record names the writers, and `prune`'s question adds to that rule and takes nothing from it.
  - The record of final and published states' point 3. Where a record of exports cannot be read, it takes the piece as final, which guards the piece's folder from writes. `prune` writes nothing in a piece, and taking the piece as final would let it remove more, since a final lock keeps only what it names. So it stops instead (point 9).
  - The record of files and validation's point 7, and the record of change over time's point 9, "These are commands". The before-and-after stays a command, and no validator runs it.
  - The record of work outside the engine's point 7. Its gate and its stops read as they stand, and point 2 here holds the run to them.
  - Its Implications on a lock move's before-and-after, and the record of what an export reads' on its one filling. Both describe point 5's command.
  - The record of a list's fields' point 2 and the record of ties' point 4. A person's move to such versions stays a finding, and point 7 only says how a person names them.
  - The record of shipped library releases' point 5. "The project removes it" holds. Where no newer version of that major stands, only a hand serves that case, and its finding stays until then.
  - The founding record's point 7, the record of the engine's point 13 and the record of what an export reads' point 5. A new engine reaches a piece at a render a person runs, and the run's render is one (point 2).
- **The use case of putting a figure in a documentation page (UC-094)** needs no edit. The change holds the copy's two sides in every format, and a documentation page that shows a dead image holds no figure to move (point 6). Point 3's way past is a person's word, and variant 6b describes the run without it.
- **The reference pages.** The capability's reference pages on files and checks anchor points of these records, and UC-094 anchors the record of change over time's points 8 and 9, so each may owe answers once the edits land. No page changes its text in this change, since the changes below build what this record decides.
- **The change that builds the proposal** carries out points 1 to 7, and point 11's first and last bullets. It lands after the changes that write a current copy and hold it at the gate (DEC-017, Implications). It names the before-and-after's command, and sets how a person names an edit. It keeps the gate at the export a person runs, apart from what the run shares with it.
- **The change that builds `outdated`** carries out point 8, and gives the fact its new words.
- **The change that builds `prune`** carries out points 9 and 10, and point 11's second bullet. It lands after the change that lets a piece's format take `final` and `published`, or a lock it reads under those states stops it. It adds point 9's automated test. The search's refusal past its bounds tells a person to take out versions no piece needs. That advice stays as it is and does not name `prune`, which spares many of the versions the search tries.
- **A copy's form.** [project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700) decides it, and this record assumes what point 5 lists. A file for each mode, or one for several, leaves the rule, and the before-and-after draws the modes a review tool does not show. A form no review tool draws asks a reviewer to open each side, as a PDF does. Should a form need more of a proposal, that record names the edit to this one, in its own change.
- **A pinned draft and written code.** Their locks go on moving by hand, and `outdated` lists them. Whether the run comes to serve them is left to a later change.
