---
id: DEC-001
title: Software analysis keeps actors, use cases, journeys and terms true as the software changes
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project needs a written account of *what its software must do*: who uses it, what they are trying to achieve, how they get there, and what the words mean. Without one, every new person and every agent reconstructs it from code, and every design is judged against a picture that exists only in someone's head.

Such an account decays silently. Code changes, the account does not, and nobody notices until a reader is misled or a design is built on something no longer true. This capability's membership test follows from that: **an artefact belongs here if a change to the software can make it false, and we want to find out when it does.**

The core layer supplies the machinery this needs:
- where a project's technical documentation lives (COR-049);
- anchors and friction, which detect when what an artefact rests on has changed (COR-050);
- rule sets, which hold the rules a component ships, each binding at its status and only through the project's own sets (COR-051);
- the rule-set reviewer, a core agent that judges a change against the rules that bind on it (COR-057);
- versioned dependencies between capabilities, required or optional (COR-030);
- artefact types, which name what an artefact is, so a rule set can select it (COR-056);
- connection points, through which components exchange knowledge and signals without depending on each other: data slots (COR-052) as one kind, addressed by role (COR-053).

This record decides what the capability keeps, in what shape, and where, one analysis per component. It also decides how an analysis stays true, in what order it is built, and how it meets the project's decisions and architecture.

## Decision

**The capability keeps four kinds of product knowledge (actors, use cases, journeys and glossary terms) as anchored artefacts, each carrying every part its kind ships, and keeps them true through revalidation: planned before code changes, and triggered by friction after.**

### 1. What it keeps, and in what shape

This point gives what each kind is for, and the distinctions behind its parts. Each kind's declared structure, below, holds the full list of its parts, their order, labels and forms.
- **Actors:** named roles that use the system, not personas. An actor says what the role is and does with the system, when it comes to the system and with what, and carries in its front matter the needs it brings.
- **Use cases:** one actor's goal and how the system fulfils it: the other actors who take part and what it must protect for each, what holds before it starts, what starts it, the main path and its variants, the state that shows the goal is met, and what the system still guarantees when it ends early or fails. What holds before it starts is split in two. A precondition is a state a use case makes true, by its postconditions or a guarantee, and no step checks it. An assumption is what the environment gives, which nothing in the system secures, and it names the record that admits it. A condition that holds only in some cases is a variant's, not a precondition.
- **Journeys:** one actor's end-to-end path across several of its use cases, including the seams between them where the path can break. Each step carries its own seams: what it needs from an earlier step, or from a use case outside the journey, and how that can break. Like a use case, a journey states its goal, its own variants, the state that shows the whole path succeeded, and what still holds when it stops before its end. It is a summary-level path through the system, not a map of the actor's experience.
- **Glossary terms:** the domain words, each with a stable id separate from its display name and a record of names it replaces, so that renaming a term does not break what cites it. A term's name is written as running text writes it, with no article, and in lower case unless it is a proper name. Its definition is a phrase that could stand in for the term, in the form terminology standards give a definition (ISO 1087 and the ISO/IEC Directives, Part 2): its broader kind, then what sets it apart. A term also gives an example, and the words it could be confused with and how each differs. The names it replaces are only those it carried in the analysis or in an accepted record; a working name that now means something else is one of the words it could be confused with.
- **Domain-model views:** a few views beside the glossary, written by hand, one for each group of related concepts. A view explains each concept of its group in words, and draws how they relate. A term a view explains links to the view's section on it (refinement per [software-analysis:DEC-004-domain-model-views]). Elsewhere in this record, a view named alone is an architecture view.

A user story, in the sense of a need stated in one sentence, is an actor's need and a use case's goal, not a separate artefact. The hints the capability ships ask for each need, and for the goal of a use case or a journey, in the actor's own voice: one sentence that starts with its verb, or with *Never* and the verb. A project that prefers another voice replaces those hints.

**What makes a precondition true.** Each precondition names its producers: every use case in force of its analysis that makes it true. Any one of them is enough.
- **A producer** is another use case of the same analysis, or the use case itself, as a release starts from the last release.
- **A new producer.** The change that adds a use case, or splits one, names it among the producers of each precondition it makes true.
- **The environment, once.** An environment fact alone is an assumption, stated in the Assumptions part only. Where it is an alternative to a use case, it is stated in that precondition's line instead, with its record.
- **The words.** Each line of the Preconditions part opens with its producers, such as `**From UC-003:**` or `**From UC-059, or Environment:**`.
- **The data.** A use case's optional `after` lists, for each precondition in its order, its producers: use-case ids, its own id among them, and `environment`. Where it is written, it names the producers its words name. An entry never names `environment` alone.
- **No anchor.** `after` draws no anchor. A use case that names itself, or a loop of producers, would close a cycle (COR-050 point 5).
- **Initial use cases.** A use case that needs no other one has no precondition. It writes no `after`, and its Preconditions part reads `None.`. Followed back, every precondition ends at such use cases, or at the environment beside a producer.
- **What holds it.** A judgement rule of `SAN`, the rule of logical consequence, holds this, with the order of the areas (point 12). Its *How* says what a check of `after` can hold, and the limits a reviewer judges.

**A kind's structure.** Every artefact and every record carries every part its kind ships, and a part with nothing to say reads `None.`. Which parts those are is the kind's *structure*, declared once as data. An artefact's structure binds where the capability's format rule binds, and a record's is checked always. A project may add to an artefact kind's structure, but never relax a kind's.
- **Declared once, as data.** Each kind, the revalidation record (point 6) among them, declares its structure in data whose schema this capability ships. A structure lists the parts of the kind's body in their order, each with a permanent id, a label, a hint and an example. It also gives the forms a script checks in a part or a front-matter field, and the hint of each front-matter field a writer fills. For the glossary, a collection, it covers each term's section and the file's head. The body of the kind's template is rendered from the structure and shows exactly it; the template's front matter is written by hand and held to the kind's schema. Nothing reads a structure out of a template's text.
- **Hints.** Where the stamp leaves a part or a field for a writer to fill, its hint is the placeholder, one marked line that says what goes there. A hint left in is refused as any placeholder is, on every artefact and record and whatever a rule's status. The check's messages repeat the hint. A hint is advice: what binds is a part's presence, its order and its form. A tool takes data from an artefact's front matter only: a body's parts serve readers and the check, never another tool.
- **What every kind asks.** Every part a kind ships is present in every artefact or record of that kind, and wherever the structure binds, a missing part is an error. A part with nothing to say reads `None.`, where its structure allows it, so a script tells a part considered from a part forgotten. A project's own additions are no shipped parts: each is optional unless the project marks it required.
- **When it binds.** The capability's method rule set, `SAN` (COR-051 point 6), holds a format rule: an analysis artefact carries its kind's declared structure. `SAN` takes no scope, so every route to it starts at a set of the project's own, and its accepted rules bind only where such routes lead (COR-051 point 7). The check takes where they bind from the backbone's one answer, and holds an artefact to its structure only where the format rule binds on it. A glossary's head belongs to no term, but it is part of the term kind's structure. So the check holds the head to that structure wherever the format rule binds on a term of its file, and nowhere else.
- **A set of the project's own.** A set through which `SAN` binds is the project's own (COR-051 point 6). A scope that selects by the capability's types (point 2) reaches the analysis's artefacts wherever they lie. Such a set's pin decides when a new major of `SAN` starts binding through it, since no rule binds through a pin behind its set (COR-051 point 7).
- **The rule's checkable part.** An artefact's structure is the format rule's checkable part, beside it as a schema is (COR-051 point 1), and no part of the rule's content. So changing a structure leaves the set's version alone, and a change that fails an artefact the check passed before is a breaking change of the capability. An artefact's structure binds at the rule's status: under any status but accepted, the normal check reports nothing of it (COR-051 point 4). A kind's schema checks its front matter always, whatever the rule's status and whether or not the rule binds there.
- **Revalidation records.** A revalidation record is a held document, not an artefact (COR-050 point 1), and a scope selects artefacts alone (COR-051 point 2). So no route leads from a record, and no rule binds on one (COR-051 point 7). The capability checks a record's structure itself, always, as a kind's schema checks its front matter. The record's structure is the capability's own, as its schema is, and no rule's checkable part. A change to it that fails a record the check passed before is a breaking change of the capability.
- **Never silent.** The check's summary counts the analysis artefacts no rule of `SAN` binds on. Where the analysis holds artefacts and no rule of `SAN` binds on any of them, validation says so, and why. While no rule of `SAN` is accepted, it says so at the severity that reports without judging. Once one is, it warns (COR-055 points 4 and 5).
- **A preview on request.** A check previews a proposed rule on request, as if it were accepted, and never fails on what it previews. A preview finding takes the severity that reports without judging, labelled `preview` (COR-055 point 4).
- **What a project may change.** A project may relabel a shipped part, and replace the hint and example of a part or a field, with no rule, since a hint binds nothing. It may also tighten a structure, by adding parts or by requiring more of it, in data of its own in the capability's project tier. Each tightening names the project rule that asks for it, and binds at that rule's status and at the format rule's. It never relaxes a shipped structure: it does not drop or loosen a shipped part, or reorder the shipped parts. Nor may it invent a form, or add a kind, which needs a decision of its own (point 11). A part's id is permanent once shipped, retired and never renamed, as a rule's id is (COR-051 point 3). A tightening applies to an artefact only where the rule that asks for it binds. No rule binds on a revalidation record, so a project tightens no record's structure. The schema of the project's data refuses a tightening of the record kind until a rule set can reach a held document. In a domain-model view, a project adds labels, never a heading (refinement per [software-analysis:DEC-004-domain-model-views]).
- **Chosen at adoption.** Adopting the capability includes choosing each kind's parts. A project reviews each kind's shipped structure, and keeps it, relabels it or, for an artefact kind, adds parts of its own. A shipped part it finds wrong is a change it proposes to the capability. The shipped structure is a starting point a project reviews, never a default it skips.
- **When a structure changes.** Live artefacts, every artefact in force, describe the system and its domain as they are, so they are always migrated to the current structure. A revalidation record is the log of a revalidation that happened: it stays as written, and is checked against the structure in force when it was written. A withdrawn artefact is history too, and the check holds it to no part or form that came after its withdrawal.

