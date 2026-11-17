---
id: COR-075
title: In a relaxed acceptance mode, the delegate accepts a record that carries out the person's agreement
status: proposed
date: 2026-11-17
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project's committed configuration sets how its decision records and rules are accepted: `strict` or `relaxed`. Strict is the acceptance gate as it stands, where a person accepts each one. Relaxed lets the delegate the project names accept a record or a rule in the person's place. It may do so only where the reviewers the project requires passed it, and where each choice it makes carries out an agreement the person made, such as an issue, a note or their words in a conversation.

A reviewer checks each such acceptance before the merge. The person is told after it what was accepted and on which agreement, and is not asked. A record that changes who accepts or who merges, or that loosens what agents may run or write, waits for the person in both modes. The install and the upgrade write `relaxed`, and name a delegate where the project names none. Their report says how to set `strict` or withdraw the delegate, and after that only the person changes either.

## Context

A decision record or a rule binds only once a person accepts it, in the change that proposes it ([COR-066](COR-066-accepted-before-landing.md) point 1). A person's review accepts a rule ([COR-051](COR-051-rule-sets.md) point 4). A person may name one agent, the *delegate*, to decide in their place the answers on artefacts that no change owes, and accepting a record stays the person's ([COR-064](COR-064-answer-delegate.md) points 1 and 6).

Where agents do most of a project's work, most records carry out a choice the person has already made. The person filed an issue that says what the record decides, or wrote a scratchpad note, or said it in a conversation. The reviewers then judge the draft. What the person adds by accepting it is a reading: does the record say what they agreed, and nothing they did not? That is a check of a text against a text, which an agent with both in front of it is placed to make. Asked for it many times a day, a person accepts by habit, or the work waits.

What a person cannot hand on is the choice itself, and that lives in the agreement. Some records also change the gate itself, or what agents may do. An agent that accepted those could widen its own reach, which no agreement read by that agent should settle.

The delegate is named in the backbone configuration ([COR-048](COR-048-backbone-configuration.md)), on the person's own word (COR-064 point 2). A key of that configuration is written only by the writers its owning record names, with consent, and an upgrade migration that record specifies is one, where running the upgrade is the consent (COR-048 point 5). Every such migration runs inside a version transition, under the one consent of choosing its target ([COR-059](COR-059-version-transition.md) points 3 and 4).

## Decision

**A key of the backbone configuration sets the project's acceptance mode, `strict` or `relaxed`, as the default branch's tip holds it. Strict is the acceptance gate as it stands. Relaxed lets the delegate accept a proposed record or rule in the person's place, where the reviewers the project requires passed it with no blocking finding, and each choice it makes carries out an agreement the person made. The delegate never accepts a record it drafted. A reviewer checks every such acceptance, and the person is told after the merge, not asked. A record or rule that changes who accepts or who merges, or that loosens what agents may run or write, waits for the person in both modes. The install and the upgrade write `relaxed`, and name a delegate where none is named, and only the person changes either after that.**

**Terms.** *The person* and *the delegate* are COR-064's. An *agreement* is words the person wrote, or said they agreed to, that state a choice: in an issue, in a scratchpad note ([COR-012](COR-012-scratchpad-notes.md)), or in a conversation or another channel. To *hold* a record is to leave it proposed, for a person to accept as in strict mode. The *landing check* is the check of its own that COR-066 point 2 decides, and its *list* is the list of what a change makes accepted that COR-066 point 3 decides.

### 1. The mode is a key, read at the default branch's tip

