---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-19
---

# Analysis concepts and order

## The question

How is an analysis built from its concepts, in what order, and where does each component keep its own? The maintainer decided all three on 19 October. This note designs those decisions for software-analysis, for any project, with project-kit as the worked example.

- **The design, as decided:** the domain model, numbering, one analysis per component, and the rule of logical consequence. Each is a constraint here, not an open option.
- **What changes, and the order to build it.**
- **Weighed and set aside:** one line for each alternative, with why.
- **The reviews,** and the questions left for the maintainer.

## Where things stand

The design builds on what main holds today, and on a map of project-kit's chain of use cases.

- **Seven kinds, and no domain model.** DEC-001 keeps actors, use cases, journeys and terms, and DEC-002 adds three kinds of requirement. A new kind needs a decision of its own (DEC-001 point 11).
- **The glossary holds 65 terms.** Each definition takes ISO 1087's form: its broader kind, then what sets it apart (DEC-001 point 1). #1785 settled six groups of them: the whole and its ownership, the parts, records and rules, the checks, change over time, and work.
- **A use case splits what holds before it starts.** A precondition is a state the system or an earlier use case made true. An assumption is what nothing in the system secures, with the record that admits it (DEC-001 point 1). Nothing says which use case made a precondition true.
- **An analysis is built bottom-up** (DEC-001 point 12). The glossary comes first, then the requirements, the use cases area by area, and the journeys. Which area builds on which is the writer's judgement.
- **A concept is used only as the glossary defines it** (RS-SAN-008, proposed). A reviewer reads the glossary of the analysis that holds the artefact.
- **One analysis per repository.** project-kit's lies under `tech-docs/analysis/`, with two use-case areas, `change` and `release`.
- **Ids are kept apart within one analysis.** Each kind has its prefix (DEC-001 point 3), and the analysis's validation refuses an id two of its artefacts share.
- **The backbone looks an artefact anchor up across the repository.** Its lookup takes the first artefact it finds with that id (`find` in `friction_discovery.py`). Friction knows no analysis.
- **Use cases reach work tracking by id.** The analysis gives each use case to work tracking under its id, and an id names one use case for good (DEC-001 point 8). project-management reads that id as `UC-` and three or more digits (project-management DEC-054 point 1).
- **The reverse of an anchor is computed, never stored** (DEC-001 point 11, DEC-002 point 7).

**The chain, mapped on 19 October** from main at `b41cf6ec`, over the use cases written and planned:

- **One initial use case.** "Develop the methodology in its source repository" needs only two assumptions: the source repository, and Python with `uv`.
- **Cycles, each broken by a fact.** A project holds the system after install, and install needs a release, which needs those same use cases. The source repository holds the system from the start, with no install (ADR-059). So that precondition has two producers.
- **Gaps:** two needs no actor states, four preconditions nothing produces, and seven use cases that read "None." under Preconditions but rely on another use case.
- **Three cycles among the glossary's definitions:** base, head and change, anchor and artefact, and answer and friction. Point 12 rules them out, but RS-SAN-008 judges what a definition uses, not its order, so they passed.

## 1. The domain model

The domain model explains the domain's concepts and how they relate, in a few hand-written views beside the glossary. It takes known methods, and keeps the glossary as it is.

### The methods it takes

- **The Unified Process's domain model** (Larman, *Applying UML and Patterns*): conceptual classes, their associations and attributes, and no operations. It uses UML's class-diagram notation, and describes the domain, never the software.
- **ICONIX's order:** the domain model first, with the glossary, before the use cases.
- **ISO 704 and ISO 1087:** a concept is distinct from the term that names it. Concepts relate in three ways, generic, partitive and associative, and a concept diagram draws them.
- **State models** (Shlaer–Mellor, UML state machines): a concept's life cycle, as states and the events that move it.
- **Note:** Domain-Driven Design's "domain model" is solution design, which the analysis keeps out (DEC-001 point 11). So it is not this artefact.

### The glossary and the views

