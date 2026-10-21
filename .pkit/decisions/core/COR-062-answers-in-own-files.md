---
id: COR-062
title: A change's answers live in files of its own
status: proposed
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

COR-050 has a change answer friction in the artefact it answers. A revalidation goes in the artefact's `revalidated` block, a deferral in that block's `deferred` list, and a revisit entry in its `revisited` list. The answer sits beside the text it justifies, and the checks need nothing but the repository.

Two changes that revalidate one artefact rewrite the same lines of that block. Git cannot merge them, so whichever lands second is in conflict.
- **The host.** A host merges with git's own merge, on its own side. It runs no merge tool a clone registers, and many hosts run no checks on a change in conflict.
- **The round.** Someone merges the base in by hand, resolves the block, writes the answer again and waits for the checks. COR-050 point 3 asks whoever resolves the conflict to revalidate the combined state, so the round also forces that judgment.
- **The cost.** A few documents that many changes answer on, such as a command reference, put almost every open change in conflict after each merge. The rounds run one after another, and most conflict only in answers.

Git merges two changes cleanly where each adds a file at a path no other change writes. It conflicts where both edit the same lines. It may also pair a removed file with a similar added one, as a rename. So on a host, the only answer that never conflicts is one written to a path no other change writes.

## Decision

**A change writes its answers to friction in new files of its own, outside the artefacts they answer, and never in a pull-request description. A change that answers only adds such files. Each answer names the other answers on its artefact that it read, and replaces what it read by its kind. Two revalidations of one artefact, neither of which read the other, were made apart. Their combined state is reported as debt until a revalidation that reads both judges it. This record partially supersedes COR-050.**

In short, answers no longer conflict, because no two changes write one file. The judgment a conflict forced, of the combined state, moves to the next change that answers on the artefact. Until then it shows as debt. Anchor lists and bodies still conflict as before.

Four terms recur:
- An **answer file** holds a change's answers (point 1).
- The **answer folder** holds the answer files (point 2).
- An answer on an artefact is **live** while it answers something and no answer that read it replaces it (point 5).
- Two live revalidations of one artefact, neither of which read the other, were **answered apart** (point 7).

### 1. Answers live in answer files

A change writes its answers to friction in an answer file: a file in the answer folder, under a name no other change uses.
- **What it holds.** For each artefact it answers, the artefact's location and the answers on it. Those are a revalidation (COR-050 point 3), deferrals (point 4) and revisit entries (point 16). A document is named by its path. A collection entry is named by its file's path, `#` and its id.
- **Its keys** are COR-050's: `at`, `outcome`, `unchanged-because`, `deferred` and `revisited`. Each answer adds `supersedes` (point 4). Their layout belongs to the schema the backbone ships.
- **What stays in the artefact.** Its block keeps its anchors, its reason for having none and the tool-written status (COR-050 points 1 and 10). It holds no answer. An answer left in it is read only in history, for its points (point 6), and validation finds it (point 10).
- **What the checks read.** Both checks, the debt listing and the explanation read an artefact's answers from the answer files. The change check reads the answers a change wrote from the answer files its diff adds. Its machine-readable output lists them, each with its words, for the reviewer of COR-050 point 3.

### 2. The answer folder

The answer folder sits at one path on the project-owned side of the methodology's tree, named for the functionality.
- **One path everywhere.** The backbone fixes the path. It is the same in every project, and no setting moves it (COR-048 point 2). So a reader finds the answers at any commit without reading that commit's settings.
- **The project's own.** The answers are the project's. No sync reads or writes the folder, which is never a synced tree (COR-050 point 14). The backbone's writers write in it on the project's behalf, as they write in an artefact's block.
- **No artefact.** The folder is never a place. No place reads an answer file as an artefact, whatever the place covers, as no place reads a held document (COR-050 point 1). Neither measure counts an answer file, and the declared surface leaves the folder out (COR-050 point 8).
- **No anchor stands on an answer file.** What a path anchor, or an anchor of a registered kind, stands on leaves out every answer file. Otherwise each answer would flag every artefact with a path anchor over the folder. Their own answers would add files there, which would flag them again, without end. An anchor that matches only answer files is dead, as one matching only excluded paths is (COR-050 point 7).

