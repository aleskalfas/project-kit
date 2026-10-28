---
id: DEC-062
title: Each axis is put on the board in the substrate map, and the board flag says only that a board exists
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project puts an axis on its Projects v2 board by binding it to the board in its substrate map, one axis at a time. The `has_projects_v2_board` flag says only that the project has a board, and carries no axis, so priority can move to the board before state. The map gains an arm that names the kit's own labels, so a project can write a map and keep some axes on them. A migration writes, for each project that sets the flag, the bindings that keep every axis where it is carried.

## Context

[project-management:DEC-051-axis-carriage-activation] made a map binding govern the axis it names, and left the flag to govern carriage wherever the map is silent (point 3). Under a set flag, priority, workstream and state all live on the board unless the map names them. DEC-051 kept that as a legacy default, so that no working configuration changed on upgrade. It named retiring it as a later decision (its Implications).

On 28 October the maintainer decided that where an issue's state lives is a per-project choice, made in the substrate map, and that each axis is chosen there on its own ([#2243](https://github.com/aleskalfas/project-kit/issues/2243)). The flag's carriage stands in the way. A project that sets the flag to put one axis on its board puts all three there.

A project with no map cannot write one to move a single axis either. An axis absent from a present map degrades ([project-management:DEC-036-substrate-pluggable-adoption] point 2), so a map that binds only priority to the board degrades type, workstream and state. DEC-051 named this obstacle when it rejected letting the map win where it is silent: no migration could write the repair.

## Decision

**Each axis is put on the board in the substrate map. The board flag says only that a project has a board, and carries no axis. The map can name the kit's own labels for an axis, and a migration writes the bindings that keep every axis where the flag carries it today.**

### 1. The flag says only that a board exists

`has_projects_v2_board` says that the project has a Projects v2 board. It governs what follows from that: which board it is, and that every issue belongs on it ([project-management:DEC-019-mandatory-issue-state]). It carries no axis. An axis lives on the board only where the map binds it there with `board: true` (DEC-051 point 2), and that binding needs the flag to be set.

### 2. Where the map is silent, an axis reads as it does with no board

An axis the map does not bind reads as DEC-036 point 2 says, whether the project has a board or not. With no map, it reads the kit's own labels. In a present map, an axis that is absent or marked `unsupported` degrades. So `unsupported` means one thing with a board or without: the axis has no encoding, and the rules that need it soften.

### 3. The map can name the kit's own labels

The map gains an arm, `kit-label: true`. It takes no parameter and is admissible on every axis. It binds the axis to the kit's own labels, so the axis is read, written and has its labels created as it does with no map.

A project can then write a map that moves one axis to its board and keeps the others on the kit's own labels, with none degrading. The rule that an axis absent from a present map degrades stands as it is.

### 4. A migration keeps every axis where it is carried

The change that ends the flag's carriage ships a migration ([pkit:COR-010]). It acts only in a project whose flag is set, and writes there the bindings that keep each axis where it is carried that day.

- **In a present map,** each of priority, workstream and state that the map omits or marks `unsupported` gets `board: true`.
- **With no map,** it writes one. Priority, workstream and state get `board: true`, and every other axis gets `kit-label: true`.
- **Its report** names each binding it wrote, so an adopter who meant otherwise changes it. The map stays the adopter's.

### What this overturns, and what stands

This record partially supersedes DEC-051. Each overturned passage stays in DEC-051 as it stood.

- **Overturned in DEC-051:**
  - the flag that governs carriage where the map is silent: the second half of the title, the summary's "where the map says nothing, the flag governs carriage", the plain-terms "If your map is silent about it, nothing changes from today", point 3 whole, point 4's "if it is silent, ask the flag", and the Implications' carriage table that governs wherever the map is silent. Point 2 here replaces them.
  - in point 1, `unsupported` falling through to the flag as an omitted axis does. It degrades, as an omitted axis does (point 2 here).
  - the Implications' "The flag keeps one carriage job", with its guard that exactly one site reads the flag for carriage. No site reads it for carriage.
  - the case against a map that decides every axis, silent or not: the Rationale's "Why the binding wins where it exists", and the rejected alternatives "The map always wins, even where silent" and "Making a present map authoritative". Points 3 and 4 here answer it, with an arm for the kit's labels and a migration that writes the bindings.
