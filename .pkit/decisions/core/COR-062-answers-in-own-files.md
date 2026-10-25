---
id: COR-062
title: A change's answers live in files of its own
status: accepted
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a change no longer writes its answers to friction into the front matter of the documents it answers on. It writes them into new files of its own, in one folder. It never rewrites such a file once its base holds it, and removes one only to prune it or to revert. Two changes that answer on one document then merge with no conflict, on any host. Each answer names the other answers on its document that it read. Two revalidations made apart, neither naming the other, are reported as debt until the next revalidation on the document reads both. That is the judgment a merge conflict used to force. Anchors stay in the document, and anchor lists and bodies still conflict as before.

## Context

COR-050 has a change answer friction in the artefact it answers. A revalidation goes in the artefact's `revalidated` block, a deferral in that block's `deferred` list, and a revisit entry in its `revisited` list. The answer sits beside the text it justifies, and the checks need nothing but the repository.

Two changes that revalidate one artefact rewrite the same lines of that block. Git cannot merge them, so whichever lands second is in conflict.
- **The host.** A host merges with git's own merge, on its own side. It runs no merge tool a clone registers, and many hosts run no checks on a change in conflict.
- **The round.** Someone merges the base in by hand, resolves the block, writes the answer again and waits for the checks. COR-050 point 3 asks whoever resolves the conflict to revalidate the combined state, so the round also forces that judgment.
- **The cost.** A few documents that many changes answer on, such as a command reference, put almost every open change in conflict after each merge. The rounds run one after another, and many conflict only in answers.

Git merges two changes cleanly where each adds a file at a path no other change writes. It conflicts where both edit the same lines. It may also pair a removed file with a similar added one, as a rename. So on a host, the only answer that never conflicts is one written to a path no other change writes.

## Decision

**A change writes its answers to friction in new files of its own, outside the artefacts they answer, and never in a pull-request description. It never rewrites such a file its base holds, and removes one only to prune or to revert. Each answer names the other answers on its artefact that it read, and only an answer that read another can replace it. Two revalidations of one artefact, neither of which read the other, were made apart. Their combined state is reported as debt until a revalidation that reads both judges it. This record partially supersedes COR-050.**

In short, answers no longer conflict, because no two changes write one file. The judgment a conflict forced, of the combined state, moves to the next revalidation on the artefact, and its reviewer checks it. Until then it shows as debt. Anchor lists and bodies still conflict as before.

Four terms recur:
- An **answer file** holds a change's answers (point 1).
- The **answer folder** holds the answer files (point 2).
- An answer on an artefact is **live** while it answers something and no answer that read it replaces it (point 5).
- Two live revalidations of one artefact, neither of which read the other, were **answered apart** (point 7).

### 1. Answers live in answer files

A change writes its answers to friction in an answer file: a file in the answer folder, under a name no other change uses.
- **What it holds.** For each artefact it answers, the artefact's location and the answers on it. Those are a revalidation (COR-050 point 3), deferrals (point 4) and revisit entries (point 16). A document is named by its path. A collection entry is named by its file's path, `#` and its id.
- **Its keys** are COR-050's: `at`, `outcome`, `unchanged-because`, `deferred` and `revisited`. Each answer adds `read` (point 4). Their layout, and the checks a schema makes of them, belong to the schema the backbone ships.
- **What stays in the artefact.** Its block keeps its anchors, its reason for having none and the tool-written status (COR-050 points 1 and 10). It holds no answer. An answer left in it is read only in history, for its points (point 6), and validation finds it (point 10).
- **What the checks read.** Both checks, the debt listing and the explanation read an artefact's answers from the answer files. The change check reads the answers a change wrote from the answer files its diff adds. Its machine-readable output lists them, each with its words and its flags, for the reviewer of COR-050 point 3.

### 2. The answer folder

