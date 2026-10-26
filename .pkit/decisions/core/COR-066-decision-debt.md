---
id: COR-066
title: Decisions land only accepted, and what is not carried out is listed
status: proposed
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a decision record or a rule is a proposal only inside the change that proposes it. A person accepts it there, before work rests on it, and it reaches the default branch accepted. Once a record is accepted, each of its points is marked where the system carries it out: an artefact, such as a document, names the point as one it carries out, beside its anchors on what carries it out. A reviewer checks each mark, and friction asks again whenever what it anchors changes. A point that needs nothing to carry it out says so in its record, and a person accepts that with the record. One command lists the decision debt: what is proposed on the default branch, each accepted point neither marked nor named so, and each mark gone stale. A project chooses when it starts tracking.

## Context

The decision-record specification and [COR-025](COR-025-adr-decision-space.md) let a record land on the default branch as `proposed`, and be accepted later in a separate step. [COR-051](COR-051-rule-sets.md) point 4 gives rules the same statuses. A proposed record or rule binds nothing, and accepting one stays a person's ([COR-064](COR-064-answer-delegate.md) point 6), so no agent decides alone. A proposal that lands, though, stays on the default branch with nothing to end it: it reads like a decision beside the accepted ones, and later work may build on it or decide its question without citing it.

[COR-065](COR-065-records-and-projection.md) makes the rest of the system, where an accepted record decides, its projection. Nothing yet shows, for each point of an accepted record, whether anything carries it out. A decision can be accepted and forgotten, with no sign anywhere that the system never followed it.

[COR-050](COR-050-anchors-and-friction.md) already gives an artefact anchors, including anchors on one point of a record, answers when what an anchor stands on changes, a reviewer who checks the answers a change writes, and debt derived from history.

## Decision

**Nothing proposed reaches the default branch. Each point of an accepted record is marked by an artefact that declares it carries the point out, or is named in its record as needing nothing to carry it out. The decision debt is derived from those marks and names, and one command lists it.**

### 1. Nothing proposed reaches the default branch

A decision record or a rule is proposed only within the change that proposes it. A person accepts it in that change, before work in the change rests on it, and an agent writes `accepted` only once a person has; until then it reads `proposed` on its branch. Work in a change built on that one may rest on it once it is accepted, and reaches the default branch no earlier than that change does. A proposal that is refused is the change closed, so it never lands. A refused proposal whose reasoning is worth keeping becomes a scratchpad note, abandoned with the reason it was refused ([COR-012](COR-012-scratchpad-notes.md)).

A check of its own, apart from a change's other checks, reports each record or rule proposed at the change's head and not proposed at its base: an added proposal, or an accepted one set back to proposed. A record or rule moved to another path is not added. The check fails while it reports one. A component that authorises merges runs it before it merges, after the reviewers have judged the change, proposal included, and refuses to merge while it fails. A project without such a component requires the check for a merge, as a check of its own, so its failure while a proposal is discussed hides no other. A check run before a push leaves it out.

The same check lists each record and rule the change makes accepted, added accepted or set to accepted. For each, it shows the commit that set it to accepted, the change's commits before that one that touch anything else, and the record's edits since. Whoever authorises the change to reach the default branch sees that list first, through a component that authorises merges or, without one, from the change's author, and reads there the text that lands. An edit made to a record after its acceptance in the change is accepted only so. The check cannot tell who wrote a status: where no component shows the list, only the author's word says the person saw it.

A proposed record or rule already on the default branch is listed as debt (point 4), and blocks no change. A record or rule a project receives from elsewhere is judged where it is kept: the check skips it, and it is never the receiving project's debt.

This overturns COR-025's "ADRs land as `proposed`", and the specification's practice of landing records proposed. A person's acceptance stays a separate act, made within the change. The statuses stand: a proposed record or rule binds nothing, and it exists only on the branch of the change that proposes it.

### 2. A point is marked by an artefact that declares it carries the point out

An artefact other than a record, held in a declared place (COR-050 point 1) and not under an excluded path (COR-050 point 7), marks a point of an accepted record when it names that point, in a field beside its anchors, with those of its anchors that name what carries the point out: code, a schema, a skill, a configuration or other content. Each anchor a mark names is one of the artefact's, and not an anchor on a record. A mark names none only where the artefact's own text carries the point out, such as a specification that states a rule. A change to what those anchors name asks whether the artefact still holds.

A record whose decision has no points, or holds them in list form (COR-058 point 2), is **tracked whole**: a mark names the record, and marks it whole.

An anchor with no mark marks nothing. An artefact may anchor a point it rests on, states, plans or says is not yet carried out, as COR-050 point 2 allows, and the point stays debt. A record marks no other record's points, since it decides and carries nothing out.

The work that carries a point out writes or updates the artefact with its mark, in the same change, as it writes the answers that change owes: that is how an agent marks a point carried out. A point the system carries out with no artefact describing how stays on the list, so the debt also shows what is undocumented. A project that keeps no artefact in a declared place has all its points as debt, and may leave tracking off (point 5).

