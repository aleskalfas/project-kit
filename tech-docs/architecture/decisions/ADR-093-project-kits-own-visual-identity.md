---
id: ADR-093
title: project-kit keeps its visual identity in libraries of its own, and its brand builds on the foundations with no base
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** project-kit's own look and meaning live in libraries of its own, in the folder where it keeps its visual work. They are a brand, the notation it already has, and a component library once two of its pieces share a form of project-kit's own. project-kit owns them, never ships them, and a piece names them as it names any library.

The brand builds on the foundations and has no base, as the neutral brand does. A brand built on neutral could change none of neutral's values or give a logo, since neutral opens no role. Nor could it add an axis of its own, and its drawings would give way if neutral came to draw that kind of work.

With no base, all the brand needs lies in its own files, where the capability's designer may write in any project. So the designer works with an adopter's powers. It waits only where any adopter's designer waits: on a person, who commits fonts, supplies any logo and runs each release. Nothing the capability ships takes anything from project-kit's identity.

Three points stay open for project-kit's maintainer, each with what the trials do meanwhile:
- the libraries' names
- whether every piece of project-kit's moves onto the brand
- where a generic form that two of its pieces share goes

What a brand built on the neutral brand may make its own is left to the capability's owner.

## Context

[#3154](https://github.com/aleskalfas/project-kit/issues/3154), under [#3149](https://github.com/aleskalfas/project-kit/issues/3149), asks where project-kit's own visual identity lives, and on what base. Two trials wait on the answer. In one the designer redraws the showcase deck ([#3156](https://github.com/aleskalfas/project-kit/issues/3156)), and in the other it designs the sockets figure ([#3157](https://github.com/aleskalfas/project-kit/issues/3157)). In both it has an adopter's powers only, and may write no library the capability ships.

Two terms, as this record uses them:
- **Visual identity:** what makes project-kit's pieces look and mean its own. It is a brand's values and its own form, a notation's concepts, and the forms of project-kit's own that its pieces share. project-kit's rules of style are left out here, since a project keeps those in rule sets of its own ([visual-communication:DEC-028-principles-of-visual-communication] point 1). project-kit keeps its rule sets outside its location for visual work.
- **An adopter's powers:** what the capability's designer, `graphic-designer`, may write in any project that installs the capability ([visual-communication:DEC-030-design-agents] point 5). Its grant names the project's location for visual work. There it writes a piece's files and the versions not yet released of the project's own libraries, never a library the capability ships.
  - **Where the capability is authored,** that point also lets it change a shipped library's version being built. The trials take that one power away.
  - **In any project,** it leaves each font, any logo and each release to a person (Decision, point 1).

What the records already settle:
- **A project's identity is its own.** A project's brand, notations and taste are the project's, in its own files, never in the capability's folder ([visual-communication:DEC-001-visual-communication-discipline] points 9 and 11).
- **A shipped brand stays a brand to start from,** and one project's identity goes into that project's own libraries (DEC-030 point 4).
- **project-kit's notation is kept and never shipped,** and so is any other library project-kit writes for its pieces, a brand among them ([PRJ-012](../../../.pkit/decisions/project/PRJ-012-showcase-deck.md) point 3). The notation already lies in project-kit's location, `visual/`, as a version not yet released.
- **project-kit's pieces use only what every project gets** (PRJ-012 point 2).

What makes the base a question:
- **A brand built on a base gives values only to the roles the base opens** ([visual-communication:DEC-004-brands-and-notations] point 6). The neutral brand, the brand the capability ships to start from, opens none. So a brand built on it changes none of the values neutral gives.
- **It keeps more of its base than values.** It keeps its base's logo unless the base opens that role, and adds no axis of its own ([visual-communication:DEC-025-picture-files] point 4, DEC-004 point 6). Where its base comes to serve a top the brand draws, the base's drawings win ([visual-communication:DEC-034-brand-drawings] point 8).
- **A brand may have no base.** It then builds on the foundations, and gives the shared roles their values itself, as the neutral brand does.

No record says where project-kit's brand and component library lie, who owns them, or what the brand builds on. This record decides it. It ships to no project ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)), and holds no design value and no form.

## Decision

**project-kit's brand, its notation and any component library of its own are libraries of project-kit's own, in its location for visual work. project-kit owns them, never ships them, releases them as any project releases its own, and a piece names them as it names any library. Its brand builds on the foundations, with no base. Nothing the capability ships takes anything from project-kit's identity.**

### 1. Libraries of project-kit's own, in its location

- **Where:** each lies in the library folder of project-kit's location for visual work, listed there with the project as its source ([visual-communication:DEC-003-change-over-time] point 4). None lies in the capability's folder (DEC-001 point 11).
- **Which:** a brand, the notation project-kit already has, and a component library once a form of project-kit's own needs one (Implications).
- **Who owns them:** project-kit, as a project that installs the capability, and it releases each of them. Whoever maintains the capability owns none of them, though one person may hold both roles.
- **Who writes them:** the designer writes their versions not yet released, within its grant over the location (DEC-030 point 5). So every file of them lies within that grant. The designer leaves three things to a person, as it does in any project:
  - each font a brand names, committed with its licence where the licence allows (DEC-004 point 9)
  - any logo, since making the art lies outside the capability (DEC-001 point 9)
  - each release, which a command writes (DEC-030 point 5)
- **What each holds:** the brand holds project-kit's values and the form that is the brand's own, such as its drawings of layouts. The notation holds project-kit's concepts. A component library of project-kit's holds forms of project-kit's own that several of its pieces share. Which library a form belongs in is decided as for any library (DEC-001 point 5, DEC-030 point 3).

### 2. Never shipped, and released as any project's own library

- **Never shipped:** no release of the methodology carries them, and no sync or install writes them into another project (PRJ-012 point 3).
- **Not yet released while only drafts lock them.** A version not yet released changes freely, and only a draft may lock it (DEC-003 points 6 and 8). The designer works there.
- **Released for a piece that leaves the draft state.** A final or published piece locks only released versions, and a person sets a piece's state (DEC-003 point 8). So project-kit releases a version when a piece that locks it is to become final or published. It does so by the release of a project's own library ([visual-communication:DEC-014-own-library-needed-release] point 1). The released version is fixed, and the next change starts a new one.
- **The shipped versions it locks are released too.** Such a piece also locks only released versions of the shipped libraries it names. Where it needs what only a shipped library's version being built holds, such as a size the foundations add, it waits. Whoever maintains the capability releases that version ([visual-communication:DEC-013-shipped-library-releases] point 1). Any project's piece waits for it the same way.

### 3. A piece names them as it names any library

- **By name:** a piece names project-kit's brand as its brand, and the notation among its notations (DEC-001 points 3, 5 and 7). It names a component by its library's name, and each version in its lock. Nothing marks them as project-kit's.
- **A name of its own for each.** It takes the shape every library's name takes (DEC-004 point 4). It is no other library's name in the location, since one name holds one library (DEC-003 point 4). It is no name of a library the capability ships, nor one it reserves (DEC-004 point 7, and the capability's reference of files). Which names they take is left open (Implications).

### 4. project-kit's brand builds on the foundations, with no base

- **Its base:** none. It names the foundations among the libraries it builds on, by major, and marks no library as its base (DEC-004 point 6).
- **What it owes:** a value for each shared role with no default, picture roles aside, and each size its pieces name (DEC-004 points 2, 7 and 11). Its fonts lie in committed files (DEC-004 point 9).
- **What it may do,** as any brand with no base may:
  - name another library, to give that library's roles values ([visual-communication:DEC-008-library-role-defaults] point 4)
  - draw the layouts of a top whose library it names ([visual-communication:DEC-009-layout-defaults] points 2 and 3), declared as DEC-034 point 1 has it
  - add axes of its own (DEC-004 point 2)
  - give a logo, from a file a person supplies (DEC-025 point 4)

  Which of these it does is the designer's choice.
- **What it starts from:** a copy of the neutral brand's values at a released version, or nothing. Either is the designer's choice, and the change that makes the first version says which (Rationale, point 4).
- **What it waits on:** only what any project's own brand waits on: a person, for its fonts, any logo and each release (point 1). Its base needs no change to a library the capability ships, and no decision of the capability's owner.

### 5. Nothing the capability ships takes anything from project-kit's identity

- **No library it ships.** Nothing made for project-kit's identity, or taken from it, goes into a library the capability ships. That covers any value, concept, form, name or font chosen for project-kit's pieces, in a version being built or a released one. The rule holds whoever writes the change (DEC-001 point 9, COR-014). A value both hold by coincidence, such as a font, breaks nothing.
- **Nor the rest of what it ships.** The same holds for the capability's rule sets, its design knowledge and its agents' instructions. A lesson the trials teach goes there only as practice or a rule that serves any project (DEC-028 point 1, DEC-030 point 8). project-kit's own taste goes into its own libraries and rule sets.
- **The neutral brand stays a brand to start from** (DEC-030 point 4). It never becomes project-kit's look, and never holds it as a mode (DEC-004 point 2).
- **A need any project shares** goes to the shipped library that holds such things, by its owner's bar, as DEC-030 point 4 sets. A designer that may not write that library, as in the trials, sends its owner a request. Meanwhile each piece with the need goes on with a local component of its own, or waits. Whether a form two of project-kit's pieces share waits elsewhere meanwhile is left open (Implications).

## Rationale

**Point 1, the location.** A project's work lies in its location (DEC-001 point 11, [visual-communication:DEC-002-files-and-validation] point 1). The designer's grant names that location in every project (DEC-030 point 5). Placed there, project-kit's libraries are work the designer reaches with an adopter's powers alone. Separate libraries keep values, meaning and structure apart, since each changes for its own reasons (DEC-001, Rationale).

**Point 1, what a person does.** Judging a font's licence, making a logo's art and running a release are left to a person in every project. So the trials wait on a person only where any adopter's designer would.

**Point 2, never shipped, released on need.**
- **Never shipped.** A library shipped with the capability would carry one project's taste into every project (PRJ-012 point 3, COR-014). Kept in project-kit's location, the libraries reach no project through the methodology.
- **Fetched as from any repository.** A project may still fetch a released version from project-kit's repository (DEC-003 point 4). That fetch reads the version in full first, since a number released where the capability is authored vouches for nothing (DEC-014 points 3 and 4).
- **Released on need.** A release made before a piece needs one would fix a look still being tried, while a draft may lock a version not yet released.
- **A shipped library's release is any project's wait.** A final piece of project-kit's waits for it as any project's piece does. So the trials meet that wait as an adopter would, and lean on nothing made for project-kit.

**Point 3, names.** A piece reads every library the same way. So a showcase that names project-kit's brand shows how any project names its own (PRJ-012 point 2). A name the capability ships would clash in the location's list, where one name holds one library. A release fixes a name, and a brand's names are public, so a person accepts each before that (DEC-003 point 6, DEC-004 point 5).

**Point 4, the base.** Among what the capability gives every project, a brand has two bases to choose from: the brand the capability ships to start from, or none.
- **On the neutral brand,** the brand would keep much of neutral's:
  - every value neutral gives, since neutral opens no role (DEC-004 point 6)
  - no logo, since neutral gives none and does not open `picture.logo` (DEC-025 point 4)
  - the starter's roles at their defaults, since neutral names no library but the foundations (DEC-008 point 4)
  - the shared axes alone, since a brand built on a base adds none (DEC-004 point 6)
  - its own drawings of a top only until neutral comes to serve that top, which breaks nothing (DEC-034 point 8)

  So every component of the foundations and the starter would draw in neutral's values.
- **With no base,** the brand gives every value itself, its logo and any axis of its own among them (DEC-004 point 2). It may give values to the roles of any library it names (DEC-008 point 4), and draws the layouts it chooses (DEC-009 point 3). All of it lies in the brand's own files, within the designer's grant.

So the foundations are the base on which an adopter's powers suffice. The capability's reference sends adopters the same way. It says that a project that wants other values than the neutral brand's writes its own brand. The trials then measure what an adopter pays for a look of its own, and lean on nothing made for project-kit (PRJ-012 point 2).

The costs:
- **A larger first version.** The brand owes a value to each shared role with no default, and each size its pieces name. A brand on an open base would owe only what it changes.
- **Neutral's fixes do not reach it.** project-kit's pieces draw in neutral's look until a trial moves them, so a first version may copy neutral's values (Decision, point 4). A copy loses each later fix of neutral, and a blank start owes every value at once. The contrast pairs the foundations declare judge either in every combination (DEC-004 point 8).
- **Upkeep at each release of the foundations.** A shared role the foundations add later carries a default, so it breaks no brand (DEC-004 point 7). Until the brand gives it a value, that default may stand for another meaning (DEC-008 point 2). So the brand's owner reads each release of the foundations for such roles, a task neutral's owner would do for a brand on neutral.

**Why not wait for the neutral brand to open its roles.** Three reasons hold:
- **Opening roles alone would not be enough.** A brand built on neutral would keep the starter at its defaults, the shared axes alone, and drawings neutral may displace (the list above). Its logo would need `picture.logo` opened too.
- **An open role is weighed for every project.** It stays open until a major release of neutral (DEC-004 point 5). A fix neutral makes to an open role reaches no brand that gives the role a value. The open list exists to limit that (DEC-004, Alternatives considered). So which roles neutral opens is its owner's to weigh, for every project built on it.
- **The trials would wait** on a record of the capability's owner, for a path the capability's reference sends no adopter down.

**Point 5, the shipped libraries.** A shipped library serves every project, and one project's identity goes into that project's own libraries (DEC-030 point 4). Where the capability is authored, the designer may change a shipped library's version being built (DEC-030 point 5). Identity written there would reach every project that brings in that library's next release (DEC-013 point 5). A request to its owner keeps a shared need in sight, as the trials' work list does, and leaves the owner's bar to judge it.

**Point 5, by origin and beyond libraries.** The rule names where a thing came from, not what it is, so a value both hold by coincidence breaks nothing. The capability's rule sets, design knowledge and agents reach every project too. So one project's taste stays out of them, as it stays out of the shipped libraries (DEC-030 point 8, COR-014).

### Alternatives considered

- **A brand built on the neutral brand as it stands.** Rejected: it could change no value neutral gives, so every shared component would draw in neutral's look (Rationale, point 4). Nor could it give a logo or add an axis.
- **A brand built on the neutral brand once neutral opens its roles.** Not taken: opening roles alone leaves the logo, the starter's roles, the axes and the drawings as Rationale point 4 lists them. The trials would also wait on a record of the capability's owner. The question stays open (Implications).
- **project-kit's look as a mode of the neutral brand, or neutral's values changed to it.** Rejected: a look with another owner is a brand, not a mode (DEC-004 point 2). Either way, project-kit's look would ship to every project (DEC-001 point 9).
- **A brand of project-kit's shipped with the capability.** Rejected: PRJ-012 point 3 keeps project-kit's libraries unshipped.
- **The brand the capability's tests keep.** Rejected: no project locks it ([visual-communication:DEC-004-brands-and-notations], Implications), and project-kit's pieces are no fixture (PRJ-012 point 1).
- **No brand of project-kit's, its look kept in local components.** Rejected: only a brand holds a raw value (DEC-001 point 5), so a local component cannot carry a look.
- **project-kit's libraries in a repository of their own, fetched into the location.** Rejected: a fetched version is released, so the designer could change none of it (DEC-003 points 4 and 6). It would also add a repository and its releases for one user (COR-007).
- **project-kit's libraries in the capability's folder, kept out of what ships.** Rejected: a project's work never lies there (DEC-001 point 11), and the designer's grant names nothing there (DEC-030 point 5).
- **Forms of project-kit's own kept as parts of its brand, with no component library.** A brand's own parts are the few no shared component has (DEC-001 point 5). The designer puts a reusable form in a component library (DEC-030 point 3). If every piece of project-kit's moves onto the brand, though, a form that brand alone uses could be its part ([visual-communication:DEC-007-starter-library] point 4). So this is left to whether project-kit's pieces must move onto the brand (Implications).
- **A change of its own that makes the brand before either trial.** Not taken: the issues already order the trials, the first making the brand and the second building on it (Implications).
- **A command of the capability that starts a project's brand from neutral's values.** Not taken here: it is the capability's to build, and worth it only if the trials show that setup recurs (COR-007).

## Implications

- **No edit to an accepted record.** Read against this record, and left as they stand:
  - PRJ-012 points 2 and 3, which this record follows for project-kit's brand and component library
  - DEC-030 points 4 and 5, whose change of a shipped library's version being built, where the capability is authored, stays for what serves every project
  - DEC-004 point 6, and the neutral brand's open roles, which this record leaves as they are
- **The trial of #3156 makes the brand's first version.** The trial of #3157 starts from the default branch as #3156 left it, since both would build the brand's values (#3157). So one change makes the brand, and the other builds on it.
- **The component library comes with its first shared form of project-kit's own.** It is made when a local component of one piece is needed by another, and no shipped library would hold it (DEC-030 point 2). A generic form two pieces share is left open below.
- **The brand's fonts** are only fonts whose licence lets a public repository hold them (PRJ-012, Implications).
- **Left open for project-kit's maintainer,** each with what the trials do meanwhile:
  - **The libraries' names.** Meanwhile the change that makes a library gives it a name that keeps to point 3. A person accepts each name before that library's first release (Rationale, point 3). Until then, renaming a library, the notation included, changes only project-kit's own files.
  - **Whether project-kit's pieces must move onto the brand.** Meanwhile each trial moves its own piece onto the brand, whose values it builds for that piece. The piece moves as any piece moves onto another brand (DEC-001 point 5), and no other piece moves for this record. The answer also says whether a form of project-kit's own may be a part of the brand (Alternatives considered).
  - **Where a generic form that two of project-kit's pieces share goes,** while no shipped library holds it. Meanwhile the trials follow DEC-030 point 4, and send the starter's owner a request. Each piece that needs the form goes on with a local component, or waits. The other way weighed is project-kit's component library as the form's home, until the starter takes it.
- **Left open for the capability's owner.** A follow-up issue, #3169, asks what a project's brand built on the neutral brand may make its own. Four questions decide it:
  - which roles neutral opens, `picture.logo` among them (DEC-004 point 6, DEC-025 point 4)
  - whether neutral names the starter, so that a brand built on it reaches the starter's roles. Every project that uses neutral would then hold and lock the starter (DEC-008 point 4).
  - what a brand built on neutral keeps of its drawings of a top that neutral comes to serve. Neutral's drawings then win, with no break (DEC-034 point 8).
  - whether the capability's reference keeps sending a project that wants a look of its own to a brand with no base

  Whoever maintains the capability decides it in a record of the capability, by what serves every project that builds on neutral. This record decides nothing of it, and nothing here waits on it.
- **Revisit this record** if a brand built on the neutral brand could come to hold all that project-kit's brand then holds. That is every value it gives, its logo, its drawings and any axis of its own. Whether the brand moves onto neutral is weighed at that time.
- **No migration and no changeset:** nothing ships, no installed project's state changes, and no file of the capability changes.