### 3. A change that answers only adds files

- **Adding.** A change writes its answers only by adding answer files. It may rewrite an answer file it added, since its base does not hold that file.
- **What it leaves alone.** It rewrites no answer file its base holds. A change that removes answer files adds none: it prunes, or it reverts (point 8).
- **The finding.** The change check finds a change that rewrites an answer file its base holds, or that removes one and adds one. It fails on it in enforcing mode, as on friction (COR-050 point 12).
- **A file put back.** A change may add an answer file with the path and the content that its base's history held. That puts back an answer as it was, and writes no new one. So point 4 does not apply to it, and the change check does not list it among the change's answers. Its values keep their points (point 6).
- **A cherry-pick** carries an answer file unchanged, or leaves it out and writes that line's own answer in a new file. So one path never holds two contents.

### 4. Each answer names what it read

- **What it names.** Each answer on an artefact names, in `supersedes`, every other answer file that holds an answer on that artefact. Those are the files present in the tree of its change's own head, whether their answers are live or not.
- **The change's own head.** That tree is the head's, not the merge a host or a queue builds of the change with its base. So an answer landing on the default branch in parallel never fails the change's checks. The change check judges `supersedes` against the change's own head wherever it runs (COR-050 point 6).
- **A merge of the base.** A change that merges its base in brings the answers other changes landed into its head. Its answers on those artefacts then name them, and so take on the combined state. A change stacked on another names its parent's answer files.
- **Present, not only live.** Naming only live files would bring a replaced answer back when a middle one goes. Take answers X, Y and W, where Y read X and W read Y. Were W to name only Y, removing Y would leave X live beside W.
- **The findings.** The change check finds an answer whose `supersedes` leaves out such a file, and fails on it in enforcing mode. A name of a file the head does not hold names nothing. Two answers that each name the other's file have read neither, so validation fails the pair.

### 5. What an answer replaces

An answer on an artefact is live while it answers something and no other answer replaces it. Replacing it takes naming its file, by a name that history agrees with.
- **By kind.**
  - A revalidation replaces the revalidations it read. It also replaces each deferral it read that it does not re-state.
  - A deferral replaces only the deferral of its own anchor that it read.
  - A revisit entry replaces only the entry for its own target that it read.

  So an answer that only defers need not re-state a revalidation to keep it.
- **What no longer exists.** An answer on what its artefact no longer holds answers nothing, and is not live. Such are a deferral of an anchor the artefact no longer declares, and a revisit entry for a target no link of the artefact takes. So is an answer whose location holds no artefact (point 10). Pruning removes their files (point 8).
- **Names that history agrees with.** A name in `supersedes` is honoured only where history agrees with it. The file it names must have been added in a commit that first carried the name, or in an ancestor of one. A name first carried on two lines of work, as after a cherry-pick, needs this of one of them. Any other name is void, and what it named stays live. A void name errs toward more friction, never less.
- **Reaching a deferral.** A revalidation reaches a deferral (COR-050 point 4) only where it keeps the deferral itself, or read the file that holds it. Ancestry is not enough. After a squash, ancestry would let it reach a parallel deferral nobody read.
- **No rubber stamp.** An `unchanged-because` must differ from that of each revalidation it read on its artefact (COR-050 point 3). A revisit entry's reason must differ from that of each entry it replaces (COR-050 point 16).

### 6. Each value keeps its point across homes

- **One history, two homes.** The revalidation point of an artefact is the commit where its answers first carried the parsed value of `at` (COR-050 point 3). Its answers are those of the answer files that name it, and, in history, those its own block carried. A value first carried in one home keeps its point when it moves to the other, or to another answer file. So does a deferral, by its anchor and reason (COR-050 point 4).
- **What relies on it.** Moving every answer out of the blocks moves no point. Nor does putting back an answer file, or writing back a value the artefact's answers carried before.
- **How far back.** The history is read back to where the artefact was last added, its file or its entry, renames followed (COR-050 point 3). It is not cut where an answer file was added.

