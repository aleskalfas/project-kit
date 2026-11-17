---
id: COR-072
title: A person sets, for the project and for each area of work, how much agents decide in a person's place
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person chooses, in one setting, how much the agents decide without asking. The choice is a *level*, set for the whole project and, where the person wants, for an area of work, such as one component's files. There are four, each holding the ones below. At *ask*, a person decides each question. At *answer*, the agent the person named as delegate decides the answers on artefacts that no change owes, and a reviewer checks each. At *land*, a change merges without asking once its checks and its reviewers pass and nothing in it needs a person. At *accept*, the delegate also accepts a decision record or a rule that carries out what the person agreed, such as in an issue or a conversation, once the reviewers the project names pass it at the merge.

The setting lives in the project's committed configuration and counts as the default branch holds it. With no setting, the project stands at the top level, and the install and the upgrade write it, naming a delegate where none is named. Before an agent first decides in a person's place, the person's machine shows once what the setting hands over. At every level some things stay a person's, among them a change to who accepts or who merges, a change that loosens what agents may run, write, start or reach, and releasing and publishing. The person is told afterwards what was decided in their place, and lowers the level at once: with a word for their own session, and with a change for everyone.

## Context

Several records keep a question for a person, each in its own way.
- **Answers on artefacts.** The answers no change owes are a person's, unless the person names a delegate to decide them ([COR-064](COR-064-answer-delegate.md) point 1).
- **Authorising a merge.** A change reaches the default branch on a person's authorisation, given for that change (COR-064 point 6).
- **Accepting a decision.** A person accepts a record or a rule in the change that proposes it, and the person who authorises the merge sees first what the change makes accepted, and each edit it makes to an accepted record ([COR-066](COR-066-accepted-before-landing.md) points 1, 3 and 5).
- **A finding for a person.** A reviewer may leave a passage for a person to judge, where the rule it cites does not settle it ([COR-057](COR-057-rule-set-reviewer.md) point 3).
- **Other questions,** such as when planned work is scheduled or closed, and which agent may run on its own.

A person who trusts the agents with an area of work cannot say so anywhere that lasts. A grant given in words, such as "merge what passes review", lives in no file, and an agent in another clone never hears it. So the person is asked, many times a day, to accept answers, merges and records they could judge only by redoing the reviewers' work. That is the rubber stamp the anchors-and-friction record guards against ([COR-050](COR-050-anchors-and-friction.md) point 3).

The questions differ in what can stand in for the person.
- **A check of files.** An answer says whether an artefact still holds against what it rests on, which a reviewer can check against the same files.
- **A class the person can name.** Whether a change may merge can be settled in advance for a class of change: one confined to an area, passing every check and every reviewer, and carrying nothing a person must judge.
- **A choice the person already made.** Most records an agent drafts carry out a choice the person stated, in an issue, a note or a conversation. What the person adds by accepting is a reading of the record against what they agreed, which a reviewer can make with both texts in front of it.
- **A choice nobody stated.** Whether the agents' own reach should widen, or whether a change was meant, rests on what people intend. An agent that settled the first would set the limits of its own powers.

**Terms.** *The person* and *the delegate* are COR-064's. An *agreement* is words the person wrote, or said they agreed to, that state a choice, in an issue, a scratchpad note ([COR-012](COR-012-scratchpad-notes.md)), a conversation or another channel. A *standing authorisation* is an authorisation of merges a person gives once, for a class of change they name, ahead of the changes it covers. The *landing check* is the check COR-066 point 2 decides, and its *list* the list of what a change makes accepted (COR-066 point 3). To *hold* a question is to leave it to a person, as at the lowest level.

## Decision

**A person sets a level for the project, and for any area of work, in committed configuration read at the default branch's tip: ask, answer, land or accept. Each level hands agents one more kind of question and names what checks the agent's choice. An absent setting reads the top level. A change that would widen what agents may do, and a question no check can stand in for, stay a person's at every level, and the person is told afterwards what was decided in their place.**

### 1. The setting holds a level for the project and for each area

The *delegation setting*, the *setting* in this record, is one key of the project's backbone configuration, which this record owns ([COR-048](COR-048-backbone-configuration.md) point 2). It holds the project's level, which applies wherever no area does; any number of areas, each with a level of its own; and the reviewers the levels rest on (point 8).

An *area of work* names files, as a path anchor names them (COR-050 point 2). An area may instead name an item of planned work, such as a feature, where a component that plans work says how a change is matched to it. Such an area may only lower the level, since the links that tie a change to planned work lie outside the default branch, where a change can write them.

