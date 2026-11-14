---
id: DEC-044
title: A brand gives its own components' tokens their values, as it gives those of a library it names
status: proposed
date: 2026-11-14
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand may hold components of its own, such as a badge no shared library has, and each may declare component tokens, such as `component.acme.badge.fill` in a brand named `acme`. The brand gives such a token a value in its own token files, at that path, as it gives a value to a token of a library it names. A token it holds under `component.acme` that names no token of its components, or is of another type, gives nothing, and fails the check. A base opens its own components' tokens as it opens any role, so a brand built on it restyles one of the base's parts alone, further along a chain too. Under a brand outside that chain, the brand's components draw their tokens at their defaults, in that brand's values.

## Context

The record of component tokens lets a brand's own components declare and read their tokens as a library's components do, at `component.<brand>.<component>.<name>` ([visual-communication:DEC-035-component-tokens] points 1 to 4). A brand reaches the component tokens of a library's components only where it names the library. Its tokens under `component.<library>` are judged as its tokens under that library's name: where it names the library, one that names no token its components declare, or is of another type, is a finding ([visual-communication:DEC-008-library-role-defaults] point 4, DEC-035 point 7). A brand names no library for its own components. So DEC-035 point 7 keeps a brand's tokens under `component.<its own name>` private, with no finding, and leaves two questions to the change that builds a brand's own components ([project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573)): what gives those components' tokens values, and how the check judges a brand's tokens under its own name.

Three facts bear on the answer:
- **A brand's part reads roles, never the brand's private tokens.** A component names roles, and only a brand holds a value ([visual-communication:DEC-001-visual-communication-discipline] point 5). A brand's private tokens, such as a palette, are never exported and never open ([visual-communication:DEC-004-brands-and-notations] point 5).
- **A base opens component tokens.** A base lists the roles a brand built on it may give values, component tokens among them, and along a chain of brands each link opens only what is open to it. A brand built on a base keeps the base's parts, and may add parts of its own with their component tokens (DEC-004 point 6).
- **A brand's component may be drawn under another brand.** A top a brand holds is drawn under another brand in that brand's values ([visual-communication:DEC-034-brand-drawings] point 4), and a piece may place a part another brand holds (DEC-034, Rationale for point 4).

The capability as built resolves a brand with the component tokens of component libraries alone. A brand's own component that reads its own token finds no role at its path, which the engine reports. The token's default is judged nowhere, and a base whose open roles name one opens nothing, and fails.

## Decision

**A brand gives its own components' tokens values under `component.<its own name>`, and the check judges its tokens there as under the name of a library it names. A base opens them as it opens any role, and a brand along its chain gives one a value only where its base opens it. Under any other brand, they take their defaults.**

### 1. A brand gives its own components' tokens values, as it gives a named library's

- **Reached as if named.** A brand reaches the component tokens of the components it holds, its drawings and a top it holds among them, as it reaches those of a library it names (DEC-008 point 4): to give one a value, open it or alias it. It names no library for them, since they are its own.
- **At the token's path.** Each token the brand holds under `component.<its own name>` gives one of its components' tokens a value of its type. One that names no token they declare, or is of another type, gives nothing, and is a finding (point 4).
- **Resolved as any component token is** (DEC-035 point 4). The brand's value wins in the combinations its sources cover. Elsewhere the token's default holds, and takes the brand's value for the role it aliases.
- **A default aliases a role, never a private token.** It aliases what DEC-035 point 4 lets a default alias, the brand standing as the component's library: a role of the brand's own, or of a library it names, the shared roles included. A token the brand keeps private is no role (DEC-004 point 5).
- **Exported as any component token is.** The brand exports those it gives values (DEC-004 point 5), and the document of resolved values holds each, at the brand's value or at its default (DEC-008 point 5).

### 2. A base opens its own components' tokens, and a brand along its chain gives one a value only where it is open to it

A brand's *chain of bases* is its base, and each brand that base builds on as its base in turn (DEC-004 point 6).
- **A base opens them as it opens any role.** It opens a token of its own components, or a group of them by whole segments of their paths, such as `component.<its own name>`, whether or not it gives the token a value, as DEC-035 point 2 has a base open a token of a library it names.
- **Each link narrows.** A brand opens a token of a component of a brand along its chain only where its base opens it to it (DEC-004 point 6).
- **A brand gives such a token a value only where its base opens it to it.** The base's value comes first, then the brand's own, in the combinations its sources cover, and every token that aliases it follows (DEC-004 point 6).
- **No other brand of the chain is named.** A brand names its base by the major it fits, and each link names its own base so. The chain fixes the major of every brand along it, so a brand names none of them but its base to reach their components' tokens.
- **Judged as under a library it names.** A token a brand holds under `component.<the name of a brand along its chain>` that names no token of that brand's components, or is of another type, gives nothing, and is a finding. One that names a token its base does not open to it gives nothing too, as a value for any role its base does not open (DEC-004 point 11). Either way the base's value, or the token's default, holds.

