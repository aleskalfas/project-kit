---
id: COR-067
title: Each accepted point is marked where the system carries it out
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** once a record is accepted, each of its points is marked where the system carries it out. An artefact, such as a document, names the point as one it carries out, beside its anchors on what carries it out. A reviewer checks each mark, and friction, the check that asks whether an artefact still holds when what it rests on changes, asks again whenever what the mark anchors changes. A point that needs nothing to carry it out says so in its record, and a person accepts that with the record. One command lists the decision debt: what is proposed on the default branch, each accepted point neither marked nor named so, and each mark gone stale. A project chooses when it starts tracking.

## Context

[COR-065](COR-065-records-and-projection.md) makes the rest of the system, where an accepted record decides, its projection. Nothing yet shows, for each point of an accepted record, whether anything carries it out. A decision can be accepted and forgotten, with no sign anywhere that the system never followed it.

[COR-050](COR-050-anchors-and-friction.md) already gives an artefact anchors, including anchors on one point of a record, answers when what an anchor stands on changes, a reviewer who checks the answers a change writes, and debt derived from history. [COR-066](COR-066-accepted-before-landing.md) has a record reach the default branch only accepted.

## Decision

**Each point of an accepted record is marked by an artefact that declares it carries the point out, or is named in its record as needing nothing to carry it out. The decision debt is derived from those marks and names, and one command lists it.**

### 1. A point is marked by an artefact that declares it carries the point out

An artefact other than a record, held in a declared place (COR-050 point 1) and not under an excluded path (COR-050 point 7), marks a point of an accepted record when it names that point, in a field beside its anchors, with those of its anchors that name what carries the point out: code, a schema, a skill, a configuration or other content. Each anchor a mark names is one of the artefact's, and not an anchor on a record. A mark names none only where the artefact's own text carries the point out, such as a specification that states a rule. A change to what those anchors name asks whether the artefact still holds.

A record whose decision has no points, or holds them in list form ([COR-058](COR-058-record-points.md) point 2), is **tracked whole**: a mark names the record, and marks it whole.

An anchor with no mark marks nothing. An artefact may anchor a point it rests on, states, plans or says is not yet carried out, as COR-050 point 2 allows, and the point stays debt. A record marks no other record's points, since it decides and carries nothing out.

The work that carries a point out writes or updates the artefact with its mark, in the same change, as it writes the answers that change owes: that is how an agent marks a point carried out. A point the system carries out with no artefact describing how stays on the list, so the debt also shows what is undocumented. A project that keeps no artefact in a declared place has all its points as debt, and may leave tracking off (point 4).

A mark is not a proof. It says where its writer judged the point is carried out. Friction's change check (COR-050) lists each mark a change adds or removes, and a reviewer other than its writer checks it against what its anchors name, as for an answer (COR-050 point 3). Friction keeps asking whether it holds after. A change that leaves the artefact saying the point is no longer carried out removes the mark, and the reviewer checks that it does.

### 2. A point that needs nothing to carry it out is named in its record

A point of an accepted record that needs nothing to carry it out, because it decides a principle no artefact carries, is named in the record's front matter as having **nothing to carry out**, with a sentence saying why. A record tracked whole is named so only where none of it needs carrying out. A person accepts each name with the record, or, for a name added to an accepted record, in the change that adds it, whose check of a change on records lists the name among that record's edits.

A point with a heading that a later accepted record overturns whole owes nothing while that record stands: the overturning record names it in its own front matter. A point overturned in part is not named, and owes a mark for what stands. The overturned record gains only the top line the specification gives it. A record tracked whole stays tracked whole when part of it is overturned.

Validation warns ([COR-055](COR-055-validation.md) point 4) of a mark or a name for a point its record does not hold as a live point, and of a point both marked and named. It also warns of a mark or a name of the whole of a record whose points have headings, which counts for each of its points until it is moved to them. Every other point no artefact marks is debt until one does.

A rule is not marked: the checks that enforce it, where a project runs them (COR-051 point 2), and the reviewer that judges a change against it ([COR-057](COR-057-rule-set-reviewer.md)) carry it out.

### 3. The decision debt is derived, and one command lists it

The **decision debt** of a project is derived from its records, the artefacts that mark them, and their history, each time it is read, and kept nowhere (COR-050 point 9). One command lists it:

- each proposed record or rule of the project's own on the default branch, with its age, which COR-066 points 1 and 4 have a person settle;
- each point of an accepted record of the project's own that is tracked (point 4), or each such record tracked whole, that no artefact marks and no record names, with the age since it was accepted;
- each mark whose artefact is stale on one of the mark's anchors, or deferred, as friction reports it.

A record superseded whole owes nothing. A record or rule a project receives from elsewhere is never its debt. The command reads only what the repository holds, and fails nothing.

