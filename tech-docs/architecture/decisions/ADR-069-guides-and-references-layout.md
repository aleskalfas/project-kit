---
id: ADR-069
title: Guides for people sit in docs/, references for agents beside what they describe
status: accepted
date: 2026-10-25
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** people learning project-kit read guides in `docs/`, on GitHub. Agents in an adopter's project read references under `.pkit/`, because only those ship. Each side has a folder per area, led by its README. The reference holds the contract; the guide explains it.

## Context

ADR-055 point 3 makes each adopter-facing README under `.pkit/` a user page, and the documentation rework (EPIC #1928) needs a layout. On 25 October the maintainer split user documentation by audience. Agents in an adopter's project need reference for the installed version, and shipped skills, agents and rules already send them to `.pkit/`'s READMEs. Only `.pkit/` reaches an adopter (COR-049 point 1).

## Decision

### 1. Where pages live

- **Guides** sit in `docs/`, which does not ship. A guide says why an area exists, what it solves, how it compares, and how people do its tasks. `docs/` has a folder per area, capability or adapter, named as under `.pkit/`, and material across the tool at its top.
- **References** sit under `.pkit/`, beside what they describe, and ship. A reference holds the contract an agent acts on: formats, statuses, paths, and what each command does and how it fails. How an area is built goes to the technical space.
- **Agents' task procedures** live in skills, which carry procedure (COR-006).
- **An adapter's references** sit at its top level. Sync copies no adapter subfolder but its core settings, and reads each folder under `.pkit/adapters/` as an adapter.

### 2. An area's guide and reference

- **Each fact has one home** (RS-LDOC-002). A fact a record decides has that record as its home on each page that anchors it, so a guide anchors the record, not the reference. Any other contract fact has its home in the reference, which ships with its version; a guide that summarises it links and anchors that section. The why and people's tasks have their home in the guide, which no reference anchors.
- **A reference's purpose line** rests on its area's or capability's deciding record, which it anchors, so it needs no link to the guide. The guide expands the why.
- **A guide links its reference** by a relative path. A site built from `docs/` alone would break these links, and would have to handle them.
- **A reference links its guide** at the `latest` tag, `https://github.com/aleskalfas/project-kit/blob/latest/docs/<area>/README.md`, and names it in words. The address is project-kit's own fact in project-kit's own text, as its install line already is (PRJ-004). GitHub redirects a moved repository; a fork with guides of its own rewrites the addresses.
- **A linked guide README keeps its path,** since no migration reaches an installed reference. A test of project-kit's own checks that every guide address in the tree's references, and in those of each version tag, names a README in the tree's `docs/`.

### 3. A folder's README leads its pages

A README that is a page leads its folder. Maintainers' sub-READMEs, such as those of templates and migrations, lead nothing.
- **It is the folder's stable address,** and moves only with its folder.
- **Its kind follows its side.** A guide's README is a `guide`: the area's why and common tasks, then its pages in number order. Until living-docs ships that kind, it reports the kind and fails nothing (living-docs DEC-001 point 3). A reference's README is a `reference`: a one-line purpose (point 2), then what it describes. Its list of pages is a signpost (RS-LDOC-005).
- **It anchors each page it lists.** No page anchors its own README, which would make a cycle (COR-050 point 5).
- **Folders are planned** with an area's rework, each created with its first page and its README, so no page moves when the second lands.

### 4. The page rules live in the spaces' rule sets

How pages are written, named and linked is kept as rules of `USER` and `TECH`, which the rule-set reviewer enforces (COR-051). During the rework the user pages' rules sit in the interim set `REWORK`, whose scope lists the reworked pages one by one. Each rule binds once accepted (COR-051 point 4).
- **Every user page,** reference, guide or the top-level `README.md`, follows `LDOC`, `USER`'s own rules, `WRITE`, which `REWORK` inherits, and the rules below.
- **Guides and the top-level `README.md`** also follow the style rules: problem first, proof, comparison, when not to use it, highlights. A scope belongs to a set (COR-051 point 2), so these sit in a set of their own, scoped to `docs/**` and `README.md`.
- **Names:** pages and subfolders read in order are numbered in tens, `010-`, `020-`, and lookup pages take a topic name. A test declared as the rule's check (COR-051 point 2) holds each README's list to the numbers.
- **Moves** fix every link to what moved. A section that leaves a page keeps its old address there as an HTML id.
- **Citations:** a user page cites the core's and the capabilities' records, holds project-kit's own only as anchors, cites no issue and links nothing under `tech-docs/`. A shipped page links nothing unshipped but its guide's README.
- **Backbone pages** are reached through the area's README or by their role, since a component runs across backbone versions.

### 5. Pages and readers of the spaces

This refines ADR-055 point 3.
- **User space:** `README.md`, its entry point; the guides; each reference an adopter's agent reads to use an area, capability or adapter, with the pages its README lists; and `.pkit/README.md`, which signposts the references.
- **Readers:** a guide names `user`, or the analysis actor it serves. A reference names the AI agent, `act-ai-agent`, a reader software-analysis supplies from the analysis's actors (living-docs DEC-001 point 7). That agent uses the system and never needs its internals, so one user space holds both.
- **Area by area:** a shipped README keeps `reader: user` until its area's slice of the rework makes it a reference.
- **Safe for adopters:** in an adopter's project `.pkit/` is a synced tree, never a place (living-docs DEC-001 point 1), so nothing there resolves the shipped id (COR-014).
- **Technical space:** `tech-docs/`, `CONTRIBUTING.md`, and the release guide, `.pkit/release/README.md`, which never ships.
- **A generated file kept fresh by a test** is no page, and sits in a folder of its own (living-docs DEC-001 point 4).

## Rationale

**The contract ships with what it describes.** An adopter's agent never sees `docs/`. Kept in the reference, the contract matches the installed version, and a guide that summarises it is flagged when it changes.

**The newest release's guide.** On `latest`, the link shows the guide for what `@latest` installs (#2052). An older install reads a newer guide, and its own reference decides each contract fact. The default branch would show guides for work no release holds. A version tag would make each release rewrite shipped text, since versions are written only at release (PRJ-002). A component released alone reaches `latest` with the next backbone release, as it reaches a tagged install (PRJ-004). Read the Docs' `stable` is the same kind of address (the note on document versions, `.pkit/scratchpad/active/2026-10-08-document-versioning.md`).

**Addresses read from the tags.** Each version tag holds the references it shipped, so a moved guide fails the test even when nobody remembers the old address. A list kept beside the test would depend on that memory, and forgetting is the slip the test exists to catch. CI's checkout fetches the tags.

**One user space.** Guide and reference link each other, and a documentation site serves one space (living-docs DEC-001 point 1). Scopes give them different rules.

### Alternatives considered

- **Guides installed with the references.** Rejected: every project would carry text its agents do not use.
- **A space of its own for the references.** Not taken: the audience is the same, and a scope already gives the split.
- **A reader of project-kit's own for the references.** Not taken: the analysis already has the actor.
- **The page rules as points of this record.** Rejected: nothing would enforce them page by page.

## Implications

- **The tag first:** no reference links its guide before `latest` exists (#2052, PR #2055).
- **The pilot:** the guide part of the permissions README moves to `docs/permissions/`, which creates the user root (ADR-055 point 1). `.pkit/permissions/README.md` stays, as a `reference` for `act-ai-agent`. Its internals go to the records and code they rest on. Sections that shipped skills, agents and rules name keep their labels.
- **ADR-055 point 3** restates its user-space sentence, and its reason for keeping the `.pkit/` READMEs, as point 5 does, marked `(refinement per ADR-069)`. Its implication on anchors reads "shipped pages". Point 4 settles its open question on links into the decision corpus.
- **Rule sets:** the standing answer on #1928, on what a page that ships may cite, binds every user page (living-docs DEC-001 point 1). The style rules drafted into `REWORK` (#2022) move to the guides' set. At the close, `USER` inherits `WRITE` and takes `REWORK`'s other rules.
- **The AI agent actor** gains the need that references serve. The self-host test on the space's default reader accepts its id.
- **`USER`'s scope** widens to `.pkit/**/*.md`, leaving out `.pkit/release/**`. The places test accepts a page under `.pkit/` that is not a README exactly when its folder's README is a place and lists it. A page beside the `decisions/` or `scratchpad/` README joins the bundle's list of shipped files.
- **Renames:** renaming a guide owes no migration. Renaming a shipped page owes revalidations (COR-050 points 3 and 6), a changeset (PRJ-002), and whatever COR-010 asks.