### 3. Under any other brand, a brand's components take their tokens' defaults

- **Outside the chain.** Where a piece's brand neither holds a component nor has the brand that holds it along its chain of bases, the component draws each of its tokens at its default, in the piece's brand's values (DEC-035 point 4). So a top a brand holds, drawn under another brand (DEC-034 point 4), and a part of a brand that a piece places, draw in one brand's values.
- **The holding brand's values stay its own.** Its value for one of its components' tokens holds only under it and under each brand that has it along its chain of bases (point 2).
- **The piece's brand gives them nothing.** A token it holds under `component.<the holding brand's name>` stays private, as one under a library it does not name, and asks the brand's owner for attention where a piece's lock holds the holding brand with it (DEC-035 point 7).

### 4. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released brand version, it asks for attention and names who can correct it.
- **Where each lies.** A finding on a brand's own component's tokens lies in that component's file in the brand's version, as DEC-035 point 9 places one in its component's version. A finding on a brand's tokens under `component.<its own name>`, or under `component.<the name of a brand along its chain>`, lies in the brand's version, judged when the brand is checked alone, as DEC-008 point 9 places a brand's finding against a library it names.
- **Fails validation:**
  - each finding DEC-035 point 9 makes of a component's tokens and their defaults, on a brand's own component's
  - a brand's token under `component.<its own name>`, or under `component.<the name of a brand along its chain>`, that names no token of that brand's components, or is of another type
  - a brand's token that gives a value to a token of a component of a brand along its chain that its base does not open to it (DEC-004 point 11)
- **Asks for attention, never failing:**
  - a brand's token under `component.<the name of a brand outside its chain>`, where a piece's lock holds that brand with it (point 3)
  - a token that a drawing's file reads nowhere, as an experimental component's does (DEC-035 point 9), since a drawing carries no status (DEC-034 point 8)

### 5. What this changes in format 1

- **No schema refuses a file it accepted.** Only the check's judgement of a brand's tokens and open roles changes, as it did for a token under a library's own name (DEC-008 point 8).
- **Judged for the first time.** A token a brand holds under `component.<its own name>`, which stayed private before this record, gives a value or is a finding. An open role that names a token of a brand's own components opens it, where it opened nothing and failed.

## Rationale

**Point 1, the brand gives its own tokens values.** A brand's part reads roles alone, so a value the brand wants for one of its own parts, which no shared role carries, reaches the part only through a token it declares. The record of component tokens already resolves a brand's own component's tokens as a library's, a brand's value winning (DEC-035 point 4). The holding brand is both that brand and the component's library, so it needs no name for itself. Judged as under a library it names, a misspelt token fails where the brand's owner looks, rather than giving nothing without a word, the reason DEC-035 gives for its point 7.

**Point 2, the chain.** A base says what a brand built on it may change, and each link narrows what the one before it opens (DEC-004 point 6), so a brand reaches a token of a brand further down only where every link between opens it. Naming a library buys a brand values that never meet a major they were not tuned for (DEC-008, Rationale). Along a chain, each link names its base by major, and moving to a new major of a base breaks every brand built on it (DEC-008 point 4), so the chain already gives that. Asking a brand to name every brand of its chain would ask it to name brands other than its base, which DEC-034 leaves open.

**Point 3, the defaults elsewhere.** A piece is drawn in one brand's values. The holding brand's value for its token, drawn under another brand, would mix two brands' looks in one piece, which the record of a library's own roles refuses (DEC-008, Alternatives considered). The default draws the component in the piece's brand's values, as DEC-034 point 4 draws a top a brand holds.

**Point 4, the severities.** The project corrects its own brand's version, so a finding there fails (DEC-002 point 7). A drawing's token that its file reads nowhere breaks nothing, and nothing promises a drawing's tokens (DEC-034 point 8), so its owner may drop the token at once, as an experimental component's owner may (DEC-035, Rationale for point 9).

### Alternatives considered

- **The holding brand's own tokens always at their defaults under it,** given values only by the brands built on it: a brand could give its own part no value that no shared role carries, and a base could not give its own part the look it opens to the brands built on it.
- **A brand's own part reading the brand's private tokens:** a component would read a value, not a role (DEC-001 point 5). The private tokens a base reshapes freely would become a promise, and a brand built on it, which reaches only what its base opens, could never restyle that part.
- **A brand's tokens under `component.<its own name>` kept private:** a misspelt token would give nothing without a word.
- **One that names no token asking only for attention:** the project corrects its own brand, and DEC-008 point 9 fails the same mistake under a library the brand names.
- **A brand naming each brand of its chain:** for the reason the Rationale gives under point 2.
- **A brand reaching only its base's own components' tokens:** a base could not pass on what is open to it, against DEC-004 point 6.
- **The holding brand's values following its components under any brand:** for the reason the Rationale gives under point 3.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it with the pointer "(refinement per DEC-044)". Accepting this record accepts them (COR-066 point 5).
  - DEC-035 point 7, "Not under its own name," comes to read "Under its own name, and its chain's." It comes to say that a brand's token under `component.<its own name>` gives a token of the brand's own components a value of its type, and that one that names none they declare, or is of another type, gives nothing and is a finding. It comes to add that a brand's token under `component.<the name of a brand along its chain of bases>` is judged as DEC-044 point 2 has it, whether or not the brand names that brand, an exception to the point's two bullets before it.
  - DEC-035 point 2, "What a base opens": "A group opens only the tokens of the libraries the base names" comes to end "of the libraries the base names, of its own components, and of the components of a brand along its chain that its base opens to it".
  - DEC-035's Context, its last sentence, comes to say that a brand may hold components of its own, with their component tokens (DEC-004 point 6), and that DEC-044 decides what gives those tokens values and how the check judges a brand's tokens under its own name.
  - DEC-035's Implications, "[project-kit#2573] decides what point 7 leaves to it," comes to say that DEC-044 decides it.
  - DEC-008 point 4, "Named by major," comes to add that a brand reaches its own components' tokens as it reaches those of a library it names, and the tokens of the components of a brand along its chain of bases where its base opens them to it, naming none of that chain but its base.
  - DEC-008 point 4, "What it owes a library it names": "but for one under `component.<its own name>`" comes to say that one under `component.<its own name>` is judged so too, against its own components' tokens.
  - DEC-008 point 4, "Where it names none": "but for one under `component.<its own name>`" comes to except one under `component.<the name of a brand along its chain of bases>` too.
  - DEC-008 point 9: the failing finding on a brand's token under `component.<library>` comes to cover one under `component.<its own name>` and one under `component.<the name of a brand along its chain of bases>`. The attention for a token under `component.<library>` for a library a piece locks with the brand comes to except one under `component.<the name of a brand along its chain>` too.
  - DEC-034's Implications, "Left open": its last item, what gives the tokens of a brand's own components their values, comes out, since DEC-044 decides it.
- **Read against this record, and left as they stand:**
  - DEC-001 point 5: a brand holds the parts no shared component has, and a component names roles, never values.
  - DEC-004 point 5: a brand exports the tokens of its own components that it gives values, and a brand built on a base exports what its base exports.
  - DEC-004 points 6 and 11, which point 2 follows for a base's open roles, their narrowing along a chain, and a value for a role its base does not open.
  - DEC-008 point 5: the document of resolved values holds every component token of the libraries locked with the brand, the brand and its chain of bases among them.
  - DEC-034 point 4, which point 3 follows for a top a brand holds.
  - DEC-034 point 8 and DEC-035 point 6: a drawing carries no status, so no release compares its tokens as a component's, and a base that opens one promises what its open roles and its exports promise (DEC-004 point 5).
  - DEC-035 points 1, 3, 4, 6 and 9, which hold for a brand's own components as for a library's.
- **The Task that builds this record,** filed under [project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573) once this record is accepted:
  - The resolution of a brand, and the check of a brand alone, read the component tokens of the brand's own components and of each brand along its chain, and of each other brand a lock holds, and judge their declarations as a library's (points 1 and 4).
  - A brand's tokens under `component.<its own name>`, and under `component.<the name of a brand along its chain>`, give values and are judged (points 1, 2 and 4). A base's open roles open its own components' tokens and those open to it (point 2). A brand outside the chain draws them at their defaults (point 3).
  - The release reads a brand's own components' tokens as the brand's resolution reads them.
  - The capability's code cites this record where it cites [project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573) or DEC-035 point 7 for a brand's own components' tokens.
- **Edits to the capability's pages,** made in that Task, each anchored to this record:
  - `components.md`, Tokens: a brand's own component's token, and what gives it a value (points 1 and 3).
  - `files.md`, A library's roles: a brand's tokens under `component.<its own name>` (point 1) and under `component.<the name of a brand along its chain>` (point 2), in place of the line that they stay private.
  - `files.md`, Open roles: what a base opens of its own components' tokens and of its chain's (point 2).
  - `checks.md`, Brands, tokens and contrast: the `library-token`, `library-token-private`, `role-not-open` and `open-unknown` rows (point 4).
- **Revisit this record** if a brand comes to name a brand other than its base (DEC-034, Implications), or to hold roles of its own (DEC-004 point 6).
