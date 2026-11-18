---
id: COR-072
title: A person chooses how much agents decide in their place, by area of work
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person chooses, in one setting, how much the agents decide without asking: a *level* for the whole project and, where they want, for an area of work, such as one component's files. There are four, each holding the ones below. At *ask*, a person decides each question. At *answer*, the agent the person named as delegate decides the answers on artefacts that no change owes, and a reviewer checks each. At *land*, a change merges without asking once its checks pass, the reviewers the person named approve it, and nothing in it needs a person. At *accept*, the delegate also accepts a decision record or a rule that carries out what the person agreed, such as in an issue, once the reviewers the person named pass it at the merge.

The setting is committed, and counts as the default branch holds it. Nothing is handed on until the person declares, in a change held for them, the level it turns on, the delegate and the reviewers each level rests on. The upgrade writes the setting where it is absent, and moves into it the name of a delegate the person named before, but it chooses no delegate and declares nothing. Until a project's backbone reads the setting, a delegate named before keeps deciding the answers as it did. At every level some things stay a person's, such as a change to who accepts or who merges, a change that loosens what agents may run, write, start or reach, and releasing and publishing. The person is told afterwards what was decided in their place. They lower the level at once for their own runs, by a word or in their working tree, and for everyone by a change.

## Context

Several records keep a question for a person, each in its own way.
- **Answers on artefacts.** The answers no change owes are a person's, unless the person names a delegate to decide them ([COR-064](COR-064-answer-delegate.md) point 1).
- **Authorising a merge.** A change reaches the default branch on a person's authorisation (COR-064 point 6).
- **Accepting a decision.** A person accepts a record or a rule in the change that proposes it, and the person who authorises the merge sees first what the change makes accepted, and each edit it makes to an accepted record ([COR-066](COR-066-accepted-before-landing.md) points 1, 3 and 5).
- **A finding for a person.** A reviewer may leave a passage for a person to judge, where the rule it cites does not settle it ([COR-057](COR-057-rule-set-reviewer.md) point 3).
- **Other questions,** such as when planned work is scheduled or closed, and which agent may run on its own.

A person who trusts the agents with an area of work cannot say so anywhere that lasts. A grant given in words, such as "merge what passes review", lives in no file, and an agent in another clone never hears it. So the person is asked, many times a day, to accept answers, merges and records they could judge only by redoing the reviewers' work. That is the rubber stamp the anchors-and-friction record guards against ([COR-050](COR-050-anchors-and-friction.md) point 3).

The questions differ in what can stand in for the person: a reviewer's check of an answer against the files, a class of change the person names in advance for a merge, or the person's own statement of the choice a record makes. Whether the agents' own reach should widen, or whether a change was meant, rests on what people intend, and an agent that settled the first would set the limits of its own powers.

**Terms.**
- *The person* and *the delegate* are COR-064's.
- An *agreement* is a passage that states a choice the person made: words they wrote, words they said they agreed to, or words an agent wrote for them from what they said, such as an issue it filed. It may lie in an issue, a scratchpad note ([COR-012](COR-012-scratchpad-notes.md)), a conversation or another channel.
- A *standing authorisation* is the person's authorisation of merges, given once and ahead of the changes it covers, for the class of change the setting names, by their declaration of point 8.
- The *landing check* is the check COR-066 point 2 decides, and its *list* the list of what a change makes accepted (COR-066 point 3).
- To *hold* a question is to leave it to a person, as at the lowest level. A reviewer holds a change by withholding its approval.

## Decision

**A person sets a level for the project, and for any area of its files, in committed configuration read at the default branch's tip: ask, answer, land or accept. Each level hands agents one more kind of question and names what checks the agent's choice. None hands anything on until the person declares, in a change held for them, the level it turns on and the reviewers it rests on. A change that would widen what agents may do, and a question no check can stand in for, stay a person's at every level, and the person is told afterwards what was decided in their place.**

### 1. The setting holds a level for the project and for each area

The *delegation setting*, the *setting* in this record, is one key of the project's backbone configuration, which this record owns ([COR-048](COR-048-backbone-configuration.md) point 2). It holds:
- the project's level, which applies wherever no area does;
- any number of *areas of work*, each naming files as a path anchor names them (COR-050 point 2), and each with a level of its own;
- the person's declaration (point 8): the level it turns on, the delegate, named under COR-064 point 2's tests, and the reviewers the levels rest on;
- the files it adds to the floor (point 7).

### 2. Four levels, each holding the ones below

1. **Ask.** A person decides every question this record covers.
2. **Answer.** The delegate decides the answers no change owes (point 4).
3. **Land.** A change also merges on the person's standing authorisation (point 5).
4. **Accept.** The delegate also accepts a record or a rule that carries out the person's agreement (point 6).