The answer folder sits at one path on the project-owned side of the methodology's tree, named for the functionality.
- **One path everywhere.** The backbone fixes the path. It is the same in every project, and no setting moves it. So a reader finds the answers at any commit without reading that commit's settings.
- **The project's own.** The answers are the project's. No sync reads or writes the folder, which is never a synced tree (COR-050 point 14). The backbone's writers write in it on the project's behalf, as they write in an artefact's block.
- **No artefact.** The folder is never a place. No place reads an answer file as an artefact, whatever the place covers, as no place reads a held document (COR-050 point 1). Neither measure counts an answer file, and the declared surface leaves the folder out (COR-050 point 8).
- **No anchor stands on an answer file.** What a path anchor, or an anchor of a registered kind, stands on leaves out every answer file. Otherwise each answer would flag every artefact with a path anchor over the folder. Their own answers would add files there, which would flag them again, without end. An anchor that matches only answer files is dead, as one matching only excluded paths is (COR-050 point 7).
- **Bookkeeping, never code.** An answer file is the methodology's bookkeeping about artefacts, as a container is (COR-050 point 5). A component that judges a change by the paths it touches never reads an answer file as the project's code. A review that a change to code requires is one such judgment.

### 3. A change adds answer files, and rewrites none its base holds

- **Adding.** A change writes its answers only by adding answer files. It may rewrite or remove an answer file it added, since its base does not hold that file.
- **Never rewriting.** It rewrites no answer file its base holds.
- **Removing.** It removes an answer file its base holds only to prune or to revert (point 8).
  - A prune removes only files in which no answer is live at its base, and adds none.
  - A change that removes a file in which an answer is live takes that answer away, as a revert does. It may add answer files of its own beside the removal.
- **The finding.** The change check finds a change that rewrites an answer file its base holds. It also finds one that adds answer files and removes one in which no answer is live at its base, a prune mixed with answers. It fails on either in enforcing mode, as on friction (COR-050 point 12).
- **A file put back.** A change may add an answer file with the path and the content that its base's history held. That puts back an answer as it was, and writes no new one. So point 4 does not apply to it, and the change check does not list it among the change's answers. Its values keep their points (point 6).
- **An answer moved.** A change may add an answer that one live answer of its base, in the artefact's block, carries with the same words and values. Where the added answer names no file in `read`, it is moved. A moved answer writes no new answer. Point 4 does not apply to it, as to a file put back, and naming no file, it replaces nothing (point 5).
  - **Compared per answer, and whole.** A revalidation is compared by its `at`, parsed as point 6 reads it, its outcome and its `unchanged-because`. A deferral is compared by its anchor and its reason. A revisit entry is compared by its target, its outcome and its reason. Each is compared with one answer of the base, never pieced together from several, and one word changed makes a new answer.
  - **Listed apart.** The change check lists it apart from the change's answers, marked as moved. Nobody is asked to accept it.
  - **Only from a block.** An answer that repeats the words of an answer file, as a partial revert may add, is not moved. It is asked as any answer is.
- **A cherry-pick** carries an answer file unchanged, or leaves it out and writes that line's own answer in a new file. So one path never holds two contents.

### 4. Each answer names what it read

- **What it names.** Each answer on an artefact names, in `read`, every other answer file that holds an answer on that artefact. Those are the files present in the tree of its change's own head, whether their answers are live or not. Point 10 says how an answer on a moved artefact is found.
- **The change's own head.** That tree is the head's, not the merge a host or a queue builds of the change with its base. So an answer landing on the default branch in parallel never fails the change's checks. The change check judges `read` against the change's own head wherever it runs.
- **A merge of the base.** A change that merges its base in brings the answers other changes landed into its head. Each live answer of the change on those artefacts must then name them, and so take on the combined state. The change rewrites the answer, or replaces it with a new one that names them (point 5). A change stacked on another names its parent's answer files.
- **Present, not only live.** Naming only live files would bring a replaced answer back when a middle one goes. Take answers X, Y and W, where Y read X and W read Y. Were W to name only Y, removing Y would leave X live beside W.
- **The findings.** The change check finds an answer the change adds, live at the change's head, whose `read` leaves out such a file, and fails on it in enforcing mode. An answer the change added and then replaced with a later one of its own is not asked this, since the later answer read it. Nor is a moved answer (point 3). A name of a file the head does not hold names nothing. Two answers that each name the other's file have read neither, so validation fails the pair.

### 5. What an answer replaces

An answer on an artefact is live while it answers something and no other answer replaces it. Replacing it takes naming its file, by a name that history agrees with.
- **By kind.**
  - A revalidation replaces the revalidations it read. It also replaces each deferral it read that it does not re-state.
  - A deferral replaces only the deferral of its own anchor that it read.
  - A revisit entry replaces only the entry for its own target that it read.

  So an answer that only defers need not re-state a revalidation to keep it.
