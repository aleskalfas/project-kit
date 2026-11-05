---
id: ADR-081
title: A check of its own refuses to land a proposal and lists what a change makes accepted
status: proposed
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a check of its own, `pkit decisions check-landing`, judges what a change would land: git's merge of the change into the base the run names. Everything else that decides the outcome, such as which branch is the default, it reads at the base's tip, where the change cannot move it. It reports each decision record and rule that would land proposed, and lists what the change makes accepted, with the commits around each acceptance. A key the default branch holds decides whether a reported proposal fails a landing there.

A component that carries out merges runs the check before it merges, and shows the person the list. A project with no such component has its host require the check, and a direct commit is checked before its push. A merge sent past that component, by the host's button or a backbone command, meets no refusal. Where the check cannot compute what lands, it gives no answer, which is never a pass.

**Why an ADR.** The core record that decides the refusal, the list and the key asks for an architecture record that realizes them ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md), Implications). This record names the check and the key, and places each computation in one home ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2). It also sets what a component that merges relies on.

## Context

**What COR-066 decides.** A decision record or a rule reaches the default branch only accepted, within the change that proposes it (point 1). A check of its own refuses to land a proposal: one added proposed, or an accepted one set back to proposed (point 2). The same check lists what a change makes accepted, for the person who authorises the change to land (point 3). A key in the backbone configuration turns the refusal on, and it counts as the default branch holds it (point 4).

**What this record rests on.** This record judges what a change's merge would land, where accepted COR-066 point 2 reads the change's head. So it reads true only once point 2 says the same, an edit that lands first as a core change of its own. COR-066's Implications give the list to the numbering check, where its point 3 gives it to the same check as the refusal. This record follows point 3, which is the decision.

**What the backbone has.**
- **The numbering check,** `pkit decisions check-diff`, compares the records a change touches with where its branch left the base ([COR-058](../../../.pkit/decisions/core/COR-058-record-points.md) point 8). It is a line of the project's check gate, which the pre-push hook and the pipeline run on every change. Its exit 1 means an error in the change's numbering, and its document, at version 1, lists the accepted records the change edits. project-management's landing command reads that document, and refuses any other version.
  - **What it reads.** Its reading of a state's records skips a file that is not text, and leaves it to validation. It reads which files the project receives, and where the ADR folder is, from the working tree.
- **`pkit friction since`** walks the head's first parents from a commit and reads what each commit contributes. It reads a merge of the base against git's merge of its parents, and a conflict there against git's merges taking each side.
- **The rule-set reader** reads each rule's status, a rule with none as proposed ([COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md) point 4). A rule's id carries its set's name and never changes (COR-051 point 3). A loaded rule set's rules have the same statuses ([COR-068](../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md) point 1).
- **The configuration's reader** reads the working tree's file forgivingly, the default branch's name among its keys ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md) point 1). Artefact discovery reads the same file forgivingly at a named state, for the friction settings. The delegate's name counts as the default branch holds it ([COR-064](../../../.pkit/decisions/core/COR-064-answer-delegate.md) point 2), and so will the decision-debt key ([COR-067](../../../.pkit/decisions/core/COR-067-decision-debt.md) point 4). No reader gives one key at the default branch's commit.

**What makes the comparison hard.** A branch falls behind its base, and the base may accept a record the branch left proposed. A branch stacked on a parent lands the parent's records too, and where the parent landed squashed, its commits lie outside the base's history. Commits may run on parallel lines, and many rules share one file. What decides the refusal, such as which branch is the default, is read from the working tree, which the change holds.

## Decision

**A check of its own judges what a change's merge would land and lists what it makes accepted. Where the default branch turns the refusal on, a proposal landing there fails the check. It runs where COR-066 point 2 places it, and nowhere else, so a merge sent past those places meets no refusal.**

### 1. A command of its own carries the refusal and the list

The *landing check*, `pkit decisions check-landing`, gives both the refusal and the list (COR-066 points 2 and 3). It is a command of the `decisions` group, apart from the numbering check.
- **The numbering check gains no mode.** Its exits, its place in the check gate and its document stay as they are, its document at version 1.
- **The list sits with the refusal,** in "the same check" that COR-066 point 3 names. The numbering check's list of edits to accepted records stays where it is.
- **Commits only.** Its head is a commit, `--head`, else HEAD, since only what is committed lands.