No level hands anything on above the level the person's declaration turns on, nor before the declaration names the reviewers it rests on (point 8), and answer and accept hand on nothing where no delegate is named. A finding for a person holds no merge at land, and holds a record or a rule at every level (points 5 and 6). No level hands on a grant or a consent (point 7), and a question another record keeps takes the level that record places it at (point 13).

### 3. Which level a question takes

Each path takes the level of the areas that hold it, the lowest where several do, or the project's level where none does, and never a level above the one the person's declaration turns on (point 8). A question takes the lowest level among the paths it touches. So an area raises the level only for a question wholly inside areas at that level, and lowers it for any question that reaches into it.

What a question touches:
- **an answer:** the artefact it answers on;
- **a merge:** every file the change alters, save the answer files it adds for its own answers ([COR-062](COR-062-answers-in-own-files.md) point 1);
- **an acceptance:** the record's or the rule's file, and each file its named edits change. It takes no higher level than its change's merge;
- **another record's question:** what that record says (point 13).

**Raising and lowering** are read by their effect, from the setting at a change's base and at its head. A change *raises* the setting where any path takes a higher level at the head than at the base. It *lowers* the setting where no path takes a higher level, some path takes a lower one, and nothing else in the setting changes. So removing an area at ask raises the setting, as do narrowing it, widening a raised area and raising the level the declaration turns on. Removing the setting raises nothing, since it removes the declaration, and it is held as a change to the delegate and the reviewers (point 7).

### 4. Answer: the delegate decides the answers no change owes

The delegate decides the answers no change owes, as COR-064 sets out, wherever the question's level is answer or higher, and the answers' reviewer the person declared checks each (point 8). At ask it decides none, even where it is named.

### 5. Land: a standing authorisation to merge

At land, once the person has declared the level and the merge reviewers (point 8), the setting is the person's standing authorisation of each merge into the default branch of a change whose every file falls at land or higher. No agent decides to merge: the merge reviewers judge the change, and the component that carries out merges applies the class. It merges only where all of these hold at the head it merges:
- **its checks:** the project's checks pass;
- **its reviewers:** each merge reviewer of point 8, and each other reviewer the base's configuration requires of the change's files, approves that head by a verdict that rests on no other session's word. A run the component itself started for that head gives one, and so does a person's own approval of that head, where the project's review is a person's. An input the change or its issues carry, such as a label, may add a reviewer and never removes one of these. Where a reviewer was overridden or its review bypassed, no standing authorisation applies;
- **no decision for a person:** the landing check reports no proposal. Every record or rule the change makes accepted is the delegate's acceptance under point 6, and every edit it makes to an accepted record or rule, such as those the numbering check lists ([COR-058](COR-058-record-points.md) point 8), is a named edit of one of them. Any other edit holds the merge, even one that changes no decision, since telling which do is a judgement;
- **no answer for a person:** every answer the change check marks as not asked for, and every reason for having no anchors, falls at answer or higher and passed, at that head, the answers' reviewer, and COR-064 point 4's reviewer where it is another, each by a verdict that rests on no other session's word. Nor does the change leave a revalidation answered apart (COR-062 point 7);
- **nothing held:** the change is of no kind point 7 holds, and alters no file on its floor;
- **the component's own conditions,** which its records set (point 13).

Where any fails, or cannot be read, the component stops and asks a person, as at ask.

- **A withheld verdict holds what the change alters.** A verdict that withholds approval and rests on no other session's word, a person's among them, holds the change's diff from its base, not its commit, for every later run. So a head with the same diff, such as after an empty commit or a rebase, stays held. A later run is given the withheld findings, and the hold lifts only when a verdict finds them met, or a person judges them.
- **A finding for a person holds no merge.** It withholds no approval. The passage merges, and the finding reaches the person in its reviewer's words and waits on them until a person judges it, as the component's records say (COR-057 point 3).
- **One reading, from the backbone.** The backbone computes, for a change, the level of each file it alters and the files on the floor it touches, or says it has no answer, which counts as a person's question. The component computes neither.
- **Judged by the state it lands onto.** The setting, the floor and the reviewers are read at the state of the default branch the change lands onto, just before the merge and again after any wait. What judges the change, the checks' code and the reviewers' definitions among it, is that state's, and a test the change adds is judged by its reviewers. What merges is the head the component judged. Where the component cannot read the state the change lands onto, as through a queue, its record bounds the tip it may land onto.

### 6. Accept: the delegate accepts a record or a rule that carries out the person's agreement