- **What no longer exists.** An answer on what its artefact no longer holds answers nothing, and is not live. Such are a deferral of an anchor the artefact no longer declares, and a revisit entry for a target no link of the artefact takes. So is an answer whose location, followed as point 10 says, holds no artefact. Pruning removes their files (point 8).
- **Names that history agrees with.** A name in `read` is honoured only where history agrees with it. The file it names must have been added in a commit that first carried the name, or in an ancestor of one. A name first carried on two lines of work, as after a cherry-pick, needs this of one of them. Any other name is void, and what it named stays live. A void name errs toward more friction, never less.
- **Reaching a deferral.** A revalidation reaches a deferral (COR-050 point 4) only where it keeps the deferral itself, or read the file that holds it. Ancestry is not enough. After a squash, ancestry would let it reach a parallel deferral nobody read.
- **No rubber stamp.** An `unchanged-because` must differ from that of each revalidation it read on its artefact (COR-050 point 3). A revisit entry's reason must differ from that of each entry it replaces (COR-050 point 16).

### 6. Each value keeps its point across homes

- **One history, two homes.** The revalidation point of an artefact is the commit where its answers first carried the parsed value of `at` (COR-050 point 3). Its answers are those of the answer files that name it, and, in history, those its own block carried. A value first carried in one home keeps its point when it moves to the other, or to another answer file. So does a deferral put back, by its anchor and reason (COR-050 point 4).
- **A deferral that replaces one.** A new deferral may replace an earlier deferral of the same anchor that it read. It then keeps the earlier one's point, whatever its reason, as a reworded entry does (COR-050 point 4). That holds whether a revalidation re-states it or a deferral writes it. A deferral that read no deferral of its anchor starts a point of its own.
- **What relies on it.** Moving every answer out of the blocks moves no point. Nor does putting back an answer file, or writing back a value the artefact's answers carried before.
- **How far back.** The history is read back to where the artefact was last added, its file or its entry, renames followed (COR-050 point 3). It is not cut where an answer file was added.

### 7. Answers made apart are debt, not a conflict

Two live revalidations of one artefact, neither of which read the other, were answered apart. Nobody has judged their combined state.
- **Any two.** Every such pair is answered apart, whichever anchors each answered. Telling whether both changes moved one anchor needs each change's bounds, and a rebase-merge or a direct push loses them. It would also miss two `updated` edits whose bodies merge cleanly.
- **Measured as before.** An anchor has changed only where it differs from what it stood on at every live revalidation. That is how COR-050 point 3 measures points on lines of work apart. The finding, not a changed anchor, carries the unjudged combined state.
- **Debt, cleared by the next revalidation.** The whole-repository check reports each artefact answered apart as debt, from the first commit that holds both revalidations. The debt listing shows it, with that commit's author, date and change (COR-050 point 9). The next revalidation on the artefact reads both, judges their combined state and replaces them.
- **No staleness.** Being answered apart is no state of an anchor. Neither check's states, nor the tool-written status (COR-050 point 10), read it as stale. A component that turns the checks' states into obligations on a change asks none for it, as it asks none for a deferral. The debt waits for the next change that answers on the artefact.
- **Judged in front of a reviewer.** The change check flags, among a change's answers, each revalidation that replaces revalidations answered apart. The reviewer of COR-050 point 3 then checks that its reason judges their combined state. Where the change was not asked for that revalidation, it is a person's decision, as every answer a change was not asked for is (COR-050 point 3).
- **Told before the merge.** For each artefact a change revalidates, the change check reports each live revalidation on its base's tip that the change's answer did not read. Merged, the two would be answered apart. The person who authorises the merge is told of it with the change's answers, as information, not a gate (COR-050 point 3).
- **Never a failure.** Neither check fails on it, in any mode. A component through which a change's merge is authorised may choose to stop on it. Such a stop would bring back the round this record removes.
- **Deferrals made apart.** Two live deferrals of one anchor, neither of which read the other, each defer the anchor as it stood at its own deferral point. The anchor is new friction where it differs from what it stood on at every one of those points, as for revalidations above. So a combined state neither line deferred is friction, never covered.
- **Revisit entries made apart.** Two entries for one target, made apart, each answered the trigger of its own change. That is all COR-050 point 16 asks, and only the change check reads an entry, so nothing reports them.

