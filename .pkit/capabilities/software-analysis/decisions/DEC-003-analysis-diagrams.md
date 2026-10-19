---
id: DEC-003
title: The capability draws an analysis's diagrams from its front matter, and no diagram is a fact's home
status: accepted
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

An analysis holds relations a reader grasps faster in a picture. A diagram drawn by hand from them drifts as soon as one relation changes. Examples of such relations:
- who takes part in which use case
- the path a journey takes
- what must meet each requirement
- which use case follows from which

[software-analysis:DEC-001-software-analysis-discipline] and [software-analysis:DEC-002-analysis-requirements] already decide what such a picture can rest on:
- **A tool reads front matter only.** A body's parts serve readers and the check, never another tool (DEC-001 point 1).
- **What meets a requirement is computed,** never stored on the requirement (DEC-002 point 7).
- **Views of the solution stay outside the analysis.** A context view names the analysis's actors by id, and states none of their facts (DEC-001 point 11).
- **A use case names what makes each precondition true,** optionally as data in `after` (DEC-001 point 1).

The capability's maintainer set three constraints on 18 October, on [project-kit#1770](https://github.com/aleskalfas/project-kit/issues/1770):
- **The direction:** software-analysis supports diagrams by default.
- **A diagram is a view of truth held elsewhere:** in decisions, requirements, use cases or code. It states nothing that has no other home, and it anchors what it shows. It is generated from that home where it can be.
- **Content and presentation stay apart:** content is neutral and carries no styling. A sensible default needs no setup, and reads right on GitHub.

A design note weighed the options against established practice. That practice includes UML's use-case diagram, the context diagram of requirements engineering, and diagram-as-code tools. The capability's maintainer took its recommendations on 19 October, on the same issue.
- **This record holds software-analysis's share of them.** A page's diagrams are the documentation component's to decide.
- **Its share includes the overview and the rules.** The note makes this capability's record the origin of its new rules, and the overview's held folder refines DEC-001 point 2.

## Decision

**The capability draws four diagrams from an analysis's front matter: a use-case diagram, a journey's flow, a requirement map and the chain of use cases. A query prints them on demand, and a generated overview shows them to readers. No diagram is a fact's home. A diagram written in an artefact shows only what that artefact, or an analysis artefact it anchors, states.**

### 1. A diagram is never a fact's home

Each fact the analysis holds has its home in the artefact that states it. A diagram shows only facts with such a home.
- **A relation's home** is the front-matter field that lists it, such as a use case's `actor` or a journey's `steps`.
- **Any other fact's home** is the part or the field that states it.
- **A diagram in any form is never a home,** written by hand or generated, as a fence, a source file or an image. A fact that only a diagram states has no home.
- **Why.** An arrow does not say which relation it shows, and a layout can change with no fact changing. So a diagram cannot hold a fact precisely enough to be where a change to it is made.

### 2. A diagram written in an artefact shows only what its anchors carry

An analysis artefact may hold a diagram in its body, written as a Mermaid fence.
- **What it shows:** only what its own artefact states, or what an analysis artefact it anchors states. A use case may draw its main path, which restates its steps. A journey may label its steps with their use cases' titles. Anything wider is drawn only by the capability (point 4), or not in the analysis.
- **Why that far.** A change elsewhere reaches an artefact only through its anchors. The analysis's anchors follow its lists, and a journey's use-case anchors match its steps and its `relies-on` (DEC-001 point 4 and DEC-002 point 7). So a change to what such a diagram shows flags the artefact that holds it.
- **Why an analysis artefact only.** A record or a view the artefact anchors belongs to the solution. Drawing its facts would bring the solution into the analysis (DEC-001 point 11).
- **Where it sits,** after a blank line, in one of two places:
  - in a part of free text, as part of the text it follows
  - indented under an item of a part whose form reads items, as part of that item

  A part that reads `None.` holds no fence.
- **No part of its own.** No kind ships a part for diagrams. A shipped part would read `None.` in most artefacts, and every live artefact would need a migration (DEC-001 point 1). A project that wants such a part adds one of its own.
- **No styling.** The fence holds nothing that sets a colour, a font, a theme or a class. Examples are Mermaid's `%%{init}%%` directive, a `config` block in a diagram's front matter, and `classDef`, `class`, `:::`, `style` and `linkStyle` lines. Presentation is each project's.
- **Its syntax is not validated.** A check would need a Mermaid parser installed, and its answer would then depend on the machine (COR-050 point 2). A project may run such a check in its own continuous integration.
- **Another language** is not taken yet in the analysis. Its diagram would be an image rendered from a separate source, which nothing keeps fresh with its artefact. It comes when a project needs one (COR-007).

### 3. The generated diagrams read front matter only