### 2. It judges what the merge would land

- **The landing state.** The check judges the tree git's merge of the head into the base's tip gives: the *landing state*. Where the head descends from that tip, it is the head's own tree.
- **The base is named.** The run names the base, on its command line or by the override a pipeline sets (COR-054 point 3). It resolves as any named base does, and the check takes no default base. A default would be the default branch, whose name would come from the working tree, which the change can move.
- **What it judges.** It compares each record and rule at the landing state with its state at the base's tip, and judges those the merge changes. One the merge leaves as the tip holds it lands nothing.
- **Records** are paired by the numbering check's pairing (ADR-057 point 2), so a record moved to another path is paired, not added.
- **Rules** are those of each rule set the rule-set reader finds, a loaded set's included (COR-068 point 1). They are paired by the change check's pairing of artefacts (ADR-057 point 2). Each rule is judged on its own, however many rules its file holds.
  - **A rule moved to another set** takes that set's name in its id (COR-051 point 3), so it is a new rule, judged as added. The rule it replaces stays in place, superseded or withdrawn.
  - **A rule set moved whole** to another path keeps its rules' ids, so its rules are paired.
- **What it cannot read counts as proposed.** Where the check cannot read a record's or rule's status at a state, it counts it as proposed there, with why. Its file may not be text, its front matter may not parse, or its status may be one its kind does not have. A record has three statuses, and a rule those and `withdrawn` (COR-051 point 4), so a withdrawn rule never reads as proposed. A rule-set file the reader cannot read counts as one proposal.
- **Refused and listed.** It reports each record and rule proposed at the landing state and not proposed at the tip (COR-066 point 2). One proposed at both is already on the base, and blocks nothing. Each record and rule accepted at the landing state and not accepted at the tip goes on the list (point 4 below).
- **Skipped where received.** A record or rule set the project receives by sync is judged where it is kept, so the check skips it (point 3 below). It tells such a file by the *synced-copy test*, code held in the tree ([ADR-075](ADR-075-generated-operational-rules.md) point 5), not by the kind of set. So a method rule set authored in the project's own repository, as the methodology's source authors its own, is judged.

### 3. All else is read at the base's tip

Besides what lands and the code that runs, every input to the judgement is read at the base's tip, a state the change cannot move. Which files the project receives and where the check looks are read at the landing state too.
- **Whether the base is the default branch** is decided by the base's name, never by resolving the default branch. The base counts as the default branch unless the run names it as a branch whose name differs from the name the tip declares. A remote's copy counts by its branch's name, and a base named only by a commit counts as the default branch. So a queue's base, or a commit that raced a push, is judged as the default branch is.
- **Only a landing on the default branch is refused.** On another base, such as a parent's branch or an integration branch, the check refuses nothing and gives the list. COR-066 bounds what reaches the default branch, so a proposal merged elsewhere is refused when that branch lands.
- **Which files the project receives** is read at the tip and at the landing state, each from that state's own files. A file either reading skips is skipped. The check reports each record and rule-set file the two readings disagree on, for the person to see. It ignores discovery's own mark of a received file, which reads the working tree.
  - **The tree's copy.** The check asks the working tree's copy of the test, the one every reader loads, and discovery runs that copy too. The test reads a filesystem root, so each state gets a *stand-in root*, a temporary folder. It holds the test's three inputs at that state: the manifest, and the two paths that mark the methodology's source.
  - **A state that cannot tell.** Where a state's manifest does not read, its stand-in holds no manifest, so that state skips no capability's record. Where the manifest records a capability's origin ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)) as one the test does not know, the test skips no file of that capability. A tree with no such module skips no file, as the numbering check reads it. The check says why, so a broken manifest hides no record, and a sync mends an unknown origin.
  - **The cost for rules.** Where the landing state's manifest does not read, no capability's rule sets are read there, so a proposed rule in one passes this check. A manifest that does not read already fails the project's validation, so that merge does not go unseen.
