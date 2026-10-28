---
id: DEC-062
title: Each axis is put on the board in the substrate map, and the board flag says only that a board exists
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project puts an axis on its Projects v2 board by binding it there in its substrate map, one axis at a time, state among them. The `has_projects_v2_board` flag says only that the project has a board. Where a project binds state to its board, the board's Status says where an open issue stands, and a closed issue is Done whatever its card says. A migration keeps each axis where a project reads it today, with state on the native primitives until the project itself moves it.

## Context

[project-management:DEC-051-axis-carriage-activation] made a map binding govern the axis it names, and left the flag to govern carriage wherever the map is silent (point 3). Under a set flag, priority, workstream and state all live on the board unless the map names them. DEC-051 kept that as a legacy default, so that no working configuration changed on upgrade. It named retiring it as a later decision (its Implications).

On 28 October the maintainer decided that where an issue's state lives is a per-project choice, made in the substrate map, and that each axis is chosen there on its own ([#2243](https://github.com/aleskalfas/project-kit/issues/2243)). Two rulings stand in the way. [project-management:DEC-006-state-machine-and-cascade] makes a board's Status a projection in every project, with native winning where the two disagree, so no project can make its board the source of its state. The flag's carriage puts three axes on the board at once, so a project that sets the flag to move one axis moves all three.

A project with no map cannot write one to move a single axis either. An axis absent from a present map degrades ([project-management:DEC-036-substrate-pluggable-adoption] point 2), so a map that binds only priority to the board degrades type, workstream and state. DEC-051 named this obstacle when it rejected letting the map win where it is silent: no migration could write the repair.

## Decision

**Each axis is put on the board in the substrate map, state among them, and the board flag says only that a project has a board. Where the map puts state on the board, the board's Status is the source of an open issue's position. The map can name the kit's own labels for an axis, and carries nothing beyond its bindings. A migration keeps each axis where an existing project reads it.**

### 1. The flag says only that a board exists

`has_projects_v2_board` says that the project has a Projects v2 board. It governs what follows from that: which board it is, and that every issue belongs on it ([project-management:DEC-019-mandatory-issue-state]). It carries no axis. An axis lives on the board only where the map binds it there with `board: true` (DEC-051 point 2), and that binding needs the flag to be set.

### 2. Where the map is silent, an axis reads as it does with no board

An axis the map does not bind reads as DEC-036 point 2 says, whether the project has a board or not. With no map, it reads the kit's own labels. In a present map, an axis that is absent or marked `unsupported` degrades. So `unsupported` means one thing with a board or without: the axis has no encoding, and the rules that need it soften.

### 3. The map can name the kit's own labels

The map gains an arm, `kit-label: true`. It takes no parameter and is admissible on every axis. It binds the axis to the kit's own labels, so the axis is read, written and checked, and has its labels created, as it is with no map.

A project can then write a map that moves one axis to its board and keeps the others on the kit's own labels, with none degrading. The rule that an axis absent from a present map degrades stands as it is.

### 4. A map carries nothing beyond its bindings

A present map says where each axis lives through the binding it gives the axis, and degrades an axis it omits (DEC-036 point 2). Its presence carries nothing more, and puts the project in no mode. So a `kit-label` axis behaves in any map as it does with no map, and a map that binds every axis that way behaves as no map. Each behaviour that keys on a map's presence keys instead on the binding of the axis it concerns, as the Implications list.

### 5. Where the map puts state on the board, the board's Status is the source of an open issue's position

Where an issue's state lives is the project's choice, made in its map as for every other axis. Where the map binds state to the board with `board: true` (DEC-051 point 2), the board's Status is the source of an open issue's position: Todo, Backlog, In Progress or Review. DEC-051 point 6 says how it is read, and what a read that fails yields. Elsewhere the native primitives are the source, and a board's Status, where a board exists, is a projection that native wins over (DEC-006).

In every project, closed stays native and wins. A closed issue is Done whatever its card says, so the closure cascade never needs the board.

A project binds state to its board only by its own choice. A brownfield project may make it at adoption, where each axis is chosen ([project-management:DEC-037-adoption-ceremony] point 1), and any project may make it later. Before it does, its board's Status options are checked against the five states, and every open issue is given a card and a Status.

### 6. A migration keeps each axis where an existing project reads it

The change that ends the flag's carriage ships a migration ([pkit:COR-010]). It acts only in a project whose flag is set, and keeps there each axis where the project reads it that day.

