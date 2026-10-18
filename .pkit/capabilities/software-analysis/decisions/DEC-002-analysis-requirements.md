---
id: DEC-002
title: The analysis keeps quality requirements, functional requirements and constraints
status: accepted
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A use case holds one actor's goal and how the system fulfils it. Some of what a system must do binds many use cases at once, and no single use case is its home:
- how well the system behaves, such as how fast, how reliably or how safely
- behaviour that holds across use cases, such as a business rule
- limits on the solution, which the design takes as given

The capability keeps actors, use cases, journeys and glossary terms ([software-analysis:DEC-001-software-analysis-discipline]). Its point 11 leaves further kinds of analysis artefact to a decision of their own, once a real need arrives. Decision records often state such requirements, with no home in the analysis.

Established practice keeps them beside the use cases. RUP's supplementary specification holds them beside the use-case model. arc42 gives quality requirements and constraints sections of their own. ISO/IEC/IEEE 29148 names them as kinds of requirement.

This record is the decision DEC-001 point 11 asks for. DEC-001 gives the shape every kind follows. That is a declared structure (point 1), a place and a type (point 2), ids (point 3) and anchors (point 4). Its point 11 says how the analysis meets the solution, and where a statement belongs. This record decides for its three kinds what DEC-001 points 2 and 4 decide for theirs, and only what the new kinds add.

## Decision

**The analysis keeps three more kinds of artefact: quality requirements, functional requirements and constraints. They share one numbering, live in a folder for each kind, and are listed by the use cases and journeys that must meet them.**

### 1. Three kinds

- **A quality requirement** says how well the system must behave, such as how fast, how reliably or how safely.
- **A functional requirement** is behaviour that holds across use cases, such as a business rule of the project's domain.
- **A constraint** limits the solution. The design takes it as given.

Behaviour that serves one actor's goal is a use case, not a functional requirement.

- **Each is a kind in DEC-001's sense.** It declares its structure, and has a place and a type, a companion schema, a template, its stamp and its check.
- **No catch-all.** Every requirement is of one of the three kinds. A further kind of requirement is a refinement of this record, with its own folder, parts and check. A further kind of analysis artefact that is no requirement takes a record of its own (DEC-001 point 11).

### 2. One numbering, and the kind beside the id

Requirements are numbered within the project as `REQ-NNN`, one numbering across the three kinds.
- **Reclassifying keeps the id.** A requirement moved to another kind is rewritten to that kind's structure, and keeps its number.
- **The kind shows beside the id** in the path, in the heading, in tool output and on pages. The heading shows the id, the kind and the title, such as `# REQ-007 · Quality · <title>`.
- **DEC-001 point 3's rules for numbered ids** apply to `REQ-NNN`. Its next free number and its check of parallel work read the three kinds' folders as one.

### 3. Places and types

Each kind has a folder of its own, and the three sit in one folder of the analysis that holds the requirements. The README gives the layout once the kinds are built.
- **A place for each kind.** Each kind's folder is a place, which gives its artefacts the kind's type: `quality-requirement`, `functional-requirement` or `constraint`. A scope names them in full, as `software-analysis:constraint`.
- **As for DEC-001's kinds,** no type names a kind field, and no place admits a project place (DEC-001 point 2).
- **The folder that holds the three is no place.** A requirement lies in the folder of its kind.
- **Areas.** A kind's folder may group its requirements in folders by functional area, as the use cases may be. Moving a requirement between areas never changes its id.

### 4. Their parts: the fields a tool reads, and the parts a reader reads

The obligation itself, and its measure, are front-matter fields, which a tool reads. The rest serves readers and the check (DEC-001 point 1). Every kind has the same fields and the same parts, save one part, which differs for a constraint. Each kind's structure gives the parts their labels.
- **Front-matter fields,** beside its id, title and status:
  - `statement`: the requirement or the constraint, in one sentence.
  - `measure`: the value or the condition that shows it is met. It reads `None.` where there is none.
  - `actors`: the actors whose need it meets, if any.
  - `refines`: the requirements of any kind it refines, if any.
