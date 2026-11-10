---
id: DEC-035
title: A component declares its tokens in its own file, and no other component or piece reads them
status: proposed
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component whose look a brand may need to change apart, such as a card's fill, declares a *component token* for it in its own file, under `tokens`. Each token has a name, a type and a default, and lies at `component.<library>.<component>.<name>`, such as `component.ui.card.fill` for a card in a library named `ui`. Its default aliases a role the component's library may name, and holds until a brand gives the token a value. Among components and what a piece writes, only the component that declares a token reads it, by that full path, in as many of its parts as need it. Content never points a part at a token, and a piece's own component declares none, since no brand could reach it. A brand gives a token a value only where it names the token's library, as it does for the library's own roles. A stable component's tokens are part of what its library promises, and a release compares them. This completes the records that make the token without saying where it is declared or who reads it.

## Context

The record of brands and notations makes the *component token*: a role one component declares for one of its parts, such as a control's fill, so a brand can style that part apart from a shared role. Component tokens lie under one group, `component`, then the component's library and name. Each has a default that aliases a role, never a value, so no brand has to give the token a value. A base may open one alone ([visual-communication:DEC-004-brands-and-notations] point 7).

The record of a library's role defaults decides what a library's own role's default may alias, and that a component token's default may alias such a role, "as it aliases any role". It decides that a brand reaches a library's own roles, and the component tokens of its components, only where it names the library, and what a brand exports of each ([visual-communication:DEC-008-library-role-defaults] points 3 to 5). A library's `roles.yaml` holds no component token (DEC-008, Implications).