- **Priority and workstream** stay on the board, as the flag carries them. Each that the map omits or marks `unsupported` gets `board: true`, keeping the axis's `default:`.
- **State** stays native, read from the kit's labels and the native primitives. Where the map omits it or marks it `unsupported`, it gets `kit-label: true`. The migration never binds state to the board, which is the project's own choice (point 5).
- **With no map,** it writes one with those bindings, and `kit-label: true` on every other axis. By point 4, that map behaves as no map but for its board bindings.
- **In a present map,** it keeps the comments and every other key, and changes only the axes named above.

It runs once. It acts only on a positive sign that it has not run in the project, and no axis's binding is that sign, since an axis left `unsupported` reads the same before the migration as after a later choice by the project. So an axis a project later leaves `unsupported` under its board is never overwritten. Its report names each binding it wrote, so an adopter who meant otherwise changes it, and the map stays the adopter's.

### What this overturns, and what stands

This record partially supersedes DEC-051 and DEC-006. Each overturned passage stays in its record as it stood.

- **Overturned in DEC-051:**
  - the flag that governs carriage where the map is silent, which point 2 here replaces. These passages state it: the title's "elsewhere the flag still governs carriage", the summary's "where the map says nothing, the flag governs carriage as it does with no map", and the plain-terms "If your map is silent about it, nothing changes from today". So do point 3 whole, point 4's "if it is silent, ask the flag", the Implications' "It continues to govern wherever the map is silent", said of DEC-012's carriage table, and the rejected alternative's "silence keeps today's behaviour".
  - in point 1, `unsupported` that "falls through to the flag exactly as an axis the map omits does". It degrades, as an omitted axis does (point 2 here).
  - the Implications' "The flag keeps one carriage job", with its guard that exactly one site reads the flag for carriage. No site reads it for carriage.
  - the Implications' "Adopters holding the workaround are told, not rewritten", where its migration "does not edit the map". The migration of point 6 here edits it.
  - the case against a map that decides every axis, silent or not: the Rationale's "Why 'the binding wins where it exists' rather than a global winner", and the rejected alternatives "The map always wins, even where silent" and "Making a present map authoritative for board-claimable axes". Points 3, 4 and 6 here answer it.
- **Overturned in DEC-006:** the State machine's "When a Projects v2 board exists, its Status field is a projection the agent maintains. When the board and native primitives disagree, native wins.", for a project whose map binds state to its board. Point 5 here replaces it there, and it stands as the default.
- **Stands in DEC-051:**
  - point 1's rule that a binding governs the axis it names, for every consumer
  - point 4's one accessor, asked by every consumer
  - point 5's rule that a declined write never reports success. The double claim it softens no longer arises, since the flag claims no axis.
  - the flag's jobs of board identity and membership
- **Refined in place:**
  - DEC-006: its Implications on the Status a move writes where the board carries the state, and on a card a person drags by hand, left open
  - DEC-012: its title, its substrate per axis, its rule for priority and workstream, its Rationale on the two adoption paths, and its implications on parity and on Status
  - DEC-036: point 1's list of arms, and point 5, where bootstrap's label creation follows each binding and a map's presence suppresses nothing
  - DEC-037: point 1, where each axis's place is chosen at adoption, point 2's capability matrix, and its Implication on the map's binding kinds
  - DEC-051: point 2, which admits `state` on the `board:` arm, point 6, the read of a board-carried state, and its Implications on admissibility and on the architecture record that places the read

## Rationale

**Why each axis in the map.** The map already decides an axis wherever it names one (DEC-051 point 1), and it activates per axis, with no global switch (DEC-036 point 2). The flag's carriage was the one global switch left: a second declaration that decided three axes at once wherever the map was silent. With every carriage in the map, there is one place to ask where an axis lives, and a project moves its axes to the board one at a time.

**Where the state lives.** A project whose people move cards on its board does its work there, so its board holds where open work stands. A project with no board, or one that keeps its board as a view, keeps the native source. Closed stays native in every project: a merge closes its Task with no board in the loop, and the closure cascade counts closed children. So no board read stands between a merge and the cascade, and no card left in another column holds a closed issue open.

**Why DEC-006 is superseded in part rather than refined.** DEC-006 makes a board's Status a projection in every project. For a project that binds state to its board, this record makes the Status the source, so another record decides otherwise there. DEC-006's sentence stands as the default for every other project.

**Why an arm for the kit's own labels.** A present map degrades every axis it omits, and that rule protects a brownfield adopter from a demand for labels it cannot create (DEC-036 point 2). A project that can create the kit's labels needs to keep them for some axes while it moves others. Naming them per axis says that, and leaves the rule for an absent axis as it stands.

