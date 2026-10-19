---
id: DEC-004
title: An analysis explains its concepts in a few hand-written domain-model views
status: proposed
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The glossary defines each concept of an analysis's domain, one term at a time. Each definition gives its broader kind and what sets it apart ([software-analysis:DEC-001-software-analysis-discipline] point 1). A reader cannot see there how the concepts fit together. Which belongs to which, what each holds, and how one moves through its states stay hidden.

- **The build order** puts the concepts first, before the actors, the requirements and the use cases (DEC-001 point 12). Its first step has no artefact that shows how they relate.
- **A new kind of artefact** needs a decision of its own (DEC-001 point 11).
- **Diagrams are decided.** A diagram written in an artefact shows only what that artefact, or an analysis artefact it anchors, states. No diagram is a fact's home ([software-analysis:DEC-003-analysis-diagrams] points 1 and 2).
- **No query draws the concepts,** since a term holds no relation to another term as data. Whether an analysis keeps views of them drawn by hand is left to a decision of its own (DEC-003 point 6).

The capability's maintainer decided the domain model's shape on 19 October, with the order an analysis is built in. The design note on analysis concepts and order lays it out, and its answered questions settle where it meets accepted records ([project-kit#1808](https://github.com/aleskalfas/project-kit/pull/1808)). This record holds the kind of artefact that note designs.

## Decision

**An analysis may keep a domain model: a few views beside the glossary, written by hand, one for each group of related concepts. A view explains each concept of its group in words and draws how they relate. It anchors the terms it explains and the records it rests on. The glossary stays as it is, and each term a view explains links to its section.**

In this record, a *view* is a domain-model view. A view of the solution, such as an architecture view, is always named in full.

### 1. What a domain model is

A domain model explains the concepts of the analysis's domain and how they relate. It describes the domain, never the software.
- **The methods it takes:**
  - **The Unified Process's domain model** (Larman, *Applying UML and Patterns*): concepts with their associations and attributes, and no operations, drawn as a class diagram.
  - **ICONIX's order:** the domain model comes first, with the glossary, before the use cases.
  - **ISO 704 and ISO 1087:** a concept is distinct from the term that names it. Concepts relate in three ways: generic, partitive and associative.
  - **State models,** as in Shlaer–Mellor and UML's state machines: a concept's life cycle, as states and the events that move it.
- **A few views.** The domain model is a folder of views, one for each group of related concepts. Which concepts form a group is the writer's choice, such as those of ordering, or of payment.
- **Optional.** An analysis keeps a domain model only where its project chooses. A term no view explains stays as it is.
- **Not Domain-Driven Design's domain model,** which designs the solution. The analysis keeps the solution out (DEC-001 point 11).

### 2. What a view holds

A view opens with what its group covers and the group's class diagram. Then it gives one section to each concept it explains.
- **What it explains,** as data: its front matter's `explains` lists, by their ids, the terms whose concepts it explains, in the order of its sections. It lists one term at least. A tool reads that list, never the sections (DEC-001 point 1).
- **Its heading:** its id and its title, such as `# VIEW-orders-and-payments — Orders and payments`.
- **Its opening:** what the group covers, then the group's class diagram. The diagram shows the concepts, what relates to what, and attributes where they matter.
- **A section for each concept,** headed by its term's name at the second level, such as `## order`. Every heading at that level is such a section. A section holds, in order:
  - an explanation of the concept for a newcomer, in plain words
  - its attributes, shipped as *Attributes*: what each instance of the concept holds
  - its relations, shipped as *Relations*: how it relates to other concepts, such as those of its group or of a lower view (point 6)
  - its life cycle, shipped as *States*: its states and the events that move it, as free text
  - what is always true of it, shipped as *Always true*: what holds of every instance, as the records decide it (point 3)

  A label with nothing to say reads `None.`, as in every kind (DEC-001 point 1).
- **One declared structure.** The kind declares its structure as data, as every kind does (DEC-001 point 1). It is the first document kind with a section that repeats, once for each concept. So the schema of the structures gains a repeating section.
- **The headings match the list.** Each section's heading is the name of the term `explains` lists in its place. This is a form of the repeating section, so it binds where the format rule binds, and at its status (DEC-001 point 1).
- **One slug for each section.** The structure refuses two sections of one view whose headings give one slug. A page anchor on either would be ambiguous (COR-050 point 7).
- **What a project adds.** A project may add labels to the opening, or to each concept's section, never a heading (DEC-001 point 1).
- **Its diagrams** are Mermaid fences written by hand, each with its `accTitle` and its `accDescr`, and with no styling (DEC-003 points 2 and 10).
  - **Where they sit:** the class diagram in the opening, and a concept's state diagram in its *States*, after the text (DEC-003 point 2).
  - **Another view's concept** is drawn by its name alone, as is a term no view explains. The view neither states nor anchors their facts, so its diagram shows none of them (DEC-003 point 2).
  - **Asked by the hints.** The opening's hint asks for the class diagram, and the hint of *States* for a state diagram where the concept has a life cycle. A hint binds nothing (DEC-001 point 1), so no check asks for a diagram.
  - **No part of their own.** The kind ships no part for diagrams, since DEC-003 point 2 decides that no kind does. So the diagrams sit in the opening and in *States*, not after the opening as a part of their own.

### 3. What a view states, and where each fact has its home

Each section states its concept's attributes, relations and states in words. A view's diagrams show only what its sections state.
- **A diagram is never a fact's home** (DEC-003 point 1). The class diagram restates the relations and the attributes the sections state. A state diagram restates its concept's *States*.
- **What is always true** of a concept is what its records decide, such as that an issued invoice is never changed. The section states it, and the view anchors the record that decides it (point 5).
- **An obligation stays a requirement.** What the system must keep, such as a business rule across use cases, is a functional requirement ([software-analysis:DEC-002-analysis-requirements] point 1). The requirement names the concept by its term.
- **The definition defines.** A term's `definition` defines its concept, as ISO 1087 has it, and is the home of its broader kind. The term's section explains that concept, restating the broader kind where it helps. What the section states fits exactly what the definition fits, never more and never less.

### 4. Its place, its type and its id

- **Its place:** a folder `domain-model/` in each analysis, beside the glossary (DEC-001 point 2). The capability declares it as a place that holds anchored artefacts.
- **Its type:** `domain-model-view`, named in a scope as `software-analysis:domain-model-view` (COR-056). As for every kind, no type names a kind field, and the place admits no project place (DEC-001 point 2).
- **Its file's name** opens with a number and a hyphen, such as `010-orders-and-payments.md`. The number gives the view's place in the domain model's order (point 6).
  - **Its form is the project's,** such as its width and its steps, as for an area's number (DEC-001 point 2).
  - **Numbers are compared as numbers.** A view's number is the digits its file's name opens with. Two views may share one, and then neither builds on the other.
- **Its id** is `VIEW-` and its file's name without its number, the hyphen after it and `.md`, such as `VIEW-orders-and-payments`. A view given another number keeps its id.
- **As every kind's id,** it is unique across the repository's analyses, and never reused (DEC-001 point 3). A view is withdrawn, never deleted, so its status is `active` or `withdrawn`.

### 5. What it anchors

A view anchors each term it explains and each record it rests on. Nothing in the analysis anchors a view.
- **Its terms,** by artefact anchors: exactly the terms its `explains` lists. The stamp writes them from the list. The capability's check holds them equal to the list, whatever any rule's status, as it holds a journey's anchors to its steps (DEC-001 point 4).
- **Why its terms.** Using a term asks for no anchor on it (DEC-001, Rationale). A view explains what a term defines, so a changed definition asks whether its section still holds.
- **Its records,** by record anchors: each record its statements cite or apply. Each fact it states as always true rests on the record that decides it.
- **No code.** A view describes the domain, never the software. The stamp writes no path anchor on a view, and the check refuses one.
- **What it explains:**
  - **terms of its own analysis alone.** A term that the head of its glossary lists from another analysis is explained there (DEC-001 point 2).
  - **terms in force alone,** while the view is in force. So the change that withdraws a term takes its section out of the view in force that explains it.
  - **each term once.** No two views in force explain one term, so each explanation has one home (COR-006). The capability's check holds it, whatever any rule's status.
- **A withdrawn view** keeps its `explains` and its anchors, as any withdrawn artefact keeps its own (DEC-001 point 3). It explains nothing: no term links to it, and it counts for no term's one view.
- **No cycle.** A term's link to its section is no anchor (point 7), so a view's anchors on its terms close no cycle.
- **No actor.** A view names no actor, since the actors come after it (point 8). A role the domain holds, such as a customer, is a concept with a term of its own. The term tells it apart from the actor that plays such a role in the system.
- **The cost of whole terms.** A term is anchored whole, as a collection entry is (COR-050 point 2). So a reworded example flags the view that explains the term, and costs a short answer.
- **The cost of no code.** A change of code reaches a view only through a term whose revalidation changes it. A change that adds a state, or drops an attribute, while the term's definition still holds, flags no view. So whoever revalidates a term reads the section that explains it too.

### 6. The order inside the domain model

The views of an analysis are written in the order of their numbers, and each uses only the views before it.
- **A view uses only lower views.** Its sections and its diagrams may name a concept that a lower view of its analysis explains, to state a relation. They name no concept that a view of its analysis explains with an equal or a higher number.
- **A relation between two views' concepts** is stated in the higher view, in its sections and its diagrams.
- **The glossary comes first.** A view may name any term in force that no view of its analysis explains, since the glossary comes before the views (point 8). A term the head of its glossary lists from another analysis is used as that analysis defines it, whatever explains it there.
- **What a number means:** one valid order of the views, never their importance, as for an area's number (DEC-001 point 2). The number is no part of the id (point 4).
- **A new section.** A section added to a view, or moved into it, can put a lower view that already names its concept out of order. So the change that adds or moves the section owns that break, and mends it.
- **What holds it.** A judgement rule of `SAN` holds the order, with this record as its origin. A view's uses of other views lie in its prose and its diagrams, which draw no anchor, so no check sees them.

### 7. The glossary, and each term's link to its section

The glossary stays as it is: one collection of terms, each defined in ISO 1087's form (DEC-001 point 1). A term a view explains links to that view's section on it.
- **Where:** an unlabelled line under the term's heading in the glossary, before its first part, where a reader reads the term. The link names the view's file and the section, such as `domain-model/010-orders-and-payments.md#order`. The section's name is its heading's slug, as COR-050 point 2 makes it.
- **Written and held.** The stamp writes the link from the view's `explains`, its file's name and the term's name. The capability's check holds it equal to the view in force that explains the term, whatever any rule's status. A term no view explains carries no link.
- **No part.** The term kind ships no part for the link, so no live term needs a migration (DEC-001 point 1). The structure check reads the line as no part, and a project's closed list of labels does not refuse it. A project without a domain model sees no change to its glossary.
- **A named exception.** The link is the reverse of the view's anchor on the term. No accepted point stores the reverse of an anchor (DEC-001 point 11, DEC-002 point 7). This link stores one, as a named exception: a copy for navigation, which the check holds equal, so it never drifts.
- **What it meets.** A copy in another artefact's body changes with every edit elsewhere, and flags that artefact's dependants (DEC-003 point 9). That is this link's cost, which this record accepts.
- **No anchor.** The link draws no anchor, so the term rests on nothing the view states.
- **The cost.** The link is part of the term's content. So a change to it flags whatever anchors the term, the view that explains it among them. Each of these changes a link:
  - a view's number, or the name of its file
  - a section added to a view, moved between views or taken out
  - a view withdrawn

  A view renumbered or renamed is a moved file, which is revalidated in that change anyway (COR-050 point 3).
- **A heading that drifts.** Where the format rule does not bind on a view, its headings are not held to its `explains`. A heading can then drift from its term's name, and the term's link leads nowhere in the view.

### 8. Its place in the build order

The views come in the build order's first step: after the glossary, and before the actors (DEC-001 point 12).
- **Step 1:** the glossary, then the views in the order of their numbers, then the actors with their needs.
- **After the glossary,** since a view explains the concepts the glossary defines, under their terms' names.
- **Before the actors,** since every later artefact uses the concepts. Showing how they relate finds the concepts the definitions missed, while the glossary is still being written.
- **Going back.** A view that needs a concept the glossary lacks goes back and defines it first, as DEC-001 point 12 asks of every artefact.

### 9. In living docs

A documentation page that is no architecture view may rest on a view's section (DEC-001 point 11).
- **A page that states a concept's facts** may anchor that concept's section of its view.
- **By the view's id,** such as `VIEW-orders-and-payments#order` (COR-050 point 2). An anchor on the file's path would die when the view is renumbered.
- **The home of the facts only the section states.** A section of an analysis artefact is one of the homes beyond the pages ([living-docs:DEC-002-visual-elements] point 3). Until a major of `LDOC` accepts the rule that states it, a fact's home stays among the pages and the records (living-docs DEC-002 point 10).
- **A renamed term** renames its section's heading, and a moved section takes its heading to another view. Each page anchor on that section is then dead, and validation fails until the same change mends it (COR-050 point 7). Such a change is rare, and the failure is loud.
- **living-docs needs nothing from this record.** Without an analysis, a page's facts keep their homes among records and pages ([living-docs:DEC-001-living-docs-discipline] points 3 and 9).

## Rationale

**Why views beside the glossary.** A definition says what one concept is. It cannot show how several fit together, nor how one moves through its states. A diagram with words beside it shows both. A newcomer reads it before the use cases that act on those concepts.

**Why hand-written views, not generated ones.** A term holds no relation to another as data, so nothing could draw one. Making relations and states data would add fields to every concept, more structure than the domain needs. Generated views per concept can come later, if hand-written ones prove a burden (COR-007).

**Why one view for each group.** One file for the whole domain model would be long to read, and would conflict on every branch that touched it. A file for each concept would scatter the relations its group shares. A group is what a reader takes in at once.

**Why the glossary stays.** A term's definition already defines its concept, in the form terminology standards give (ISO 1087). Moving the definitions into the views would withdraw the term kind, which every artefact relies on. Kept apart, the glossary defines and a view explains.

**Why a list of the terms it explains.** A tool reads front matter only (DEC-001 point 1). The stamp writes a view's anchors and each term's link, so it reads them from `explains`, as it writes a journey's anchors from its `steps`. The sections' headings are held to the list by a form of the structure, as a journey's step lines are held to its `steps`.

**Why the headings bind with the format rule.** The headings are part of the view kind's declared structure, which is the format rule's checkable part (DEC-001 point 1). Checking them always would enforce part of one rule two ways, which DEC-001 rejects for the glossary's head (COR-051). The anchors, the link and the one view for each term lie outside any structure, so the check holds them always.

**Why the always-true facts come from records.** A view explains the domain as the project decided it. What is always true of a concept is a decision, so its home is the record that decides it. An obligation the system must keep is a requirement's, which is checkable and may carry a measure (DEC-002 point 1).

**What that costs.** A project whose invariants no record decides writes `None.` under *Always true*. Its business rules live as functional requirements, which come after the views in the build order. So a view never states them, and a reader finds them where the requirements name the concept.

**Why a number, and its form the project's.** The order of the views is part of the kind (point 6), so each view carries a number. A file listing shows the order only where the names carry it. How the number is written is a project's style, as it is for an area's folder (DEC-001 point 2). The number is no part of the id, so a view moved in the order keeps every citation true.

**Why a view uses only lower views.** A higher view builds on the concepts of the lower ones, as an area builds on the areas before it (DEC-001 point 12). A relation stated once, in the higher view, has one home among the views. Read in order, each view relies only on what the reader has already met.

**Why a view anchors the terms it explains, and only those.** Explaining a concept builds on its definition, so a changed definition should ask whether the explanation still holds. Using a term asks for no anchor anywhere in the analysis (DEC-001, Rationale). A view that anchored every term it names would be flagged by each edit to any of them.

**Why a view anchors no code.** The domain model describes the domain, never the software. Code that embodies a concept is anchored by its term (DEC-001 point 4). The cost is a code change the term's definition survives, which reaches no view (point 5). Whoever revalidates the term reads its section, so the view is read where the code changed.

**Why the term's link is an exception.** A reader looks for the explanation where the term is read, in the glossary.
- **Computed elsewhere,** such as in a generated overview, it would not show where the term is read.
- **A stored reverse is refused elsewhere** because it drifts unseen (DEC-002 point 7). This one cannot drift, since the check holds it equal to the view.
- **It points no solution back at the analysis,** which is DEC-001 point 11's other reason. Both ends lie in the analysis, and the link is no anchor.
- **Its cost** is the flags its changes raise on the terms' dependants (point 7).

**What the views cost in words.** A view's attributes, states and events are often concepts of the domain, so each needs a term before a view uses it (DEC-001 point 12). Writing views grows the glossary. That is the build order working, since a concept found while drawing it gets its one name there.

**Why a page may rest on a view's section.** A page that explains a concept would otherwise state its facts again, in a second home. Anchoring the section keeps one home, and a change to the section flags the page.

### Alternatives considered

- **One file for each concept, with its relations and states as data, and views generated from them.** Rejected. It is more structure than the domain needs. Generated views come later only if hand-written ones prove a burden (COR-007).
- **A definition tied to a field for its broader concept.** Rejected. It needs the fields above.
- **One domain-model file, a collection like the glossary.** Rejected. Dozens of sections are long to read, and the file conflicts on every branch. A collection entry also takes no anchor on a section, so no page could rest on one concept (COR-050 point 2).
- **One entry for each concept holding its names, as ISO 704 and TBX keep them, with the glossary generated.** Rejected. It withdraws the term kind, which every artefact relies on.
- **Domain-Driven Design's domain model.** Rejected. It designs the solution, which the analysis keeps out (DEC-001 point 11).
- **Views without numbers, their order computed.** Rejected. A file listing would never show the order.
- **A form of the number fixed by the capability, such as three digits in steps of 10.** Rejected. The order needs only a number, and its form is a project's style, as for its areas.
- **A view's id without a prefix.** Rejected. Every kind's id takes one (DEC-001 point 3), so no two kinds share an id.
- **A prefix of the domain model's own, such as `DMV-`.** Not taken. `VIEW-` was settled with the ids across analyses ([project-kit#1808](https://github.com/aleskalfas/project-kit/pull/1808)), and a reader knows the word. Its cost: a project whose own artefacts take `VIEW-` ids must keep their slugs apart from its views'.
- **The terms a view explains read from its headings.** Rejected. The stamp would read a body, which DEC-001 point 1 keeps from every tool but the check.
- **A shipped part for the diagrams, after the opening.** Rejected. DEC-003 point 2 decides that no kind ships a part for diagrams. The opening and *States* hold them as free text instead.
- **A check that asks each view for a class diagram.** Not taken. A view of one concept may have nothing to draw, and the hints ask for it.
- **The term's link computed where the glossary is shown, such as in the overview, and stored nowhere.** Rejected. A reader reads the glossary on a repository host, where no computed link shows.
- **A shipped part for the link in each term.** Rejected. Every live term would need a migration, and a term no view explains would read `None.`.
- **A view anchoring every term it uses.** Rejected. Each edit to any term it names would flag it, an anchor broader than what makes the view true (COR-050 point 7).
- **A view anchoring the code behind its attributes and states.** Rejected. A view describes the domain, and the term anchors the code that embodies it.
- **Two views explaining one concept, each from its group's side.** Rejected. Two explanations of one concept drift apart (COR-006).
- **A check that a view uses only lower views.** Not taken. A view's uses lie in its prose and its diagrams. Whether a word names a concept is a reader's judgement, as the rule on domain concepts says.
- **The order held inside the rule on domain concepts.** Rejected. A finding on the order would cite a rule whose statement says nothing of it.

## Implications

- **The capability ships** the view kind in a build of its own. It brings its place and type, its declared structure with a repeating section, and its template. It also brings its companion schema, its stamp and its check.
  - **The check holds, whatever any rule's status:**
    - a view's term anchors to its `explains`
    - no path anchor on a view
    - each term explained by one view in force at most
    - each term's link to its section
  - **The structure holds** a view's headings to the names of the terms its `explains` lists, where the format rule binds. Each heading gives a slug of its own (point 2).
  - **The structures' schema** refuses an added heading in a view, and gains the repeating section with no new `schema_version`.
  - **A section added by hand** is added to `explains` too. How the anchor and the link are then written is the build's to settle, and the README says how.
- **`SAN`'s judgement rules read views,** proposed with its other rules, so `SAN` keeps its version (COR-051 point 4):
  - The rule on anchors lists what a view anchors (point 5). It leaves the term anchors to the check.
  - The rule on domain concepts reads a view's sections and its diagrams as statements. It judges a section against its term's definition (point 3).
  - A new rule holds the order of point 6, with this record as its origin.
- **DEC-001** points 1, 2, 3, 4 and 12 name what this record adds to them.
- **A project's own set** must select the new type for `SAN` to bind on views. The set that installing creates selects it once the kind is built. A set created before is the project's, so the release that adds the kind tells the project to add the type.
- **A clash of types.** A project's own bare type named `domain-model-view` clashes with the capability's. Validation refuses the clash (COR-056 point 2), and the release that adds the kind says so.
- **Revalidation** applies to views as to every kind: its four outcomes, its records and its agent (DEC-001 points 5 and 6). The agent becomes the fixer of the new type too (DEC-001 point 8).
- **Revalidating a term** reads the section that explains it, in the authoring skill and in the agent (point 5).
- **The authoring skill** walks the views in the build order's first step, after the glossary.
- **Projects** that keep a domain model write its views after the glossary, one for each group of related concepts. They number the views in the order they build on each other.
