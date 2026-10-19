---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-19
---

# Analysis concepts and order

## The question

How is an analysis built from its concepts? The maintainer decided on 19 October that a concept is not a term, that concepts explain the domain with diagrams, and that an analysis follows by logical consequence. This note designs that for software-analysis, for any project, with project-kit as the worked example.

It weighs six things, each with options and a recommendation:

1. the concept kind
2. term and concept, and the glossary entries merged on 19 October
3. the rule of logical consequence
4. areas, folders and numbering
5. concepts as living-docs' background
6. what changes, and the order to build it

The maintainer's decisions are at the end, in "For the maintainer".

## What the maintainer has decided

These bind the design. They are constraints here, not open questions.

- **Concepts are not terms** (19 October). The glossary lists terms, each pointing at its concept. "Define what concept is first."
- **What a concept is** (19 October, the definition he took):
  - one thing the domain deals with
  - described by what kind of thing it is, what it consists of, its relations to other concepts, the states it goes through and what is always true of it
  - anchored to the records that decide it
  - the concepts together form the domain model
- **Concepts use diagrams heavily** (19 October): "pure explanation of thoughts easy to read and understand for innocent reader". They are "good background for living docs".
- **Order by logical consequence** (19 October), as a general rule of building an analysis, to be written down:
  - each precondition of a use case is the postcondition of another use case, or an assumption about the environment
  - followed back, every precondition ends at the initial use cases
  - project-kit's analysis starts "from development of the pkit itself"