**Diagrams.** A part may hold a diagram, written as a Mermaid fence, that shows only what its own artefact, or an analysis artefact it anchors, states. No kind ships a part for one, and no diagram is a fact's home. The capability's diagrams of the analysis's relations are drawn from front matter, and never stored in an artefact (refinement per [software-analysis:DEC-003-analysis-diagrams]).

### 2. Where it keeps them

Everything lives under the project's internal documentation root (COR-049), in an `analysis` folder. The folder holds one analysis for each component that keeps one (below). Each analysis is laid out after a use-case model (refinement per [software-analysis:DEC-002-analysis-requirements]):
- the glossary is one collection file, serving everything;
- the domain model is a folder of domain-model views, one file each (refinement per [software-analysis:DEC-004-domain-model-views]);
- the use-case model holds a folder of actors, one file each, a folder of use cases (optionally grouped by functional area), and a folder of journeys;
- revalidation records are kept in a folder of their own;
- a generated overview of its diagrams is kept in a folder of its own (refinement per [software-analysis:DEC-003-analysis-diagrams]).

**A kind with many files gets its own folder; a kind with one file is a file.** Folders appear only when something goes into them.
- **Numbered areas.** An area's folder name may open with a number, such as `010-`. The number gives one valid order in which the areas build on each other, never their importance (point 12). It is no part of any id (point 3).

- **Location.** The `analysis` sub-path is declared in the capability's package metadata. Its location is recorded on first use in the capability's own project configuration, as the documentation-roots record requires (COR-049). A later change of root therefore never moves an existing analysis.
- **Places.** The capability declares the glossary, the domain model's folder, actors, use cases and journeys as places holding anchored artefacts (COR-050, refinement per [software-analysis:DEC-004-domain-model-views]). Revalidation records describe an act and are not anchored artefacts, so their folder is not a place: the capability declares it as a folder of held documents (COR-050 point 1), so the records are listed as this capability's and no place reads them as artefacts. The overview's folder is held in the same way (refinement per [software-analysis:DEC-003-analysis-diagrams]).
- **Types.** Each place gives its artefacts a type (COR-056). So a rule set selects the analysis's artefacts by what they are, without naming where they lie.
  - **The type registry.** The capability's type registry, in its package metadata, declares one type for each kind of anchored artefact. They are `actor`, `use-case`, `journey`, `term` and `domain-model-view`, each with a description (refinement per [software-analysis:DEC-002-analysis-requirements] and [software-analysis:DEC-004-domain-model-views]). A scope names them `software-analysis:actor` and so on.
  - **Each place's type.** The actors' place gives `actor`, the use cases' place `use-case` and the journeys' place `journey`. The glossary gives its entries `term`, and the domain model's place gives `domain-model-view` (refinement per [software-analysis:DEC-004-domain-model-views]).
  - **No kind field.** No type names a kind field. The capability's check holds every file in a place to that place's kind, so no kind field needs to gate the place's type (COR-056 points 2 and 4).
  - **No project place.** None of these places admits a project place. The capability checks only the artefacts in its own places, so a project place would give its types to files the capability never checks.
  - **No type for a record.** A revalidation record is a held document, so it has no type (COR-056 point 1).
- **Surface.** The capability declares no surface by default, since it cannot know a project's code. The project declares which paths its analysis ought to cover, in the friction key of its backbone configuration (COR-050).
- **Ownership.** The artefacts live outside the capability's own subtree, so uninstalling the capability never removes them.
- **Across analyses.** The places are the capability's, whatever the number of analyses. The core's friction checks read every place at once, and so does work tracking's use-case point (point 8).

**One analysis per component.** In this point, a component is a part of the project's system that is developed and versioned on its own. A methodology's core and each of its capabilities are such components. A component may keep an analysis of its own, which describes it alone. Which components keep one is the project's choice.
- **Where.** An analysis lives in the internal documentation of the repository where its component is developed. It never ships with the component, so whoever receives the component receives no analysis.
- **The layout.** A project with one analysis keeps it at the `analysis` folder's root. Several analyses each take a folder named after their component, which holds the layout above. So a project that adds a second analysis moves the first into its own folder. The places match both layouts.
- **What marks an analysis.** Where a project keeps several, the capability's project configuration lists them, each with its folder and the analyses it builds on. Validation then refuses an artefact in a place that no listed analysis holds. A project with one analysis needs no list. The same configuration records the `analysis` folder's location (above).
- **Its own.** Each analysis has artefacts of every kind of its own, its own areas and its own revalidation records. The ids of its artefacts are unique across the repository (point 3).
- **A reference across analyses** names the analysis by its component's name, in the form a capability's decision is cited, such as `core:TERM-change`.
- **Moving in.** Each artefact a project moves into an analysis's folder is revalidated in the same change (COR-050 point 3).
- **Moving out.** A component that moves to a repository of its own takes its analysis's folder with it (COR-041). What the repository it leaves keeps is point 3's.