### 2. Four levels, each holding the ones below

1. **Ask.** A person decides every question this record covers.
2. **Answer.** The delegate decides the answers no change owes (point 4).
3. **Land.** A change also merges on a standing authorisation (point 5).
4. **Accept.** The delegate also accepts a record or a rule that carries out the person's agreement (point 6).

Where no delegate is named, answer and accept hand on nothing, and land still gives its standing authorisation, which no agent decides. Where a reviewer a level rests on is not declared, that level hands on nothing that reviewer would check (point 8).

| Question | Lowest level that hands it to agents | What checks the agent's choice |
|---|---|---|
| An answer no change owes, or a reason for having no anchors | Answer | The answers' reviewer, from the change check's own list (COR-064 point 4) |
| A merge's authorisation | Land | No agent chooses. The component that carries out merges applies the class the person named, and starts the reviewers itself (point 5) |
| A finding left for a person on a passage other than a record or a rule | Land | No agent judges it. The passage merges, and the finding waits for a person after the merge (point 5) |
| A record's or a rule's acceptance | Accept | The reviewers the setting requires of it, and the acceptance reviewer, each started by the merging component at the head it merges (point 6) |
| A finding left for a person on a record or a rule | None | It holds the record or the rule for a person (point 6) |
| A grant to an agent to run on its own, or any other grant or consent | None | It stays a person's (point 7) |
| A question another record keeps for a person | The level that record places it at | The check that record names (point 13) |

### 3. Which level a question takes

Each file a question touches takes the level of the areas that hold it, the lowest where several do, or the project's level where none does. The question takes the lowest level among its files, and no higher than any area of planned work it is matched to. So an area raises the level only for a question wholly inside areas at that level, and lowers it for any question that reaches into it.

What a question touches:
- **an answer:** the artefact it answers on;
- **a merge:** every file the change alters, save the answer files it adds for its own answers ([COR-062](COR-062-answers-in-own-files.md) point 1);
- **an acceptance:** the record's or the rule's file, and each file its named edits change;
- **another record's question:** what that record says (point 13).

### 4. Answer: the delegate decides the answers no change owes

The delegate decides the answers no change owes, as COR-064 sets out, wherever the question's level is answer or higher, and the answers' reviewer the setting declares checks each (point 8). At ask it decides none, even where it is named.

### 5. Land: a standing authorisation to merge

At land, the setting is the person's standing authorisation of each merge into the default branch of a change whose every file falls at land or higher. The person names the class once, the component that carries out merges applies it, and no agent judges whether a change should merge. The component merges only where all of these hold at the head it merges:
- **its checks:** the project's checks pass;
- **its reviewers:** each reviewer the merge waits for approves that head, in a run the component itself started for it, and a verdict another run posted counts for nothing. Which reviewers the merge waits for is read as the base's tip configures them. An input from elsewhere, such as a label, may add a reviewer and never removes one. Where a reviewer was overridden or the review bypassed, no standing authorisation applies;
- **no decision for a person:** the landing check reports no proposal. Every record or rule the change makes accepted, and every edit it makes to an accepted record or rule, such as those the numbering check lists ([COR-058](COR-058-record-points.md) point 8), stands under the delegate's acceptance of point 6;
- **no answer for a person:** every answer the change check marks as not asked for, and every reason for having no anchors, falls at answer or higher and passed the answers' reviewer, started by the component for the head. Nor does the change leave a revalidation answered apart, of which the person is told before the merge (COR-062 point 7);
- **nothing held:** the change is of no kind point 7 holds, and alters no file on its floor;
- **the component's own conditions,** which its records set (point 13).

Where any fails, or cannot be read, the component stops and asks a person, as at ask.

- **A finding for a person holds no merge.** The passage merges, and the finding reaches the person after the merge, in its reviewer's words, and waits on them, recorded where it outlasts the merge, until a person judges it. What they want changed goes into a follow-up. A finding that withholds approval stops the merge.
- **One reading, from the backbone.** The backbone computes, for a change, the level of each file it alters and the files on the floor it touches, or says it has no answer, which counts as a person's question. The component reads that and computes neither.
- **Judged by the base.** The setting, the floor and the reviewers are read at the base's tip just before the merge, and again after any wait. The code and configuration that judge the change, and the definitions of the reviewers the component starts, are the base's tip's, never the head's. The files a change alters are those its merge would land against that tip.
- **The merge it checked.** A standing authorisation covers only the merge of the head the component checked onto the tip it read. Where a queue builds a merge of its own, the component pins the queue to that head, and where it cannot, the standing authorisation does not apply.

