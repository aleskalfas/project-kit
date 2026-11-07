---
id: COR-071
title: A person sets, for each area of work, how much agents decide in a person's place
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person chooses how much the agents decide without asking. The choice is a *level*, set for the whole project and, where the person wants, for an area of work, such as one component's files. There are three levels. At the lowest, a person decides each question. One level up, the agent the person named as delegate decides the answers on artefacts that no change owes, and a reviewer checks each. At the top, a change in the area merges without asking once its checks and its reviewers pass and nothing in it needs a person. The setting lives in the project's committed configuration, counts as the default branch holds it, and only a person changes it. Some things never move past a person at any level: the setting itself, every grant and consent, accepting a decision, a finding a reviewer left for a person, and whether a change was meant. Nor does a change that alters what the merge and its checks run on. The person is told afterwards what an agent decided in their place.

## Context

Several records keep a question for a person, each in its own way.
- **Answers on artefacts.** The answers no change owes are a person's, unless the person names a delegate to decide them ([COR-064](COR-064-answer-delegate.md) point 1).
- **Authorising a merge.** A change reaches the default branch on a person's authorisation (COR-064 point 6), given for that change. Before the merge, the person sees what the change makes accepted ([COR-066](COR-066-accepted-before-landing.md) point 3).
- **Accepting a decision.** A record or a rule is accepted by a person in the change that proposes it (COR-066 point 1).
- **Other questions.** Records keep many more for a person, such as when planned work is scheduled or closed, which agent may run on its own, and how a finding a reviewer left for a person is settled.

A person who trusts the agents with an area of work cannot say so anywhere that lasts. A grant given in words, such as "merge what passes review", lives in no file. Each session starts again from asking, and an agent in another clone never hears it. So the person is asked, many times a day, to accept answers and authorise merges they could judge only by redoing the reviewers' work. That is the rubber stamp the anchors-and-friction record guards against ([COR-050](COR-050-anchors-and-friction.md) point 3).

The questions differ in what can stand in for the person.
- **A check of files.** An answer says whether an artefact still holds against what it rests on, and a reviewer can check that against the same files.
- **A class the person can name.** Whether a change may merge can be settled in advance for a class of change: one confined to an area, passing every check and every reviewer, and carrying nothing a person must judge.
- **A choice no file settles.** Whether the project wants a decision, or meant a change, rests on what people intend. No file records it, so no check of files reaches it.

## Decision

**A person sets a level for the project, and for any area of work, in committed configuration: ask, answer, or land, where a change that passes every check and reviewer and holds nothing for a person merges on a standing authorisation. Nothing that widens what agents may do, and no choice that no file settles, moves past a person, who is told afterwards what was decided in their place.**

### 1. The setting holds a level for the project and for each area

The *setting* is one value of the project's configuration. It holds:
- **the project's level,** which applies wherever no area does, whichever agent asks and in whichever session;
- **any number of areas,** each with a level of its own.

An *area of work* names files, as a path anchor names them (COR-050 point 2). An area may instead name an item of planned work, such as a feature, where a component that plans work says how a change is matched to it. Such an area may only lower the level. The links that tie a change to planned work lie outside the default branch, where a change can write them, so no link ever raises the level.

With no setting, the project stands at the lowest level. A project that names a delegate and sets no level stands at the second level for the whole project, as COR-064 has it.

### 2. Three levels, each holding the ones below

1. **Ask.** A person decides every question this record covers.
2. **Answer.** The delegate decides the answers no change owes (COR-064 point 1), and a reviewer checks them (COR-064 point 4).
3. **Land.** A change also merges on a standing authorisation, under point 5's conditions.

Where no delegate is named, the second level hands on nothing. The third still gives its standing authorisation, which needs no agent to decide.

### 3. Which level a question takes

Each file a question touches takes the level of the areas that hold it, the lowest where several do, or the project's level where none does. The question takes the lowest level among its files, and no higher than any area of planned work it is matched to. So an area raises the level only for a question wholly inside areas at that level, and it lowers the level for any question that reaches into it.

What a question touches:
- **an answer:** the artefact it answers on;
- **a merge:** every file the change alters, save the answer files it adds for its own answers ([COR-062](COR-062-answers-in-own-files.md) point 1), which take no level of their own;
- **another record's question:** what that record says (point 8).

### 4. What each level hands to agents, and what checks the agent's choice