### 7. Two revalidations made apart are debt, not a conflict

Two live revalidations of one artefact, neither of which read the other, were answered apart. Nobody has judged their combined state.
- **Any two.** Every such pair is answered apart, whichever anchors each answered. Telling whether both changes moved one anchor needs each change's bounds, and a rebase-merge or a direct push loses them. It would also miss two `updated` edits whose bodies merge cleanly.
- **Measured as before.** An anchor has changed only where it differs from what it stood on at each live revalidation. That is how COR-050 point 3 measures points on lines of work apart. The finding, not staleness, carries the unjudged combined state.
- **Debt, cleared by the next revalidation.** The whole-repository check reports each artefact answered apart as debt, from the first commit that holds both revalidations. The debt listing shows it, with that commit's author, date and change (COR-050 point 9). The tool-written status records it as stale, from that commit (COR-050 point 10). The next revalidation on the artefact reads both, judges their combined state and replaces them.
- **Told before the merge.** For each artefact a change revalidates, the change check reports each live revalidation on its base's tip that the change's answer did not read. Merged, the two would be answered apart. The person who authorises the merge is told of it with the change's answers, as information, not a gate (COR-050 point 3).
- **Never a failure.** Neither check fails on it, in any mode. A component through which a change's merge is authorised may choose to stop on it. Such a stop would bring back the round this record removes.

### 8. Removing answer files: pruning and reverts

- **Pruning.** A change of its own removes answer files in which no answer is live. A prune removes files and adds none. It changes no live answer, so it owes nothing and flags no dependant. A writing command prunes, and names what it removes (COR-050 point 13).
- **What stays replaced.** An answer stays replaced while an answer that read it is present. So a prune, a revert or a file put back brings back no answer that a present answer read. Where every answer that read one is gone, it may come back beside later answers. They are then answered apart (point 7), which errs toward more friction.
- **A revert.** Reverting a change removes the answer files it added. An answer they replaced is live again, as a value written back is (COR-050 point 3). So the change check judges the artefact against that answer's points, as COR-050 point 6 judges a written-back `at`. A revert that owes nothing then only removes.
- **A revert that owes an answer** keeps the answer files it would remove, and its new answer names them. So it only adds, as point 3 asks. Kept, they stay until a prune.
- **The cost.** Reverting the only answer that read a pruned file can leave the artefact with no live revalidation. Its revalidation point is then the commit that first introduced its block, as for an artefact with no `at` (COR-050 point 3). That over-reports, toward more friction, never less.

### 9. An artefact received by sync owes no answer

An artefact a project receives by sync, such as a rule of a method rule set (COR-051 point 2), owes that project no answer.
- **Why.** Its answers live in its source's answer folder, which no sync carries (point 2). So a project never answers on a file it does not own.
- **As for an excluded path.** Neither check asks the receiving project for an answer on it, or reports it stale there. That is how COR-050 point 7 treats an artefact under an excluded path.

### 10. Whose file, and what each finding is

- **A writer's own file.** A writer writes only into an answer file it can tell is its own change's. It never writes into one another line of work added, a parent's on a stacked branch included. It refuses where two files it could call its own would each answer one artefact. Each would then have to name the other (point 4).
- **A moved artefact.** An answer names its artefact by location. Where a parallel change moved the artefact, the checks follow the move, as they do for its revalidation point (COR-050 point 3). The two changes' revalidations were then answered apart (point 7), so the debt shows. `supersedes` follows a move the same way, or a moved artefact's earlier answers could never be pruned.
- **What validation fails:**
  - an answer file that cannot be read, or that names no artefact, since it answers nothing
  - two answers that each name the other's file (point 4)
  - a second entry for one target within one answer (COR-050 point 16)
  - an answer in an artefact's own block (point 1). In a file the project receives by sync, it is reported, never failed, since the project cannot mend it there.