### 4. A project chooses when tracking starts

A project turns tracking on with a key in its backbone configuration that this record owns ([COR-048](COR-048-backbone-configuration.md) point 2). With the key absent, tracking is off and the debt is not listed. The key counts as the default branch holds it, so a change that turns it on or off counts only once it has landed. Its writers are an install and a change a person authorises, each with consent as COR-048 point 5 asks. An upgrade does not write it.

The **starting line** is the first commit, along the default branch's own line of commits, that turned tracking on. Turning tracking off stops the listing, and turning it on again keeps the line where it was. A point is **tracked** when the change that added it to an accepted record, or accepted its record, reached the default branch after the starting line, and so is a record tracked whole. A point converted from a list (COR-058 point 9) is as old as its record. A point split from another (COR-058 point 4) under a new id counts from the change that split it.

A point or record accepted before the line is listed apart, as accepted before tracking, until an artefact marks it or a record names it, and no later edit ends that. No one owes it backwards: that list is expected to remain, and shrinks as changes touch its records.

## Rationale

**Why a mark is declared, not read from any anchor.** An anchor on a point carries other relations: a design written before the code anchors the point it plans, and a requirement anchors the decisions that answer it. Counting every anchor as a mark would clear the debt before the work is done. A mark names the anchors on what carries its point out, so a decision carried out and later undone asks again when that content changes. A reviewer checks the mark, and each point is tracked on its own. The record stays free of paths, and a change to busy code asks for answers only from the artefacts that describe it. Marks also lead from a changed path to the points it carries out, for the reading COR-065 point 7 asks.

**Why the name sits in the record.** That a point needs nothing to carry it out says what kind of choice it is, not how far the system has got. It changes only when the point does, so it sits with the point's text and is accepted with it, by a person, never by an agent alone. These names change nothing an artefact resting on the record relies on, so they are not text an anchor on the record stands on. A person asked to read many such names at once would stamp them, so the list of points accepted before tracking is cleared as changes touch its records, not all at once. A point a later record overturns is named in that record, since the overturning is that record's decision, and the overturned record gains only the top line the specification gives it.

**Why a point not yet carried out has no entry.** It is the debt, and the list shows it with its age. A line in an artefact saying the work is still to come informs that artefact's readers (COR-065 point 6); the list is where the lag is tracked.

**Why the debt is derived.** A stored list of open decisions drifts from the records and the code. Derived from the marks, names and history each time, the debt is always what the files say, as friction's debt is.

**Why tracking waits for its key, and its line is held by the default branch.** A project that adopts this has many accepted points with no marks. Counting every old point as debt would bury the debt that matters under history no one will answer soon. So a project starts when it chooses, and a new one starts at once. Order read along the default branch's own line counts a record accepted on a branch from when it landed. A split point's new id records no origin, so it counts as new.

### Alternatives considered

- **Every anchor on a point marks it.** Rejected: anchors carry other relations, and the debt would clear before the work is done.
- **A separate answer for each point**, saying it is carried out, deferred or needs nothing. Rejected: a second kind of answer beside friction's, with rules of its own, and a "carried out" that stays true after the code that carried it out is gone.
- **The record anchors the code that carries it out.** Rejected: a record's anchors cover the whole record, so a record carried out in part leaves the debt; a change to busy code would ask for answers from every record anchoring it; and code a record anchors would count as described when no document describes it.
- **A field in the record that marks it carried out.** Rejected: it is state inside the choice, and it never goes stale when the code changes. A name for a point needing nothing is not state, so it stays.
- **Names kept in the project's answer folder** ([COR-062](COR-062-answers-in-own-files.md) point 2). Rejected: a name is part of the choice the person accepts, so it belongs with the record's text and its acceptance.
- **The overturned record names its overturned points.** Rejected: it would carry, beside its top line, a decision another record made.

## Implications

- **COR-050** is refined in place, the refinement citing this record: an artefact may hold marks, each naming a point and anchors of its own; friction's change check lists each mark added or removed for the reviewer; and a record's names of points needing nothing, or of points it overturns, are not text an anchor on the record stands on. **COR-064** is unchanged: the delegate decides no name, and marks are written with the work, as the answers a change owes are.
- **The decision-record specification** gives the front matter that names points needing nothing, and the points a record overturns, and its check of a change on records lists a change to those fields among an accepted record's edits.
- **The authoring skill for records and the agent that authors architecture records** name in a record's front matter each point needing nothing, for the person to accept with it.
- **A command** lists the decision debt, and the backbone configuration holds the tracking key.
- **An architecture record realizes this record**: the mark's field, the front matter of names, the command and the key, and the lookup from a path to the points its marks carry out.