- **Stands in DEC-051:**
  - point 1: a binding governs the axis it names, for every consumer
  - point 2, and the read of a board-carried state in point 6
  - point 4's one accessor, asked by every consumer
  - point 5's rule that a declined write never reports success. The double claim it softens no longer arises, since the flag claims no axis.
  - the flag's jobs of board identity and membership
- **Refined in place:**
  - DEC-012's substrate per axis, its rule for priority and workstream, and its implications on parity and on Status
  - DEC-036 point 1's list of arms, and point 5, since a `kit-label` binding does not stop bootstrap creating the kit's labels
  - DEC-037's list of the map's binding kinds

## Rationale

**Why each axis in the map.** The map already decides an axis wherever it names one (DEC-051 point 1), and it activates per axis, with no global switch (DEC-036 point 2). The flag's carriage was the one global switch left: a second declaration that decided three axes at once wherever the map was silent. With every carriage in the map, there is one place to ask where an axis lives, and a project moves its axes to the board one at a time.

**Why an arm for the kit's own labels.** A present map degrades every axis it omits, and that rule protects a brownfield adopter from a demand for labels it cannot create (DEC-036 point 2). A project that can create the kit's labels needs to keep them for some axes while it moves others. Naming them per axis says that, and leaves the rule for an absent axis as it stands.

**Why the migration may write the adopter's map.** DEC-051 refused to rewrite an adopter's `unsupported` workaround, since its signature could not show what the adopter meant. This migration infers no intent. It writes what each axis resolves to on the day it runs, so nothing an adopter relies on changes, and it reports each binding for the adopter to change.

**Why state goes with the others.** Under a set flag, the writers already leave state to the board and write no state label. The migration's `board: true` on state keeps that, and the reader of DEC-051 point 6 then reads the board's Status rather than guess the state from the Milestone.

### Alternatives considered

- **Keep the flag's carriage where the map is silent.** Rejected: a project could not move one axis to its board without moving all three, and a project with no map could not choose per axis at all.
- **A list of board axes in the configuration.** Rejected: a second place that says where an axis lives, beside the map, which DEC-036 and DEC-051 both refuse.
- **A map that binds only `board:` arms leaves its other axes on the kit's labels.** Rejected: whether an omitted axis degrades would then hang on the map's other entries, an implicit switch of the kind DEC-036 rejects.
- **Name the kit's own labels with a `label` remap.** Rejected: a `label` binding names labels the adopter owns, so bootstrap would not create them and the commands that manage the kit's labels would leave them alone.
- **A migration that only warns.** Rejected: a project that sets the flag and leaves its map silent would lose priority, workstream and state on upgrade, until it acted.

## Implications

- **The carriage accessor** asks the map alone. Where the map is silent, it answers as DEC-036 point 2 says, and a guard test holds that no site reads the flag for carriage.
- **The map's schema** gains the `kit-label` arm on every axis. Every consumer that reads, writes or creates the kit's own labels with no map does the same for a `kit-label` axis.
- **The migration** ships in the change that ends the flag's carriage. That change lands no earlier than the reader of a board-carried state (DEC-051 point 6), since the migration writes `board: true` on state.
- **The prerequisite check** reports an axis that the map omits under a configured board as degraded, as it reports any omitted axis. Its advice to declare `board: true` for such an axis goes with the flag's carriage.
- **Adopter documentation** that says a configured board claims priority, workstream and state goes stale, and changes with the build.
- **The architecture records** that describe the flag's carriage are the architect's to refine once this record is accepted. They are the board-versus-label switch of the label read-path contract ([pkit:ADR-026] point 4) and the case where carriage keys on the flag in the board read-path contract ([pkit:ADR-053] point 2).
- **A surface change** for the capability: the flag's meaning, a new arm and a migration. The build's changeset declares it.
- **Acceptance:** this record partially supersedes the accepted DEC-051 and refines DEC-012, DEC-036 and DEC-037 in place, so accepting it needs the maintainer's sign-off. The refinements land only with this record accepted.