### 6. Accept: the delegate accepts a record or a rule that carries out the person's agreement

At accept, the delegate accepts a proposed record or rule in the person's place only where all of these hold:
- **It traces to an agreement, choice by choice.** Each point of the record's Decision, each edit its Implications name, each name of a point with nothing to carry out ([COR-067](COR-067-decision-debt.md) point 2), and a rule's statement, carries out a choice a passage of the agreement states, or settles one the passage leaves open within what it asks. None contradicts the agreement, or leaves out or weakens a choice it states.
- **Quoted and mapped by the drafter.** The change quotes each passage word for word, with where it is, when it was written or said, and whether the person or an agent wrote it. It maps each point and each named edit to its passage, and lists each choice the agreement left open. The drafter writes the quotes and the map, never the delegate, since choosing which passage covers which point is drafting.
- **Read where it lies.** An agreement in a file of the repository, or in the project's issue tracker, the delegate reads there, never from the quote alone, and a quote it does not find there, as the source stood when quoted, fails. A passage an agent wrote for the person, such as an issue it filed from what they said, counts as the agreement. Words no file holds, such as a conversation the delegate did not hear, are the drafter's account. Both reach the person marked as such (point 12).
- **Not the delegate's own.** The delegate never accepts a record or rule it drafted, in whole or in part, nor one holding a choice it proposed to the drafter or a reviewer, whoever wrote the choice in. Drafting is writing or changing a choice, and mending a word that changes no choice is not. The change names the drafter. The files cannot tell who drafted, so the bar rests on the delegate's discipline and on the acceptance reviewer's check of what the change names, as COR-050 point 3 says of who read an answer.
- **No reviewer's finding to hold it.** The delegate accepts only where no verdict on the text by a reviewer the setting requires of it withholds approval or leaves a finding for a person. That reading lets it accept before work rests on the record, and counts for nothing at the merge.
- **Of no held kind,** read over the whole record, its named edits and what its Implications say carries it out included (point 7).
- **Through a merging component.** The record lands by a merge through a component that carries out merges, whose records apply this point (point 13). A record committed straight to the default branch, or merged any other way, is a person's to accept (COR-066 point 2).
- **A component keeps its own.** Where a component's record keeps the acceptance of its records, rules or entries for a person, it stays the person's until that record hands it on, as COR-064 point 1 has for answers.
- **No raise of a budget.** A rule that needs room in a rules file waits for the person, since raising the budget stays theirs ([COR-069](COR-069-rules-word-budget.md) point 4).

**Accepting.** The delegate reads the record and the agreement word for word, and accepts or holds. It writes `accepted` in a commit of its own within the change, before work there rests on it, as a person's acceptance is made (COR-066 point 1). Accepting a record accepts the edits its Implications name (COR-066 point 5). A rule's origin names as its decider the person whose agreement it carries out, in the agreement's words, and says the delegate accepted it ([COR-051](COR-051-rule-sets.md) point 5). The delegate never refuses a record, since refusing closes the change, which stays a person's (COR-066 point 1). A record it holds waits for a person.

**At the merge.** The merging component starts, at the head it merges, each reviewer the setting requires of that kind of record or rule, and the acceptance reviewer. The delegate's acceptance stands only where each approves that head and none leaves a finding for a person on the record or rule. Otherwise the change waits for a person, who accepts the record through the list (COR-066 point 3) or closes the change.

**The acceptance reviewer** is neither the delegate nor the drafter. It reads each acceptance the change says the delegate made in the landing check's list, with its named edits as made and its edits since, and checks that:
- the trace holds, and each quote matches its source where the source can be read;
- the change names a drafter other than the delegate;
- the record is of no held kind;
- each named edit, as made, says what its name says and goes no further;
- what the person is told of the record (point 12) says what it decides;
- the base's tip names that delegate, and puts the record's question at accept.

It blocks the merge where one does not hold.

- **An edit after the acceptance** is accepted only by the delegate accepting the record again under these tests, or by a person through the list.
- **A person's acceptance.** An acceptance the change does not say is the delegate's is a person's, and holds the merge for the person who authorises it to see first, as COR-066 point 3 has it. A claim that the delegate accepted only brings a record under these tests, so a wrong claim, either way, leaves the record to a person.

### 7. What stays a person's at every level