- **Two values.** `strict` is the gate as it stands: a person accepts each record and rule (COR-066 point 1, COR-051 point 4). `relaxed` lets the delegate accept as points 3 to 9 set out.
- **Owned here.** This record owns the key (COR-048 point 2), and names its writers (point 2).
- **What an absent key reads as.** A key that is absent reads as `strict` (COR-048 point 3). So does one a reading command cannot read, which warns and takes that default (COR-048 point 4). `relaxed` is the value the install and the upgrade write, not what absence means.
- **The default branch holds it.** The mode counts as the default branch's tip holds it, as the delegate's name does (COR-064 point 2). So no change relaxes the mode for its own records.
- **At the acceptance and at the merge.** A delegate's acceptance stands only where the tip holds `relaxed` and names that delegate, both when it accepts and when the change merges. Where the mode or the name has gone in between, what it accepted waits for a person.
- **Relaxed with no delegate** accepts nothing, and every record and rule stays a person's.
- **Shown before it counts.** A change that sets, changes or removes the mode is shown to the person who authorises its merge, among what the change does. An authorisation given before that person could see it does not cover it, as COR-064 point 2 has for the delegate's name.
- **A person's word** stops the delegate accepting in the session where it is given, as it stops it deciding answers (COR-064 point 2). The mode leaves `relaxed` through a change.

### 2. The install and the upgrade write `relaxed`, and a delegate where none is named

- **The mode.** Where the configuration holds no mode, the first install and a backbone migration of the upgrade write `relaxed`.
- **The delegate.** In the same write, where the configuration names no delegate, they name the agent whose definition declares that it acts as the delegate (COR-013), where exactly one of the project's agents does. Where none does, or several do, they name none, and the mode accepts nothing until a person names one.
- **A component installed later.** The install of a component that ships such an agent names it in the same way, where the mode reads `relaxed` and the configuration names no delegate.
- **What is kept.** None of these writes touches a mode or a delegate the configuration already holds. A project that names a delegate keeps it.
- **Safe over any state.** The migration acts only on an absent mode, the positive sign that its change is needed, so a transition may run it again over any state (COR-059 point 6). A mode the project wrote, `strict` or `relaxed`, keeps it from writing either key. A replay restores a mode the project deleted, so the way to turn the mode off is to write `strict`, and the release's notes say so.
- **The consent.** The upgrade's migration writes both keys as a migration the records that own them specify, where running the upgrade is the consent (COR-048 point 5). Choosing the upgrade's target is that consent, and it covers every part of the transition (COR-059 points 3 and 4). An install, the first or a component's, writes them with the consent COR-048 point 5 asks of it: asked once where a person can answer, or given by an explicit confirmation flag. With neither, it writes nothing, and nothing changes.
- **How this refines COR-064 for these writes.** COR-064 point 2 has only the person name the delegate, on their own word, and point 6 keeps naming it the person's. These writes name one only where nobody is named, under the consent of the install or the upgrade the person chose. Like any name, it counts only once the default branch holds it, and the change that holds it is shown before it counts (point 1, COR-064 point 2). After that, only the person names, changes or withdraws the delegate, and only the person changes the mode. No agent writes either on its own initiative.
- **The report.** The install and the upgrade say what they wrote: the mode, and the delegate they named, or that they named none and why. They say what `relaxed` lets the delegate do, how to set `strict`, and how to withdraw the delegate.

### 3. What the delegate checks before it accepts

In a relaxed mode, the delegate accepts a proposed record or rule in the person's place only where all of these hold for the text it accepts:

- **The reviewers passed it.** Each reviewer the project requires of a record or a rule judged this text. None left a finding the project counts as blocking, or a finding addressed to the person rather than to the drafter. Where the project requires no reviewer of a record or a rule, the delegate accepts none.
- **It carries out an agreement,** choice by choice (point 4).
- **The delegate did not draft it** (point 5).
- **It is of no held kind** (point 8).
- **It lands by a merge.** A record committed straight to the default branch is accepted by a person before the commit, as COR-066 point 2 has it.
- **A component keeps its own.** Where a component's record keeps the acceptance of a record or rule of that component's for a person, that acceptance stays a person's until the component's record hands it on, as COR-064 point 1 has for answers.