- **The glossary stays as it is.** A term's definition, in ISO 1087's form, defines its concept.
- **A term gains a link to its concept's section** in a view. The link is the reverse of the view's anchor on the term, which the records compute and never store. So the link is a named exception, or is computed where the glossary is shown (question 6).
- **The domain model is a folder of views,** `domain-model/`, one view per group of related concepts. project-kit's core has about six, from the groups #1785 settled.
- **What a view holds:**
  - **Its group's diagrams,** hand-drawn Mermaid. A class diagram shows what relates to what, with attributes where they matter. A state diagram shows a concept's life cycle, where it has one. Each fence carries `accTitle` and `accDescr`, and no styling (#1770 decisions 1 and 11).
  - **One section per concept,** headed by its term's name. It opens with a plain explanation for a newcomer. It then gives the concept's attributes, relations and states in words, and what is always true of it.
  - **Anchors** on the terms it explains and the records it rests on. So a changed definition or record flags the view for review.
- **What is always true of a concept** is what its records decide, such as "a rule has one status at a time" (COR-051 point 4). An obligation the system must keep, such as a business rule across use cases, stays a functional requirement (DEC-002 point 1). The requirement uses the concept's term.
- **A diagram is never a fact's home** (#1770 decision 2). A view's diagram restates what the terms, the records and its own sections state. Its sections state each attribute, relation and state in words, so the diagram shows only what its view states (#1770 piece 1).
- **Generated views per concept may come later,** if hand-drawn views prove a burden (COR-007).

### The view as a kind

The domain-model view is a new kind of analysis artefact, so a record of its own decides it (DEC-001 point 11).

- **Its type:** `software-analysis:domain-model-view`, given by the `domain-model/` place of each analysis.
- **Its id:** the file's name without its number. `010-records-and-rules.md` is `records-and-rules`, so a view moved to another number keeps its id. Whether it also takes a prefix is question 4.
- **Its parts:** a lead that says what the group covers, the diagrams, then one section per concept.
  - **A concept's section** opens with its explanation, then the labels **Attributes:**, **Relations:**, **States:** and **Always true:**.
  - **The structure** declares a section that repeats once per concept, which is new for a document kind (DEC-001 point 1).
- **What it anchors:** each term it explains, by an artefact anchor, and each record it rests on. RS-SAN-005's list of what each kind anchors gains it.
  - **Why a view anchors its terms:** using a term asks for no anchor (RS-SAN-008). A view explains what the term defines, so a changed definition asks whether its section still holds.
  - **The cost:** a term is anchored whole, as a collection entry is (COR-050 point 2). A reworded example flags the view too, and costs a short answer.
- **What anchors it:** a living-docs page may anchor one concept's section (below). Nothing in the analysis anchors a view. A term's link to its section is no anchor, so the view's anchor on the term closes no cycle.
- **What a reviewer reads:** RS-SAN-008 reads a view's sections as statements. It also reads the labels in a view's diagrams, which needs RS-SAN-008, proposed, to stop leaving every fenced block out.

### The order inside the domain model

- **A view uses only views with lower numbers.** Its sections and diagrams may name a concept of a lower view, to show a relation. A relation between two views' concepts is stated in the higher view.
- **A reviewer judges it,** under a judgement rule of `SAN` that comes with the view kind's record. A view's uses of other views lie in prose and diagrams, which draw no anchor, so no check sees them.
- **The three definition cycles are broken when project-kit's views are written.** One term of each pair is defined first, and the other's definition names it. For example, base and head become the commits a comparison starts and ends at, and change names both.

### In living docs

- **A page that states a concept's facts** anchors that concept's section of its view, once #1802's record is accepted (#1770 decision 2). The page never becomes the home of those facts.
- **A renamed term** renames its section's heading. Each page anchor on that section is then dead, and validation fails until the same change mends it (COR-050 point 7). Renames are rare, and the failure is loud.
- **living-docs stays independent.** Without an analysis, a page's facts keep their homes among records and pages (living-docs DEC-001 point 9).

## 2. Numbering

Numbers go in names only where a real order exists. They show the order things build on each other.

- **The form:** three digits, in steps of 10, such as `010-` and `020-`, with the same width in every folder. A new item between two takes a free number between them, so nothing is renamed.
- **No part of an id.** A view's id stays `records-and-rules` in `010-records-and-rules.md`. A use case keeps its permanent `UC-NNN` id, whatever its area's number (DEC-001 point 3).
- **What is numbered:** the domain-model views and the use-case area folders, and nothing else.
- **What a number means:** one valid order of a partial order, never importance.
- **What holds it:**
  - **Views:** a view uses only views with lower numbers, and a reviewer judges it.
  - **Areas:** an area builds only on lower-numbered areas. The `after` check holds it for use cases (item 4).
- **Two areas that build on each other** cannot both keep their numbers. The project cuts them again, or makes them one. So point 12's "areas that build on each other are written together" falls away.
- **Its two homes, kept apart:**
  - **General:** what a leading number means, and that the check reads it where a folder has one. DEC-001 points 2 and 12, and `SAN`, hold it.
  - **project-kit's own:** that project-kit numbers its views and areas, and the form above. `ANA` holds it.

## 3. One analysis per component

Each component owns its analysis, as each capability owns its decision records. The core has one, and each capability has one. There is no monolith, since a capability may move to another repository (COR-041).

- **Adapters:** an adapter is a component too, so it may keep an analysis of its own. That follows from the decision, and waits for the maintainer's confirmation (question 1).

### Where

An analysis lives in the internal documentation of the repository where its component is developed, and never ships with it.

```
tech-docs/analysis/
  core/
    glossary.md
    domain-model/010-….md …
    use-case-model/actors/, use-cases/010-develop/ … 050-adopt/, journeys/
    requirements/
  project-management/
    glossary.md, domain-model/, use-case-model/, requirements/
  software-analysis/
  …
```

- **Why internal:** an analysis is documentation for those who develop the system (COR-049).
- **A move:** a capability that moves to its own repository takes its analysis folder with it, as it already takes its tests from `tests/`. What the repository it leaves keeps is question 5.
- **Install is unchanged.** An adopter receives no analysis of the methodology.
- **The core's use-case areas:** `010-develop`, `020-set-up`, `030-change`, `040-release` and `050-adopt`, the five stages of the chain.
- **A capability's areas:** a capability with several areas numbers its own. One with a single area needs no area folders.
- **What marks an analysis:** the capability's project configuration lists the analyses, each with its folder and the analyses it builds on. That configuration already records the analysis's location (DEC-001 point 2).
- **A project with one analysis** keeps it at the analysis area's root, as today. Several analyses each take a folder named after their component. The places match both layouts, so a single analysis stays in them after an upgrade.
- **Revalidation records:** each analysis keeps its own folder of them, which moves with it.
- **The cost of moving in:** each artefact a project moves into such a folder is revalidated in the same change (COR-050 point 3). For project-kit, that is 65 terms, 9 actors and 13 use cases, and moving use cases into numbered areas is the same.

### Dependencies go one way

- **A capability's analysis builds on the core's.** The core's analysis never names a capability's.
- **Between capabilities, only as an option:** "uses X where it is installed, and works without it". A capability may also require another (COR-030), which question 2 weighs.
- **Its head:** a capability's analysis states, at its head, which core stage it builds on. Recommended: the head of its glossary, which then lists all the analysis takes from the core, the stage, the terms and the actors.
  - **The cost:** the stage names a core area folder, which carries no anchor. A re-cut of the core's areas leaves the head stale with no signal, until a reviewer reads it.

### The core as a capability's environment

- **Assumptions:** a capability's use cases state what the core provides as assumptions, each naming the record that admits it.
- **Terms:** a capability's glossary lists, at its head, the core terms it uses. It gives names only, each with a link to the core's glossary at the backbone version the capability requires. It copies no definition.
  - **Its reviewer** reads those core terms as defined, so RS-SAN-008's glossary to read takes them in.
  - **No clash:** a capability's own term never takes the name of a core term it lists.
  - **The version:** question 10.
- **Anchors:** its artefacts anchor the core's records behind those terms and assumptions. Record anchors cross a sync, and artefact anchors do not (COR-050 point 14).
  - **Where they sit:** the glossary's head belongs to no term and carries no anchors (DEC-001 point 1). So a capability's own term that builds on a core term anchors the records behind it. A use case anchors the records its assumptions name.
  - **The cost:** a changed core actor or term flags no capability artefact, even in project-kit. Only a changed record behind it does.
- **The same form everywhere:** project-kit and any other repository use it alike, so a move changes nothing in the analysis.
- **Actors:**
  - **Core actors:** a capability's analysis lists those it uses by name with a link, as for terms. It defines only actors of its own, such as project-management's project manager and implementer.
  - **A use case whose actor is the core's** names it with its analysis, as `core:ACT-developer`. Validation resolves it against the capability's list. The use case anchors the records behind that actor, not the actor. This refines what a use case names and anchors (DEC-001 point 4).
  - **Their needs:** question 9.
  - **The core as an actor:** where the core triggers a capability, such as validation running a capability's check, the core is a secondary actor of that capability's analysis.

### Tooling

- **Several analyses:** software-analysis supports one analysis per component under its analysis area. Each has its own glossary, domain model, actors and numbering.
- **A reference across analyses** names the analysis, in the form a capability's decision is cited: `core:TERM-change`, `project-management:ACT-implementer`.
- **Per analysis:** the kinds' places and types, the stamp and validation.
- **Across the repository:** the friction checks are the backbone's, and read every place at once. So do work tracking's use cases. Whether ids may repeat across analyses is question 4.

## 4. The rule of logical consequence

A use case starts only from what is already true: what another use case made true, or what the environment gives. The maintainer chose the minimal form, one optional field and one check.

### The rule

For any project's analysis:

- **Each precondition** of a use case is a state another use case makes true, by its postconditions or a guarantee. Otherwise it is an assumption about the environment, with the record that admits it.
- **Followed back,** every precondition ends at the initial use cases, whose preconditions are all assumptions.
  - **In most projects,** they rest on an assumption such as "the system is deployed".
  - **A project that develops its own system** starts from developing it, as project-kit does.
- **A condition that holds only in some cases** is a variant's, not a precondition.
- **What it narrows:** DEC-001 point 1's precondition, "a state the system or an earlier use case made true".

**Its grounding:**

- **Cockburn's precondition** (*Writing Effective Use Cases*): what another use case has already set up.
- **Use-case contracts in a light form** (Nebut et al. 2006, and Ryser and Glinz's dependency charts), which link use cases through their conditions.
- **Set aside:** the contracts' formal-predicate form, as too heavy.

### The data

A use case's optional `after` lists, for each precondition, its producers. Any one of them is enough.

- **A producer** is a use-case id of the same analysis, `environment`, or the use case itself, as a release starts from the last.
- **The words:** the Preconditions part names the same producers, such as `**From UC-003:** …` and `**Environment:** … (record)`.
- **The Assumptions part** already holds what the environment gives, with its record. How the two parts share the environment is question 7.
- **No anchor.** `after` draws no anchor, since a use case naming itself, or a loop of producers, would be a cycle (COR-050 point 5). So a changed postcondition flags nothing, and a reviewer of that change reads what follows from it.

In a release use case, say `UC-059`, the planned ids of the map:

```yaml
after:
  - [UC-001, UC-064]        # a project holding the system: the source repository, or an install
  - [UC-059, environment]   # the last release, or the first version in the source repository
```

```markdown
**Preconditions:**

- **From UC-001 or UC-064:** the project holds the system.
- **From UC-059, or Environment:** the last release, or the first version in the source repository (ADR-059).
```

Install, `UC-064`, lies in `050-adopt`, after the release's `040-release`. Read literally, the check below refuses this entry, and some 58 entries like it (question 8).

### The check

One check, and nothing more:

- each producer resolves to a use case in force of the same analysis, or is `environment`
- the field and the words agree
- no producer lies in a later-numbered area folder

It reads only use cases that write `after`. It binds at the new rule's status, through a set of the project's own (DEC-001 point 1).

- **Generated:** the overview (#1805) draws the chain from `after`, grouped by area, leaving out implied arrows. #1804's record gains that picture.
- **Dropped:** the report on changed postconditions, the layer computation and the trace check.

### Its limits

The rule states its limits, since the maintainer asked whether it is naive.

1. **The link checks structure, not meaning.** A reviewer judges that the producer's postcondition makes the precondition true. The check proves no consistency.
2. **Real dependencies hold alternatives and loops.** So the list allows "any one of", the environment and the use case itself.
3. **"Environment" is no escape hatch.** Each assumption names its record, and a reviewer checks it.
4. **Dependencies form a partial order.** The numbers show one valid order.
5. **A generated picture** leaves out implied arrows, and groups by area.
6. **Splitting or merging use cases** leaves a list incomplete. The check cannot see it, and a reviewer must.

### Where the rules go

- **`SAN`, proposed, beside RS-SAN-008:** the rule of logical consequence, its limits and its check, and what a leading number means.
- **`ANA`, proposed:** project-kit's own choices. These are the numbering, the analyses it keeps and the core's five areas. Its scope also gains the view's type.
- **The one-way rule between analyses:** recommended for `SAN` (question 3).

## 5. What changes, and the order to build it

The work is staged, so nothing fails an adopter after upgrading.

### The upgrade path

- **Optional:** the domain model, `after` and several analyses.
- **When checks bind:** the new checks bind at the new rules' status.
- **The new type:** a project's own set must select it for `SAN` to reach views, as DEC-002's Implications say for its kinds. A project's own type of the same name is refused (COR-056 point 2), and the release says so.
- **Several analyses:** a project that moves to them revalidates each artefact it moves, in the same change.

### What the records refine

- **software-analysis DEC-001:**
  - point 1, the precondition, `after` and its words
  - point 2, several analyses, their layout and configuration, and the view's place and type
  - point 3, ids across a repository's analyses, and a move out (questions 4 and 5)
  - point 4, what a view anchors, and a core actor in a capability's use case
  - point 8, the readers point where an actor's needs span analyses (question 9)
  - point 12, the order
- **software-analysis DEC-002 point 2,** a requirement's numbering, as for use cases.
- **`SAN`:** the consequence rule, proposed. RS-SAN-005 gains the view, and RS-SAN-008 reads a view's diagrams and a capability's core terms. RS-SAN-003's actor and the validation behind it take a core actor.
- **`ANA`:** project-kit's choices, proposed.
- **COR-050 point 7,** if question 4 is taken: an artefact anchor on an id two artefacts share is ambiguous.

### DEC-001 point 12, refined

- **Step 1:** the glossary and the domain-model views, then the actors.
- **The areas** follow their numbered order, which `after` holds.
- **The rest of the order stays.**

### The order to build

1. **The foundation:** software-analysis DEC-001 points 1, 2, 3 and 12 refined, for the precondition, several analyses, their ids and the order. The `SAN` rule is proposed in the same change.
2. **The diagram records,** #1802 and #1804. #1804 gains the chain picture from `after`. #1805's overview holds it, and no views per concept.
3. **A record for the domain model,** the view kind. Several analyses are already in step 1.
4. **The build, one task after another:** several analyses, then `after` and its check, then the view kind and its skill, then #1805's overview.
5. **project-kit's core analysis, bottom-up:**
   - the move into `core/`, each moved artefact revalidated in that change
   - the glossary's cycles broken, then the domain-model views and the actors
   - the requirements (#1786, held), then the five areas in order, then the journeys
   - existing work realigned to this layout: #1685, #1712 to #1715, #1719 and #1720
6. **Each capability's analysis,** after the core stage it builds on.

`SAN`'s changes ride one major, with #1727 and #1806 (#1770 decision 12).

**What each step waits for:**

- **Step 1:** the answers to questions 2 to 5, 7 and 8.
- **Step 4:** the view kind's record accepted, with question 6 answered.
- **Step 5:** `ANA`'s choices accepted, and #1802's record before any page anchors a view's section.
- **Step 6:** the answers to questions 1, 9 and 10.

## Weighed and set aside

- **One file per concept, with relations and states as data, and generated views per concept:** more structure than the domain needs. Hand-drawn views come first (COR-007).
- **A form tying a definition to a broader-concept field:** dropped with the fields.
- **One domain-model file, a collection like the glossary:** some 65 sections are long to read, and conflict on every branch.
- **One entry per concept holding its names (ISO 704, TBX), with the glossary generated:** it withdraws the term kind.
- **Areas named by their goal, unnumbered, with the order computed:** a file listing never shows the order.
- **Layers computed from preconditions, as folders:** a layer moves whenever a precondition changes.
- **Areas named after the concepts they act on:** a concept's use cases span the chain, so such areas give no order.
- **A judgement rule alone, with no field:** it leaves the chain to each reviewer, and the overview has nothing to draw.
- **The full trace, with layers and a report on changed postconditions:** more than the order needs.
- **Conditions as formal predicates on concepts' states:** too heavy.
- **One analysis for the whole repository:** a capability could not move, and nothing would keep dependencies one way.
- **A component's analysis shipped with it:** an analysis is internal documentation for its developers (COR-049).
- **A capability's glossary copying the core's definitions:** two homes for one definition.
- **A capability's artefacts anchoring the core's artefacts:** the core's analysis never ships, so after a move they would anchor nothing.

## Review

The critic reviewed the revised note, and the architect the note revised for the critic. Every finding is taken below, into the design or as a question. No decision of 19 October was changed.

### The critic

- **Red flag 1, the note's own example failed its check.** A release's precondition has install, in a later area, as one producer, and the map gives that precondition to some 58 use cases. Taken as question 8, with the example kept to show it.
- **Red flag 2, nothing held the needs a core actor brings to a capability.** RS-SAN-004 asks a goal to be one of its actor's needs. Taken as question 9. Validation's resolving of the actor is now named as refined.
- **Red flag 3, the question on ids counted only anchors.** Taken: the question, now question 4, counts work tracking's ids, project-management's id pattern and a new concept on places (COR-056 point 7). Its recommendation moved to one numbering across a repository's analyses. The anchor lookup is now cited to the code, not to COR-050 point 2.
- **Gaps, each taken:**
  - **Numbering's two homes:** what a number means is general, and project-kit's form is `ANA`'s.
  - **The term's link as a stored reverse:** no field stores it now. The architect took it further (question 6).
  - **A renamed term** kills page anchors on its section. The cost is named.
  - **No home for the record anchors behind core terms:** a capability's own terms and its use cases carry them.
  - **Diagram labels:** RS-SAN-008's fenced-block exemption is named for amending, and the diagram is held to what its view states.
  - **The links' version lags the floor:** question 10.
  - **Names clashing across glossaries:** a capability's term never takes a core term's name.
  - **Refined points missing from the foundation:** DEC-001 points 3, 4 and 8, DEC-002 point 2, and RS-SAN-003 are listed.
  - **`after` details:** it draws no anchor, and a producer resolves to a use case in force.
  - **The move costs revalidations:** named for project-kit's move and for the upgrade path.
  - **The view's id has no prefix:** in question 4.
- **Weak reasoning, each taken:** question 7 now states each environment fact once. A view anchors only the terms it explains, and says why. The last set-aside line now gives the real reason.
- **Cuts, taken:** Domain-Driven Design appears once, and the precedent sentence is gone.

### The architect

The architect found the view kind's place in software-analysis right, and the upgrade path sound. It raised four conflicts with accepted records, which need the maintainer's authorisation.

- **A1, "between capabilities, only as an option" against COR-030.** software-engineering requires project-management. Taken as question 2.
- **A2, a move out breaks append-only ids** (DEC-001 point 3, project-management DEC-054 point 2). Taken as question 5. The move now cites COR-041.
- **A3, question 4 covered numbered kinds only.** Named ids collide too, and the lookup belongs to the backbone. Taken: the question now covers every kind, and recommends the core refinement of ambiguous anchors.
- **A4, the term's link stores the reverse of an anchor.** The note had cited DEC-002 point 7 for the opposite. Taken as question 6, and the citation is mended.
- **Fit issues, taken:**
  - **Question 10 had the release write a capability's file.** It now keeps the pin in `ANA` and in software-analysis's validation.
  - **Nothing marked a folder as an analysis.** The capability's configuration now lists the analyses, and the places match both layouts.
  - **Two misstatements:** the merge gate is project-management's, so the example of the core as an actor is now validation. The friction checks run across the repository, not per analysis.
- **Gaps, taken:**
  - the readers point (question 9), and revalidation records kept per analysis
  - a loop inside one area (question 8)
  - the costs of a changed core actor, and of the head's stage
- **Build order:** several analyses now have one home, step 1. "What each step waits for" lists the answers and acceptances each step needs.
- **Escalation: yes,** on A1 to A4, now questions 2, 4, 5 and 6.

### The critic's confirmation

One short round, at low effort, on the revision. It found no new conflict with an accepted record, and three slips, each mended:

- the Review section named the question on ids by its old number
- the tooling section stated question 4's recommendation as decided
- the questions' lead-in counted question 3 among the conflicts, though it is the choice left to this note

## For the maintainer

Each question gives a recommendation, in the order the build needs the answers. Question 3 is the choice the maintainer left to this note. Questions 2 and 4 to 10 come from places where a decision of 19 October, read as stated, meets an accepted record or another decision.

**All ten are answered, each as it recommends.** The maintainer's delegate answered them on 19 October, under the maintainer's standing delegation. Step 1 writes them into software-analysis DEC-001 and DEC-002, `SAN` and `ANA` (#1809). Each question's last line says where its answer lies.

1. **Adapters.** Confirm that each adapter may keep an analysis of its own, since an adapter is a component. Recommended: yes, on a capability's terms, once an adapter needs one (COR-007).
   - **Answered:** as recommended, in `ANA`'s RS-ANA-004. DEC-001 point 2 leaves to each project which components keep an analysis.
2. **Dependencies between capabilities' analyses.** The decision allows them only as an option. But a capability may require another (COR-030), as software-engineering requires project-management.
   - **Recommended:** an analysis builds on the analyses of the components its component depends on, required or optional. A required one is its environment, as the core is. An optional one is used "where it is installed".
   - **What follows:** the head's list, the versioned links and the record anchors serve any analysis depended on, not only the core's.
   - **Answered:** as recommended, in DEC-001 points 2 and 4, and `SAN`'s RS-SAN-010.
3. **The one-way rule between analyses:** general, in `SAN`, or project-kit's, in `ANA`? Recommended: `SAN`. Any project with several analyses meets it, and it follows the direction of a component's dependencies (COR-030). In `SAN` it reads without the core's name. An analysis names only analyses of components its own component depends on, and an optional one only as an option.
   - **Answered:** as recommended, as `SAN`'s RS-SAN-010.
4. **Ids across a repository's analyses.** "Its own numbering" lets project-kit hold several `UC-001`, and two analyses could each hold `TERM-gate` or an actor for the core. Three readers take an id across the repository:
   - **the anchor lookup,** which takes the first artefact with the id, so an anchor could silently reach another analysis's.
   - **work tracking,** which receives every use case under its id, an id naming one use case for good (DEC-001 point 8).
   - **project-management,** which reads that id as `UC-` and digits (DEC-054 point 1). A qualified `core:UC-001` would need a new version of the point's schema (COR-052 point 5).

   **Recommended:** ids unique across a repository's analyses, of every kind, so no reader changes.
   - **Numbered kinds:** one numbering of each across the repository. "Its own numbering" then means its own areas and views.
   - **Named kinds:** software-analysis's validation refuses an id two analyses share. A view's id takes a prefix, as every kind's does (DEC-001 point 3), such as `VIEW-records-and-rules`.
   - **The backbone:** an artefact anchor on an id two artefacts share becomes ambiguous, as a point or a slug two share already is (COR-050 point 7). It warns first, so nothing fails an adopter.

   **The alternative:** each analysis numbers alone, and the backbone reads an artefact as `<analysis>:<id>`. That adds a concept to places, which moves them into a functionality of their own (COR-056 point 7). It also changes work tracking's point and project-management.

   **Answered:** as recommended. DEC-001 point 3 and DEC-002 point 2 hold the ids. The view's prefix comes with the view kind's record (step 3), and the backbone's warning with COR-050 point 7.
5. **A capability's analysis leaving the repository.** Taking the folder away deletes cited artefacts, which append-only ids forbid (DEC-001 point 3). Issues cite its use cases, which work tracking's point promises to keep (project-management DEC-054 point 2). Their numbers could also be given again.
   - **Recommended:** the repository a capability leaves keeps each moved artefact as a withdrawn stub that says where it went. That uses withdrawal as it stands, and adds no concept.
   - **Answered:** as recommended, in DEC-001 point 3.
6. **The term's link to its view.** The decision gives a term a link to its concept's section. The link is the reverse of the view's anchor, which the records compute and never store (DEC-001 point 11, DEC-002 point 7). As body text it is the term's content, so renumbering a view or renaming its heading changes every term it explains.
   - **Recommended:** keep the link as a named exception, a copy for navigation that the stamp writes from the views' headings and the check holds equal. Record its cost: such a change flags whatever anchors those terms. Readers want the link where they read the term.
   - **The alternative:** compute the link where the glossary is shown, such as in the overview, and store none.
   - **Answered:** as recommended. The view kind's record carries it (step 3).
7. **The environment in a use case.** DEC-001 point 1's Assumptions part already holds what the environment gives, with its record. The decision also puts `**Environment:** … (record)` in the Preconditions part, so two parts could hold one fact.
   - **Recommended:** each environment fact is stated once. Alone, it sits in the Assumptions part, and `after` does not list it. As an alternative beside a use case, it sits in that precondition's line, as `**From UC-059, or Environment:**`. An initial use case then writes no `after`, and its Preconditions part reads `None.`.
   - **The alternative:** the Preconditions part takes every environment line, and the Assumptions part is retired. Every live use case would then need a migration.
   - **Answered:** as recommended, in DEC-001 point 1 and `SAN`'s RS-SAN-009.
8. **The check, where producers are alternatives.** "No producer lies in a later-numbered area folder" refuses an alternative that comes later, such as install for "a project holding the system". The map gives that precondition to some 58 use cases. The same alternative closes a loop, release to install to release, so "leaving out implied arrows" has no single answer.
   - **Recommended:** read the check as "each precondition has at least one producer in its own area or an earlier one". The overview reduces over those earliest producers, and draws the later ones dotted.
   - **And a seventh limit:** a loop of use cases inside one area, with no way out to the environment, passes the check. So nothing proves that each chain ends at an initial use case, and a reviewer judges it.
   - **Answered:** as recommended, in `SAN`'s RS-SAN-009 and DEC-001's rationale. The overview's dotted arrows come with #1804's record.
9. **A core actor's needs in a capability.** A use case's goal is one of its actor's needs (RS-SAN-004), and an actor carries its needs (DEC-001 point 1). A capability lists core actors by name only, and the core's analysis never names a capability's. So a capability's use case for a core actor has no need to meet. `ACT-developer` holds about 14 needs today that only capabilities meet.
   - **Recommended:** beside each core actor it lists, a capability's analysis states the needs that actor brings to it, and RS-SAN-004 reads them there. The core actor's needs that only a capability meets move to that capability's analysis.
   - **The readers point:** software-analysis gives each core actor once, with the needs every analysis states for it (DEC-001 point 8).
   - **Answered:** as recommended, in DEC-001 points 2 and 8, and `SAN`'s RS-SAN-004.
10. **The version of the links to the core's glossary.** A capability's backbone floor rises only when a change declares it (PRJ-002 D4), and a floor is project-kit's mechanism, not every adopter's (COR-014). A floor set before the core's analysis existed links to no file.
    - **Recommended:** `SAN` says only that the head links to the glossary of the analysis depended on. `ANA` pins project-kit's links to the capability's backbone floor, once in the head. software-analysis's validation warns where the head's version differs from the floor. The release never writes it.
    - **Before the core's analysis exists at the floor,** the head names the first release that holds it, and says why.
    - **Answered:** as recommended, in DEC-001 point 2 and `ANA`'s RS-ANA-006.