| Question | Lowest level that hands it to agents | What checks the agent's choice |
|---|---|---|
| An answer no change owes, or a reason for having no anchors | Answer | The reviewer of answers, from the change check's own list (COR-064 point 4) |
| A merge's authorisation | Land | No agent chooses. The component that carries out merges applies the class the person named, under point 5's conditions: the project's checks, each reviewer the merge waits for, and the landing check (COR-066 point 2) |
| A record's or a rule's acceptance, or a change to what an accepted one decides | None | It stays a person's (point 7) |
| A finding a reviewer left for a person ([COR-057](COR-057-rule-set-reviewer.md) point 3) | None | It stays a person's (point 7) |
| A grant to an agent to run on its own, or any other grant or consent | None | It stays a person's (point 7) |
| A question only someone's account can settle | None | It stays a person's (point 7) |
| A question another record keeps for a person | The level that record places it at | The check that record names (point 8) |

The delegate decides as COR-064 point 3 sets out. It judges from what the files hold, and never decides what it drafted: such a question stays a person's. It may refer any question to a person instead of deciding it.

### 5. A standing authorisation to merge

At the third level, the setting is the person's authorisation, given in advance, to merge each change whose every file falls at that level. The person names the class of change once, and the component that carries out merges applies it. That component merges such a change only where all of these hold at the head it merges:
- **its checks:** the project's checks pass;
- **its reviewers:** each reviewer the merge waits for gave a verdict that stands for that head, and none withholds approval. Which reviewers it waits for is read as the default branch's configuration sets it. An input from elsewhere, such as a label or a flag, may add a reviewer and never removes one. Where a reviewer was overridden or the review bypassed, no standing authorisation applies;
- **no decision for a person:** the landing check reports no proposal and lists nothing the change makes accepted (COR-066 points 2 and 3), and the numbering check lists no edit to an accepted record ([COR-058](COR-058-record-points.md) point 8);
- **no finding for a person:** no reviewer the merge waits for left one;
- **no answer for a person:** every answer the change check marks as not asked for, and every reason for having no anchors, falls at the second level or higher, and the reviewer of answers checked it;
- **nothing on the floor:** the change alters no file point 6 keeps from a standing authorisation;
- **the component's own conditions,** which its records set.

Where any fails, or cannot be read, the component stops and asks a person, as it would with no setting. A run that merges says that it merged under the setting, naming the level and the area.

- **One reading, from the backbone.** The backbone computes, for a change, the level of each file it alters and the floor's files it touches, or says it has no answer. The component reads that and computes neither. No answer counts as a person's question.
- **Read at the merge.** The setting and the floor are read at the base's tip just before the merge, and again after any wait. The files a change alters are those its merge would land against that tip, as the landing check reads them.
- **The merge it checked.** A standing authorisation covers only the merge of the head it checked onto the tip it read. Where a queue builds a merge of its own with other changes in it, the component pins the queue to that head. Where it cannot, the standing authorisation does not apply.

### 6. The floor: what a standing authorisation never merges

A standing authorisation never covers a change that alters one of these files:
- **configuration:** the backbone configuration, each component's project configuration, and each component's package metadata;
- **what an agent may do:** each agent's definition, and each file that grants an agent a tool, a permission or a run;
- **what checks a change:** the files from which the hosting service runs its checks on a change, the harness's settings and hooks, and the project's own hooks;
- **what carries out the merge:** the code that runs the checks, the reviewers and the landing, its helpers included, and the code that reads the setting;
- **what that code rests on:** the configuration and baselines the checks read, and the files that pin what the code depends on.

Who declares them:
- **The backbone and each component** declare, in their package metadata, the files of these kinds they hold, whole. The adapter declares the harness's.
- **The project** names in the setting its own files of these kinds, such as the hosting service's workflow files and its own check scripts, or says it has none. Validation refuses the third level until it does.
- **Nothing narrows the floor.** The setting may add to it. A project's own entry never replaces a component's.

The floor fails closed:
- **A component that declares nothing.** Where an installed component, or the backbone, declares no floor, no standing authorisation applies.
- **Both states.** The declarations are read at the base's tip and at the merge the change would land, and the floor is both together. So a change that drops a declaration and edits its file still waits.
- **What cannot be read.** A declaration that cannot be read counts as no declaration.

A change that alters any file on the floor waits for a person, at every level.

### 7. What never moves past a person

