---
id: DEC-080
title: A project setting, offered at the upgrade and turned on by the person, authorises every merge whose review passes
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a key in this capability's project configuration authorises, once and ahead of time, every merge the landing command makes of a pull request whose checks all passed and whose required reviewers all approve its head. That covers merges into the default branch, and a Task's merge into an integration branch. Where the key is on, an agent's run of the landing command merges such a pull request in the run that finds it ready, and the agent that brought it to review lands it without being asked. A person at a terminal is asked, as without the key.

The key covers no change to what governs merges: the configuration the methodology declares as governing them, the instructions the harness loads, the reviewers' definitions, the files the project receives and the continuous-integration workflows. Nor does it cover a head that holds a build's commits, a merge that closes more than its Task, or a review mode a label set. A merge that adds, accepts or edits a record or a rule set stops too, as does one whose review left a finding for the person. Each of these stops as it would without the key.

The upgrade that brings this record writes the key as offered, which authorises nothing. A run the key would have merged then stops at its ready line, as without the key, and shows what the key does. The person accepts by authorising the merge of a change that sets the key on, once its stop has shown them those words, and no run asks again. A person turns the key off at once. This partially supersedes [project-management:DEC-006-state-machine-and-cascade], whose authorisations are per-issue and in-session.

## Context

**Terms.**

- **The landing command** is this capability's command that lands an issue's pull request in one run. It waits for the checks, has the reviewers review the head, prints what the person is told, checks the merge with the base, and merges ([project-management:DEC-026-work-ownership-lifecycle], [project-management:DEC-055-pr-lists-answers]).
- **A pull request's review passes** where every check on its head has passed, and every reviewer the merge gate requires has a verdict that approves that head and stands for it ([project-management:DEC-028-agent-as-approver-paths]). A reviewer the person overrode ([project-management:DEC-050-per-reviewer-override]) has no such verdict.
- **The person** is a person who decides what reaches the project's default branch, as [COR-064](../../../decisions/core/COR-064-answer-delegate.md) defines the term.
- **A run authorised up front** is a run of the landing command given its authorisation before it starts, as DEC-055 point 3 uses the term.
- **A run at a terminal** is one whose standard input and standard output are both terminals, the test DEC-069 reads.
- **The standing authorisation of merges** is the authorisation this record's key gives. A merge is **held** where the landing command stops it ready, or refuses it, until a person acts.
- **A run the key would cover** is a run of the landing command not at a terminal, with no authorisation for a head, on a pull request whose review passes, where point 3 holds nothing.

**What stands today.** DEC-006 makes Review → Done the person's, per pull request, and every authorisation per-issue and in-session: no standing go-ahead applies in a later turn. So the landing command stops at every ready pull request, naming its head, and the agent runs it again with the person's authorisation for that head. Most such stops ask the person nothing: the checks passed, the reviewers approved, and no finding waits for them.

What a run authorised up front meets is decided elsewhere:

- **Findings.** It merges on a `[person]` finding only where it found the finding's verdict at its start, standing for the head, since the person is shown each finding before giving that authorisation (DEC-055 point 3).
- **Records.** The person who authorises a merge sees first each record and rule the change makes accepted, and each edit to an accepted record ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) points 3 and 5).
- **Settings.** No authorisation given up front covers a change that turns on the switch of [project-management:DEC-069-when-fixers-start] or of [project-management:DEC-072-sync-gives-missing-cards]. Nor does one given before the person could see it cover a change that names, changes or removes the delegate (COR-064 point 2).