A mark is not a proof. It says where its writer judged the point is carried out. Friction's change check (COR-050) lists each mark a change adds or removes, and a reviewer other than its writer checks it against what its anchors name, as for an answer (COR-050 point 3). Friction keeps asking whether it holds after. A change that leaves the artefact saying the point is no longer carried out removes the mark, and the reviewer checks that it does.

### 3. A point that needs nothing to carry it out is named in its record

A point of an accepted record that needs nothing to carry it out, because it decides a principle no artefact carries, is named in the record's front matter as having **nothing to carry out**, with a sentence saying why. A record tracked whole is named so only where none of it needs carrying out. A person accepts each name with the record, or, for a name added to an accepted record, in the change that adds it, which lists it among that record's edits.

A point with a heading that a later accepted record overturns whole owes nothing while that record stands: the overturning record names it in its own front matter. A point overturned in part is not named, and owes a mark for what stands. The overturned record gains only the top line the specification gives it. A record tracked whole stays tracked whole when part of it is overturned.

Validation warns ([COR-055](COR-055-validation.md) point 4) of a mark or a name for a point its record does not hold as a live point, and of a point both marked and named. It also warns of a mark or a name of the whole of a record whose points have headings, which counts for each of its points until it is moved to them. Every other point no artefact marks is debt until one does.

A rule is not marked: the checks that enforce it, where a project runs them (COR-051 point 2), and the reviewer that judges a change against it ([COR-057](COR-057-rule-set-reviewer.md)) carry it out.

### 4. The decision debt is derived, and one command lists it

The **decision debt** of a project is derived from its records, the artefacts that mark them, and their history, each time it is read, and kept nowhere (COR-050 point 9). One command lists it:

- each proposed record or rule of the project's own on the default branch, with its age;
- each point of an accepted record of the project's own that is tracked (point 5), or each such record tracked whole, that no artefact marks and no record names, with the age since it was accepted;
- each mark whose artefact is stale on one of the mark's anchors, or deferred, as friction reports it.

A record superseded whole owes nothing. The command reads only what the repository holds, and fails nothing.

### 5. A project chooses when tracking starts

Point 1 binds every project. A project turns on point 1's check, and the debt list, with a key in its backbone configuration that this record owns ([COR-048](COR-048-backbone-configuration.md) point 2). With the key absent, tracking is off. The list of what a change makes accepted is shown either way. The key counts as the default branch holds it when a check runs, so a change that turns it on or off counts only once it has landed, and the person who authorises that change sees it. Its writers are an install and a change a person authorises, each with consent as COR-048 point 5 asks. An upgrade does not write it.

The **starting line** is the first commit, along the default branch's own line of commits, that turned tracking on. Turning tracking off stops point 1's check and the debt list, and turning it on again keeps the line where it was. A point is **tracked** when the change that added it to an accepted record, or accepted its record, reached the default branch after the starting line, and so is a record tracked whole. A point converted from a list (COR-058 point 9), or split from another (COR-058 point 4), is as old as the text it came from.

A point or record accepted before the line is listed apart, as accepted before tracking, until an artefact marks it or a record names it, and no later edit ends that. No one owes it backwards: that list is expected to remain, and shrinks as changes touch its records.

## Rationale

**Why nothing proposed lands.** Accepting a decision stays a person's so that no agent decides alone. A proposal that lands keeps that promise, since it binds nothing, but it stays: it sits beside accepted records, where readers and agents meet it, and work builds on it or around it. Kept inside its change, a proposal is either accepted or closed, and the default branch holds only what a person decided. The change is the place to discuss and refine a proposal, so nothing is lost.

**Why acceptance comes first, and is shown again at landing.** A person accepts a record before work rests on it, as COR-065 point 3 asks. The check sees only a change's commits, not who wrote them, so refusing only the word `proposed` would push an agent to write `accepted` itself. The list at landing shows the person who authorises the merge each acceptance, the commit that made it, the work that came before it and every edit since. An acceptance no person gave, or text changed after it, is then seen before it lands. Without a component that shows it, this rests on the author's word, as an answer's evidence does (COR-050 point 3).

**Why the refusal is a check of its own.** A proposal is pushed, reviewed and revised in its change before a person accepts it. A failure among the change's other checks would block the push where a hook runs them, stop the reviewers where the merge waits for every check to pass, and hide the other failures. A check of its own, run where the merge is decided, refuses only the merge.

**Why rules too.** A proposed rule is a draft awaiting the same acceptance. What it would report can be shown on the branch that proposes it, before it binds. A rule set that never holds a proposed rule on its default branch never delivers one to a project that receives it. There are two costs. A rule is accepted in the change that adds it, so a rule set gathers its new rules into one change where it wants them in one version. And a proposed rule is tried only on the changes its proposing branch has the reviewer judge, where one on the default branch was reported, to inform, on every change (COR-057).

