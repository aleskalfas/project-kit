---
id: DEC-014
title: A project's own library needs the capability's version current at its release
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when a project releases a library of its own, the release of the capability it needs is the version of the capability the project has installed. The command that releases the library writes that number, and no person does. Where the project's copy of the capability is what a release carried, the number never understates what the library needs. It may overstate it: a project on an older release then upgrades before it can read the library. Elsewhere, no version says what the capability holds, so the number may understate, as the methodology's own version may. So a project that takes a library from another repository reads it in full on its own capability before taking it, and refuses what its capability does not know. The engine never works out from a library's contents which release it needs.

## Context

The record of change over time decides what a library's numbers mean ([visual-communication:DEC-003-change-over-time]):
- **The release a library needs** is the oldest release of the capability whose tools and fields it uses. The engine computes it from what the library uses, and checks it against what the library names. A library the capability ships names it by the rule of the record of shipped library releases (point 1).
- **A library copy at a format the capability's schemas do not hold** fails the project's data validation, which the project cannot correct (point 3).
- **A version from another repository** is fetched whole at its release by a command of the capability (point 4).
- **A project's own library** changes freely only in a version not yet released. Releasing a version runs the check on it first, and fixes it (point 6).
- **The release compares** each stable component with the previous release, and refuses a break outside a major release (point 7, [visual-communication:DEC-004-brands-and-notations] point 5).
- **The check fails** a project's own library, not yet released, that names an older release than it needs. It asks for attention on a released library that does so (point 9).

How the capability handles the number today:
- **Written by hand.** A library's file names the release it needs, and nothing computes it.
- **Read against the installed capability.** The check reads the version the capability's package metadata carries. A draft's lock does not move to a version that needs a newer release, and a lock that names one fails.
- **Unknown keys are refused.** The capability's schemas refuse a key or a value they do not declare. The project's data validation checks every file of the format against them, a library copy included.
- **What the schemas leave to the engine** is found only when the engine reads it: the names inside a formula, a brand's token files and Resolver document, which no schema of the capability binds, and a brand's fonts, opened only to lay text out. The check of a version alone judges its own roles and its patterns. It reports a component the engine cannot read only where a piece places it.
- **A finding inside a released version asks its owner for attention,** and never fails ([visual-communication:DEC-002-files-and-validation] point 7).
- **The commands that bring in a library version** refuse one the installed capability cannot read, so such a copy arrives only by hand (DEC-002, Implications).

The record of shipped library releases settles the number for the libraries the capability ships ([visual-communication:DEC-013-shipped-library-releases]):
- **The capability's current version** is the version of the capability its tree carries, as the release step wrote it (point 1).
- **A shipped version names it** when it is released. It is released only where no change has touched it since the release step's change that wrote that version, and the capability's own checks read every version it ships (points 1, 3 and 6).
- **For a project's own library,** it leaves the question to this record and decides nothing of it (Implications).

In the repository the capability is authored in, a version-bump policy frames the numbers ([pkit:PRJ-002]):
- **No branch writes a version.** A release step writes them on the default branch, from the changesets each change declares (D1 and D3).
- **The capability's version moves** at a release only where a pending changeset declares a change an adopter can observe. A new tool or field is such a change. So several releases may carry one version of the capability.
- **The capability has no release yet.** The version its package metadata carries was stamped when it was created (DEC-013, Context).

How a project receives the capability ([pkit:ADR-065-upgrade-runs-the-transition] point 12):
- **A tagged install** ties each version of the methodology to one content, as a release carried it. The methodology's CLI reference recommends it.
- **An untagged install,** from the default branch or another branch, carries the last release's version over files that may be newer. No version vouches for its content, and nothing checks whether an install is tagged.
- **Sync copies the running install's capability** over the project's copy where the two versions are equal. So a sync from an untagged install writes newer files under the version a release wrote (the lifecycle README, "The downgrade guard on capability refresh").
- **A capability's version reaches a project on a tagged install** only with a release of the backbone, the only kind that is tagged.