At accept, the delegate accepts a proposed record or rule in the person's place only where all of these hold:
- **It traces to an agreement, choice by choice.** Each point of the record's Decision, each edit its Implications name, each name of a point with nothing to carry out ([COR-067](COR-067-decision-debt.md) point 2), and a rule's statement, carries out a choice a passage of the agreement states, or settles one the passage leaves open within what it asks. None contradicts the agreement, or leaves out or weakens a choice it states.
- **Quoted and mapped by the drafter.** The change quotes each passage word for word, with where it is, when it was written or said, and who wrote it: the person, or which agent. It maps each point and each named edit to its passage, lists each choice the agreement left open, and names the drafter. The drafter writes them, never the delegate, since choosing which passage covers which point is drafting.
- **Read where it lies.** An agreement in a file of the repository, or in the project's issue tracker, the delegate reads there, and a quote it does not find as the source stood when quoted fails. Words no file holds, such as a conversation the delegate did not hear, are the drafter's account, and reach the person marked as such, as do words an agent wrote (point 12).
- **The delegate's own words.** Where the delegate wrote a passage itself, only the person's own words count as the agreement: those it quotes of them, and a confirmation in their words, quoted from a file or the tracker. The delegate's or the drafter's account of what the person confirmed counts for nothing, and a choice that rests on it, or on the rest of the passage, is held for the person.
- **Not the delegate's own draft.** The delegate never accepts a record or rule it drafted, in whole or in part, nor one holding a choice it proposed to the drafter or a reviewer, whoever wrote the choice in. Drafting is writing or changing a choice, and mending a word that changes no choice is not.
- **Reviewed.** Each reviewer the setting requires of the record's kind gave a verdict on its text, and none withholds approval or leaves a finding for a person. That reading lets the delegate accept before work rests on the record, and counts for nothing at the merge.
- **Of no held kind,** read over the whole record, its named edits and what its Implications say carries it out included (point 7).
- **The floor holds the merge, not the acceptance.** The delegate may accept a record or a rule whose file, or a file its named edits change, lies on the floor (point 7). Its change then waits at the merge for a person, who reads the list, the delegate's acceptance on it included (COR-066 point 3). So accept does not wait for the floor's declaration.
- **Through a merging component.** The record lands through a component that carries out merges and applies this point (point 13). One committed straight to the default branch, or merged any other way, is a person's to accept (COR-066 point 2).
- **A component keeps its own.** Where a component's record keeps the acceptance of its records, rules or entries for a person, it stays the person's until that record hands it on, as COR-064 point 1 has for answers.
- **No raise of a budget.** A rule that needs room in a rules file waits for the person, since raising the budget stays theirs ([COR-069](COR-069-rules-word-budget.md) point 4).

**Accepting.** The delegate reads the record and the agreement word for word, and accepts or holds. It writes `accepted` in a commit of its own within the change, before work there rests on it, and accepting a record accepts the edits its Implications name (COR-066 points 1 and 5). A rule's origin either cites a decision record accepted by a person, or by the delegate under this point, or names as its decider the person whose agreement the rule carries out, quotes the agreement, marking the words an agent wrote, and says the delegate accepted it ([COR-051](COR-051-rule-sets.md) point 5). The delegate never refuses a record, since refusing closes the change, which stays a person's.

**At the merge.** For each acceptance the change says is the delegate's, the merging component has, at the head it merges, a verdict from each reviewer the setting requires of its kind and from the acceptance reviewer, each resting on no other session's word (point 5). The acceptance stands only where each approves that head. A finding for a person on the record or rule holds the change as a withheld approval does (point 5). Otherwise the change waits for a person, who accepts the record through the list (COR-066 point 3) or closes the change.

**The acceptance reviewer** is neither the delegate nor the drafter. It reads each acceptance the change says the delegate made in the landing check's list, with its named edits as made and its edits since, and withholds its approval unless:
- the trace holds, each quote matches its source where the source can be read, and a passage the delegate wrote counts only as far as this point lets it;
- the change names a drafter other than the delegate;
- the record is of no held kind;
- each named edit, as made, says what its name says and goes no further;
- what the person is told of the record (point 12) says what it decides;
- the default branch, read as point 5 reads it, names that delegate, and puts the record's question at accept.

- **An edit after the acceptance** is accepted only by the delegate accepting the record again under these tests, or by a person through the list.
- **A person's acceptance.** An acceptance the change does not say is the delegate's is a person's, and holds the merge for a person, as COR-066 point 3 has it. A person who authorises a merge reads the list first, the delegate's acceptances on it included. So a wrong claim, either way, leaves the record to a person.

### 7. What stays a person's at every level

At every level, these wait for a person, and the change says in plain words what each changes:
- **Who accepts or who merges.** A change that decides or changes who accepts a record or a rule, who authorises a merge, a standing authorisation, the delegate, what the delegate may decide or the tests it applies, or the person's declaration of point 8. A change that raises the setting is one, and one that only lowers it is not (point 9).
- **What gates a merge or an acceptance.** A change that removes or loosens a check, an existing test among them, a reviewer, a rule, of its own layer or another's ([COR-070](COR-070-capability-loaded-rules.md) point 4), or a condition of points 5 and 6, and a record that places a question at a level (point 13).
- **What agents may run, write, start or reach.** A change that loosens it, by any means, a record's named edits included, such as through the permission model ([COR-028](COR-028-permission-model-realization.md)), a sandbox, a grant of paths through the agent overlay, an agent's tool access ([COR-013](COR-013-agent-architecture.md) point 7), a switch that lets an agent run on its own, or the removal of a consent a record asks of a person.
- **Releasing and publishing,** which leave the repository and which no follow-up takes back, a merge that starts either among them. Whether a merge into the default branch starts either is a fact of the project, which the person's declaration states and no reviewer judges, and where it does, land hands nothing on (point 8).
- **Every other grant or consent a record asks of a person,** such as the consent before a configuration key is written (COR-048 point 5), naming the delegate among them.
- **Raising a rules file's budget** (COR-069 point 4).
- **A question only someone's account can settle,** such as whether a change was meant (COR-064 point 3).