**Why a map carries nothing beyond its bindings.** The migration writes a map into each project that sets the flag and has none (point 6). Were a map's presence to put a project in a brownfield mode, that map would switch on a mode the project never chose, such as a capability matrix in place of its label checks. Keeping the migration from writing a map would move priority and workstream off the board in such a project, once the flag carries no axis, which is the change the migration exists to prevent. Keying each behaviour on its axis's binding changes less: a map with no `kit-label` binding behaves as it did, so only a map that uses the new arm sees the change.

**Why the migration may write the adopter's map.** DEC-051 refused to rewrite an adopter's `unsupported` workaround, since its signature could not show what the adopter meant. This migration infers no intent. It writes, for each axis, where the project reads it on the day it runs, so nothing an adopter relies on changes, and it reports each binding for the adopter to change. It runs once, so a choice the project makes after it stands.

**Why the migration keeps state native.** Under a set flag, the writers write no state label, since the flag puts state on the board, yet no command reads the board's Status as an issue's state. Each command reads an open issue's state from the native primitives. Binding state to the board would make a board nobody has checked the source of every open issue's position, with Status options never matched to the five states and open issues with no card or no Status. So the migration keeps state where it is read, and the project moves it once its board is ready (point 5).

### Alternatives considered

- **Keep the flag's carriage where the map is silent.** Rejected: a project could not move one axis to its board without moving all three, and a project with no map could not choose per axis at all.
- **A list of board axes in the configuration.** Rejected: a second place that says where an axis lives, beside the map, which DEC-036 and DEC-051 both refuse.
- **A map that binds only `board:` arms leaves its other axes on the kit's labels.** Rejected: whether an omitted axis degrades would then hang on the map's other entries, an implicit switch of the kind DEC-036 rejects.
- **Name the kit's own labels with a `label` remap.** Rejected: a `label` binding names labels the adopter owns, so bootstrap would not create them and the commands that manage the kit's labels would leave them alone.
- **A migration that only warns.** Rejected: a project that sets the flag and leaves its map silent would lose priority and workstream from its board on upgrade, until it acted.
- **A migration that binds state to the board, as the flag carries it.** Rejected, as "Why the migration keeps state native" says.
- **A migration that writes no map where a project has none.** Rejected, as "Why a map carries nothing beyond its bindings" says.

## Implications

- **The carriage accessor** asks the map alone. Where the map is silent, it answers as DEC-036 point 2 says, and a guard test holds that no site reads the flag for carriage.
- **The map's schema** gains the `kit-label` arm on every axis. Every consumer that reads, writes or creates the kit's own labels with no map does the same for a `kit-label` axis.
- **What keys on a map's presence** keys on the bindings instead (point 4). For a `kit-label` axis, each behaves as with no map:
  - the map schema's note that the map is a brownfield project's file, whose presence switches the project out of greenfield
  - the prerequisite check's capability matrix, which takes the place of the kit's label checks wherever a map is present (DEC-037 point 2). A `kit-label` axis keeps the label checks.
  - the checks of the kit's title prefixes, in the prerequisite check and the issue validator, which a present map skips unless `type` is bound to title prefixes
  - bootstrap's suppression of the kit's label palette, which follows each binding (DEC-036 point 5)
- **The migration** ships in the change that ends the flag's carriage, and needs no reader of a board-carried state, since it binds no state to the board. Its sign that it has not run is chosen with that change.
- **After the migration,** a project that set the flag writes the kit's state labels with each move, and keeps the board's Status as the state's projection (DEC-006), as any project whose state is native does.
- **The prerequisite check** reports an axis that the map omits under a configured board as degraded, as it reports any omitted axis. Its advice to declare `board: true` for such an axis goes with the flag's carriage.
- **Adopter documentation** that says a configured board claims priority, workstream and state goes stale, and changes with the build.
- **The architecture records** that describe the flag's carriage are the architect's to refine. They are the board-versus-label switch of the label read-path contract ([pkit:ADR-026] point 4) and the case where carriage keys on the flag in the board read-path contract ([pkit:ADR-053] point 2).
- **A surface change** for the capability: the flag's meaning, a new arm and a migration. The build's changeset declares it.
- **Acceptance:** this record partially supersedes the accepted DEC-051 and DEC-006, and refines DEC-006, DEC-012, DEC-036, DEC-037 and DEC-051 in place, so accepting it needs the maintainer's sign-off. The refinements land only with this record accepted.