**Dependencies between analyses follow the components'.** An analysis builds on the analyses of the components its component depends on, required or optional. It names no other analysis.
- **Where they are read.** Where the components declare their dependencies, as a capability does in its package metadata (COR-030), validation holds the configuration's list to them. Elsewhere, the configuration's list is the project's statement of them.
- **A required one** is its environment, as a methodology's core is for each of its capabilities, or a library for the application built on it. What it provides is stated as assumptions, each naming the record that admits it.
- **An optional one** is used only where its component is present, and the analysis works without it.
- **The head.** The head of its glossary lists what it takes from each analysis it builds on: the area it builds on, the terms and the actors. A term or an actor is listed by name, with a link to its home in that analysis. No definition is copied.
- **As data.** What the head lists is data in the glossary's front matter, since a tool reads data only there (point 1). That is each analysis it builds on with the version its links name, the terms, the actors and the needs beside each actor. The check holds the head's text equal to that data.
- **An actor's needs.** Beside each actor it lists, the analysis states the needs that actor brings to it. A need of that actor that only this analysis meets lives here, not in the actor's own analysis.
- **A component as an actor.** A component it builds on may trigger its own. That component is then an actor this analysis defines, under an id of its own (point 3). An example is a core's validation that runs a capability's check.
- **No clash.** A term of its own never takes the name of a term its head lists.
- **The links' version.** Which version of the other analysis a link names is the project's choice. Where the component declares the lowest version it needs of the one it depends on, the capability's validation warns where a link names another.
- **Anchors.** Its artefacts anchor the records behind what it takes from another analysis, never that analysis's artefacts (point 4).
- **Fields across analyses.** Of the fields that the check holds equal to artefact anchors, only those that name actors may name another analysis's artefact (point 4). Every other such field names artefacts of its own analysis alone, such as a journey's steps.
- **What another analysis provides** is an assumption, which names the record that admits it. A requirement that no record backs, such as one that binds the whole system, is named by its id with its analysis, such as `core:REQ-007`. That name is no anchor.
- **What holds it.** A judgement rule of `SAN` holds that an analysis names only the analyses its component depends on.

The exact layout is in the capability's README, and each kind's parts are in its declared structure (point 1). The friction block — anchors and revalidation — follows the core schema, inside the methodology's container in each artefact (COR-050, COR-053).

### 3. Identifiers

Use cases and journeys are numbered within the repository (`UC-NNN`, `JRN-NNN`), independent of any grouping. Moving a use case between areas never changes its id, and nor does an area's number. Actors and terms are keyed by stable ids, an actor's naming its file and a term's its entry in the glossary, with distinct prefixes (`ACT-` for actors, `TERM-` for terms), so that no two artefacts in the analysis share an id. A domain-model view's id is `VIEW-` and the slug its file's name gives after its number (refinement per [software-analysis:DEC-004-domain-model-views]). So a domain-model view given another number keeps its id.
- **Across a repository's analyses.** No two artefacts of a repository's analyses share an id, of any kind. Each numbered kind has one numbering across them, and the capability's validation refuses an id that two analyses share. So each reader of an id across the repository reads one artefact, as with one analysis: an anchor, and work tracking's use-case point (point 8). Each analysis numbers its own areas, never its own ids.
- **Leaving the repository.** The repository a component leaves keeps each artefact of its analysis as a withdrawn stub, which says where the artefact went. So whatever cites one of its ids keeps a true reference, and the id is never given again.
- **Append-only.** An artefact is withdrawn, never deleted, and its id is never reused: once settled, an id names one artefact for good. There is one exception, and only the project makes it; no tool infers it. Artefacts that nothing cites — a pilot abandoned before anything cited it, say — may be removed from the default branch, and the project may then name them; their ids are free again. Nothing else frees an id. Something cites an id when it names the artefact by that id and expects the analysis to answer for it; history fixed at a commit, such as a commit message, does not.

  Inside a use case, steps are numbered and variants are lettered after the step they branch from. Both are append-only too, because journeys and evidence cite them. A check compares each use case with the default branch's, and reports a step or a variant renumbered or removed.
- **Parallel work.** When two lines of work number a new artefact the same, the first to reach the default branch keeps the number. A check that compares the branch with its base reports the collision, and the other renumbers before merging. A new number is given past what the default branch holds, and past any base the stamp is named, while a collision is judged at the merge at hand — against the base of that comparison, an integration branch included (refinement per COR-054, point 3).

### 4. Every artefact says what makes it true

Each carries anchors and a revalidation in the sense of the anchors-and-friction record (COR-050). Anchors run in one direction only, so they never form a cycle. The analysis anchors the decisions it relies on and the architecture views that realise it. Neither a decision nor an architecture view anchors the analysis (point 11). Each kind anchors as follows (refinement per [software-analysis:DEC-002-analysis-requirements]):
- Actors and terms anchor to where the software or a decision embodies them. An actor with no such anchor is reported as unanchored, which is not an error.
- Use cases anchor to their actor and to each other actor they involve, as artefact anchors. They also anchor to the code they exercise and the decisions they rely on, those that answer them included (point 11). They anchor to each architecture view that realises them too. The other actors are listed in the use case's front matter, so a check resolves each to an actor.
  - **An actor of another analysis,** one the use case's analysis builds on, is named with that analysis, such as `core:ACT-developer`. Validation resolves it against the actors that the head of its analysis's glossary lists from that one (point 2). The use case anchors the records behind that actor, not the actor. A journey, and a requirement in its `actors`, name and anchor such an actor in the same way.
- Journeys anchor to their actor; to the use cases they pass through, and to each use case outside the journey that a step relies on; and to the code and decisions at the seams between them. A journey's ordered list of steps, and its list of the use cases it relies on, are the source. Its use-case anchors are written into its anchor field from the two by the capability's stamp and check, and validation requires them to match, so the friction check sees them and they cannot drift apart.
- Domain-model views anchor each term they explain, as artefact anchors, and each record their statements cite or apply. Each one's list of the terms it explains is the source, and validation requires its term anchors to match it. Nothing in the analysis anchors a domain-model view (refinement per [software-analysis:DEC-004-domain-model-views]).
- Across analyses, only record anchors run. An artefact anchors the records behind what it takes from another analysis, never that analysis's artefacts. So a term whose definition names a term of another analysis anchors the records behind that term. A use case anchors the records its assumptions name. Where the other artefact anchors no record, nothing is anchored in its place.

A changed actor flags the use cases and journeys that anchor to it, and a changed use case flags the journeys that pass through it or rely on it. Friction is reported in that order. Revalidation is this capability's name for the act the core record calls by the same name; recording it on the artefact — its `at`, its outcome and any deferrals — is what clears friction (COR-050).

### 5. Revalidation

A **revalidation** is one review of some artefacts against one version of the system: a proposed design, or the actual code. It is an act, repeated whenever something triggers it:
- **planned**: a change is proposed, before code;
- **drift**: friction on a pull request;
- **scheduled**: friction found by the whole-repository check;
- **close**: a pull request that changes artefacts, or their anchors, lands;
- **onboarding**.

It ends, for each artefact, in one of these outcomes:
- it **holds**;
- **the analysis was stale**: the change was intended, so the artefact is updated;
- **the code regressed**: the artefact still describes what is wanted, so a defect is reported rather than the analysis rewritten to match;
- **a gap was found**: behaviour exists that nothing describes, or a description has no behaviour.

These four outcomes map onto the core record's two (refinement per COR-050): *holds* and *the code regressed* are recorded as `unchanged`, with the justification saying why the description stands — for a regression, naming the defect reported; *the analysis was stale* ends in `updated`; *a gap was found* ends in `updated` where the artefact itself changed, and in `unchanged` — the justification naming the gap and the artefact that fills it — where the gap is closed by a new artefact. Friction an agent or person chooses not to resolve yet is a core deferral, with its reason, not an outcome. Whoever performs the revalidation (a person, or an agent) records it on the artefacts it covered. An agent proposes the outcomes. Where "stale" versus "regressed" is ambiguous, a person decides before any revalidation is recorded. The analysis is never silently rewritten to match broken code.

When a person starts the capability's agent, it proposes the outcomes to them. It is also the fixer of the capability's types (point 8), so a command may start it where the project granted it. Nobody can answer it in such a run, so an artefact it finds ambiguous waits there with its question for a person. It judges there only through the capability's own reading of the change, as in a session. Where the run cannot make that reading, it judges nothing, and says why. Each answer it proposes in such a run waits as data until a person decides it (refinement per [project-management:DEC-056-drift-fixers]).