Where an agent or a reviewer cannot tell whether a change is of these kinds, it holds it: the delegate holds such a record, and each reviewer the merge waits for, with the acceptance reviewer, withholds its approval. Under a standing authorisation, no reviewer's approval, an agent's or a person's, stands for a change of these kinds: the change stops and asks the person who authorises merges, as at ask.

**The floor.** A change that alters a file on the floor waits at its merge for a person at every level, whatever it means. The floor holds, by role:
- the files that govern how a change is reviewed and merged: the configuration of the backbone and of each component; the harness's settings, and the instructions, rules and skills it loads, with each file they include or import; the definitions of the reviewers, of the delegate and of each agent or component that decides in a person's place; every rule set, and the conventions the reviewers judge by; the workflows the host runs on a change; the code that runs the checks, the reviews and the merge; and the files that choose and run the tests, such as their configuration;
- the files that set what agents may run, write, start or reach;
- what the project receives from elsewhere, the dependencies it declares and locks among them, and the versions it records ([COR-059](COR-059-version-transition.md) point 1).

A test is not on the floor for being a test: a change that removes or weakens an existing test is held as one that loosens a check, and a test a change adds is judged by its reviewers. Nor is a decision record a convention here: a record is held only by the kinds above.

The floor is read from the set of such files the methodology declares, as a later record decides. It fails closed:
- **Unknown until declared.** Until a declaration of every role can be read, land hands nothing on. Accept does not wait for it, since the floor holds only the merge (point 6).
- **Both states.** The declarations are read at the base's tip and at the merge the change would land, and the floor is both together, so a change that drops a declaration and edits its file still waits.
- **Nothing narrows it.** The setting may add files to the floor, and take none away.
- **A lowering passes.** A change whose only change on the floor lowers the setting is not held for it (point 9).

The setting reaches neither the confirmations an agent's operational rules ask of it in a session, such as before a destructive operation, nor the permission model, whose grants it never widens.

### 8. The person declares the level and the reviewers it rests on

- **What it declares.** The setting holds, as the default branch's tip holds it, the person's declaration of:
  - the *level it turns on*, above which no question is handed on (point 3);
  - the delegate, which answer and accept need (point 2);
  - the *merge reviewers*, whose approval of a head land rests on, at least one (point 5);
  - the *answers' reviewer*, which checks each answer the delegate decided. COR-064 point 4's check of every answer no change owes stays with the reviewer the project chose there, and the two may be one;
  - for each kind of record or rule, the reviewers it requires before the delegate may accept it;
  - the *acceptance reviewer* (point 6);
  - whether a merge into the default branch releases or publishes (point 7).
- **Only the person's.** Only the person writes it, in a change point 7 holds, save a change that only lowers it (point 9). No install or upgrade writes any part of it, save the move of a delegate's name the person wrote before (point 10). The configuration command that writes it proposes the agent a component offers as the delegate (point 10), and the person's change names the delegate with the level and the reviewers.
- **Nothing on until it is made.** Once the backbone a project runs reads the setting, no level hands anything on until the declaration can be read. A declaration counts only where it states the level it turns on, so the change that turns a level on shows it. Then each level up to that one hands on only what its roles are declared for: land needs the merge reviewers and a statement that a merge neither releases nor publishes, answer needs the answers' reviewer, and accept, for a kind of record, needs its required reviewers and the acceptance reviewer. A role that names none declares nothing. An absent setting holds no declaration, so it hands nothing on.
- **Agents of the project.** Each role names an agent of the project, tested as COR-064 point 2 tests the delegate's name, save that the merge reviewers may name the project's review by a person, where it has one. A reviewer that is the delegate counts as none, and so, for a change, does one that drafted what it would check.
- **Verdicts.** Each gives a verdict that approves, withholds approval or leaves a finding for a person (COR-057 point 3). One that gives no such verdict fills no role.
- **The merge's own reviewers.** Reviewers the merging component's configuration requires add to the merge reviewers, and never stand in for them.
- **Before the backbone reads it.** Until the backbone a project runs reads the setting, the delegation of the answers no change owes stands as it stood: the friction key names the delegate (COR-050 point 14), which decides those answers under the reviewer the project chose (COR-064 point 4), and no level hands anything else on. This record decides that reading itself, so it rests on no text this record edits.