The capability's diagrams are drawn from the analysis's front matter, as every tool reads it (DEC-001 point 1).
- **What follows:** they draw relations, never a use case's main path or a journey's seams, which lie in the body.
- **The next step:** the capability's own queries are to read a body's parts by their permanent id, as its check already reads them. A diagram of a use case's path, or of a journey's seams, comes with it. The change that builds it refines DEC-001 point 1.

### 4. What it draws

The capability draws three diagrams from the relations of its actors, use cases, journeys and requirements. Each draws only the artefacts in force, as only use cases and journeys in force meet a requirement (DEC-002 point 7).
- **A use-case diagram:** the system's boundary, the use cases inside it, and the actors around it. A use case is joined to its `actor` and to each of its `other-actors`. It is UML's diagram of that name, without include or extend. An analysis with no use case in force has none.
- **A journey's flow:** its actor, then its `steps` in their order. The use cases of its `relies-on` stand in a group of their own, with no arrow. Which step relies on which of them lies in the body, so no arrow could say.
- **A requirement map:** each requirement, the use cases and journeys that list it in their `requirements`, the requirements it `refines`, and the actors whose need it meets.
- **A reference to no artefact in force,** such as a withdrawn actor, draws nothing, save a journey's step. The capability's check reports it. A step keeps its place in the order, drawn by its id alone.
- **Not a context view.** Every node of the use-case diagram is an artefact of the analysis, and every line is a relation its front matter holds. A context view shows the system as one whole among the people and systems around it, and is part of the solution (DEC-001 point 11).

### 5. The chain of use cases

A fourth diagram draws which use case follows from which, from each use case's `after` (DEC-001 point 1).
- **Its arrows:** one from each producer a use case names to that use case. A use case that names itself, as a release starts from the last release, draws an arrow to itself.
- **The environment** is one node, drawn where a use case names `environment` beside a producer.
- **Grouped by area:** each area's use cases are drawn together. The text lists the areas in the order of their numbers, and the renderer lays them out (DEC-001 point 2).
- **A producer in a later area** is drawn dotted, as an alternative its use case's area does not build on (DEC-001 point 12). It is in a later area only where both areas carry numbers, and the producer's area has the higher number. Every other producer is drawn solid, the environment included.
- **Implied arrows left out.** The use cases on one loop of solid arrows count as one node here. A solid arrow is left out where other solid arrows also lead from its producer's node to its use case's node, through a third node.
- **What is never left out,** so the arrows left out are always the same ones:
  - a dotted arrow, which implies no other arrow either
  - an arrow from a use case to itself
  - an arrow within a loop
- **What is not in force** draws nothing, as in point 4.
- **One reading.** `after` may hold loops, a use case that names itself, and alternatives. So the picture shows one reading of the chain, and does not tell a precondition's alternatives from several preconditions. The use cases are what the rule of logical consequence judges, never the picture.
- **When.** Its query comes with the build that adds `after` and its check. Until then no part of the capability reads `after`.

### 6. Each diagram is drawn for one analysis

A diagram draws one analysis's artefacts (DEC-001 point 2).
- **Its lines.** Every line drawn is a relation this analysis's front matter holds. A journey's steps and a precondition's producers stay within one analysis.
- **Another analysis's actor** is the one node a diagram draws from beyond its analysis's edge. It is point 4's other exception. An artefact of this analysis may name one, such as `core:ACT-developer`. Once the capability reads several analyses, the diagram draws that actor among the actors, by that id alone, so no diagram depends on another analysis's files.
- **Several analyses.** Once the capability reads them, the query names the analysis it draws.
- **The glossary's concepts.** No query draws them, since a term holds no relation to another term as data. Whether an analysis keeps views of its concepts drawn by hand is a decision of its own.

### 7. A query prints them, each with its text alternative

A query prints each diagram as Mermaid text, computed from the analysis in the working tree each time. It writes nothing.
- **Its text alternative:** each diagram carries an `accTitle` that names it and an `accDescr` that says in words what it shows. Both travel with the diagram into every renderer.
- **Neutral:** no styling (point 2). A shape tells kinds apart, such as a use case's oval, and an arrow's form tells relations apart. Neither is styling.
- **The same bytes:** the same analysis prints the same text, its nodes sorted and its node ids stable.
- **Complete, or no answer.** The query prints no diagram where a file of a place it reads cannot be read as its kind. A smaller diagram would read as a true one.
- **Its own Mermaid writer,** beside the backbone's graph of the process wiring. The two overlap only in making node ids and labels safe, which each does its own way. What each draws differs, and only this one carries a text alternative. A third component that prints Mermaid is the trigger to weigh a shared writer (COR-007).

### 8. A generated overview shows them by default

