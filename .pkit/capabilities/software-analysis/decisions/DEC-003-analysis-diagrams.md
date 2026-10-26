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
- **A tool reads data from front matter.** A body's text serves readers and the check, never another tool (DEC-001 point 1).
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

On 22 October the capability's maintainer asked that the overview read first as a story for a newcomer ([project-kit#1887](https://github.com/aleskalfas/project-kit/issues/1887)). It opens with what the component is for, which a decision record states. Drawn for the core's analysis, the requirement map, the chain and the use-case diagram are too big to read on a page.

## Decision

**The capability draws four diagrams from an analysis's front matter: a use-case diagram, a journey's flow, a requirement map and the chain of use cases. A query prints them on demand, from the working tree. Each analysis's generated overview shows what the analysis holds, and names that query. Of the diagrams, it shows only each journey's flow, beside its journey. It is written for a newcomer first, and opens with what the component is for, from a decision record the configuration names. No diagram is a fact's home. A diagram written in an artefact shows only what that artefact, or an analysis artefact it anchors, states.**

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
- **Its query** is point 7's, with the chain as its subject. It draws the chain where a use case in force writes `after`.

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

### 8. A generated overview is the reader's entry point

Each analysis keeps a generated overview, the reader's entry point. A reader on a repository host, such as GitHub, sees there with no setup what the component is for and how the analysis describes it. The reader also sees why its areas are cut as they are.
- **What it is:** a held document, `overview/README.md`, in a folder of held documents of its own in the analysis (COR-050 point 1). A held folder never equals or encloses a documentation root or another declaration's place.
- **Its reader** is a newcomer first: someone new to the analysis, joining work on the component, a person or an agent. Such a reader reads the page from top to bottom, so the page's order is the reading path, in two parts:
  - **the story,** read in order: the opening, then the areas, and the use cases in no area last
  - **reference,** read when needed: everything else but the closing line, under the heading "Reference"
- **What it shows,** in this order, each artefact in force and linked:
  - **the opening:** what the component is for, from its purpose record (below). Then two sentences say what the analysis is and what it builds on. For a component named billing that builds on no other analysis, they read:

    > This analysis describes what billing does: who uses it, what they do with it, and what it must meet. It builds on no other analysis.

    An analysis that builds on others names them in the second sentence, as the configuration lists them. The one analysis at the location's top names no component, so its first sentence reads "the system" where a component's name would stand.
  - **the areas,** in their numbered order, each with its goal, the areas it builds on, its concepts, its requirements and its use cases (below). Then the use cases in no area, in a section of their own. An analysis whose use cases lie in no area lists them under its use cases.
  - **reference,** each part below a section heading of its own under "Reference":
    - **who takes part:** one table of the actors (below)
    - **the words:** the glossary, then each domain-model view in its numbered order, by its number and its title
    - **the requirements in no area:** those whose file lies in no area's folder, such as those that bind the whole system (DEC-001 point 12)
    - **the journeys,** each with its flow, where journeys exist. A journey's flow is the query's own output, with its text alternative (point 7).
    - **"Not built yet":** each open shortfall a use case in force lists, with its use case, its step or variant, its record and its issue (DEC-001 point 1). It is shown where there is one.
    - **the diagrams:** one line that names the query, as it is run for this analysis, and its subjects. It ends reference on every page, so every page has the heading "Reference".
  - **a closing line:** the command writes the page from the analysis, so a reader changes the analysis, never the page