**What the maintainer asked.** The maintainer said he never wanted to authorise each merge, and that a change whose review passed should merge at once ([project-kit#3385](https://github.com/aleskalfas/project-kit/issues/3385)). Offered three places for a standing authorisation, he chose a setting in the project's committed configuration for this capability, set on by default. He asked that the release that brings it write it on in each project's configuration at upgrade. The question put to him said that the agent would still stop for a finding a reviewer left for him, and for a change that accepts or alters a decision record. Told later that an agent may run the upgrade and its words may then reach nobody, he chose how the person consents: the upgrade still writes the key, the first run the key would cover stops once and shows what the key does, and once the person says yes, no run asks again.

## Decision

**A key in this capability's project configuration authorises up front every merge the landing command makes of a pull request whose review passes, where nothing is held for a person. An install or an upgrade writes it as an offer, which authorises nothing. The person turns it on by authorising a change that sets it on, once a ready stop has shown them what it does. Where it is on, a run not at a terminal merges such a pull request in the run that finds it ready. It covers no change to what governs merges, nor a merge where a person is owed something first. Turning it off counts at once.**

### 1. The key is the person's authorisation of each merge whose review passes

- **What it authorises.** Every merge the landing command makes of a pull request whose review passes, where point 3 holds nothing: into the default branch, or a Task's into an integration branch ([project-management:DEC-013-branch-and-pr-conventions]). It is the person's authorisation of Review → Done for each such merge, given once for them all, across issues and sessions. Every other move DEC-006 gives the person stays per-issue and in-session.
- **The person's own word.** Authorising a merge stays the person's (COR-064 point 6), and the key is that authorisation. The person gives it by authorising the merge of a change that sets it on (point 4). No reviewer's verdict stands in for it, and a role authorises nothing ([project-management:DEC-059-topology-of-seats] point 8).
- **Its values.** On, offered or off. An offered key authorises nothing, and has a run show the offer (point 4).
- **The ask to land, too.** Where the key is on, the agent that brought a pull request to Review runs the landing command on it without waiting to be asked.
- **Where it is read.** In this capability's configuration at the tip of the default branch, as the landing command fetches it, never at the pull request's head. A key that is absent, or a configuration that cannot be read there, counts as off.
- **Only the landing command merges on it,** since only it makes every hold of point 3. The other merge commands of this capability, run directly, ask for each merge as before.
- **A mark that keeps a pull request off it.** The key obliges no merge. A pull request that carries this capability's hold label stays off the key until a person removes the label, such as a change that waits on its testing. No command of this capability removes the label, the one that makes a pull request ready among them. A word to the agent lasts only its session (DEC-006), and a draft only until that command makes the pull request ready (DEC-026), so the label is the lasting mark. A draft is never landed on the key either.

### 2. Where it is on, an agent's run that finds a pull request ready merges it

- **One run.** A run the key would cover, from a checkout point 6 allows, merges the pull request in that run. It does not stop at its ready line, and its last line says that the standing authorisation covered the merge.
- **A person at a terminal is asked,** as without the key. A dry run, and a run told not to wait, merge nothing.
- **A run authorised for a head** goes on as it does without the key.
- **A run authorised up front.** A run on the standing authorisation is one, so every hold that stops such a run stops it, such as a sentence on a document the change check does not mark updated (DEC-055 point 3, [project-management:DEC-065-answers-read-from-check] point 4). Point 3 adds holds of its own.
- **The review starts beside the checks.** Such a run stops on every `[person]` finding (point 3), so it starts the reviewers once the checks the project names have passed, as a run with no authorisation does ([project-management:DEC-063-task-builder] point 8, refined in place).
- **A verdict this run started.** On the local path, a verdict counts for a run on the key only where this run started that reviewer for the head, as the verdict shows. A verdict another session posted is an attestation this run did not make (DEC-028), so the run starts that reviewer itself.
- **Only the head its checks judged.** A run on the key never merges a head it did not judge. Where the base merges through a queue, it enqueues that head and waits for the merge, never returning before it (DEC-026, "Merging through a queue"). Where the wait ends first, it takes the pull request out of the queue and merges nothing. A merge the queue makes at another head is not one the key covered: the run says so, and what follows is [project-kit#3351](https://github.com/aleskalfas/project-kit/issues/3351)'s.
- **A head that moved.** Where the head moves before the merge, the run stops and merges nothing. A run again judges the new head from the start, on the same key: its checks, its review and every hold. So the agent may run it again on its own.
- **Its trail.** The merge's commit message carries a line naming the standing authorisation and the commit of the default branch whose configuration held the key on, at every audit setting. Where the audit setting is not `off` ([project-management:DEC-049-audit-journal-model] point 2), the run also posts that line on the issue as an audit comment before it merges. Where it cannot write either, nothing merges.

### 3. What governs merges, and what a person is owed, stays held

The standing authorisation covers none of the merges below. Each stops as it stops without the key, and goes on only as it would there.

- **A change to what governs merges.** A change to a file the methodology declares as governing how a change is reviewed and merged. The hold needs that set to take in:
  - each installed component's configuration, with this capability's topology of seats, members and review settings
  - the backbone configuration ([COR-048](../../../decisions/core/COR-048-backbone-configuration.md)), with its friction key and the delegate it names, and the agent overlay
  - the harness's permission settings, and the deployed definitions of the reviewers the merge gate can require
  - the continuous-integration workflows
  - the instructions and rules the harness loads, and the conventions corpus the reviewers judge by

  A record of the core layer decides how these are declared (point 7). Where nothing declares them, or a declaration cannot be read, no run merges on the key. A change whose only change there turns this key off is not held (point 5).
- **A change that turns the key on,** where the default branch's tip does not hold it on. Its ready stop, or its question at a terminal, shows the key's words (point 4), and no authorisation given before the person could see them covers it, as COR-064 point 2 has for the delegate.
- **What the project receives.** A change to a file the project receives from elsewhere, as the methodology's test of a synced copy tells it, or one that moves a version the project records ([COR-059](../../../decisions/core/COR-059-version-transition.md) point 1).
- **A build's head.** A head that holds a build's commits (DEC-063 point 7), read as the landing command reads them for [project-management:DEC-067-heads-that-start-programs] point 1.
- **A close beyond the Task.** A pull request whose closing references name any issue other than a Task in Review. The last pull request of an integration branch is one: it closes the issue that owns the branch, a close DEC-006 keeps the person's.
- **A review mode a label set.** A pull request whose review mode, as the merge gate resolves it, is weaker than the project default its base holds, or comes from a label on the issue ([project-management:DEC-027-review-modes]).
- **The records.** A change with any of these:
  - what COR-066 point 2's check reports, such as a proposed record or rule the change adds, whether or not the project turned that check's refusal on
  - a record or rule the change makes accepted, which COR-066 point 3 has the person see
  - an edit to an accepted record, which COR-066 point 5 has the person read
  - an edit to the file a rule set is authored in
- **A finding for the person.** Each `[person]` finding, even one the run found at its start, as at a later head (DEC-055 point 3).
- **Answers made apart.** A live revalidation on the base's tip that the change's answer did not read, which the run reports (DEC-055 point 3, "Answered apart").
- **An answer no change owes,** and each reason for having no anchors (COR-064 point 1). Such an answer is not held where three things hold:
  - the default branch's configuration names a delegate
  - the review configuration declares which reviewer checks these answers, and the merge gate requires that reviewer for the pull request (COR-064 point 4)
  - that reviewer checks that the delegate decided no answer it drafted (COR-064 point 3)

  It then reaches the person after the merge, as COR-064 point 5 has it. Otherwise each stays held.
- **Every other stop** the landing command makes, such as a failed check, a verdict that asks for changes, a merge with the base that the change check fails, or a head from elsewhere that needs a person (DEC-067).

The first of these takes in the holds other records make at every merge, such as the one on a change that turns DEC-069's switch on.

### 4. An install or an upgrade writes it as an offer, and the person turns it on

- **The upgrade writes the offer.** The upgrade to the release that builds this record runs a migration of this capability, a script of the lifecycle that the upgrade runs, not a manifest of [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline], which no upgrade runs. Where the project's configuration of this capability holds no such key, and no earlier run of it left its marker, it writes the key as offered, and leaves its marker. It never changes a value the project set.
- **Whoever runs the upgrade.** A transition writes each pending migration's writes that the records owning the content allow, and the person's choice of its target is the consent to them (COR-059 points 3 and 4). This record allows this write: an offer authorises no merge, so it asks no consent of its own.
- **An install** writes the key as offered too, for the same reason.
- **The key's words** say, in plain words, that once the key is on, agents will land each pull request whose review passes without asking, what stays held, how to turn it on and how to turn it off. The upgrade and the install print them, and say that the key is offered and authorises nothing yet.
- **The offer at a ready stop.** While the default branch's tip holds the key offered, a run the key would cover stops at its ready line, as with the key off, and shows the key's words with how to accept them. A run at a terminal shows them before its question. The agent shows the person that stop, as it shows any ready stop. The offer stops only a run that would have stopped anyway, and each such run shows it until the person answers.
- **The person's yes is a held change.** The person accepts by having a change set the key on, which point 3 holds and whose stop shows the key's words again. Only the person's authorisation of its merge covers it, given once they could see those words. Once it merges, every clone reads the key on at the default branch's tip, and no run asks again. The person's no sets the key off, and no run asks again either.
- **Where no upgrade runs.** A project that takes no upgrade of this capability gets the key through a change that writes it, held as any change to the key.
- **Turning it off** is setting it off. An absent key reads as off too, and the marker keeps a replay from writing the offer back.

### 5. A person turns it off at once

- **No hold.** A change that turns the key off is not held, since it only narrows what merges.
- **At once.** The key counts as off where this capability's configuration sets it off in a working tree, committed or not: the working tree of the checkout the landing command runs from, or the clone's main working tree, as DEC-069 point 4 reads its switch.
- **For one pull request.** A run told to stop ready stops there, as without the key, and the person authorises that merge for its head. The hold label keeps a pull request off the key for longer (point 1).
- **With several people.** The change that turns the key on covers the landing runs of every clone, whoever runs them, each under that person's own credentials. In the human review mode (DEC-027), a member's approving review is a verdict the merge gate requires, so a run on the key merges once it and every other required verdict approve the head. Each person turns the key off for their own runs at once, from their own working tree, and any person turns it off for everyone by a change.

### 6. The run judges from the base's tip

- **Where it runs.** A run on the standing authorisation runs only from a checkout whose commit is the tip of the pull request's base, and whose working tree differs from that commit in no tracked file, save a change that only turns the key off (point 5). So the landing command, the merge gate's settings, the reviewers' definitions, the instructions loaded by the reviewers it starts, and the backbone code the tree supplies are all the base's, and none of the head's files judges the head.
- **Elsewhere it stops ready,** naming why, such as a checkout on the head's branch or behind the base's tip, or a working tree with changes. The agent may bring its checkout to the tip and run again on its own.

### 7. What stays open

- **The person is told after.** A run on the standing authorisation prints what the person is told of the change's answers, and the count line of what waits on them ([project-management:DEC-056-drift-fixers] point 6), and merges in the same run. The description carries only the authors' sentences (DEC-065 point 1). So the person learns what is left out of date, and what waits on them, only where the agent passes on the run's printout, as this capability's guidance to the agent that lands work obliges it to do ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 3).
- **Who decided or drafted an answer.** The run cannot tell who decided an answer no change owes (COR-064 point 4). The reviewer's check that the delegate decided none of its own drafts reads what the change shows of who drafted each. An answer a person decided passes too, and that person read it word for word before it was written.
- **The local path's verdicts.** A verdict this run started is still a comment the session's own command posts under the person's account. DEC-028 accepts it as an attestation, not a proof ("Allowlist as attestation, not security"). With the key on, nothing but the session's honesty stands behind what such a verdict shows of the run that started it.
- **Labels choose reviewers too.** The reviewers a capability contributes are chosen by the classification of the issues a pull request closes ([project-management:DEC-032-conditional-reviewer-requirements]), which labels carry and any session can write. A label that drops such a reviewer is not held.
- **What the hold covers.** In a project that builds its own tooling, the code that judges a merge, such as the landing command's own, is neither received nor declared as configuration. A change to it merges on the key there, and judges each later merge.
- **What the checkout cannot show.** The run compares tracked files only (point 6). What lies outside them still judges: settings and instructions kept outside the repository, files the project does not track, and a tool installed on the machine where it is not the version the tree records.
- **Paths not yet declared.** Nothing yet declares what governs merges. [project-kit#3389](https://github.com/aleskalfas/project-kit/issues/3389) proposes the core record that decides it, and this record's build lands no earlier, so no run merges on the key before it can tell such a change.
- **Merges the hold does not see.** A direct commit to the default branch, or a merge outside this capability's commands, passes no hold (DEC-069 point 5).
- **A terminal tells that one is attached,** not that a person watches. A person who runs the landing command with its output piped, or from a task runner, is not at a terminal by that test, so their run merges on the key without asking.
- **Taking a pull request out of a queue** races the queue, so it may merge first (DEC-026). A merge at a head the run did not judge is #3351's.
- **Words that reach nobody.** The upgrade's words may reach nobody, where an agent runs it. Nothing rests on them, since the offer authorises nothing.

## Rationale

**Why a standing authorisation.** Authorising a merge stays the person's (COR-064 point 6). This record keeps it so, and lets the person give that word once for every merge whose review passes, where nothing is owed to them. No reviewer's verdict stands in for the person: the key is the person's own choice, made by a change they authorise. Asked at each merge, the work would wait on a word the person chose to give once, the wait the maintainer asked to end.

**Why the person's yes is a held change, not the upgrade.** A consent at the upgrade would be whoever ran it. An agent may run the upgrade, or choose its target for the person, and its words may then reach nobody, while COR-064 point 6 keeps every consent a record asks the person's. An offer authorises nothing, so the upgrade may write it in every project, whoever runs it. The person meets the offer where they already authorise merges, at a ready stop, and their yes is the act by which they authorise any merge, taken once they could see what it turns on and kept in configuration every clone reads.

**Why an offer in every project.** A project that wants no standing authorisation loses nothing: every merge there stays the person's, and the words at its ready stops end once its person sets the key off. A project that wants it gets it through one change its person authorises, with the words before them. So the default suits any project, since it widens nothing until that project's own person accepts it. DEC-069's and DEC-072's switches widen what runs with nobody watching, and no upgrade offers them. A merge on the key lands only what the checks and the required reviewers passed, with point 3's holds kept, in the open with its verdicts and its trail, and a change reverts what it merged, though not what the merge set off, such as a deployment or an issue's close. So it is offered where those switches stay silent, and like them, only the person's own change turns it on.

**Why an absent key reads as off.** A project where nothing wrote the key, such as one whose upgrade has not run, merges as it did, each merge authorised. Read as on, the key would authorise merges in every project from the moment its tooling carried this record's build, before anyone said anything. The switches of DEC-069 and DEC-072 likewise read an absent setting as off. The marker keeps the absent key absent, where a person removed it.

**Why what governs merges stays held.** A change to the merge gate's settings, the topology, the reviewers, the instructions they load or the delegate would weaken the gate that judges every later merge. Held, each such change still reaches the default branch only on the person's word. So what those records rest on stays true: what binds is configuration a person reviewed (DEC-058 point 1), the allowlists stay the project's attestation (DEC-028), and the delegate is shown before it counts (COR-064 point 2). Only a component knows which of its files configure it, and a declaration nobody made says nothing, so where none can be read no run merges on the key.

**Why what the project receives stays held.** In a project that receives the methodology, each upgrade replaces the landing command, the rules, the skills and the reviewers' definitions, which judge every later merge. Held, each upgrade's change reaches the person with what it brings. An ordinary change touches no received file, since the project edits none ([COR-001](../../../decisions/core/COR-001-content-mechanisms.md)), so the hold costs it nothing.

**Why a build's head stays held.** A build's commits run only in a sandbox until a person reviews them (DEC-063 point 7). A seat's tree follows the default branch, so a build merged on the key would run there outside the sandbox. Every build of a worker's Task goes through the build command (DEC-063 point 1), so in a project with seats the key covers none of a worker's merges. It covers the pull requests made outside that command, such as a lead's or those of a person's own session, and costs a project with no seats nothing.

**Why a close beyond the Task stays held.** DEC-006 keeps the close of a container the person's, and a parent that becomes eligible to close never closes on its own. A merge into the default branch closes every issue its pull request names, so a merge that names more than its Task would make that close.

**Why a review mode a label set stays held.** The review mode decides which kind of reviewer satisfies the gate (DEC-027). A label any session can write would otherwise lower it below what the project's reviewed configuration sets, so in a project that asked for human review, the key would merge a change no person reviewed.

**Why the records stay held.** COR-066 has the person see what a change makes accepted, and read each edit to an accepted record, before it lands. A proposed record that lands binds nothing, but reads like a decision, and where a project's refusal is off, the person's word at the merge is its only check. No command yet tells which edits to a rule set alter an accepted rule, so the file the set is authored in stands for it.

**Why every `[person]` finding stops it.** DEC-055 lets a run authorised for a head merge on a finding it found at its start, since the person is shown each finding before they give that authorisation. The standing authorisation came before any finding existed, so no finding was shown before it. As at a later head, the run cannot tell what the person saw.

**Why answers made apart stop it.** COR-062 point 7 has the person told of them before the merge, and lets a component through which the merge is authorised stop on them. A run on the key tells the person only after, so it stops instead. Such answers are rare, so the stop costs little.

**Why an answer the delegate decided passes.** Showing such an answer at the merge does not make it valid: authorising a merge does not accept it (DEC-055 point 3). The delegate decided it in the person's place, and a reviewer the merge requires checked it, and checked that the delegate decided none of its own drafts (COR-064 points 3 and 4). The person is told afterwards (COR-064 point 5). Where nothing declares that reviewer, the run cannot tell that one checked, so the answers stay held.

**Why a verdict this run started.** A verdict on the local path is a comment under the person's account, which any session can post. One whose reviewer the run itself started for the head rests on no other session's word.

**Why the run judges from the base's tip.** The key is read at the default branch, so no change turns on its own key. A command run from a tree that holds the head is the head's own (DEC-067 point 6), and so are the backbone code that tree supplies and the instructions its reviewers load, so a comparison made there shows nothing. Run from the base's tip, the gate that judges a change is the one a person let in, as the delegate's definition (COR-064 point 2) and the topology of seats (DEC-059 point 1) are read there.

**Why only the landing command.** It alone prints the findings, what the person is told of the answers and the accepted records the change alters, and makes the holds of point 3. A merge command that shows none of them would merge on an authorisation given before anything was there to see.

**Why the review starts beside the checks.** DEC-063 point 8 holds back the reviewers of a run authorised up front only so that its next run cannot merge on a finding nobody was shown. A run on the standing authorisation stops on every finding, so that cannot happen. Holding its review back would add the whole suite's time to every landing in every project with the key on.

**Why a terminal asks.** The maintainer asked that the agent not wait on him. A person who runs the landing command at a terminal is there to answer, and keeping the question keeps their habit: a run with no authorisation for a head merges nothing until they say so.

**Why a trail in the commit and on the issue.** An authorisation-bearing move leaves its source on the issue (DEC-026, "Audit-trail comments"). A project whose audit setting is `off` posts no comment, so the commit's line keeps the source there too, for every later reader of the history.

**Why a label marks a pull request off the key.** A change that waits on its testing must not land on the key. A word to the agent ends with its session, and a draft ends when the pull request is made ready, so only a mark no command of this capability clears outlasts both.

**Why a queue's wait ends with the pull request out.** Left queued, it would merge with nobody watching, after the run that judged it had ended.

**Why off at once, with no hold.** Turning the key off only narrows what merges, so it needs no consent, and is safe to read from any working tree, as DEC-069 point 4 reads its switch.

### Alternatives considered

- **A setting on the person's machine only.** Not taken. It is not reviewed, and no other clone or sandbox reads it, as DEC-059 found of a topology kept per user. An agent's session on that machine could write it with no merge to hold it.
- **Once per session.** Not taken. Each session would ask again, the wait the maintainer asked to end, and a word given in a session leaves nothing another clone or a later reader can see.
- **An absent key read as on.** Not taken, as "Why an absent key reads as off" says.
- **The key written on at the upgrade, running it the consent.** Not taken. Whoever ran the upgrade would consent, an agent among them, as "Why the person's yes is a held change" says.
- **The key written on only where the upgrade runs at a terminal, or under an explicit flag.** Not taken. The key would differ between projects by who ran the upgrade, and at a terminal its words arrive among a long report. A ready stop meets the person where they authorise merges.
- **Off with no offer, turned on only by the person's own change, as DEC-069's switch is.** Not taken. The key would wait on the person finding it. The offer reaches them at the first stop it would spare, and widens nothing until they accept.
- **The consent at the merge of the upgrade's change.** Not taken. The older landing command usually lands that change, so nothing shows the key's words there, and an install's change merges before the capability is there to hold anything.
- **A list of named holds, with whatever else a record has the person see.** Not taken. No command can test for "whatever else", and a list goes stale as records add holds. One rule on what governs merges takes them in.
- **Holding every answer no change owes.** Not taken. Where a delegate decides them and a declared reviewer checks them, the hold would make the person wait on answers their word does not validate.
- **DEC-055's findings' hold for a run on the standing authorisation.** Not taken. A finding the run found at its start would merge with nobody shown it.
- **Reading the review settings from the working tree, or comparing it with the base's tip from any checkout.** Not taken. From a tree that holds the head, the head's own code would make the comparison, and its reviewers would load the head's instructions.
- **Every merge command merging on it.** Not taken, as "Why only the landing command" says.
- **The host's own automatic merge.** Not taken. The host merges once its own required checks pass, and none of the landing command's holds run: not the findings, the answers, the records, the configuration or the merge check.
- **A draft as the only lasting mark.** Not taken, as "Why a label marks a pull request off the key" says.

## Implications

- **Edits that change what a record decides,** made in this change once this record is accepted, and accepted with it (COR-066 point 5):
  - **DEC-006's top line** names this record beside DEC-062, reading *Partially superseded by [project-management:DEC-062-axes-chosen-in-the-map] and [project-management:DEC-080-standing-merge-authorisation]*. After what it says of DEC-062, it says in the line itself: "Where the project's configuration turns the standing authorisation of merges on, a merge the landing command makes of a pull request whose review passes, with nothing held for a person, is authorised once for every such merge, across issues and sessions. That holds for a merge into the default branch, and for a Task's merge into an integration branch (DEC-080). Overturned there: the Authorisation gates' 'per-PR approval' for Review → Done, the `pr-merge-into-main` path's 'user authorises merge' and the same step of the `pr-merge-into-integration` path, and 'per-issue and in-session — no standing "go ahead with everything" applies in a later turn'. Each stands for every other move and every other merge." The rest of DEC-006 stays as it stood.
  - **DEC-055's sentence** "An authorisation to merge is given for the head the landing command's ready stop names", in its Context and in point 3's "A later head", reads "An authorisation to merge one pull request is given for the head the landing command's ready stop names". Point 3's "How long it lasts" reads "This sets which heads an authorisation given for a head covers, not how long it lasts (DEC-006). The standing authorisation of merges names no head, and covers what DEC-080 decides (refinement per DEC-080)." Point 3's "The findings' hold" ends "A run on the standing authorisation of merges merges on no such finding, even one it found at its start (refinement per DEC-080)." The Decision's headline sentence "On an authorisation given up front, it merges only if…" takes the pointer "(refinement per DEC-080)".
  - **DEC-063 point 7's second bullet** ends "…so the seat's own tools, settings, hooks and instructions are always code a person reviewed, save, in a project that builds its own tooling, the code that tooling runs, which may merge on the standing authorisation of merges (refinement per DEC-080)."
  - **DEC-063 point 8's fourth bullet** reads "A run authorised up front for a head starts no reviewer before every check has passed. A stop between its verdicts and the findings' step would let its next run merge on a `[person]` finding nobody was shown (DEC-055 point 3). A run on the standing authorisation of merges stops on every such finding, so it starts the reviewers as a run with no authorisation does (refinement per DEC-080)."
  - **DEC-026's "Audit-trail comments"** gains a form for the landing command's merge on the standing authorisation: `Merge authorised by the project's standing authorisation of merges, read at <commit of the default branch>` (refinement per DEC-080).
- **Edits that change no record's decision,** made in this change once this record is accepted, since each cites it:
  - **DEC-057's bullet** "A person schedules work, and authorises each close and each landing" reads "A person schedules work, and authorises each close and each landing, a landing for its pull request or once for every landing the standing authorisation of merges covers ([project-management:DEC-080-standing-merge-authorisation])". Its Rationale's "the person holds both ends" stands, since the key is the person's own word.
  - **DEC-063 point 8's last bullet** reads "The person authorises the merge, for its head or through the standing authorisation of merges (DEC-080)." Its "Stands" names "the person's authorisation of each merge, for its head or through the standing authorisation of merges (DEC-080)".
- **Edits the build makes,** changing no record's decision:
  - **The workflow schema's Review → Done** says in its reason and notes that the user authorises the merge for each pull request, or once for every merge the standing authorisation covers. For a merge on the key, the cross-authority artefact its gate asks for ([COR-033](../../../decisions/core/COR-033-process-substrate.md) P4) is the key as the default branch holds it, which a change the person authorised turned on. The merge's trail names that commit.
  - **The project-manager agent's** line on standing authorisations says it acts on none across sessions save the standing authorisation of merges, and on that one only through the landing command.
  - **The project-manager agent's storyboard,** where its worker "merges nothing", says the key leaves that so: the worker's pull request holds a build's commits, which point 3 holds for the person.
  - **The pm skill's landing step** says that where the key is on, one run lands a pull request whose review passes, from a checkout at the base's tip, that a run at a terminal asks, and that a run stopped on a hold is shown to the person and authorised for its head as before. Where the key is offered, the agent shows the person the key's words with the stop, and on their yes makes the change that sets it on. After a merge on the key, the agent passes on to the person what the run printed: what changed, what is left out of date until which follow-up, each answer the delegate decided, and the count line of what waits on them. Its sentence that an authorisation is per-issue and in-session names the standing authorisation beside it.
  - **The pm skill's exit-code guidance:** its "run again without `--yes`" under exits 2, 6 and 7 says that where the key is on, such a run merges, which stays safe since it stops on every finding. Under exit 3, the agent may run the landing command again on its own where the key is on, and that run judges the new head from the start (point 2). Under exit 8, it names the holds of point 3, and a checkout not at the base's tip, after which the agent may bring its checkout to the tip and run again (point 6).
  - **The pm skill's worker loop** says that the standing authorisation covers none of a worker's pull requests, since each holds a build's commits (point 3), so the worker lands one only on the person's authorisation for its head, as before.
  - **The capability's configuration** gains the key, and a declaration of which reviewer checks the answers no change owes (point 3). Its labels gain the hold label (point 1).
  - **The capability's README,** in "Landing a pull request in one command", says what points 1 to 7 decide. Its account of the project configuration names the key and its offer, and its lists of what each merging command holds name point 3.
  - **The analysis's use cases and journeys of landing** follow, as the change check asks of them.
- **A follow-up, [project-kit#3389](https://github.com/aleskalfas/project-kit/issues/3389),** proposes the core record by which each component declares its own configuration files, never a whole tier of the tree, and the backbone collects them with its own configuration file, the agent overlay, the adapter's permission settings and the definitions it deploys, the host's workflows, and the instructions, rules and conventions corpus point 3 names. This record's build lands with or after it, and the build's changeset raises `requires_backbone` to the release that carries it.
- **Records that stand,** each kept true by what this record holds or passes on:
  - What binds is configuration a person reviewed (DEC-058 point 1), and the topology is read at the default branch (DEC-059 point 1). Point 3 holds every change to them.
  - A head from elsewhere, or one that holds a build's commits, starts no program until a person reviews it (DEC-067 point 1). Point 3 holds a build's head, and keeps every stop DEC-067 makes.
  - The delegate is shown before it counts (COR-064 point 2). Point 3 holds a change that names it.
  - A local verdict is an attestation the developer accepts (DEC-028, "Allowlist as attestation, not security"). On the key the run itself started each such reviewer, and the person who turns the key on accepts such verdicts ahead of time, which point 7 states.
  - The person meets, at each merge, the count line of what waits on them (DEC-056 point 6, DEC-069 point 4, and DEC-072's reason for leaving its names in the run's output). After a merge on the key, the agent passes that line on (point 7).
- **A surface change** once built: a new key and its offer, point 4's migration, the hold label, a landing that merges with no second run, and its trail, each declared by the build's changeset.
- **Acceptance:** this record partially supersedes the accepted DEC-006, and refines DEC-026, DEC-055 and DEC-063 in place, so accepting it needs the maintainer's sign-off.