At every level, these wait for a person, and the change says in plain words what each changes:
- **Who accepts or who merges.** A change that decides or changes who accepts a record or a rule, who authorises a merge, a standing authorisation, the delegate, what the delegate may decide or the tests it applies, or the reviewers of point 8. A change to the setting that raises a level, or names or changes the delegate or a reviewer, is one (point 9).
- **What agents may run, write, start or reach.** A change that loosens it, by any means: a record, a rule, a configuration or any other file, its named edits included. Examples are the permission model ([COR-028](COR-028-permission-model-realization.md)), a confinement such as a sandbox, a grant of paths through the agent overlay, an agent's tool access ([COR-013](COR-013-agent-architecture.md) point 7), a switch that lets an agent run on its own, and removing a consent a record asks of a person.
- **Releasing and publishing,** which leave the repository, and which no follow-up takes back.
- **Every other grant or consent a record asks of a person,** such as the consent before a configuration key is written (COR-048 point 5), and naming the delegate, save point 10's first name.
- **Raising a rules file's budget** (COR-069 point 4).
- **A question only someone's account can settle,** such as whether a change was meant (COR-064 point 3).

Where an agent or a reviewer cannot tell whether a change is of these kinds, it holds it. The delegate holds a record of such a kind, and each reviewer the merge waits for, with the acceptance reviewer, holds a change it finds of one.

**The floor.** A change that alters a file on the floor waits for a person at every level, whatever it means. The floor holds, by role:
- the files that govern how a change is reviewed and merged, among them the configuration of the backbone and each component, the reviewers' definitions, the harness's settings and the instructions, rules and skills it loads, the workflows the host runs on a change, and the code that runs the checks, the reviews and the merge;
- the files that set what agents may run, write, start or reach;
- what the project receives from elsewhere, and the versions it records ([COR-059](COR-059-version-transition.md) point 1).

The floor is read from the set of such files the methodology declares, as a later record decides. It fails closed:
- **Unknown until declared.** Until a declaration of every role can be read, the floor is unknown, and neither land nor accept hands anything on.
- **Both states.** The declarations are read at the base's tip and at the merge the change would land, and the floor is both together, so a change that drops a declaration and edits its file still waits.
- **Nothing narrows it.** The setting may add files to the floor, and take none away.
- **A lowering passes.** A change whose only change on the floor lowers the setting's levels is not held for it (point 9).

The setting does not reach the confirmations an agent's operational rules ask of it in a session, such as before a destructive operation. Nor is it the permission model, which decides which commands an agent runs without a prompt, and it never widens what that model grants.

### 8. The reviewers the levels rest on

- **One home.** The setting declares, as the default branch's tip holds it:
  - the answers' reviewer, which checks the answers no change owes (COR-064 point 4);
  - for each kind of record or rule, the reviewers it requires before the delegate may accept it;
  - the acceptance reviewer (point 6).
- **Agents of the project.** Each names an agent of the project, tested as COR-064 point 2 tests the delegate's name. A declared reviewer that is the delegate counts as none, and so, for a change, does one that drafted what it would check.
- **No reviewer, no delegation.** With no answers' reviewer, the delegate decides no answer. With no required reviewer for a kind of record, or no acceptance reviewer, it accepts nothing of that kind.
- **The person's.** Only the person declares them, through a change point 7 holds. No install or upgrade writes one.
- **The merge's own reviewers** stay those the merging component's configuration names (point 5).

### 9. Where it lives, and who changes it

- **The default branch holds it.** The setting counts as the default branch's tip holds it ([COR-054](COR-054-default-branch.md)), so no change raises the level for its own questions.
- **Its writers.** A change a person authorises, on their own word; the backbone's configuration commands, on a person's word, under the consent COR-048 point 5 asks; and the writes of point 10. No agent writes it on its own initiative.
- **A raise is held and shown.** A change that raises a level, or names, changes or removes a reviewer or the delegate, waits for a person at every level (point 7). It is shown to the person who authorises its merge, and no authorisation given before that person could see it covers it.
- **A lowering is not held.** A change that only lowers levels narrows what agents decide, so nothing holds it.
- **Words lower it, and never raise it.** A person's word in a session lowers the level for that session at once. Agents in other sessions stop once a change lowers it on the default branch. A person's decision on one question, given in words, counts as any such decision does, and a grant in words of a kind of question counts for nothing.
- **What cannot be read reads as ask.** A setting any part of which cannot be read counts, as a whole, as ask for the whole project, and validation fails it. So no part that lowers the level is dropped while one that raises it stands. This is what a command reads for it under COR-048 point 4, not the default an absent setting reads (point 10).
- **Validation** also fails an unknown level, an area it cannot match, and a reviewer that names no agent of the project.

### 10. The default, and what the install and the upgrade write