- **Body parts:**
  - **Where it holds,** shipped as *Applies to*. It says so in words, such as a class of commands or the whole system, and never reads `None.`. It names no use case or journey: those that must meet the requirement list it (point 7).
  - **What verifies it today,** shipped as *Verified by* (point 5). It may read `None.`.
  - **Why it is needed,** shipped as *Rationale*, on a quality or a functional requirement. On a constraint, **who or what imposes it** instead, and why the design cannot choose otherwise, shipped as *Imposed by*. Each may read `None.`.
- **What triggers the core's signal.** The core may give a signal from a link's source to its targets ([project-kit#1667](https://github.com/aleskalfas/project-kit/issues/1667)). Where the capability declares it for these kinds, a change to the statement or the measure triggers it. This record decides which of the capability's fields trigger the signal, and nothing of its shape.
- **What the declaration leaves out:**
  - a change to a body part, such as the wording of the reason. It still flags each use case and journey that lists the requirement (point 7).
  - a change to where it holds, though moving where a requirement holds can change what it asks.
  - a change of kind, or a withdrawal, which leaves both fields as they were.

  Whoever makes such a change revisits what the requirement anchors.
- **A project may ask more** by a rule of its own, such as that every part is filled.
- **No classification field,** such as a quality characteristic of a standard.

### 5. What verifies it: tests named in words, and anchored by path

- **In words.** The part on what verifies the requirement names each test, check or review by what it does, never by its path.
- **As anchors.** The file of each test or check it names is a path anchor of the requirement.
- **What that gives.** A changed test flags the requirement, as any changed anchor does (COR-050). And where the core's signal reaches a requirement's anchors, its tests are among them.
- **`None.`** says nothing verifies the requirement yet. So a requirement nothing checks is seen.
- **What no check holds.** No check matches the tests that part names against the requirement's path anchors. A reviewer does.

### 6. Their anchors

A requirement points at the solution, and nothing in the solution points back at it (DEC-001 point 11).
- **The solution it anchors:**
  - each decision record it rests on or is answered by, whole or one of its points
  - each architecture view that realises it
  - the files that verify it (point 5), and the narrow code that holds it. An anchor on every command of the class it binds would be over-broad (COR-050 point 7).
- **Within the analysis,** it anchors only each actor in its `actors` and each requirement in its `refines`, as artefact anchors. The stamp writes them from the fields, and the check requires its anchors within the analysis to match the two fields exactly.
- **Refined in a circle.** A requirement that comes back round to itself through `refines` closes a cycle, which validation refuses (COR-050 point 5).
- **With no anchor.** A requirement with no anchor at all may give the reason it has none, as an actor or a term may (DEC-001 point 9). It then has no actor, no requirement it refines and nothing in the solution, such as a requirement a stakeholder states.

### 7. Use cases and journeys list the requirements they must meet

- **A use case** lists in `requirements` each requirement it must meet. The field is optional, so no use case needs changing.
- **A journey** lists only the requirements that bind its whole path. A requirement that binds one of its steps is that step's use case's to list.
- **As anchors.** Each requirement listed is an artefact anchor of the use case or the journey. The stamp writes it. The check requires the requirement anchors to match the list exactly, as a journey's use-case anchors match its steps. So a changed requirement flags each use case and journey that lists it.
- **In force.** The stamp and the check refuse a listed requirement the analysis does not hold. They refuse a withdrawn one listed by a use case or a journey in force, or refined by a requirement in force. So the change that withdraws a requirement also takes it off those lists, and the friction its withdrawal raises points at each of them.
- **What meets it is computed.** The use cases and journeys in force that list a requirement are shown with it, such as under "Met by", worked out from their lists. The requirement never stores them.

### 8. What approves a requirement, and the record it rests on

- **Approval.** Merging the change that adds a requirement approves it. A requirement no record backs needs no record to decide it first. The analysis is then its one home.
- **The accepted record wins.** A requirement that contradicts an accepted decision record it rests on breaks a judgement rule of `SAN`, beside its other judgement rules. The record wins until it is changed.
- **A conflict between requirements** is a choice, so a decision record holds it. No field relates two requirements that conflict.

### 9. Records keep their text

- **No rewrite.** Adopting these kinds changes no decision record. A record that restates a requirement's measure names the requirement instead when it is next changed, as DEC-001 point 11 asks.
- **A record that ships** keeps its text. It ships the same text to every project, so it never names one project's requirement.

## Rationale

**Why three kinds.** Practice keeps them apart, and so do their readers. A design trades quality requirements against each other and against cost. It takes a constraint as given. A business rule that holds across use cases is behaviour, and neither a quality nor a limit. RUP's supplementary specification holds such system-wide functional requirements beside the qualities. Their parts agree, so a requirement keeps its fields when it changes kind. Only a constraint says who imposes it, where a requirement gives why it is needed.

**Why behaviour for one goal stays a use case.** A use case already holds one actor's goal and its path. A functional requirement for one goal would state the same behaviour twice.

**Why no catch-all.** Each place gives one kind, and each structure is keyed by kind (DEC-001 points 1 and 2). A requirement of no kind would have no structure to check.

**Why one numbering.** The line between the kinds blurs. A property with a measure and a limit taken as given can describe one obligation, and a project's understanding of it moves. With a number per kind, moving a requirement would change its id, and everything that cites it. One numbering keeps the id, and showing the kind beside it keeps what a separate prefix would show.

**Why the statement and the measure are front-matter fields.** A tool reads data from an artefact's front matter only, and a body's parts serve readers and the check (DEC-001 point 1). Should the core give a signal, it is a tool's, so the parts that trigger it are fields. The statement is the obligation, and the measure is what a solution must reach. A new reason explains the same obligation.

**Why the declaration leaves the other changes out.** The fields that trigger are the two that state the obligation itself. Where a requirement holds is a body part, which no tool but the check reads. A change of kind or a withdrawal is rare, and is reviewed as a change of its own. So each leaves the revisiting to whoever makes it.

**Why a measure may read `None.`.** A requirement found before its measure is still worth keeping. `None.` says the measure was considered and is missing, so the gap is seen.

**Why tests are named in words and anchored by path.** An artefact's content is its body and its own fields, and a change to it flags every artefact anchored to it (COR-050 point 5). A test's path in the body, or in a field, would make a renamed test flag what lists the requirement. Anchors sit in the methodology's container, which is no content. So the path in an anchor flags the requirement when the test changes, and nothing beyond it. The words say what the test checks, which the path does not. The cost is twofold. No check matches the words to the anchors. And a file holding many tests flags the requirement on an edit of any of them.

**Why use cases list requirements, and not the reverse.** A changed requirement can make a use case false, so the use case anchors it. A requirement that listed the use cases it applies to would be flagged on each of their edits, and a cross-cutting one would list dozens. Listing follows a journey's steps, which already anchor upstream. The cost is that any change to a requirement's content flags every use case and journey that lists it (COR-050 point 5). A reworded reason flags them too, and a requirement that binds the whole system flags every use case that lists it.

**Why a journey lists only whole-path requirements.** The use case of a step lists what the step needs. Listed by the journey too, one change would flag both for one obligation.

**Why where it holds names no use case.** A use case named there would be a stored copy of what lists the requirement. It would go stale unflagged when the use case drops the requirement, since the requirement cannot anchor the use case without a cycle. What meets a requirement is computed from the lists, so it is never stale.

**Why `actors` and `refines`.** ISO/IEC/IEEE 29148 traces a requirement to its source, and an actor whose need it meets is one. arc42 refines a quality goal into narrower ones. Each is one relation, upstream of the requirement, so neither forms a cycle with the use cases that list it.

**Why no relation for a conflict.** A conflict between two requirements is resolved by a choice. A decision holds the choice and why it was made (DEC-001 point 11).

**Why merging approves a requirement.** The change that adds a requirement is reviewed like any other. A record written only to approve it would hold the same obligation twice, and one fact has one home (COR-006).

**Why the accepted record wins.** A requirement restates in checkable form an obligation a record created. Where the two disagree, the record is what was decided. The requirement changes, or the record is changed first.

**Why no classification field.** No tool reads one yet. A closed list in a companion schema binds every project, and would shut out one that classifies by another standard or another edition of one. A project that wants one adds it as a part of its own.

**Why records are not rewritten.** Moving every measure out of every record is a large change that decides nothing. Each record names its requirement when it is next changed, so the corpus moves at the pace of its edits.

### Alternatives considered

- **Two kinds, quality requirements and constraints.** Rejected. Behaviour that holds across use cases would have no home but a use case.
- **One kind with a field for its type.** Rejected. DEC-001's places give their type with no kind field (point 2). A folder for each kind also shows a reader the kind before the file is opened.
- **A prefix for each kind, such as `QR-` and `CNS-`.** Rejected. Reclassifying would change the id, and the boundary between the kinds blurs.
- **The kind only in the path.** Rejected. A reader of a heading, a finding or a page would not see it.
- **One collection file, as RUP's single document.** Rejected. Each entry carries a friction block and several parts, so the file grows long and cannot be grouped by area.
- **The statement and the measure as body parts.** Rejected. No tool but the check reads a body's parts.
- **Where it holds as a field a declaration of the signal names too.** Not taken. It says where the obligation holds, not what it is, and it stays a part a reader reads.
- **A change of kind or a withdrawal that a declaration of the signal names.** Not taken. Each is rare and reviewed as a change of its own, and neither changes the fields that state the obligation.
- **Where it holds, naming the use cases it binds.** Rejected. It would store a copy of what lists the requirement, which goes stale unflagged.
- **A test's path in the body, or in a field.** Rejected. A renamed test would flag every use case and journey that lists the requirement.
- **A kind of anchor for tests, which the capability registers (COR-050 point 2), so a test is told from code.** Not taken. It needs a resolver command for what a path anchor already resolves, and a testing component is likelier to own it.
- **No measure on a constraint.** Rejected. A limit can carry a condition that shows it is kept, and a requirement that changes kind would lose its field.
- **A measure that never reads `None.`.** Rejected. A requirement found before its measure would have no place.
- **A requirement that lists the use cases it applies to.** Rejected. Every edit of any of them would flag it.
- **A relation for requirements that conflict.** Rejected. A conflict is a choice, which a decision record holds.
- **A classification field now.** Rejected. Nothing reads it, and a closed list shuts out other standards.
- **Rewriting every record to name its requirements.** Rejected. It changes much and decides nothing.

## Implications

- **The capability ships** for each kind its structure, template, companion schema, place and type. It ships the stamp of each kind and `requirements` on use cases and journeys. It ships the check of the ids, fields and parts, and a query that lists what meets each requirement. The README gives the layout, and says that behaviour serving one actor's goal is a use case.
- **DEC-001 governs its four kinds, and this record the three it adds.**
- **`SAN`:**
  - its format rule covers the new kinds as it covers every kind.
  - the rule of point 8 joins it as a proposed judgement rule.
  - a judgement rule that lists what each kind anchors gains the new kinds, and the `requirements` of a use case and a journey.
- **A project's set** must select the new types for `SAN` to bind on them. The set that installing creates selects them. A set created before is the project's, so the release that adds the kinds tells the project to add them. Until a set selects them, the check counts the requirements no rule of `SAN` binds on (DEC-001 point 1).
- **A clash of types.** A project's own bare type that takes one of the three names clashes with the capability's, chiefly `constraint`. Validation refuses the clash (COR-056 point 2), and the release that adds the kinds says so.
- **Ids in records and evidence.** A revalidation record's outcomes and the evidence point's entries may name a requirement by its id. A requirement has no steps, as an actor has none. The addition leaves the evidence point's schema version as it is (COR-052 point 5).
- **Revalidation** applies to the new kinds as it does to every kind: its four outcomes, its records and its agent (DEC-001 points 5 and 6).