- **What the change check fails on,** in enforcing mode, beside COR-050 point 12's findings:
  - a change that rewrites an answer file its base holds, or that removes one and adds one (point 3)
  - an answer whose `supersedes` leaves out a file (point 4)
  - a deferral or a revisit entry the change writes that names no anchor or target of its artefact
- **What is reported only,** in every mode:
  - an artefact answered apart, as debt in the whole-repository check, and on the base's tip in the change check (point 7)
  - an answer that answers nothing because what it names is gone (point 5). Pruning removes it.

### What this overturns, and what stands

This record partially supersedes COR-050. Each overturned passage stays in COR-050 as it stood.
- **Overturned:**
  - in the lead, "The answer to friction lives in the artefact itself". Its second half, "never in a pull-request description", stands. So does the lead's "and when it was last revalidated", read as what the artefact's answers record.
  - in the lead's second paragraph, recording "on the artefact" why a target stands. The entry is among the artefact's answers (point 1 here).
  - in the definition of the revalidation point, the artefact's own `at` as the only home of the value (point 6 here)
  - in point 1, that each artefact carries its own revalidation, and that everything COR-050 owns in an artefact sits in its block. The block keeps the rest (point 1 here).
  - where points 3, 4 and 16 put answers: the `revalidated` block, its `deferred` list and the `revisited` list. With it go the rules that follow from that home:
    - the artefact's file as the only history of its answers (points 3 and 6)
    - entries kept sorted so that parallel branches merge cleanly (points 4 and 16)
    - a revalidation rewriting the block (point 4), and an entry staying until a later change rewrites it (point 16)
  - point 3's rule that whoever resolves two conflicting revalidations judges their combined state, and point 16's "Conflicts" rule for revisit entries. Two answers made apart are reported instead (point 7 here).
  - what an `unchanged-because`, and a revisit entry's reason, must differ from (point 5 here)
  - point 4's "reaches", read through what a revalidation holds or read (point 5 here)
  - point 4's "Removing an anchor removes its entry" and "Removing the artefact … removes its entries", with the validation error on a dangling entry. An answer on what is gone is no longer live (point 5 here).
  - in point 16, validation failing an entry that names no target, and a second entry for one target written apart (point 10 here)
  - in point 12, that enforcing mode fails on the first six findings alone. It also fails on those of point 10 here.
  - in point 6, the artefact's own file history as all the change check reads behind the base. It reads the answer files' history too.
  - in the Rationale:
    - "Why the answer lives in the artefact", where it puts the justification next to the thing it justifies
    - in "Why deferrals are per anchor", that reasons merge cleanly because each has its own line
    - in "Where the two checks part", the case of a conflict resolved by keeping the line of work's revalidation
    - in "Why a path anchor stands on the content of a file a place holds", that each sync bringing its source's revalidation flags the path anchors on a received file
  - in Alternatives, "in favour of revalidating the combined state", on keeping either timestamp of a conflicting revalidation
  - in Implications, a component that withdraws a link removing the entries that would dangle. Those entries answer nothing (point 5 here).
- **Stands:**
  - anchors, their kinds and parts, and what each stands on (points 2 and 5)
  - the three answers and what clears friction (point 5), read from the answer files
  - who decides an answer, what the reviewer checks and what the person is told (point 3)
  - the revalidation point read from git, and a value written back keeping its point (point 3)
  - deferrals per anchor, re-stated by a revalidation that keeps them (point 4)
  - links and what they ask (point 16), the reason staying among the source's answers
  - both checks, the measures, the tool-written status, the other findings and the settings (points 6 to 15)
  - that no answer is read from a pull-request description, and that no merge claims a revalidation nobody made

## Rationale

**Why files of a change's own.** A host merges two changes cleanly where each adds a file no other change writes, and only there. A file of the change's own also keeps the answer the change's. It is in the change's diff, the change check reads it there, and the reviewer checks it from the check's list (COR-050 point 3). Nothing but the repository is needed, so the check works for any host, a local run included.