### 9. Where it lives, and who changes it

- **The default branch holds it.** The setting counts as the default branch's tip holds it ([COR-054](COR-054-default-branch.md)), for a merge into any branch, so no change raises the level for its own questions.
- **Its writers.** A change a person authorises, on their own word; the backbone's configuration commands, on a person's word, under the consent COR-048 point 5 asks; and the upgrade's writes of point 10. No agent writes it on its own initiative.
- **A raise is held and shown.** A change that raises the setting (point 3) waits for a person at every level (point 7). It is shown to the person who authorises its merge, and no authorisation given before that person could see it covers it.
- **A lowering counts at once.** A change that only lowers the setting is not held, and counts for every clone once it merges, save for a change already waiting in a queue (Rationale, "What the setting cannot hold"). Before then, a setting in a working tree, committed or not, counts where it lowers a level, for the runs that read that working tree, and nowhere where it raises one. A person's word lowers the level for their session, and a grant in words counts for nothing.
- **What cannot be read reads as ask.** A setting any part of which cannot be read counts, as a whole, as ask for the whole project, and validation fails it. So does a configuration that holds a top-level key no record owns, which may be the setting misspelt. This is what a command reads under COR-048 point 4, not the reading of an absent setting (point 10).
- **Validation** also fails an unknown level, an area it cannot match, a reviewer or a delegate that names no agent of the project, and two names of the delegate that differ (point 10).

### 10. The default, and what the upgrade writes

- **An absent setting reads the top level** (COR-048 point 3), and hands nothing on, since it holds no declaration (point 8).
- **Written as the missing default.** Where the configuration holds no setting, the backbone's upgrade migration writes the top level, a missing default being the sign a migration may act on (COR-059, Implications). The first install writes nothing, since the absent setting reads the same, and its report says what the setting hands over, and that nothing is handed on until the person's declaration.
- **The name moves.** The upgrade's migration moves a delegate's name from where the configuration held it before into the setting. A name in the old place is its sign, since the person wrote it. Where the setting already names the same agent, the move removes the old key. Where the two name different agents, neither is the delegate until a person removes one, and validation says so.
- **Offered by a component.** A component may declare, in its package metadata, one agent of its own that it offers as the delegate, whose definition says when and how it decides (COR-064 point 2). The component decides which agent, in a record of its own. The configuration command that writes the person's declaration proposes it, and the person's change names it (point 8).
- **No other name.** No install or upgrade names a delegate, so a delegate the person withdrew stays withdrawn.
- **What is kept.** No write touches a setting or a delegate the configuration holds, save the move.
- **The consent.** The upgrade's migration writes under the consent of choosing the upgrade's target (COR-059 points 3 and 4).
- **The report** says what it wrote or moved, what each level hands over once declared, which parts of the person's declaration are missing, the agent a component offers as the delegate, how to lower the level, and how to withdraw the delegate.

### 11. Each person's machine shows the words once

- **Before the first decision.** Before an agent, or a merging component on a standing authorisation, first decides a question in a person's place on that person's machine, its run stops without deciding. It shows the setting's words, and leaves a mark in the person's own configuration on the machine, outside every repository. A later run for them there, from any clone of the project, decides.
- **The words** say, in plain words, what is handed on, each level the declaration turns on with the roles declared for it, what stays a person's, how the person is told, and how to lower the level at once.
- **New words show again.** The mark names the version of the words it showed, and a run whose words differ stops again, such as once a declaration turns on another level or declares another level's roles, or once a record places another question.
- **No mark, no decision.** A run that can keep no mark, such as one in an environment that keeps nothing between runs, decides nothing in a person's place, and says why.
- **What the mark shows** is that a run showed the words, not that a person read them.

### 12. The person is told, not asked

- **Recorded where it lasts.** Each decision made in a person's place, by an agent or by a merging component on a standing authorisation, is recorded with what was decided, what decided it, and the level and the area that let it:
  - **a merge,** with the change, where its merge keeps it in the default branch's history, with what the change's answers tell the person who authorises its merge (COR-050 point 3, COR-064 point 5);
  - **an answer,** as COR-064 point 5 sets out;
  - **an acceptance,** in the change and in the delegate's report to the person it works for. It says what the record or rule decides, in two sentences, and the agreement it rests on, with where and when. It names each passage an agent wrote, and which agent, each that only the drafter's account holds, and each choice the agreement left open;
  - **a question another record placed,** in the trail of the component that decided it.
- **Not taken where it cannot be recorded.** Where that record cannot be written, nothing is decided, and a person is asked.
- **One place to read.** A component that gathers for the person what waits on them gathers these too, and until one does, the report of the run that decided tells the person it works for. Nothing waits for the person to read them.
- **Within reach.** The person may replace an answer (COR-062 point 5), revert a merge, supersede a record accepted in their place, judge a finding left for them, or lower the level. A revert cannot recall what a merge started, which is why a merge that publishes stays a person's (point 7).