- **Where it looks.** The ADR folder is read at the tip and at the landing state, and a record either reading finds is judged. So a change hides no record by moving the folder. A state's rule sets are read at that state's own places, so a rule in a place the landing state drops is not read.
- **Read forgivingly.** A file at the tip that does not parse, or an invalid value there, gives a warning and the default ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 4). A misspelt key reads as absent. Validation fails all three, a misspelt key as an unknown one.
- **What it trusts.** The check runs the tool at hand and the working tree's copy of the synced-copy test, and reads neither at the tip. Where a run takes either, or its pipeline line, from the change, the change can alter the check. So the check is an interlock against a proposal landing by mistake, not a defence against a change that edits the tree's code. In this repository, `uv run pkit` runs the change's own code anyway.

### 4. The list shows each acceptance with the work around it

The list gives, for each record and rule the change makes accepted, three things COR-066 point 3 names. A second list gives the change's edits to what the base accepted since the branch left it.
- **The change's commits** are those the head reaches and the base's tip does not, a stacked parent's included.
- **What a commit contributes** is read against its *prior state*, the state before it that the home of a commit's contribution gives (ADR-057 point 2). A merge's other parents lie among the change's commits or in the tip's history, so its prior state is git's merge of its parents. A status a conflicted merge holds is its own only where neither of git's merges taking one side holds it. Every test below reads a prior state's status this way.
- **The commits that accepted it** are each of the change's commits that hold it accepted where their prior state does not. Each is shown with the rest of what it contributes, so work bundled or squashed with an acceptance is seen.
- **The work before** is, for each commit that accepted it, the change's commits before that one that touch anything else (COR-066 point 3). A commit touches what it contributes, and one on a parallel line counts as before. So work done first and recorded after is shown. For a rule, anything else is anything but its own content, so an edit to another rule in its file counts.
- **The edits since** are how its text at the landing state differs from its text at each commit that accepted it. A record's edits are read point by point, as the numbering check reads an accepted record's, and a rule's as its content.
- **Only what lands is shown** of each commit's work, so a parent's work the base already holds is not shown again. A commit left with nothing to show stays on the list, and says so.
- **Accepted on the base since the branch left it.** The *branch point* is where the head's line left the base, as the numbering check reads it. A record or rule goes on the second list where the tip holds it accepted, the branch point does not, and the merge changes it. The list shows how it differs at the landing state from the tip, read as the edits since are.

### 5. The key, read where the default branch holds it

- **Name and shape.** The key that turns the refusal on (COR-066 point 4) is `decisions.refuse-proposals`, a boolean in the backbone configuration. With `true`, the refusal is on, and with the key, its block or the file absent, it is off (COR-048 point 3). Validation fails any other value.
- **Read at the default branch.** The check reads the key at the base's tip (point 3 above), through the home of a configuration key at a commit (ADR-057 point 2). So a change that turns it on or off counts once it has landed (COR-066 point 4).
- **It decides only whether the refusal fails.** The check reports the proposals and gives the list whether the key is on or off. With it on, a reported proposal fails a landing on the default branch. Otherwise the check passes and says why.
- **A change to it** is reported, with its value at each state, so the person who authorises it sees it (COR-066 point 4).
- **Turned on, the default branch's proposals are listed.** Where the landing turns the key on, the check also lists each proposed record and rule of the project's own that the tip holds. They block nothing (COR-066 point 2), and a person settles each (COR-066 point 4). The check lists them on that run only, and their standing listing is the decision-debt command's (COR-067 point 3).
- **Its writers** are the two COR-066 point 4 names, with COR-048 point 5's consent. The install writes the key only on an explicit flag, and makes no offer. Otherwise a change a person authorises writes it, by the configuration command or by an edit.

### 6. No answer is never a pass, and it exits apart from a refusal

The check gives no answer, and says why, only where it cannot compute what lands:
- The run names no base, the base resolves to no commit, or the head names none (COR-054 point 4).
- The clone is shallow, so the change's commits may not all be here.
- Git's merge of the head into the base's tip conflicts, where the fix is to merge the base in.
- The git at hand cannot compute a merge the check needs.
- The synced-copy test cannot run: the working tree's copy raises, or no stand-in root can be made. The check catches the error, in discovery's runs of the test too.

Nothing else stops it. What it cannot read of a record or rule counts as proposed (point 2 above), and the configuration is read forgivingly (point 3 above). So no answer and a refusal never meet, and with no answer the document gives only why.

No answer is never an empty list, and never the refusal off. A caller holds the merge on it, whatever the key says, since the list cannot be shown. A pass exits 0, and a refusal exits 1, as a failing check does. No answer exits with a code of its own, apart from the usage error's, which the CLI reference names.