**Why a mark is declared, not read from any anchor.** An anchor on a point carries other relations: a design written before the code anchors the point it plans, and a requirement anchors the decisions that answer it. Counting every anchor as a mark would clear the debt before the work is done. A mark names the anchors on what carries its point out, so a decision carried out and later undone asks again when that content changes. A reviewer checks the mark, and each point is tracked on its own. The record stays free of paths, and a change to busy code asks for answers only from the artefacts that describe it.

**Why the name sits in the record.** That a point needs nothing to carry it out says what kind of choice it is, not how far the system has got. It changes only when the point does, so it sits with the point's text and is accepted with it, by a person, never by an agent alone. These names change nothing an artefact resting on the record relies on, so they are not text an anchor on the record stands on. A person asked to read many such names at once would stamp them, so the list of points accepted before tracking is cleared as changes touch its records, not all at once. A point a later record overturns is named in that record, since a record whose points have no headings could otherwise only be named whole, falsely.

**Why a point not yet carried out has no entry.** It is the debt, and the list shows it with its age. A line in an artefact saying the work is still to come informs that artefact's readers (COR-065 point 6); the list is where the lag is tracked.

**Why the debt is derived.** A stored list of open decisions drifts from the records and the code. Derived from the marks, names and history each time, the debt is always what the files say, as friction's debt is.

**Why tracking waits for its key, and its line is held by the default branch.** A project that adopts this has open changes and many accepted points with no marks. An upgrade that refused proposals at once would stop the open changes that hold one, and counting every old point as debt would bury the debt that matters under history no one will answer soon. So a project starts when it chooses, and a new one starts at once. The list of what a change makes accepted costs nothing backwards, so it is shown either way. Held by the default branch, the key cannot be moved by the change it would check, and order read along the default branch's own line counts a record accepted on a branch from when it landed.

### Alternatives considered

- **Keep landing records proposed, and list the old ones.** Rejected: a landed proposal reads like a decision, and nothing ends its life.
- **The refusal fails among a change's other checks.** Rejected: it would block a proposal's push where a hook runs those checks, stop the reviewers where the merge waits for every check to pass, and hide other failures.
- **The refusal fails only in the run that lands the change.** Rejected: on a host with no landing command, that run cannot be told apart.
- **Every anchor on a point marks it.** Rejected: anchors carry other relations, and the debt would clear before the work is done.
- **A separate answer for each point**, saying it is carried out, deferred or needs nothing. Rejected: a second kind of answer beside friction's, with rules of its own, and a "carried out" that stays true after the code that carried it out is gone.
- **The record anchors the code that carries it out.** Rejected: a record's anchors cover the whole record, so a record carried out in part leaves the debt; a change to busy code would ask for answers from every record anchoring it; and code a record anchors would count as described when no document describes it.
- **A field in the record that marks it carried out.** Rejected: it is state inside the choice, and it never goes stale when the code changes. A name for a point needing nothing is not state, so it stays.
- **Names kept in the project's answer folder** ([COR-062](COR-062-answers-in-own-files.md) point 2). Rejected: a name is part of the choice the person accepts, so it belongs with the record's text and its acceptance.
- **The overturned record names its overturned points.** Rejected: a record whose points have no headings would have to be named whole, falsely.

## Implications

- **COR-025** gains a first line saying it is partially superseded by this record, for landing records proposed. **COR-050** is refined in place, the refinement citing this record: an artefact may hold marks, each naming a point and anchors of its own; friction's change check lists each mark added or removed for the reviewer; and a record's names of points needing nothing, or of points it overturns, are not text an anchor on the record stands on. **COR-064** is unchanged: the delegate decides no name, and marks are written with the work, as the answers a change owes are.
- **The decision-record specification** says a record reaches the default branch accepted, after a person accepts it in its change. Its acceptance gate counts a record a person accepted in the change, or in a change it is built on. It gives the front matter that names points needing nothing, and the points a record overturns. Its check of a change on records lists a change to those fields among an accepted record's edits, and reads rules through their own reader.
- **A component that authorises merges** runs the reviewers on a change that holds a proposal, shows the person one list of what the change decides (the records and rules it makes accepted, beside the edits to accepted records it already lists), and runs point 1's check before it merges.
- **A project's checks run before a push**, and those every change must pass, leave point 1's check out; where no component authorises merges, it is required for a merge as a check of its own.
- **The authoring skill for records and the agent that authors architecture records** have a person accept a record in its change before work rests on it, and name in its front matter each point needing nothing, for the person to accept with it.
- **A command** lists the decision debt, and the backbone configuration holds the tracking key.
- **The proposed records and rules on a project's own default branch, when it starts tracking**, are its first debt. A record is accepted by a person or deleted, since a record has no state for a refused proposal. A rule is accepted or withdrawn, which keeps it in place binding nothing (COR-051 point 4).
- **An architecture record realizes this record**: the mark's field, the front matter of names, point 1's check and how it reads rules, the command and the key.