The plan for released libraries asks how the release a project's own library needs is computed, with no branch writing the number of a release still to come ([project-kit#2612](https://github.com/aleskalfas/project-kit/issues/2612)). Three ways were known:
- **The installed capability's version.**
- **A table of the release that brought each tool and field,** written by the release step.
- **The oldest release whose own check, run from history, reads the library.**

## Decision

**The release a project's own library needs is the capability's current version in the project when the library is released. The command that releases the library reads every component of the version first, then writes that number. Where the project's copy of the capability is a release's content, the number never understates. Elsewhere it vouches for nothing, as no version there does. So the command that fetches a version from another repository reads it in full first, and refuses what the installed capability cannot read. The engine computes no release from what a library uses, and the release step writes nothing for a library.**

### 1. The release a version needs is the capability's current version, written by its release

- **Written by the library's release.** The command that releases a version of a project's own library writes the capability's current version as the release the version needs. It writes it into the version's file before it computes the version's hash, so the hash covers it. No person writes it.
- **The capability's current version** is the version the capability's package metadata carries in the project's tree (DEC-013 point 1). Where the project installs a capability that has had a release, the release step of the repository the capability is authored in wrote it.
- **Read in full first.** Before it writes, the command checks the version as DEC-003 point 6 asks. It reads every file of the version, reads every component and the brand's tokens as the engine reads them, and opens each font it holds as the engine opens it. It computes no scene. It refuses a finding that fails. So the version uses no key, value or name the installed capability does not know.
- **While a version is built,** it names any release the installed capability reads. Its release replaces that number.
- **Never computed from use.** The engine knows the release that brought no tool and no field. The check judges by the number a library names whether the installed capability reads it. Only the commands that release or fetch a version also read it in full (point 4).

### 2. Where the project's copy of the capability is a release's content, the number never understates

- **When that holds.** The project's copy holds the capability as a release of the methodology carried it, as a tagged install's sync or upgrade last wrote it (Context). Once a release of the capability has written its version, the release that wrote it carried every tool and field that copy holds. A later release that carried it under the same version shipped only changes declared to move nothing. A new tool or field is a change an adopter can observe, which moves the version ([pkit:PRJ-002]).
- **Why that is enough.** The command read the version in full on that copy (point 1). So the version uses only what the release that wrote the number carried. The number covers what the capability's tree holds, the dependencies its scripts pin included.
- **It may overstate.** A library that uses only older tools still names the newer version. For a project on an older release, the fetch refuses it and names the upgrade (point 4). A copy made by hand fails as point 5 says. The project reads the library once it upgrades. On a tagged install, that is an upgrade of the methodology, since a capability's version reaches it only with a release of the backbone. A project that pins its methodology's version moves its pin first.

### 3. Elsewhere, the number vouches for nothing, as no version there does

- **Where.** Wherever the project's copy of the capability may hold files newer than its version:
  - an untagged install, or a sync from one, which writes newer files under an equal version;
  - the repository the capability is authored in, whose tree holds every change merged since the release that wrote the capability's current version;
  - before the capability's first release, anywhere, since no release wrote the version it carries;
  - and wherever a change that added a tool was wrongly declared to move nothing.
- **What the command does.** It names the capability's current version there too. It cannot tell whether the project's copy is a release's content, since nothing checks whether an install is tagged. Its reference tells an owner who releases a library for other projects to sync from a tagged install first.
- **Who meets an understated number.** A project whose copy of the capability lacks a tool the library uses: at an older version, or at the same version holding a release's content. The project that owns the library reads it on a copy that holds every tool it uses, until a sync rewrites that copy (point 4).

### 4. A version from another repository is read in full before it is taken