- **Folders** (19 October): he is unsure whether use-case folders carry numbers, since "everything came up from concepts".
- **An analysis is built bottom-up** (18 October), as a rule of the method: software-analysis DEC-001 point 12, on main. This note refines it.
- **Diagrams** (19 October): the 13 recommendations of the note on visual elements, taken as they stand (#1770, built by #1802 to #1807). Those that bind here:
  - a diagram is a `mermaid` fence with no styling, carrying `accTitle` and `accDescr` (its decisions 1 and 11)
  - a diagram is never a fact's home, and a page may anchor any record, artefact or code as the home of what it states (decision 2)
  - the generator reads front matter only (decision 3)
  - generated diagrams show on demand and in a generated overview, a held document of the analysis, and never inside an analysis artefact (decision 5)
  - a hand-drawn diagram in an artefact shows only what its artefact states (its piece 1)

## Where things stand

- **The glossary holds 65 terms.** 48 of them landed on 19 October (#1785). Each has a definition in ISO 1087's form, its broader kind and then what sets it apart, and anchors the records that decide it (software-analysis DEC-001 point 1).
- **Seven kinds, and no domain model.** DEC-001 keeps actors, use cases, journeys and terms, and DEC-002 adds three kinds of requirement. A new kind needs a decision of its own (DEC-001 points 1 and 11). The note on visual elements found that a domain model passes the analysis's membership test, since a change to the software can make it false, and left it waiting for a project that asks. The maintainer now asks.
- **A use case already splits what holds before it starts** (DEC-001 point 1). A precondition is a state the system or an earlier use case made true. An assumption is what nothing in the system secures, with the record that admits it. Both are prose. Nothing says which use case made a precondition true.
- **Point 12 orders the kinds, and the writer orders the areas.** An area is written after the areas it builds on, and areas that build on each other are written together. Which area builds on which is the writer's judgement. No rule holds it (DEC-001 point 12, "What the writer keeps").
- **RS-SAN-008, proposed, holds what the order leaves.** An artefact uses a domain concept only where a term defines it, by that term's name. A term's statement is its definition alone.
- **A tool reads front matter only** (DEC-001 point 1). A body's parts serve readers and the check.
- **The check may hold a part to front matter.** A journey's Steps part must match its `steps` field, by the form `steps-match-front-matter` (DEC-001 point 4).
- **Text the stamp writes from another artefact** is a precedent: a journey's step line copies a use case's title, and RS-SAN-008 reads it as that artefact's. So are a journey's use-case anchors, which the stamp writes into its front matter from its steps (DEC-001 point 4).
- **An anchor may name a section or the lead of an artefact** (COR-050 point 2). Such an anchor changes only when that part's text, or the artefact's own fields, change. A part opened by a bold label is no section.
- **A cycle of artefact anchors is an error** (COR-050 point 5).
- **A page's anchors ground every statement it makes,** analysis artefacts among them (living-docs DEC-001 point 3). An analysis artefact as the home of a page's fact comes with #1802.
- **#1804 leaves room for concept diagrams.** It builds the query that prints the analysis's diagrams, and decides nothing about the concept kind.

## The worked example: project-kit's chain

A working map of project-kit's use cases as a chain of preconditions was drawn on 19 October, from main at `b41cf6ec`. It is not part of this note. What it found bears on every item below.

- **One initial use case.** "Develop the methodology in its source repository" needs only two assumptions: the source repository, and Python with `uv`. Every other use case follows from it.
- **70 use cases in 12 layers.** A use case's layer is one more than the highest layer of the use cases its preconditions follow from. 58 can first run in the source repository, 4 ship the system out, and 7 need an adopter's project.
- **Ten environment assumptions.** They include git and GitHub, the harness, a CI service and the operating system's sandbox. No use case makes them true.
- **Five cycles, each broken by a fact:**
  - **The system develops itself.** Use cases need "a project holding the system". Install makes it true in an adopter's project, and install needs a release, which needs those same use cases. The source repository holds the system from the initial use case, with no release and no install (ADR-059). So that precondition has two producers, and the earlier one breaks the cycle.
  - **A capability judges its own change,** **the first required check,** **planning and revising the analysis,** and **each release starting from the last.** Each is broken by a precondition that holds only in some cases, or by an environment assumption.
- **Gaps it found:**
  - **Two needs no actor states.** Putting the tool on a machine at a release, and readying a repository's tracker for project-management. Use cases need both.
  - **Four preconditions nothing produces,** such as a capability from another repository, whose fetch is not built.
  - **Seven use cases on main read "None."** under Preconditions, but rely on what another use case makes true. Four of them rely on an area not yet written.
- **The plan's ten areas give no order.** Eight of them build on each other in one cycle, since four areas hold use cases at both ends of the chain. Moving eleven use cases between the existing areas, adding none, gives an order in five steps.
- **Layers make poor folders.** Layer 2 alone holds 18 use cases from seven areas, and a layer moves whenever a precondition changes.

The same reading finds cycles among the glossary's definitions, which point 12 already rules out ("a definition uses terms already defined"):

- **base and head** use change, and change uses base and head
- **anchor** uses artefact, and artefact uses anchors
- **answer** uses friction, and friction uses answer

RS-SAN-008 judges what a definition uses, not its order, so the cycles passed.


## 1. The concept kind

A concept is one thing the domain deals with. Its kind holds the maintainer's five descriptions, the records that decide it, and an explanation for a reader new to the domain.

A concept describes the domain, not the code. Its parts and relations are the domain's, never the classes or tables that build them, which belong to the solution (DEC-001 point 11).

### Its parts

What a tool reads is data, in front matter. What a reader reads is prose, in the body (DEC-001 point 1).

| Part | Data or prose | What it holds |
|---|---|---|
| `broader` | data | its broader concept, by id. Absent where the broader kind is a dictionary word, such as "file". |
| `consists-of` | data | the concepts it is made of, by id, each with how many |
| `relates-to` | data | each other concept it relates to, by id, with a verb phrase and how many |
| `states` | data | each state it goes through, the states it moves to, and the event that moves it |
| the lead | copied | its term's name in the heading and its term's definition under it, which the stamp writes (item 2), and a link to its view (below) |
| Explanation | prose | plain words for a reader new to the domain: what it is for, and how it fits. It may hold hand-drawn diagrams. |
| Always true | prose | what holds of it by the records that decide it, each with that record |

- **Sections, not labels.** The two prose parts are headed `## Explanation` and `## Always true`. So an anchor can name either one, or the lead, which holds only what the stamp writes. An anchor on the lead then changes only when the concept's data or its term's definition change, never on an edit of its explanation (COR-050 point 2).
- **The names.** `broader` is the thesaurus word for a broader concept, as SKOS uses it. `consists-of` avoids "parts", the word for a kind's parts. Both are the kind's own words, so RS-SAN-008 reads neither as a domain concept.
- **Always true, and requirements.** A concept states what holds of it by its records and is no part of its definition, such as "a rule has one status at a time" (COR-051 point 4). An obligation the system must keep, such as a business rule across use cases, is a functional requirement (DEC-002 point 1). Requirements come after concepts (point 12), so the requirement uses the concept's term, and the concept never names the requirement.
- **One home among concepts.** A fact belongs to the concept it is about. Another concept names that concept, and never states the fact again. So a decision record's page names the acceptance gate, and the acceptance gate's concept holds the condition.
- **States name events, not use cases.** Concepts come before use cases (point 12), so a concept names no use case. An event may be a concept of its own, such as install, which moves a project into holding the system. Linking a use case to the state it reaches waits for item 3's option C, since postconditions are prose a tool does not read.
- **Anchors.** The records that decide it, and the code that embodies it, as a term anchors today (DEC-001 point 4). Also the lead of each concept its `broader`, `consists-of` and `relates-to` name, which the stamp writes from those fields, as it writes a journey's anchors. So a change to what an earlier concept is flags the concepts built on it, and an edit of its explanation flags none.
- **Where it lives.** One file each, `CONCEPT-<slug>.md`, in a `domain-model` folder beside the use-case model. The folder is a place whose type is `software-analysis:concept`.

### The order inside the domain model

Point 12 asks that "a definition uses terms already defined". The concepts keep that order where they build on each other, and nowhere else.

- **What the order binds:** a term's definition, and a concept's `broader`, `consists-of` and `relates-to`. Each names only concepts before it. Each relation is listed once, on the later concept, and the reverse is computed.
- **What it does not bind:** a concept's `states`, its explanation and what is always true of it. They may name any concept of the model. What a concept is for, and the event that moves it, are often later concepts. A foundational concept such as change could not say what it is for otherwise.
- **How it is held:**
  - **The structure, by validation.** The anchors follow `broader`, `consists-of` and `relates-to`, so validation's refusal of a cycle holds their order (COR-050 points 5 and 12). States and prose draw no anchors.
  - **The definitions, by a reviewer.** A definition's uses of other terms are prose, so they draw no anchor, and no check sees a cycle between two definitions. The new judgement rule of item 3 holds it: no two definitions use each other, directly or through others. The base, anchor and answer cycles above are what it finds.

This refines point 12's step 1, whose "uses" covers every statement of an artefact.

### Its diagrams

**Generated, from front matter only** (#1770 decision 3):

- **The domain model:** a Mermaid class diagram, UML's notation for a domain model. A broader concept is a generalisation, `consists-of` a composition, and `relates-to` an association with its verb and how many.
- **A concept's states:** a Mermaid state diagram, drawn from `states`.
- **Where they show: one view per concept,** held in the overview's folder of held documents (#1770 decision 5, built by #1805). Each view draws the concept's neighbourhood both ways: its broader and narrower concepts, what it consists of, each concept related to it in either direction, and its states. The overview's index lists every concept with its view.
- **Why a view per concept:** 65 concepts in one diagram are unreadable, and one file of some 130 diagrams would conflict on every branch that edits a concept. A view changes only when its concept or a neighbour changes. It is drawn both ways, so a foundational concept's view shows what builds on it.
- **Never inside a concept,** as #1770 decided for every artefact. The concept's lead holds a link to its view, which the stamp writes from its id, so the link never changes.

**Hand-drawn, to explain a thought:**

- **Where:** in the Explanation section, as #1770's piece 1 allows in free text.
- **What it may show:** only what its concept states, and the concepts it names. A diagram is never a fact's home, so it adds no fact that the concept or its records do not state.
- **Its form:** a `mermaid` fence with `accTitle` and `accDescr`, and no styling.
- **What goes elsewhere:** a picture across several concepts, such as how a change becomes a release, goes on a living-docs page (item 5).

### Options

- **A. A kind of its own,** with the parts above, one file per concept in `domain-model/`. Generated diagrams show in one held view per concept, drawn both ways, and hand-drawn ones in its explanation.
- **B. A, but each concept's own diagrams generated into a part of its body,** from its own front matter. A reader opening the file on GitHub sees them there.
  - **What it refines:** #1770's line that a generated diagram never shows inside an artefact. That line's reason was another artefact's edit changing a body. A concept's own front matter is not another artefact.
  - **What it costs:** it can draw only one way, since its own data names only earlier concepts. So a foundational concept's diagram shows almost nothing. Each edit of its data also rewrites its body.
- **C. One domain-model file,** a collection like the glossary, each concept a keyed entry. One file of 65 sections, each with its explanation, is long to read and to review.

**Recommended: A.** A view drawn both ways shows a newcomer what a concept is for, which B cannot. A keeps the line #1770 drew, and a reader reaches each concept's diagrams in one click from its file. C loses the page per concept that a newcomer reads.

## 2. Term and concept

A term is a word. A concept is the thing it names. The glossary is the domain's terminology, and the concepts are its model.

### Options

- **A. One concept for each term, with the definition moved to the concept.** The term keeps only the word: its name, the names it replaces, and its distinctions. The glossary shows each definition as a copy the stamp writes from the concept.
  - **What it costs:** a term's `definition` is the writer's until its concept is written, and the stamp's after. RS-SAN-008, which reads a term's definition as its statement, moves to the concept.
- **B. One concept for each term, sharing its slug, with the definition kept on the term.**
  - **The term holds the word and its meaning:** its name, its definition, its example, the names it replaces and its distinctions, as today. It gains `concept`, which `pkit analysis new concept` writes when the concept is written, and which must name the concept of the same slug.
  - **The concept holds the model:** its broader concept, what it consists of, its relations and states, what is always true of it, its explanation, and the records that decide it.
  - **The copy:** the concept's lead shows its term's name and definition, which the stamp writes. A check holds them equal, as a journey's anchors are held to its steps.
  - **Kept together by a form:** where a concept has a `broader`, its term's definition opens with that concept's name, or a form of it. So the definition's first words and `broader` cannot part, and a script sees it.
  - **A term stands alone** until its concept is written. Where the analysis holds at least one concept, validation reports each term that has none, and never fails it.
  - **Withdrawing a term** withdraws its concept with it. Merging two terms keeps one, and its concept takes what still holds of the other.
- **C. Fewer, larger concepts.** A term names a concept, or one part, state or relation of a concept, and keeps its definition.
  - **What it gives:** about twenty pages for project-kit, where B gives 65.
  - **What it costs:** "concept" then means two things, what a term defines in RS-SAN-008's sense and a page of the domain model.
- **D. One entry per concept, holding its names, as terminology practice keeps them** (ISO 704, and the TermBase eXchange format). The concept carries its name and the names it replaces, and the glossary becomes a listing the stamp generates.
  - **What it gives:** no copies.
  - **What it costs:** the term kind is withdrawn. It can be staged term by term, but each converted term is withdrawn and kept as history in the glossary (DEC-001 point 3). So the glossary ends as a file of withdrawn entries beside a generated listing. It reaches DEC-001 points 1 and 2, RS-SAN-008 and `ANA`'s scope.
- **E. B, and a term may name a state, an event or an invariant of a concept** instead of a concept of its own, such as acceptance gate as a condition on a decision record. Fewer, fuller concepts, but each such term's definition sits inside another concept's data, and "concept" again means two things.

**Recommended: B.** The glossary keeps every term as it reads today, so nothing changes for a project that keeps terms alone. The concept adds what a term cannot hold: the model, its diagrams and its explanation. Each fact keeps one home: the meaning on the term and the model on the concept. The one fact they share, the broader kind, is held by a form. A has the same homes with the copy reversed, but a field that changes owner and a rule that moves. D is the cleanest end state, at the cost of withdrawing the term kind. C and E give fewer pages, at the cost of a word with two meanings.

**Its costs:**
- **One copy,** the term's name and definition in the concept's lead. A changed definition rewrites the lead, which flags the concepts built on it. That is right: they build on what the concept is.
- **Many short concepts,** such as head or base. Each view shows them in their neighbourhood.

### The glossary's entries

With B, each of the 65 terms, the 48 of 19 October among them, keeps everything it holds today. project-kit gives each its concept, in the concepts' order:

- **written by the stamp:** the concept file, its lead, and the term's `concept`
- **written by hand:** its broader concept, what it consists of, its relations and states, what is always true, its explanation, and the records that decide it
- **the cycles above broken:** one term of each pair is defined first, and the other's definition names it. For example, base and head become the commit a comparison starts from and the commit it ends at, and change names both.

**What changes in the rules:**
- **RS-SAN-008, proposed,** also reads a concept's prose as statements.
- **RS-SAN-005, proposed,** whose list of what each kind anchors is whole, gains a concept resting on its records, its code and the leads of the concepts it builds on.

**The six groups #1785 settled** read as the model's first cut: the whole and its ownership, the parts, records and rules, the checks, change over time, and work.

## 3. The rule of logical consequence

### The statement

The general rule, for any project's analysis:

- **Each use case follows from what is already true.** Each of its preconditions is a state another use case makes true, by its postconditions or by a guarantee it gives, in its minimal guarantees or to its other actors. Anything else it needs is an assumption about the environment, listed with the record that admits it.
- **Followed back, every precondition ends at the initial use cases,** whose preconditions are all assumptions. An analysis starts from them.
  - **In most projects,** the initial use cases rest on an assumption such as "the system is deployed".
  - **A project that develops its own system,** as project-kit does, starts from developing it.
- **A precondition may have several producers,** any one of which is enough. At least one must come earlier.
  - **Two use cases:** the source repository and an install both make a project hold the system.
  - **A use case or the environment:** a change in the working tree comes from a person's edit, or from an agent that builds it.
  - **The use case itself, or the environment:** each release step starts from the last release, and the first version stands in the source repository before any release.
- **A condition that holds only in some cases is no precondition.** It is a variant's condition.
- **Concepts follow the same rule** where they build on each other (item 1).

### The data

A use case's front matter gains `after`, an optional field. Each entry is one precondition's producers, any of which is enough: use case ids, and `environment` where an assumption may stand in.

```yaml
after:
  - [UC-001, UC-064]        # a project holding the system
  - [UC-033, environment]   # a change in the working tree
```

In the release use case, say `UC-059`, the last release is its own:

```yaml
after:
  - [UC-059, environment]   # the last release, or the first version in the source repository
```

- **The Preconditions part names them too.** Each precondition opens with its producers, such as `**From UC-001 or UC-064:** a project holding the system.` A form holds the part and the field to each other, as `steps-match-front-matter` holds a journey's.
- **An `environment` producer** is matched by an assumption in the Assumptions part, with the record that admits it.
- **What it refines in DEC-001 point 1:** a precondition narrows from a state "the system, or an earlier use case" made true to one another use case, or the environment, makes true. A condition that holds only in some cases moves to a variant. The hint of the Preconditions part changes with it.

### Friction on the chain

- **No anchors in the first build.** A changed postcondition can leave a precondition untrue, so the chain should carry friction. But a use case's parts are labels, not sections, so an anchor on a producer names its whole file. Anchoring each precondition's first producer would flag a use case on every edit of that producer. In project-kit, every edit of the initial use case would flag 58 use cases.
- **A report instead.** `pkit analysis check-numbers`, which compares a change with its base, also reports a change to a use case's postconditions or guarantees, with the use cases that follow from it. It reports and never fails. It runs where the project runs `check-numbers`, in its check gate, since `pkit validate` never runs it. The change's reviewer reads what it lists.
- **Anchors later,** once a use case's postconditions can be anchored apart from the rest of it, as a concept's sections can (item 1). Only the first producer of each precondition would be anchored. It comes earlier, so the anchors form no cycle.

### What the checks hold

Offline, from front matter and the Preconditions part:

- **Each producer resolves** to a use case in force, or is `environment`. This holds always, wherever `after` is written, as each of a use case's other actors resolves (DEC-001 point 4).
- **The part and the field agree,** and a part that reads `None.` goes with an empty `after`.
- **Every use case traces back to an initial one.** Taking each precondition at its earliest producer, and `environment` at the start, the check gives every use case a layer. A use case it cannot place fails, with the preconditions that loop.

The last two are declared under the new rule's `checks` in `SAN`, as RS-SAN-002's comparison is, and not in a kind's structure, which RS-SAN-001 holds. So they bind only once the new rule is accepted, through a set of the project's own, at its pin (DEC-001 point 1, "When it binds"; COR-051 point 7). A project that does not inherit `SAN` is not held to the method, and a use case with no `after` fails nothing.

**Computed and shown, never stored:** the initial use cases, each use case's layer, which area builds on which, and the order of the areas. Areas that build on each other are reported, never failed, so the project draws the line between them again or writes them together.

### What a reviewer judges

A new judgement rule of `SAN`, proposed beside RS-SAN-008, with the checks above as its checkable part:

- **The producer makes the precondition true,** by its postconditions or its guarantees. The check sees only that the ids resolve.
- **A precondition that no use case must make true** is an assumption, or has `environment` among its producers. One that nothing in the environment gives and no use case makes true is a missing use case or a missing need, as the tool on the machine and the tracker's bootstrap were.
- **Nothing the main path relies on is left out** of both parts.
- **A condition that holds only in some cases** sits in a variant.
- **The initial use cases are where the project's system begins.**
- **No two terms' definitions use each other,** directly or through others, since no check sees what a definition's prose uses (item 1).

### How it refines DEC-001 point 12

- **"Builds on" is computed where it can be.** Point 12 says today that the writer judges which area builds on which, and that no rule holds it. Where a use case writes `after` and the new rule binds, the check computes it from preconditions. Elsewhere the writer judges, as today. The rationale "Why a rule holds the result, and the writer the order" is rewritten with it.
- **Only preconditions order the areas.** Point 12 says an area builds on another where its use cases "rely on" what that area's use cases make true, which a variant does too. Refined, only preconditions count. A variant that relies on a later area's use case is written once that use case exists. Its cost: a reader of the earlier area meets a variant that names a later use case. In project-kit, planning names use cases of `analysis`, written later, only in a variant.
- **The order of writing stays the writer's.** Which file was written first is in no artefact, so the alternative "a rule that holds which area is written before which" stays not taken.
- **Step 1 becomes the terms and their concepts,** then the actors (items 1 and 2).
- **Brownfield candidates** (point 9) are traced back from the use cases the code shows, to the initial ones, as the worked example was.

### Options

- **A. A rule with a checkable part:** `after`, the checks and the reviewer's judgement above.
- **B. A judgement rule only.** The Preconditions part names producers in prose, and a reviewer follows them back. No field, no check and no computed order. The order of areas stays the writer's, and nothing draws the chain.
- **C. Conditions as states of concepts.** Each precondition and postcondition names a concept's state, and the check matches them. It is the most exact, and it would link each use case to the states it moves. But every condition becomes data, which DEC-001 point 1 keeps apart from the readers' text, and every concept's states must be complete first.

**Recommended: A, with C as a later refinement once concepts carry their states.** A gives the order as data, which the overview draws and the area order reads. B leaves the chain to each reviewer's patience. C waits for a project whose concepts are complete (COR-007).

## 4. Areas, folders and numbering

A use case's id is global and append-only (DEC-001 point 3), so it never shows an order. The question is what the folders show.

### Options

- **A. Areas named by their goal, with no numbers.**
  - **The cut:** areas are drawn so that they follow the chain, as the worked example's re-cut does.
  - **The order:** computed from `after`, and shown by a query and in the overview. The overview draws the order of the areas as one small diagram, then each area's use cases by layer, with the producers they need from outside it. A chain of 70 use cases in one diagram is as unreadable as 65 concepts.
  - **What moves:** no file, when the order changes.
  - **What it costs:** GitHub lists folders by name, so the file list never shows the order. Only the overview does. A re-cut also moves use cases whose goal the old name no longer fits, so an area may need a new name.
- **B. Numbered area folders,** such as `1-components/`. A file listing shows the order.
  - **What it costs:** each change of order renames folders, and links by path break. A new area between two renumbers those after it. Two areas written together need one number.
- **C. Areas named after the concept their use cases act on,** as "everything came up from concepts" suggests.
  - **What it costs:** a concept's use cases span the chain. A project's settings come at layer 1 and its install at layer 9. A capability is added at layer 2 and upgraded alone at layer 11. Such areas build on each other, and give no order.
- **D. No areas.** One folder, and the order only computed. Point 12 allows it, but 70 files in one folder hide what belongs together.

**Recommended: A.** It shows the order without renaming files, and keeps a folder stable. The concepts still name the areas: an area's name uses the glossary's term where one fits, such as `capabilities`, `change` or `release`. For project-kit, the five steps of the worked example's re-cut:

1. `components`
2. `agents` and `capabilities`
3. `change`, `decisions` and `work`
4. `analysis`, `docs` and `release`
5. `adoption`

The re-cut moves eleven use cases, each answering in the same change what its move raises (COR-050 point 3). Where the moves leave a name that no longer reads as its goal, such as the project's settings under `capabilities`, the area is renamed in the same change.

## 5. Concepts as living-docs' background

A concept explains the domain once. A page explains it to its own reader. The page must not become a second home for what the concept states.

### Options

- **A. A page states what a concept states, for its reader, and anchors the part of the concept that states it.**
  - **Its ground:** #1770 decision 2, which #1802 builds: a page may anchor any artefact as the home of what it states. A changed concept flags the page, and two statements that disagree break the rule on a fact's home.
  - **The part it anchors:** the concept's lead, for what it is and how it relates, or the section that states the fact, as a page anchors one point of a record. An anchor on the whole concept would flag the page on every edit of its explanation, which living-docs rejects for a summary of a home (living-docs DEC-001 point 3).
  - **What #1802 must give:** an artefact as a home works as a record does. The page may state the fact, and needs no link to it. Otherwise a page of the user space would need a link into the internal root.
  - **Its links:** a page of the technical space may link to the concept. A page of the user space anchors it and links nothing in the internal root, since user navigation never leads there (living-docs DEC-001 point 1). An anchor is no link.
  - **Its diagrams:** a page may draw a concept by hand, with the concept as the home of what it shows. Generated concept diagrams reach a page later, through the data point #1770 describes.
  - **Its kind:** living-docs ships reference and signpost pages. An explanation kind comes with the first page that needs one (COR-007).
- **B. The concept files are the background pages,** with the domain-model folder as a place of the technical space. Ruled out: a document of another component's type is that component's, never a page (living-docs DEC-001 point 1). The user space could not reach it either.
- **C. A page links to the concept, and states nothing of it.** Nothing is repeated. But a page of the user space cannot link into the internal root, and a page that must explain a concept to its reader cannot.

**Recommended: A, once #1802's record is accepted.** The concept stays the one home, and each page is held to it by its anchor. A page never becomes the home of a concept's fact.
- **living-docs stays independent.** Without an analysis, a page's facts keep their homes among records and pages (living-docs DEC-001 point 9).
- **`docs-author`'s guidance applies only where an analysis exists:** read the concepts a page touches first, and name each by its term.

## 6. What changes, and the order to build it

### What changes

**software-analysis's records:**
- **DEC-001 points 1 and 12, refined in place,** for the rule of logical consequence: the narrower precondition, `after`, the checks, the reviewer's part, and "builds on" computed from preconditions where it can be.
- **`SAN`:** the consequence rule proposed, with its checks.
- **#1804's record,** on the analysis's diagrams.
- **A new record on concepts:** the kind, term and concept, the layout, ids, anchors, the order inside the domain model, and the concept diagrams with their views. A new kind needs a decision of its own (DEC-001 point 11), and one topic takes one record, as #1770 decision 13 chose. It refines:
  - DEC-001 point 1, the kinds and their parts
  - DEC-001 point 2, the layout, the places and the type registry, which gains `concept`
  - DEC-001 point 3, the `CONCEPT-` ids
  - DEC-001 point 4, what a concept anchors
  - DEC-001 point 12, step 1
  - #1804's record, for the concept and state diagrams, and #1805's overview, for a view per concept
  - RS-SAN-005 and RS-SAN-008, both proposed
- **All `SAN` changes ride one major,** which accepts its proposed rules with #1727 and #1806 (#1770 decision 12).

**software-analysis's build:**
- `after`, its form, its checks, the report on changed postconditions, and the query of the order
- the concept's schema, structure and template, `pkit analysis new concept`, and the form that ties a definition to `broader`
- the views and the chain in the overview (#1805)
- `analysis-author`: a sub-procedure for concepts, and `build-analysis.md` and `use-case.md` updated for the initial use cases and `after`

**For adopters, nothing fails after an upgrade:**
- a term may stand without a concept
- `after` is optional, and the consequence checks bind only at the new rule's status
- the release says that a project's own set must select the new type `concept` for `SAN` to reach concepts, as DEC-002's Implications say for its kinds
- a project with a type of its own named `concept` is refused, as COR-056 point 2 refuses such a collision, and the release says so

**living-docs:** nothing beyond #1802's homes, and the guidance in `docs-author`. An explanation kind comes later.

**project-kit's own analysis:**
- its domain model, from its 65 terms, with the three cycles broken
- `after` on UC-001 to UC-013, mending the seven that read "None."
- the two needs the chain found, in the maintainer's own words (RS-WRITE-013)
- the areas re-cut as item 4 gives, then the requirements of #1786, then the areas in the chain's order from the initial use case, then the journeys, #1685 renumbered among them

### Options for the order

- **A. The foundation, then the diagram records, then the concept record, then the build, then project-kit's analysis bottom-up.**
  1. **The foundation:** DEC-001 points 1 and 12 refined, and the consequence rule proposed, in one change the maintainer accepts.
  2. **#1802 and #1804,** the diagram records.
  3. **The concept record,** which can then decide its own diagrams, citing only accepted records.
  4. **The build,** one task after the other, since each touches the kinds' structure, the validator and the stamp: first `after` and its checks, then the concept kind and its skill, then #1805's overview with the views.
  5. **project-kit's analysis:** its domain model, then #1786, then the areas in the chain's order, then the journeys.
- **B. project-kit's analysis first, by hand, and the capability after.** Hand-stamped artefacts break core rule 3, nothing checks them, and they are rewritten once the kind lands.
- **C. The consequence rule first, the concepts later.** The areas could start sooner. But they would use terms whose concepts are not built, against "everything came up from concepts" and point 12's order.

**Recommended: A.** It follows the sequence the maintainer agreed on 19 October: the analysis's foundation, then the diagram records, then the concept kind, the requirements and the areas in the chain's order. Until the concept record lands, this note is where the direction on concepts' diagrams is written. #1786 stays held until project-kit's concepts land.

## Where the recommendations fall short of the direction

- **"Concepts use diagrams heavily."** A concept's file holds only hand-drawn diagrams. Its generated ones are one click away, in its view. To meet it in the file: item 1, option B, which draws one way only.
- **"The glossary lists terms, each pointing at its concept."** A term may stand without a concept until one is written, so an adopter's glossary may point at none. project-kit gives every term its concept. To meet it everywhere: fail a term with no concept once a rule binds, at the cost of a breaking change for adopters.
- **"Each precondition is the postcondition of another use case."** The rule also admits a guarantee, the environment, and the use case's own last run, since the worked example's chain does not close without them.
- **Friction on the chain.** A changed postcondition is reported, not flagged, until a use case's postconditions can be anchored apart.
- **The order of the areas** is computed from preconditions only, so a variant may name a later area's use case.

## Review

The architect reviewed the first draft, and the critic the second. Each finding follows, with what the note did with it.

### The architect

The architect found the direction sound: a kind of its own, the consequence relation as data with a computed order, unnumbered areas, and the concept as a page's home. It raised one objection, and asked for the maintainer's authorisation on four points.

- **Objection, item 2: no migration can write a valid concept.** A hint left in is refused, and writing `None.` records a judgement nobody made. Taken. A term stands alone until its concept is written, and no migration writes concepts.
- **Concerns, item 1:**
  - **"Always true" overlaps the functional requirement** (DEC-002 point 1). Taken. A concept states what holds by its records, and a business rule stays a requirement. It is decision 2. The requirement uses the concept's term, and the concept never names the requirement, which comes later in point 12's order.
  - **"Which use case moves a concept is computed" had no front-matter source.** Taken. It now waits for item 3's option C.
- **Notes, item 1, all taken:**
  - a second check on concept cycles is dropped, since validation's refusal of a cycle holds the order
  - a concept describes the domain, not the code
  - the growth of the overview is stated as a cost, and answered by a view per concept
  - the type `concept` and a project's set are in item 6
- **Concerns, item 2:**
  - **The copies ran both ways,** so a rename changed the concept too. Answered by the critic's finding below: the definition stays on the term, and the one copy runs from the term into the concept.
  - **An alternative not weighed:** one entry per concept, holding its names, as terminology practice keeps them. Now option D. It is not recommended, since it withdraws the term kind.
  - **A copy in front matter is stored derived data.** No copy is left in a term. The concept's copy is in its lead, as body text.
  - **Withdrawing or merging a term** is now covered.
- **Concerns, item 3:**
  - **No anchors means no friction on the chain.** Weighed. Anchoring each precondition's first producer would flag a use case on every edit of that producer, 58 of them for project-kit's initial use case. So the first build reports a changed postcondition with what follows from it, and anchors wait until a postcondition can be anchored apart.
  - **Where each check binds.** Taken. A producer resolves always. The form and the trace are the new rule's checks, binding only at its status through the project's set.
  - **Breaking adopters.** Taken. `after` is optional, and nothing fails an adopter after upgrading. It is decision 8.
  - **It also refines DEC-001 point 1:** the precondition narrows. Taken. It is decision 6.
  - **The point 12 reversal** must be shown to the maintainer, with its rationale rewritten. Taken. It is decision 7.
  - **The rule read as project-kit's self-hosting** (COR-014). Taken. Most projects' initial use cases rest on an assumption such as "the system is deployed".
- **Notes, items 4 and 5, taken:**
  - the re-cut's moves owe answers
  - the chain is drawn area by area, since 70 use cases in one diagram are unreadable
  - item 5 waits for #1802's record, which must treat an artefact as a record is treated, with no link needed
  - `docs-author`'s guidance applies only where an analysis exists
- **Concerns, item 6:**
  - **The acceptance gate.** The concept record leaned on #1770's decisions, which no accepted record holds yet. Taken. The concept record now comes after the diagram records, and decides its own diagrams.
  - **The list of records was short.** Taken: RS-SAN-005, DEC-001 points 1 and 2, the type and the project's set are now listed. No breaking change remains, since nothing fails an adopter.
  - **The two build tasks share files.** Taken. They run one after the other.
- **Escalation: yes,** on the upgrade path, the narrower precondition, what is always true against requirements, and the point 12 reversal. Each is now a decision of its own: 2, 6, 7 and 8.

### The critic

The critic found three red flags, each changing a recommendation, and said decisions 8 to 10 stood.

- **Red flag 1, decision 1 narrowed "diagram-heavy, for an innocent reader".** A concept's file showed no generated diagram, and the order kept a foundational concept from saying what it is for. Taken, by its counter-alternative and its relaxed order:
  - **A view per concept,** held in the overview's folder, drawn both ways, so a foundational concept shows what builds on it. One file of 130 diagrams is gone.
  - **The order binds definitions and structure only.** A concept's states, explanation and what is always true may name any concept of the model.
  - **"Where the recommendations fall short of the direction"** is back.
  - Its option B, diagrams in the concept's own file, stays an option. It draws one way only, so a foundational concept's diagram would show almost nothing.
- **Red flag 2, decision 4: `after` could not express the worked example.** Several preconditions there have a use case or the environment as alternatives, and one release starts from the last. Taken. An entry may name `environment`, and a use case may name itself. The judgement rule now reads "a precondition that no use case must make true".
- **Red flag 3, decisions 2 and 3: the one example of "Always true" had three homes.** Taken in part:
  - **The example** is replaced by one that no definition states.
  - **One home among concepts** is now stated: a fact belongs to the concept it is about, and others name that concept.
  - **Its counter-alternative,** a term naming a state, event or invariant of a concept, is now option E. It is not recommended, since such a term's definition would sit inside another concept's data, and "concept" would mean two things.
- **Gaps, all taken:**
  - **States broke the order unchecked.** States now stand outside the order, and draw no anchors.
  - **Whole-file anchors were judged two ways.** A concept's prose parts are now sections. Concepts, terms and pages anchor its lead or a section, never its whole file.
  - **The narrower precondition had no producer for a guarantee.** A precondition may follow from a use case's postconditions or its guarantees.
  - **What variants rely on dropped out of "builds on".** Now stated as a refinement of point 12 and decision 7, with its cost.
  - **Staging did not deliver "nothing fails".** The form and the trace are declared under the new rule's checks, not in a kind's structure that RS-SAN-001 holds. A term keeps its definition, so no part is present only sometimes. COR-056 point 2 refuses a colliding type, and the note now says so.
  - **The reversal bound everywhere at once.** The writer still judges where `after` is absent or the rule does not bind.
  - **Nothing ran the postcondition report.** It runs where the project runs `check-numbers`.
  - **Item 4's costs** are now stated: GitHub lists folders by name, and a re-cut may need a new name.
- **Weak reasoning:**
  - **D was dismissed on its framing.** Taken. D can be staged, but each converted term stays as withdrawn history beside a generated listing.
  - **The scale of the overview was hidden.** Answered by the views.
  - **"Only a reviewer holds" the definition and `broader` together.** Taken. A form now holds them, which also makes the definition's staying on the term the better choice. Decision 3 moves from A to B.
  - **A report on every term without a concept is noise.** Taken. It reports only where the analysis holds a concept.
  - **"Four kinds" was wrong.** Seven, after DEC-002.

### The critic's confirmation

The critic read the third draft once more, since its findings had changed three recommendations.

- **Its three red flags:** resolved.
- **One new red flag: the note claimed a check held the order of definitions.** Validation's refusal of a cycle follows anchors, and a definition's prose draws none. So the base, anchor and answer cycles would still pass. Taken. Item 1 now says validation holds the structure's order and a reviewer the definitions', and the new judgement rule of item 3 carries it. Decision 4 says so.
- **A small point:** the example of `after` showed no use case naming itself. Taken, with the release use case.

## For the maintainer

Eleven decisions, in order. Each builds on the ones before it.

1. **The concept kind:** take item 1's A, a kind of its own in `domain-model/`, with its broader concept, what it consists of, relations and states as data, an explanation and what is always true as prose, and its generated diagrams in one view per concept, drawn both ways.
2. **What is always true of a concept:** take what holds of it by its records, and leave an obligation the system must keep to a functional requirement, which uses the concept's term.
3. **Term and concept:** take item 2's B, one concept for each term, sharing its slug, with the meaning on the term, the model on the concept, a form holding the definition to `broader`, and a term standing alone until its concept is written.
4. **The order inside the domain model:** let the order bind a term's definition and a concept's broader concept, what it consists of and its relations, held by validation for the structure and by a reviewer for the definitions, while a concept's states and prose may name any concept.
5. **The rule of logical consequence:** take item 3's A, a use case's `after` naming the use cases or the environment its preconditions follow from, a check that traces every use case back to an initial one, a judgement rule for the rest, and a report, not anchors, when a postcondition changes.
6. **What a precondition is:** narrow DEC-001 point 1, so that a precondition is what another use case makes true, by its postconditions or its guarantees, or the environment gives, and a condition that holds only in some cases is a variant's.
7. **Who judges "builds on":** let the check compute it from preconditions where `after` is written and the rule binds, and the writer judge it elsewhere, reversing point 12's sentence for those use cases.
8. **The upgrade path:** take the staged path, where nothing fails an adopter after upgrading, since a term may stand without a concept, `after` is optional and the consequence checks bind only at the new rule's status.
9. **Areas and folders:** take item 4's A, areas named by their goal with no numbers, re-cut to follow the chain, with the order computed and shown in the overview.
10. **Living docs:** take item 5's A, once #1802's record is accepted, so that a page stating a concept's facts anchors the part of the concept that states them, and never becomes their home.
11. **The order to build:** take item 6's A, the foundation first, then the diagram records, then the concept record, then the build, then project-kit's analysis bottom-up.
