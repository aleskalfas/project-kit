---
id: ADR-093
title: project-kit keeps its visual identity in libraries of its own, and its brand builds on the foundations with no base
status: proposed
date: 2026-11-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** project-kit draws its pieces with the visual-communication capability, as any project does. Its own look and meaning live in libraries of its own, in the folder where it keeps its visual work. They are a brand, the notation it already has, and a component library once two of its pieces share a form of project-kit's own. project-kit owns them, and never ships them.

Its brand is built on no other brand. So every value in it is project-kit's choice, not the fixed values of the neutral brand, which the capability ships to start from. The brand may also give a logo, and add axes of its own, ways for its look to vary beyond those every brand shares.

All the brand needs then lies in its own files, which the capability's designer agent may write in any project. So the designer builds project-kit's look as it would any project's. A person commits the brand's fonts, supplies any logo and runs each release, as in any project.

Nothing the capability ships takes anything from project-kit's identity. Any change a shipped library would need for project-kit's pieces, even one any project could use, reaches it only as a request. Whoever maintains the capability then shapes the change, and judges whether it serves every project.

Three questions stay open for project-kit's maintainer, each with what holds until it is decided:
- the libraries' names
- whether every piece of project-kit's moves onto the brand
- where a generic form that two of its pieces share is kept, while no shipped library holds one

What a brand built on the neutral brand may make its own is left to whoever maintains the capability.

## Context