### 7. Where it runs

- **Through a merge component.** A *merge component* carries out merges on a person's authority. The backbone's own merge commands are not one: every project has them, so COR-066 point 2's "project without such a component" would otherwise describe nothing. A merge component runs the check before it merges, after the reviewers have judged the change. It does not merge while the check refuses or gives no answer.
  - **What it shows.** Before the person authorises the merge, it shows them the list and any change to the key. It also shows each file the two readings of point 3 above disagree on, and the proposals point 5 above lists. How, and in how many runs, is its own record's.
- **A project without a merge component** has its host require the check for a merge: the *host check*. It runs on a line of its own in the pipeline, apart from the check gate. The line names the pull request's target by its branch name as base and its own head as head, and fetches their history.
  - **With the key off** no proposal fails it, so the line can be wired before the key is turned on. Only no answer fails it then.
  - **Its pass can go stale.** The host check's pass holds for the tip it ran against. If the base moves, or the key is turned on, an open pull request stays green on the old run. A project that wants no stale pass requires each change to be up to date with its base, or merges through a queue. Otherwise it accepts the cost.
- **A direct commit.** A person accepts each record and rule a commit makes accepted before the commit (COR-066 point 2). Whoever commits straight to the default branch then runs the check before the push, and pushes only on a pass. Its head is the commit, and its base the default branch, fetched.
  - **A hook.** A project may wire one for a push whose target is the default branch, since no change's own push meets it. The backbone installs none.
- **Nowhere else.** The project's check gate, a hook run on every push, and the numbering check never run it. So the refusal blocks no push, and hides no other check (COR-066 point 2).
- **What meets no refusal.** The host does not require the check where a merge component merges. So a merge sent past the component meets neither the refusal nor the list. It may go by the host's own controls, or by a backbone command such as `pkit pull-request land` or the release merge. So does an administrator merge past a host check.

### 8. What a caller relies on

As the reading of the base is for any component (COR-054 point 5):
- **The caller names the base and the head.** The check fetches nothing, so the caller fetches the base and the change's history before the run.
- **One document of its own.** With `--json`, the check prints one document whether it answers or gives no answer. Its version is its own, raised when a key a reader relies on changes its meaning or goes, never for a key added. It gives:
  - the base as named, the tip it judged, the head, and the landing state's tree, which a caller can use rather than build again
  - whether the base is the default branch, the key's value with any warning, whether the refusal is on, and any change to the key
  - each proposal point 2 above reports, whether the check refuses on them, and the two lists of point 4 above
  - each file the two readings disagree on, why a state could not tell (point 3 above), and the proposals point 5 above lists
  - a problem, which says why there is no answer, and with which the document gives nothing else
- **The numbering check's document is unchanged.** A component that shows the person one list of what a change decides reads both documents, and computes none of it.

### 9. One home for each computation

Each computation the check performs has one home, and the landing check computes none itself. This record adds four homes to ADR-057 point 2, which its Implications name. The synced-copy test keeps its home, the lifecycle layer's ownership module ([ADR-051](ADR-051-process-author-edit-authority.md) point 3). Points 2 to 5 above say what the check does with each.

## Rationale

**Why a command of its own, not a mode of the numbering check.** The numbering check is a line of the project's check gate, and its exit 1 means an error in a change's numbering. A mode would put the refusal one option away from the places COR-066 point 2 keeps it out of, and give one exit two meanings. The numbering check reads the working tree, where the landing check judges only commits. A command of its own keeps each check to one question, with its own exits, inputs and document.

**Why the list sits with the refusal.** One status, read at the landing state against the base's tip, gives both answers: proposed is the refusal's, and accepted is the list's. Computed in two commands, the two answers would drift on the same record. The list is wanted when a change lands, where the check gate does not run, and it walks a history no push should pay for. COR-066 point 3 puts the list in "the same check" as the refusal.

**Why the landing state.** A head compared with the base's tip would refuse a record the base accepted after the branch left it, which the merge lands accepted. A head compared with its branch point would list again a parent's record that landed squashed, and miss what the base did since. A merge commit and a squash land git's merge of the head into the tip, and a rebase usually lands the same tree. A conflict means the branch takes the base in before anything can be judged.

