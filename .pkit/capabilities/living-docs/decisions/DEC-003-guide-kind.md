---
id: DEC-003
title: A guide page says why its subject exists, then how its tasks are done
status: accepted
date: 2026-10-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability ships a page kind for explaining, `guide`. A guide tells its reader why a subject exists, what it solves for them and how they do its tasks. It opens with its title and a lead, then says why the subject exists, then gives the reader's tasks. Where it is a folder's entry page, it ends with the folder's pages. How a guide argues its case, such as by a comparison or a proof, each project adds in its own rules. The validator checks only that a guide has a title. Whether it holds the rest, in order, is judged by the reviewers and decided by people.

## Context

[living-docs:DEC-001-living-docs-discipline] point 3 says that pages of a kind follow one format, with a template per kind (RS-LDOC-004). It calls the part of the format a tool checks the kind's *structure*, which the capability declares for each kind it ships. A page whose kind declares no structure is reported with its kind and never failed.

A page that describes a surface to the reader who uses it says first what the surface is for, then how it is used and the rules and facts true of it. A signpost says what a folder holds (RS-LDOC-005). Neither makes the case for its subject: a reader who has not yet chosen the subject, or who needs to know why it exists before using it, finds no page shaped for that. The capability's README lists the kinds it ships.

The methodology's own documentation wrote its first such page, and named its kind `guide` before the capability shipped one ([project-kit#2012](https://github.com/aleskalfas/project-kit/issues/2012)). It plans one for each of its areas. Nothing checks such a page against a format. On [project-kit#2060](https://github.com/aleskalfas/project-kit/issues/2060) its maintainer asked that the capability ship the kind, for "a page that explains an area to people, why it exists, what it solves and how to do its tasks".

## Decision

**The capability ships the page kind `guide`, for a page that explains one subject to the reader who uses it. A guide holds its title, a lead, why the subject exists and the reader's tasks, in that order, and a folder's entry page ends with the folder's pages. Its structure, the part the validator checks, is its title.**

### 1. A guide explains one subject to the reader who uses it

A *guide* is a page of the kind `guide`. Its *subject* is one thing the project offers the page's reader, such as an area, a component, a tool or a feature.
- **What it says:** why the subject exists, what problem it solves for the reader, and how the reader does its tasks.
- **What it leaves to other pages:** detail a reader looks up rather than reads through, such as each option of a command or each key of a file. Where the guide summarises such a fact, it links and anchors the fact's home, as the rule on one home asks of any page (DEC-001 point 3).
- **Telling it from a page that describes a surface:** a guide's first section after its lead says why its subject exists, and the guide leaves the detail to look up to other pages. A page that describes a surface opens with what the surface is for, and goes on to how it is used and what is true of it.

### 2. A guide holds the why, then the tasks

A guide's format holds these parts, in this order, and its template shows them:
- **Its title,** a level-1 heading naming the subject.
- **A lead:** a paragraph saying what the subject is, for this reader, and which page describes it, where one does. A contents list may follow the lead.
- **Why the subject exists:** the problem it solves for the reader. It is the first section after the lead and any contents list.
- **The reader's tasks:** a section for each task the guide teaches. A task comes after any task it needs done first. The tasks' sections may stand under one heading that gathers them.
- **The folder's pages, last,** where the guide is a folder's *entry page*, such as its README, and the folder holds further pages for the guide's reader. Each such page is listed with a line on what the reader finds there, in the order the reader takes them. The list takes a signpost's form (RS-LDOC-005). The guide's why and tasks are its own, never a summary of those pages.

A section on how the subject works may stand anywhere after the why, where its reader needs one. A guide may carry other sections, such as the project's own case (point 3), where they keep this order. The writer words every heading.

### 3. How a guide makes its case is the project's

How a guide argues for its subject is left to each project: whether it proves what it claims, compares the subject with what its reader would otherwise use, says when the reader does not need it, or shows an example first. A project that wants such rules keeps them in a rule set of its own, scoped to where its guides lie (COR-051 point 2).

### 4. A guide's structure is its title

