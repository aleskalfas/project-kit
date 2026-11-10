---
id: DEC-013
title: A shipped library is released on its own, as a release of the capability carried it
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a library the capability ships, such as the foundations, has releases of its own, and a release of the capability releases none. A version is released only as the release that wrote the capability's current version carried it, and names that version as the one it needs. Every released version ships beside the version being built, and the command that brings a library into a project takes the newest released one. For example, a change to the foundations after that release holds their next release back until the capability's version moves again.

## Context

[project-kit#2571](https://github.com/aleskalfas/project-kit/issues/2571) asks when a version of a library the capability ships counts as released, and who releases it, which the record of change over time left open ([visual-communication:DEC-003-change-over-time] points 5 and 6). It also asks how the release the version needs, its number and its hash are fixed, how parallel branches change it, and whether the command that brings it in may replace a copy not yet released. It was asked before the capability's first release, while the version the capability's package metadata carried had been stamped when the capability was created, and no release had written it. A released version of a project's own library names the capability's version installed at its release, which the engine checks and never computes ([visual-communication:DEC-014-own-library-needed-release] point 1).

The answer meets three things outside this record:
- **The version-bump policy** of the repository the capability is authored in ([pkit:PRJ-002]). A release step writes all version state, on the default branch alone, so a branch cannot know the number of the release that will ship it (D1 and D3). The capability's version moves at a release only where a pending changeset declares a change of it an adopter can observe.
- **The check of migrations** (COR-010), which the default branch's required checks run on each change. It reads every rename or removal of a file in a capability's folder as owing a migration, unless the file is a decision record, or lies in a migrations folder or the project's own folder.
- **A library copy,** a released version held whole in a project, which is the project's file and never rewritten while a lock names it ([visual-communication:DEC-001-visual-communication-discipline] point 11).

## Decision

**A version of a library the capability ships is released on its own, as the release that wrote the capability's current version carried it, and ships beside every other released version and the version being built; the command that brings the library in takes the newest released one.**

### 1. A shipped version is released by a release of its own

- **Who and where.** Whoever maintains the capability releases a version of a library it ships, where the capability is authored: where the methodology holds the capability's folder as its source, never as a synced copy. The release takes the steps a project's own library's release takes: it runs the check first, and compares the version with the library's previous release, refusing a break outside a major release (DEC-003 points 6 and 7, [visual-communication:DEC-004-brands-and-notations] point 5).
- **As it stands.** The capability's *current version* is the version its tree carries, as the release step wrote it, when the library's release is made. The release takes the version being built as the default branch holds it, and refuses unless the history shows that no change since the release step's change that wrote the current version has touched the place of the version being built. So the released version is, file for file, the one that release carried.
- **A change since puts it off.** A change to the version being built after that release, a library added since included, puts the library's release off until the next release that moves the capability's version.
- **Its other refusals:** where no release wrote the version the tree carries, as before the capability's first release, and where the version being built carries a number already released.
- **Read in that release.** A version is released only where the tree at the release step's change held the capability's own checks (point 6), so they read it as that release carried it.
- **On released bases.** The release checks the version on the newest released version of each library it builds on, within the majors it names, a base released earlier in the same change included. So no released version rests on a base not yet released, and a base is released before a library built on it.
- **Not by the capability's release.** A release of the capability carries each library as the default branch holds it, released or not, and releases none.
- **Released once it lands.** The version is released, where the capability is authored, once the change that releases it lands on the default branch, and every later release of the capability carries it released.

### 2. The capability ships every released version, and the version being built

- **Every released version** of each library, whole, as it was released, in a place of its own. Its release adds that place, and nothing later renames or removes it.
- **The version being built:** at most one version of each library, which every change to the library goes into. It keeps one place, apart from the released versions, under a name that names no version, so a change of its number moves no file. A library's first version starts it.
- **The library's record and its released places lie outside it,** so the look at the history of point 1 sees only changes to the version being built.
- **While it carries a released number,** it holds that released version's files, but for the release that version needs. It is then that released version, and the command takes the released one (point 5).
- **A record for each library** keeps its released versions, each with its hash, in the shape and with the hash the location's list gives a released version (DEC-003 point 4). The command copies the hash as it is.
- **A release only adds** its released place and its entry in the library's record, renames or removes no file, and changes no other file of the capability's folder, the version being built's included.

### 3. What a release fixes: the release the version needs, its number and its hash

- **The release it needs** is the capability's current version (point 1), which the release writes into the released place. It names no release still to come, never understates what the version needs, and may overstate it, where its tools are older.
- **What that rests on.** The checks at the release that wrote the capability's current version refuse what its engine does not know, rather than pass over it.
- **While it is built,** the version names a release no later than the capability's version its tree carries, so that tree reads it, and it may understate. A project takes it only from an installed capability whose tree reads it (DEC-003 point 5), and its release sets the number.
- **Its number** follows semantic versioning from the newest released version, with the segments DEC-003 point 1 sets, and a library's first version is 1.0.0. The version being built carries the highest segment its changes need: a patch at least, a minor once a change adds or changes a look, a major once a change breaks what the newest release promises (DEC-003 points 6 and 7, DEC-004 point 5).
- **A change raises it.** A change that needs more than the number says raises it. A change to a version being built that carries a released number raises it first, by the segment the change needs. The release raises no number.
- **A break.** Where the version's major has no released version for the capability's own checks to compare it with (point 6), the release's comparison with the library's previous release judges a break. The release shows the segment its comparison finds before it writes anything. Whether a change is a patch or a minor is the owner's judgement.
- **It never falls** below a number a release has carried for the library. The release refuses a number below one the version being built carried at an earlier release, as the default branch's history shows. A number the version being built passed unreleased, once a release carried a higher one, is never released, and the capability ships no version of it.
- **Its hash.** The release writes the hash of every file of the released version, the release it needs included, into the library's record.
- **Content, not version state.** A library's version, the release it needs and its hash are the capability's content, which the library's owner versions, as a schema's version is its schema's. The release step writes nothing for the libraries, and, since the release step alone writes version state, no branch predicts a number ([pkit:PRJ-002] D1 and D3).

### 4. How parallel changes meet

- **Every change declares at least a patch.** A change to a version the capability ships is one an adopter can observe, since the command that brings it in copies it. So it declares at least a patch of the capability under the version-bump policy, never a change that moves nothing, and so does each release of a version.
- **Changes go into the version being built,** never into a released version (point 6). They change its files as they change any file, and move no number but where a change needs a higher one (point 3). Two that raise it to different numbers meet on the line that holds it: the higher holds, and the second to merge reads the version again after its rebase.
- **A library's release and a change to the library merged beside it:** whichever lands second fails, on the capability's own checks (point 6): a change until it raises the number (point 3), or the library's release, which is put off as point 1 says and made again.
- **A library's release and a release of the capability** that lands between its branch and its merge meet in point 6's look at the history. Where the library's release passes it, it names a version of the capability older than the one the tree carries, whose release carried it unchanged.
- **Releases of two libraries** meet nowhere but in the capability's own checks, which read a library with its base (point 6), since each adds its own place and changes its own record. A base and a library built on it that each need the other's new version are released in one change, the base first.
- **As each would merge.** These hold where the default branch's required checks run on each change as it would merge, as a merge queue runs them, the release step's own change included. A change that bypasses the queue is caught only after it lands, by the same checks on the default branch. A release caught so is taken back by a change that removes its place, which meets the check of migrations as any removal in the capability's folder does. Once a release of the capability has carried it, it stays.

### 5. The command that brings a shipped library in takes the newest released version, and brings a copy not yet released up to date

- **By default, the newest released version,** copied whole, checked against the hash in the library's record, and listed released with that hash. The command refuses where the files the capability ships no longer match it.
- **Another version where asked:** any other released version the capability ships, where a person names its number; the version being built, where a person asks for it or the library has no released version, listed not released, with no hash.
- **Every copy of the library, in the same run.** The command writes over a version the project holds only to replace whole, with what the capability ships, a copy the list marks not released whose number it ships, released or being built, or to restore a released copy whose files no longer match its hash. Each run does so for every such copy of the library, and lists a replaced copy released, with its hash, where its number is released. Running it is the consent (DEC-003 point 5), and it names each copy it writes and each piece that locks it.
- **Under a lock that follows, or no longer draws:** an unpinned draft's, which moves at each render, or a final piece's, which draws from its exports ([visual-communication:DEC-002-files-and-validation] point 7). The command replaces a copy not yet released where each lock that names it is such a lock. Where the capability released the copy's number, that mends a final piece's lock without moving it, and where the number is being built, it changes none of the piece's exports.
- **Under a lock that moves only on purpose:** a pinned draft's, written code's or a published piece's (DEC-003 point 8, [visual-communication:DEC-005-engine-and-plugins] point 7). The command replaces a copy not yet released only where the person names each such piece in the command, after the before-and-after its state asks: naming it is the move on purpose, the lock keeps its number, and what it draws changes only then. Otherwise the command leaves the copy as it is, names each such piece and does the rest of its run, and the finding of point 6 stands for that copy.
- **A change the project made in a copy it replaces or restores is lost,** as the project's diff shows: a shipped library changes where it is authored, never in a copy.
- **A released copy is never replaced.** One that matches its hash is not written, and restoring one, as a project may restore a library copy (DEC-002 point 7), needs no piece named, since it brings the copy back to what every lock on it names. Where the hash the capability records for that version differs from the list's, the command refuses.
- **A new number is a new version,** copied beside the others, and replaces none.
- **A number the installed capability does not ship.** A copy not yet released of it stays as it is. A draft that follows moves by itself once the project holds a newer version of its major. Where the capability builds no later version of that major, a person moves each draft that locks the copy, on purpose, to a version the capability ships, by pinning it to that version or by taking the new major. Once no lock names the copy, the project removes it (DEC-003 point 4). A final piece that locks it keeps the finding of point 6.

### 6. What the checks report, and how severely

Under the policy of the record of files and validation (DEC-002 point 7):
- **Fails:** a library version that no longer matches its released hash (DEC-003 point 9). Where the capability ships that version, the finding names the command that brings it in, which restores it.
- **Asks for attention:**
  - a finding inside a copy whose source is the capability, released or not, naming whoever maintains the capability;
  - a copy the location's list marks not released, of a library the capability ships, that is not what the installed capability ships under its number: other files, a released version, or a number it does not ship. The finding names the command that brings the library in, or, for a number not shipped, the way out of point 5;
  - a copy the list marks released whose hash differs from the one the capability records for that version, such as a copy from another distribution of the capability, naming both hashes.
- **The capability's own checks** are its tests in the suite of the repository it is authored in, run on each change as point 4 says. A project's validation never runs them. They:
  - read every component of each version, a brand's tokens and fonts included, through the routine that reads a version in full, so point 3's ground holds for a component no piece places (refinement per [visual-communication:DEC-014-own-library-needed-release]);
  - hold each released version to the hash its record keeps. Read alone, a released version fails them only where it no longer matches that hash, or the engine can no longer read its files (DEC-003 point 3), and any other finding in it is reported and fails nothing (DEC-002 point 7);
  - hold every released version to point 1's condition, from the release step's change that wrote the version of the capability it names up to the change that brings it onto the default branch, that change as it would merge included, read from the tree, its changelog and its history with no diff, so they hold on the default branch too, and fail where that history is not at hand;
  - fail the newest released versions of the libraries the capability ships where the engine cannot read them together, each on the newest released version of each major it builds on;
  - read and check each version being built on the versions being built of its bases, and fail a finding in it;
  - fail a version being built that carries a released number but differs from that version, but for the release it needs, or whose number falls below the newest released one;
  - run the release's comparison of each version being built with the newest released version of its major, and fail a number that does not cover a break it finds. The comparison is a command, never a project's validator (DEC-002 point 7).
- **An engine change that tightens a rule** the engine applies to a library read with its bases lands only once the rule reports what it finds in a version written before, asking for attention, rather than refusing to read it (DEC-003 point 3). The capability's own checks hold it back where the newest released versions no longer read together, and review holds it back where it refuses only an older pair that projects lock. Releasing versions that meet the rule clears the versions the capability ships, never the copies projects hold.

### 7. No project file changes shape, and no release owes a migration

- **No project file changes shape.** The location's list marks which versions are released, with a hash of each, and a library's file names the release it needs, so this record adds nothing to a project's files, and each reads and draws as it did. A copy this record finds in a project stays as it is until a person runs the command (point 5).
- **No migration.** Neither a release nor this layout renames or removes a file (point 2), so the check of migrations finds nothing for them to cover, and they owe none (COR-010). A change that renames or removes a file within a version being built, such as an experimental component removed, meets that check as any such change to the capability's folder does, and ships the capability migration it asks, though nothing installed breaks.

## Rationale

**Why a release of its own, not the capability's.** A library released with the capability would be fixed at every release that moves its version, for a change to any part of it, whether or not its owner judged the library ready. The owner judges a version ready, as it judges a component (DEC-003 point 7), and each shared role added after the foundations' first release costs a default or a major release ([visual-communication:DEC-008-library-role-defaults] point 2).

**Why as it stands.** The release that wrote the capability's current version carried the library's version with all it uses, and its checks read it there, the ground point 3 states, so one look at the history, made again as the release merges, is the whole of *as it stands*. The costs:
- **An overstatement,** met only by a project that moves its capability back below that version, since a project takes a shipped version only from the capability it installed (DEC-003 point 5).
- **Time.** A change reaches a project released no earlier than the release after the one that first ships it, normally one that moves the backbone, the only kind that is tagged, though a draft may take it as soon as it ships.
- **Now and then a release made again,** where a change lands while it waits to merge, which releasing soon after a release of the capability keeps rare.

A slip fails closed: a change wrongly declared to move nothing holds the library's release back, and no number is fixed to files a release did not ship under it.

**Why every released version ships, beside the version being built.** A project that installs the capability while the next version is built needs a released version for a final or a published piece (DEC-003 point 8). A library released on the foundations' first major stays drawable once their second is released, and a piece copied from another project takes the version it locks by the command. The cost is a folder that grows by one version with each release, which every distribution of the methodology carries.

**Why the version being built keeps its place, and changes raise its number.** A number in its folder's name would move every file when it rises, and meet every parallel change. The number cannot wait for the release, since a draft takes the newest version within its major (DEC-003 point 8), so a break must carry the next major before any copy of it is drawn. A number below one a release carried would leave a project's stale copy holding a higher number than the version it should give way to, and its drafts would keep it.

**Why a copy not yet released is brought up to date.** A draft that follows its libraries sees each change at its next render (DEC-003 point 8). A copy not yet released is no library copy (DEC-001 point 11). Were it never replaced, it could not follow the version it locks, and since it may not be removed while a lock names it (DEC-003 point 4), a person would copy it by hand.
- **A replacement moves a copy forward,** since nothing a later release ships under a number is older than what an earlier one shipped under it (points 1, 3 and 4). A project that moves its capability back, or copies from a project on a newer capability, may get older files, as its diff shows, and a draft may lose an experimental component, which any release may remove (DEC-003 point 7).
- **A final piece's lock never moves** (DEC-003 point 8), so no move on purpose is owed it before its copy is replaced.
- **A lock that moves only on purpose** has nowhere else to move, since the released version keeps the copy's number.

**Why a finding inside a shipped version only asks for attention.** The project cannot correct it, since the command writes over a change it made, and failing it would fail every project for a fault only the capability's owner corrects (DEC-002 point 7). A tightened engine rule reports rather than refuses for the same reason, and the checks read only the newest released versions together because a new project locks those together.

**Why inside the capability.** The release step could write the release a version marked on a branch needs, as it writes a floor declared on the release ([pkit:PRJ-002] D4), and spare the wait. Its costs:
- **The tier.** A process belongs to the backbone where the backbone needs it to exist, evolve or ship (COR-010), and releasing a library is the capability's own discipline.
- **The hash** would cover the file the release step rewrites, so either the backbone's release could not complete without the capability's code, which the version-bump policy's backbone-internal release step rules out, or the hash leaves out the release the version needs, so a released version's files could differ from its hash.
- **A third state,** marked but not yet released, which the check, the command and every lock must tell from the other two.
- **A mechanism with one user,** built before any second use (COR-007).

So the releases of the capability and of its libraries meet only through what the release step has already written, which the capability reads and never writes.

### Alternatives considered

- **Every release of the capability releases the libraries it ships.** Rejected, for the reason under *Why a release of its own*.
- **The release step fixes a version marked on a branch.** Not chosen, for the costs under *Why inside the capability*: it would also need a record of policy and one of architecture, both the methodology maintainer's to decide.
- **The library's version declared on each branch, and written at the release.** Rejected: it needs the same seam, to spare raises that meet only where they differ.
- **Released from history, with the number raised where the version changed since.** Rejected: it needs a raise inside the release and a walk over every later release, and would move a later copy back.
- **Released where its files still match what that release carried, though changes touched them since.** Rejected: a release between may have shipped other files under that number.
- **Released at once, naming the first version of the capability after the one its tree carries.** Rejected: that tree, and any install from a commit between releases, would refuse a library whose tools it holds, and the field would gain a second form.
- **Released at once, where the engine finds every tool and field the version uses in the capability's current version.** Rejected: the engine would have to know the release that brought each, which the branch that adds one cannot write.
- **Released at once, naming the oldest release whose own check, run from history, reads the version.** Rejected for now: the release would run an older release's code, with its own dependencies, in a location built for it.
- **The release it needs as the version the capability's package metadata carries at each change.** Rejected: it understates once a release brings tools a library uses ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)).
- **One version shipped, released or not.** Rejected: while the next version is built, a final piece has no released version to lock.
- **Only the newest released version shipped, beside the version being built.** Rejected: each release would remove one, owing a migration though nothing installed breaks, and could leave a library without its base.
- **Projects receive released versions only.** Not taken: a draft could take a change only a release later, and a library with no released version not at all, where a draft may lock one not yet released (DEC-003 point 8).
- **An exemption in the check of migrations for a capability's shipped libraries.** Not chosen here: a layout that only adds needs none, and the backbone's check is the methodology maintainer's to weigh.
- **A migration with each release, which does nothing.** Rejected: every release would owe one, though nothing installed breaks.
- **Released versions kept as tags, fetched whole when a project brings one in.** Rejected: bringing a library in would need the network, and a fetch of its own.
- **A version being built for each major.** Not chosen for now: it lets a fix reach the current major while the next is built, but majors are rare while a library's components are experimental.
- **A pre-release number for each state of the version being built.** Rejected: parallel branches would meet on every number, copies would multiply, and a version would gain a second form.
- **A hash recorded for a copy not yet released, as it is copied.** Rejected: a project changes no shipped library in its copy, and the list's hash would gain a second meaning.
- **The command never writes over a version the project holds.** Rejected: a draft's copy could not follow the version it locks.
- **Under a lock that moves only on purpose, the copy stays until no such lock names it.** Rejected, for the reason under *Why a copy not yet released is brought up to date*: the copy would stay as no release left it.

## Implications

- **Edits to accepted records,** each citing this record. A person accepts each edit (the decisions README, "Refining an accepted record"):
  - DEC-003 point 1: a shipped library's released version names the capability's version current at its release, whose release carried it as it stands, and while it is built a version no later than its tree carries.
  - DEC-003 point 4: the command that brings a shipped library in lists a released version with the hash the capability records.
  - DEC-003 point 5: the capability ships every released version and the version being built, and the command takes the newest released one and writes over a version the project holds only as this record's point 5 says. A copy not yet released is no library copy, so the founding record's protection does not reach it.
  - DEC-003 point 6: whoever maintains the capability releases a shipped version as it stands, where the capability is authored, untouched since the release that wrote the capability's current version, and a change since puts that release off until the next release that moves the capability's version.
  - DEC-003 point 9: the findings of this record's point 6, and none for a shipped version being built that names an older release than it needs.
  - DEC-001 point 11: a version not yet released, held in a project, is no library copy, and the command that brought it in may bring it up to date; restoring a library copy to its released hash rewrites nothing.
  - DEC-002 point 9: no command writes the capability's own folder but the release of a version it ships, where the capability is authored, and restoring a library copy to its released hash is no rewrite of it.
- **The Tasks of #2571** build points 1 to 6: the capability's own checks, the shipped folder, the command that brings a shipped library in, and the release of a shipped version.
- **A project's own library** is released by a command of its own, and DEC-014 decides the release it needs. Should the engine come to know the release that brought each tool and field, the wait of point 1 may give way to it, by a refinement of this record.
- **No change to the backbone's code or policy,** so no project record beside the version-bump policy, and no architecture record. The release mechanics' page names the release of a shipped version among what reads the release step's work.
- **Revisit this record** once the released versions of the libraries the capability ships pass the size the libraries' README names, weighing then a shipped brand's fonts held once, apart from the versions; if the release step changes how it writes a capability's version, or how its changelog records one; if the version-bump policy changes when a capability's version moves; or if the release of a project's own library needs a seam in the release step.
- **Left open:**
  - a fix to the current major while its next major is built, and a fix to an older major once a newer one is released, since one version of each library is built at a time;
  - withdrawing a released version, such as one whose font turns out not to be the brand's to ship (DEC-004 point 9), since nothing removes a released version.