### 6. Records only when there is something to say

A revalidation that is planned, or that finds a gap or a regression, leaves a record in the revalidations folder. The record names the change that carried it (a tracked work item, a pull request, or a range of commits on the default branch), the trigger, the artefacts covered with their outcomes, and the gaps. Each gap is labelled with the artefacts it affects, and says what resolved it or carries its fix. A check holds the gaps to the outcomes: every artefact whose outcome is a regression or a gap is named by a gap, and every gap names an artefact the record covers. Records cite artefacts by id, including withdrawn ones, and are named by date and subject rather than numbered, so parallel work cannot collide. A routine revalidation that finds everything still holds writes no record: the artefact's own revalidation block, with its outcome and justification, is the record.

**What a planned record reviewed.** A planned record also names where the design it reviewed stood, in its front matter as `reviewed-against`. Each source of the design is named by what it is, its link where it lies outside this repository, and its version. The version is a pointer to the text reviewed, never a version number: the capability's artefacts and records carry no declared versions.
- Text in a repository is pinned by a commit its default branch holds, or, in this repository, by the change the record lands in, whose commit is found from the history as a revalidation's is (COR-050 point 3).
- Text in a tracker is pinned by its link and the time it was read.
- A pull request's head is never a pointer, since a rebase loses a head reviewed mid-way. Nor is any other commit the default branch does not hold, since a squash leaves a branch's commits off it (COR-009 point 1).

Validation checks the pointers' form. This record puts the check of where each commit sits outside validation (COR-055 point 1), because the pointers are provenance, not a gate. That check runs offline, and reports each commit of this repository that the default branch does not hold. A commit it cannot place, beyond a shallow clone's history say, it reports as unknown, never as a failure.

### 7. Revalidation is not testing

Revalidation asks whether *the description* is still true of the software, and usually fixes the description. Testing asks whether *the software* still does what the description says, and fixes the software. The capability owns revalidation. It does not run the software.

The capability provides the **analysis role** and, under it, accepts a data point, `<methodology>::analysis:revalidation-evidence` (refinement per COR-053), for executed results that confirm or refute an artefact at a commit:
- its schema is a companion schema the capability ships, named after the point (COR-052). At version 1 it has one entry per result, keyed by three parts — the artefact, the commit and the **check** — and holding the result and what was run. The check names one thing that was run against the artefact — a test, a scripted walk-through — and keeps that name from commit to commit; a filler gives each result it reports for one artefact at one commit a check of its own. A capability's checks open with the capability's own name, and a project file's with `project`. So two fillers' results for one artefact at one commit stand side by side, and only two that claim one check collide, which the project settles (COR-052 point 4). The opening name is a convention: where the capability's validation reads the point it warns on a capability's check that opens with another name, and never refuses, because the project replaces a capability's entry by writing one under that capability's check;
- its policy is `union`;
- no default takes part;
- its inert policy is `fallback`, because the evidence advises and does not gate.

The slots record (COR-052) allows three kinds of filler: a project file, a capability, and the provider's default. Here, a capability fills it (a later testing capability, or one that reads the test results the project already produces), or a project file records results, and no default takes part. Evidence **informs** a revalidation: a passing result is support for "holds", and a failing one is a regression with proof attached. It never replaces the revalidation. Only a revalidation or a deferral recorded on the artefact clears friction (COR-050). A revalidation record keeps a copy of each entry it drew on. A routine revalidation that writes no record (point 6) keeps none: its justification on the artefact says in its own words why the description holds, and naming a result is not a justification. Evidence kept on the artefact itself is not decided here (point 11).

### 8. What it contributes to others

The capability contributes to the documentation role's readers point, `<methodology>::documentation:readers`, by mapping its actors and their needs onto that point's shape (refinement per COR-053). It gives each actor once, with the needs every analysis states for it. Those are the needs its own analysis gives it, and those each analysis that lists it states beside it (point 2). It contributes to the work-tracking role's use-case point, `<methodology>::work-tracking:use-cases`, every use case the default branch holds, withdrawn ones included, each under its id. Once settled, an id names one use case for good; the only id that later names another is one the project freed, declaring that nothing cites it (point 3). Its filler reads settled state alone, and gives the whole set or no answer when a reading it relies on fails (refinement per COR-052 point 6 and COR-054).

It also contributes to the work-tracking role's fixers point, `<methodology>::work-tracking:fixers`. Its entries name its agent as the fixer of each of its types, one entry per type (refinement per [project-management:DEC-056-drift-fixers] point 1). The value is static, so it reads in the package metadata, and resolving it runs nothing. The entries grant nothing. project-management, as the role's provider, starts the agent only where the project granted it ([project-management:DEC-056-drift-fixers] point 2), and the agent only proposes (point 5). A release of project-management that does not define the point warns of the contribution. So the optional dependency on project-management starts at its first release that defines it, raised as point 10 says.

Each contribution addresses a role, not a capability, so any provider of that role receives it. A contribution is inert whenever no provider of its role is installed, and the capability never requires one.

### 12. An analysis is built from its concepts up

An analysis is built bottom-up, from the concepts it uses. Whoever writes it, a person or an agent, keeps to this order:
1. **The concepts and how they relate,** in the glossary, then in the domain-model views where the analysis keeps them. Each term's definition gives its broader kind and what sets it apart (point 1), and names the concepts it relates to by their terms, wherever its form allows. The domain-model views follow in the order of their numbers, each explaining a group of the concepts (refinement per [software-analysis:DEC-004-domain-model-views]). The actors follow, with their needs.
2. **The requirements that bind the whole system,** of the kinds [software-analysis:DEC-002-analysis-requirements] gives.
3. **The use cases, area by area.** An area is written only after the areas it builds on, in their numbered order where they carry numbers.
   - **Builds on.** A precondition relies on one of its producers, any one being enough (point 1). An area builds on another where a precondition of its use cases relies on a producer that area holds.
   - **The numbers.** Where the areas carry numbers (point 2), each precondition relies on a producer in its own area or a lower-numbered one. The environment counts as one before every area. A producer in a later area may stand beside it, as an alternative the area does not build on. Two areas that rely on each other cannot both keep their numbers, so the project cuts them again, or makes them one.
   - **Together.** Areas without numbers that build on each other are written together.
   - **Their requirements.** A requirement that binds one area comes before that area's use cases. One that binds some areas comes before the first of them.
   - **No areas.** A project that groups no use cases into areas writes them as one area.
4. **The journeys, last,** across the areas they pass through.

What the order binds:
- **What each artefact uses.** An artefact uses only what the order puts before it: what an earlier step wrote, or what its own step wrote first. So a definition uses terms already defined, an actor's needs use the glossary's terms, and an area uses the areas it builds on. A domain-model view uses the domain-model views of its analysis numbered before it. Each artefact names a concept by the one term that defines it.
- **Going back.** An artefact that needs something the order puts before it, and finds it missing, goes back and writes it there first. That may be a concept, an actor, a requirement, or a use case of an area it builds on. So the order binds what an artefact uses, not when a step is closed.
- **Every analysis.** The order holds for a new analysis and for an area added later. It holds for a brownfield project's candidates (point 9), and for an artefact a revalidation updates.
- **What a reviewer checks.** A judgement rule of `SAN` holds the result the order leaves in the analysis. An artefact uses a domain concept only where a term of the glossary defines it, and names the concept by that term's name. No two terms define one concept. A term's definition is judged too, and a term breaks the rule while an artefact in force uses a name it replaces. Another judgement rule holds the order of the domain-model views. A domain-model view names a concept that another domain-model view of its analysis explains only where that one's number is lower (refinement per [software-analysis:DEC-004-domain-model-views]).
- **What the areas leave.** Which area builds on which is in the analysis: the producers each precondition names, and the areas' numbers. The rule of logical consequence holds them (point 1), with a check where a use case writes `after`.
- **What the writer keeps.** The order in which the steps are written leaves nothing in the analysis a reviewer could read. So the writer keeps it, as the authoring skill walks the steps. No rule holds it.