### 8. Removing answer files: pruning and reverts

- **Pruning.** A change of its own removes answer files in which no answer is live. A prune removes files and adds none. It changes no answer live at its head, so it owes nothing and flags no dependant. A writing command prunes, and names what it removes (COR-050 point 13).
- **What stays replaced.** An answer stays replaced while an answer that read it is present. So a prune, a revert or a file put back brings back no answer that a present answer read. Where every answer that read one is gone, it may come back beside later answers. They are then answered apart (point 7), which errs toward more friction.
- **Removing a live answer.** Any change that removes an answer file in which an answer is live takes that answer away, whatever the change calls itself. An answer the removed one replaced is live again, as a value written back is (COR-050 point 3). So the change check judges the artefact against that answer's points, as COR-050 point 6 judges a written-back `at`.
- **A revert** removes the answer files the reverted change added. Reverting a change together with what its answers answered then owes nothing. A revert that owes an answer adds its own answer file beside the removal. A partial revert may keep a file, and its new answer names it (point 4).
- **The cost.** Reverting the only answer that read a pruned file can leave the artefact with no live revalidation. Its revalidation point is then the commit that first introduced its block, as for an artefact with no `at` (COR-050 point 3). A prune judges liveness at its own head, so one that lands beside a revert may remove an answer the revert made live again. Both over-report, toward more friction, never less.

### 9. An artefact received by sync owes no answer

An artefact a project receives by sync, such as a rule of a method rule set (COR-051 point 2), owes that project no answer.
- **Why.** Its answers live in its source's answer folder, which no sync carries (point 2). So a project never answers on a file it does not own.
- **As for an excluded path.** Neither check asks the receiving project for an answer on it, or reports it stale there. That is how COR-050 point 7 treats an artefact under an excluded path. No place of the project reads a synced tree either (COR-050 point 14).

### 10. Whose file, moved artefacts, and what each finding is

- **A writer's own file.** A writer writes only into an answer file it can tell is its own change's. It never writes into one another line of work added, a parent's on a stacked branch included. It refuses where two files it could call its own would each answer one artefact. Each would then have to name the other (point 4).
- **A moved artefact.** An answer names its artefact by its location when the answer was added. The checks follow that location through the renames of the artefact's file since, as they follow its history (COR-050 point 3). An entry moved between collection files starts its history again where it lands (COR-050 point 3), so answers on its old location are not followed. An answer whose location, so followed, holds no artefact is not live (point 5). So:
  - **A move and its revalidation in one change.** COR-050 point 3 requires the revalidation. It reads the answers on the old location, and replaces them.
  - **A move made apart from a revalidation.** The revalidation on the old location follows the file to the new one. It and the move's revalidation were answered apart (point 7), so the debt shows.
  - **An entry moved apart from a revalidation.** The revalidation on the old location is not live. A change it answered to an anchor shows as friction against the move's revalidation, toward more friction. A body edit it answered goes unjudged against the combined state. That is the cost of an entry's history starting again where it lands.
- **What validation fails:**
  - an answer file that cannot be read, or that names no artefact, since it answers nothing
  - two answers that each name the other's file (point 4)
  - a second entry for one target within one answer (COR-050 point 16)
  - an answer in an artefact's own block (point 1). In a file the project receives by sync, it is reported, never failed, since the project cannot mend it there.
- **What the change check fails on,** in enforcing mode, beside COR-050 point 12's findings:
  - a change that rewrites an answer file its base holds, or that adds answer files and removes one in which no answer is live at its base (point 3)
  - an answer the change adds, live at its head, whose `read` leaves out a file (point 4)
  - a deferral or a revisit entry the change writes that names no anchor or target of its artefact
- **What is reported only,** in every mode:
  - an artefact answered apart, as debt in the whole-repository check, and on the base's tip in the change check (point 7)
  - the flag on a revalidation that replaces revalidations answered apart (point 7)
  - an answer that answers nothing because what it names is gone (point 5). Pruning removes it.
  - the answers a change moved, listed apart from its answers (point 3)

### 11. The move, once, and what it costs