The structure the capability declares for `guide` is one section: a level-1 heading the writer words. The validator checks it where the one-format rule (RS-LDOC-004) binds on the page (DEC-001 point 3). Whether a guide holds the other parts of point 2, in order, is judgment under that rule:
- **On a change** that alters the guide, the rule-set reviewer judges it (COR-057). Where the rule's own words do not settle a break, a person decides it.
- **In reader-review,** the capability's agent judges it (DEC-001 point 6).

### 5. The shipped kind takes the name `guide`

Every page that names `guide` in its `kind` field follows this format, whoever wrote it. A project with a kind of its own named `guide` follows this format, or renames its kind.

## Rationale

**Why a kind of its own.** A page that describes a surface serves a reader who has chosen the surface and comes to use it, so it puts the surface's purpose and use first. A guide serves a reader who needs the reason first: one who has not chosen the subject, or who must understand it to use it well. The two differ in what comes first and in what they leave to other pages, so they are two kinds.

**Why the why comes first.** A reader decides from the problem whether the subject is for them. A guide that opens with its mechanism makes them read how something works before they know whether they need it. The cost falls on a reader who comes for one task, who passes the why first. A contents list after the lead sends that reader on.

**Why tasks, in the order they depend on each other.** A reader comes to a guide to do something. A task placed before the task it needs fails for the reader who follows the page in order.

**Why the folder's pages come last.** A reader who opens a folder's entry page learns there why the subject exists and does its common tasks. The folder's other pages are where that reader goes next. A reader who wants only the list reaches it from the contents list.

**Why the case is the project's.** What persuades a reader differs between projects and audiences. A rule on proof, comparison or limits that suits a tool's entry page would bind every guide of every project that adopts the capability. Such rules belong in the shared set only once more than one project has tried them.

**Why the structure is the title alone.** Every other heading of a guide is worded by its writer, in the page's language. A fixed heading such as "Why" would bind every project's wording and language. A structure of levels alone, a title and some second-level sections, passes any page that has headings, and tells nothing of whether the page holds its why or its tasks. So what each section says stays judgment, and the structure names only what every guide carries, as DEC-001 point 3 asks of a structure. The cost is that no check fails a guide that lacks its why. A project that wants its guides' sections checked by their wording declares a check of its own for that part of a rule of its own (COR-051 point 2).

**Why the shipped kind takes the name.** A page names its kind by one word, with no owner in it, so one word means one kind in a project. Were a project's own `guide` kept apart, nothing could tell which format a page that names it follows.

### Alternatives considered

- **Guides as pages that describe a surface,** of the kind that already ships. Rejected. The two differ in what comes first and in what they leave to other pages (Rationale).
- **Separate kinds for explaining a subject and for doing its tasks,** as documentation typologies such as Diátaxis split explanation from how-to guides. Not taken. A reader of one subject finds its why and its common tasks on one page. A page that teaches one task alone can come as a kind of its own once such a page is written.
- **Fixed headings,** such as "Why" and "Tasks", in the structure. Rejected. They bind every project's wording and language.
- **A structure of levels,** a title and at least two second-level sections. Rejected. Any two headings pass it, so it fails no page that lacks its why.
- **Sections marked by their role,** such as by an HTML comment before each, which the validator could check for order without fixing wording. Not taken. It asks markup of every guide in every project, for a check of order alone.
- **A rule of the shared set that names a guide's order.** Not taken now. It would let the rule-set reviewer settle a break of the order from the rule's own words. But a new rule binds only from the shared set's next major (COR-051 point 7), and the format already stands under the one-format rule.
- **A comparison, a section on when not to use the subject, and a first example in the format.** Not taken. They suit an introducing page more than every guide, and are a project's choices (point 3).
- **Kinds named with their owner,** such as `living-docs:guide`, so a project's own `guide` keeps its name. Rejected. It changes the kind every page names, for a clash a rename settles.

## Implications

- **The capability** ships the kind's template, and declares its structure beside the other kinds'. The authoring command stamps a guide as it stamps any kind the capability declares. The capability's README lists the kind.
- **A page that names `guide` already** is checked against the structure where the one-format rule binds on it, and judged against the format (point 5). One whose title the validator does not read as a level-1 heading passed before and then fails, such as a page with no title or with an HTML heading. So shipping the kind is a breaking change of the capability (DEC-001 point 3), which its release notes say.
- **The capability's agent and its authoring skill** read the guide's template beside the other kinds'.