- **The fetch reads it first.** The commands that bring in a library version already refuse one the installed capability cannot read (DEC-002, Implications). The command that fetches a version from another repository (DEC-003 point 4) reads it in full to judge that, as the library's release does (point 1). It reads it on the newest version the project holds of each major it builds on, and on the versions fetched in the same run.
- **What it refuses.** First a number newer than the installed capability. Then anything the installed capability does not know: a key or a value its schemas refuse, a name in a formula, a token's type, a feature of a Resolver document, or a font the version holds that it cannot open. It names each one, and says to upgrade the capability. Any other finding of the read keeps the fix and the level the check gives it. A font the brand names by hash, which the project commits itself, is such a finding: the project's to add (DEC-004 point 9).
- **So an understated number stops at the fetch,** on any install, whatever made it understate.
- **What remains open:** a version copied in by hand, and a copy of the capability that a sync rewrote at an equal version, to a release's content that lacks a tool a version uses. That version may be one the project fetched, or one of its own it released on the copy before. Its capability then meets what it does not know:
  - **A key or a value its schemas do not declare.** The project's data validation fails on the library copy, as it fails on a copy at a format it does not hold (DEC-003 point 3). The project upgrades the capability, or removes the copy once no lock names it (DEC-003 point 4).
  - **What the schemas leave to the engine:** a formula's names, a brand's tokens and Resolver document, or a font. The check reports what it cannot read, where it reads it. Inside a released version, that finding asks for attention (DEC-002 point 7). It names the upgrade beside the owner, since a version the command released carries nothing its owner's capability refused. A formula's value computes as zero, and a role read from an unknown token has no value.
- **Mostly bounded by the lock.** A lock moves only under a person's eye: a draft's at a render its author sees, a published piece's through a reviewed before-and-after, and a final piece's never (DEC-003 point 8). So a piece meets a version copied in by hand only where a person takes it, with the finding beside it. A sync that rewrites the capability changes what a lock already names, with nobody taking anything. Its remedy is a sync from the install whose files held the tool, or an upgrade once a release ships it.

### 5. The check reads the number, and computes no need

- **No finding of a need understated.** The engine computes no need, so the check reports no library that names an older release than it needs, released or not (DEC-003 point 9).
- **What still fails:** a library version the project holds that needs a newer release than the installed capability reads, and a lock that names one. The number in a released version is no fault in it. The project corrects the finding by upgrading, or by removing a version no lock names (DEC-003 point 4). So it fails, and names the project, never the library's owner, released version or not (DEC-002 point 7). A released version whose files no longer match its hash fails too, which covers a number changed after the library's release (DEC-003 point 9).

### 6. What this changes, and what still holds

- **The record of change over time's point 1** loses the oldest release, and the engine's computation. A library names a release of the capability: a released version of a project's own library names the capability's version current at its release. The engine checks that number against the installed capability, and computes none.
- **Its point 4:** the fetch of a version from another repository reads it in full first, as point 4 here says.
- **Its point 6:** releasing a project's own library reads every component of the version, and writes the release it needs.
- **Its point 9** loses both findings of a library that names an older release than it needs. It says that a held version needing a newer release than the installed capability reads fails, released or not, and names the project (point 5).
- **The wait of the record of shipped library releases' point 1 stands, unrefined.** That record lets the wait give way only once the engine knows the release that brought each tool and field. This record leaves the engine without that knowledge.
- **No project file changes shape.** A library's file already names the release it needs, and every file a project holds reads as before.
- **No change to the backbone.** The release step writes nothing for a library. The command reads only the version the release step wrote into the capability's package metadata.

## Rationale

**Why the capability's current version.** It is a number a release of the capability has already written, so no branch predicts one ([pkit:PRJ-002] D1). It vouches for the library exactly where a version vouches for the capability's content: a copy a tagged install wrote, of a released capability ([pkit:ADR-065-upgrade-runs-the-transition] point 12). It needs no table, no older code, no new number and no seam in the release step. Go's module file starts the same way: `go mod init` writes the version of the Go toolchain that runs it.
- **It is the release the owner saw.** The owner checked the library, and reviewed its look, on that release. An older release that reads the library may still draw it differently, since read is not drawn the same (DEC-003 point 2). The number keeps every project off releases older than the one its owner reviewed the look on.
- **What the overstatement costs.** The owner's own pieces read the library whatever the number says, so the number's only readers are the projects that take the library. Each one on an older release upgrades its methodology before it reads any release of the library, a fix included. One that pins its version moves its pin first. Go eases the same cost by fetching the newer toolchain itself, which the methodology does not do.
- **What it gives up.** A way that knows the release of each tool would give three things this one lacks. A project on an older release could read a library that uses only older tools. The owner's own check could find a number that understates. And a number released from an untagged install, or where the capability is authored, could still be right. The Alternatives weigh what each such way costs.