- **Complete, or no answer.** The command writes no overview where the query could not draw each of its diagrams in full (point 7). The two share one test, so the page is written only where the query it names answers. Validation fails such a file in any case.
- **Front matter, and the links to the terms.** The overview reads the analysis's front matter and the paths of its files, as DEC-001 point 1 allows a tool. Of a body, it reads only the links to the glossary's entries a use case or a requirement holds, which the links command writes and the check holds ([software-analysis:DEC-004-domain-model-views] point 7). A requirement's area is read from its path. Beyond the analysis's files, it reads the capability's configuration and the front matter of the record its purpose names.
- **Its purpose.** What a component is for is a decision, so a decision record states it. The analysis's entry in the capability's configuration points to that record, `purpose: <record id>`, as the entry names the analyses it builds on.
  - **Which record:** a decision record the project owns, named as a record anchor names one, such as `PRJ-004` or `billing:DEC-001`. That is a project or an architecture record, or, for a capability's analysis, a decision of that capability.
  - **Never a record a release changes.** A core record, or another capability's decision, reaches an adopting project with a release. A new title there would leave the overview stale after an upgrade, so the check refuses such a pointer.
  - **A record whole,** never one of its points. A point has no title in front matter, which is all the overview reads of a record.
  - **The one analysis** at the location's top keeps its pointer at the configuration's top, as it keeps its goals.
  - **What it shows:** the record's title as a sentence, linked to the record. The title is shown as written, with a full stop where it ends with none. So whoever titles the record states there what the component is for.
  - **The check** fails a pointer to no record, and one to a record that is not accepted, as the acceptance gate asks. It checks the pointer whatever the setting that keeps the overview, since a pointer left in the configuration still names a record.
  - **Such a pointer on the page.** The overview shows no title of a record that is not accepted. It says instead that the record named is not accepted, or that no record has that id. The rest of the page is written as usual.
  - **No record named:** the overview says that no record states what the component is for yet. It names the command that writes one, and the setting that names it. Nothing fails.
- **Each area** shows, below its goal:
  - **Builds on:** the other areas that hold a producer its use cases name in `after`. A producer in a later area is left out, as an alternative the area does not build on (point 5, DEC-001 point 12). The environment is no area. Where none of the area's use cases writes `after`, the line is left out, since nothing says what the area builds on.
  - **Its concepts:** each domain-model view in force of its own analysis that explains a term one of the area's use cases or requirements links to, in the order of the views' numbers. It is shown where the analysis holds a view in force. An analysis whose use cases lie in no area, and the use cases in no area, show no concepts.
  - **Its requirements:** each requirement in force whose file lies in a folder named for the area, inside its kind's folder (DEC-002 point 3). A requirement's area folder takes the name of the use cases' area, so the two read as one area.
  - **Its use cases,** each marked where an open shortfall names one of its steps or variants.
  - **Not written yet:** an area whose goal the configuration gives, and which holds no use case in force, shows its goal and "Not written yet."

  The areas shown are those that hold a use case or a requirement in force, and those the configuration gives a goal. An area is matched by its folder's name, among the use cases, the requirements and the goals alike.
- **Who takes part:** one table, with a row for each actor in force. It shows the actor, linked, who it is, and the areas it acts in.
  - **Who it is:** the actor's `summary`, the first sentence of its opening, as its front matter gives it (DEC-001 point 1). The cell is empty where an actor gives none.
  - **The areas it acts in:** those of the use cases in force where the actor is the main actor, its `actor`, or takes part, its `other-actors`. They are computed from the use cases' front matter, so the table states no fact of its own.
  - **A use case in no area** is shown as such beside the areas. In an analysis without areas, the cell points to its use cases.
  - **An actor of another analysis.** An analysis that builds on another may name that analysis's actors (DEC-001 point 2). Its table lists each one its glossary's head lists, or a use case names, after its own actors. It shows the actor by its id with that analysis and the name the head gives it, and the areas it acts in. Who it is says which analysis it belongs to, and whether the head lists it. It reads no file of the other analysis.
- **An area's goal:** one line for each area of an analysis's use cases, kept as data in the capability's configuration beside the area's folder name. It is the area's summary goal, one level above its use cases, which are the steps toward it.
  - **Its form:** one phrase that starts with its verb, as the capability's hints ask of a use case's goal (DEC-001 point 1). So it reads after "The goal is to …". It may end with "so" and its reason, what reaching the goal serves. An example is `010-ordering: Place an order and pay for it`.
  - **No actor's voice:** it holds no *I* or *my*, since an area has several actors.
  - **Each analysis its own.** Each analysis numbers its own areas (DEC-001 point 2), so it keeps the goals of its own areas.
  - **Its home** is the configuration. It is the one text the overview shows that neither an artefact nor a record holds. No anchor covers it, and no rule of `SAN` judges its words or its form. This record and the authoring skill carry its form.
  - **The check.** Where the project keeps its overview, it warns of an area of use cases or requirements in force without a goal. A goal whose area holds no use case shows that area as not written yet, so the check fails no goal.
  - **No areas.** A project whose use cases and requirements lie in no area keeps no goal.