**Why a change that answers only adds.** Git may pair a removed file with a similar added one as a rename.
- **Removing beside adding.** A change might remove the answer it replaced and add its own. A parallel change might do the same to that file, or prune it. The two would conflict over one file.
- **Rewriting.** A change that rewrote a landed answer file would change an answer its reviewer never saw. A name it added there would clear friction unlisted.
- **What a change adds only.** Removing replaced answers is a change of its own, which adds nothing. A revert that owes an answer keeps the files it would remove. That costs a hand step after a plain revert, and the kept files stay until a prune. In return, a partial revert keeps the answers on anchors it left alone.

**Why each answer names what it read.** Replacing an answer needs to know that its replacer read it. The tree of the change's own head shows what was there to read. A merge built by a host or a queue also holds answers landed after the change answered. Judged against it, every later run of the change would fail for answers it could not have read. The names are verified against history. A name copied onto another line of work, or written wrong, keeps an answer live rather than clearing friction.

**Why a file put back writes no answer.** Reverting a prune, or reverting a revert, puts back a file with the names it had. It leaves out every answer file added since, so point 4 would fail it. Rewriting its names to pass would make an old answer replace newer ones. Put back as history held it, it says only what it said before, with its points.

**Why answered apart is a finding, not a conflict.** The conflict forced the judgment of the combined state on whoever landed second, at the cost of a round. Most rounds conflicted only in answers. The conflict's protection was also partial:
- **A body edit without an answer.** It merges cleanly beside a change that answers, and nobody judges the combined state.
- **A parallel deferral.** It can merge cleanly beside a revalidation in the block, and the revalidation then reaches it unread.

The finding names every pair, whatever merged cleanly. It moves the judgment to the next change that answers on the artefact. The cost is that, until then, the combined state stands unjudged, reported as debt.

**Why every pair, not only those on one anchor.** A pair on one anchor can be told only from each change's bounds. A rebase-merge or a direct push loses them, and two `updated` edits whose bodies merge cleanly share no anchor. A finding that missed them would report health where nobody judged.

**Why a revalidation reaches only what it holds or read.** Under a squash, a change's commits land as one, after the parallel ones. Ancestry would then let a revalidation reach a deferral that landed beside it and was never read. Reading through `supersedes` reaches only what the answer had in front of it.

**Why an answer on what is gone is not live.** A landed answer file is never rewritten, so an answer in it cannot be taken out when its anchor or target goes. Failed by validation, it would hold the default branch failing with no change able to mend it. Not live, it answers nothing, the measures ignore it, and a prune removes it. The change that writes such an answer is still stopped, since that is where it can be mended.

**Why no anchor stands on an answer file.** An answer would otherwise flag every artefact with a path anchor over the folder. That artefact's own answer would add another file there, which would flag it again. A path anchor leaves out a container for the same reason (COR-050, "Why a path anchor stands on the content of a file a place holds").

**Why one fixed path.** Reading an artefact's answers at a commit needs the folder at that commit. A setting would have to be read at each commit, and a change to it would strand the answers left behind. A path the backbone fixes reads the same at every commit, in every project.

**Why an artefact received by sync owes no answer.** Its answers stay in its source's folder, since no sync carries that folder. Asked of the receiving project, an answer would be one on a file the project does not own, about a change it did not make. Its source answers it, where it is authored.

**A gain where files arrive by sync.** Answers leave the files a sync carries. A revalidation in the source no longer changes a received file, so a sync that brings one flags nothing. That ends the churn COR-050 describes, where each such sync flags the path anchors on the received file.

**What still conflicts.** Anchor lists and bodies. Their conflicts are in what the changes said, so a person resolves them, as before.

**Where the two checks part.** The change check reads what an answer read against the change's own head. It reports the revalidations its base's tip adds beside the change's, and fails nothing on them. The whole-repository check reports each pair once both have landed, as debt, until a revalidation reads both.

### Alternatives considered