**Accepting.** The delegate reads the record and the agreement word for word, and accepts the record or holds it. An agent writes `accepted` only once it has, as for a person's acceptance. The delegate never refuses a record: refusing closes the change, which stays a person's (COR-066 point 1). Accepting a record accepts the edits its Implications name, whoever accepts it (COR-066 point 5).

**The text that lands.** The acceptance stands for the text the delegate read. An edit made after it is accepted only where the delegate accepts the record again under these tests, the reviewers having judged the edit, or where a person accepts it through the landing check's list (COR-066 point 3).

### 4. The agreement covers each choice the record makes

- **It states the choice.** An agreement says what is chosen, not only that a choice is wanted. An issue that asks for a record on a question, without the answer, covers nothing.
- **Quoted in the change.** The change quotes word for word each passage of the agreement the record rests on, and says where it is and when it was written or said.
- **Mapped choice by choice.** The change maps each point of the record's Decision, and each edit its Implications name, to the passage it carries out. For a rule, its statement. The Rationale and the alternatives weighed are the drafter's, and need no passage.
- **Covered.** A point is covered where it makes the choice its passage states, in the passage's meaning. A point that settles a choice the agreement leaves open is covered only where the agreement leaves that choice to the drafter in its own words. Where a point is not covered, or the record and the agreement disagree, the delegate holds the record.
- **Read where it lies.** An agreement in a file of the repository, or in the project's issue tracker, the delegate reads there, never from the quote alone (COR-064 point 3). A quote it does not find there, as the source stood when the quote was taken, fails.
- **Words no file holds.** Words the person said in a conversation the delegate cannot read are the drafter's account of them. The delegate may accept on them, and the person, told of the quote after the merge (point 7), is the check on it. That is the hazard left, as COR-066 point 3 leaves a person's acceptance resting on the author's word where no component shows its list.

### 5. Never a record it drafted

- **Another's draft only.** The delegate never accepts a record or rule it drafted, in whole or in part. Such a record is a person's, as in strict mode.
- **What drafting is.** Writing a choice of the record, or changing one. Mending a word that changes no choice is not drafting, as writing an answer it decided is not (COR-064 point 3). A choice the delegate would change is a draft of its own, which goes back to the drafter, and the reviewers judge it again.
- **Named in the change.** The change names the agent that drafted the record. The files cannot tell who drafted it, so the bar rests on the delegate's own discipline, as COR-064 point 4 says of who read an answer.

### 6. A reviewer checks each acceptance the delegate made

- **Each one.** A reviewer checks each record and rule the change says the delegate accepted. It reads each in the landing check's list (COR-066 point 3), its text and its edits since the acceptance, never in an account the delegate or the change's author composed. It blocks the merge when one does not hold.
- **Against point 3's tests.** The reviewers' verdicts stand for the text that lands. Each choice maps to a passage that states it, and that its source holds as quoted where the source can be read. The record is of no held kind. The change names a drafter other than the delegate. The two sentences the person is told say what the record decides (point 7). The default branch's tip holds `relaxed` and names the delegate.
- **Neither the delegate nor the drafter.** Which reviewer is the project's choice, as in COR-064 point 4. It may be the one that checks the answers no change owes.
- **No reviewer, no acceptance.** Where the project chose no such reviewer, or chose the delegate, the delegate accepts nothing, and every record and rule stays a person's.
- **A person's acceptance** is outside this check. The change says which acceptances the delegate made. Every other acceptance is a person's, and keeps COR-066 point 3 whole (point 9).

### 7. The person is told after the merge, not asked

- **What.** For each record and rule the delegate accepted: what it decides, in two sentences, the agreement it rests on with where and when, and that the delegate accepted it.
- **Where.** In the change that lands it, where the person who authorises its merge reads it, and in the delegate's report to the person it works for. A component that gathers for the person what was decided in their place may bring these into one report (COR-064 point 5).
- **Never a gate.** A change carrying such acceptances merges under the same authorisation as any other.
- **Undone by a follow-up.** The person undoes an acceptance with a follow-up record that supersedes the record, in whole or in part. Until then the record stays accepted, and the follow-up's change mends what rested on it.

