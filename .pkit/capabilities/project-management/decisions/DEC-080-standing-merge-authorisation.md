---
id: DEC-080
title: A project setting, on by default, authorises up front every merge whose review passes
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a key in this capability's project configuration authorises, once and ahead of time, every merge into the default branch of a pull request whose checks all passed and whose required reviewers all approve its head. Where the key is on, the landing command merges such a pull request in the run that finds it ready, and the agent that brought it to review lands it without being asked. The key covers no merge where a person is owed something first: a reviewer's finding left for the person, an answer only a person decides, a decision record or rule the change makes accepted or alters, the changes other records hold at every merge, and a change that turns this key on. Those stop as they do today. A new install writes the key on, an upgrade writes it on wherever a project's configuration lacks it, and the merge of that change waits for the person to authorise it themselves. A person turns the key off at once, with no hold. This partially supersedes [project-management:DEC-006-state-machine-and-cascade], whose authorisations are per-issue and in-session.

## Context

**Terms.**

- **The landing command** is this capability's command that lands an issue's pull request in one run. It waits for the checks, has the reviewers review the head, prints what the person is told, checks the merge with the base, and merges ([project-management:DEC-026-work-ownership-lifecycle], [project-management:DEC-055-pr-lists-answers]).
- **A pull request's review passes** where every check on its head has passed, and every reviewer the merge gate requires has a verdict that approves that head and stands for it ([project-management:DEC-028-agent-as-approver-paths]). A reviewer the person overrode ([project-management:DEC-050-per-reviewer-override]) has no such verdict.
- **A run authorised up front** is a run of the landing command given its authorisation before it starts, as DEC-055 point 3 uses the term.
- **The standing authorisation of merges** is the authorisation this record's key gives. **Held:** a merge is held where the landing command stops it ready, or refuses it, until a person acts.

**What stands today.** DEC-006 makes Review → Done the person's, per pull request, and every authorisation per-issue and in-session: no standing go-ahead applies in a later turn. So the landing command stops at every ready pull request, naming its head, and the agent runs it again with the person's authorisation for that head. Most such stops ask the person nothing: the checks passed, the reviewers approved, and no finding waits for them.

What a run authorised up front meets is decided elsewhere:

- **Findings.** It merges on a `[person]` finding only where it found the finding's verdict at its start, standing for the head, since the person is shown each finding before giving that authorisation. An authorisation for one head covers a later head only where nothing there needs the person (DEC-055 point 3).
- **Records.** The person who authorises a merge sees first each record and rule the change makes accepted, and each edit to an accepted record ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) points 3 and 5).
- **Switches.** No authorisation given up front covers a change that turns on the switch of [project-management:DEC-069-when-fixers-start] or of [project-management:DEC-072-sync-gives-missing-cards]. Each command of this capability that merges holds such a change until the person authorises that merge themselves.