At every level, these stay a person's:
- **the setting itself:** every change to it, in either direction, and who may make one (point 9);
- **each grant or consent that widens what agents may do or decide.** Among them are naming the delegate (COR-064 point 2), granting an agent to run on its own, a grant of the permission model, and the consent before a configuration key is written ([COR-048](COR-048-backbone-configuration.md) point 5);
- **accepting a record or a rule,** and every change to what an accepted one decides;
- **a finding a reviewer left for a person,** which judges a passage under a rule that does not settle it (COR-057 point 3);
- **a question only someone's account can settle,** such as whether a change was meant (COR-064 point 3).

No level here hands on a record's acceptance or a finding left for a person. Either would need two things this record does not give. One is something in the files for the delegate to judge against, since whether the project wants a decision is a choice no file records. The other is a way to tell an acceptance the delegate gave from one any agent wrote, once no person sees the change before it lands. A later record may add a level above the third that gives both.

The setting does not reach the confirmations an agent's operational rules ask of it in a session, such as before a destructive operation. Nor is it the permission model's ([COR-028](COR-028-permission-model-realization.md)), which decides which commands an agent runs without a prompt. This setting decides which questions an agent settles in a person's place, and never widens what the permission model grants.

### 8. Every other record places its own questions

A question another record keeps for a person stays a person's until that record places it at a level. Examples are when planned work is scheduled or closed, a budget raised, or a choice made within a version transition. Placing it, the record names what checks the agent's choice, or says that the person is told and nothing checks it. No record places a question point 7 keeps for a person.

A component that carries out merges gives no standing authorisation until its own records say how it applies point 5. Its records may add conditions, and never drop one. Where a reviewer's verdict rests on a person's own run of it, they also say what stands in for that person when no one is there.

### 9. Where it lives, and who changes it

- **Committed configuration.** A key of the backbone configuration, which this record owns (COR-048 point 2), holds the setting.
- **The default branch holds it.** The setting counts as the default branch holds it ([COR-054](COR-054-default-branch.md)). So a change cannot raise the level for its own questions.
- **Only a person changes it.** A person who decides what reaches the default branch changes it, on their own word, under the consent COR-048 point 5 asks. No agent writes it on its own initiative.
- **Shown before it counts.** A change to the setting is shown to the person who authorises its merge. No standing authorisation covers it, since it lies on the floor, and nor does an authorisation given before that person could see it.
- **Words lower it, and never raise it.** A person's word in a session lowers the level for that session at once. Agents in other sessions, such as agents working in parallel in other clones, stop only once a change lowers it on the default branch. A raise takes a change. A person's decision on one question, given in words, counts as any such decision does. A grant in words of a kind of question counts for nothing.
- **A setting any part of which cannot be read** counts, as a whole, as the lowest level for the whole project, and validation fails it. That is the default COR-048 point 4 has a command read, which this record sets. So no part that lowers the level is dropped while one that raises it stands, and the delegate decides nothing until the setting is mended.

### 10. The person is told, not asked

- **Where it lands.** Each decision an agent made in a person's place is recorded with what it changed. For a merge, that is with the change, where its merge keeps it in the default branch's history. For an answer, it is what COR-064 point 5 sets out. For a question another record placed, it is the audit trail of the component that wrote it. The record of it names what was decided, the agent that decided it, and the level and the area that let it.
- **Not taken where it cannot be recorded.** Where that record cannot be written, such as where a component writes no audit trail, the agent does not decide, and asks a person.
- **One place to read.** These decisions reach the person at their own pace. A component that gathers for the person what waits on them gathers these too. Until one does, the agent's report of its run tells the person it works for.
- **Never a gate.** Nothing waits for the person to read them.
- **Within reach.** The person may replace an answer (COR-062 point 5), revert a merge, or lower the level. A revert cannot recall what a merge has already started, such as a release or a deploy. Where a merge of certain files starts one, a project keeps those files out of its raised areas, or adds them to the floor. Where every merge starts one, the third level means that every merge it covers does.

## Rationale

**Why one setting with ordered levels.** The person's question is how deep the agents may go, in one area or everywhere. Ordered levels answer it with one word for each area. Each level adds the next kind of question in order of how much stands in for the person. An answer is checked against the files by a reviewer. A merge is settled for a class the person named, with the reviewers and the checks behind it. Merging unasked while asking about each answer would invert that order. A further kind, such as accepting a decision, would take a level above these, once something can stand in for the person there.

