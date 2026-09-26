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

5. **A derived location is recorded when it is first used.** A component that derives a location from a root stores it as an explicit value when it first places a document there, in the overlay or in its own configuration. From then on it reads the stored value, not the root. Recording follows the same consent forms as the backbone configuration (COR-048). Recording a location into an overlay category is how a project chooses it: once recorded, agents that reference that category resolve to it. That is intended, because it is now an explicit choice.

6. **No document moves, no location changes silently.** Introducing the roots changes no location that is already resolved, because existing overlay values are explicit. Because of point 5, changing a root later affects only locations chosen afterwards. The methodology's status report shows the declared roots. It also shows any explicit documentation location lying outside the internal root, so a project can see what a relocation would involve. Moving documents is always an explicit, reviewable operation.

7. **Visible and checked.** The status report shows each resolved documentation location and where it came from: explicit, or derived from a root. Validation checks the documentation key against the configuration schema (COR-048) and checks each root against the constraints in point 1. A declared root that does not exist yet produces a warning, not a failure, since a fresh project may have no documentation folder. A command that merely reads an invalid root warns and uses the default, as COR-048 requires of readers. The **user root** has no backbone consumer; it exists for components that place user-facing documents.

## Rationale

**Why the backbone configuration, not more overlay categories.** The overlay exists so agent bodies can name project content at deploy time. Commands, checks and capabilities are the ones that need the roots. Putting the roots in the overlay would make every one of those readers learn the overlay's resolution rules. The backbone configuration (COR-048) exists for project-level declarations like this one, and serves all of them from one source.

**Why derive only where a location is being chosen.** Agents resolve placeholders from explicit overlay values only. Deriving at deploy time would silently resolve placeholders the project never filled, and change what agents read and whether they deploy. Deriving where a location is filled in, stamped or placed gives every new location the right home. It keeps each choice explicit, and changes nothing that already resolves.

**Why both roots default to `docs/`.** With the default root, derived locations are identical to today's conventional ones, so declaring nothing changes nothing. Most projects keep both audiences in one folder anyway. A separate default would impose a separation rule that belongs to a documentation discipline.

**Why no migration.** Every location that resolves today is an explicit overlay value, and an unset category stays unset. Introducing the roots therefore changes no resolved location, and there is nothing to pin or rewrite.

### Alternatives considered

- **Two more overlay categories for the roots.** Rejected. The overlay is an agent-body substitution mechanism, so every non-agent reader would have to parse it, and the existing categories would stay unrelated to the roots.
- **Each capability configures its own locations.** Rejected. The same project's technical documentation would be described several times over, and nothing would record that its parts share one space.
- **Derive at agent deploy time.** Rejected. It resolves placeholders the project never filled, silently.
- **Default the internal root to a separate folder.** Rejected. Derived locations would diverge from today's, and the backbone would be imposing a documentation discipline's rule.
- **Move existing documents into the roots on upgrade.** Rejected. It acts on project-owned content, breaks citations from outside the repository, and cannot judge which audience an ambiguous document serves.

## Implications

- **The configuration schema** (COR-048) gains the documentation key; its field names are documented in the CLI reference.
- **The commands that fill missing overlay categories** compute each conventional location from the internal root. Where they create a missing folder, they create it at the derived location, and they test for an existing folder there too. Commands that **stamp documents** fall back to the roots when their category is unset, and record what they chose (point 5).
- **The status report** lists the roots, each resolved documentation location with its source, and explicit locations outside the internal root.
- **Capabilities that keep documents** place them under the roots and inherit points 2, 5 and 6.
- **No migration.** Existing overlay values stay authoritative.
