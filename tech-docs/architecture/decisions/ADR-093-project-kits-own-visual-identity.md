---
id: ADR-093
title: project-kit keeps its visual identity in libraries of its own, and its brand builds on the foundations with no base
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** project-kit's own look and meaning live in libraries of its own, in the folder where it keeps its visual work. They are a brand, the notation it already has, and a component library once two of its pieces share a form. project-kit owns them, and they never ship to another project. A piece names them as it names any library. The brand builds on the foundations and has no base, as the neutral brand does, so it gives every shared role a value of its own. The neutral brand opens no role, so a brand built on it could change none of its values. On the foundations, every part of project-kit's identity lies in files the capability's designer may write in any project. So project-kit's designer works with an adopter's powers, and waits on no one. The libraries the capability ships keep nothing of project-kit's. Whether the neutral brand should open its roles is left to the capability's owner.

## Context

[#3154](https://github.com/aleskalfas/project-kit/issues/3154), under [#3149](https://github.com/aleskalfas/project-kit/issues/3149), asks where project-kit's own visual identity lives, and on what base. Two trials wait on the answer. In one the designer redraws the showcase deck ([#3156](https://github.com/aleskalfas/project-kit/issues/3156)), and in the other it designs the sockets figure ([#3157](https://github.com/aleskalfas/project-kit/issues/3157)). In both it has an adopter's powers only, and may write no library the capability ships.

Two terms, as this record uses them:
- **Visual identity:** what makes project-kit's pieces look and mean its own. It is a brand's values and its own form, a notation's concepts, and the forms of project-kit's own that its pieces share.
- **An adopter's powers:** what the capability's designer, `graphic-designer`, may write in any project that installs the capability ([visual-communication:DEC-030-design-agents] point 5). Its grant names the project's location for visual work. There it writes a piece's files and the versions not yet released of the project's own libraries, and never a library the capability ships. Where the capability is authored, that point also lets it change a shipped library's version being built. The trials take that one power away.

What the records already settle:
- **A project's identity is its own.** A project's brand, notations and taste are the project's, in its own files, never in the capability's folder ([visual-communication:DEC-001-visual-communication-discipline] points 9 and 11).
- **A shipped brand stays a brand to start from,** and one project's identity goes into that project's own libraries (DEC-030 point 4).
- **project-kit's notation is kept and never shipped,** and so is any other library project-kit writes for its pieces, a brand among them ([PRJ-012](../../../.pkit/decisions/project/PRJ-012-showcase-deck.md) point 3). The notation already lies in project-kit's location, `visual/`, as a version not yet released.
- **project-kit's pieces use only what every project gets** (PRJ-012 point 2).

What makes the base a question:
- **A brand built on a base gives values only to the roles the base opens** ([visual-communication:DEC-004-brands-and-notations] point 6). The neutral brand, the brand the capability ships to start from, opens none, and gives every shared role a value. So a brand built on it changes none of those values.
- **A brand may have no base.** It then builds on the foundations, and gives every shared role a value itself, as the neutral brand does.

No record says where project-kit's brand and component library lie, who owns them, or what the brand builds on. This record decides it. It ships to no project ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)), and holds no design value and no form.

## Decision

**project-kit's brand, notation and component library are libraries of project-kit's own, in its location for visual work. project-kit owns them, never ships them, and releases them as any project releases its own. A piece names them as it names any library. The brand builds on the foundations and has no base. The libraries the capability ships hold nothing of project-kit's identity.**

### 1. Three libraries of project-kit's own, in its location

- **Where:** each lies in the library folder of project-kit's location for visual work, listed there with the project as its source ([visual-communication:DEC-003-change-over-time] point 4). None lies in the capability's folder (DEC-001 point 11).
- **Who owns them:** project-kit, as a project that installs the capability, and it releases each of them. Whoever maintains the capability owns none of them, though one person may hold both roles.
- **Who writes them:** the designer writes their versions not yet released, within its grant over the location (DEC-030 point 5). So no part of project-kit's identity needs a write outside that grant.
- **What each holds:** the brand holds project-kit's values and the form that is the brand's own, such as its drawings of layouts. The notation holds project-kit's concepts. The component library holds the forms several of project-kit's pieces share. Which library a form belongs in is decided as for any library (DEC-001 point 5, [visual-communication:DEC-007-starter-library] point 4).

### 2. Never shipped, and released as any project's own library

- **Never shipped:** no release of the methodology carries them, and no sync or install writes them into another project (PRJ-012 point 3).
- **Not yet released while only drafts lock them.** A version not yet released changes freely, and only a draft may lock it (DEC-003 points 6 and 8). The designer works there.
- **Released for a piece that leaves the draft state.** A final or published piece locks only released versions, and a person sets a piece's state (DEC-003 point 8). So project-kit releases a version when a piece that locks it is to become final or published. It does so by the release of a project's own library ([visual-communication:DEC-014-own-library-needed-release] point 1). The released version is fixed, and the next change starts a new one.

### 3. A piece names them as it names any library

- **By name:** a piece names project-kit's brand as its brand, the notation among its notations, a component by its library's name, and each version in its lock (DEC-001 points 3, 5 and 7). Nothing marks them as project-kit's.
- **A name of its own for each:** the change that makes a library names it. The name takes the shape every library's name takes (DEC-004 point 4). It is no other library's name in the location, since one name holds one library (DEC-003 point 4). It is no name of a library the capability ships, and no top group of the shared roles (DEC-004 point 7).

### 4. project-kit's brand builds on the foundations, with no base

- **Its base:** none. It names the foundations among the libraries it builds on, by major, and marks no library as its base (DEC-004 point 6).
- **What it owes:** a value of its own for every shared role but a picture role, and each size its pieces name on a shared size axis (DEC-004 points 2 and 11). It commits its fonts as the record of brands and notations says (DEC-004 point 9).
- **What it may do,** as any brand with no base may:
  - name another library, to give that library's roles values ([visual-communication:DEC-008-library-role-defaults] point 4)
  - draw the layouts of a top whose library it names ([visual-communication:DEC-034-brand-drawings] point 1)

  Which of these it does is the designer's choice.
- **What it waits on:** nothing. Its base needs no change to a library the capability ships, and no decision of the capability's owner.

### 5. The libraries the capability ships hold nothing of project-kit's identity

- **Only what serves any project.** A shipped library holds no value, concept, form, name or font of project-kit's identity, in its version being built or in a released version. That holds whoever writes the change (DEC-001 point 9, COR-014).
- **The neutral brand stays a brand to start from** (DEC-030 point 4). It never becomes project-kit's look, and never holds it as a mode (DEC-004 point 2).
- **A need any project shares** goes to the shipped library that holds such things, by its owner's bar, as DEC-030 point 4 sets. A designer that may not write that library, as in the trials, sends its owner a request. Meanwhile the piece goes on with a local component, or waits.

## Rationale

**Point 1, the location.** A project's work lies in its location (DEC-001 point 11, [visual-communication:DEC-002-files-and-validation] point 1). The designer's grant names that location in every project (DEC-030 point 5). Placed there, project-kit's identity is work the designer reaches with an adopter's powers alone. Three libraries keep values, meaning and structure apart, since each changes for its own reasons (DEC-001 point 5).

**Point 2, never shipped, released on need.** A library shipped with the capability would carry one project's taste into every project (PRJ-012 point 3, COR-014). Kept in project-kit's location, the libraries reach no project through the methodology. A project may still fetch a released version from project-kit's repository, as from any repository (DEC-003 point 4). That fetch reads the version in full first, since a number released where the capability is authored vouches for nothing (DEC-014 points 3 and 4). A release made before a piece needs one would fix a look still being tried, while a draft may lock a version not yet released.

**Point 3, names.** A piece reads every library the same way. So a showcase that names project-kit's brand shows how any project names its own (PRJ-012 point 2). A name the capability ships would clash in the location's list, where one name holds one library.

**Point 4, the base.** Among what the capability gives every project, a brand has two bases to choose from: the brand the capability ships to start from, or none.
- **On the neutral brand,** every shared role keeps neutral's value, since neutral opens none (DEC-004 point 6). The starter's roles stay at their defaults, since neutral names no library but the foundations (DEC-008 point 4). So every component of the foundations and the starter draws in neutral's values. Only the brand's own parts and drawings could differ.
- **With no base,** the brand gives every value itself, may give values to the roles of any library it names, and draws the layouts it chooses. All of it lies in the brand's own files, which the designer's grant reaches.

So the foundations are the base on which an adopter's powers suffice. The trials then measure what an adopter pays for a look of its own, and lean on nothing made for project-kit (PRJ-012 point 2).

The costs:
- **A larger first version.** The brand owes every shared role a value, and each size its pieces name. A brand on an open base would owe only what it changes.
- **No fix of neutral's reaches it.** Neutral's values are no part of project-kit's look, so the brand loses nothing it wants. The contrast pairs the foundations declare still judge it in every combination, as they judge every brand (DEC-004 point 8). A shared role the foundations add later carries a default, so it breaks no brand (DEC-004 point 7).

**Why not wait for the neutral brand to open its roles.** Once open, a role stays open until a major release of the base (DEC-004 point 5). So which roles neutral opens is a promise to every project that builds on it, and its owner weighs them all. Opened to unblock project-kit's trials, it would be a change of a shipped library made for project-kit's pieces (PRJ-012 point 2). And the trials would wait on that record.

**Point 5, the shipped libraries.** A shipped library serves every project, and one project's identity goes into that project's own libraries (DEC-030 point 4). Where the capability is authored, the designer may change a shipped library's version being built (DEC-030 point 5). Identity written there would reach every project that brings in that library's next release ([visual-communication:DEC-013-shipped-library-releases] point 5). A request to the library's owner keeps a shared need in sight, as the trials' work list does, and leaves its owner's bar to judge it.

### Alternatives considered

- **A brand built on the neutral brand as it stands.** Rejected: it could change no value neutral gives, so every shared component would draw in neutral's look (Rationale, point 4).
- **A brand built on the neutral brand once neutral opens its roles.** Not taken: the trials would wait on a decision of the capability's owner. An opening made for project-kit's trials is also a change made for its pieces alone. The question stays open (Implications).
- **project-kit's look as a mode of the neutral brand, or neutral's values changed to it.** Rejected: a look with another owner is a brand, not a mode (DEC-004 point 2). Either way, project-kit's look would ship to every project (DEC-001 point 9).
- **A brand of project-kit's shipped with the capability.** Rejected: PRJ-012 point 3 keeps project-kit's libraries unshipped.
- **The brand the capability's tests keep.** Rejected: no project locks it ([visual-communication:DEC-004-brands-and-notations], Implications), and project-kit's pieces are no fixture (PRJ-012 point 1).
- **No brand of project-kit's, its look kept in local components.** Rejected: only a brand holds a raw value (DEC-001 point 5), so a local component cannot carry a look.
- **project-kit's libraries in a repository of their own, fetched into the location.** Rejected: a fetched version is released, so the designer could change none of it (DEC-003 points 4 and 6). It would also add a repository and its releases for one user (COR-007).
- **project-kit's libraries in the capability's folder, kept out of what ships.** Rejected: a project's work never lies there (DEC-001 point 11), and the designer's grant names nothing there (DEC-030 point 5).
- **One library for project-kit's values and its shared forms.** Rejected: a brand holds values, and of forms only those that are its own (DEC-001 point 5, DEC-007 point 4).

## Implications

- **No edit to an accepted record.** Read against this record, and left as they stand:
  - PRJ-012 points 2 and 3, which this record follows for project-kit's brand and component library
  - DEC-030 points 4 and 5, whose change of a shipped library's version being built, where the capability is authored, stays for what serves every project
  - DEC-004 point 6, and the neutral brand's open roles, which this record leaves as they are
- **The brand is made by the first change that gives project-kit's pieces a look of their own.** The trials of #3156 and #3157 are the first to try. A piece of project-kit's moves onto the brand as any piece moves onto another brand (DEC-001 point 5).
- **The component library comes with its first shared form.** It is made when a local component of one of project-kit's pieces is needed by another (DEC-030 point 2).
- **The brand's fonts** are only fonts whose licence lets a public repository hold them (PRJ-012, Implications).
- **Left open, as a follow-up for the capability's owner:** whether the neutral brand opens roles, and which, so that a project can build on it a brand that changes what neutral gives a value to. Whoever maintains the capability decides it, in a record of the capability, by what serves every project that builds on neutral. An issue is filed for it. This record decides nothing of it, and nothing here waits on it.
- **Revisit this record** if the neutral brand comes to open the roles project-kit's brand gives values to. Whether the brand then moves onto neutral is weighed then.
- **No migration and no changeset:** nothing ships, no installed project's state changes, and no file of the capability changes.
