---
id: COR-049
title: A project declares where its documentation lives, by audience
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project's documentation serves two audiences. **Users** read how to use the system. **Maintainers** — and the agents that write, check and extend the project — read why it is built the way it is: decisions, architecture, contributing and release guides, analysis of what the system must do. Most projects keep both in one folder; some separate them.

The methodology already locates some of this. Agents name project documents through overlay categories (COR-013), and architectural decisions live at an overlay-resolved location with a conventional default (COR-025). Each category is configured on its own, and an agent's placeholders resolve only to what the overlay explicitly contains. Nothing tells the methodology that these locations are parts of *one* technical documentation space, and nothing names where user-facing documentation lives. Every new component that places or reads documents would otherwise pick its own folder or guess.

## Decision

**A project declares two documentation roots — one for internal (technical) documentation and one for user-facing documentation — in its backbone configuration. Whatever in the methodology fills in, places or looks up a documentation location derives it from those roots, unless an explicit location is already set.**

1. **The roots.** The project's backbone configuration (COR-048) gains a documentation key, owned by this record, naming an **internal root** and a **user root**. Both default to `docs/`. A root is a relative path whose *resolved* location (after following links) lies inside the repository and outside the methodology's own tree. The two roots may be the same folder, or one may be nested inside the other. The roots describe *layout*. Whether a project should separate its audiences is a documentation discipline's rule, not the backbone's.

2. **Independent of any capability; who may write it.** Declaring the roots is optional and possible at any time; with no declaration the defaults apply. The writers this record names are the backbone's own configuration commands and any capability that places or reads documents, which may show the resolved roots on install or first use and offer to record them. Every write follows COR-048's consent rule, and nothing removes the key on uninstall.

3. **Where derivation applies.** An **explicit location always wins**: a value already set in the overlay, or wherever a component is configured. Otherwise, a component that has to *choose* a documentation location derives it from the roots. That covers:
   - the commands that fill missing overlay categories;
   - commands that stamp new documents;
   - capabilities that keep documents of their own.

   **Agent deployment derives nothing.** It resolves placeholders only from what the overlay explicitly contains; an unset category stays unset.

4. **The derivation rule.** A category that locates a *folder* of documents derives as the internal root plus that category's conventional sub-path. Architecture documents and architectural decision records are examples; with the default root they land exactly where they do today. A category that lists individual *files*, such as the project-root documents, does not derive. The conventional sub-paths of the overlay's categories are kept in one list the backbone owns, relative to the root. A capability declares the sub-paths of its own documents in its own package metadata. Neither hard-codes a folder.

5. **A derived location is recorded when it is first used.** A component that derives a location from a root stores it as an explicit value when it first places a document there, in the overlay or in its own configuration. From then on it reads the stored value, not the root. What consent the recording takes turns on one question: **does it change, when it is written, what anything reads or may write among documents already there?**
   - **A location a component keeps in its own configuration: no.** Until it is recorded the location is read as derived, so the value recorded is the one already in use, and recording only keeps a later change of root from moving it (point 6). Running the command is the consent. The command says what it recorded, which root the value was derived from, and where to change it.
   - **An overlay category, over a folder that already holds the project's documents: yes.** Agent deployment derives nothing (point 3), so until the category is recorded no agent reaches those documents through it, and once it is, every agent that references the category does — to read them, or to write them where the agent owns the category (COR-013). Recording a location into an overlay category is how a project chooses it, and that is intended, because the category is an explicit choice from then on. Here the choice is put to whoever runs the command, in the consent forms of the backbone configuration (COR-048 point 5): interactively, by asking once; non-interactively, only when an explicit confirmation flag is given. For a command that only shows what it would record until it is told to write, the option that tells it to write is that flag. With nobody to ask and no flag, the command records nothing and places nothing, since a document placed at an unrecorded location is left behind by a later change of root (point 6). It makes no difference whether the command also places a document there.
   - **An overlay category, over a folder the command creates or one that holds nothing: no.** No document is handed over, so it is recorded as a location in a component's own configuration is, and said in the same way.

   These are the least a command asks. A component may ask more; a command that asks and is declined records nothing and places nothing. Whether an agent may consent, on a person's behalf, to recording an overlay category over existing documents is a separate decision, not taken here: this record says only that the choice is put to whoever runs the command.

6. **No document moves, no location changes silently.** Introducing the roots changes no location that is already resolved, because existing overlay values are explicit. Because of point 5, changing a root later affects only locations chosen afterwards. The methodology's status report shows the declared roots. It also shows any explicit documentation location lying outside the internal root, so a project can see what a relocation would involve. Moving documents is always an explicit, reviewable operation.