- **Once, every answer.** A project's existing answers move out of the artefacts' blocks once, as the project takes up this record. Each artefact's answers go to an answer file of their own, and each value keeps its point (point 6). After the move no reader reads an answer from a block, but in history.
- **No question for a person.** Each answer the move adds carries an answer of its base's block and names no file, so it is moved (point 3). The move asks nobody to accept an answer.
- **Not a received file.** The move takes no answer out of a file the project receives by sync. Those answers are the source's, and move where it is authored (point 9).
- **A backbone newer than the move.** A backbone that reads answer files, run over a project whose answers have not moved, says so once and names the move. It does not report each answer as missing.
- **A line of work open at the move.** One that answered in the old blocks conflicts with the move where the move changed the same lines. Where it did not, as with a first answer in a block that held none, it merges cleanly. Validation then fails the answer left in the block (point 10), and the move, run again, takes it out into a new answer file. The move never rewrites an answer file, and run again over a state it already moved, it writes nothing.
- **Dependants of COR-050.** The line that says COR-050 is partially superseded sits in COR-050's preamble, on which each of its points stands (COR-050 point 5). So it flags, once, every dependant anchored on COR-050 or on one of its points. Those dependants are answered wherever answers live when the line lands.

### What this overturns, and what stands

This record partially supersedes COR-050. Each overturned passage stays in COR-050 as it stood.
- **Overturned:**
  - in the lead, "The answer to friction lives in the artefact itself". Its second half, "never in a pull-request description", stands. So does the lead's "and when it was last revalidated", read as what the artefact's answers record.
  - in the lead's sentence on revisits, that a change "records on the artefact" why a target still stands. The entry is among the artefact's answers (point 1 here).
  - in the definition of the revalidation point, the artefact's own `at` as the only home of the value (point 6 here)
  - in point 1, that each artefact carries its own revalidation, and that everything COR-050 owns in an artefact sits in its block. The block keeps the rest (point 1 here).
  - in point 2, "The block's fields are owned by this record", where the block's schema checks a revalidation. The answer files' schema does (point 1 here).
  - where points 3, 4 and 16 put answers: the `revalidated` block, its `deferred` list and the `revisited` list. With it go the rules that follow from that home:
    - the artefact's file as the only history of its answers (points 3 and 6)
    - entries kept sorted so that parallel branches merge cleanly (points 4 and 16)
    - a revalidation rewriting the block (point 4), and an entry staying until a later change rewrites it (point 16)
  - point 3's rule that whoever resolves two conflicting revalidations judges their combined state. Two revalidations made apart are reported instead, and the one that clears them is flagged to its reviewer (point 7 here).
  - point 16's "Conflicts" rule for revisit entries, with nothing in its place. Two entries made apart each answered their own change (point 7 here).
  - what an `unchanged-because`, and a revisit entry's reason, must differ from (point 5 here)
  - point 4's "reaches", read through what a revalidation holds or read (point 5 here)
  - point 4's "Removing an anchor removes its entry" and "Removing the artefact … removes its entries", with the validation error on a dangling entry. An answer on what is gone is no longer live (point 5 here).
  - in point 16, validation failing an entry that names no target, and a second entry for one target written apart (point 10 here)
  - in point 6, the artefact's own file history as all the change check reads behind the base. It reads the answer files' history too.
  - in point 6, that the check reads the artefacts, never the description. It reads the answer files, never the description.
  - in point 12, that enforcing mode fails on the first six findings alone. It also fails on those of point 10 here. Validation's list in point 12 loses the dangling deferral and the revisit entry that names no target, as above.
  - in the Rationale:
    - "Why the answer lives in the artefact", where it puts the justification next to the thing it justifies
    - in "Why deferrals are per anchor", that reasons merge cleanly because each has its own line
    - in "Where the two checks part", the case of a conflict resolved by keeping the line of work's revalidation
    - in "Why a record anchor stands on the record's content", and in "Why a path anchor stands on the content of a file a place holds", that each sync bringing its source's revalidation reaches a received file
  - in Alternatives, "in favour of revalidating the combined state", on keeping either timestamp of a conflicting revalidation
  - in Implications:
    - the checks reading the blocks for answers, and the block's schema leaving existing documents unaffected. The answers move once (point 11 here).
    - "an artefact's answer is on the artefact". It is in the answer files.
    - a component that withdraws a link removing the entries that would dangle. Those entries answer nothing (point 5 here).