Each analysis keeps a generated overview of its diagrams, so a reader on a repository host, such as GitHub, sees them with no setup.
- **What it is:** a held document, in a folder of held documents of its own in the analysis (COR-050 point 1). A held folder never equals or encloses a documentation root or another declaration's place.
- **How it starts:** install writes it. A migration writes it for a project that installed the capability before (COR-010). How install does so is a question for the overview's build (Implications).
- **How it stays fresh:** the stamp rewrites it whenever it writes an artefact. After a hand edit of a field a diagram draws, a command rewrites it, apart from the query, which writes nothing. Validation fails a stale overview, and its finding names the command.
- **Opting out:** a project that deletes it is reported, never failed. How a deletion lasts past the stamp's next rewrite is a question for the overview's build (Implications).
- **What it anchors:** nothing, since a held document carries no friction block (COR-050 point 12). Generation and the check that it is fresh keep it true to what it draws. The capability's maintainer took this as meeting "it anchors what it shows".
- **What it costs each adopter:** a change to anything it draws owes a rewrite of the overview in the adopter's own analysis, a title or a status included. Two branches that each make such a change conflict on the overview, as on a lock file. The command's rewrite resolves it.

### 9. Where a generated diagram never shows

A generated diagram shows on demand and in the overview. A copy pasted by hand follows the same limits. It never shows in two places:
- **Inside an analysis artefact.** Each relation has one home, the front-matter field that lists it. A copy in another artefact's body would change with every edit elsewhere, and flag that artefact's dependants. What meets a requirement is never stored on it for the same reason (DEC-002 point 7).
- **In a view of the solution,** such as an architecture page or a record. A view states none of an analysis artefact's facts (DEC-001 point 11), and a generated diagram states them.

A copy on any other page is that page's diagram, and the page anchors each artefact it draws.

### 10. The rules bind at SAN's next major

`SAN` gains two rules, proposed, with this record their origin:
- **A diagram's facts,** stating points 1 and 2. A diagram in the analysis shows no fact without a home elsewhere. A diagram in an artefact shows only what that artefact, or an analysis artefact it anchors, states.
- **A text alternative.** A diagram, an image or a recording in the analysis that carries meaning has one. A decorative image has an empty one.
  - **A Mermaid diagram's alternative** is its `accTitle` and `accDescr`. An image's is its alt text, and a recording needs one of its own, such as a transcript.
  - **Its checkable part:** each `mermaid` fence in an analysis artefact carries an `accTitle` and an `accDescr`, each followed by text that is not blank. The capability's validation fails a fence without them, where the rule binds.
  - **Images are left to a reviewer.** No check tells a decorative image from one that carries meaning.

A diagram's labels are statements of its artefact. So a judgement rule of `SAN` that reads an artefact's statements reads them too, and does not pass over a Mermaid fence as quoted code.

Until a major accepts the two rules, they bind nothing (COR-051 point 4). They join the major that accepts `SAN`'s other proposed rules, so adopters review one major, not two (COR-051 point 7).

## Rationale

**Why diagrams are generated where they can be.** A diagram that nobody edits cannot drift from what it draws. The analysis already holds the relations as data, so drawing them asks no writer to draw.

**Why a diagram is never a fact's home.** A home is where a change to a fact is made. A picture cannot say which relation each line shows, so the change is always made in the field or the part that the picture restates.

**Why front matter only, for now.** Reading front matter needs no change to an accepted point. It draws what the capability's maintainer took: who takes part, a journey's path and what meets a requirement. Reading body parts by their permanent id would draw paths and seams too, so it changes what DEC-001 point 1 allows a tool. It comes as a refinement of its own.

**Why a use-case diagram, not a context diagram.**
- **What was asked** was a context diagram from actors and use cases. Drawn from them, it is UML's use-case diagram, which shows the system's boundary with the actors around it.
- **A context diagram,** the system as one box among its actors, is the context view DEC-001 point 11 keeps outside the analysis. A title would not change what it shows. So an analysis with actors and no use case draws no use-case diagram, which would be that box.

**Why a journey's `relies-on` draws no arrow.** The front matter lists the use cases a journey relies on as a set. Which step needs which lies in the body, so any arrow would state a fact the front matter does not hold.

**Why the chain leaves implied arrows out.** Many use cases need the same early ones, such as the use case every later one starts from. An arrow from it to each of them repeats what the chain already shows through the use cases between. Leaving those out shows the order the areas' numbers give.

**Why loops count as one node.** `after` allows a use case to name itself, and producers to close a loop (DEC-001 point 1). Within a loop, every arrow is implied by the others, so leaving out implied arrows there has no single answer. Counting a loop as one node keeps every arrow within it, and gives one answer outside it.

**Why a later producer is dotted.** A precondition may name several producers, any one enough. A later one is a true alternative, so it is still drawn, apart from those its area builds on.

