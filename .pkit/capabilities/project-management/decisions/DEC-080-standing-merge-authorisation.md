---
id: DEC-080
title: A project setting authorises up front every merge whose review passes, and an upgrade turns it on
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a key in this capability's project configuration authorises, once and ahead of time, every merge the landing command makes of a pull request whose checks all passed and whose required reviewers all approve its head. That covers merges into the default branch, and a Task's merge into an integration branch. Where the key is on, an agent's run of the landing command merges such a pull request in the run that finds it ready, and the agent that brought it to review lands it without being asked. A person at a terminal is still asked.

The key covers no change to what governs merges: the methodology's configuration, the harness's permission settings, the reviewers' definitions and the continuous-integration workflows. Nor does it cover a head that holds a build's commits, or a merge that closes more than its Task. A merge that lands a proposed or newly accepted record, or edits an accepted record or a rule set, stops too, as does one whose review left a finding for the person. Those stop as they do today.

The upgrade that brings this record writes the key on where the project has not set it, and says so in plain words: running the upgrade is the consent. A person turns the key off at once. This partially supersedes [project-management:DEC-006-state-machine-and-cascade], whose authorisations are per-issue and in-session.

## Context

**Terms.**

- **The landing command** is this capability's command that lands an issue's pull request in one run. It waits for the checks, has the reviewers review the head, prints what the person is told, checks the merge with the base, and merges ([project-management:DEC-026-work-ownership-lifecycle], [project-management:DEC-055-pr-lists-answers]).
- **A pull request's review passes** where every check on its head has passed, and every reviewer the merge gate requires has a verdict that approves that head and stands for it ([project-management:DEC-028-agent-as-approver-paths]). A reviewer the person overrode ([project-management:DEC-050-per-reviewer-override]) has no such verdict.
- **The person** is a person who decides what reaches the project's default branch, as [COR-064](../../../decisions/core/COR-064-answer-delegate.md) defines the term.
- **A run authorised up front** is a run of the landing command given its authorisation before it starts, as DEC-055 point 3 uses the term.
- **A run at a terminal** is one whose standard input and standard output are both terminals, the test DEC-069 reads.
- **The standing authorisation of merges** is the authorisation this record's key gives. A merge is **held** where the landing command stops it ready, or refuses it, until a person acts.
- **The methodology's committed configuration** is what a project commits to tell the methodology how to run it: the backbone configuration ([COR-048](../../../decisions/core/COR-048-backbone-configuration.md)), each installed component's project configuration, and the agent overlay.

**What stands today.** DEC-006 makes Review → Done the person's, per pull request, and every authorisation per-issue and in-session: no standing go-ahead applies in a later turn. So the landing command stops at every ready pull request, naming its head, and the agent runs it again with the person's authorisation for that head. Most such stops ask the person nothing: the checks passed, the reviewers approved, and no finding waits for them.

What a run authorised up front meets is decided elsewhere:

- **Findings.** It merges on a `[person]` finding only where it found the finding's verdict at its start, standing for the head, since the person is shown each finding before giving that authorisation (DEC-055 point 3).
- **Records.** The person who authorises a merge sees first each record and rule the change makes accepted, and each edit to an accepted record ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) points 3 and 5).
- **Settings.** No authorisation given up front covers a change that turns on the switch of [project-management:DEC-069-when-fixers-start] or of [project-management:DEC-072-sync-gives-missing-cards]. Nor does one given before the person could see it cover a change that names, changes or removes the delegate (COR-064 point 2).