**What a standing authorisation is.** The person commits in advance to trust the project's checks and its reviewers for a class of change they chose. That is a different trust from reading each change. COR-064 rejects a standing acceptance of every answer of a kind, because nobody would read each answer before it is written. Here each change is read before it merges, by the reviewers the merge waits for. What the person gives up is their own reading of it, for the class they chose. No agent judges whether a change should merge: the component checks the change against the person's class.

**Why the standing authorisation holds on any decision for a person.** A change can carry a question no level hands on, such as a record it makes accepted, or a finding a reviewer left for a person. Merging it would settle that question with no one deciding. The landing check and the numbering check list such questions from the change itself, so the hold needs no one's account.

**Why the floor is files, declared, and fails closed.** A change could weaken what every later merge relies on: drop a required reviewer, switch a check to warning, raise a baseline, or edit the code that runs the landing. None of those widens what an agent may do on its face, so a test of what a change means would miss them, and an agent would be making that test about its own change. A list of files the change touches is read from the diff alone. The owners of the machinery declare its files whole, helpers included, since they know them. A file nobody declares would be off the floor, so a missing declaration withholds the standing authorisation instead. Reading the declarations at both states keeps a change from removing a file from the floor and editing it at once. Where the project's own repository holds the backbone's code, nearly every change to the backbone then waits for a person, which is the intent.

**Why one reading, at the merge.** Two components computing the level apart would drift. Read at the base's tip just before the merge, a lowering that lands while a run waits stops that run. The files the merge would land, not the branch's own diff, are what reaches the default branch.

**What a standing authorisation cannot hold.** A merge sent past the component, by another merge command or the host's own controls, meets none of its conditions, as COR-066 says of the landing check. The check of what a change alters runs the code the project holds, so in a project whose repository holds that code, the floor is what keeps a change from rewriting it. Who decided an answer is not shown in any file, as COR-064 point 4 says, so the reviewer checks each answer whoever decided it.

**Why records and findings stay a person's here.** Accepting a decision chooses what the project does. A reviewer can judge its reasoning, but whether the project wants it is in no file, so the delegate could judge only against a draft's own account. A finding left for a person is a reading that the rule, by its own reviewer's judgement, does not settle. COR-064 holds that an independent check must replace the person's reading, or there is no delegation. Neither has one. A project whose rules leave many readings to a person will see the third level stop often. The remedy is that the rule's owner settle the rule in its words, not that an agent settle it each time.

**Why the rest of the floor.** An agent that could widen what agents may do could raise its own reach, and no check would stand outside the agents. So the setting, every grant and every consent stay with a person. Whether a change was meant rests on an intent no file records.

**Why areas, and why a file takes the lowest level that holds it.** A person trusts agents with a part of the work, such as one component, before the whole. A change raised by an area must lie wholly in raised areas, so a change that reaches elsewhere does not ride on the grant. An area also lowers the level for any file in it, so a person can keep a sensitive part asking within a raised area. A change's own answer files lie wherever its answers are kept, not in the area, so they take no level. An item of planned work is matched through links that lie outside the default branch, so it never raises the level, and an agent cannot choose its own level by filing work under a raised item.

**Why committed configuration on the default branch.** A grant in a file the project commits is visible in review and in history, reaches every clone, and cannot be claimed by an agent that was not given it. Read where the default branch holds it, a change cannot raise the level for its own questions. These are COR-064's reasons for the delegate's name.

**Why words lower and never raise.** Lowering errs toward asking, which harms nothing, so a word in the session where it is given suffices. A raise hands on decisions the person made before, so it is shown in review and counts once it merges.

**Why the delegate decides, and never its own draft.** One agent deciding gives one place for the person to look, and COR-064's discipline already binds it. A delegate that decided its own drafts would leave one agent both writing and accepting. A delegate that also drafts much of the work leaves those drafts to a person, so a project gains most by naming one that drafts nothing.

**Why other records place their own questions.** A record may keep a question for reasons this record cannot see. This record does not presume to hand it on, as COR-064 point 1 holds for answers. Each places its questions on the one scale, so the person still sets one level.

**Why a decision that cannot be recorded is not taken.** The person's way to see what agents decided is the record of it. A decision with no record would never reach the person.

**Why the person is told.** Told what an agent decided, the person can undo it or lower the level. Asked first, they would be back to judging each question.

### Alternatives considered