**Why the command reads every component first.** The release rests on the version using only what the installed capability knows. The check of a version alone reports a component the engine cannot read only where a piece places it. So a component no piece places could use a name the capability lacks, unreported. Reading every component, as the engine reads it, makes the release's own check refuse it. No scene is computed, since a component that draws only an item of a list has no scene of its own.

**Why the fetch reads the version in full.** The number cannot vouch for every repository a library comes from (point 3). Reading the version on the installed capability asks that capability itself whether it reads the version, at the one moment the project takes it. It runs no older code and needs no table. It catches an understated number however it arose, with a message that says to upgrade. It extends a refusal the fetch already makes, from the number and the schemas to everything the engine reads. It changes no severity: a command refuses, and validation still only reports a fault inside a released version. The number still refuses first, so a project takes only a version on the release its owner reviewed it on, or a later one.

**Why no wait where the capability is authored.** The number vouches for nothing there, as on an untagged install. A wait like the one for shipped versions would need more than it has:
- **A check that read the version at that release.** The project's validation at the release step's change reports a component the engine cannot read only where a piece places it. So it cannot vouch for the version's names.
- **A check of history on every later change.** A shipped version has the capability's own checks, which hold every released version to the wait as each change would merge (DEC-013 point 6). A project's validation reads no history.
- **A release that moves the capability's version.** A change to a project's own library declares no change of the capability, so its wait would end only when an unrelated change moves that version.
- **Few readers, and the fetch.** That repository's own pieces read its libraries on a tree that holds every tool. Its own libraries are kept, never shipped ([pkit:PRJ-012-showcase-deck] point 3). A project that takes one anyway reads it in full at the fetch, at its own version or an older one (point 4). A shipped version reaches every project that installs the capability, through a command that trusts its number, which is why its wait is worth its cost there.

**Why the check loses the findings of a need understated.** Both need the computation this record does without. The finding on a version not yet released guarded a number its release would fix, and the release writes the number. A released number is fixed by its hash. The loss: the owner's own check no longer finds a number that understates. A project on an older release meets it at the fetch instead (point 4).

**Why no table of the release that brought each tool and field.** It would give the oldest release, the owner's finding of an understated number, and a number that vouches everywhere. A branch writes each row naming the version its tree carries, and the release that ships the tool fills it, or the engine reads it as later. A version whose tools all have filled rows is released at once; one that uses a row not yet filled is refused, on any install. Go keeps such a list of when each name of its standard library came, which its release completes, and checks no widening. Its costs:
- **A row and a detector for every addition.** Each change that adds a tool, a field or an accepted value writes a row. The engine needs a detector that finds each row's use in a library. A row or a detector missed understates, and nothing reports it.
- **Widenings are no name.** Take a field that accepts a value it refused before, or a key allowed in a file where it was not. Neither has a tool or a key to list, so each needs a detector of its own.
- **Who fills a row.** A branch cannot write the release's number (PRJ-002 D1). Either the release step writes it, a seam in its release step, or a later change of the capability fills it from the changelog.
- **The seam.** The release step would carry a process the backbone does not need, built for one user (COR-007). The record of shipped library releases weighs the same tier and the same single use (DEC-013, Rationale, "Why inside the capability").
- **The wait stays.** A library that uses a tool not yet released waits for the release that ships it, wherever it is released.
- **What it would add to the fetch's read:** only that a project on an older release could take a library whose number overstates. The fetch already stops every number that understates, but in a copy made by hand or rewritten by a sync.

**Why no level of additions.** A number in the capability's tree, raised by each change that adds a tool, field or accepted value, would vouch on any install too. Its costs:
- **A fourth number,** in a field that every library's file then names, beside or in place of the release it needs (DEC-003 points 1 and 3).
- **History on every branch.** A branch raises the level only above the last level a release carried, so it must read the default branch's history.
- **A fingerprint to enforce it.** The capability's own checks would tie the level to a fingerprint of everything a library can use. A name outside the fingerprint would understate, and nothing would report it.