The Task that builds component tokens met choices that neither record makes ([project-kit#2966](https://github.com/aleskalfas/project-kit/issues/2966)):
- where a component declares a token, and what follows the component's name in its path
- how a part reads a token, and what else may read one
- a token's type, and what its default may alias
- whether a piece's own component declares tokens
- what a release's comparison counts when a component library's tokens change
- whether a brand's token under `component.<library>` gives that library's tokens values, as a token under the library's own name gives its roles values
- whether a contrast pair may name a component token

Until validation accepts files at an older format number, the format grows only by additions that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3). A brand may hold components, its own parts with their component tokens among them (DEC-004 point 6), but a brand's check and its release do not judge them yet ([project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573)). So this record decides how every component declares and reads its tokens, a brand's included, and leaves to that work what gives a brand's own components' tokens their values.

## Decision

**A component declares each token in its own file, by one name below its own group, with a declared type and a default that aliases a role its library may name. Among components and what a piece writes, only that component reads the token, by its full path. A brand's tokens under `component.<library>` are judged as its tokens under the library's name, and a release compares a stable component's tokens under the component's promise.**

### 1. A component declares its tokens in its own file

- **Under `tokens`,** a key of the component's file. It maps each token's name to its declaration, `{type, default}`, as a library's `roles.yaml` maps a role's path to its declaration.
- **Declared by its name, read by its path.** The declaration lies inside the component, so its file gives the token's group, and the key is the name alone. Everything that reads the token spells its full path (point 3).
- **Beside the parts that read it.** A reader finds every token a component offers a brand in the component's file. A release compares them with the rest of the component (point 6).
- **An addition to the format.** The key is optional, and a component that declares no token reads as before (DEC-003 point 3).

### 2. A token's path is its component's group and one name

- **`component.<library>.<component>.<name>`.** The component chooses the name: one segment, of the shape DEC-004 point 4 gives every name that enters a token path.
- **No library takes the name `component`,** so no library's own roles, which lie under its name, meet a token's path. It joins the names of the top groups of the shared roles, which DEC-004 point 7 keeps from every library.
- **No part's name in the path.** A part stays private unless the component exposes it, so its library may rename it freely ([visual-communication:DEC-005-engine-and-plugins] point 3). A token's path is public, since a brand gives it a value and exports it (DEC-004 point 5). So renaming a part renames no token.
- **A token names what it styles, not the part that reads it.** Several of the component's parts may read one token, so a brand restyles them as one.
- **What a base opens.** A base opens a token, or a group of tokens by whole segments of its path, as DEC-004 point 6 has it for any role, whether or not it gives the token a value, as DEC-008 point 4 has it for a library's role. A group opens only the tokens of the libraries the base names (DEC-008 point 4).

### 3. Only the declaring component reads a token

- **Read as any role is read, by its full path.** A paint, a text's style and a formula name it as they name any role. No short form stands for it. So paints, styles and formulas gain no grammar, and the component spells the path that a brand writes and the exports show.
- **Anywhere in the component's own file** that a role may be read.
- **No other component reads it.** One component that read another's token would let a brand's value for the first restyle the second, out of sight of whoever wrote the value.
- **A brand's drawing of a top's layout** is a component of the brand ([visual-communication:DEC-009-layout-defaults] point 2), so it reads none of the top's tokens. It is written in the brand's own values.
- **Nothing a piece writes names one.** Content's override points a part at another role, never at a value ([visual-communication:DEC-001-visual-communication-discipline] point 6), and never at a component token, for the same reason: the token is one component's. Nor does what a piece writes for a program run while preparing, such as a producer's inputs, name one ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2).
- **Outside components and pieces, nothing changes.** A brand that names the library may alias a token (DEC-008 point 4). Written code reads the document of resolved values, which holds every token of the libraries locked with the brand (DEC-005 point 7).
- **A token aliases one role.** A part painted from its instance's colour family takes its role from the concept or the state (DEC-001 point 6), so no token stands for it.
- **A token the component's file reads nowhere** breaks nothing, and a brand's value for it changes nothing. In an experimental component it asks the component's owner for attention, since the owner may remove it in any release. In a stable or deprecated component it states a fact, since removing it waits for the library's next major (point 6).

### 4. A token has a declared type and a default

- **A declared type:** any type a role takes but `picture`, since only the foundations declare a picture role ([visual-communication:DEC-025-picture-files] point 4). A declared type stays known where the role its default aliases cannot be read. So a version checked alone types the token with no brand behind it, and a release sees the type change (point 6).
- **A default, always,** as DEC-004 point 7 has it, since no brand has to give a token a value.
- **What the default may alias** is what a library's own role's default may alias (DEC-008 point 3): an own role of the component's library, or a role of a library that library builds on, the shared roles included. It is of the token's type.
- **Never a value, and never a component token,** the component's own included. So defaults run one way, from a part to a library's role and on to a shared role, as DEC-008 point 3 runs them for a library's roles. Parts that must change together read one token (point 2).
- **Resolved as a library's own role is** (DEC-008 point 1). So a brand's value wins where its sources cover the token. Elsewhere the default holds, and takes the brand's value for the role it aliases.
- **Where its chain ends.** As for a library's own role (DEC-008 point 3), a token draws under every brand only where its default's chain ends at a shared role. Each token of the starter's components ends at one, as every role of the starter does (DEC-008 point 2).
- **A role a token's default aliases is read through a default** by the token's component, as DEC-008 point 7 counts an own role a component reads. So an own role that a stable component's token aliases takes that component's promise.

### 5. A piece's own component declares no token

- **No brand could reach it.** Its token would lie under the word by which `use` names the piece itself, which no library takes ([visual-communication:DEC-002-files-and-validation] point 4). So no brand names it (DEC-008 point 4), and the token would hold its default under every brand.
- **A component declares a token only where a brand needs to differ** (DEC-004 point 7), which a local component never meets. Where a component lies already decides what a brand reaches, as a local top always draws itself (DEC-009 point 3).

### 6. A release compares a stable component's tokens under its promise

A token promises what the component that declares it promises (DEC-003 point 7). So a release compares only the tokens of a component that the earlier version marks stable or deprecated. An experimental component's tokens may change in any release. For a compared component:
- **Breaking:** a token removed, or of another type, since a brand that gives it a value breaks (DEC-003 point 6). So is a token whose default's chain no longer ends at a shared role, where it did. The chain is part of what a token declares, as it is for a library's own role (DEC-008 point 7).
- **An addition:** a new token, whatever its chain ends at. A token always has a default, so a new one never asks a brand for a value, unlike a new own role with no default. A new own role along its chain is compared as DEC-008 point 7 has it, since the token's component reads it through a default (point 4).
- **Neither:** any other change of a token, such as a default pointed at another role, or a part that starts or stops reading a token. Each changes only how a part looks (DEC-003 point 6).

### 7. How a brand's tokens under `component.<library>` are judged

A brand reaches a library's own roles, and the component tokens of its components, only where it names the library (DEC-008 point 4). What that record says of a brand's token under a library's name, a brand's token under `component.<library>` takes too:
- **Where the brand names the library,** each token it holds under `component.<library>` gives a token of the library's components a value of its type. A token there that names no token the library's components declare, or is of another type, gives nothing, and is a finding.
- **Where it names none,** a token there gives the library nothing, and stays private, as a brand's other tokens do (DEC-004 point 5). Where a piece's lock holds the library with the brand, it asks the brand's owner for attention.
- **Not under its own name.** A brand's token under `component.<its own name>` lies where its own components' tokens lie. This point leaves it private and with no finding, for the change that builds a brand's own components to decide what gives those tokens values (#2573).
- **What still holds.** No schema refuses a file it accepted. Only the check's judgement of a brand's tokens changes, as it did for a token under a library's own name (DEC-008 point 8).

### 8. No contrast pair names a component token

- **A library pairs its own roles** (DEC-004 point 8), and none of its pairs names a component token. At its library's defaults, a pair rests on a pair the foundations declare, each own role replaced by the role its default aliases (DEC-008 point 6). A token is no own role (DEC-008 point 1), so that step would not reach it.
- **What guards a token's colour.** Drawn text is measured against the fill under it in every combination a piece is drawn in (DEC-004 point 8). A token's colour that is no text's ground, such as an edge's, meets no check of contrast.

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides (DEC-002 point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.
- **Where each lies.** A finding on a component's tokens lies in the component's version, or in the piece that holds a local component. A finding on an override, or on what a piece writes for a program run while preparing, lies in that piece. A brand's tokens under `component.<library>` take the findings DEC-008 point 9 gives a brand's tokens under a library's name, at the places it gives them (point 7).
- **Fails validation:**
  - a token declared in a piece's own component
  - a token of the type `picture`, one with no default, or one whose name is not of the shape point 2 gives
  - a default that is no alias, or that aliases a component token, a role of another type, or a role of a library the component's library does not build on; or a default that leads nowhere
  - a component that reads a component token it does not declare
  - an override, or an input a piece writes for a program run while preparing, that names a component token
  - a pair that names a component token
  - a library named `component` (point 2)
  - at a lock, a part that reads a token with no value under the brand, where the brand does not name the library (DEC-008 point 9)
- **Asks for attention, never failing:** a token that an experimental component's file reads nowhere, naming the component's owner.
- **Stated as a fact:**
  - a token that a stable or deprecated component's file reads nowhere
  - a token whose default's chain does not end at a shared role, so that only a brand that gives a value along it draws what reads it

## Rationale

**Why the component's file, under `tokens`.** A library's `roles.yaml` holds no component token (DEC-008, Implications), and a component's promise is compared component by component (DEC-003 point 7). So the token lies with the component that promises it. A declaration under each part would scatter a component's public names among its private parts. A key named `roles` would mix the token up with a library's own roles, which DEC-008 point 1 keeps apart. `tokens` names what the records call them.

**Why one name, and no part's.** A part is private unless exposed, and a library renames it freely. A token's path is public, and a brand writes it. A path that held the part's name would turn every rename of a private part into a breaking change of every brand that gives the token a value.

**Why the full path.** A role is already read by its token path everywhere a component names one, a library's own role included. A short form would add a grammar to paints, styles and formulas, and the component would spell the token otherwise than the brand and the exports do.

**Why only its own component, and nothing a piece writes.** A component token is the narrowest role, for one component's part (DEC-004 point 7). Read by another component, pointed at by content's override in another component's part, or handed to a producer, a brand's value meant for one component would restyle something else. Its author would not see it, and the release could no longer compare the token under one component's promise. A brand's drawing of a top's layout is another component, written in the brand's own values, so it needs none of the top's tokens. Written code is another matter: a brand exports the tokens it gives values, and a runtime that styles its own copy of a component reads them as the brand promises them (DEC-004 point 5).

**Why an unread token never fails.** No invariant is broken, and a brand's value for it is only wasted. An experimental component can drop the token at once, so its owner is asked to. A stable component that stops reading a token must keep declaring it until a major release. That is a lawful state with nothing to do yet, as a published piece's lock that lies behind is (DEC-003 point 9), so it states a fact.

**Why a declared type.** A token's type is part of its promise, as a role's is. Taken from the role its default aliases, it would change whenever the default moved, and a release could not tell a change of type from a change of look.

**Why never a component token as a default.** A default that followed another component's token would tie two components' promises together. One that followed a token of its own component would start a second chain within the component. Reading one token in several parts already lets parts change together.

**Why no token in a local component.** No brand names the piece, so no brand could give the token a value. It would only rename the role it aliases, and break the rule that a component declares a token where a brand needs to differ. A local component stays the same kind of data as a library's, and only this key, which serves brands alone, is refused there.

**Why the release compares tokens.** A token is a name a brand writes (DEC-004 point 5). Uncompared, a stable component's minor release could remove one. Every brand that gives it a value would then fail when checked with the new version, with no major release to warn it. A removed role already breaks (DEC-003 point 6), and a component token is a role. A new token adds a name no brand wrote, and asks no brand for a value. A part pointed at it changes only that part's look, as a part pointed at another role does.

**Why `component.<library>` is judged as the library's name.** The brand's owner writes those tokens to give the library's tokens values. A misspelt one would otherwise stay private, and give nothing without a word. Judged with the brand alone, the finding lies where the brand's owner looks (DEC-008, Rationale).

**Why no pairs of tokens.** A pair of a component's tokens would add a declaration and a check at each brand, held at its defaults as a library's pairs are. Drawn text, the case that most often fails, is already measured in every combination a piece is drawn in. The cost falls on marks that are no text, such as an edge, until a component's tokens need pairs of their own.

### Alternatives considered

- **Tokens in the library's `roles.yaml`.** Rejected. That file holds none, and the promise would lie apart from the component that keeps it.
- **Tokens declared under each part, or under a key named `roles`.** Rejected, for the reasons above.
- **The part's name in the path, or a path of any depth.** Rejected. A private part's rename would break brands, and a deeper path adds nothing that a hyphenated name lacks.
- **A short form relative to the component, such as `~fill`.** Rejected. It adds a grammar in three places.
- **Any component, content's override, or a producer's inputs reading any component token.** Rejected, for the reasons above.
- **A brand's drawing of a top's layout reading the top's tokens.** Rejected. A copy of the top's drawing would carry the top's token names into the brand, and a brand's drawing restyles nothing through them that the brand's own values cannot.
- **A token read by one entry of `parts` alone.** Rejected. A brand would give two values to what it sees as one, and they could drift apart.
- **An unread token that fails.** Rejected. It would fail a stable component that keeps a token until its next major.
- **A mark on a token that its component no longer reads,** as DTCG marks a deprecated token. Rejected for now. It adds a field to say what the component's file already shows.
- **A type taken from the role the default aliases.** Rejected, for the reason above.
- **A default that may alias a token of its own component.** Rejected. Several parts reading one token serve the same need with one chain.
- **Tokens in a local component, always at their defaults.** Rejected. They would hold a default no brand can replace.
- **A component library's tokens left out of the release's comparison.** Rejected. A stable component's release could break every brand that gives a token a value.
- **A new token whose chain ends at no shared role counted as breaking.** Rejected. It asks nothing new of a brand that names the library, which already gives the role at the end of the chain a value. What it changes is how a part looks.
- **Pairs a component declares for its tokens.** Rejected for now, for the reason above.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-004 point 7, "A component token".** "A role one component declares for one of its parts" comes to say a role one component declares for what its parts draw. It adds that the component declares the token in its own file, at `component.<library>.<component>.<name>`, and that among components and what a piece writes only that component reads it. It adds that no library takes the name `component`. It takes the pointer "(refinement per DEC-035)".
  - **DEC-004 point 8, "Declared pairs".** "A library declares the pairs that involve its own roles" comes to add that none of them names a component token. It takes the pointer "(refinement per DEC-035)".
  - **DEC-008 point 3, "A component token's default".** "As it aliases any role" comes to say that it aliases what a library's own role's default may alias, and never a component token. It takes the pointer "(refinement per DEC-035)".
  - **DEC-008 point 4, "What it owes a library it names" and "Where it names none".** Each comes to add that a brand's token under `component.<library>` is judged as its token under that library's name, but for a brand's token under `component.<its own name>`. Each takes the pointer "(refinement per DEC-035)".
  - **DEC-008 point 9,** the failing finding of a brand's token under the name of a library it names, and the attention for one under the name of a library a piece locks with it. Each comes to cover a brand's token under `component.<library>` too, judged as the edit to DEC-008 point 4 judges it. Each takes the pointer "(refinement per DEC-035)".
  - **DEC-001 point 4, "A library component".** "Both are the same kind of data" comes to add that a local component declares no component token. It takes the pointer "(refinement per DEC-035)".
  - **DEC-001 point 6, "Colour says what a thing is".** "Content may also point one part at another role, never at a value" comes to end "never at a value or a component token". It takes the pointer "(refinement per DEC-035)".
  - **DEC-006 point 2, "Roles in what is written for the picture".** "Name roles, never raw values" comes to end "never raw values or component tokens". It takes the pointer "(refinement per DEC-035)".
- **Read against this record, and left as they stand:**
  - DEC-002 point 4, since `override` still points a part at another role, one other than a component token.
  - DEC-003 points 6 and 7, since a removed role still breaks, and a stable component's tokens are compared as the rest of it is (point 6).
  - DEC-004 point 4, since a token's name takes the shape of every name in a path, and the code writers spell it as they spell any token path.
  - DEC-004 point 5, DEC-005 point 7 and DEC-008 point 5, since a brand exports the component tokens it, or its base, gives values, and the document of resolved values holds every token of the libraries locked with it, each promised as point 6 has it.
  - DEC-004 point 6, since a base opens a token alone or by a group of whole segments, and a brand adds parts of its own with their component tokens, which point 1 declares as any component's.
  - DEC-008 point 2, since every role of the starter ends at a shared role, the tokens of its components included.
  - DEC-008 point 6, since a library's pairs at their defaults are judged as before.
  - DEC-008 point 7, since an own role a stable component reads through its token's default takes that component's promise (point 4).
  - DEC-009 point 2, since a brand's drawing is a component of the brand, which point 3 holds to its own tokens.
  - DEC-025 point 4, since only the foundations declare a picture role.
- **The Task that builds component tokens** ([project-kit#2966](https://github.com/aleskalfas/project-kit/issues/2966)) builds this record, in this record's change once it is accepted. The component's schema gains `tokens`. The capability reads and resolves tokens, a brand's values for them, its exports and the document of values. The release's comparison reads a brand's exported tokens, as DEC-004 point 5 has it, and a stable component's tokens, as point 6 has it. The check reports point 9's findings.
- **Edits to the capability's pages,** made in that change once this record is accepted, each anchored to it:
  - `components.md`, A component's file: the `tokens` key, a token's declaration, and the parts that read one, with a card's token as the example.
  - `components.md`, Values, states and colour: an `override` never names a component token.
  - `components.md`, Formulas, References and Errors: a formula reads its component's own token by its full path, and no other.
  - `files.md`, `roles.yaml`: a component token's default lies below every brand's value, as a library's own role's does.
  - `files.md`, A library's roles: where a component's token lies, and how a brand's token under `component.<library>` is judged.
  - `files.md`, Open roles: a base opens a token, or a group of tokens, whether or not it gives the token a value.
  - `files.md`, Content files: an `override` never names a component token.
  - `files.md`, What a release compares: a stable component's tokens and a brand's exported component tokens, in place of the line that they are not compared yet.
  - `outputs.md`, Produced pictures, Declaring a produced output: a producer's input never names a component token.
  - `checks.md`, Brands, tokens and contrast: point 9's findings on a component's tokens and their defaults, and on a brand's token under `component.<library>`, and the `open-unknown` row for a token a base opens.
  - `checks.md`, Scenes: a part that reads a token its component does not declare, or one with no value under the brand, and an `override` that names a component token.
  - `checks.md`, Produced pictures: a producer's input that names a component token.
- **Left to the change that builds a brand's own components** ([project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573)): what gives the tokens of a brand's own components their values, and how the check judges a brand's tokens under its own name.
- **Revisit this record** if a component needs one of its tokens to follow another, its tokens need contrast pairs of their own, or a brand's drawing needs a top's tokens.