- **Stands:**
  - anchors, their kinds and parts, and what each stands on (points 2 and 5)
  - the three answers and what clears friction (point 5), read from the answer files
  - who decides an answer, what the reviewer checks and what the person is told (point 3)
  - the revalidation point read from git, and a value written back keeping its point (point 3)
  - deferrals per anchor, re-stated by a revalidation that keeps them, and a deferral's point, which rewording does not move (point 4, read across answer files by point 6 here)
  - links and what they ask (point 16), the reason staying among the source's answers
  - both checks, the measures, the tool-written status, the other findings and the settings (points 6 to 15)
  - that no answer is read from a pull-request description, and that no merge claims a revalidation nobody made

## Rationale

**Why files of a change's own.** A host merges two changes cleanly where each adds a file no other change writes, and only there. A file of the change's own also keeps the answer the change's. It is in the change's diff, the change check reads it there, and the reviewer checks it from the check's list (COR-050 point 3). Nothing but the repository is needed, so the check works for any host, a local run included.

**Why a change never rewrites a landed answer file, and removes one only to prune or to revert.**
- **Rewriting.** A change that rewrote a landed answer file would change an answer its reviewer never saw. A name it added there would clear friction unlisted.
- **Removing beside adding.** Git may pair a removed file with a similar added one as a rename. A change that removed the answers it replaced and added its own would conflict with a parallel change that did the same, or that pruned them. So replaced answers go in a prune, which adds nothing.
- **A revert.** It removes answers that are live, which no prune removes. A parallel change meets the same file only after it replaced those answers and pruned them, which is rare and shows as a conflict, never silently. In return, reverting a change together with what its answers answered owes nothing, as it did when the answers lived in the artefact.

**Why each answer names what it read.** Replacing an answer needs to know that its replacer read it. The tree of the change's own head shows what was there to read. A merge built by a host or a queue also holds answers landed after the change answered. Judged against it, every later run of the change would fail for answers it could not have read. Only an answer still live is asked to name them: one the change replaced was read by its replacer. The names are verified against history. A name copied onto another line of work, or written wrong, keeps an answer live rather than clearing friction.

**Why a file put back writes no answer.** Reverting a prune, or reverting a revert, puts back a file with the names it had. It leaves out every answer file added since, so point 4 would fail it. Rewriting its names to pass would make an old answer replace newer ones. Put back as history held it, it says only what it said before, with its points.

**Why a moved answer asks nothing.** COR-050 point 3 asks a reviewer or a person to accept an answer, since it is a judgment the tool cannot make. A moved answer makes no new judgment. Its words were answered for when its base's block first carried them. Its values keep their points (point 6), and it reads no file, so it clears no friction and replaces no answer that its base did not. Asking again would send each moved answer to a person word for word.

**Why only from a block, reading nothing.** The block named no file, so a moved answer has none to name. Reading none, it is answered apart from any answer file on its artefact (point 7), so a second run of the move beside a newer answer shows as debt. An answer that repeated an answer file's words would have to name the files beside it, and would replace them unseen. So it is asked as any answer is.

**Why answered apart is a finding, not a conflict.** The conflict forced the judgment of the combined state on whoever landed second, at the cost of a round. Most rounds conflicted only in answers. The conflict's protection was also partial:
- **A body edit without an answer.** It merges cleanly beside a change that answers, and nobody judges the combined state. Neither the conflict nor the finding covers it.
- **A parallel deferral.** It can merge cleanly beside a revalidation in the block, and the revalidation then reaches it unread.

The finding names every pair of revalidations made apart, whatever merged cleanly. It moves the judgment to the next revalidation on the artefact. The cost is that, until then, the combined state stands unjudged, reported as debt.

**Why answered apart is no staleness.** A component may turn staleness into an obligation on every change, such as a documentation check. Each change would then owe a revalidation on an artefact it never touched, and the round would come back across every change. The debt belongs to the next change that answers on the artefact.

**Why the revalidation that clears it is flagged.** The judgment moves only if someone makes it. The reviewer checks a reason against its change (COR-050 point 3), and the change may be about something else. The flag tells the reviewer that this reason must also judge the combined state.