**What the maintainer asked.** The maintainer said he never wanted to authorise each merge, and that a change whose review passed should merge at once ([project-kit#3385](https://github.com/aleskalfas/project-kit/issues/3385)). Offered three places for a standing authorisation, he chose a setting in the project's committed configuration for this capability, set on by default. He asked that the release that brings it write it on in each project's configuration at upgrade. The question put to him said that the agent would still stop for a finding a reviewer left for him, and for a change that accepts or alters a decision record.

## Decision

**A key in this capability's project configuration, which an install and an upgrade write on with the person's consent, authorises up front every merge the landing command makes of a pull request whose review passes, where nothing is held for a person. Where the key is on, a run not at a terminal merges such a pull request in the run that finds it ready. The key covers no change to what governs merges, and no merge where a person is owed something first. Turning it off counts at once.**

### 1. The key is the person's authorisation of each merge whose review passes

- **What it authorises.** Every merge the landing command makes of a pull request whose review passes, where point 3 holds nothing: into the default branch, or a Task's into an integration branch ([project-management:DEC-013-branch-and-pr-conventions]). It is the person's authorisation of Review → Done for each such merge, given once for them all, across issues and sessions. Every other move DEC-006 gives the person stays per-issue and in-session.
- **The person's own word.** Authorising a merge stays the person's (COR-064 point 6), and the key is that authorisation. The person gives it by running the upgrade or the install that writes it (point 4), or by authorising a change that turns it on themselves. No reviewer's verdict stands in for it, and a role authorises nothing ([project-management:DEC-059-topology-of-seats] point 8).
- **The ask to land, too.** Where the key is on, the agent that brought a pull request to Review runs the landing command on it without waiting to be asked.
- **Where it is read.** In this capability's configuration at the tip of the default branch, as the landing command fetches it, never at the pull request's head. A key that is absent, or a configuration that cannot be read there, counts as off.
- **Only the landing command merges on it,** since only it makes every hold of point 3. The other merge commands of this capability, run directly, ask for each merge as before.
- **A draft is never landed on it.** The key obliges no merge. A pull request marked draft stays off the key for as long as it stays draft, such as a change that waits on its testing. A word to the agent lasts only its session (DEC-006), so the draft is the lasting mark.

### 2. Where it is on, an agent's run that finds a pull request ready merges it

- **One run.** A run not at a terminal, with no authorisation for a head, merges a pull request whose review passes where nothing is held, in that run. It does not stop at its ready line, and its last line says that the standing authorisation covered the merge.
- **A person at a terminal is asked,** as without the key. A dry run, and a run told not to wait, merge nothing.
- **A run authorised for a head** goes on as it does without the key.
- **A run authorised up front.** A run on the standing authorisation is one, so every hold that stops such a run stops it, such as a sentence on a document the change check does not mark updated (DEC-055 point 3, [project-management:DEC-065-answers-read-from-check] point 4). Point 3 adds the holds such a run does not meet today.
- **The review starts beside the checks.** Such a run stops on every `[person]` finding (point 3), so it starts the reviewers once the checks the project names have passed, as a run with no authorisation does ([project-management:DEC-063-task-builder] point 8, refined in place).
- **Only the head its checks judged.** A run on the key never merges a head it did not judge. Where the base merges through a queue, it enqueues that head and never asks to return before the merge (DEC-026, "Merging through a queue"). A merge the queue makes at another head is not one the key covered: the run says so, and what follows is [project-kit#3351](https://github.com/aleskalfas/project-kit/issues/3351)'s.
- **A head that moved.** Where the head moves before the merge, the run stops and merges nothing. A run again judges the new head from the start, on the same key: its checks, its review and every hold. So the agent may run it again on its own.
- **An audit comment.** Before it merges, the run posts on the issue an audit comment naming the standing authorisation and the commit of the default branch whose configuration held the key on. It posts it at every audit setting but `off` ([project-management:DEC-049-audit-journal-model] point 2), and with no comment posted, nothing merges.

### 3. What governs merges, and what a person is owed, stays held

The standing authorisation covers none of the merges below. Each stops as it stops without the key, and goes on only as it would there.

- **A change to what governs merges.** A change to the methodology's committed configuration: the backbone configuration, with its friction key and the delegate it names, each component's project configuration, with this capability's topology of seats, members and review settings, and the agent overlay. A change, too, to the harness's permission settings, the deployed definitions of the reviewers the merge gate can require, or the continuous-integration workflows. The backbone says which paths these are, and the adapter for the harness's settings and the definitions it deploys (point 7). A change whose only change there turns this key off is not held (point 5).
- **A build's head.** A head that holds a build's commits (DEC-063 point 7), read as the landing command reads them for [project-management:DEC-067-heads-that-start-programs] point 1.
- **A close beyond the Task.** A pull request whose closing references name any issue other than a Task in Review. The last pull request of an integration branch is one: it closes the issue that owns the branch, a close DEC-006 keeps the person's.
- **The records.** A change with any of these:
  - what COR-066 point 2's check reports, such as a proposed record or rule the change adds, whether or not the project turned that check's refusal on
  - a record or rule the change makes accepted, which COR-066 point 3 has the person see
  - an edit to an accepted record, which COR-066 point 5 has the person read
  - an edit to the file a rule set is authored in
- **A finding for the person.** Each `[person]` finding, even one the run found at its start, as at a later head (DEC-055 point 3).
- **An answer no change owes,** and each reason for having no anchors (COR-064 point 1). Such an answer is not held where the default branch's configuration names a delegate, and the reviewer of the answers is among those the merge gate requires for the pull request (COR-064 point 4). It then reaches the person after the merge, as COR-064 point 5 has it. Where no delegate is named, no delegate decided them, and each stays held.
- **Every other stop** the landing command makes, such as a failed check, a verdict that asks for changes, a merge with the base that the change check fails, or a head from elsewhere that needs a person (DEC-067).

The first of these takes in what other records hold at every merge: the switch and the grant list of DEC-069 point 4, the switch of DEC-072 point 3, the key of COR-066 point 4, the delegate COR-064 point 2 shows, and a change that turns this key on.

### 4. An upgrade turns it on, and running it is the consent

- **The upgrade writes it on.** The upgrade to the release that builds this record runs a migration of this capability, a script of the lifecycle that the upgrade runs, not a manifest of [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline], which no upgrade runs. It writes the key on where the key is absent and no earlier run of it left its marker, and it leaves its marker. It never changes a value the project set.
- **It says what it turns on.** At the upgrade, in plain words: that agents will land each pull request whose review passes without asking, what stays held, and how to turn the key off.
- **Running the upgrade is the consent.** COR-048 point 5 takes that consent for a key an upgrade's migration writes, where the key's owning record specifies the migration. This record specifies it for its own key.
- **An install** writes the key on and says the same words, and installing is the consent.
- **No hold of its own at the merge.** The consent came at the upgrade. The key is not on at the base of the upgrade's change, so the person authorises that merge in any case. A later change to the key, once it is on, is held as point 3 holds any change to this capability's configuration.
- **Where the capability is authored.** A project that takes no upgrade of this capability gets the key through a change that writes it. There the build's change writes it on, and the person authorises that merge themselves: the key is off at its base, and point 3 would hold it if it were on.
- **Turning it off** is setting it off. An absent key reads as off too, and the marker keeps a replay from writing it back.

### 5. A person turns it off at once

- **No hold.** A change that turns the key off is not held, since it only narrows what merges.
- **At once.** The key counts as off where this capability's configuration sets it off in the working tree of the checkout the landing command runs from, committed or not, as DEC-069 point 4 reads its switch.
- **For one pull request.** A run told to stop ready stops there, as without the key, and the person authorises that merge for its head. A draft keeps a pull request off the key for longer (point 1).
- **With several people.** The upgrade's consent, or the change that turns the key on, covers the landing runs of every clone, whoever runs them, each under that person's own credentials. In the human review mode ([project-management:DEC-027-review-modes]), a member's approving review is a verdict the merge gate requires, so a run on the key merges once it and every other required verdict approve the head. Each person turns the key off for their own runs at once, from their own working tree, and any person turns it off for everyone by a change.

### 6. The run judges by what the base holds

- **What it reads there.** A run on the standing authorisation reads the merge gate's settings in this capability's configuration, the definitions of the reviewers the gate requires, and the files of the landing command, at the tip of the pull request's base.
- **Where the working tree differs.** Where the working tree's copy of any of them differs from the tip's, the run stops ready, naming each such file. So a change neither weakens the review of its own merge nor brings holds of its own through the tree the command runs from.

### 7. What stays open

- **The person is told after.** A run on the standing authorisation prints what the person is told of the change's answers, and merges in the same run. The description carries only the authors' sentences (DEC-065 point 1). So the person learns what is left out of date only where the agent passes on the run's printout, which the pm skill obliges it to do ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 3).
- **Who decided an answer.** The run cannot tell who decided an answer no change owes (COR-064 point 4). Where a delegate is named, an answer a person decided passes too. That person read it word for word before it was written.
- **The local path's verdicts.** A local reviewer's verdict is a comment the session's own command posts under the person's account. DEC-028 accepts it as an attestation, not a proof ("Allowlist as attestation, not security"). With the key on, nothing but that session's honesty stands behind such a verdict before the merge.
- **What the hold covers.** It covers what point 3 names, not the code that judges a merge, such as the landing command's own. In a project that builds its own tooling, a change to that code merges on the key and judges each later merge.
- **Paths not yet named.** Neither the backbone nor the adapter names the paths point 3 holds. A follow-up of this record has them do so, and this record's build lands no earlier, so no run merges on the key before it can tell such a change.
- **Merges the hold does not see.** A direct commit to the default branch, or a merge outside this capability's commands, passes no hold (DEC-069 point 5).
- **Words that reach nobody.** The upgrade's words reach whoever reads its output. An upgrade an agent runs, or one under an agent host, may show them to nobody. That a message reaches a person is behaviour this capability can neither set nor read, which [pkit:ADR-091] point 6 makes a harness requirement.
- **A queue's wait.** DEC-026 bounds the wait for a queue, so a run whose wait ends first leaves the pull request queued and unwatched. A later head the queue merges is #3351's.

## Rationale

**Why a standing authorisation.** Authorising a merge stays the person's (COR-064 point 6). This record keeps it so, and lets the person give that word once for every merge whose review passes, where nothing is owed to them. No reviewer's verdict stands in for the person: the key is the person's own choice, made at the upgrade or by a change they authorise. Asked at each merge, the work would wait on a word the person chose to give once, the wait the maintainer asked to end.

**Why the person consents at the upgrade.** The upgrade is where the person acts. A hold at the merge of the upgrade's change would often not meet it. The landing command runs from the checkout it is run in, usually on the default branch and so the older command, as a seat's tree always is (DEC-063 point 7). An install's change merges before the capability is there to hold anything. COR-048 point 5 takes running an upgrade as the consent for what its migration writes, and the plain words at the upgrade make that consent informed.

**Why on at the upgrade, for every project.** The key widens what merges with nobody watching each merge, as DEC-069's and DEC-072's switches widen what runs with nobody watching. Those switches stay off and out of every upgrade's reach. An unconfined fixer's run may do whatever its settings let a session do, and nothing checks what it changed (DEC-069 point 5). A merge on the key lands only what the checks and the required reviewers passed, with point 3's holds kept. It lands in the open, with its verdicts and its audit comment, and a change reverts it. So the upgrade offers the key to every project in plain words, and the person accepts it by running the upgrade or turns it off in the same change.

**Why an absent key reads as off.** A project where nothing wrote the key, such as one whose upgrade has not run, merges as it did, each merge authorised. Read as on, the key would authorise merges in every project from the moment its tooling carried this record's build, before the upgrade said anything. The switches of DEC-069 and DEC-072 likewise read an absent setting as off. The marker keeps the absent key absent, where a person removed it.

**Why what governs merges stays held.** A change to the merge gate's settings, the topology, the reviewers or the delegate would weaken the gate that judges every later merge. Held, each such change still reaches the default branch only on the person's word. So what those records rest on stays true: what binds is configuration a person reviewed (DEC-058 point 1), the allowlists stay the project's attestation (DEC-028), and the delegate is shown before it counts (COR-064 point 2). One rule takes in the holds other records make at every merge, so none needs a list that goes stale.

**Why a build's head stays held.** A build's commits run only in a sandbox until a person reviews them (DEC-063 point 7). A seat's tree follows the default branch, so a build merged on the key would run there outside the sandbox. This costs a project with no seats nothing.

**Why a close beyond the Task stays held.** DEC-006 keeps the close of a container the person's, and a parent that becomes eligible to close never closes on its own. A merge into the default branch closes every issue its pull request names, so a merge that names more than its Task would make that close.

**Why the records stay held.** COR-066 has the person see what a change makes accepted, and read each edit to an accepted record, before it lands. A proposed record that lands binds nothing, but reads like a decision, and where a project's refusal is off, the person's word at the merge is its only check. No command yet tells which edits to a rule set alter an accepted rule, so the file the set is authored in stands for it.

**Why every `[person]` finding stops it.** DEC-055 lets a run authorised for a head merge on a finding it found at its start, since the person is shown each finding before they give that authorisation. The standing authorisation came before any finding existed, so no finding was shown before it. As at a later head, the run cannot tell what the person saw.

**Why an answer the delegate decided passes.** Showing such an answer at the merge does not make it valid: authorising a merge does not accept it (DEC-055 point 3). The delegate decided it in the person's place, a reviewer the merge requires checked it (COR-064 point 4), and the person is told afterwards (COR-064 point 5). With no delegate named, only a person could have decided it, and the run cannot tell that one did.

**Why the run reads at the base.** The key is read at the default branch, so no change turns on its own key. What decides whether the review passes would otherwise come from the tree the command runs from, which a change can alter. Read at the base, as the delegate's definition (COR-064 point 2) and the topology of seats (DEC-059 point 1) are, the gate judging a change is the one a person let in.

**Why only the landing command.** It alone prints the findings, what the person is told of the answers and the accepted records the change alters, and makes the holds of point 3. A merge command that shows none of them would merge on an authorisation given before anything was there to see.

**Why the review starts beside the checks.** DEC-063 point 8 holds back the reviewers of a run authorised up front only so that its next run cannot merge on a finding nobody was shown. A run on the standing authorisation stops on every finding, so that cannot happen. Holding its review back would add the whole suite's time to every landing in every project with the key on.

**Why a terminal still asks.** The maintainer asked that the agent not wait on him. A person who runs the landing command at a terminal is there to answer, and keeping the question keeps their habit: a run with no authorisation for a head merges nothing until they say so.

**Why an audit comment.** An authorisation-bearing move leaves its source on the issue (DEC-026, "Audit-trail comments"). A line in a run's output reaches only that run's reader, so the comment names the key and the commit that held it, for every later reader.

**Why off at once, with no hold.** Turning the key off only narrows what merges, so it needs no consent, and is safe to read from any working tree, as DEC-069 point 4 reads its switch.

### Alternatives considered

- **A setting on the person's machine only.** Not taken. It is not reviewed, and no other clone or sandbox reads it, as DEC-059 found of a topology kept per user. An agent's session on that machine could write it with no merge to hold it.
- **Once per session.** Not taken. Each session would ask again, the wait the maintainer asked to end, and a word given in a session leaves nothing another clone or a later reader can see.
- **An absent key read as on.** Not taken, as "Why an absent key reads as off" says.
- **Off by default, turned on only by the person's own change, as DEC-069's switch is.** Not taken. The maintainer asked for it on in every project, and the upgrade puts it to the person in plain words.
- **The consent at the merge of the upgrade's change.** Not taken. The older landing command usually lands that change, and an install's change merges before the capability is there, as "Why the person consents at the upgrade" says.
- **A list of named holds, with whatever else a record has the person see.** Not taken. No command can test for "whatever else", and a list goes stale as records add holds. One rule on what governs merges takes them in.
- **Holding every answer no change owes.** Not taken. Where a delegate decides them and a reviewer checks them, the hold would make the person wait on answers their word does not validate.
- **DEC-055's findings' hold for a run on the standing authorisation.** Not taken. A finding the run found at its start would merge with nobody shown it.
- **Reading the review settings from the working tree.** Not taken. A change could then weaken the review of its own merge, as "Why the run reads at the base" says.
- **Every merge command merging on it.** Not taken, as "Why only the landing command" says.
- **The host's own automatic merge.** Not taken. The host merges once its own required checks pass, and none of the landing command's holds run: not the findings, the answers, the records, the configuration or the merge check.

## Implications

- **Edits that change what a record decides,** made in this change once this record is accepted, and accepted with it (COR-066 point 5):
  - **DEC-006's top line** names this record beside DEC-062, reading *Partially superseded by [project-management:DEC-062-axes-chosen-in-the-map] and [project-management:DEC-080-standing-merge-authorisation]*. After what it says of DEC-062, it says in the line itself: "Where the project's configuration turns the standing authorisation of merges on, a merge the landing command makes of a pull request whose review passes, with nothing held for a person, is authorised once for every such merge, across issues and sessions. That holds for a merge into the default branch, and for a Task's merge into an integration branch (DEC-080). Overturned there: the Authorisation gates' 'per-PR approval' for Review → Done, the `pr-merge-into-main` path's 'user authorises merge', and 'per-issue and in-session — no standing "go ahead with everything" applies in a later turn'. Each stands for every other move and every other merge." The rest of DEC-006 stays as it stood.
  - **DEC-055's sentence** "An authorisation to merge is given for the head the landing command's ready stop names", in its Context and in point 3's "A later head", reads "An authorisation to merge one pull request is given for the head the landing command's ready stop names". Point 3's "How long it lasts" reads "This sets which heads an authorisation given for a head covers, not how long it lasts (DEC-006). The standing authorisation of merges names no head, and covers what DEC-080 decides (refinement per DEC-080)." Point 3's "The findings' hold" ends "A run on the standing authorisation of merges merges on no such finding, even one it found at its start (refinement per DEC-080)." The Decision's headline sentence "On an authorisation given up front, it merges only if…" takes the pointer "(refinement per DEC-080)".
  - **DEC-063 point 8's fourth bullet** reads "A run authorised up front for a head starts no reviewer before every check has passed. A stop between its verdicts and the findings' step would let its next run merge on a `[person]` finding nobody was shown (DEC-055 point 3). A run on the standing authorisation of merges stops on every such finding, so it starts the reviewers as a run with no authorisation does (refinement per DEC-080)."
  - **DEC-026's "Audit-trail comments"** gains a form for the landing command's merge on the standing authorisation: `Merge authorised by the project's standing authorisation of merges, read at <commit of the default branch>` (refinement per DEC-080).
- **Edits that change no record's decision,** made in this change once this record is accepted, since each cites it:
  - **DEC-057's bullet** "A person schedules work, and authorises each close and each landing" reads "A person schedules work, and authorises each close and each landing, a landing for its pull request or once for every landing the standing authorisation of merges covers ([project-management:DEC-080-standing-merge-authorisation])". Its Rationale's "the person holds both ends" stands, since the key is the person's own word.
  - **DEC-063 point 8's last bullet** reads "The person authorises the merge, for its head or through the standing authorisation of merges (DEC-080)." Its "Stands" names "the person's authorisation of each merge, for its head or through the standing authorisation of merges (DEC-080)".
- **Edits the build makes,** changing no record's decision:
  - **The workflow schema's Review → Done** says in its reason and notes that the user authorises the merge for each pull request, or once for every merge the standing authorisation covers. For a merge on the key, the cross-authority artefact its gate asks for ([COR-033](../../../decisions/core/COR-033-process-substrate.md) P4) is the key as the default branch holds it, which the person's upgrade or a change they authorised wrote. The merge's audit comment names that commit.
  - **The project-manager agent's** line on standing authorisations says it acts on none across sessions save the standing authorisation of merges, and on that one only through the landing command.
  - **The project-manager agent's storyboard,** where its worker "merges nothing", says that where the key is on, the worker's landing run merges a pull request whose review passes, and the person is shown what the run printed.
  - **The pm skill's landing step** says that where the key is on, one run lands a pull request whose review passes, that a run at a terminal still asks, and that a run stopped on a hold is shown to the person and authorised for its head as before. After a merge on the key, the agent passes on to the person what the run printed of the answers: what changed, what is left out of date until which follow-up, and each answer the delegate decided. Its sentence that an authorisation is per-issue and in-session names the standing authorisation beside it.
  - **The pm skill's exit-code guidance:** its "run again without `--yes`" under exits 2, 6 and 7 says that where the key is on, such a run merges, which stays safe since it stops on every finding. Under exit 3, the agent may run the landing command again on its own where the key is on, and that run judges the new head from the start (point 2). Under exit 8, it names the holds of point 3.
  - **The pm skill's worker loop** says that where the key is on, the worker lands each pull request of its own once its review passes, and merges on the person's authorisation for a head only where the landing stops for them.
  - **The capability's README,** in "Landing a pull request in one command", says what points 1 to 7 decide. Its account of the project configuration names the key, and its lists of what each merging command holds name point 3.
  - **The analysis's use cases and journeys of landing** follow, as the change check asks of them.
- **A follow-up:** the backbone, and the adapter for the harness's settings and the definitions it deploys, name the paths point 3 holds. This record's build lands with or after it (point 7).
- **Records that stand:** the holds of point 3 keep true what DEC-058 point 1, DEC-059 point 1, DEC-063 point 7, DEC-067 point 1, DEC-028's allowlists and COR-064 point 2 rest on, so none of them is edited.
- **A surface change** once built: a new key, point 4's migration, a landing that merges with no second run, and its audit comment, each declared by the build's changeset.
- **Acceptance:** this record partially supersedes the accepted DEC-006, and refines DEC-026, DEC-055 and DEC-063 in place, so accepting it needs the maintainer's sign-off.
