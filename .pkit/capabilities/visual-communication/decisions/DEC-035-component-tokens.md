---
id: DEC-035
title: A component declares its tokens in its own file, and no other component or piece reads them
status: accepted
date: 2026-11-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component whose look a brand may need to change apart declares a *component token* in its own file, with a type and a default that aliases a role. For example, a card in a library named `ui` declares the token `fill`, defaulting to the shared role `surface`, and paints its box with `component.ui.card.fill`. A brand that names `ui` may give the token a value, and under a brand that gives it none the box takes the brand's `surface`. No other component, and nothing a piece writes, reads the token.

## Context

The record of brands and notations makes the *component token*: a role one component declares for what its parts draw, such as a control's fill, so a brand can style it apart from a shared role. Component tokens lie under one group, `component`, then the component's library and name. Each has a default that aliases a role, never a value, so no brand has to give the token a value ([visual-communication:DEC-004-brands-and-notations] point 7). The record of a library's role defaults decides what a library's own role's default may alias, that a brand reaches a library's own roles and the component tokens of its components only where it names the library, and what a brand exports of each ([visual-communication:DEC-008-library-role-defaults] points 3 to 5).

The Task that builds component tokens ([project-kit#2966](https://github.com/aleskalfas/project-kit/issues/2966)) met choices that neither record makes: where a component declares a token, and what follows the component's name in its path; what may read a token, and how; a token's type, and what its default may alias; whether a piece's own component declares tokens; what a release compares; how a brand's tokens under `component.<library>` are judged; and whether a contrast pair may name a component token. A brand may hold components of its own, with their component tokens (DEC-004 point 6), but a brand's check and its release do not judge them yet ([project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573)).

## Decision

**A component declares its tokens in its own file, and no other component or piece reads them.**

### 1. A component declares its tokens in its own file

- **Under `tokens`,** an optional key of the component's file. It maps each token's name to its declaration, `{type, default}`, as a library's `roles.yaml` maps a role's path to its declaration. A component that declares no token reads as before.
- **Keyed by the token's name alone.** The component's file gives the rest of its path (point 2).
- **A brand's own components** declare and read their tokens by points 1 to 4, as a library's components do.

### 2. A token's path is its component's group and one name

- **`component.<library>.<component>.<name>`.** The component chooses the name: one segment, of the shape DEC-004 point 4 gives every name that enters a token path. No part's name enters the path.
- **A token names what it styles, not a part.** Several of the component's parts may read one token, and parts that must change together read one.
- **No library takes the name `component`,** as none takes the name of a top group of the shared roles (DEC-004 point 7).
- **What a base opens.** A base opens a token, or a group of tokens by whole segments of its path, as DEC-004 point 6 has it for any role, whether or not it gives the token a value, as DEC-008 point 4 has it for a library's role. A group opens only the tokens of the libraries the base names (DEC-008 point 4).

### 3. Only the declaring component reads a token

- **By its full path, as any role is read,** anywhere in the component's own file that a role may be read, such as a paint, a text's style or a formula. No short form stands for it.
- **No other component reads it.**
- **A brand's drawing of a top's layout** is a component of the brand ([visual-communication:DEC-009-layout-defaults] point 2), so it reads none of the top's tokens, and is written in the brand's own values.
- **Nothing a piece writes names one:** neither content's override, which points a part at another role ([visual-communication:DEC-001-visual-communication-discipline] point 6), nor what a piece writes for a program run while preparing, such as a producer's inputs ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2).
- **No token stands for a part painted from its instance's colour family** (DEC-001 point 6).
- **Outside components and pieces, nothing changes.** A brand that names the library may alias a token (DEC-008 point 4). Written code reads the document of resolved values, which holds every token of the libraries locked with the brand ([visual-communication:DEC-005-engine-and-plugins] point 7).

### 4. A token has a declared type and a default

- **A declared type:** any type a role takes but `picture` ([visual-communication:DEC-025-picture-files] point 4).
- **A default, always** (DEC-004 point 7), aliasing a role of the token's type that a library's own role's default may alias (DEC-008 point 3): an own role of the component's library, or a role of a library that library builds on, the shared roles included.
- **Never a value, and never a component token,** the component's own included.
- **Resolved as a library's own role is** (DEC-008 point 1). A brand's value wins where its sources cover the token. Elsewhere the default holds, and takes the brand's value for the role it aliases.
- **Where its chain ends.** A token draws under every brand only where its default's chain ends at a shared role, as a library's own role does (DEC-008 point 3). Each token of the starter's components ends at one, as every role of the starter does (DEC-008 point 2).
- **A role a token's default aliases is read through a default** by the token's component, as DEC-008 point 7 counts an own role a component reads. So an own role that a stable component's token aliases takes that component's promise.

### 5. A piece's own component declares no token

- **Only `tokens` is refused there,** of all that a component's file may hold.

### 6. A release compares a stable component's tokens under its promise

- **A token promises what its component promises** ([visual-communication:DEC-003-change-over-time] point 7). So a release compares only the tokens of a component that the earlier version marks stable or deprecated, and an experimental component's tokens may change in any release.
- **Breaking:** a token removed, or of another type, or whose default's chain no longer ends at a shared role, where it did.
- **An addition:** a new token, whatever its chain ends at. A new own role along its chain is compared as DEC-008 point 7 has it (point 4).
- **Neither:** any other change of a token, such as a default pointed at another role, or a part that starts or stops reading a token.

### 7. How a brand's tokens under `component.<library>` are judged

What DEC-008 point 4 says of a brand's token under a library's name, a brand's token under `component.<library>` takes too:
- **Where the brand names the library,** each token it holds there gives a token of the library's components a value of its type. One that names no token they declare, or is of another type, gives nothing, and is a finding.
- **Where it names none,** a token there gives the library nothing, and stays private, as a brand's other tokens do (DEC-004 point 5). Where a piece's lock holds the library with the brand, it asks the brand's owner for attention.
- **Not under its own name.** A brand's token under `component.<its own name>`, where its own components' tokens lie, stays private and with no finding. What gives its own components' tokens values, and how the check judges a brand's tokens under `component.<its own name>`, is left to the change that builds a brand's own components (#2573).
- **No schema refuses a file it accepted.** Only the check's judgement of a brand's tokens changes, as it did for a token under a library's own name (DEC-008 point 8).

### 8. No contrast pair names a component token

- **A library pairs its own roles** (DEC-004 point 8), and none of its pairs names a component token.

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.
- **Where each lies.** A finding on a component's tokens lies in the component's version, or in the piece that holds a local component. A finding on an override, or on what a piece writes for a program run while preparing, lies in that piece. A brand's tokens under `component.<library>` take the findings DEC-008 point 9 gives a brand's tokens under a library's name, at the places it gives them (point 7).
- **Fails validation:**
  - a token in a piece's own component
  - a token of the type `picture`, one with no default, or one whose name is not of the shape point 2 gives
  - a default that is no alias, or that aliases a component token, a role of another type, or a role of a library the component's library does not build on; or a default that leads nowhere
  - a library named `component`
  - a component that reads a component token it does not declare
  - an override, or an input a piece writes for a program run while preparing, that names a component token
  - a pair that names a component token
  - at a lock, a part that reads a token with no value under the brand, where the brand does not name the library (DEC-008 point 9)
- **Asks for attention, never failing:** a token that an experimental component's file reads nowhere, naming the component's owner.
- **Stated as a fact:** a token that a stable or deprecated component's file reads nowhere, and a token whose default's chain ends at no shared role (point 4).

## Rationale

**Point 1, the component's file.** A component's promise is compared component by component (DEC-003 point 7), so its tokens lie with it, and a reader finds every token a component offers a brand in its file. `tokens` names what the records call them. The key is optional because, until validation accepts files at an older format number, the format grows only by additions that every file written before still meets (DEC-003 point 3).

**Point 2, one name.** A part stays private unless the component exposes it, so its library renames it freely (DEC-005 point 3). A token's path is public, since a brand gives it a value and exports it (DEC-004 point 5). Reserving `component` keeps every library's own roles, which lie under its name, off a token's path.

**Point 3, the reader.** A component token is the narrowest role, for one component (DEC-004 point 7). The full path is how a component already reads every role, a library's own included, and how a brand and the exports spell the token, so paints, styles and formulas gain no grammar. A token aliases one role, while a part painted from its colour family takes a role that changes with the concept or the state. Written code is another matter: a brand exports the tokens it gives values, and a runtime that styles its own copy of a component reads them as the brand promises them (DEC-004 point 5).

**Point 4, type and default.** A token's type is part of its promise, as a role's is. Declared, it stays known where the role its default aliases cannot be read, so a version checked alone types the token with no brand behind it, and a release sees a change of type. Only the foundations declare a picture role. A default that followed another component's token would tie two components' promises together. With a component token refused as a default, defaults run one way, from a component to a library's role and on to a shared role, as DEC-008 point 3 runs them for a library's roles.

**Point 5, no token in a local component.** Its token would lie under the word by which `use` names the piece itself, which no library takes (DEC-002 point 4). So no brand names it (DEC-008 point 4), and it would hold its default under every brand. A component declares a token only where a brand needs to differ (DEC-004 point 7), which a local component never meets: where it lies already decides what a brand reaches, as a local top always draws itself (DEC-009 point 3). The key serves brands alone, and in all else a local component stays the same kind of data as a library's (DEC-001 point 4).

**Point 6, the release.** A token is a name a brand writes (DEC-004 point 5), and a component token is a role, whose removal already breaks (DEC-003 point 6). A brand that gives a token a value breaks too when the token changes type. The chain is part of what a token declares, as it is for a library's own role (DEC-008 point 7). A new token always has a default, so it asks no brand for a value, unlike a new own role with no default. Any other change alters only how a part looks (DEC-003 point 6).

**Point 7, judged as the library's name.** The brand's owner writes those tokens to give the library's tokens values. A misspelt one would otherwise stay private, and give nothing without a word. Judged with the brand alone, the finding lies where the brand's owner looks (DEC-008, Rationale).

**Point 8, no pairs.** At its library's defaults, a pair rests on a pair the foundations declare, each own role replaced by the role its default aliases (DEC-008 point 6). A token is no own role (DEC-008 point 1), so that step would not reach it. Drawn text, the case that most often fails, is still measured against the fill under it in every combination a piece is drawn in (DEC-004 point 8). The cost: a token's colour that is no text's ground, such as an edge's, meets no check of contrast.

**Point 9, an unread token.** It breaks no invariant, and a brand's value for it is only wasted. An experimental component can drop the token at once, so its owner is asked to. A stable component's unread token is a lawful state with nothing to do until its next major (point 6), as a published piece's lock that lies behind is (DEC-003 point 9), so it states a fact.

### Alternatives considered

- **Tokens in the library's `roles.yaml`:** DEC-008's Implications keep that file free of them, and the promise would lie apart from the component that keeps it.
- **Tokens declared under each part:** a component's public names would scatter among its private parts.
- **A key named `roles`:** it would mix the tokens up with a library's own roles, which DEC-008 point 1 keeps apart.
- **The part's name in the path:** renaming a private part would break every brand that gives the token a value.
- **A path of any depth:** it adds nothing that a hyphenated name lacks.
- **A short form relative to the component, such as `~fill`:** it adds a grammar in three places.
- **Any component, content's override, or a producer's inputs reading any component token:** a brand's value meant for one component would restyle something else out of its author's sight, and no release could compare the token under one component's promise.
- **A brand's drawing of a top's layout reading the top's tokens:** a copy of the top's drawing would carry the top's token names into the brand, and it restyles nothing through them that the brand's own values cannot.
- **A token read by one entry of `parts` alone:** a brand would give two values to what it sees as one, and they could drift apart.
- **An unread token that fails:** it would fail a stable component that keeps a token until its next major (point 6).
- **A mark on a token that its component no longer reads,** as DTCG marks a deprecated token, rejected for now: it adds a field to say what the component's file already shows.
- **A type taken from the role the default aliases:** it would change whenever the default moved, and a release could not tell a change of type from a change of look.
- **A default that may alias a token of its own component:** it starts a second chain within the component, where several parts reading one token serve the same need.
- **Tokens in a local component, always at their defaults:** each would only rename the role it aliases.
- **A component library's tokens left out of the release's comparison:** a stable component's minor release could remove one, and every brand that gives it a value would fail when checked with the new version, with no major release to warn it.
- **A new token whose chain ends at no shared role counted as breaking:** it asks nothing new of a brand that names the library, which already gives the role at the end of the chain a value, and changes only how a part looks.
- **Pairs a component declares for its tokens,** rejected for now: each brand would gain a declaration and a check, held at its defaults as a library's pairs are.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it with the pointer "(refinement per DEC-035)". Accepting this record accepts them (COR-066 point 5).
  - DEC-004 point 7, "A component token": "A role one component declares for one of its parts" comes to say "a role one component declares for what its parts draw", and the point comes to add that the component declares the token in its own file at `component.<library>.<component>.<name>`, that among components and what a piece writes only that component reads it, and that no library takes the name `component`.
  - DEC-004 point 8, "Declared pairs": "A library declares the pairs that involve its own roles" comes to add that none of them names a component token.
  - DEC-008 point 3, "A component token's default": "as it aliases any role" comes to say that it aliases what a library's own role's default may alias, and never a component token.
  - DEC-008 point 4, "What it owes a library it names" and "Where it names none": each comes to add that a brand's token under `component.<library>` is judged as its token under that library's name, but for one under `component.<its own name>`.
  - DEC-008 point 9: the failing finding on a brand's token under the name of a library it names, and the attention for one under the name of a library a piece locks with it, each come to cover a brand's token under `component.<library>`, judged as the edit to DEC-008 point 4 judges it.
  - DEC-001 point 4, "A library component": "Both are the same kind of data" comes to add that a local component declares no component token.
  - DEC-001 point 6, "Colour says what a thing is": "Content may also point one part at another role, never at a value" comes to end "never at a value or a component token".
  - DEC-006 point 2, "Roles in what is written for the picture": "Name roles, never raw values" comes to end "never raw values or component tokens".
- **Read against this record, and left as they stand:**
  - DEC-002 point 4: `override` still points a part at another role, one other than a component token.
  - DEC-003 points 6 and 7, which point 6 applies to a stable component's tokens.
  - DEC-004 point 4: a token's name has the shape of every name in a path, and the code writers spell it as any token path.
  - DEC-004 point 5, DEC-005 point 7 and DEC-008 point 5: a brand's exports and the document of resolved values hold component tokens as they stand, each promised as point 6 has it.
  - DEC-004 point 6: a base opens a token as point 2 has it, and a brand's own parts declare their tokens as point 1 has it.
  - DEC-008 point 2, which holds for the tokens of the starter's components too (point 4).
  - DEC-008 point 6: a library's pairs at their defaults are judged as before.
  - DEC-008 point 7, which point 4 applies to an own role a token's default aliases.
  - DEC-009 point 2, which point 3 applies to a brand's drawing.
  - DEC-025 point 4, which point 4 follows.
- **The Task that builds component tokens** ([project-kit#2966](https://github.com/aleskalfas/project-kit/issues/2966)) builds this record in this record's change once it is accepted, with the release's comparison of a brand's exported tokens that DEC-004 point 5 asks for.
- **Edits to the capability's pages,** made in that change once this record is accepted, each anchored to it:
  - `components.md`, A component's file: the `tokens` key and the parts that read a token (points 1 to 4), with a card's token as the example.
  - `components.md`, Values, states and colour: the override (point 3).
  - `components.md`, Formulas, References and Errors: a formula's reading of a token (point 3).
  - `files.md`, `roles.yaml`: where a token's default lies under a brand's values (point 4).
  - `files.md`, A library's roles: where a component's tokens lie (points 1 and 2), and how a brand's tokens under `component.<library>` are judged (point 7).
  - `files.md`, Open roles: what a base opens (point 2).
  - `files.md`, Content files: the override (point 3).
  - `files.md`, What a release compares: a stable component's tokens (point 6) and a brand's exported component tokens, in place of the line that they are not compared yet.
  - `outputs.md`, Produced pictures, Declaring a produced output: a producer's input (point 3).
  - `checks.md`, Brands, tokens and contrast: point 9's findings on a component's tokens and their defaults and on a brand's tokens under `component.<library>`, and the `open-unknown` row for a token a base opens.
  - `checks.md`, Scenes: point 9's findings on a part that reads a token and on an override.
  - `checks.md`, Produced pictures: point 9's finding on a producer's input.
- **[project-kit#2573](https://github.com/aleskalfas/project-kit/issues/2573)** decides what point 7 leaves to it.
- **Revisit this record** if a component needs one of its tokens to follow another, its tokens need contrast pairs of their own, or a brand's drawing needs a top's tokens.