- **A switch for each kind of question.** Not taken. It gives the person more to weigh, and lets a project merge unasked while a person still reads each answer, which inverts what stands in for whom.
- **A grant given in words for a session.** Rejected. It leaves no record a reviewer or another clone can read, and an agent could claim one it was not given.
- **The delegate judging each merge.** Rejected. Whether to merge decides what the project does. The person names the class once instead, and the component checks each change against it.
- **A fourth level at which the delegate accepts records and rules, and judges findings left for a person.** Not taken in this record. Nothing in the files would tell the delegate whether the project wants a decision. And once no person sees a change before it lands, nothing tells an acceptance the delegate gave from one any agent wrote.
- **A floor of what a change means, such as a record that decides who decides.** Rejected. It is a judgement an agent would make about its own change, and it misses a change that weakens the checks without widening anything.
- **A floor the person may narrow.** Rejected. A narrowed floor lets a change rewrite what checks it.
- **An area of planned work that raises the level.** Rejected. The links that put a change under it lie outside the default branch, where a change can write them.
- **A question takes the lowest level of every area it touches, the project's included.** Rejected. An area could then never raise the level above the project's.
- **Each component keeps a setting of its own.** Rejected. The person would set several and read several reports.

## Implications

- **The answer-delegate record (COR-064)** is refined in place, with forward pointers here. What the delegate decides stands, and so does its line that the delegation covers those answers and nothing else. The edits make it say:
  - in point 1, that the delegate decides an answer no change owes where its level is the second or higher, and that a named delegate with no setting puts the project at the second level;
  - in point 6's item on authorising a merge, "for each change, or in advance for a class of change the setting names";
  - in its summary, after "Everything else a person decides stays theirs", that this includes a merge's authorisation, which a person may give in advance for a class of change;
  - in the Context's paragraph on what a person cannot hand to an agent, and in the Rationale's "Why the line falls where it does", that a person may authorise a class of merges in advance. They then trust the checks and the reviewers for that class, and no agent chooses whether a change merges. Their claim that no reviewer's check stands in for the person's choice stands;
  - in the Rationale's "What the delegation does not change", that the person authorises each merge, or names in advance a class that merges without asking.
- **The record on landing only accepted decisions (COR-066)** gains a forward pointer in point 3: a standing authorisation never merges a change whose list is not empty, so the person sees that list first.
- **The record on records and their projection ([COR-065](COR-065-records-and-projection.md))** is refined in place in point 3. Where a standing authorisation merges a change, the change's reviewers judge alone whether it needed a record. A reviewer who finds that it did holds the merge for a person, who decides. The operational rule that mirrors it (backbone:RS-OPS-023) says the same.
- **The anchors-and-friction record (COR-050)** gains a forward pointer in point 3, where it says the delegate decides the answers a person would: "where the setting's level hands it the answer".
- **The operational rule on answers** (backbone:RS-OPS-020) says that the delegate decides where the setting's level hands it the answer. Its origin cites this record. So does the agents' guidance on who writes an answer, in the agents README.
- **The backbone configuration's schema** gains the setting's key. Validation fails a setting it cannot read, an unknown level, an area it cannot match, and the third level where the setting names neither the project's floor files nor that it has none.
- **An architecture record realizes this record:** the key's name and shape, where the backbone computes a change's levels and floor, the field the declarations take, the states they are read at, and the reading's document and its no-answer case.
- **A component that carries out merges** keeps each merge a person's in its own records. It changes them by a record of its own namespace, refining each or overturning it in part, before it gives any standing authorisation (point 8). In project-management, the records that keep each landing a person's are [project-management:DEC-006-state-machine-and-cascade], [project-management:DEC-008-pm-and-implementer-roles], [project-management:DEC-029-project-manager-agent-shape], [project-management:DEC-055-pr-lists-answers] point 3, [project-management:DEC-057-purpose] and [project-management:DEC-059-topology-of-seats] point 8. Among what its record decides is that its agent acts on the setting as the default branch holds it, and on no standing authorisation given in words.
- **A component that keeps answers or other questions for a person** places them on a level by refining its own record (point 8). An example is the answers a fixer proposes and a component holds for a person. Whether a change was meant stays a person's.
- **The work that builds it:**
  - the key, its schema and its validation, and the backbone's reading of a change's levels and floor;
  - the floor's declarations, by the backbone, the adapters and each component;
  - each merging component's record and its standing authorisation;
  - the report of what agents decided in a person's place.
- **No migration.** The key is new, and absent by default.