### Alternatives considered

- **The oldest release, from a table the release step fills.** Not chosen (Rationale). A branch would write each row with a word, which the release step replaces by the version it writes for the capability. It does so for a declared floor ([pkit:PRJ-002] D4). It would need a project record of policy beside the version-bump policy, or a refinement of its D4. That record would decide that a release writes content derived from the version it writes, for a capability that declares it. It would also need an architecture record of the mechanism: how a capability declares it, what the release step writes, and what a failure holds back. Both would be the methodology maintainer's to decide.
- **The oldest release, from a table a change of the capability fills after each release.** Not chosen. Each row names the version its tree carried when the tool came. The engine reads such a row as the first release after that version, and fills nothing before a release has. It needs no seam, but keeps every other cost of the table (Rationale).
- **A level of additions, raised by each change that adds to what a library can use.** Not chosen (Rationale).
- **The oldest release whose own check, run from history, reads the library.** Rejected. It is exact, widenings included, but runs the capability's code of each release tried, with that release's own dependencies, in a location built for it. In a project that installs the capability, that code must be fetched, so no library's release runs offline. The fetch's read asks the one release that matters to the project taking the version: its own.
- **The fetch refuses by the number and the schemas only,** as the record of files and validation has it. Rejected. An understated number would pass it. A formula's value would then compute as zero, and a role would go without a value, with only a finding that asks for attention.
- **The number trusted where the installed capability meets it, and the version read in full where it does not.** A version whose number is newer than the installed capability would be taken where the read passes, at the fetch, in the check and in a draft's lock. Not chosen. It would spare the overstatement's upgrade. But the number would become a release known to read the version, not the release it needs, and the check would read such versions in full on every run. A project would also take a library on a release its owner never reviewed it on (Rationale).
- **Where the capability is authored, a wait until a release of the capability has read the version,** as a shipped version waits. Not chosen (Rationale). The project's validation does not report every component it cannot read, reads no history, and the wait would hang on unrelated changes.
- **Where the capability is authored, a release that names the current version only where the capability's schemas and engine are untouched since the release that wrote it.** Not chosen. It would make the number right there more often, and still wait for a release that moves the version otherwise. Which files define what a library can use is a judgement the record cannot fix for good. The fetch already stops what it would prevent.
- **Where the capability is authored, the check of the release that wrote the current version, run from history on the version as it stands.** Not chosen. It runs older code, for a number few read, and the fetch stops what it would prevent.
- **Where the capability is authored, no release of a project's own library.** Rejected. A final or published piece locks only released versions (DEC-003 point 8), and that repository may hand out its own.
- **A lock fails where it names a released version that the installed engine cannot read in full.** Not chosen here. It would close the case point 4 leaves open: a copy made by hand, or one a sync rewrote. A version the command released carries nothing its owner's capability refused, so such a fault means a number that understates, and the lock is the project's to move. Its cost is small: the check of a version alone already reads each component, and drops what it finds where no piece places it. Reporting that comes first, and is left open below; failing the lock on it can follow.
- **The check of a version alone reports what it finds in a component no piece places,** asking for attention in a released version and naming the upgrade. Not chosen here. It would make point 4's open case visible, and a version not yet released would fail on it. It changes the check beyond the question of this record, so it is left open below.
- **The owner names an older release by hand,** as Go lets an author lower the version in a module file. Rejected. Nothing checks that the older release reads the library. So the number would give up point 2's guarantee where it holds, on a copy a tagged install wrote.
- **The first release after the version the tree carries.** Rejected, as the record of shipped library releases rejects it. The tree that releases the library carries the version before, and would refuse a library whose tools it holds. The field would gain a second form (DEC-013, Alternatives).
- **The command warns where the project's copy may not be a release's content,** by comparing the copy with the capability a tagged install carries. Not chosen for now. The install that runs the command may be untagged, and a sync from another install may have written the copy. It would serve only an owner who releases for other projects, and the fetch stops what it would warn of.