- **An absent setting reads the top level** (COR-048 point 3).
- **Written as the missing default.** Where the configuration holds no setting, the backbone's upgrade migration, and the install of a component that offers a delegate, write the top level. A missing default is the sign a migration may act on (COR-059, Implications). The first install writes nothing, since the absent setting reads the same, and no component is installed yet to offer a delegate.
- **The delegate, in the same run.** In the run that writes the setting, and only then, where the configuration names no delegate, they name the agent an installed component the methodology ships offers as the delegate, where exactly one such component offers one. Where none or several do, they name none, and say why.
- **Offered by a component.** A component may declare, in its package metadata, one agent of its own that it offers as the delegate, whose definition says when and how it decides (COR-064 point 2). One a project authors, or receives from an external source, may offer one too, which only a person names.
- **What is kept.** No write touches a setting or a delegate the configuration holds. Once the setting is written, no run names a delegate, so a withdrawn delegate stays withdrawn while the setting stays. A replay over a deleted setting writes it again, with a delegate where none is named, and the release's notes say so. A project that wants a person to decide each question writes `ask`.
- **The consent.** The upgrade's migration writes under the consent of choosing the upgrade's target (COR-048 point 5, COR-059 points 3 and 4). A component's install writes with its install's consent, asked once or given by an explicit confirmation flag, and with neither it writes nothing (COR-048 point 5).
- **Shown before it counts.** A name counts once the default branch holds it, and the change that holds these writes names a delegate, so it waits for a person (point 7), who sees it before authorising its merge (COR-064 point 2).
- **The report** says what they wrote: the level, and the delegate they named or why they named none. It says what each level hands over, which reviewers of point 8 are not yet declared and so which levels hand nothing on, how to lower the level, and how to withdraw the delegate.

### 11. Each person's machine shows the words once

- **Before the first decision.** Before an agent first decides a question in a person's place above ask, on that person's machine, its run stops without deciding. It shows the setting's words, and leaves a mark in the person's own configuration on the machine, outside every repository. A later run for them there, from any clone of the project, decides.
- **The words** say, in plain words, what each level in force hands over, what stays a person's, how the person is told, and how to lower the level at once.
- **A higher level shows them again.** The mark names the highest level whose words it showed, and a run under a higher one stops again.
- **What the mark shows** is that a run showed the words, not that a person read them.

### 12. The person is told, not asked

- **Recorded where it lasts.** Each decision an agent made in a person's place is recorded with what was decided, the agent that decided it, and the level and the area that let it:
  - **a merge,** with the change, where its merge keeps it in the default branch's history;
  - **an answer,** as COR-064 point 5 sets out;
  - **an acceptance,** in the change and in the delegate's report to the person it works for. It says what the record or rule decides, in two sentences, and the agreement it rests on, with where and when. It names each passage an agent wrote, each that only the drafter's account holds, and each choice the agreement left open;
  - **a question another record placed,** in the trail of the component that wrote it.
- **Not taken where it cannot be recorded.** Where that record cannot be written, the agent does not decide, and asks a person.
- **One place to read.** A component that gathers for the person what waits on them gathers these too. Until one does, the agent's report of its run tells the person it works for.
- **Never a gate.** Nothing waits for the person to read them.
- **Within reach.** The person may replace an answer (COR-062 point 5), revert a merge, supersede a record accepted in their place by a follow-up record, judge a finding left for them, or lower the level. A revert cannot recall what a merge has already started, such as a deployment, so a project keeps the files whose merge starts one out of its raised areas, or adds them to the floor.

### 13. Every other record places its own questions

- **A question another record keeps** for a person stays theirs until that record places it at a level, such as when planned work is scheduled or closed, or how much a designing agent changes alone. Placing it, the record names what checks the agent's choice, or says that the person is told and nothing checks it. No record places a question point 7 keeps.
- **A component that carries out merges** gives no standing authorisation, and lands no acceptance by the delegate, until its own records say how it applies points 5 and 6. They may add conditions, and never drop one.
- **A reviewer the merge waits for** holds a change of a held kind (point 7), and its definition says so.

## Rationale

**Why one setting with ordered levels.** The person's question is how deep the agents may go, in one area or everywhere, and ordered levels answer it with one word for each area. Each level adds the next kind of question in the order of how much stands in for the person. An answer is checked against the files by a reviewer. A merge is settled for a class the person named, with the checks and the reviewers behind it. An acceptance rests on the person's own agreement, the record's reviewers and a reviewer of the acceptance. Accept sits above land because, with each merge still asked, the person reads each acceptance in the list before the merge anyway, so accepting in their place would spare them nothing.