- **Who writes it:** its own command, which writes the overview of each analysis that holds an artefact, and the stamp, after it writes an artefact. Each writes a file only where its bytes change. The query writes nothing. Install writes none, since install runs no command of a capability (COR-017). So a project gets its overview from its first stamp, or from the command.
- **How it stays fresh:** the overview carries a fingerprint of what it draws, the data it reads, never its text. Validation compares it with the analysis, and fails a stale overview. Its finding names the command.
  - **A release that only prints it differently** changes no fingerprint, so it fails no project. The next rewrite prints it anew.
  - **A release that changes what the fingerprint reads, or how it is computed,** raises the version the fingerprint carries. An overview written under another version is a warning until the command rewrites it, so such a release fails no project either.
  - **A missing overview** is a warning that names the command. So a project that installed the capability before fails nothing, and needs no migration.
- **Keeping none:** a setting in the capability's configuration turns the overview off. The stamp then writes none, the command refuses, and validation asks for no overview and no goal. It still checks a purpose's pointer. It warns of an overview left in place, which nothing keeps fresh.
- **What it anchors:** nothing, since a held document carries no friction block (COR-050 point 12). Generation and the check that it is fresh keep it true to what it draws. The capability's maintainer took this as meeting "it anchors what it shows".
- **What it costs each adopter:** a change to anything it draws owes a rewrite of the overview in the adopter's own analysis. A title, a status, a use case's actors and shortfalls, an actor's summary and a goal are included. So is a link to a term that leads an area to another view. So are the title and the status of the purpose record, though the record lies outside the analysis. A change that supersedes that record also fails validation, until the pointer names its successor. Two branches that each make such a change conflict on the overview, as on a lock file.
  - **Where they conflict:** always on its fingerprint's line, and on each section both change. A section for each part keeps the rest apart.
  - **Resolving it** is running the command.

### 9. Where a generated diagram never shows

A generated diagram shows on demand, and a journey's flow in the overview too. A copy pasted by hand follows the same limits. It never shows in two places:
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

**Why an overview of its own.** A reader on a repository host sees the overview with no setup. Regions on another component's pages would need a data point, and a rule on grounding that no page needs yet (COR-007).