**Why one analysis per diagram.** Each analysis describes one component, and its journeys and chains stop at its edge (DEC-001 point 2). Of the fields a diagram reads, only an actor's may name another analysis's artefact. So that actor is the one node drawn from beyond the edge.

**Why the overview, beside the query.**
- **A reader on a repository host** sees the overview with no setup, which "supports diagrams by default" asks.
- **The query alone** shows nothing until someone runs it.
- **Regions on another component's pages** need a data point and a rule on grounding that no page needs yet (COR-007).

**Why the overview carries no anchors.** A held document carries no friction block, and validation fails one that does (COR-050 point 12). The overview is generated from what it draws, and checked fresh, so it cannot drift from it. An anchor would add a flag on every drawn change, which the freshness check already fails until the overview is rewritten.

**Why its own Mermaid writer.** A shared writer would be a backbone command that takes a graph from a capability and returns its text. The part the two writers share is small. A command for it would carry more than it saves, until a third writer shows what such a command must take.

**Why the rules wait for a major.** A new accepted rule needs a new major of `SAN`, and every project's pin then falls behind until it reviews the set (COR-051 point 7). Landing them proposed lets a reviewer preview them, and lets them share one major with `SAN`'s other proposed rules.

### Alternatives considered

- **Reading body parts by their permanent id in this first build.** Not taken. It refines DEC-001 point 1, and the first diagrams are drawn without it. It is the next step (point 3).
- **Moving a use case's steps and a journey's seams into front matter.** Rejected. It moves the readers' text into data, which DEC-001 point 1 keeps apart.
- **A requirements context diagram beside the use-case diagram.** Rejected. It is a context view, which DEC-001 point 11 keeps outside the analysis. A project that wants its system's scope without its use cases draws such a view in its solution's documentation.
- **A shipped part for diagrams in each kind.** Rejected. Most artefacts would carry it as `None.`, and every live artefact would need a migration.
- **A diagram in an artefact that shows more than its anchors carry,** such as the journeys a use case takes part in. Rejected. A use case anchors none of them, so a change to one would flag nothing. A use case that anchored a journey to mend that would close a cycle (COR-050 point 5).
- **A rule against styling, with a check of Mermaid's directives.** Not taken yet. The authoring skill is to carry point 2 (Implications), and a rule comes when a project finds styling the skill did not prevent (COR-007).
- **A generated diagram stored inside an artefact.** Rejected. See point 9.
- **Diagrams on demand only, with no overview.** Rejected. It meets "it anchors what it shows" word for word, but shows nothing on a repository host.
- **Regions on another component's pages, filled through a data point now.** Not taken yet. A page that must show an analysis diagram is the trigger. The capability would then contribute to that point, as it contributes to the readers point, refining DEC-001 point 8.
- **Every producer drawn solid, implied arrows included.** Rejected. An early use case would draw an arrow to each use case after it, and the picture would show little else.
- **The chain at two levels:** the areas' order between areas, and every arrow within an area. Not taken. Between areas, it would lose which use case leads to which.
- **The chain's query built now.** Not taken. The capability reads no `after` yet, and the query comes with the build that adds it.
- **A backbone command that turns a graph into Mermaid.** Not taken yet. See Rationale.
- **The rules accepted now, in a major of their own.** Rejected. Each major is a review for every adopter.

## Implications

- **A query** prints the use-case diagram, each journey's flow and the requirement map of the analysis, or the one its subject names (points 4 and 7). It is read-only and offline.
- **The chain's query** comes with the build that adds `after` and its check (point 5).
- **The overview** is built after the query (point 8). That build adds:
  - its folder of held documents
  - its writing by install, a migration and the stamp
  - the command that rewrites it, and the check that it is fresh
- **Three questions for the overview's build.** Each answer refines point 8, so the build brings it to the capability's maintainer before it lands:
  - **How install writes it.** Install creates what a capability declares, such as its project rule set, and has no step that runs a capability's command (COR-017).
  - **How a release prints it.** A check of its text alone fails every adopter's overview at each release that prints it differently, until a migration rewrites it. A fingerprint of what it draws, beside the text, would tell the two apart.
  - **How a project keeps none.** The stamp's next rewrite would restore a deleted overview, so the opt-out needs a form that lasts, such as a setting.
- **`SAN`** gains the two proposed rules of point 10, and the validator their checkable part. Its judgement rules read a Mermaid fence's labels as statements. The forms check reads a fence as part of the text or the item it follows (point 2).
- **DEC-001** points 1, 2 and 11 name what this record adds to them. Point 8 is not refined, since the capability contributes no diagram to another component's point.
- **The authoring skill** tells a writer where a fence may sit, what it may show, and that it holds no styling (point 2).
- **Projects** see their analysis's diagrams with no setup once the overview is built. A project that adopts the rules at `SAN`'s next major reviews the diagrams in its artefacts for their text alternatives.
