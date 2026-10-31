---
id: DEC-007
title: Any hand-over between an actor's own use cases is a sign of a path
status: proposed
date: 2026-10-31
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an actor's own use cases are those whose goal is its own, even where others do their work. Any hand-over one of them states is a sign that they make a path, which a journey tells. It may stand in a precondition, a trigger or a step, such as a last step that names the next use case. A state left standing, and a goal a run did not meet, make a path only where one goal joins the use cases.

## Context

[software-analysis:DEC-005-finding-functionality] point 2 asks for a journey for each path. A path is several of one actor's own use cases, which it takes in turn toward one goal that none of them reaches alone. The point names one sign of a path: a precondition that an earlier use case of the same actor makes true. A reviewer judges the rest (DEC-005 point 5).

On 30 October, a reviewer read each actor's use cases for paths, in the analysis of the methodology's core that this capability ships with ([project-kit#2386](https://github.com/aleskalfas/project-kit/issues/2386)). Three readings decided verdicts that the method's words left open:
- **A use case that ends in another.** Two use cases end with the release step. Each names its actor's own release use case in its last step, and each one's postconditions are the release's outcome.
- **What it is to take a use case.** Others start two of the AI agent's use cases and carry them out. The operator's sync, or the adopter's install, does the work, and the agent finds the result.
- **Signs beyond a precondition.** One of the operator's use cases starts where another of the operator's did not meet its goal. Its preconditions name no such use case, and the authoring skill looked for paths through preconditions alone.

The reviewer settled each by a reading of their own, which the pull request records ([project-kit#2392](https://github.com/aleskalfas/project-kit/pull/2392)). Another reviewer could read each the other way. Nothing records a reviewer's judgement that use cases make no path (DEC-005, Rationale), so no later reviewer can build on it. [project-kit#2391](https://github.com/aleskalfas/project-kit/issues/2391) asks the method to decide the three.

## Decision

**An actor's own use cases are those whose goal is its own, whoever does their work. Any hand-over one of them states with another is a sign of a path, never proof. A step that names the next use case hands over to it, and a use case reaches alone only what its own steps make true. A state left standing, and a goal a run did not meet, join use cases in a path only where one goal joins them.**

### 1. An actor takes each use case whose goal it is

A use case's actor is the one whose goal it is ([software-analysis:DEC-001-software-analysis-discipline] point 1). That actor takes the use case, whoever starts it and whoever carries out its steps.
- **Others may do the work.** Another actor may start the use case, or carry out every step of it. An example is a customer's order that a courier brings to the door. The use case is still the customer's.
- **So a path is read among them.** Each use case whose actor it is may be a step of that actor's path. A journey's steps are its actor's own use cases in the same sense (DEC-005 point 2).
- **In turn** is the order of the use cases in the path, each taking up what an earlier one left, whoever starts each of them.
- **What decides a path stays.** Each step takes up what an earlier one left, toward one goal of the actor's that none of them reaches alone (DEC-005 point 2).

### 2. A sign of a path is any hand-over a use case states

A use case may state a hand-over with another use case of the same actor. It takes up what the other leaves, or the other takes up what it leaves. Each such statement is a sign of a path, never proof, in whichever part it stands:
- **A precondition** that the other use case makes true (DEC-005 point 2).
- **A trigger** that is the other use case's end, or a state or a file it leaves. That includes what a run of it leaves where it did not meet the actor's goal, such as a test that failed.
- **A step,** of the main path or of a variant, that takes up a state or a file the other use case leaves. A step that names the other as the work that comes next is one too (point 3).

**Read from the words.** A precondition names its producers by their ids (DEC-001 point 1). A trigger or a step may name the other use case by its id, or only by what it leaves. Either is a sign.

**What is no sign:**
- **A mention that takes nothing up,** such as a step that writes a file as another use case does.
- **Another actor's use case.** It is no step of the path, and the journey relies on it (DEC-005 point 2).

**Judged by DEC-005's test.** For each sign, a reader asks whether the actor takes the two in turn toward one goal none of them reaches alone. Point 4 says how two common kinds of sign meet that test.

### 3. A step that names the next use case hands over to it

A step of a use case's main path or variant may name another use case of the same actor as the work that comes next. An example is an order whose last step names the delivery that brings it.
- **A trigger of its own.** The named use case has one where an event other than that step starts it. That may be its actor's own choice, or the end of the use case that names it. The step then hands over to it, and is a sign of a path (point 2).
- **Part of it.** A use case that runs only inside that step, started by it and by nothing else, is part of the use case that names it. The two make no path.
- **What a use case reaches alone** is what its own steps make true. A postcondition that only another use case's steps make true, such as a parcel delivered, is reached through that use case. So the two may reach together a goal that neither reaches alone.
- **The named use case stays its own.** It keeps its trigger and its other purposes, as one delivery may bring many orders. A journey takes it as a step only of the path that journey tells.

### 4. A standing condition, and a goal a run did not meet

Two kinds of sign meet DEC-005's test in a way of their own. Each time a use case is taken is a run of it.
- **A standing condition.** A state one use case leaves standing, which any number of later runs rely on, is a standing condition for them. It joins a later use case in a path only where the actor takes the two in turn toward one goal. An example is a first purchase, which takes opening an account and then placing an order.
- **Served without end.** A goal served again each time a later run relies on the state joins no path, since a path ends (DEC-005 point 2). An example is a saved card, which serves every later order.
- **Taken up once.** A hand-over that the next run takes up once, such as a parcel that one delivery brings, is no standing condition.
- **A goal a run did not meet.** What one run leaves where it did not meet the actor's goal, such as a test run's failures, is a sign like any other. It makes a path with the use case that takes it up only where one goal joins the two. Knowing why a suite fails joins running it and reading a failure.
- **A remedy.** A use case that only restores the other's goal makes no path toward it, where the other's main path reaches that goal alone.
- **Met because of a standing state.** What later runs meet because of a state left standing is read as a standing condition, not as a goal a run did not meet.

### What this refines, and what stands

This record refines DEC-005 point 2, which names what it adds with a pointer to this record. It overturns nothing.
- **Stands:** what a path is, its seams, what tells it, its course across areas, and another actor's use case on the way (DEC-005 point 2). That a sign is never proof stands too.
- **Unchanged elsewhere:** a use case's parts, and what each holds (DEC-001 point 1). This record reads them for a path, and asks nothing new of them.

## Rationale

**Why the actor whose goal it is.** The analysis already says whose a use case is. It is one actor's goal, and the other actors who take part in it stand apart (DEC-001 point 1). A path reaches a goal of the actor's, and who carries out a step does not change whose goal it serves. Use-case practice names the primary actor by its goal, and the one who triggers a use case may be another (Cockburn, *Writing Effective Use Cases*).

**Why every hand-over is a sign.** A seam is a hand-over, whichever part of a use case states it (DEC-005 point 2). A precondition holds before a use case starts, and no step checks it (DEC-001 point 1). A trigger says when a use case starts, and a state that holds only in some cases is a variant's. So a hand-over a trigger or a step states may have no precondition to show it.

**Why a step that names the next use case hands over.** A trigger of its own shows that the named use case is taken apart from the step, at its own time. The hand-over is then a seam where the path can break, such as an address the order holds against the one the courier reads. A journey anchors both use cases, so a change to either flags it. Use cases anchor no use case, so a step that names the next one flags nothing when that one changes (DEC-001 point 4).

**Why a use case reaches alone only what its own steps make true.** A postcondition may state an outcome that the next use case brings. Credited to the use case that states it, such a postcondition would hide a path behind one use case's promise. A writer could then spare a journey by naming the next use case in a last step. A use case's own steps are what it does, which a reader can check against each postcondition.

**Why a use case that runs only inside a step is part of it.** It runs once in each run of the use case that names it, as UML's include relation inserts one use case's behaviour into another's. It is how the use case does its step, not a goal the actor takes in turn. A journey of the two would tell no hand-over that a later step could break apart from the first.

**Why a goal a run did not meet is a sign too.** What the run did not meet is still what it left, such as a test run's failures. The path can break at that hand-over as at any other. Left out, such a seam would stay unwritten, and a change that breaks it would flag nothing (DEC-005, Rationale). The one-goal test still turns a mere remedy away, where the goal it restores is one the other's main path reaches alone.

**Why a standing condition is read apart.** A hand-over taken up once ends, as one delivery brings one parcel. A state that later runs rely on without end gives no end-to-end sequence for a journey to tell. So such a state joins a path only where the actor takes the use cases in turn toward one goal, as a first purchase does. What later runs meet because of that state is read the same way, or two readings would disagree on one hand-over.

**What it costs.**
- **More to read.** A reader reads each trigger and each step for what it takes up from the actor's other use cases, by id or by words. No diagram draws them, and each sign still needs a reader's judgement.
- **More journeys.** A path whose first use case names the next in its last step needs a journey where an analysis read it as none. So does a path whose hand-over stands only in a trigger or a step. The change that brings an analysis to this record says which of its verdicts change.
- **A goal to name.** Whether one goal joins the use cases behind a sign stays a reading. This record narrows it, and leaves it to a reviewer (DEC-005 point 5).

### Alternatives considered

- **An actor takes only a use case it starts, or one whose steps it carries out.** Rejected. A use case's actor and the actor that takes it would be two, and no field records the second. A goal others carry out for the actor could then be no step of its path.
- **Use cases that others carry out read as making no path, whatever they hand over.** Rejected, for the same reason.
- **A precondition as the only sign.** Rejected. It misses a path whose hand-over a trigger or a step states.
- **Every hand-over written as a precondition, so one sign serves.** Not taken. A trigger says when a use case starts, and a state that holds only in some cases is a variant's (DEC-001 point 1).
- **A goal a run did not meet read as no sign.** Rejected. It would leave out the path that reads why a run failed, whose seam breaks as any other does.
- **A use case that ends in another read as one use case, where its postconditions wait on the other's work.** Rejected. The writer's postconditions would decide it, so a writer could spare a journey by stating the next use case's outcome. A postcondition that promises what later runs will do reads either way. A change to the named use case would flag nothing.
- **The last step alone read as making the named use case part of its use case.** Rejected. A step's place says nothing of whether the named use case is taken on its own.
- **Each use case ends at its own goal, and no step names the next use case's work.** Not taken. It would rewrite each use case that names the next one, though the link already leads a reader on (DEC-001 point 14). The hand-over is a sign either way.
- **A rule that a trigger or a step names the use case it takes up from by its id, so a script finds each sign.** Not taken yet. It asks something new of every use case's words, which no rule holds now. The trigger to weigh it is a path missed because its sign stood only in words (COR-007).
- **A field that records each sign.** Not taken. Whether a trigger or a step takes something up is read from its words. DEC-005 rejected a report of chains no journey tells, which would never clear.
- **The three edges left to each reviewer.** Rejected. Each could be read either way, and no record keeps a judgement of no path.

## Implications

- **DEC-005 point 2** names what this record adds, with a pointer to it. Its Rationale's account of a path left untold names a trigger and a step too.
- **`SAN`'s rule on areas and journeys,** `RS-SAN-014`, states these readings where its *A path* reads them. A change that alters a trigger or a step can leave a path untold too, and the rule names it.
- **The authoring skill** says how to judge each edge where it asks whether use cases make a path. That is its procedure for a journey, and the build order's step 4.
- **No tool reads a sign from words.** The capability's diagram of the chain draws the producers that preconditions name, and a reader reads the triggers and the steps (DEC-005 point 5).
- **An analysis written before this record** may hold a path no journey tells. Its hand-over may stand only in a trigger or a step, or in a last step that names the next use case. A reviewer finds it once `RS-SAN-014` binds.