**What a standing authorisation is.** The person commits in advance to trust the project's checks and its reviewers for a class of change they chose. COR-064 rejects a standing acceptance of every answer of a kind, because nobody would read each answer before it is written. Here the reviewers the merge waits for read each change before it merges, and what the person gives up is their own reading, for the class they chose.

**Why the merge starts its own reviewers.** A verdict is words a session posted, and the agent that accepts or lands a change could pass on a verdict never given for that head. A reviewer the merging component started for the head it merges rests on no other session's word.

**Why a finding for a person holds no merge, and holds an acceptance.** A finding for a person withholds no approval, and how it reaches the person is the gate's to say (COR-057 points 3 and 5). Held at each merge, it would bring the person's word back into the merges the setting spares them. Merged, the passage stands and the finding waits on the person, so only the order changes. A record is different: its acceptance chooses what the project decides, and a reviewer's question for the person about it is a question about that choice, which the delegate would answer for them.

**Why the person's agreement can stand in, choice by choice.** The choice a record makes is the person's, and the agreement holds it. What remains is whether the record carries the agreement out, which the acceptance reviewer checks against the agreement's own words, and whether it is sound, which the record's reviewers judge. Every point binds later work, so each must trace to a passage. An agreement seldom states every choice, so a point may settle what its passage leaves open, within what the passage asks, and each such choice reaches the person after the merge. A point that contradicts the agreement, or drops a limit it states, does not trace.

**Why words an agent wrote count, and are marked.** Where agents do most of the work, an agent writes most issues from what the person said, and the person tests the work against those issues. The files cannot tell who wrote an issue under the person's account. Barring such words would bar most agreements, and counting them unmarked would hide that the person never wrote them. Marked, they reach the person as an agent's words, and the person corrects what the agent misheard.

**Why never the delegate's own draft or proposal.** The drafter chooses what the record says, and the acceptance chooses whether it carries out the agreement. One agent making both would leave the second choice to the first, as COR-064 found for answers. A choice the delegate proposed to the drafter is its draft too, or a fix round would launder it. Where the delegate is also the agent the person talks to, what it drafts in that conversation waits for the person, and it accepts what other agents draft from the agreement.

**Why some changes stay a person's, by effect and by file.** An agent that could widen what agents may do, or change who accepts or merges, would decide the limits of its own powers. Stated by effect, the hold covers any means, a record's named edits included, and a mechanism a list would miss. A test of effect is a judgement an agent would make about its own change, so a floor of files, read from the diff alone, nets the machinery whatever a change means. The floor's owners declare its files, and a declaration nobody made says nothing, so the floor fails closed.

**Why the reviewers have one home, and only the person declares them.** A reviewer's check is what replaces the person's reading, so without one there is no delegation (COR-064 point 4). Declared in the setting, they count as the default branch holds them, and a change to them is held and shown, so no change lowers the reviewer that would judge it. Choosing what replaces their reading is the person's consent to the delegation, so no install writes it.

**Why an absent setting reads the top level.** A project whose agents do most of its work gains at once, and a setting that waits to be found is chosen late. No level hands on what its checks do not stand behind: with no delegate, answer and accept hand nothing on, with no reviewer declared nothing it would check, and with no floor declared neither land nor accept. Land needs no delegate, so it reaches every project with no setting once the floor is declared and its merging component applies point 5, and the words each machine shows are where that project's person first meets it. A word lowers the level at once. The upgrade's write only makes visible the default the project already has. The keys that refuse proposals and track debt read off when absent, so an upgrade that wrote them would turn something on, while this write writes what absence already reads.

**Why the delegate is named only with the setting.** A missing name is no sign that a delegate is needed, since a person may have withdrawn one. Written only in the run that writes the setting, the name follows the one sign this record has, and a withdrawal holds while the setting stays. Only a component the methodology ships may offer the agent named, since an offer a project or an external source made would choose who decides in the person's place without the person.

**Why each person's machine shows the words.** The change that holds the setting is one person's to authorise, and every clone reads it. A person on another machine would otherwise meet no stop that shows what the agents decide before one decides in their place. The mark stays in the person's own configuration, out of the repository every clone shares, so the stop comes once, not once a session.

**Why words lower, and an unreadable setting reads ask.** Lowering errs toward asking, which harms nothing, so a word suffices and a lowering needs no hold. A raise hands on decisions the person made before, so it is shown in review and counts once it merges. A setting that cannot be read could be dropping a part that lowers the level, so it reads as ask.