### 13. Every other record places its own questions

- **A question another record keeps** for a person stays theirs until that record places it at a level, such as when planned work is scheduled or closed, or how much a designing agent changes alone. Placing it, the record names what checks the agent's choice, or says that the person is told and nothing checks it. Such a record waits for a person (point 7), and none places a question point 7 keeps.
- **A component that carries out merges** gives no standing authorisation, and lands no acceptance by the delegate, until its own records say how it applies points 5 and 6: how it gets verdicts that rest on no other session's word, how a withheld one holds what the change alters, what bounds the state a change lands onto, and how what merges is what it judged. They may add conditions, and never drop one. They also place merges into a branch other than the default.
- **A reviewer the merge waits for,** a person among them, withholds its approval of a change of a held kind (point 7), and an agent's definition says so.

## Rationale

**Why one setting with ordered levels.** The person's question is how deep the agents may go, in one area or everywhere, and ordered levels answer it with one word for each area. Each level adds the next kind of question in the order of how much stands in for the person: a check of files for an answer; the checks and the reviewers the person chose, for a merge; and for an acceptance, the person's agreement, the record's reviewers and a reviewer of the acceptance. Accept sits above land because an acceptance decides what binds later work. It spares the person the wait in the middle of a change, before work may rest on the record, but their reading of the list at the merge only where a standing authorisation merges the change, so an acceptance takes no higher level than its merge.

**Why every level waits for the person's declaration.** A standing authorisation is the person's own, given once for a class they chose, so COR-064's rule that authorising a merge stays a person's stands. Land rests on reviewers the person declares, as answer and accept do, so no level hands anything on in any project before the person acts, and an absent setting can read the top level safely. The declaration states the level it turns on, so the change that turns a level on shows it, and each machine shows the new words. COR-064 rejects a standing acceptance of every answer of a kind because nobody would read each answer, while here the reviewers the person named read each change before it merges.

**Why a verdict rests on no other session's word, and a withheld one holds what the change alters.** The agent that accepts or lands a change could pass on a verdict never given for that head, so a verdict counts only where it rests on no other session's word, as one from a run the merging component started for that head does, or a person's own approval of it. A review run again until it passes would let chance decide. So a withheld verdict, or a finding for a person on a record, holds what the change alters, whatever commit carries it, and the next run reads its findings, until a verdict finds them met or a person judges them.

**Why a finding for a person holds no merge, and holds an acceptance.** A finding for a person withholds no approval (COR-057 point 3). Holding each merge on one would bring the person's word back into the merges the setting spares, while merging changes only when the person judges it. An acceptance chooses what the project decides, and a question about it for the person is one the delegate would answer for them.

**Why the agreement can stand in, choice by choice.** The choice a record makes is the person's, and the agreement holds it, so what remains is whether the record carries it out, which the acceptance reviewer checks, and whether it is sound, which the record's reviewers judge. An agreement seldom states every choice, so a point may settle what its passage leaves open, within what the passage asks. That bound is a judgement a generous reader stretches, so the list of choices left open, which reaches the person, is what keeps it honest.

**Why words an agent wrote count, and the delegate's own words and drafts do not.** An agent writes most issues from what the person said, so barring such words would bar most agreements, and counting them unmarked would hide that the person never wrote them. Words the delegate wrote are its own reading of the person, and a confirmation that only an agent reports is that agent's word again, so only the person's own words count there. A record the delegate drafted, or a choice it proposed, is its own choice. Accepting against either would leave the check to the one it checks, as COR-064 found for answers.

**Why some changes stay a person's, by effect and by file.** An agent that could widen what agents may do, change who accepts or merges, or remove what checks them would decide the limits of its own powers. Stated by effect, the hold covers any means. A test of effect is a judgement an agent makes about its own change, so a floor of files, read from the diff alone, nets the machinery whatever a change means. A project whose own code runs its checks, reviews and merges keeps that code on the floor, so land covers little of it. The files that choose and run the tests are on the floor and the tests are not, so a change that adds a test lands as it would without one, and one that weakens a test is held for what it does. Whether a merge publishes is a fact of the project, not of a change, so the person states it, and no reviewer reads it from a diff. The floor holds the merge and not the acceptance: a record or a rule on it reaches the default branch only through a merge that waits for a person, who reads the list, while the delegate's acceptance still spares them the wait in the middle of the change.

**Why the reviewers have one home, declared only by the person.** A reviewer's check is what replaces the person's reading, so without one there is no delegation (COR-064 point 4), and choosing it is the person's consent to the delegation, so no install writes it. Declared in the setting, the reviewers count as the default branch holds them, and a change to them is held, so no change lowers the reviewer that would judge it. A delegate that decides answers under COR-064 keeps doing so until its project's backbone reads the setting. From then it decides nothing until the person's declaration, like every level, so the delegation stops only once the person can declare it.