7. **Visible and checked.** The status report shows each resolved documentation location and where it came from: explicit, or derived from a root. Validation checks the documentation key against the configuration schema (COR-048) and checks each root against the constraints in point 1. A declared root that does not exist yet produces a warning, not a failure, since a fresh project may have no documentation folder. A command that merely reads an invalid root warns and uses the default, as COR-048 requires of readers. The **user root** has no backbone consumer; it exists for components that place user-facing documents.

## Rationale

**Why the backbone configuration, not more overlay categories.** The overlay exists so agent bodies can name project content at deploy time. Commands, checks and capabilities are the ones that need the roots. Putting the roots in the overlay would make every one of those readers learn the overlay's resolution rules. The backbone configuration (COR-048) exists for project-level declarations like this one, and serves all of them from one source.

**Why derive only where a location is being chosen.** Agents resolve placeholders from explicit overlay values only. Deriving at deploy time would silently resolve placeholders the project never filled, and change what agents read and whether they deploy. Deriving where a location is filled in, stamped or placed gives every new location the right home. It keeps each choice explicit, and changes nothing that already resolves.

**Why consent follows what the recording changes, not the fact of a write.** Asking is worth its cost where a write does something its author might not want and could not easily see or undo. Recording a location in a component's own configuration does nothing on the day it is written: the value was already in use, the command says so, and the entry is a value in a file the project owns and can review. Declining it is the branch that harms, since the location then moves with the next change of root (point 6), and a confirmation demanded of a non-interactive run is given by whatever drives the run, which makes it ceremony. Recording an overlay category over existing documents differs in effect: it extends an agent's reach, and the write authority of an agent that owns the category, to documents the project wrote before, at a path nobody may have typed. That is the kind of write the backbone configuration's consent rule exists for, which confirms even a write named in full (COR-048 point 5). A flag passed by whatever drives a run is weak consent here too, but it puts the choice in the command itself, where it can be seen and reviewed, and without it the run stops — a real choice left visible, where in a component's own configuration there was none to make. The roots, declared or default, are the project's standing answer to where its documents go; a command that places a document applies that answer, and what is left to ask is only whether existing documents come under an agent's reach.

**Why both roots default to `docs/`.** With the default root, derived locations are identical to today's conventional ones, so declaring nothing changes nothing. Most projects keep both audiences in one folder anyway. A separate default would impose a separation rule that belongs to a documentation discipline.

**Why no migration.** Every location that resolves today is an explicit overlay value, and an unset category stays unset. Introducing the roots therefore changes no resolved location, and there is nothing to pin or rewrite.

### Alternatives considered

- **Two more overlay categories for the roots.** Rejected. The overlay is an agent-body substitution mechanism, so every non-agent reader would have to parse it, and the existing categories would stay unrelated to the roots.
- **Each capability configures its own locations.** Rejected. The same project's technical documentation would be described several times over, and nothing would record that its parts share one space.
- **Derive at agent deploy time.** Rejected. It resolves placeholders the project never filled, silently.
- **Default the internal root to a separate folder.** Rejected. Derived locations would diverge from today's, and the backbone would be imposing a documentation discipline's rule.
- **Move existing documents into the roots on upgrade.** Rejected. It acts on project-owned content, breaks citations from outside the repository, and cannot judge which audience an ambiguous document serves.
- **Ask, or require the confirmation flag, on every first recording.** Rejected. Where the recorded value is already in use the question protects nothing, declining leaves a location the next change of root moves, and a non-interactive run answers mechanically.
- **Ask only when a command records without placing a document.** Rejected. Whether a document is placed says nothing about what the recording hands over: a command can place one document into a folder full of others and record an overlay category over all of them.
- **Never ask; treat every recording as applying the roots.** Rejected. Recording an overlay category over existing documents changes what agents read and may write, which declaring a root does not choose.

## Implications

- **The configuration schema** (COR-048) gains the documentation key; its field names are documented in the CLI reference.
- **The commands that fill missing overlay categories** compute each conventional location from the internal root. Where they create a missing folder, they create it at the derived location, and they test for an existing folder there too. Commands that **stamp documents** fall back to the roots when their category is unset, and record what they chose (point 5).
- **The status report** lists the roots, each resolved documentation location with its source, and explicit locations outside the internal root.
- **Capabilities that keep documents** place them under the roots and inherit points 2, 5 and 6.
- **No migration.** Existing overlay values stay authoritative.