**Why areas, and the lowest level that holds a file.** A person trusts agents with a part of the work before the whole. A change raised by an area must lie wholly in raised areas, so a change that reaches elsewhere does not ride on the grant, and a person can keep a sensitive part asking within a raised one. An item of planned work is matched through links a change can write, so it never raises the level.

**Why committed configuration, and other records placing their own questions.** A setting the project commits is seen in review, reaches every clone, and cannot be claimed by an agent not given it, as COR-064 found for the delegate's name. A record may keep a question for reasons this record cannot see, so it places its own questions on the one scale.

**Why the person is told.** Told, the person can undo a decision or lower the level. Asked first, they would be back to judging each question. A decision with no record would never reach them, so it is not taken.

**What the setting cannot hold.** A merge sent past the merging component, by another command or the host's own controls, meets none of its conditions, as COR-066 says of the landing check, and lands no delegate's acceptance. Who decided an answer, who drafted a record and who wrote an agreement show in no file, so the reviewers check what the change names, and the bars on the delegate rest on its discipline. Words no file holds rest on the drafter's account, and the person, told after the merge, is the check on them.

### Alternatives considered

- **A switch for each kind of question, such as an acceptance mode of its own.** Not taken. Two settings would answer one question with no rule for which wins, and a project could accept records unasked while a person still reads each merge, which spares nothing.
- **An absent setting reads ask.** Not taken. The setting would wait to be found, and a migration that wrote a higher level would act on no sign that its change is needed.
- **The install and the upgrade write an offer, which reads as ask, and the person turns it on by a change held for them.** Not taken. The levels would wait on the person finding the offer. The words each machine shows, the levels' own checks and the hold on every widening reach the person without the wait.
- **The delegate accepts on the reviewers' passes alone.** Rejected. The reviewers judge whether a record is sound, not whether it is what the person agreed.
- **Each choice of a record stated in the agreement.** Not taken. Few agreements state every choice, so the delegate would accept almost nothing, and the choices left open reach the person after the merge instead.
- **Only words the person wrote count, or a separate delegate for acceptance.** Not taken. Most agreements are issues an agent filed, so the first would bar most acceptances, and the second would split the place the person looks. Marking what an agent wrote reaches the same person.
- **The delegate's account of the reviewers' verdicts.** Rejected. A verdict passed on by the agent that accepts rests on that agent's word.
- **The acceptance reviewer checking every acceptance in the list.** Not taken, unlike COR-064 for answers. An acceptance not said to be the delegate's holds the merge for the person, so a wrong claim errs toward asking.
- **A field in the record naming who accepted it.** Rejected. Anyone writing the file can write it, as COR-064 found for answers.
- **A finding for a person holding the standing authorisation.** Not taken. It would bring the person's word back into most merges the setting spares, on findings that ask the person to judge, not to authorise.
- **A floor of what a change means alone, or a floor the person may narrow.** Rejected. The first is a judgement an agent would make about its own change, and the second lets a change rewrite what checks it.
- **The reviewers of point 8 written by the install.** Not taken. Choosing what replaces the person's reading is the person's consent to the delegation.
- **A delegate named wherever none is named.** Rejected. A person who withdrew one would see it return at the next install.
- **An area of planned work that raises the level.** Rejected. The links that put a change under it lie outside the default branch.
- **A grant given in words for a session, or each component keeping a setting of its own.** Rejected. The first leaves no record another clone can read, and an agent could claim one. The second gives the person several settings to set and several reports to read.
- **The delegate judging each merge.** Rejected. The person names the class once, and the component checks each change against it.

## Implications

The edits this record makes to accepted records and rules, sorted by kind and then by id, each made in this record's change once it is accepted (COR-066 point 5).

**Overturned in part.** Each record gains a *Partially superseded by [COR-072](COR-072-delegation-levels.md)* top line, which says what this record decides there and names what it overturns. Those passages stay as they stood.
- **COR-064:** the delegation setting decides how much the delegate decides. At its top level the delegate also accepts a record or a rule that carries out the person's agreement, and the person authorises merges once for a class of change. The install and the upgrade name a delegate where none is named, in the run that writes the setting. Overturned: the top line's "and nothing else a person decides"; point 2's "by the person alone", "It names none by default" and "Only the person names it", as to that first name; point 6's items on naming the delegate and on accepting a record or a rule, as to that name and to the delegate's acceptances; and the summary, the Context, the Rationale and the one alternative that say the same.
- **COR-066:** at the delegation setting's top level, the delegate accepts a record or a rule in the person's place. The reviewers this record names check that acceptance at the merge, reading the list and each edit to an accepted record in the person's place, and the person is told afterwards. Overturned, for such acceptances alone: "by a person" in the summary, the top line and point 1; point 1's "only once a person has"; point 3's "sees that list first"; point 5's "That person reads each edit before the change lands"; and the Context and the Rationale where they say the same.