**Why all else is read at the base's tip.** COR-066 point 4 keeps the key out of the change's reach, and the same holds for whatever decides the refusal. Read from the working tree, the default branch's name could point the key at the change's own branch. The manifest could skip the change's own proposals, and a moved ADR folder could hide them. At the tip, the change moves none of these.

The ADR folder is read at both states, since looking further hides nothing. A state's rule sets stay at its own places, since discovery takes no other state's. Which files the project receives is read at both too, since a component the change installs is received, and COR-066 point 2 skips it. A disagreement between the two readings is shown, not refused.

**Why the tree's copy of the test, not the tool's.** The check is an interlock, and discovery runs the tree's copy in this check anyway. So the tool's own copy would protect nothing. It would cost an entry point, a second loader and an exception to what every reader loads. The tree's copy costs a stand-in root, and a list of the test's inputs kept by hand, which a test pins.

**Why a state that cannot tell skips nothing.** The test reads an unreadable manifest as every capability kit-shipped, which protects write authority. Here that bias fails open: it would skip the records of every capability the project authors. So such a state's stand-in holds no manifest, and the other state's reading stands. A false refusal is mended by mending the manifest or by a sync, and a hidden record mends nothing.

**Why the default branch is told by name.** A test that compared commits would fail open. A queue's base, a commit that raced a push, or a default branch not fetched would each read as another base, and pass. A name needs no resolving, so every case has an answer. A doubt counts as the default branch: the cost is a false refusal on an integration branch named by commit, which naming it mends.

**Why what cannot be read counts as proposed.** A rule with no status reads as proposed (COR-051 point 4). A record the check cannot read reads the same way, so one mistake has one exit. It fails safe: the refusal sees it, and validation names the fix. No answer is then kept for what cannot be computed at all.

**Why the list reads each commit's own states.** A stacked change lands its parent's work too, and the list shows a record accepted in the change it is built on (COR-066 point 5). Reading a merge against git's merge of its parents counts each commit's work once, as `friction since` reads a merge of the base. Showing only what the merge would land keeps a parent that landed squashed from being shown twice.

**Why the list holds every commit COR-066 point 3 names.** A record that realizes a point does not narrow it. A parallel line has no order to read, so its commits count as before. A commit left with nothing to show stays listed.

**Why the key is read at the default branch, forgivingly.** Held by the default branch, the key cannot be moved by the change it checks (COR-066 point 4). Read forgivingly, as COR-048 point 4 has every reader read, a broken file never locks merges, the change that mends it included. The refusal is off while such a file stands, and the check says so. Absence stays off, so a project that never chose has nothing to mend.

This rests on validation being a required check, which fails the file on the default branch and on each new change. A misspelt key reads as absent, so the check says off, not invalid. Where validation is not required, the refusal can be off unseen. Everywhere, a change cut before the break still passes while the file stands.

**Why no answer exits apart.** A check that cannot compute what lands and passes is a pass nobody earned. A refusal asks a person to settle a proposal. No answer asks for a named base, a fetch or a merge of the base. A caller that read one exit for both would ask for the wrong one.

**Why the check runs only where COR-066 places it.** COR-066 point 2 already decides where the refusal meets a merge, and this record realizes that and no more. So the backbone's merges stay as they are, and a project that never chose the refusal gains no new way for a merge to fail.

The cost is real: a merge sent past the component meets neither the refusal nor the list. COR-067's listing shows a proposal such a merge let through, only where a project turns tracking on. The same door keeps a defect in the check from locking a project, since a person can merge there.

### Alternatives considered

- **What COR-066 and COR-048 rule out.** Each of these departs from COR-066: a hook on every push, a refusal on every base, the key read at the head. So do the default branch's proposals listed on every run, and an upgrade that writes the key. A strict read of the key, or an unreadable key counted as on, departs from COR-048 point 4.
- **Read which files the project receives only at the base's tip.** Rejected: a change that installs a component would have that component's proposals refused, which the project cannot settle (COR-066 point 2).
- **Pair rules by content, so a rule moved to another set counts as moved.** Rejected: a rule's id carries its set's name (COR-051 point 3), and a renumbering would pass unseen, as would a copied proposal.
- **Skip every method rule set.** Rejected: the methodology's source keeps its own, and they would be judged nowhere.
- **Read "before" as only what the accepting commit reaches.** Rejected: work on a parallel line would go unseen.
- **A stop in the backbone's two merge requests.** The direct merge and the enqueue would each run the check, so the landing command and the release merge would meet the refusal. A later record can add it if the gap proves real. Rejected on five grounds:
  - Those requests know no base, so each merge gains a reading, and at times a fetch, that can fail with the key off.
  - A pull request found queued sends no request, and one armed for auto-merge merges anyway.
  - It would end the administrator override, and rest on a stop for every landing, which an opt-in refusal is not ([ADR-061](ADR-061-hosting-service-acts-in-the-backbone.md) point 5).
  - A merge request's stated bound would grow by a fetch and the check, which have none of their own.
  - A tip that moved after the person saw the list would land text nobody saw.