**What the maintainer asked.** The maintainer said he never wanted to authorise each merge, and that a change whose review passed should merge at once ([project-kit#3385](https://github.com/aleskalfas/project-kit/issues/3385)). Offered three places for a standing authorisation, he chose a setting in the project's committed configuration for this capability, set on by default, and asked that the release that brings it write it on in each project's configuration at upgrade. The question put to him said that the agent would still stop for a finding a reviewer left for him, and for a change that accepts or alters a decision record.

## Decision

**A key in this capability's project configuration, written on by an install and by an upgrade, authorises up front every merge into the default branch that the landing command makes of a pull request whose review passes, where nothing is held for a person. Where the key is on, the landing command merges such a pull request in the run that finds it ready. The key covers no merge where a person is owed something first. A change that turns it on waits for the person at its merge, and turning it off counts at once.**

### 1. The key is the person's authorisation of each merge whose review passes

- **What it authorises.** Every merge into the default branch, made by the landing command, of a pull request whose review passes, where point 3 holds nothing. It is the person's authorisation of Review → Done for each such merge, given once for them all, across issues and sessions. Every other move DEC-006 gives the person stays per-issue and in-session.
- **The ask to land, too.** Where the key is on, the agent that brought a pull request to Review runs the landing command on it without waiting to be asked. A role still authorises nothing, since the key is the person's ([project-management:DEC-059-topology-of-seats] point 8).
- **Where it is read.** In the configuration at the tip of the pull request's base, as the landing command fetches it, never at the pull request's head. A key that is absent, or a configuration that cannot be read there, counts as off.
- **Only the landing command merges on it,** since only it makes every hold of point 3. The other merge commands of this capability, run directly, ask for each merge as before.
- **It obliges nothing.** A rule of the project's that keeps a change off the default branch for a time still keeps it off.

### 2. Where it is on, the run that finds a pull request ready merges it

- **One run.** A run of the landing command with no authorisation for a head merges a pull request whose review passes where nothing is held, in that run. It neither stops at its ready line nor asks at a terminal, and its last line says that the standing authorisation covered the merge. A dry run merges nothing.
- **A run authorised for a head** goes on as it does without the key.
- **A run authorised up front.** A run on the standing authorisation is one, so every hold that stops such a run stops it, such as a sentence on a document the change check does not mark updated (DEC-055 point 3, [project-management:DEC-065-answers-read-from-check] point 4). Point 3 adds the holds such a run does not meet today.
- **The review starts beside the checks.** Such a run stops on every `[person]` finding (point 3), so it starts the reviewers once the checks the project names have passed, as a run with no authorisation does ([project-management:DEC-063-task-builder] point 8, refined in place).

### 3. A merge where a person is owed something first stays held

The standing authorisation covers no such merge. It stops as it stops without the key, and goes on only as it would there:

- **What a person judges, decides or consents to.** Each `[person]` finding, each answer the change check did not ask for, each reason for having no anchors, and each change to the fixers' grant list ([project-management:DEC-056-drift-fixers] point 2). The run stops on each, even one it found at its start, as a run at a later head does (DEC-055 point 3).
- **What a record has the person see before the merge.** Each record and rule the change makes accepted, and each accepted record or rule it alters (COR-066 points 3 and 5, RS-OPS-002). So too a change to the key that turns the refusal of proposals on or off (COR-066 point 4), and whatever else an accepted record has the person who authorises a merge see before they authorise it.
- **What other records hold at every merge.** The changes DEC-069 point 4 and DEC-072 point 3 hold, held as they hold them, and a change that turns this key on (point 4).
- **Every other stop** the landing command makes, such as a failed check, a verdict that asks for changes, a merge with the base that the change check fails, or a head from elsewhere that needs a person ([project-management:DEC-067-heads-that-start-programs]).

### 4. On by default, and turned on only where the person sees it

- **Written on.** A new install's configuration carries the key on. The upgrade to the release that builds this record writes it on into each installed project's configuration, through a migration that writes only where the key is absent, so a value the project set stays. A replay of that migration writes it on again where a project removed the key. So a project turns the key off by setting it off, never by removing it, and the release's notes say so, as the rule on migrations asks of one that adds a missing default (RS-OPS-005).
- **Held at every merge.** Each command of this capability that merges a change into the default branch holds a change that turns the key on, from off or from absent, until the person authorises that merge themselves, which no authorisation given up front covers. The hold takes the form of DEC-069 point 4's, and says in plain words what turning the key on means. So the change an install or an upgrade makes is held, and in each project the person sees the key turned on once, at its merge.

### 5. A person turns it off at once

- **No hold.** A change that turns the key off is not held, since it only narrows what merges.
- **At once.** The key counts as off where this capability's configuration sets it off in the working tree of the checkout the landing command runs from, committed or not, as DEC-069 point 4 reads its switch.
- **For one pull request.** A run told to stop ready stops there, as without the key, and the person authorises that merge for its head.

### 6. What stays open

- **The person is told after.** A run on the standing authorisation prints what the person is told of the change's answers, and merges in the same run. So the person reads what changed and what is left out of date after the merge, in the run's output and the description, as information ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 3).
- **Merges the hold does not see.** A direct commit to the default branch, or a merge outside this capability's commands, passes no hold. So an install or an upgrade committed straight to the default branch turns the key on unheld, and only the commit's author vouches that the person saw it. Inside a command, a terminal tells only that one is attached (DEC-069 point 5).
- **As strong as the review.** The key adds no reviewer. A merge it covers rests on the checks and the verdicts the merge gate requires, and on nothing else.

## Rationale

**Why a standing authorisation.** A merge whose review passed, with nothing held, asks the person nothing they judge: the checks and the reviewers judged the change, and no finding waits for them. Asking each time makes the work wait on a word that adds no judgement, which the maintainer never wanted. What only a person can settle still stops the merge (point 3), so the person's time goes where their judgement is needed.

**Why the project's committed configuration.** It is reviewed, and every clone and every session reads the same key from the default branch, as every clone reads the topology of seats (DEC-059 point 1). A change that turns the key on passes a merge the person authorises themselves, so no agent turns it on unseen.

**Why on by default, where DEC-069's and DEC-072's switches are off.** Those switches widen what happens with nobody watching: an agent's run unconfined, or a guess on the board that every command reads. This key takes away no check, reviewer or hold that a merge passes through, only the person's word on a merge that needs none. The maintainer asked that projects run so from their install and their upgrade. The hold on the change that writes the key keeps the authorisation each project's person's own, given once where they see it.

**Why an absent key reads as off.** A project where nothing wrote the key, such as one whose upgrade has not merged, merges as it did, each merge authorised. Read as on, the key would authorise merges in every project from the moment its tooling carried this record's build, before any change wrote it or any person saw it. Point 4's hold would never meet a change, since none would turn the key on from off. The switches of DEC-069 and DEC-072 likewise read an absent setting as off.

**Why every `[person]` finding stops it.** DEC-055 lets a run authorised for a head merge on a finding it found at its start, since the person is shown each finding before they give that authorisation. The standing authorisation came before any finding existed, so no finding was shown before it. As at a later head, the run cannot tell what the person saw. The same holds for an answer only a person decides, and for a change to the grant list.

**Why only the landing command.** It alone prints the findings, what the person is told of the answers and the accepted records the change alters, and makes the holds of point 3. A merge command that shows none of them would merge on an authorisation given before anything was there to see.

**Why the review starts beside the checks.** DEC-063 point 8 holds back the reviewers of a run authorised up front only so that its next run cannot merge on a finding nobody was shown. A run on the standing authorisation stops on every finding, so that cannot happen. Holding its review back would add the whole suite's time to every landing in every project with the key on.

**Why off at once, with no hold.** Turning the key off only narrows what merges, so it needs no consent, and is safe to read from any working tree, as DEC-069 point 4 reads its switch.

### Alternatives considered

- **A setting on the person's machine only.** Not taken. It is not reviewed, and no other clone or sandbox reads it, as DEC-059 found of a topology kept per user. An agent's session on that machine could write it with no merge to hold it.
- **Once per session.** Not taken. Each session would ask again, the wait the maintainer asked to end, and a word given in a session leaves nothing another clone or a later reader can see.
- **An absent key read as on.** Not taken, as "Why an absent key reads as off" says.
- **Off by default, turned on only by the person's own change, as DEC-069's switch is.** Not taken. The maintainer asked for it on in every project, and point 4's hold keeps it the person's.
- **DEC-055's findings' hold for a run on the standing authorisation.** Not taken. A finding the run found at its start would merge with nobody shown it.
- **Every merge command merging on it.** Not taken, as "Why only the landing command" says.

## Implications

- **Edits that change what a record decides,** made in this change once this record is accepted, and accepted with it (COR-066 point 5):
  - **DEC-006's top line** names this record beside DEC-062, reading *Partially superseded by [project-management:DEC-062-axes-chosen-in-the-map] and [project-management:DEC-080-standing-merge-authorisation]*. After what it says of DEC-062, it says in the line itself: "Where the project's configuration turns the standing authorisation of merges on, a merge into the default branch that the landing command makes of a pull request whose review passes, with nothing held for a person, is authorised once for every such merge, across issues and sessions (DEC-080). Overturned there: the Authorisation gates' 'per-PR approval' for Review → Done, and 'per-issue and in-session — no standing "go ahead with everything" applies in a later turn'. Both stand for every other move and every other merge." The rest of DEC-006 stays as it stood.
  - **DEC-055's sentence** "An authorisation to merge is given for the head the landing command's ready stop names", in its Context and in point 3's "A later head", reads "An authorisation to merge one pull request is given for the head the landing command's ready stop names". Point 3's "How long it lasts" reads "This sets which heads an authorisation given for a head covers, not how long it lasts (DEC-006). The standing authorisation of merges names no head, and covers what DEC-080 decides (refinement per DEC-080)."
  - **DEC-063 point 8's fourth bullet** reads "A run authorised up front for a head starts no reviewer before every check has passed. A stop between its verdicts and the findings' step would let its next run merge on a `[person]` finding nobody was shown (DEC-055 point 3). A run on the standing authorisation of merges stops on every such finding, so it starts the reviewers as a run with no authorisation does (refinement per DEC-080)."
- **Edits that change no record's decision,** made by the build once this record is accepted:
  - **The project-manager agent's** line on standing authorisations says it acts on none across sessions save the standing authorisation of merges, and on that one only through the landing command.
  - **The pm skill's landing step** says that where the key is on, one run of the landing command lands a pull request whose review passes, and that a run stopped on a hold is shown to the person and authorised for its head as before. Its sentence that an authorisation is per-issue and in-session names the standing authorisation beside it.
  - **The pm skill's worker loop** says that where the key is on, the worker lands each pull request of its own once its review passes, and merges on the person's authorisation for a head only where the landing stops for them.
  - **The capability's README,** in "Landing a pull request in one command", says what points 1 to 6 decide, and its account of the project configuration names the key.
  - **The analysis's use cases and journeys of landing** follow, as the change check asks of them.
- **A surface change** once built: a new key, point 4's migration, and a landing that merges with no second run, each declared by the build's changeset.
- **Acceptance:** this record partially supersedes the accepted DEC-006, and refines DEC-055 and DEC-063 in place, so accepting it needs the maintainer's sign-off.
