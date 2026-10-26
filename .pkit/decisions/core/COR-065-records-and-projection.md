---
id: COR-065
title: Where an accepted record decides, the rest of the system carries it out
status: proposed
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where an accepted record decides something, that record governs, and the rest of the system, such as the code, the documents and the skills, carries the decision out. This record calls that rest the record's projection. A choice that later work will build on, such as a library, an interface others use or a convention, starts with its record, accepted before work rests on it. Where the system and an accepted record disagree, the system is checked first for falling short, and a record changes only by a decision a person accepts. A record keeps the choice and its reasons, and the detail that carries it out lives in the projection. What no record decides stands as built until a record decides it. A scratchpad note comes before all of this: it explores, then retires into a record or another artefact.

## Context

[COR-006](COR-006-artifact-roles.md) gives each shape of content its kind: a record carries the *why*, a document the *what-is*, a skill the *how-to-do*, an agent the *who*, and a scratchpad note the *what-might-become*. It decides that the shapes are content peers, and that none is built on top of another. [COR-050](COR-050-anchors-and-friction.md) lets an artefact anchor a record it rests on, so a change to the record asks whether the artefact still holds. The decision-record specification lets work build only on an accepted record, and [COR-064](COR-064-answer-delegate.md) point 6 keeps every change to what an accepted record decides a person's.

None of these says which side gives way when the system and a record disagree, which new choices must start with a record, or where the detail that carries a decision out belongs. A change can then make a lasting choice in the code and leave the record to be written afterwards, or settle a disagreement by rewording the record to match what was built. Both turn the records into a description of the system, kept in step after the fact, rather than the place where its choices are made.

A project also holds choices no record states. [COR-025](COR-025-adr-decision-space.md) does not require a project that adopts architecture records to backfill the architectural decisions it made before, and [COR-051](COR-051-rule-sets.md) point 5 lets an accepted rule's origin be the decider's own words. A principle about records has to hold in such a project too.

## Decision

**Where an accepted record decides, it governs, and the rest of the system is its projection. What no record decides stands as built. A choice that later work will build on starts with its record. A disagreement is read first as the projection falling short. A record holds the choice and its reasons, and the projection holds the detail.**

### 1. Where an accepted record decides, the rest of the system is its projection

In this record, an accepted record includes an accepted rule whose origin states its choice in the decider's words, as [COR-051](COR-051-rule-sets.md) point 5 allows. What an accepted record decides governs the parts of the system it covers. The code, documents, skills, agents, schemas and other content that carry such a decision out are, for that decision, its **projection**: much of it made by hand, so it can lag the record, unlike the realized harness state that [COR-028](COR-028-permission-model-realization.md) has its realizer generate from its model.

This overturns COR-006's sentence "The five shapes are content peers; none is built on top of another": where a record decides, the other shapes carry its decision out, and the record governs when they disagree. The rest of COR-006 stands. Each shape keeps the kind of content COR-006 gives it, and content still lives in one place, so an artefact that states a record's decision cites the record and does not restate its reasons. A scratchpad note stays outside the projection. It explores a question before a record exists, and retires once its content becomes a record or another part of the project, or is abandoned ([COR-012](COR-012-scratchpad-notes.md)).

### 2. What no record decides stands as built

A choice the system holds that no accepted record decides stands as it was built. No one owes a record for it until a change makes or alters that choice under point 3. Until then it stands in whatever carries it today.

### 3. A choice that later work will build on starts with its record

A change that makes a choice other work will build on, beyond the change itself, starts with a record that decides it. Examples are a library, an interface or format others use, a convention, and a boundary between parts. So does a change that alters what an accepted record decides. The record is accepted, by a person (COR-064 point 6), before work rests on it, as the decision-record specification already asks. An accepted rule whose origin states the choice, as point 1 counts it, serves as that record.

A choice that binds nothing beyond its own change, such as a name or an order inside one change, needs no record. Nor does a change that only carries out an accepted record, or mends the projection where it falls short of one. The change's author judges first whether a change makes such a choice, before the work begins. The reviewers of the change and the person who authorises its merge judge it again, and the person decides where they disagree. A project changes only its own records: where a record it receives from elsewhere decides, the project either changes its projection or proposes the change where that record is kept.

### 4. A disagreement is read first as the projection falling short

Where the system and an accepted record disagree, the first question is whether the system falls short of the record. If it does, the system is changed, or the shortfall is tracked as open work and, where an artefact states the decision, made visible there as point 6 says. The record changes only through a change under point 3. Rewording a record so that it decides what was built is such a change. Correcting a fact or a citation where the record's decision stands is not, as the specification's rule on refining an accepted record says.

### 5. A record holds the choice, and the projection holds the detail