## Implications

- **Edits to accepted records,** each citing this record once it is accepted. A person accepts each edit (the decisions README, "Refining an accepted record").
  - **Refined in place, not superseded.** The record of change over time's decision stands: a library names a release of the capability, the installed capability checks it, and an older engine refuses it. This record changes how the number is found, and narrows what the check computes, so its edits to that record are refinements in place.
  - **On top of the edits of the record of shipped library releases,** where those land first in the same points. Point 1's rule for shipped libraries and this record's rule then name the same number, and the edit may fold the two together.
  - The record of change over time:
    - point 1: a library names a release of the capability. A released version of a project's own library names the capability's version current at its release, as this record's point 1 says. The engine checks the number against the installed capability, and computes none.
    - point 4: the fetch of a version from another repository reads it in full on the installed capability first, and refuses what it cannot read.
    - point 6: releasing a project's own library reads every component of the version, and writes the release it needs.
    - point 9: neither finding of a library that names an older release than it needs. The bullet the record of shipped library releases adds there, that a shipped version being built raises no such finding, goes, since no such finding is left to exempt. A held version that needs a newer release fails, released or not, and names the project, which upgrades.
    - its Rationale's sentence on the three numbers, which likens the release a library needs to the oldest compiler release a package needs.
  - The record of shipped library releases:
    - its Context's account of the release a library needs, as the record of change over time's point 1 then reads;
    - point 6: the capability's own checks read every component of each version they read, the brand's tokens and fonts included, as this record's point 1 reads it. So point 3's ground holds for a component no piece places;
    - its Implications' paragraph on a project's own library, which names this record instead of leaving the question open.
    - Its point 1 needs no edit, and its clause to revisit it, if a project's own library needs a seam in the release step, does not fire.
- **The Tasks of #2571 it implies:**
  - **The command that releases a project's own library,** which waits for this record and for the comparison ([project-kit#2609](https://github.com/aleskalfas/project-kit/issues/2609)). It reads the version in full on the installed capability, as point 1 says, and refuses a finding that fails. It runs the comparison with the previous release, and refuses a break outside a major release. It writes the capability's current version as the release the version needs, computes the version's hash, and lists the version released with that hash. Its reference says to sync from a tagged install before releasing a library for other projects. The advice does not apply where the capability is authored, whose sync copies nothing into its tree ([pkit:ADR-059-methodology-source-repository] point 2). The capability's reference of files, and the description of the field in the library schema, say what the number holds.
  - **One routine reads a version in full,** for the library's release, the fetch and the capability's own checks of shipped versions. Three readers that drift apart would weaken the fetch's guard (COR-007).
  - **The capability's reference,** where a changeset's author reads it, says that every change that adds a tool, a field or an accepted value declares at least a minor of the capability. Point 2 rests on that declaration.
  - **The check:** a held version that needs a newer release than the installed capability reads fails, released or not, and names the project, which upgrades (point 5). The check gives that finding on a released version to its owner, which the Task mends.
  - **The capability's own checks of shipped versions** read every component of each version as point 1 here reads it, as the edit to DEC-013 point 6 says.
- **The command that fetches a version from another repository,** in the Task that builds it, reads the version in full first, and refuses as point 4 says.
- **No project record beside the version-bump policy, and no architecture record.** The release step writes nothing for a project's own library, and no command reads history.
- **Revisit this record:**
  - if the engine comes to know the release that brought each tool and field. The oldest release could then replace the current version, and the wait of DEC-013 point 1 might give way with it;
  - if projects on older releases come to take shared libraries often enough that the overstatement's upgrades cost more than a table would;
  - if the backbone comes to record whether a capability's copy is a release's content, or sync stops copying at an equal version. The command could then warn where the number may understate, and point 3 shrink;
  - if the CLI reference stops recommending a tagged install, or the version-bump policy changes when a capability's version moves.
- **Left open:** whether the check of a version alone reports what it finds in a component no piece places, and then whether a lock fails on it. Either would make point 4's open case visible: a copy made by hand, or one a sync rewrote.