### 8. What stays held in both modes

In both modes, these wait for the person, and the change says in plain words what each changes:

- **Who accepts or who merges.** A record or rule that decides or changes the acceptance mode, the delegate, what the delegate may accept or the tests it applies, or the reviewer that checks its acceptances. So is one that decides or changes who authorises a merge into the default branch, or an authorisation of merges given ahead of the changes it covers.
- **What agents may run or write.** A record or rule that loosens what agents may run or write: in the permission model ([COR-028](COR-028-permission-model-realization.md)), in a confinement of the commands they run, such as a sandbox, or by taking away a consent a record asks of a person.
- **Where the delegate cannot tell** whether a record or rule is of these kinds, it holds it.
- **Only records and rules.** The mode reaches the acceptance of records and rules alone. Every other decision a record keeps for a person stays theirs, among them authorising a merge, a consent, raising a rules file's budget ([COR-069](COR-069-rules-word-budget.md)), making a release and publishing.

### 9. How the mode reaches the gate

- **Within the change (COR-066 point 1).** The delegate accepts in the change that proposes the record, before work in it rests on it, as a person does. Work resting on it waits for that acceptance, and a change built on it lands no earlier. A record the delegate holds waits for a person, and only a person refuses one, by closing its change.
- **The landing check (COR-066 points 2 and 4)** stands as it is. A record the delegate accepted is accepted, and one it held is a proposal.
- **The list (COR-066 point 3).** It is made and shown as it stands. A record or rule a person accepted is seen first by the person who authorises the merge, in both modes. One the delegate accepted is checked before the merge by point 6's reviewer in the person's place. It reaches the person as information: before the merge where they authorise that change, and after it where the authorisation was given ahead of the change (point 7).
- **A rule (COR-051 points 4 and 5).** A rule the delegate accepts is accepted as one a person's review accepted, and carries an origin as any accepted rule does.

## Rationale

**Why a mode, and not a wider delegation alone.** A person who named a delegate under COR-064 handed it answers on artefacts, on the promise that it decides nothing else. Widening that delegation to records without a word from them would break the promise. So acceptance is a setting of its own, which the person sees when it is written and changes when they choose.

**Why the delegate may accept at all.** The choice a record makes is the person's, and the agreement already holds it. What remains is whether the record carries the agreement out, choice by choice, and whether the reviewers found it sound. An agent with the agreement and the record in front of it makes that check, and a reviewer checks it again. The person keeps the choice, and stops reading each record to confirm what they already said.

**Why an absent key reads `strict`.** A mode written by the install, the upgrade or the person rests on a consent. An absent key rests on none, as in a project whose upgrade has not run. Reading it `relaxed` would hand records to a delegate the person named only for answers. Reading it `strict` is the gate as it stood, and a reading that fails falls back to it too. The cost is a project that never runs its own migrations, such as the one where the methodology is authored, which writes the key by hand.

**Why the install and the upgrade write `relaxed`, and a delegate.** A project whose agents do most of its work gains from the mode at once, and a mode that waits to be found is chosen late. Written with the delegate, the mode works from the first upgrade. Written only where nothing is set, it keeps every choice a project made. The report says what was written and how to undo it. The change that holds the writes is shown to the person who authorises its merge, so the writes reach a person even where an agent ran the upgrade.

**Why these writes rest on the upgrade's consent.** COR-048 point 5 lets a migration its owning record specifies write a key, with the upgrade as the consent, and COR-059 point 4 makes choosing the target that one consent. Naming the delegate without the person's word departs from COR-064 point 2, so this record says where: only where nobody is named, only once the default branch holds it, and shown before it counts. After that the name is the person's again.

**Why an agreement covers each choice, not the record's top line.** The points of a record bind later work as much as its first sentence does. An agreement that covered only the top line would let a draft settle the rest unseen. Mapping each point to its passage gives the delegate and the reviewer one concrete question each: does this passage state this choice?