**Why the delegate is named by the person, in the setting.** The setting holds every other part of the delegation, so the name joins it, under one reading for a fault and one rule for who writes it. Naming the delegate chooses who decides in the person's place, so the person names it, in the change that declares the level and the reviewers. The configuration command proposes the agent a component offers, so the person need not find it. A name the person wrote in the old place is their own earlier word, so the upgrade moves it, and where two names differ, nobody decides until a person chooses.

**Why each person's machine shows the words.** Every clone reads the setting one person authorised, so a person on another machine would otherwise meet nothing that shows what is decided in their place before it is. The mark stays outside the repository, so the stop comes once for each version of the words, and a run that can keep no mark would stop forever or decide unshown.

**Why a lowering counts at once, and an unreadable setting reads ask.** Lowering errs toward asking, which harms nothing, so a working tree or a word suffices for the runs that read them, while a raise hands on decisions the person made before, so it is shown in review. A setting that cannot be read, or that a misspelt key may stand in for, could be dropping a part that lowers the level.

**Why other records place their own questions, and the person is told.** A record may keep a question for reasons this record cannot see, so it places its own questions on the one scale. Told what was decided, the person can undo it or lower the level, while a decision with no record would never reach them.

**What the setting cannot hold.**
- **Merges past the component.** A merge sent past the merging component, by another command or the host's own controls, meets none of its conditions, as COR-066 says of the landing check. A record that lands so reads `accepted`, and nothing tells the delegate's acceptance from a person's.
- **A queue.** A lowering, or a change on the floor, that merges while a change waits in a queue does not reach that change, which merges as it was judged.
- **The session that runs the component.** A verdict from a run the component started rests on that session, often the delegate's own, and what it shows of the run rests on that session's honesty.
- **Who decided, drafted or wrote.** Who decided an answer, who drafted a record and who wrote an agreement show in no file. So the reviewers check what the change names, and the bars on the delegate rest on its discipline, as COR-050 point 3 says of who read an answer. Words no file holds rest on the drafter's account, and the person, told after the merge, is the check on them.

### Alternatives considered

- **A switch for each kind of question.** Not taken. Two settings would answer one question with no rule for which wins.
- **An absent setting reads ask.** Not taken. The declaration states the level it turns on, so the level an absent setting reads hands nothing on by itself. Reading ask would have the person state each level twice, in the setting and in the declaration, before it turns on.
- **Land by absence, as the methodology's own authorisation.** Rejected. Merges would go through in a project whose person authorised none.
- **The upgrade writes the offered name, inert until the declaration.** Rejected. The name would be a choice no person made, and a backbone migration acts only on a positive sign that its change is needed, which a missing default is and a missing name is not (COR-059, Implications).
- **A delegate named wherever none is named, or an absent name read as the offered one.** Rejected. A person who withdrew the delegate would see it return.
- **The delegate accepts on the reviewers' passes alone.** Rejected. The reviewers judge whether a record is sound, not whether it is what the person agreed.
- **Only words the person wrote count, or a separate delegate for acceptance.** Not taken. Most agreements are issues an agent filed, and a second delegate would split the place the person looks.
- **The acceptance reviewer checking every acceptance in the list.** Not taken, unlike COR-064 for answers. An acceptance not said to be the delegate's holds the merge for the person, so a wrong claim errs toward asking.
- **A finding for a person holding the standing authorisation.** Not taken. It would bring the person's word back into most merges the setting spares, on findings that ask the person to judge, not to authorise.
- **A floor the person may narrow.** Rejected. A change could rewrite what checks it.
- **Every test on the floor.** Rejected. A change that adds its tests would wait for a person, while the same change without them merged.
- **Areas of planned work, such as a feature.** Not taken. The links that tie a change to planned work lie outside the default branch, where a change can write them, so such an area could only lower the level, which a merging component can do by a condition of its own.

## Implications

The edits this record makes to accepted records and rules, sorted by kind and then by id, are made in its change once it is accepted (COR-066 point 5). Each is sorted by what the passage it edits does. Where the passage decides what this record decides otherwise, its record is overturned in part there. Where the passage restates what another record decides, or this record completes it, it is refined in place.

**Overturned in part.** Each gains a *Partially superseded by [COR-072](COR-072-delegation-levels.md)* top line, which says what this record decides there and names the passages it overturns, which stay as they stood.
- **COR-064:** the delegation setting names the delegate and decides how much it decides: the answers no change owes at answer and above, and at accept a record or a rule that carries out the person's agreement, each once the person declares the level and the reviewers it rests on. No install or upgrade names a delegate, and the upgrade moves into the setting a name the friction key holds. Until the backbone a project runs reads the setting, the friction key names the delegate, and from then the setting does. Overturned: that the delegation covers nothing else a person decides; that the friction key names the delegate, once the backbone reads the setting, and that no migration moves the name; and that accepting a decision stays a person's, as to the delegate's acceptances. Point 2's "on the person's own word" stands, since the move carries the person's earlier word, and so does point 6's item on authorising a merge, since a standing authorisation is the person's.
- **COR-066:** where the setting lets it, the delegate accepts a record or a rule in the person's place, in the change that proposes it. Where a standing authorisation merges the change, the reviewers this record names check that acceptance at the merge in the person's place, and the person is told afterwards. Overturned, for the delegate's acceptances: that a person accepts, and that an edit after the acceptance is accepted only through the list. Overturned, for a merge on a standing authorisation: that the person who authorises the merge sees first what it makes accepted, and the new record's edits. A person who authorises a merge reads the list, the delegate's acceptances on it included.