### 9. Brownfield onboarding

A project with no analysis starts with nothing anchored, so friction reads zero. The signal is uncovered surface: the paths the project declares its analysis should cover (point 2), against what the artefacts anchor to (COR-050). An agent derives candidate artefacts from the code, the existing documents and the project's decisions, in the order point 12 gives, the concepts first. On a brownfield project these sources are the ground truth, so the analysis is drawn from what exists. A planned change, by contrast, reviews the analysis before the code (point 5). A person confirms the candidates. Onboarding needs a non-empty declared surface, and it is complete when that surface is covered. Every artefact must be either anchored, or explicitly accepted as unanchored with a reason recorded on the artefact, such as an actor that no code embodies. The reason is the core friction block's `unanchored-because` (COR-050 point 1), so an accepted actor or term is listed apart and never counted as unanchored work left to do (COR-050 point 8).

### 10. Independent

The capability works with no work-tracking component and no testing component installed. When a work-tracking component is present, it may cite revalidation records from its work items, as an enrichment.

**Its review contribution.** The project-management capability is one such work-tracking component. Where it is installed, this capability contributes the core rule-set reviewer to its merge gate. It does so under the gate's floor on ruled artefacts ([project-management:DEC-032-conditional-reviewer-requirements] D1).
- **What it covers:** every artefact a change alters on which an accepted rule binds, of the analysis or not. It also covers every artefact the change brings under such a rule (COR-057 point 6).
- **Its evidence:** the reviewer was run by hand on eleven changes, and the maintainer judged one of its sixteen settled breaks wrong. That meets the bar of at most one, which COR-057 point 8 leaves to the contributor ([project-kit#1599](https://github.com/aleskalfas/project-kit/issues/1599)).
- **Apart from its contributions to roles (point 8):** the contribution is addressed to project-management's gate, not to a role.
- **The dependency:** the capability declares project-management as an optional dependency, since it works without it (COR-030). In each release of the capability, the range admits no release of project-management without the gate's floor on ruled artefacts. A change cannot name a version before that version is released. So the change that adds the contribution declares that it needs the project-management release with that floor. The range's start is raised to that release when it is made ([project-kit#1640](https://github.com/aleskalfas/project-kit/issues/1640)). Without project-management, nothing reads the contribution.

### 11. Scope boundary, and how the analysis meets the solution

The analysis keeps to the requirements, and points at the solution by anchors, never the reverse. Some needs are left to decisions of their own.

**Outside this record.** Each of these needs its own decision when a real need arrives:
- lifecycles on the process substrate (a planned revalidation, onboarding)
- further kinds of analysis artefact, such as constraints and quality requirements (refinement per [software-analysis:DEC-002-analysis-requirements])
- executable use cases
- evidence kept on the artefact itself

**The analysis apart from the solution.** The analysis describes the requirements: what the system must do, and for whom. A project's decisions and its architecture describe the solution: how the system is built to do it, and why. The two stay apart, so an architecture view is no part of the analysis. They meet by anchors (COR-050), and in one direction only.
- **The analysis points at the solution.** A use case anchors:
  - **each decision record it rests on or is answered by.** The record may be a core record, a capability's record or the project's own, such as an architecture record. A record anchor names it whole, or names one of its points.
  - **each architecture view that realises it,** where the project keeps one. A view a place holds takes an artefact anchor, and any other view takes a path anchor on its file.
- **For example,** a use case that runs on git anchors the decision to use git, which it rests on. One that must export a report as a file anchors the decision to write the report as CSV, which answers it.
- **Every kind the same way.** Actors, terms and journeys anchor the decisions point 4 gives them, and so will any kind a later decision adds. Within the analysis, anchors run as point 4 gives.
- **The solution never points back.** No decision record and no architecture view anchors an analysis artefact. So no cycle runs between the two, and a record that ships needs no exception.
- **Kept by its writers.** Whoever writes a record or a view keeps to this direction, since no check finds such an anchor in general. This capability's check reads only the analysis. Validation reports one only where it closes a cycle of artefact anchors, such as from a view a place holds (COR-050 points 5 and 12).
- **What a view says of the analysis.** A view, one kept as a documentation page included, builds on no analysis artefact. It names one only by its id and states none of its facts, so it has nothing there to anchor. Nor does it show a diagram the capability draws from the analysis, since such a diagram states those facts (refinement per [software-analysis:DEC-003-analysis-diagrams]).
- **A context view** shows the system as one whole among the people and systems around it. Where the project keeps one, it names the analysis's actors by their ids, in its text only, and does not describe them again. The use-case diagram the capability draws is no context view. Each of its nodes is an artefact of the analysis, and each of its lines is a relation the analysis's front matter holds (refinement per [software-analysis:DEC-003-analysis-diagrams]).
- **The reverse is computed, never stored.** A page that shows a record or a view may show what anchors it, such as "Serves: UC-003", worked out from the analysis's anchors. Neither the record nor the view holds it.

**Where a statement belongs.** Each piece of content has one home (COR-006), and three kinds of statement are told apart:
- **A decision** holds the choice and why it was made.
- **A rule in a rule set** says what must hold of an artefact, such as how its text is written (COR-051 point 1).
- **A requirement** says what must hold of the system: a checkable obligation and, where it has them, its measure and what verifies it.

So a decision names a requirement rather than restating its measure, and the analysis artefact that states the requirement is the measure's one home.

## Rationale

**Why product knowledge, not per-design documents.** A use case is true of the product for as long as the product supports it. What belongs to one design is the *revalidation* of the use cases it touches. Keeping the two apart means the knowledge persists after the design ships, and each design's validation is recorded where it happened.

**Why a use-case model layout.** Grouping actors with the use cases they take part in, and keeping the glossary apart because it serves everything, follows an established requirements practice that analysts and newcomers already recognise. Global ids with optional grouping get the benefit of functional areas without the cost of renumbering.

**Why numbers in the areas' names.** A file listing shows the order in which areas build on each other only if their names carry it. Steps of a fixed size let a new area take a free number between two, so nothing is renamed. The number is no part of an id, so renumbering an area moves no citation.

**Why one analysis per component.** A component owns what describes it, as it owns its decision records. Its analysis then changes with it and at its pace, and depends only on what the component depends on. A component may also move to a repository of its own, as a capability may be pulled from one (COR-041). Its analysis moves with it. One analysis for the whole repository could not be split for such a move, and nothing in it would keep dependencies one way.

**Why keeping one is a project's choice.** An analysis is worth its upkeep only where readers need it. A component small enough to describe within another's analysis gains nothing from its own.

**Why an analysis never ships.** An analysis is documentation for those who develop the system (COR-049). Whoever receives a component needs what it does and how to use it, not the account its developers keep of it.

**Why dependencies between analyses follow the components'.** A component's declared dependencies already say what it may rely on (COR-030). An analysis that named one its component does not depend on would describe a system that may not be there. A required component is always there, so it is the environment. An optional one is there only where it is installed.

**Why another analysis's terms and actors are listed by name, and anchored by their records.** A copied definition is a second home for one definition (COR-006), and a link names its one home. An artefact anchor on another analysis's artefact would anchor nothing after a move, since the analysis moves with its component. A record anchor still resolves. The needs an actor brings to one analysis are that analysis's to meet, so it states them, and the readers point gathers them (point 8).

**What listing them costs.** A changed term or actor of another analysis flags no artefact that uses it. Only a changed record behind it does.
- **The area named.** The head names the area it builds on by its folder, which carries no anchor. So a re-cut of those areas leaves the head stale, with no signal, until a reviewer reads it.
- **The needs.** The needs a head states beside a listed actor carry no anchors and no revalidation. Friction reaches them only through the use cases whose goals state them.
- **A requirement named by id.** A changed requirement of another analysis flags nothing in the analysis that assumes it. What meets it is computed within its own analysis alone (DEC-002 point 7).
- **The edge of an analysis.** Journeys and the chain of preconditions stop at an analysis's edge. A journey's steps are use cases of its own analysis, and a precondition's producers too. A path across components is told as one journey in each analysis, with the hand-offs between them stated as assumptions.

**Why roles, and paths through the system.** An artefact belongs here if a change to the software can make it false. A role's needs can go false when the software changes, so an actor is a role, covering everyone who plays it; a persona's imagined traits cannot. A journey's steps and seams are what a change can break, as in the critical user journeys of reliability engineering, so a journey is a path through the system; how the actor feels along it is not something a change to the software makes false.

**Why each kind's structure is data, with its template rendered from it.** A script checks only a structure it can read, and a template that writers copy drifts from any other statement of it. Declared once as data, the structure gives the check one home, and a template rendered from it cannot disagree with the check. The hint stands where the content goes, so the first writer, often an agent, meets what a part asks for rather than a bare label.

**Why every shipped part is present, and `None.` is an answer.** A part left out reads the same as a part forgotten. Asking for every part, with `None.` where there is nothing to say, makes the writer consider each one, and lets a script see that they did. A project's own additions serve that project alone, so the project decides whether each binds.

**Why a use case splits what holds before it starts, and names its guarantees.** A precondition is made true by a use case of the system, or by the environment beside one, so a step may rely on it. An assumption is secured by nothing, so it is a risk to name, and a candidate for a check; requirements standards list assumptions apart for that reason (ISO/IEC/IEEE 29148). What the system still guarantees when a use case fails is what keeps a failure safe, so it gets a part of its own, and the other actors record whose interests the path must keep.

**Why a precondition names what makes it true.** A use case starts only from what is already true: what another use case made true, or what the environment gives. A precondition is what another use case has already set up (Cockburn, *Writing Effective Use Cases*). Use-case contracts link use cases through their conditions (Nebut et al., 2006, and Ryser and Glinz's dependency charts). This record takes them in a light form, one optional field and one rule, which the capability's maintainer chose ([project-kit#1808](https://github.com/aleskalfas/project-kit/pull/1808)). Followed back, the producers lead to the use cases that need no other one. In most projects those rest on an assumption such as "the system is deployed". A project that develops its system with that system starts from developing it.

**Why an environment fact is stated once.** Stated in the Assumptions part and again among the preconditions, one fact would have two homes (COR-006). Alone, it is an assumption. Beside a use case, it is one way a precondition comes true, so that precondition's line holds it.

**Why `after` draws no anchor.** A release starts from the last release, so a use case names itself, and alternatives can close a loop. As anchors, either would be a cycle, which has no order of revalidation (COR-050 point 5). The cost is that a changed postcondition flags none of the use cases that follow from it. A reviewer of that change reads them.

**Why one producer in its own area or an earlier one is enough.** Producers are alternatives. A later one, such as installing the system, can be one way among several to hold it, and refusing it would refuse a true precondition. So the numbers' order asks only that each precondition can come true from its own area or an earlier one.

**Why a project reviews the shipped parts.** The shipped parts come from established practice, not from the project's own system. Only a project's own examples show whether they suit it, and a default nobody reviewed binds its artefacts to a choice nobody made. What a review finds goes into the project's own changes to the structure, or into a change proposed to the capability, as a project does with a rule it disagrees with (COR-051 point 7).

**Why `SAN` binds through a set of the project's own.** A shipped rule binds only through a set of the project's own. That set decides where the rule binds, and its pin decides when a new major starts binding (COR-051 point 7). A set may be missing, or its scope may select none of the analysis. Either would leave the analysis's structure unchecked without a word, so the check and validation both say so. While no rule of `SAN` is accepted, no set could make one bind, so validation only reports the gap. The cost is a warning a project keeps while it chooses not to inherit `SAN`.

**Why the capability checks its records itself.** A rule binds only on an artefact a route leads from, and no route leads from a held document (COR-051 point 7). A format rule on records would therefore bind nowhere, and the records would go unchecked. Their structure is the capability's own, so the capability checks it as it checks their front matter. That is no invariant kept beside a rule, which the rule-set record rejects (COR-051), since no rule binds on a record. The cost is that a project cannot tighten a record's structure, since no rule it names could bind on a record.

**Why live artefacts move to a new structure, and records do not.** An actor, a use case, a journey or a term describes the system as it is, so it is read in the current shape. A record says what one revalidation found on its day. Its words are the decision of whoever performed it, and rewriting them into a later shape would change what was decided.

**Why the actor's voice ships.** A need in the actor's first-person voice is how user stories state one, and a goal that starts with its verb is how use cases name one. Neither is one project's style, so the capability ships both in its hints, and a project that writes them otherwise replaces the hints.

**Why an analysis is built from its concepts up.** Written top-down, an analysis defines its words on the way. Each area names what it meets in words of its own. So two areas name one thing differently, and a reader cannot tell one thing named twice from two things. An agent that writes the analysis makes this worse, since it fills each part plausibly, in whatever words come to it.

Built from its concepts, each later artefact uses words the glossary already gives one meaning:
- **The requirements that bind the whole system** come before the areas, so no area states them again in its own way.
- **An area that builds on another** relies only on use cases already written.
- **The journeys** come last, since their steps are use cases.
- **The actors** come with the concepts, because a requirement names the actors whose needs it meets, and a use case names its actor.
- **The anchors' direction.** Each later step anchors what an earlier one wrote: a use case its actor and its requirements, a journey its use cases. So the order writes first what others depend on, the order friction is reported in (COR-050 point 11).

The capability's maintainer decided the order of the concepts, the requirements, the use cases and the journeys as a rule of the method, not as advice ([project-kit#1784](https://github.com/aleskalfas/project-kit/issues/1784)).

**Why a rule holds the result, and the writer the order.** Advice gives way wherever it costs time, and the cost shows only later, as two names for one thing. A rule a reviewer checks holds what the order leaves: each artefact uses the glossary's one name for each concept. What an artefact uses is in the analysis at every commit. Which file was written first is not, and it tells a reader nothing. A term added in the same change as the use case that first needs it keeps the order.

**Why the glossary is judged too.** A term's definition uses concepts as any artefact does, and the definitions are where the concepts relate. Two terms for one concept would let two areas each use a defined term, and still name one thing differently. So the rule judges each term's definition, and holds that no two terms define one concept. It judges the definition alone: a term's example illustrates the definition, and its distinctions tell words apart, so neither says how the concept relates to others.

**What the rule costs.**
- **Many terms.** Each concept of the project's domain, in the rule's sense, needs a term before an artefact uses it. An analysis written before the rule meets many breaks at once, when it comes under the rule. COR-060 point 2 gives the ways out, such as bringing the analysis under the rule one area at a time.
- **A changed term.** Using a term asks for no anchor on it. So renaming, withdrawing or redefining a term flags none of the artefacts that use it, and a reviewer judges none of them in that change. Whoever changes the term finds its uses, and mends them in the same change. A rename the rule holds on the term itself: the term breaks it while an artefact in force uses a name it replaces.
- **A term's name in an everyday sense.** It breaks the rule, unless the term tells that sense apart from its own.
- **Readings for a person.** Whether a word is a concept of the project's domain is often a reading the rule does not settle. So many of its findings wait for a person (COR-057), and a gate that holds a merge for such a finding holds changes to the analysis more often.

**Why revalidation owns both planned and drift-triggered checks.** Checking before code and checking after an unplanned change are the same act with different triggers. One record shape, and one set of outcomes, serve both.

**Why records only with findings.** Most revalidations find that everything holds. Writing a file each time would bury the few that matter. Git already records the routine ones through the revalidation recorded on the artefact.

**Why a planned record names the design by pointer.** A pointer returns the exact text reviewed, which no version number does. A version an author declares on a document would tell a dependant one fact, whether the meaning changed: a minor and a major version would each ask the dependant to look again. So the capability's artefacts and records carry no declared versions, and a record points at the text itself.

**Why keep testing out.** Revalidation judges a description by reading; testing judges software by running it. Merging them would make this capability depend on executing arbitrary software, and would blur whose fix a failure demands. The evidence slot lets executed results inform revalidation without that coupling.

**Why a declared exception to never reusing an id.** An id is never reused so that whatever cites it keeps naming the artefact it meant. Artefacts nothing cites carry no such promise: a pilot abandoned before anything cited it leaves ids that name nothing anyone reads, and without the exception the analysis would count past them for good. The places that may cite an id, such as other repositories, trackers and code, are open-ended, so no tool can check them all. A person judges that nothing cites the ids, and answers for the judgement: the project declares the exception, naming each id it frees, and a reviewer sees the declaration as an act of its own.

**Why ids are unique across a repository's analyses.** Three readers take an id across the repository. The core's lookup of an artefact anchor reads an id across the repository. Work tracking's use-case point receives every use case under its id (point 8). project-management reads that id as `UC-` and digits (project-management DEC-054 point 1). With one artefact per id, none of them changes.

**Why a component leaving keeps withdrawn stubs.** Issues and records cite its artefacts by id, and an id names one artefact for good. Taking the folder away whole would delete cited artefacts, and would let their numbers be given again. A withdrawn stub keeps each id taken and each citation true, and adds no concept.

**Why a person decides stale versus regressed.** The distinction is intent: was the change meant? An agent can propose it from the change's context, but when intent is unclear, only a person knows. Getting it wrong either rewrites the truth to match a bug, or reports a defect for an intended change.

**Why one agent fixes every type.** Every type is the capability's own, and one judgment answers each of them: the revalidation's, with its four outcomes (point 5). So the capability declares one agent for them all. A project that wants another agent for a type replaces that type's entry in its own filler of the point.

**Why the analysis and the solution stay apart, and are linked.** The analysis says what the system must do, and the decisions and the architecture say how it is built to do it. Established practice keeps the two apart and links them. Requirements engineering keeps the problem space apart from the solution space. Kruchten's 4+1 view model ties its four views together through scenarios, its "+1".

Kept apart, each side changes at its own pace and keeps one owner. The analysis's anchors carry a change in the solution across, so the analysis does not go stale unseen.

**Why one fixed direction, from the analysis to the solution.** A direction that is the same for every pair is predictable. A writer never judges which way one link runs, and a reader finds every link on the analysis's side.

Anchors both ways would form a cycle, and a cycle has no order in which its artefacts could be revalidated (COR-050 point 5). With one direction, no cycle can run between the two, so no rule is needed for which anchor gives way.

Only this direction works for a record that ships, which could never anchor a project's analysis:
- **One text for every project.** It ships the same text to every project that installs its component. An anchor in it would name one project's artefact in every project, which universal applicability rules out (COR-014).
- **Never read there.** In an adopting project the anchor would not be read, since a synced tree is never a place (COR-050 point 14).
- **Not the project's to edit.** Every file has one owner, so a project may not add the anchor to the record (COR-001).

So the direction from the analysis treats a record that ships as it treats the project's own, with no exception.

**What the direction costs.** A changed use case flags no record that answers it, and no view that realises it, since no anchor runs that way. Nor does a changed actor flag a context view that names it. A signal against a link's direction would serve every component's links alike. So it is the core's to give, for every kind of link at once ([project-kit#1667](https://github.com/aleskalfas/project-kit/issues/1667)).

**Why the reverse is computed, never stored.** A reader of a record or a view still wants to know what it serves. Stored on the record or the view, that list would be a second home for each link, which drifts from the first (COR-006). It would also point the solution back at the analysis. Worked out from the analysis's anchors, it is always as true as they are.

**Why a view names analysis artefacts by id, and never anchors them.** A view is part of the solution, so an anchor from it would point back at the analysis. A name states none of the named artefact's facts, so a view that only names one builds on nothing it must anchor. The roles a context view shows using the system are the analysis's actors. Naming them by id keeps one description of each role (COR-006).

**Why a decision names a requirement rather than restating it.** A measure stated in two places drifts. The requirement holds the measure and what verifies it, so it is the measure's one home. A decision cites it, since each piece of content has one home (COR-006).

### Alternatives considered

- **Top-down, from the use cases, defining terms on the way.** Rejected. It is the order in which two areas name one thing differently.
- **The order as advice in the authoring skill alone.** Rejected. Advice gives way where it costs time, and nothing would check it.
- **A check that a term was committed before what uses it.** Rejected. The order binds what an artefact uses, which the analysis shows. A term added in the same change as its first use keeps the order.
- **Each step closed before the next starts.** Rejected. A later step finds concepts the first one missed, and going back to define them keeps the order without freezing the glossary.
- **A rule that holds the order in which areas are written.** Not taken. The analysis shows which area builds on which, through the producers and the numbers, and a rule holds that. It does not show which area was written first.
- **Areas named by their goal, unnumbered, with their order computed.** Rejected. A file listing would never show the order.
- **Layers computed from the preconditions, kept as folders.** Rejected. A layer would move whenever a precondition changed.
- **Areas named after the concepts they act on.** Rejected. A concept's use cases span the chain, so such areas give no order.
- **A judgement rule alone, with no field.** Rejected. It leaves the chain to each reviewer, and a picture of the chain would have nothing to draw.
- **The full trace, with layers and a report on changed postconditions.** Rejected. It is more than the order needs.
- **Conditions as formal predicates on the concepts' states.** Rejected. Too heavy for the analysis's readers and writers.
- **Every environment fact in the Preconditions part, with the Assumptions part retired.** Rejected. Every live use case would need a migration.
- **A check that refuses any producer in a later area.** Rejected. It refuses a true precondition whose alternatives include a later use case.
- **One analysis for the whole repository.** Rejected. A capability could not move, and nothing would keep dependencies one way.
- **A component's analysis shipped with it.** Rejected. An analysis is internal documentation for its developers (COR-049).
- **Dependencies between capabilities' analyses only as an option.** Rejected. A capability may require another (COR-030), and what it requires is always there.
- **A glossary copying the definitions of another analysis's terms.** Rejected. Two homes for one definition.
- **Artefact anchors on another analysis's artefacts.** Rejected. After a move they would anchor nothing.
- **Each analysis numbering alone, with an artefact read as `<analysis>:<id>`.** Rejected. It adds a concept to places (COR-056 point 7), and changes work tracking's use-case point and project-management's reading of an id.
- **Taking a leaving component's analysis away whole.** Rejected. It deletes cited artefacts, and frees their numbers.
- **Leaving the glossary unjudged.** Rejected. Two terms could define one concept, and each area could use its own.
- **Marking each use of a term, so a script checks it.** Rejected. Every artefact would carry markup for a script, and whether a word is a domain concept would still be a reader's judgement.
- **Each artefact anchoring the terms it uses.** Rejected. The anchors would be a second list of what the text names, and no check could hold the two together, since whether a word is a use is a judgement. Every edit to a term, a reworded example included, would also flag every artefact that uses it, an anchor broader than what makes the artefact true (COR-050 point 7).
- **Use-case sets per design, validated once.** Rejected. The knowledge would be scattered across designs and would stop being maintained after each one shipped.
- **A flat analysis folder.** Rejected. Actors and terms get lost among many use cases, and there is no natural place for grouping or later modules.
- **Actors kept in one collection file.** Rejected. An actor's needs would sit far from its description, and keeping them beside it in the body would make a tool read data from a body, or keep one fact in two places.
- **Reading a kind's structure from its template.** Rejected. Required parts, a project's additions and its own content would need markup in the template, and a script would parse text a writer copies.
- **Keeping a structure in its rule's content.** Rejected. Every change to a structure would version the rule set and flag the rule's dependants, though what the rule says had not moved.
- **Hints only in the check's messages and the skill.** Rejected. The first writer, often an agent, would meet bare labels.
- **A project's templates beside the shipped ones.** Rejected. Two shapes of one kind would drift apart, which declaring the structure once exists to prevent.
- **A project's additions in the capability's configuration file.** Rejected. Settings and data would share a file, and a rule anchored to either would be flagged by every edit to both.
- **Optional shipped parts, left out where empty.** Rejected. A part left out reads the same as a part forgotten.
- **The actor's voice as each project's own rule.** Rejected. It is the common convention for needs and goals, not one project's style, and a project that writes otherwise replaces the hints.
- **`SOFTAN` as the method rule set's name.** Rejected. It would almost never clash with a project's own set, but it reads worse in every finding than `SAN`, which follows living-docs' `LDOC`. A project's set already named `SAN` is a clash validation reports, never a silent one (COR-051 point 3).
- **`SAN` binding through the capability's own check, with no set of the project's.** Rejected. No rule of a method rule set binds until a set of the project's own with a scope inherits it, directly or not. That keeps a project's choice not to inherit it (COR-051 point 7).
- **Records held to the format rule wherever it binds on the analysis.** Rejected. It would be a second answer of where a rule binds, beside the backbone's one answer (COR-051 point 7).
- **A glossary's head checked always, as a record is.** Rejected. The head is part of the term kind's structure, the format rule's checkable part. Checking it always would enforce part of one rule two ways, which the rule-set record rejects (COR-051).
- **A route that starts at a held document, so a set can reach the records.** Not taken here. It changes the rule-set record (COR-051), and a project's tightening of the record waits for it.
- **Reporting a structure under a proposed rule.** Rejected. Everyone runs the normal check, and agents act on what it reports, so its findings would bind in practice what nobody accepted (COR-051 point 4). The preview shows them only to whoever asks.
- **A journey's seams in a part of their own.** Rejected. It gives an overview of every hand-over, but splits each step from what it needs, and a journey is read as a path.
- **The label reader in the backbone.** Not taken yet: this capability is the only component that reads declared labels (COR-007). The trigger to move it is a second component that must read them, such as a documentation component whose kinds of page declare labels, or let a project add to their structure. What would move is the reading of headings and labels, of where each part ends, and the forms any component could use. The forms only the analysis uses stay here.
- **A record for every revalidation.** Rejected. Routine records would bury the ones with findings.
- **An agent for each kind of artefact as its fixer.** Rejected. One judgment answers every kind, so the agents would differ only in name, and a project that wants another agent for a type replaces its entry.
- **Holding every record to today's structure.** Rejected. A part added later would fail every older record, and only rewriting the record would mend it.
- **Naming the design a planned record reviewed in one line of text.** Rejected. No script can check it, and each source of a design stands at a version of its own.
- **Copying the tracker text a planned record read into the record.** Rejected. The copy is exact and offline, but it doubles the design in every record that reads it.
- **A tag for each review, so a design reviewed on a branch keeps its commit.** Not taken: a commit on the default branch, or the change the record lands in, pins a design in the usual case. A tag per review is the fallback where a design must be reviewed before it lands.
- **Versions an author declares on each artefact or design, for a record to name.** Rejected. See Rationale. A pointer serves every source, and a number adds nothing a dependant reads.
- **Storing each artefact's current-or-stale state as truth.** Rejected. It would duplicate what anchors and git already answer; the core's tool-written status is a dated snapshot for visibility, never read for friction (COR-050).
- **Including executed testing in this capability.** Rejected. See Rationale; the evidence slot covers the useful part.
- **Requiring a documentation or work-tracking capability.** Rejected. The capability must be useful on its own.
- **Keeping the ids of artefacts nothing cites taken: counting past them, or restoring the artefacts as withdrawn.** Rejected. Both follow the rule, and the cost is cosmetic, but it lasts: ids that name nothing anyone reads, and withdrawn files describing work the software never had.
- **Freeing the ids of every artefact deleted before a given commit.** Rejected. It frees far more than the artefacts the project means, including any deleted while something cited them.
- **A marker in the history, such as a line in a commit message.** Rejected. It cannot be added to a commit already merged, and it is not reviewed as an act of its own.
- **Inferring which deletions free their ids.** Rejected. Deleting an artefact would become a legitimate way to free its id, the deletion the append-only rule exists to prevent.
- **Architecture views inside the analysis, beside the use cases or as a kind of their own.** Rejected. The solution would sit among the requirements, with two owners and two paces in one place.
- **Anchors both ways between an analysis artefact and a decision.** Rejected. Each such pair would be a cycle, which has no order of revalidation.
- **The solution always pointing at the analysis, a decision anchoring the obligation it answers.** Rejected. A record that ships could carry no such anchor, and a change to a decision would never reach the analysis that rests on it.
- **Anchors only to the decisions an artefact rests on, and none to those that answer it.** Rejected. A changed decision would never flag the use case it was made to meet. Yet the change can leave the use case untrue of the system.
- **A direction for each pair, by which came first, the obligation or the decision.** Rejected. A writer would judge the history of every link. A record that ships would need an exception. A chain of anchors could still close a cycle.
- **A stored reverse, such as a list on each record of what it serves.** Rejected. It is a second home for each link, and it points the solution back at the analysis.
- **A view that anchors the analysis artefacts it names, a context view its actors among them.** Rejected. The solution would point back at the analysis.
- **A context view that describes the actors again.** Rejected. Two descriptions of one role drift apart.

## Implications

- **The capability ships** the layout for its artefacts, a declared structure per kind with the template rendered from it, its method rule set with the format rule and its judgement rules, the declaration of its places and connections, commands to stamp artefacts and check their shape (friction itself is the core check), and an authoring skill that walks the order of point 12 and guides revalidation. It also ships a type registry, and each place names a type from it. It ships its contribution of the rule-set reviewer too, with an optional dependency on project-management (point 10). Its agent proposes the outcomes, and is declared as the fixer of each of its types (points 5 and 8).
- **Installing the capability** creates the project rule set it declares (COR-017). The set is the project's own. It selects the analysis by the capability's types (point 2), and inherits `SAN` at its major when the set is created.
  - Install creates it only where no set of the project's own inherits `SAN`, directly or not. So a project that chose where `SAN` binds keeps its own set.
  - A migration creates it, on the same condition, for a project that installed the capability before it declared the set.
  - From then on the set's pin decides when a new major of `SAN` binds (point 1).
- **Domain-model views** are a kind of their own, which [software-analysis:DEC-004-domain-model-views] decides, as point 11 asks. Point 12's first step writes them after the glossary, before the actors.
- **Named for later: journeys across components,** such as the delivery of a feature through several capabilities ([project-kit#1685](https://github.com/aleskalfas/project-kit/issues/1685)). Such a journey needs a decision of its own, since no analysis describes two components.
- **Several analyses and `after`** follow this record into the capability. That is the configuration that lists the analyses, a reference across them and the validation of ids across them. It is also a use case's `after`, and a check of it for the rule of logical consequence. A project uses several analyses, and `after`, only where it chooses to. A new check binds at its rule's status.
- **Projects** keep their analyses under their internal documentation root, one per component that keeps one. They choose each kind's parts when they adopt the capability, and build each analysis from its concepts up (point 12). They keep their own additions in its project tier, and wire the core friction check into their continuous integration if they want it enforced.
- **A project's use cases** anchor the records they rest on or are answered by, and the views that realise them. The project's records and views carry no anchor on the analysis (point 11).
- **A change to a kind's structure** carries the migration of the live artefacts with it, and settles how a part it adds is answered and what friction the migration raises on their dependants.
- **History kept as it was written:** the way a record, or a withdrawn artefact, is checked against the structure in force when it was written or withdrawn comes with the first change to a kind's structure that needs it.
- **Documentation disciplines** can read actors and their needs through the readers point, without any dependency.