[#3154](https://github.com/aleskalfas/project-kit/issues/3154), under [#3149](https://github.com/aleskalfas/project-kit/issues/3149), asks where project-kit's own visual identity lives, and on what base. Work that would give project-kit's pieces a look of their own waits on the answer.

Three terms, as this record uses them:
- **Visual identity:** the values, concepts, forms and names that make project-kit's pieces look and mean its own:
  - its brand's values, and the form that is the brand's own
  - its notation's concepts
  - the forms of project-kit's own that several of its pieces share
  - the names given to each

  project-kit's rules of style are left out here, since a project keeps those in rule sets of its own ([visual-communication:DEC-028-principles-of-visual-communication] point 1). project-kit keeps its rule sets outside its location for visual work.
- **A generic form:** a form any project's pieces could use, which carries nothing of project-kit's identity. It may still be first drawn for one of project-kit's pieces. A change to a shipped library, such as a form's new option or a fix, is generic in the same sense.
- **An adopter's powers:** what the capability's designer agent may write in any project that installs the capability ([visual-communication:DEC-030-design-agents] point 5). Its grant names the project's location for visual work. There it writes a piece's files and the versions not yet released of the project's own libraries, never a library the capability ships. Where the capability is authored, it may also change a shipped library's version being built (DEC-030 point 4), which is no adopter's power.

What the records already settle:
- **A project's identity is its own.** A project's brand, notations and taste are the project's, in its own files, never in the capability's folder ([visual-communication:DEC-001-visual-communication-discipline] points 9 and 11).
- **A shipped brand stays a brand to start from,** and one project's identity goes into that project's own libraries (DEC-030 point 4).
- **A shipped library's owner is whoever maintains the capability,** who releases each of its versions ([visual-communication:DEC-003-change-over-time] point 6).
- **project-kit's notation is kept and never shipped,** and so is any other library project-kit writes for its pieces, a brand among them ([PRJ-012](../../../.pkit/decisions/project/PRJ-012-showcase-deck.md) point 3). The notation already lies in project-kit's location for visual work.
- **project-kit's pieces use only what every project gets** (PRJ-012 point 2).

What makes the base a question:
- **A brand built on a base gives values only to the roles the base opens** ([visual-communication:DEC-004-brands-and-notations] point 6). The neutral brand, the brand the capability ships to start from, opens none. So a brand built on it changes none of the values neutral gives.
- **It keeps more of its base than values.** It keeps its base's logo unless the base opens that role, and adds no axis of its own ([visual-communication:DEC-025-picture-files] point 4, DEC-004 point 6). Where its base comes to serve a top the brand draws, the base's drawings win ([visual-communication:DEC-034-brand-drawings] point 8).
- **A brand may have no base.** It then builds on the foundations, and gives the shared roles their values itself, as the neutral brand does.

No record says where project-kit's brand and component library lie, who owns them, or what the brand builds on. This record decides it. It ships to no project ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)), and holds no design value and no form.

## Decision

**project-kit's brand, its notation and any component library of its own are libraries project-kit owns, in its location for visual work. Its brand builds on the foundations, with no base. Nothing the capability ships takes anything from project-kit's identity.**

### 1. Libraries project-kit owns, in its location

- **Where:** each lies in the library folder of project-kit's location for visual work, listed there with the project as its source (DEC-003 point 4). None lies in the capability's folder (DEC-001 point 11).
- **Which:** a brand, the notation project-kit already has, and a component library once a form of project-kit's identity needs one (Implications).
- **What each holds:** the brand holds project-kit's values and the form that is the brand's own, such as its drawings of layouts. The notation holds project-kit's concepts. A component library of project-kit's holds the forms of its identity that several of its pieces share. Whether it may also hold a generic form for a time is left open (Implications).
- **Who owns them:** project-kit, as a project that installs the capability. Whoever maintains the capability owns none of them, though one person may hold both roles.
- **How they are released:** as any project releases its own library ([visual-communication:DEC-014-own-library-needed-release] point 1). A final or published piece locks only released versions (DEC-003 point 8). So project-kit releases each version a piece locks before that piece becomes final or published.

### 2. project-kit's brand builds on the foundations, with no base

- **Its base:** none. It names the foundations among the libraries it builds on, by major, and marks no library as its base (DEC-004 point 6).
- **What it starts from:** a copy of the neutral brand's values at a released version, or nothing. Either is the designer's choice, and the change that makes the brand's first version says which (Rationale, point 2).
- **What it owes and may do:** what any brand with no base owes and may do (Rationale, point 2).

### 3. Nothing the capability ships takes anything from project-kit's identity

- **Its libraries,** the neutral brand among them, receive nothing of project-kit's visual identity. None receives a value, concept, form or name that makes project-kit's pieces its own, if it was made for them or taken from them. That holds in a version being built or a released one, whoever writes the change (DEC-001 point 9). A value both hold by coincidence, such as a font, breaks nothing.
- **Any change a shipped library would need** to serve one of project-kit's pieces reaches it only as a stated need. That holds for a new form, a new option or state on an existing form, and a fix. The need is a request to the library's owner (DEC-030 point 4), judged by the bar that owner keeps, as any project's is. That way the owner shapes each change and judges whether it is generic, not a designer working for one piece.
- **Its rule sets and design knowledge.** A lesson from project-kit's pieces may confirm a rule or a practice taken from the field's named sources. The lesson is never their source (DEC-028 point 1, DEC-030 point 8). project-kit's own taste goes into its own libraries and rule sets.
- **Its agents' instructions.** They serve every project, so nothing of project-kit's taste goes into them (COR-014, DEC-001 point 9).

## Rationale

**Point 1, the location.** A project's work lies in its location (DEC-001 point 11, [visual-communication:DEC-002-files-and-validation] point 1). The designer's grant names that location in every project (DEC-030 point 5). Placed there, project-kit's libraries are work the designer reaches with an adopter's powers alone. Separate libraries keep values, meaning and structure apart, since each changes for its own reasons (DEC-001, Rationale).

**What a person does.** Judging a font's licence, making a logo's art and running a release are left to a person in every project. So project-kit's designer waits on a person only where any adopter's designer would.

**Never shipped, and released as any project's own.**
- **Never shipped.** A library shipped with the capability would carry one project's taste into every project (PRJ-012 point 3, COR-014). Kept in project-kit's location, the libraries reach no project through the methodology.
- **Released as any project's own.** project-kit's pieces use only what every project gets (PRJ-012 point 2). So project-kit releases its libraries as any project releases its own.
- **A shipped library's release is any project's wait.** A final piece of project-kit's waits for it as any project's piece does (Implications). So project-kit's pieces meet that wait as an adopter's would, and lean on nothing made for project-kit.

**The names.** A piece reads every library the same way. So a showcase that names project-kit's brand shows how any project names its own (PRJ-012 point 2). A name the capability ships would clash in the location's list, where one name holds one library. A release fixes a name, and a brand's names are public, so a person accepts each before that (DEC-003 point 6, DEC-004 point 5).

**Point 2, the base.** Among what the capability gives every project, a brand has two bases to choose from: the brand the capability ships to start from, or none.
- **On the neutral brand,** the brand would keep much of neutral's:
  - every value neutral gives, since neutral opens no role (DEC-004 point 6)
  - no logo, since neutral gives none and does not open `picture.logo` (DEC-025 point 4)
  - the starter's roles at their defaults, since neutral names no library but the foundations ([visual-communication:DEC-008-library-role-defaults] point 4)
  - the shared axes alone, since a brand built on a base adds none (DEC-004 point 6)
  - its own drawings of a top only until neutral comes to serve that top, which breaks nothing (DEC-034 point 8)

  So every component of the foundations and the starter would draw in neutral's values.
- **With no base,** the brand gives every value itself, its logo and any axis of its own among them (DEC-004 point 2). It may give values to the roles of any library it names (DEC-008 point 4), and draws the layouts it chooses ([visual-communication:DEC-009-layout-defaults] point 3). All of it lies in the brand's own files, within the designer's grant.

So the foundations are the base on which an adopter's powers suffice. The capability's reference sends adopters the same way. It says that a project that wants other values than the neutral brand's writes its own brand. So project-kit pays for a look of its own what an adopter pays, and leans on nothing made for project-kit (PRJ-012 point 2).

The costs:
- **A larger first version.** The brand owes a value to each shared role with no default, picture roles aside (DEC-004 point 7). It owes each size its pieces name too (DEC-004 point 2). A brand on an open base would owe only what it changes.
- **Neutral's fixes do not reach it.** project-kit's pieces draw in neutral's look until a change moves them, so a first version may copy neutral's values (point 2). A copy loses each later fix of neutral, and a blank start owes every value at once. The contrast pairs the foundations declare judge either in every combination (DEC-004 point 8).
- **Upkeep at each release of the foundations.** A shared role the foundations add later carries a default, so it breaks no brand (DEC-004 point 7). Until the brand gives it a value, that default may stand for another meaning (DEC-008 point 2). So project-kit reads each release of the foundations for such roles, a task whoever maintains the capability would do for a brand on neutral.

**Why not wait for the neutral brand to open its roles.** Three reasons hold:
- **Opening roles alone would not be enough.** A brand built on neutral would keep the starter at its defaults, the shared axes alone, and drawings neutral may displace (the list above). Its logo would need `picture.logo` opened too.
- **An open role is weighed for every project.** It stays open until a major release of neutral (DEC-004 point 5). A fix neutral makes to an open role reaches no brand that gives the role a value. The open list exists to limit that (DEC-004, Alternatives considered). So which roles neutral opens is for whoever maintains the capability to weigh, for every project built on it.
- **project-kit's brand would wait** on a record of whoever maintains the capability, for a path the capability's reference sends no adopter down.

**Point 3, the shipped libraries.** A shipped library serves every project, and one project's identity goes into that project's own libraries (DEC-030 point 4). Where the capability is authored, the designer may change a shipped library's version being built (DEC-030 point 4). Identity written there would reach every project that brings in that library's next release ([visual-communication:DEC-013-shipped-library-releases] point 5).

**Point 3, a generic form.** Whether a form is generic, or carries something of project-kit's identity, is a judgement. A form, option or fix drawn for one of project-kit's pieces is shaped by that piece's needs, and may carry some of project-kit's identity unseen. Sent as a stated need, it reaches the library's owner as any project's need does, and the owner decides what serves every project. Written into the library by project-kit's designer, it would take a path no other project has (PRJ-012 point 2).

**Point 3, by origin and beyond libraries.** The rule names where a thing came from, not what it is, so a value both hold by coincidence breaks nothing. The capability's rule sets and design knowledge are taken from the field's named sources (DEC-028 point 1, DEC-030 point 8). A project's work confirms what they hold, and never supplies it. The capability's agents serve every project too, so one project's taste stays out of their instructions (COR-014).

### Alternatives considered

- **A brand built on the neutral brand as it stands.** Rejected: it could change no value neutral gives, so every shared component would draw in neutral's look (Rationale, point 2). Nor could it give a logo or add an axis.
- **A brand built on the neutral brand once neutral opens its roles.** Not taken: opening roles alone leaves the logo, the starter's roles, the axes and the drawings as Rationale point 2 lists them. project-kit's brand would also wait on a record of whoever maintains the capability. The question stays open (Implications).
- **project-kit's look as a mode of the neutral brand, or neutral's values changed to it.** Rejected: a look with another owner is a brand, not a mode (DEC-004 point 2). Either way, project-kit's look would ship to every project (DEC-001 point 9).
- **A brand of project-kit's shipped with the capability.** Rejected: PRJ-012 point 3 keeps project-kit's libraries unshipped.
- **The brand the capability's tests keep.** Rejected: no project locks it ([visual-communication:DEC-004-brands-and-notations], Implications), and project-kit's pieces are no fixture (PRJ-012 point 1).
- **No brand of project-kit's, its look kept in local components.** Rejected: only a brand holds a raw value (DEC-001 point 5), so a local component cannot carry a look.
- **project-kit's libraries in a repository of their own, fetched into the location.** Rejected: a fetched version is released, so the designer could change none of it (DEC-003 points 4 and 6). It would also add a repository and its releases for one user (COR-007).
- **project-kit's libraries in the capability's folder, kept out of what ships.** Rejected: a project's work never lies there (DEC-001 point 11), and the designer's grant names nothing there (DEC-030 point 5).
- **A generic form drawn for project-kit's pieces, written into a shipped library's version being built.** Where the capability is authored, DEC-030 point 4 allows that change. Rejected: a designer working for one of project-kit's pieces would shape the form, and judge it generic. Sent as a stated need, the form is shaped and judged by the library's owner (Rationale, "Point 3, a generic form").
- **Forms of project-kit's identity kept as parts of its brand, with no component library.** A brand's own parts are the few no shared component has (DEC-001 point 5). The designer puts a reusable form in a component library (DEC-030 point 3). If every piece of project-kit's moves onto the brand, though, a form that brand alone uses could be its part ([visual-communication:DEC-007-starter-library] point 4). So this is left to whether project-kit's pieces must move onto the brand (Implications).
- **A command of the capability that starts a project's brand from neutral's values.** Not taken here: it is the capability's to build, and worth it only if projects show that setup recurs (COR-007).

## Implications

- **No edit to an accepted record.** Read against this record, and left as they stand:
  - PRJ-012 points 2 and 3, which this record follows for project-kit's brand and component library
  - DEC-030 points 4 and 5. Where the capability is authored, the designer may still change a shipped library's version being built for what serves every project. A change one of project-kit's pieces needs reaches that version only as a request (point 3).
  - DEC-004 point 6, and the neutral brand's open roles, which this record leaves as they are
- **project-kit's own libraries need no more than an adopter's powers.** Every file of their versions not yet released lies within the designer's grant over the location (DEC-030 point 5). The brand's base needs no change to a shipped library, and no decision of whoever maintains the capability. As in any project, the designer leaves three things to a person:
  - each font a brand names, committed with its licence where the licence allows (DEC-004 point 9)
  - any logo, since making the art lies outside the capability (DEC-001 point 9)
  - each release, which a command writes (DEC-030 point 5)
- **The designer's shipped instructions do not carry point 3.** Where the capability is authored, they grant the designer the power to change a shipped library's version being built (DEC-030 point 4). They serve every project, so they cannot carry a rule of project-kit's own (COR-014). So point 3 reaches the designer from project-kit's side.
- **Never shipped:** no release of the methodology carries project-kit's libraries, and no project receives them (PRJ-012 point 3).
- **A shipped version a final piece locks.** A final or published piece of project-kit's also locks only released versions of the shipped libraries it names (DEC-003 point 8). Where it needs what only a version being built holds, it waits until whoever maintains the capability releases that version (DEC-013 point 1). Any project's piece waits the same way.
- **A piece names them as it names any library** (DEC-001 points 3, 5 and 7). It names project-kit's brand as its brand, and the notation among its notations. It names a component by its library's name, and each version in its lock. Nothing marks them as project-kit's.
- **Their names** take the shape every library's name takes (DEC-004 point 4). Each is no other library's name in the location, since one name holds one library (DEC-003 point 4). Nor is it a name of a library the capability ships, or one it reserves (DEC-004 point 7, and the capability's reference of files).
- **The brand's first version.** One change makes it, and later changes build on it. That change says whether the brand starts from a copy of neutral's values or from nothing (point 2).
- **The component library comes with its first shared form of project-kit's identity.** It is made when a local component of one piece is needed by another (DEC-030 point 2). Where a generic form two pieces share is kept is left open below.
- **The brand's fonts** are only fonts whose licence lets a public repository hold them (PRJ-012, Implications).
- **Left open for project-kit's maintainer,** each with what holds until it is decided:
  - **The libraries' names.** Until they are decided, the change that makes a library gives it a name that keeps to the rules on their names above. A person accepts each name before that library's first release (Rationale, "The names"). Before that release, renaming a library, the notation included, changes only project-kit's own files.
  - **Whether project-kit's pieces must move onto the brand.** Until it is decided, a piece moves onto the brand only in a change that moves its lock onto it (DEC-001 point 3). No piece moves because of this record. The answer also says whether a form of project-kit's identity may be a part of the brand (Alternatives considered).
  - **Where a generic form that two of project-kit's pieces share is kept, while no shipped library holds one.** Two places are weighed: each piece's local component, or project-kit's component library. Held in either, the form stays generic, and reaches a shipped library only as a stated need to whoever maintains the capability (point 3). Until it is decided, each piece that needs the form goes on with a local component, or waits (DEC-030 point 4).
- **Left open for whoever maintains the capability.** A follow-up issue, #3169, asks what a project's brand built on the neutral brand may make its own. Four questions decide it:
  - which roles neutral opens, `picture.logo` among them (DEC-004 point 6, DEC-025 point 4)
  - whether neutral names the starter, so that a brand built on it reaches the starter's roles. Every project that uses neutral would then hold and lock the starter (DEC-008 point 4).
  - what a brand built on neutral keeps of its drawings of a top that neutral comes to serve. Neutral's drawings then win, with no break (DEC-034 point 8).
  - whether the capability's reference keeps sending a project that wants a look of its own to a brand with no base

  Whoever maintains the capability decides it in a record of the capability, by what serves every project that builds on neutral. This record decides nothing of it, and nothing here waits on it.
- **Revisit this record** if a brand built on the neutral brand could come to hold all that project-kit's brand then holds. That is every value it gives, its logo, its drawings and any axis of its own. Whether the brand moves onto neutral is weighed at that time.
- **No migration and no changeset:** nothing ships, no installed project's state changes, and no file of the capability changes.