**Refined in place,** each edit with `(refinement per COR-072)` on what it refines, its record's decision standing:
- **COR-048 point 4:** a reading command takes the reading the owning record names for a value it cannot read, or one an unknown key may misspell, so that a fault need not widen what a command does.
- **COR-050 point 3:** a delegate decides an answer only where this record hands it the answer. **Point 14:** the delegate is named in the delegation setting and, until the backbone a project runs reads it, in the friction key.
- **COR-051 point 4:** a rule is accepted by the person's review, or by the delegate where the setting lets it. **Point 5:** a rule the delegate accepted has as its decider the person whose agreement it carries out, in the agreement's words, marked where an agent wrote them, and says the delegate accepted it, or it cites a decision record that a person or the delegate accepted.
- **COR-064 point 1:** the delegate decides the answers no change owes where this record hands them to it. **Point 4:** once the backbone a project runs reads the setting, it decides none where the setting declares no reviewer they rest on.
- **COR-065:** its summary, Context, points 3 and 5 and Rationale say a record is accepted by a person, or by the delegate where the setting lets it. Point 3 adds that where a standing authorisation merges a change, its reviewers judge alone whether it needed a record, and one that finds it did holds the merge for a person.
- **COR-067:** its summary, point 2, Rationale and Implications say the delegate accepts a name of a point with nothing to carry out only with a record it accepts, never one added alone, and that the authoring skill and agent name such a point for whoever accepts the record.
- **COR-069 point 4:** a rule that needs room waits for the person, who accepts it with the raise, where the delegate would otherwise accept it.
- **COR-070 points 3 and 4, and its Rationale:** a rule the delegate accepted where it is kept is seen and judged before its merge by the person who authorises it, since a change to a rule set waits for a person.

**An edit that changes no decision.** COR-025's top line, which restates COR-066, reads "after it is accepted in the change that proposes it" for "after a person accepts it in the change that proposes it".

**Rules of the backbone's loaded set.** The set takes a new major version, since the edit to RS-OPS-020 tightens it (COR-051 point 7), and any raise of its budget the edits need is the person's (COR-069 point 4). Each rule's anchors gain the point of this record it follows.
- **RS-OPS-002, the acceptance gate:** a person accepts a proposal in its change, or the delegate does where this record lets it. Save on a standing authorisation, the person who authorises the merge sees first what it makes accepted, and an edit after the delegate's acceptance is accepted through the list or by the delegate accepting again.
- **RS-OPS-020:** the delegate decides an answer only where this record hands it the answer, and the rule names no key for the delegate.
- **RS-OPS-023:** no work rests on the choice until the record is accepted.

**[project-management:DEC-055-pr-lists-answers] point 3,** refined in place: an entry flagged as not asked for needed the delegate's decision where this record hands it the answer.

**Not edited here.** A component that carries out merges keeps each merge and each acceptance a person's in its own records until a record of its own applies points 5 and 6 (point 13), and that record lands no earlier than this one. A component that offers a delegate decides which agent, in a record of its own. A walking skeleton's convention entries stay a person's to accept, as a component keeping its own ([software-engineering:DEC-004-skeleton-conventions-in-corpus]).

**What carries it out.**
- **An architecture record realizes this record:** the key's shape; the person's declaration; the field by which a component offers its delegate, and the configuration command that proposes it; the backbone's reading of a change's levels and floor, with its reading for a fault and for an unknown key; the one carrier by which a working tree's lowering reaches that reading; the form of the quotes and the map; point 11's step and its versioned mark; and where point 12's report lives.
- **The floor** follows the record that decides how the files governing review and merge are declared.
- **The schema, the upgrade migration and the configuration command that writes the declaration** carry points 8 to 10, the move of the delegate's name among them.
- **The offered delegate, and each reviewer point 8 names,** say their part in their definitions (COR-013), and each reviewer a merge waits for withholds its approval of a change of a held kind.
- **The documents that state the gate and the delegation,** the decision-record specification's acceptance gate among them, change with the build that makes them true.
- **Stands on these records, all accepted:** COR-012, COR-013, COR-028, COR-048, COR-050, COR-051, COR-054, COR-057, COR-058, COR-059, COR-062, COR-064, COR-065, COR-066, COR-067, COR-069 and COR-070.