**Why the delegate reads the agreement where it lies.** A quote is the drafter's account, and words can steer an agent. Read in its source, the agreement is the person's own words. A conversation the delegate cannot read stays an account, so the person is told of each such quote after the merge, and can undo what rests on a wrong one.

**Why never a record it drafted.** The drafter chooses what the record says, and the acceptance chooses whether it carries out the agreement. One agent making both would leave the second choice to the first, as COR-064 point 3 found for answers. Another agent usually drafts, such as the session the person spoke to or an agent that builds the change, so the bar costs little.

**Why a reviewer checks each acceptance.** The delegate is an agent, and an agent can misread an agreement fluently. An independent reviewer replaces the person's reading of the list before the merge, so without one there is no acceptance. It works from the landing check's list, since an account of what was accepted can be wrong.

**Why the person is told, not asked.** Told, the person can supersede any record they disagree with. Asked, they would be back to reading each record. A follow-up that supersedes undoes the acceptance in the way every decision is undone, and keeps the history.

**Why some records stay held in both modes.** A record that changes who accepts or who merges, or that loosens what agents may do, widens the reach of the agents that would accept it. An agent that could accept such a record would decide the limits of its own powers. These records are rare, so holding them costs little. Holding where the delegate cannot tell errs toward asking, which harms nothing.

**Why only records and rules.** A release and a publication leave the repository, and no follow-up record takes them back. A merge's authorisation, a consent and a budget's raise are decisions their own records keep for a person. The mode moves only the reading that an agreement settles.

**Why a person's acceptance keeps the list before the merge.** The landing check cannot tell who wrote a status (COR-066 point 3). An acceptance said to be a person's that no person gave is seen there, before it lands. The delegate's acceptances have a reviewer in that place, and a claim that the delegate accepted only brings a record under its tests.

### Alternatives considered

- **An absent key reads `relaxed`.** Rejected. A project whose upgrade has not run, or that named a delegate for answers alone, would hand records to the delegate with no consent.
- **The delegate accepts on the reviewers' passes alone.** Rejected. The reviewers judge whether a record is sound, not whether it is what the person wants.
- **An agreement covers the record's top line only.** Rejected. The points bind later work, and the person would not have chosen them.
- **The upgrade asks before it writes.** Not taken. Where nobody can answer, it would write nothing, and the mode would wait to be found. The upgrade's consent covers its migrations, and the report and the change's review show the person what was written.
- **A delegate for acceptance apart from the one for answers.** Not taken. One delegate gives one place to look for what was decided in the person's place.
- **A field in the record naming who accepted it.** Rejected. Anyone writing the file can write it, as COR-064 found for answers, so no check could rely on it. The change and the delegate's report tell the person instead.
- **The delegate accepting its own drafts, checked by the reviewer alone.** Rejected. The choice whether the record carries out the agreement would be the drafter's.
- **Held records accepted too, with the person told after.** Rejected. An agent would widen its own reach, and the person would learn of it only after the fact.
- **A quote of the agreement read as its ground, wherever the agreement lies.** Rejected. A quote can be wrong, and where the source can be read, reading it costs little.
- **A mode for each area of work.** Not taken. One mode for the project is a choice a person can hold in mind. A finer setting can refine this one where a need appears.

## Implications

The edits this record makes to accepted records and rules, sorted by kind and then by id. Each is made in this record's change once it is accepted (COR-066 point 5), and each sentence added or rewritten ends with the pointer `(refinement per COR-075)`.

**Refined in place.** Each edit widens or completes what the record decides, and its decision stands. This record overturns no record in part, and replaces none whole.