- **The release merge and the landing command run the check themselves.** Not taken: COR-066 point 2 does not ask it, and each is one more run to keep in step. A later record can add it.
- **A host check beside the merge component.** The backbone would fix the check's name, and the component would pass over it while it waits for the host's other checks. Every merge into the default branch would then meet the refusal, though the host's own controls show no list. Rejected: a name the two share, a line each project wires, and a check whose defect locks every merge.
- **Detect after the merge.** A line on each push to the default branch would run the check on the pushed commit against its first parent. Not taken: it refuses nothing, and COR-067's listing shows the same where a project turns tracking on.
- **The install offers the key.** Not taken: COR-066 point 4 names the install as a writer, and does not ask it to offer. An offer adds a prompt and a consent path, and its only gain is a nudge to a new project.

## Implications

- **ADR-057 point 2** is refined in place, each change with a forward pointer to this record. It says what each module computes, and what the landing check does with it stays here. It gains four homes:
  - **A configuration key at a commit.** One forgiving reading of the configuration's file at a commit its caller names, which each caller's record decides. It stands on artefact discovery's reading of a file at a state. It gives a key's value, or the default with why. Every reader of a key its record counts as the default branch holds it calls this reading.
  - **What a change's commits contribute, and git's merge of two commits.** One module of the binary gives that merge, and the state before each commit a reader walks. Each reader judges against that state by its own rule. For a merge whose other parents lie in the base's history or among the commits walked, that state is git's merge of its parents. For any other commit it is the first parent. For a conflicted merge, the module gives the file in git's merges taking one side, and what matches one is not the merge's own work.
  - **Which record is which across a change.** The numbering check's reading and pairing of records, at its path, else by its id-space and id. Its reading names each file it cannot read, gives the ADR folder at a state, and reads how an accepted record's points changed. The landing check calls it too.
  - **What a change lands, and the proposals a state holds.** One module compares what a change's merge would land with the base's tip. It gives what would land proposed, and what the change makes accepted with the commits around each acceptance. It gives the change's edits to what the base accepted since the branch left it, and the project's own proposals a state holds. Every reader in the binary calls it, and a component reads its answer through the check's document.
- **Two of ADR-057's sentences** on callers change. The pairing of a change's artefacts names the landing check among its callers. The home of a comparison's base says every check that compares a change with a base calls it, in place of a list.
- **The synced-copy test** stays as it is, and every reader keeps the backbone's one loader and the bias that protects write authority. The landing check asks it of each state through that state's stand-in root, and catches what it raises. Tests pin the stand-in's inputs to what the test reads. Tests also pin a manifest the change breaks, an unknown origin, a copy that raises, and a component the change installs.
- **The backbone configuration's schema** gains `decisions.refuse-proposals`, a boolean. Adding a key is additive, so no migration ships (COR-048 point 6). The CLI reference documents the key, and the landing check's options, base, document and exits.
- **The decisions README** documents the landing check beside the numbering check. It says where a project runs the check, and that the check is never wired into the check gate. Its "Not enforced yet" bullet narrows to what the backbone leaves to a project and its merge component.
- **The numbering check's reading** names the records it cannot read, for the landing check. The numbering check still leaves them to validation, and its document is unchanged.
- **`pkit friction since`** reads its commits through the home of what a change's commits contribute. Its document is unchanged.
- **A merge component** runs the check before it merges and shows the list, under a record of its own. A project without one wires the host check. project-kit has one, so it wires none, and its release merge meets no refusal.
- **COR-067's decision-debt command** finds the default branch's proposals through the home of what a change lands (ADR-057 point 2).
- **The accepted record edited** is ADR-057, refined in place.