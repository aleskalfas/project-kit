---
id: DEC-005
title: An analysis leads its reader to each function by its areas, its journeys and its concepts
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A reader comes to an analysis to find a piece of functionality: what the component does for someone, how it does it, and what that rests on. The capability's records decide what each kind of artefact holds, and the order in which an analysis is built ([software-analysis:DEC-001-software-analysis-discipline] points 1 and 12). None of them leads a reader to one function among the artefacts:
- **Areas are each analysis's choice.** DEC-001 point 2 lets the use cases be grouped by functional area, and point 12 writes an analysis with no areas as one area.
- **Journeys are a kind no analysis has to use.** The build order writes them last, where an actor's goal spans several use cases, and no rule asks for one.
- **Nothing leads back from a concept.** A use case links to the terms it uses. No artefact leads from a term to the use cases built on it ([software-analysis:DEC-004-domain-model-views] point 7).

The analyses of the methodology this capability ships with show the result. On 26 October, the core's analysis grouped its use cases into five areas, and told three journeys. Each capability's analysis listed its use cases flat, and told no journey.

The capability's maintainer found it on 26 October, reading project-management's analysis as a newcomer ([project-kit#2106](https://github.com/aleskalfas/project-kit/issues/2106)). He placed the gap in the rules for building an analysis, not in one analysis. Every analysis is to be built the same way, so the problem does not recur. Areas and journeys are planned from what the analysis holds, never from counts.

## Decision

**Every analysis leads its reader to each function in three ways. Its use cases lie in the functional areas their content has, each named by what it does. A journey tells each path one actor takes through several of its use cases. Each concept leads back to what is built on it. Areas and journeys are planned from what the use cases do, never from how many there are, and are written as part of building the analysis.**

### 1. Use cases lie in the functional areas their content has

An area is one function of the component, which a reader recognises by what it does. Every use case in force lies in an area.
- **One function** is one summary goal: the area's goal, one level above its use cases, which are the steps toward it ([software-analysis:DEC-003-analysis-diagrams] point 8). An area whose use cases serve several such goals holds several functions, whatever its goal says. Two areas serve one function where one area's goal is a step toward the other's, or a reader cannot tell the two goals apart.
- **What cuts an area** is what its use cases do. Their actor, a concept they act on and the code that carries them out cut no area, unless that is also what they do together.
- **Never from counts.** No number of use cases creates, splits or merges an area. One function is one area, however many use cases it holds. Two functions are two areas, however few use cases each holds.
- **One function, one area.** An analysis whose use cases all serve one function keeps them in one area.
- **Its goal.** The area's goal is a setting, which no rule judges (DEC-003 point 8). Where the configuration gives none, the area's function is the one summary goal its use cases serve together, as a reader names it.
- **Its number** keeps its meaning: one valid order in which the areas build on each other (DEC-001 point 2). Where two areas would build on each other, the cut by function stands and the numbers give way. The two are left without numbers and written together (DEC-001 point 12). They become one area only where they serve one function.
- **A requirement** is not cut by this record. It may lie in the folder of an area it binds, as [software-analysis:DEC-002-analysis-requirements] point 3 allows.

### 2. A journey tells each path through the use cases

A path is several of one actor's own use cases, which it takes in turn, end to end, toward one goal that none of them reaches alone. Where the use cases make a path, a journey tells it (DEC-001 point 1).
- **Its seams.** Each step takes up what an earlier one left, such as a state its postconditions make true, or a file it writes. Each such hand-over is a seam, where the path can break.
- **Read from content.** A path is there where one actor takes its use cases in turn toward one goal. A precondition that an earlier use case of the same actor makes true is a sign of one, never proof. Use cases the actor never takes in turn toward one goal make no path, however many it has.
- **Told.** A journey of the path's actor tells it where its steps, or the steps one of its variants takes, run through the path's use cases in their order. So a stretch of a longer path, and a shorter path a variant takes, are told by that journey.
- **Across areas.** A path's steps may lie in several areas. Its journey is one, whichever areas it passes through.
- **Another actor's use case** on the way is no step of the path. The journey relies on it (DEC-001 point 4). A path across components is told as one journey in each analysis (DEC-001, "What listing them costs").
- **The overview leads from an area to its journeys.** Each area lists, beside its use cases, each journey in force with a step among them, and says so where there is none. A journey's flow stays in reference (refinement of DEC-003 point 8).

### 3. Each concept leads back to what is built on it

A reader who starts from a concept finds the use cases, journeys and requirements built on it.
- **Built on a concept.** An artefact is built on a concept where one of its statements uses it, in the sense of the rule on domain concepts (DEC-001 point 12). A command reads that only in part, such as from the links between terms, which a goal and front matter never carry (DEC-004 point 7). So the lists show what the command reads, as the links do.
- **Where a reader starts:** a domain-model view, which leads to what is built on the terms it explains. An area, in the overview, leads to the domain-model views its use cases' terms come from.
- **Computed, never by hand.** A command computes the lists from the analysis. Where a page keeps them, the check holds them fresh, as it holds the overview (DEC-003 point 8). They state no fact of their own, since each follows from what the artefacts already say.
- **Where they stand is decided with their build** ([project-kit#2104](https://github.com/aleskalfas/project-kit/issues/2104)). Each way refines accepted points, so the change that builds it lands that refinement, naming its exception, read by the critic and the architect:
  - **in each view:** DEC-001 points 1 and 11 and DEC-004 point 7, since the view stores the reverse of a use. A list's words are content, so each new use changes the view and the answers on it (COR-050 point 5).
  - **in the overview:** DEC-001 point 1 and DEC-003 point 8, which reads no body but each actor's first sentence (refinement per [software-analysis:DEC-006-text-in-body]), and a new version of the overview's fingerprint
  - **a query,** as for what meets a requirement (DEC-002 point 7), **or pages in the overview's held folder:** DEC-001 point 1, since the command reads bodies

### 4. Building an analysis writes its areas and its journeys

The build order writes the areas and the journeys as part of building an analysis, never as extras afterwards (DEC-001 point 12).
- **Before the first use case,** the writer plans the areas. The actors' needs, from step 1, are the goals of the use cases to come. The writer groups them by the function each serves, and gives each area its goal.
- **Step 3** writes each use case in the area of its function. A use case whose function no area holds sends the writer back to the plan, for a new area or a goal drawn again.
- **Step 4** writes a journey for each path the use cases make. A path the writer finds while writing an area is noted then, and told in step 4.
- **Every analysis.** The same holds for a new analysis, an area added later and a brownfield project's candidates (DEC-001 point 12). A change that adds a use case puts it in its function's area, and a change that makes a path tells it.

### 5. A rule holds it, and the check fails what a script can settle

A judgement rule of `SAN`, the rule on areas and journeys, states points 1 and 2. So the rule-set reviewer judges every analysis by it, wherever it binds (DEC-001 point 1).
- **What a script can settle:** a use case in force that lies in no area's folder. Its path shows it. The check fails it where the rule binds, as the rule's checkable part.
- **What the overview shows:** each area's journeys, and an area with none (point 2). A reader and a reviewer see there where a path may be untold. It is no finding, since many areas hold no path.
- **A reviewer judges the rest:** whether an area serves one function, whether a use case is a step toward its area's goal, and whether use cases make a path no journey tells.

### What this overturns, and what stands

This record partially supersedes DEC-001. Each overturned passage stays in DEC-001 as it stood.
- **Overturned:**
  - in point 2, "(optionally grouped by functional area)": every use case in force lies in an area (point 1 here)
  - in point 12, step 3's "No areas": an analysis of one function keeps its use cases in one area's folder (point 1 here)
  - in point 12, step 3's "The numbers", that two areas that rely on each other may become one area whatever they serve. They become one only where they serve one function, and otherwise they are left without numbers (point 1 here).
  - in the Rationale, "Why a use-case model layout", that the grouping is optional. That global ids spare a renumbering when a use case moves between areas stands.
- **Stands:** the layout of an analysis, its ids, the areas' numbers and what they mean, the build order and what it binds, and a journey's kind. DEC-001 point 12's step 4 and DEC-003 point 8 gain what point 2 here adds, refined in place. DEC-002 point 3 names the use cases' areas, refined in place.

## Rationale

**Why functional areas.** A reader comes to an analysis to find what the component does. Grouped by function, the overview names each function by its goal, with the use cases that reach it below. A flat list asks the reader to read every title, and to work out which belong together. Use-case practice ranks goals the same way: a summary goal spans several user goals, each a use case of its own (Cockburn, *Writing Effective Use Cases*). An area's goal is such a summary goal (DEC-003 point 8).

**Why one function is one summary goal.** A function needs a level, or any two use cases could count as one function or as two. The area's goal gives that level, one above its use cases. Comparing a use case with the goals that exist keeps the judgement on the analysis, never on a goal the reviewer would have to invent.

**Why every analysis, one of one function too.**
- **One shape.** A reader who knows one analysis knows how to read every other.
- **A check.** A script can fail a use case in no area only where every analysis keeps its use cases in area folders.
- **No move later.** An analysis that grows past one function adds an area. A flat one would move each use case into a folder, and revalidate each move (COR-050 point 3).
- **What it costs.** An analysis of one function keeps one folder and one goal, and that goal may say much what its purpose record says.

**Why never from counts.** A count says nothing of what the use cases do.
- **A threshold** leaves a small analysis flat until it grows past it, and then reorganises it all at once.
- **A cap** splits one function in two, for no reason a reader can see.
- **The maintainer** ruled counts out when he decided this record's question ([project-kit#2106](https://github.com/aleskalfas/project-kit/issues/2106)).

**Why not by actor, concept or code.**
- **An actor** takes part in several functions, and several actors take part in one. Areas by actor split a function's use cases.
- **A concept's** use cases span the chain, so areas by concept give no order (DEC-001, Alternatives considered).
- **The code's modules** belong to the solution, which the analysis keeps apart (DEC-001 point 11).

**Why a journey for each path.** A path breaks at its seams, where one use case hands over to the next (DEC-001, "Why roles, and paths through the system").
- **Its seams written down.** A path no journey tells leaves its seams unwritten. Nothing anchors the code there, so a change that breaks a hand-over flags nothing.
- **A reader's question.** A reader who asks how to reach a goal across use cases finds them in order, with what passes between them.
- **From content.** Whether one actor takes use cases in turn toward one goal is in what they say. How many use cases an actor has says nothing of it.
- **End to end.** A journey tells a whole path, so a stretch of it needs no journey of its own. A shorter path is a variant of the journey that tells the longer one.

**Why the overview leads from an area to its journeys.** A reader of an area asks which paths pass through it. Listed beside the area's use cases, its journeys meet the reader on the story's path. On 26 October, the core's analysis held three, across one area or several, which showed how they read. A flow stays in reference, a picture a reader looks up when needed.

**Why an area with no journey is shown, and never reported.** On the core's analysis of 26 October, a report of each chain of one actor's use cases that no journey tells would name some nineteen pairs. Most are alternatives of a precondition, or hand-overs a journey already relies on. It would also miss real paths, whose use cases name an earlier producer than the step before them. Nothing would record that a reviewer judged a pair to be no path, so the report would never clear. Agents act on what a check reports (DEC-001, Alternatives considered), and would write journeys that tell no path.

**Why back from a concept.** A reader may start from the words: a domain-model view, or a term in the glossary. Such a reader asks what is built on the concept. The maintainer, reading a view of project-management's analysis, could not find the use cases and requirements that belong to it ([project-kit#2104](https://github.com/aleskalfas/project-kit/issues/2104)). Written by a command, the lists cannot drift from the analysis.

**Why written while building.** On 26 October, the capabilities' analyses were small, and none had been built under a rule that asked for areas or journeys. Small or not, each has functions a reader would look for. The build order is where a writer keeps the order (DEC-001 point 12). So it is where the areas are planned and the journeys written.

**Why a rule, with a check where a script can settle it.** Advice gives way wherever it costs time (DEC-001, "Why a rule holds the result, and the writer the order").
- **The rule** holds what the content asks, which only a reader can judge.
- **A use case outside every area** is settled by its path, so the check fails it where the rule binds, as RS-SAN-009's check holds what a script reads of `after`.

**What the rule costs.**
- **Readings for a person.** Whether two goals name one function, and whether use cases make a path, are readings the rule does not settle. Many of its findings wait for a person (COR-057), and a gate that holds a merge for such a finding holds changes to the analysis more often.
- **A goal no reviewer sees change.** A change to an area's goal alters no artefact, so the reviewer does not judge the area's use cases in it (COR-057 point 1). No rule judges a goal's words, so a goal may join several functions. The rule still reads what the area's use cases serve, and the overview shows the goal to every reader.
- **A path left untold by another change.** Withdrawing a journey, or changing a use case's actor or goal, can leave a path untold in use cases the change does not touch. The change owns that break, and its reviewer reads the actor's use cases and journeys to find it.
- **All at once.** An analysis comes under the rule when its set's pin moves to the major that accepts it (COR-051 point 7). Each flat use case and each untold path breaks it then, and each use case moved into an area is revalidated in the same change (COR-050 point 3).

### Alternatives considered

- **Areas as each analysis's own choice.** Rejected. It is the gap this record closes: no capability's analysis took them.
- **A flat analysis of one function read as one area, its goal the purpose.** Rejected. No script could tell such an analysis from one left flat, so the check could fail no use case in no area.
- **Areas once an analysis holds more than a set number of use cases.** Rejected. A count says nothing of what the use cases do.
- **An area for each actor.** Rejected. It splits a function among the actors that take part in it.
- **An area for each module of the code.** Rejected. It cuts the requirements by the solution.
- **A use case in no area left to the reviewer alone.** Not taken. A script reads it from the use case's path.
- **A journey for every actor, or for every area.** Rejected. An actor or an area with no path would get a journey that tells none.
- **A check that fails an area with no journey.** Rejected. Not every area holds a path, and no script reads whether use cases make one.
- **A report of an area with no journey, or of a chain of one actor's use cases no journey tells.** Rejected. See Rationale: it would never clear, and would push agents to write journeys that tell no path. The overview shows each area's journeys instead.
- **A path tied to a need of the actor that no single use case meets.** Not taken. It would give a reviewer a written list of paths to look for, at the cost of a change to the actor kind and to the rule that a use case's goal is one of its actor's needs.
- **Two rules, one for the areas and one for the journeys.** Not taken. A project could take the areas and leave each path untold. The cost of one rule is that a finding on a journey, often a reading for a person, holds a change to the areas too.
- **Journeys left to the build order's advice.** Rejected. Advice gives way where it costs time.
- **The links back from a concept written by hand in each view.** Rejected. They would drift from the use cases.
- **Where the links back stand, decided here.** Not taken. Kept in a view, a list shows where a term is read, as a term's link to its section does (DEC-004 point 7). Computed elsewhere, it stores no reverse. The trade-off is weighed where the lists are built, with what each way costs in front of the builder.
- **An area as a kind of artefact of its own,** with its goal, its anchors and its revalidation. Not taken yet. A goal stays a setting, which no reviewer sees change (see Rationale). The first change to a goal that lets a misfiled area pass review is the trigger to weigh it (COR-007).
- **Each journey's flow under each area it passes through.** Not taken. A flow is a picture a reader looks up, and a journey across areas would be drawn under each.

## Implications

- **DEC-001** is partially superseded, as "What this overturns, and what stands" lists. DEC-001 point 12, DEC-002 point 3 and DEC-003 point 8 name what this record adds to them.
- **`SAN` gains a judgement rule,** proposed, with this record its origin. It joins the major that accepts `SAN`'s other proposed rules (DEC-003 point 10).
- **The authoring skill** plans the areas before the first use case, writes each use case in its function's area, and writes a journey for each path (point 4).
- **What follows this record into the capability:** the check of a use case in no area (point 5), and each area's journeys in the overview (point 2). The links back from a concept follow too ([project-kit#2104](https://github.com/aleskalfas/project-kit/issues/2104)).
- **An analysis written before this record** comes under the rule when its set's pin moves to the major that accepts it (COR-051 point 7). COR-060 point 2 gives the ways out, such as a scope that leaves the analysis out until it is brought to the rule.