**Refined in place.** Each edit carries the pointer `(refinement per COR-072)` on the sentence or point it refines, and its record's decision stands.
- **COR-048 point 4:** for a value it cannot read, a reading command takes the reading the owning record names, where it names one, so a fault never widens what a command does.
- **COR-050 point 3:** a delegate decides an answer only where the delegation setting's level hands it the answer. **Point 14:** the key's writers gain, for the delegate's name, the upgrade's migration and a component's install, in the run that writes the setting.
- **COR-051 point 4:** a rule is accepted by the person's review, or, at the delegation setting's top level, by the delegate under this record's tests. **Point 5:** a rule the delegate accepted has as its origin's decider the person whose agreement it carries out, and says the delegate accepted it.
- **COR-064 point 1:** the delegate decides the answers no change owes only at answer or higher. **Point 4:** the answers' reviewer is declared in the delegation setting.
- **COR-065:** its summary, its Context, points 3 and 5 and its Rationale say a record is accepted by a person, or by the delegate where the delegation setting lets it. Point 3 also says that where a standing authorisation merges a change, its reviewers judge alone whether it needed a record, and one that finds it did holds the merge for a person.
- **COR-067:** its summary, point 2 and its Rationale say a name of a point with nothing to carry out is accepted with the record, by a person or by the delegate where the setting lets it.
- **COR-069 point 4:** a new rule that needs room waits for the person, who accepts it with the raise, where the delegate would otherwise accept it.

**An edit that changes no decision.** COR-025's top line, which restates COR-066, reads "after it is accepted in the change that proposes it" for "after a person accepts it in the change that proposes it".

**Rules of the backbone's loaded set.** The set's version moves from 6.0.0 to 7.0.0, since the edit to RS-OPS-020 tightens it (COR-051 point 7), and the three edits fit within its budget (COR-069). Each rule's anchors gain this record.
- **RS-OPS-002, the acceptance gate:** a person accepts a proposal in its change, or the delegate does at the setting's top level under this record's tests. The person who authorises the merge sees first each record and rule a person accepted, and the delegate's acceptances reach the person afterwards.
- **RS-OPS-020:** the delegate decides an answer only at a level that hands it the answer.
- **RS-OPS-023:** no work rests on the choice until the record is accepted, by whoever the acceptance gate lets accept it.

**Records of the project-management capability,** refined in place.
- **[project-management:DEC-029-project-manager-agent-shape]:** the capability offers its project manager as the delegate (point 10). Where named, the agent decides answers and accepts records at the levels the setting hands it, and never accepts a record it drafted or one holding a choice it proposed.
- **[project-management:DEC-055-pr-lists-answers] point 3:** an entry flagged as not asked for needed the delegate's decision at a level that hands it the answer.

**Not edited here.** A component that carries out merges keeps each merge and each acceptance a person's in its own records, and changes them by a record of its own before it applies points 5 and 6 (point 13). In project-management, such a record carries this record out for the capability's landing command, and lands no earlier. A walking skeleton's convention entries stay a person's to accept, as a component keeping its own ([software-engineering:DEC-004-skeleton-conventions-in-corpus]).

**What carries it out.**
- **An architecture record realizes this record:** the key's name and shape, the reviewers' declaration, the field by which a component offers its delegate, the backbone's reading of a change's levels and floor, the form in which a change quotes and maps its agreement and names its drafter, the step that shows point 11's words and the mark it leaves, and where the report of point 12 lives.
- **The floor** follows the record that decides how the files governing review and merge are declared. Until it lands, the floor is unknown.
- **The backbone configuration's schema** gains the key, and validation fails what point 9 names.
- **The backbone's upgrade migration and a component's install** write as point 10 sets out.
- **The agent a component offers as the delegate, and each reviewer point 8 names,** say their part in their definitions (COR-013), and each reviewer a merge waits for holds a change of a held kind.
- **A component that carries out merges** applies points 5 and 6 by a record of its own.
- **The documents that state the gate and the delegation,** the decision-record specification's acceptance gate among them, change with the build that makes them true.
- **Stands on these records, all accepted:** COR-012, COR-013, COR-028, COR-048, COR-050, COR-051, COR-054, COR-057, COR-058, COR-059, COR-062, COR-064, COR-065, COR-066, COR-067 and COR-069.