**Why every pair, not only those on one anchor.** A pair on one anchor can be told only from each change's bounds. A rebase-merge or a direct push loses them, and two `updated` edits whose bodies merge cleanly share no anchor. A finding that missed them would report health where nobody judged.

**Why deferrals made apart are measured against every point.** Each covers the anchor as its own line left it. Covered by either, the combined state would pass as deferred though neither line deferred it.

**Why a revalidation reaches only what it holds or read.** Under a squash, a change's commits land as one, after the parallel ones. Ancestry would then let a revalidation reach a deferral that landed beside it and was never read. Reading through `read` reaches only what the answer had in front of it.

**Why a replacing deferral keeps the point it replaces.** A reworded deferral keeps its point in COR-050, so rewording cannot cover a change nobody judged. A new answer file for the reworded deferral must not either.

**Why an answer on what is gone is not live.** A landed answer file is never rewritten, so an answer in it cannot be taken out when its anchor or target goes. Failed by validation, it would hold the default branch failing with no change able to mend it. Not live, it answers nothing, the measures ignore it, and a prune removes it. The change that writes such an answer is still stopped, since that is where it can be mended.

**Why a moved artefact's answers follow its file.** A revalidation made beside a move would otherwise be lost unread, and nothing would report the combined state. COR-050 point 3 already follows the file's renames for the revalidation point, and requires a move to revalidate, which bounds the guess rename detection makes. An entry moved between files starts again, as its history does.

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
- **Asking every answer the change adds to name what its head holds.** Rejected. An answer the change replaced would have to name its replacer, which names it, and two answers that name each other read neither.
- **The key `supersedes` for what an answer read.** Not taken. A deferral names revalidations it does not replace, and a record's front matter already has a field of that name.
- **An answered-apart finding only where both changes moved one anchor.** Rejected. It needs each change's bounds, which a rebase-merge or a direct push loses.
- **Removing a replaced answer in the change that replaces it.** Rejected. Git may pair the removal and the addition as a rename, and two such changes conflict.
- **A revert that keeps the files it would remove, and only adds.** Not taken. One file may answer several artefacts. Kept, it leaves each of their answers in force, though the revert made them stale. The revert would then owe each a new answer.
- **A moved artefact's answers left at the old location.** Rejected. A revalidation made beside a move would be lost unread, and nothing would report the combined state.
- **Validation failing an answer on what is gone.** Rejected. No change can rewrite the landed file that holds it, so the default branch would fail with no mend.
- **The old blocks drained, read until each artefact's next answer moves them out.** Rejected. Every reader would keep two homes for as long as some artefact is never answered again.
- **Answers as keys in the backbone configuration.** Rejected. One file that every change writes conflicts as the block does, and the configuration holds declarations, not bookkeeping (COR-048).
- **Answer files in the shape of a component's records of its reviews,** such as a record of a revalidation a component keeps as a held document. Not taken. Such records are a component's own, declared and read by it. Answers are the backbone's bookkeeping, which every component reads through the backbone, with names verified against history.
- **A setting that places the answer folder.** Rejected. Reading answers at a commit would need that commit's setting, and a move would strand the answers left behind.

## Implications

- **The backbone ships** the answer files' schema, writers that add answer files, a writing command that prunes, and checks that read the answers there. Its machine-readable output gives each artefact's live answers and their points, and the folder's path. Components read `at` through it, never from a file.
- **A migration** makes point 11's move in each project as it upgrades (COR-010).
- **A component that judges a change by the paths it touches,** such as by a review floor for code, leaves the answer files out (point 2). Otherwise every change that answers draws a code review, and each push that only answers stales its approvals.
- **A component through which a change's merge is authorised** shows the answered-apart report with the change's answers. Where it covers a later head whose only changes are answers, those are changes to the answer files the change adds.
- **A project that requires up-to-date branches** still has a round where the base brings an answer on an artefact the change answers. The change's answer must then name it (point 4). The round has no conflict, and only answers change in it.
- **Continuous integration** needs the answer files' history, as it needs each artefact's (COR-050 Implications). Where it checks a merge of the change with its base, it gives the change check the change's own head.
- **Readers that took `at` from an artefact's front matter** switch to the backbone's machine-readable output.