- **A merge driver for the block.** Rejected. A host runs no merge driver, so a change still shows the conflict there. A clone that did not register it gets the plain conflict, and the registration drifts.
- **Answers in the pull-request description, or in commit trailers a squash carries.** Rejected, as COR-050 rejects reading an answer from a description. A host builds a squash message as it is set up to, and a message edited by hand drops trailers silently.
- **Answers staged on the branch and folded into the artefact as the change lands.** Rejected. The fold makes a new head, so the checks run again, and a landing in that window conflicts with it. The round moves rather than goes.
- **Answer files folded into the artefacts' blocks by a job after merges.** Rejected. The job would write answers after merges, which COR-050 point 3 rules out. Without the job, the answers have two homes.
- **Splitting the documents that many changes answer on.** Not taken. It moves the conflicts rather than removing them. Shared code, sibling pages under one glob and a shared index stay hot.
- **One answer per anchor inside the block, or one entry per change in a list there.** Rejected. Two entries inserted at one place still conflict, and any order that spreads them collides by chance.
- **A union merge of an artefact's file.** Rejected. It applies to a whole file, so it would join body conflicts and repeat front-matter keys.
- **Each answer recording the default-branch commit it was answered against.** Rejected. It is a claim about ancestry that the check cannot verify from the tree.
- **A revalidation naming only the deferrals it drops.** Not taken. It says what the answer drops, not what it read, so a parallel deferral nobody read could not be told from one it kept.
- **Naming only live answer files.** Rejected. Removing a middle answer would bring back one it had replaced (point 4).
- **An answered-apart finding only where both changes moved one anchor.** Rejected. It needs each change's bounds, which a rebase-merge or a direct push loses.
- **Removing a replaced answer in the change that replaces it.** Rejected. Git may pair the removal and the addition as a rename, and two such changes conflict.
- **A revert that removes the answers it reverts and adds its own, let through as an exception.** Not taken. The check cannot tell a revert from any other removal. Let through, a plain removal beside an addition would bring back the conflict point 3 prevents.
- **Validation failing an answer on what is gone.** Rejected. No change can rewrite the landed file that holds it, so the default branch would fail with no mend.
- **The old blocks drained, read until each artefact's next answer moves them out.** Rejected. Every reader would keep two homes for as long as some artefact is never answered again.
- **A setting that places the answer folder.** Rejected. Reading answers at a commit would need that commit's setting, and a move would strand the answers left behind.

## Implications

- **The backbone ships** the answer files' schema, writers that add answer files, a writing command that prunes, and checks that read the answers there. Its machine-readable output gives each artefact's live answers and their points. Components read `at` through it, never from a file.
- **A migration** moves every project's existing answers once, one answer file per artefact, each value keeping its point (point 6, COR-010). A branch open at the upgrade that answered in the old blocks conflicts once.
- **COR-050's top line** says it is partially superseded by this record. That line opens COR-050's preamble, on which each of its points stands (COR-050 point 5). So it flags, once, every dependant anchored on COR-050 or on one of its points. Those dependants are answered wherever answers live when it lands.
- **COR-050 points 6 and 9**, and the Rationale of point 9, carry forward pointers here. **COR-051 point 2** says a received rule owes no answer.
- **A component that judges a change by the paths it touches** reads the answer folder as the methodology's bookkeeping, not as code. A review floor for code is one. Otherwise every change that answers draws a code review, and each push that only answers stales its approvals.
- **A component through which a change's merge is authorised** shows the answered-apart report with the change's answers. Where it covers a later head whose only changes are answers, those are changes to the answer files the change adds.
- **A project that requires up-to-date branches** still has a round where the base brings an answer on an artefact the change answers. The change's answer must then name it (point 4). The round has no conflict, and only answers change in it.
- **Continuous integration** needs the answer files' history, as it needs each artefact's (COR-050 Implications). Where it checks a merge of the change with its base, it gives the change check the change's own head.
- **Readers that took `at` from an artefact's front matter** switch to the backbone's machine-readable output.