A record keeps the choice, its reasons, the alternatives it weighed and what follows from it. A name or a shape stays in the record where it is itself what the record decides, the case in which [COR-046](COR-046-records-name-roles.md) point 1 keeps a name rather than a role. The detail that only carries the choice out, such as the modules, functions and files that implement it, belongs in the projection, a document above all. A document that states a shape the record decides cites the record rather than restating it.

A record need not anchor what carries it out. The artefacts that state its decision anchor the record instead (point 6), and may anchor what they rest on (COR-050), so the record stays free of paths. A revalidation of a record that would change what it decides is a change under point 3, which a person accepts.

### 6. An artefact that states a record's decision anchors it, and shows where the projection lags

An artefact other than a record, held in a declared place ([COR-050](COR-050-anchors-and-friction.md) point 1), that states what an accepted record decides anchors that record, so a change to the record reaches it. Where such an artefact states something an accepted record decides that the system does not yet carry out, it says so to its readers, in its own text, naming the record and what tracks the work. The change that carries the work out removes that line. A record's text says nothing of how far the system carries it out. A project that keeps no such artefact owes none of this.

### 7. Records are read to change the system, not loaded to run it

Work that makes a choice under point 3, or carries out or mends an accepted record, reads first the accepted records that decide the parts it changes. A session doing ordinary work is not given the records wholesale. The skills and agents it uses read or cite the records they rest on (COR-006), and so does each operational rule that a record decides, as this record asks.

## Rationale

**Why a lasting choice starts with its record.** A choice reviewed and accepted before work rests on it is cheaper to change than one found in built code. An agent starting a session knows none of a project's reasons, and the accepted records are where it can read them before it changes anything. A lasting choice made in the code first, with the record written afterwards, turns the records into a log of what happened, and the reasons stop being an argument anyone can follow.

**Why the test is whether later work builds on the choice.** Every change makes choices, and a record for each would make the records an inventory. A choice that other work builds on costs the most to undo, and is the one the specification already describes as what a record holds: a rule chosen among viable alternatives. The test also matches how a reviewer reads a change: what will others now rely on?

**Why what is built stands where no record decides.** A project adopts the methodology with choices already made, and COR-025 already requires no backfill of its earlier architectural decisions. Holding every built choice to a record would stop such a project, or turn its first months into writing history. Each choice comes under a record the first time a change makes or alters it.

**Why the projection is checked first.** Reading each disagreement as the record being wrong would rewrite the decisions to match whatever was built, one edit at a time, and nobody would decide it. Checking the projection first keeps every change to what is decided a decision a person accepts, as COR-064 point 6 asks.

**Why a record keeps only the choice.** Detail that only carries a choice out changes as often as the code, so a record holding it changes at the code's pace, grows long and drifts from what it describes. A name or shape that is itself the choice stays in the record and under its acceptance.

**Why the lag is said in the artefact's own text.** An accepted record not yet carried out looks, to a reader of an artefact stating it, like a record that holds. The answers that say an artefact is still true live in answer files ([COR-062](COR-062-answers-in-own-files.md)), which that reader does not meet. A line in the artefact, naming the record and the work, lets the reader and a reviewer tell what stands from what is still owed.

**Why records are not loaded to run the system.** Most of what records hold is reasons, which running the system does not need, and a project's records can outgrow a session. The rules, skills and agents carry what work needs, and read or cite the records where someone needs the reasons.

### Alternatives considered

- **Every change to what the system decides starts with a record, in every project.** Rejected for the core: it fails a project with choices no record states, as "Why what is built stands where no record decides" says. A project may adopt it for itself.
- **The core covers only what accepted records already decide, and leaves new choices to each project.** Rejected: "decide first" would then bind no project that does not opt in, and the choices that cost most to undo would be made in code by default.
- **The code is the source, and records explain it afterwards.** Rejected: records become a history, and a choice can change with any edit to the code, decided by no one.
- **Refine COR-006, COR-046 and COR-050 in place, with no record of its own.** Rejected: the order of change and the reading of a disagreement are one principle that each of them touches only in part. A record of its own gives it one place to cite.

## Implications

- **COR-006** gains a first line saying it is partially superseded by this record, for its sentence that the shapes are content peers. That sentence stays as it stood, as the specification says of a point another record overturns. The line lands with this record's acceptance.
- **The decision-record specification** opens with the order this record decides.
- **A component whose artefacts state what records decide**, such as an analysis of what the software must do or a documentation space kept true, says in a record of its own how its artefacts carry records out and show their lag, within points 5 and 6.
- **The core operational rules** gain one that has an agent changing the system read first the records that decide what it changes, carrying point 7, and citing this record.
- **Records that hold detail** that only carries their choice out are brought to point 5 in the passage a revision touches, with nothing rewritten backwards.
- **No command changes.** The acceptance gate, anchors and the change check already serve this record.