**Why the query prints the diagrams, and the overview names it.** The capability's maintainer chose this on 22 October, reading the core's overview ([project-kit#1887](https://github.com/aleskalfas/project-kit/issues/1887)).
- **Too big to read.** The core's analysis held 19 use cases and 9 actors when the maintainer read it. Drawn for it, the requirement map and the use-case diagram each drew more than 40 arrows. With the chain, the three would take more than half the page.
- **The page says the same in text.** Each area lists its use cases and its requirements, and the table of who takes part says where each actor acts. Each use case's page names its actors, what comes before it and the requirements it must meet. Each requirement's page names the requirements it refines and the actors whose need it meets.
- **A query prints them.** The query draws them from the working tree each time it runs. So it shows a change in progress, hand edits included, while the page changes only when it is rewritten. It also prints one requirement's map, or one journey's flow, by its id, which stays small. Its form for a program serves an agent or a tool.
- **An agent works from checks and queries.** It keeps the analysis consistent through them, never through a picture. A diagram is never a fact's home (point 1), and the rule of logical consequence judges the use cases, never the picture (point 5). On the page, the three would cost an agent some 200 lines each time it reads the overview to find its way.
- **Diagrams by default.** Every project with the capability prints them with no setup, as "supports diagrams by default" asks. The overview names the query, so a reader finds it.
- **What it costs.** A reader on a repository host, with no checkout, sees none of the three. The artefacts' own pages hold what they draw: each use case's and each requirement's page names its relations.
- **A section of its own for the line.** A reader who looks for the diagrams finds them by the heading. Below the last list of reference, the line would read as part of that list.
- **A journey's flow on the page.** A journey's flow draws one path, its steps in a line, so it does not grow into a tangle as the analysis grows. Where the journeys stand on the page is said under the two parts, below.

**Why the overview carries no anchors.** A held document carries no friction block, and validation fails one that does (COR-050 point 12). The overview is generated from what it draws, and checked fresh, so it cannot drift from it. An anchor would add a flag on every drawn change, which the freshness check already fails until the overview is rewritten.

**Why a newcomer first.** The overview is the reader's entry point, and the reader who needs it most is new to the analysis. Such a reader asks what the component is for, and how its parts follow from each other, before any list. A returning reader looks things up, so the lists follow the story. The capability's maintainer chose this order on 22 October, reading the core's overview point by point ([project-kit#1887](https://github.com/aleskalfas/project-kit/issues/1887)).
- **Which newcomer.** The analysis serves whoever works on the component, since it never ships with the component (DEC-001 point 2). So its newcomer is someone joining work on the component, a person or an agent. A project's own documents, such as its README, serve whoever decides whether to use the component. The areas' numbered order follows what builds on what (DEC-001 point 12), the order in which whoever works on the component builds it. The capability's maintainer settled this on 23 October.
- **What the analysis is.** A page that does not say what an analysis is reads as one meant for whoever decides whether to use the component. So the first of the two sentences after the purpose says what an analysis is. It names, in words a newcomer knows, who uses the component, what they do with it and what it must meet. The maintainer chose its words on 23 October.

**Why two parts, with the page's order as the reading path.** A newcomer reads the page from top to bottom, so the page's order is the reading path. A line that names two places to start gives no single path. The heading of reference marks where the story ends. So a newcomer knows where to stop, and a returning reader knows where to look things up. The capability's maintainer chose the two parts on 22 October, on the same issue.
- **The words in reference.** A term is looked up where the story uses it, so the glossary and the views lie in reference.
- **The journeys in reference.** No analysis the maintainer has reviewed holds a journey yet, so none has shown how one reads. The first that does is the trigger to weigh whether journeys belong to the story, and whether their flows stay on the page as journeys grow in number (COR-007).

**Why the purpose lives in a record, and the configuration points to it.**
- **A reason belongs in a record.** What a component is for is the reason behind every area of its analysis. A decision holds a choice and why it was made (DEC-001 point 11, "Where a statement belongs"). A record is also reviewed and accepted. An artefact that rests on it, such as a view of the component's concepts, can anchor it.
- **No rule judges a setting.** A purpose written as text in the configuration would be one more text that no artefact holds. No rule of `SAN` would judge it (point 8).
- **The pointer is structure.** Like the entry's list of the analyses it builds on, it says which record the analysis rests on, never what that record says. So the pointer holds no reason of its own.
- **Only an accepted record.** A proposed record decides nothing yet, so the overview shows none as what the component is for, as the acceptance gate asks.
- **A pointer that fails, said on the page.** The page says what is wrong, and stays fresh for the rest of the analysis. Validation fails the pointer, so the change that broke it mends it.
- **Its title.** The title states a record's decision in one line, and the overview reads only a record's front matter.
- **No solution in the analysis.** The overview is no artefact of the analysis but its entry page. A component's purpose is the one statement that comes before every requirement, so the page may name its record.
- **Nothing fails without one.** A project may adopt the capability before any record states what its component is for. The overview says so and names the way to write one.

**Why each area shows what it builds on and its own requirements.** An analysis is built area by area, each after the areas it builds on. An area's requirements come before its use cases (DEC-001 point 12). Shown together, they tell the path through the system in the order it is built. Both are computed, from `after` and from a requirement's path, so they state no fact of their own.

**Why each area shows its concepts.** A reader who starts from an area asks which concepts its use cases and requirements rest on, and where each is explained. The maintainer asked for it on 26 October, reviewing a change to project-management's analysis as a newcomer would read it ([project-kit#2104](https://github.com/aleskalfas/project-kit/issues/2104)).
- **Read from the links to the terms.** They are the one reading the analysis holds of which terms an artefact uses ([software-analysis:DEC-004-domain-model-views] point 7). The links command writes them and the check holds them, so the overview reads a copy that never drifts.
- **Only those links of a body.** A body's other text serves readers alone (DEC-001 point 1). The overview reads no part of it, so a reworded statement that moves no link leaves it fresh.
- **The order of the commands.** A mention that comes to lead an area to another view makes the overview stale once the links command links it. So the links command runs first, then the overview's, and the check names each where its output is stale.
- **Its cost.** Where most artefacts use the lowest views' concepts, each area lists most views, as four of the core's five areas did on 26 October. The line still says where each area's words are explained.

**Why an area not written yet shows.** An area the project has planned is a stage of the path, whether or not a use case is written in it yet. Shown in its place, it tells a newcomer where the path has a gap.
- **What it costs.** No check holds the areas' folder names together. A goal left behind when an area is renamed shows as an area not written yet. A requirement's folder named apart from its use cases' shows as an area of its own. A reader of the overview sees either, and the check warns of each such area that has no goal.

**Why the overview shows each area's goal.** The chain shows which use case follows from which, never why the use cases are split into those areas. The capability's maintainer asked, on 20 October, that a reader of the analysis can see the concept of the split. One line for each area says it, with no new kind of artefact.

**Why an area's goal is a summary goal that starts with its verb.** A goal answers "what is the goal of this area?". A statement of what holds once the area is done, such as "a customer can place an order", reads as a result, not a goal. Use-case practice names a goal with a verb phrase, as DEC-001's Rationale says of a use case's goal ("Why the actor's voice ships"). An area's goal is a summary goal over its use cases, which are the steps toward it. It takes no actor's voice, since an area has several actors. The capability's maintainer chose this form on 23 October.
- **No rule of `SAN` judges its form.** The goal lives in the configuration, and no rule of `SAN` judges a settings value, as "Why the purpose lives in a record" says of a purpose. So this record and the authoring skill carry the form.
- **Its reason is no record's.** A goal's "so" clause says what reaching it serves, in a few words, as part of the goal. It records no choice and why it was made, which is a record's to hold. What the component is for, the reason behind every area, stays in its purpose record.

**Why each view by its number and title.** The concepts are listed by their labels alone, so a reader scans them as a list. The capability's maintainer chose it on 21 October, on reading the core's overview. A view's opening states the problem its concepts solve on the view's own page, one link away. Quoted beside each title, it made the list of concepts long and uneven. A view's problem is a reason, whose home is a record (DEC-004 point 3). Who an actor is lies in the actor's own front matter, so the table of who takes part shows it.

**Why one table of who takes part.** A reader who meets an actor asks who it is, and where in the path it acts. One row for each actor answers both at a glance. Which use cases each actor takes part in is a longer list. Each use case's page names its actors, and the query's use-case diagram draws them all. The capability's maintainer chose the table on 22 October.

**Why the open shortfalls, after the journeys.** Each marks a step where the system falls short of an accepted record. Listed in one place, they show a reader every such step at once. The capability's maintainer decided to list them on 21 October ([project-kit#1855](https://github.com/aleskalfas/project-kit/issues/1855)).
- **Where.** A newcomer first reads the story, and looks up what the system still lacks, so the list lies in reference. Each area's use cases are marked too, so a newcomer meets each gap on the path. The maintainer placed the list on 22 October ([project-kit#1887](https://github.com/aleskalfas/project-kit/issues/1887)).

**Why the goals and the purpose's pointer sit in the configuration.** DEC-001 rejects a project's additions to a structure in the configuration, since settings and data would then share a file. The goals and the pointer sit beside the list of analyses. That list is data of the same kind: each analysis's folder and what it builds on.

**Why a fingerprint of what it draws.** A check of the overview's text would fail every adopter's overview at each release that prints it differently, until a migration rewrote it. A fingerprint of the data it reads tells a stale overview from one printed differently.

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
- **No overview, the diagrams on demand only.** Rejected. A reader on a repository host would find no entry point, and no page that says what the component is for.
- **The requirement map, the chain and the use-case diagram on the page.** Not taken. See Rationale.
- **The three folded in a collapsed block on the page.** Not taken. Folding hides their size, but keeps pictures too large to read.
- **The three on a second generated page, linked from reference.** Not taken. Its pictures would be as large, and a second page is a second file for branches to conflict on.
- **A use-case diagram for each area, in the story.** Not taken. Each area lists its use cases, and the table of who takes part says where each actor acts, so the picture would restate both.
- **A check of the overview's text, not a fingerprint.** Rejected. See Rationale.
- **The first paragraph of each view's opening, beside its title.** Rejected. It made the list of concepts long and uneven, and it reads a body's text, which DEC-001 point 1 keeps from a tool.
- **The problem in a field of the view's front matter.** Rejected. It would be a third home for a reason whose home is a record (DEC-004 point 3).
- **A page for whoever decides whether to use the component,** with its areas in the order of what such a reader would do first. Rejected. See Rationale, "Why a newcomer first".
- **A line in the opening that says where to start,** naming the first domain-model view and the first area. Rejected. It names two places to start, and the page's own order is the path (see Rationale).
- **Each actor's use cases listed under the actor in the overview.** Not taken. A reader asks where each actor acts, which one row of areas answers. Each use case's page and the query's use-case diagram show the longer list, of each use case.
- **A pointer to a record that is not accepted stopping the overview from being written.** Rejected. Each later change to the analysis would leave the overview stale too, for a reason outside the analysis.
- **A purpose written as text in the configuration, with a rule that traces each area's goal to it.** Rejected. A rule cannot judge a setting, and a reason belongs in a record (see Rationale).
- **A kind of artefact for the component's purpose, inside the analysis.** Rejected. A new kind needs a decision of its own (DEC-001 point 11), and a record already answers the need.
- **A pointer to any record, a core record or another capability's decision included.** Rejected. A release would change such a record in an adopting project, and fail its overview.
- **The purpose record's opening sentence in place of its title.** Rejected. The overview would read the record's body, and a tool reads no body's text (DEC-001 point 1).
- **A goal that names no area of the use cases failing the check.** Rejected. An area planned and not written yet would be hidden until its first use case.
- **The areas each area builds on, written in the configuration.** Rejected. They would state again what the use cases' `after` holds.
- **The views of each area written in the configuration.** Rejected. They would state again what the links to the terms hold, and drift from them.
- **Each area's concepts read from the views' closing sections.** Not taken. Each closing section is a copy of the links to the terms, so the overview would read a copy of a copy.
- **Only the views that set an area apart from the others.** Not taken. Choosing them would weigh counts of uses, and an area's words would lose the link to where some are explained.
- **Each actor's use cases in the actor's own file.** Not taken yet. A list a command writes there would change the actor's file at each new use case, and so the answers on it. It waits until a list written for navigation changes no answer ([project-kit#1844](https://github.com/aleskalfas/project-kit/issues/1844)).
- **An actor of another analysis by its name in that analysis.** Rejected. The overview would read another analysis's files, which may lie in another repository, and go stale with them. The glossary's head names the actor in this analysis.
- **Install or a migration writing the overview.** Not taken. Install runs no command of a capability (COR-017). A missing overview is a warning, so a project that installed the capability before needs no migration.
- **Deleting the overview to keep none.** Rejected. The stamp's next rewrite would restore it, while a setting lasts.
- **An area's goal stated as what holds once the area is done,** such as "a customer can place an order". Rejected. It reads as a result, not a goal (see Rationale).
- **An area's goal in a file in the area's folder.** Rejected. The folder lies in the use cases' place, so a file there would read as a use case.
- **Regions on another component's pages, filled through a data point now.** Not taken yet. A page that must show an analysis diagram is the trigger. The capability would then contribute to that point, as it contributes to the readers point, refining DEC-001 point 8.
- **Every producer drawn solid, implied arrows included.** Rejected. An early use case would draw an arrow to each use case after it, and the picture would show little else.
- **The chain at two levels:** the areas' order between areas, and every arrow within an area. Not taken. Between areas, it would lose which use case leads to which.
- **A backbone command that turns a graph into Mermaid.** Not taken yet. See Rationale.
- **The rules accepted now, in a major of their own.** Rejected. Each major is a review for every adopter.

## Implications

- **A query** prints the use-case diagram, each journey's flow, the requirement map and the chain of use cases of the analysis, or the one its subject names (points 4, 5 and 7). It is read-only and offline.
- **The overview** (point 8) adds:
  - its folder of held documents
  - its command, and the stamp's rewrite of it
  - each area's goal in the configuration, and its check
  - the pointer to the purpose record in the configuration, and its check
  - what each area builds on, read from `after`, and its requirements, read from their paths
  - each area's concepts, read from the links to the terms its use cases and requirements hold
  - the table of who takes part, with each actor's `summary` (DEC-001 point 1)
  - the fingerprint and its version, and the check that the overview is fresh
  - the setting that keeps none
  - the list of open shortfalls, read from each use case's `shortfalls`
  - the line that names the query and its subjects
- **`SAN`** gains the two proposed rules of point 10, and the validator their checkable part. Its judgement rules read a Mermaid fence's labels as statements. The forms check reads a fence as part of the text or the item it follows (point 2).
- **DEC-001** points 1, 2 and 11, and **DEC-002** point 3, name what this record adds to them. Point 8 is not refined, since the capability contributes no diagram to another component's point.
- **The authoring skill** tells a writer where a fence may sit, what it may show, and that it holds no styling (point 2). It also tells a writer to print the chain before adding a use case, or changing what one names in `after`, and how to write each area's goal (point 8).
- **Projects** print their analysis's diagrams with no setup, through the query their overview names. A project that adopts the rules at `SAN`'s next major reviews the diagrams in its artefacts for their text alternatives.