- **COR-050 point 14:** the key's writers gain, for the delegate's name, the install and the upgrade migration this record names, each with the consent COR-048 point 5 asks.
- **COR-051 point 4:** a person's review accepts a rule, or, in a relaxed acceptance mode, the delegate accepts it in the person's place, as this record sets out.
- **COR-064:**
  - Its opening summary and its Decision's top line say that the delegation covers the answers no change owes and, in a relaxed acceptance mode, the acceptance of the records and rules this record names.
  - Point 2 says that the install and the upgrade this record names may name a delegate where none is named, under their consent, as the exception to "It names none by default" and to the person's own word. Only the person changes the name after that.
  - Point 6 keeps accepting a decision record or a rule, and every change to what an accepted one decides, the person's, save where a relaxed acceptance mode lets the delegate accept a record with the edits its Implications name. It keeps naming and withdrawing the delegate the person's, save that first name.
  - Its Rationale on where the line falls, and its rejected alternative of the delegate accepting records, say that the delegate accepts no record on its own judgment: only one that carries out the person's agreement, in a relaxed mode.
- **COR-065 point 3:** the record is accepted by a person, or by the delegate where a relaxed acceptance mode lets it, before work rests on it.
- **COR-066:**
  - Its opening summary and its Decision's top line say that a person accepts a record or a rule, or the delegate in the person's place where the project's acceptance mode is relaxed.
  - Point 1 says that an agent writes `accepted` only once the person, or that delegate, has.
  - Point 3 says that a record or rule a person accepted is seen first by the person who authorises the merge, and that one the delegate accepted is checked by this record's reviewer in that place, and reaches the person as information. An edit after the delegate's acceptance is accepted only by its accepting again, or by a person through the list.

**Rules of the backbone's loaded set.** Each edit widens its rule and tightens none, so the set needs no new major (COR-051 point 7), and the edits stay within its budget (COR-069).

- **RS-OPS-002, the acceptance gate:** a person accepts a proposal in its change, or, in a relaxed acceptance mode, the delegate may in the person's place, and an agent writes `accepted` only once one of them has. The person who authorises the merge sees first each record and rule a person accepted, and the delegate's acceptances reach the person as information. Its anchors gain this record.
- **RS-OPS-023:** no work rests on a choice until its record is accepted, by a person or by the delegate where this record lets it. Its anchors gain this record.

**What carries it out.**

- **The decision-record specification's acceptance gate** says who accepts in each mode, what the delegate checks, and what stays held.
- **The backbone configuration's schema** gains the key and its two values. The configuration reference documents it.
- **A backbone migration** writes the key and the delegate as point 2 says, and the release's notes say that a replay restores a mode the project deleted. The install and a component's install write them as point 2 says. Each one's report says what it wrote.
- **An agent that may act as the delegate** declares it in its definition, and says when it accepts, what it checks and what it holds (COR-013). In a relaxed mode, validation warns of a delegate whose definition does not read this record, as COR-064 point 2 does for that record.
- **A reviewer that checks the delegate's acceptances** says so in its definition, and reads the landing check's list.
- **A component that carries out merges** reads the mode and the delegate at the default branch's tip before it merges, shows the delegate's acceptances with the change, and reports them after a merge authorised ahead of the change.
- **The authoring skill for records and the agent that authors architecture records** say that a relaxed mode lets the delegate accept, and how a change quotes and maps its agreement.
- **No component's record is edited here.** A component whose record keeps the acceptance of its records or rules for a person, or holds a merge for a record or rule the change accepts, may refine that record where it is kept.
- **This record changes who accepts,** so it is held in both modes (point 8), and a person accepts it under the gate as it stands.
- **An architecture record realizes this record.** It decides the key's name and place, how an agent declares that it acts as the delegate, and where a project names the reviewers it requires of a record or a rule and the reviewer that checks the acceptances. It also decides how a change quotes and maps its agreement and names its drafter, and how the reviewer and the report read the acceptances.
- **Stands on these records, all accepted:** COR-012, COR-013, COR-028, COR-048, COR-050, COR-051, COR-059, COR-064, COR-065, COR-066 and COR-069.
