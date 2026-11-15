---
id: DEC-057
title: A brand's own axes carry the mark `own-`, so every new shared axis is an addition
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand may add axes of its own, such as a season, beside the shared axes the foundations declare, such as the colour scheme. Were the foundations to add a shared axis by a name that a brand already gives an axis of its own, that brand would fail, so every new shared axis would need a major release of the foundations. So the name of a brand's own axis starts with the mark `own-`, as `own-season` does, and no shared axis's name does. The two can never meet, and every new shared axis comes as an addition, the axis of font profiles, named `font-profile`, among them. The mark is required from the first release that lets a brand hold axes of its own, so it refuses no brand.

## Context

A brand that builds on no other may hold axes of its own, from the first release of the capability that carries them ([project-kit#2983](https://github.com/aleskalfas/project-kit/issues/2983)). The record of brands then counts a new shared axis of the foundations as a break, since its name may meet an axis a brand holds of its own, and that brand then fails ([visual-communication:DEC-004-brands-and-notations] point 5). So each new shared axis would need a major of the foundations. Moving to a new major of a base breaks ([visual-communication:DEC-003-change-over-time] point 6), so every brand and component library built on them would follow in a major of its own, and every lock with them.

The record of brands makes a brand's font profiles the modes of one shared axis (DEC-004 point 2), which the record of font profiles, drafted under [project-kit#3275](https://github.com/aleskalfas/project-kit/issues/3275), declares.

The capability keeps apart the names a library adds and the shared ones. A library's own roles lie under a group named after the library, and no library takes the name of a top group of the shared roles (DEC-004 point 7). An axis's name has no group to lie under: it is one segment of a key, beside its mode (DEC-004 point 3), and holds no path mark ([visual-communication:DEC-002-files-and-validation] point 4).

## Decision

**The name of a brand's own axis starts with the mark `own-`, and no shared axis's name does. So no brand's own axis can meet a shared axis by name, and the release's comparison reads every new shared axis of the foundations as an addition. The mark is required from the first release that lets a brand hold axes of its own. The shared axis of font profiles is named `font-profile`.**

### 1. A brand's own axis carries the mark

- **The mark.** A name's words are those its hyphens join (DEC-004 point 4). A name takes the mark `own-` where its first word is `own` and one word or more follow it, as `own-season` does. The name of each axis a brand adds of its own takes the mark.
- **Which axes.** An axis of a brand's own is a modifier of its Resolver document that gives the axis's kind in the capability's extension point (DEC-004 points 1 and 2). A modifier that gives no kind names an axis the brand varies, a shared one or its base's own, by that name.
- **Refused without it.** An axis of a brand's own whose name does not take the mark fails validation, at the severity the record of brands gives its findings (DEC-004 point 11). So does one named `own` alone.
- **From the first release that lets a brand hold axes of its own.** So no brand ever holds an axis of its own without the mark.
- **Carried wherever the axis is named.** The mark is part of the name, so a piece's modes, every key that holds the axis, such as `own-season.winter` in the names of exports and pictures, and written code all carry it. The CSS writer switches the axis's modes by the attribute `data-own-season`, as in `[data-own-season="winter"]`, and the JSON writer gives its values under keys such as `own-season.winter`. A custom property names a token path, never an axis, so none carries the mark. No code writer's spelling changes ([visual-communication:DEC-005-engine-and-plugins] point 8).
- **A brand built on another** still adds no axis (DEC-004 point 6). It varies its base's own axes by their names, the mark included.

### 2. No shared axis carries the mark

- **Kept out of the foundations.** No axis the foundations declare takes the mark, nor `own` alone. One that does fails validation, at the same severity.
- **Nor a name the engine holds.** No name a component reads after `:`, as it reads `:width`, starts with the word `own` ([visual-communication:DEC-021-size-and-shape] point 3). So a name the engine comes to hold meets no brand's own axis.
- **By whole words.** A first word such as `owner` is no mark, so a shared axis may take it.

### 3. Every new shared axis is an addition

- **Read as an addition.** The release's comparison reads a new shared axis of the foundations, with its default, as an addition, whatever its name. Its name can meet no brand's own axis (points 1 and 2), which is the one way a new shared axis breaks a brand (DEC-004 point 5).
- **Once declared, compared as every axis is.** Removed or renamed, or of another kind or another default, it breaks, and a new mode of it is an addition (DEC-004 point 5).

### 4. The shared axis of font profiles is named `font-profile`

- **The name.** The axis whose modes are a brand's font profiles takes the name `font-profile` when the foundations declare it, and comes then as an addition (point 3).
- **Only the name is decided here.** The axis's kind, its modes and its default, how a brand gives a profile, and which plugins are handed it, are the record of font profiles' to decide.

## Rationale

**Why a mark on a brand's own axes.** It settles the clash for every shared axis to come, not for one name. The foundations add a shared axis as an addition whenever one is needed, and no library built on them, and no lock, moves to a new major for it. It follows the rule the capability's roles follow: the shared names stay bare, and what a library adds of its own is set apart in its name, so nothing the foundations add later meets it (DEC-004 point 7). The cost falls on a brand's own axes alone: four characters in each key and each name in code that holds one, in that brand, in each brand built on it, and in the code they write. Keeping the mark out of the shared axes costs nothing, since the foundations have one author.

**Why `own-`.** It is the capability's own word for what a library adds apart from the shared ones: an axis of a brand's own and a library's own roles (DEC-004 points 2 and 7). So a reader of `own-season.winter` reads the axis as the brand's. It is one fixed word, so one rule keeps it out of every shared axis's name. It takes the name shape, so every code writer spells it as any other name, and a key's grammar stays. It stays the same when a brand is renamed, and in every brand built on it. A fixed word is enough because only a brand that builds on no other adds an axis of its own (DEC-004 point 6), so no two brands of one chain each add one. Its one cost: in a brand built on another, it marks an axis of the base's own, so it reads as "a brand's own, not shared", not as "this brand's".

**Why from the first release that lets a brand hold axes of its own, and why it can be undone.** Before that release, no brand holds such an axis, so the mark refuses nothing. Required later, it could not reach a brand released without it, which never changes (DEC-003 point 6), and whose axes' names are public, so that renaming one breaks (DEC-004 point 5). That brand's axis could still meet a new shared axis, and the comparison, which reads two versions of the foundations and sees no brand, could read none as an addition. So a mark required later could bind only the brands built on a new major of the foundations, which every library and lock would move to once. Required now, it costs nothing. And it can be undone: dropping a required mark later refuses no brand, and leaves each new shared axis to break again. Each alternative below that leaves a brand's own axes unmarked reaches a mark later only through that major.

**Why `font-profile`.** It is what the record of brands calls the thing. An axis's name enters every key and every name in code that holds the axis, and `profile` alone is how the capability speaks of a picture's colour profile ([visual-communication:DEC-025-picture-files] point 5). One word for two things would mislead every reader, as the record of brands says of an axis for an audience (DEC-004 point 2). With the mark, the name needs no keeping before any release: the axis is an addition whenever it comes.

### Alternatives considered

- **Only the name `font-profile` kept from brands' own axes,** so that one axis lands as an addition. Rejected. Each later shared axis would need a major of the foundations, until a major of them came to require a mark after all.
- **`font-profile` kept bare, and each later shared axis marked.** Rejected. It reverses how roles are kept apart, where the shared names stay bare and each library's own carry its name (DEC-004 point 7). And each later shared axis, which every brand, component and reader meets, would carry the longer name, where a mark on a brand's own axes falls only on the brands that hold them.
- **A major of the foundations for each new shared axis.** Rejected. Every brand and component library built on them, and every lock, would move to a new major for each.
- **A new shared axis that breaks only where a brand holds its name.** Rejected. The comparison reads two versions of the foundations, and the brands built on them are released by their own owners, out of its sight.
- **The brand's own name as the mark,** as in `platform-season`, as a library's own roles lie under its name. Rejected. Within one name it is joined by a hyphen, so a new shared axis may still start with a library's name: a shared `colour-vision` would meet the axis `vision` of a brand named `colour`, and the foundations cannot know every library's name. Kept apart as a role is, in a segment of its own, it would need a new grammar for keys and a new spelling from every code writer (DEC-004 points 3 and 4), and would lengthen each key by the brand's name. What it would buy, two brands of one chain kept apart, no brand needs while only a brand with no base adds an axis.
- **A mark outside the name shape,** such as a leading underscore. Rejected. Every name that enters a key takes one shape, so that every code writer can spell it (DEC-004 point 4), and a second shape would widen that rule for every writer to come.
- **Another fixed word.** Rejected, each for not being the capability's word for what a library adds of its own:
  - `brand-`, since `brand` already names a kind of library and a piece's field;
  - `local-`, since the capability calls a piece's own component a local component (DEC-002 point 4), and one word for two things misleads;
  - `extra-` or `added-`, which read truly in a brand built on another too, but part the axis from the capability's other own names;
  - `my-`, which reads as the reader's, and `x-`, the old mark of a private name, which says nothing to a designer.
- **The name `profile` for the axis of font profiles.** Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). Each refines its record in place.
  - **DEC-004 point 2, "The foundations name the shared axes"** comes to say that the name of each axis a brand adds of its own takes the mark `own-`, which no shared axis's name takes.
  - **DEC-004 point 5, "Breaking changes"** comes to drop a new shared axis from the foundations' breaking changes, and **"Not breaking"** comes to count a new shared axis with a default as no break whenever it comes, since its name can meet no brand's own axis.
  - **DEC-004 point 11, "Fails validation"** comes to add an axis of a brand's own whose name does not take the mark, and an axis of the foundations whose name does.
  - **DEC-004's Rationale, "Why a key leaves defaults out, names each axis, and sorts by name"** comes to say that a brand's own axis carries a mark no shared axis takes, so a new shared axis comes as an addition, where it says a new shared axis waits for a major release.
  - **DEC-021 point 3, "A marked name"** comes to add that no name the engine holds starts with the word `own`.
  - **DEC-021 point 9, "A new shared axis is an addition while no brand can hold an axis of its own"** comes to add that it stays one after, since a brand's own axis carries the mark.
  - **DEC-021's Implications, "Left open", "A brand's own axes"** comes to say that their names carry the mark, so a new shared axis stays an addition, where it says their change makes a new shared axis breaking again. Its sentence on a mode a brand adds to a shared size axis stays open.
- **Read against this record, and left as they stand:**
  - DEC-004 point 2, "Fonts for a group of renderers are one size axis", which names no axis, since the axis takes its name when the foundations declare it.
  - DEC-004 point 3, since the mark is part of an axis's name, so a key names the axis as before, and a new shared axis with a default changes no key.
  - DEC-004 point 4, since a name with the mark takes the name shape.
  - DEC-004 point 6, since a brand built on another still adds no axis, and varies its base's by their names.
  - DEC-005 point 8, since no code writer's spelling changes.
  - DEC-025 point 5, since a picture's colour profile keeps its word.
- **[project-kit#3274](https://github.com/aleskalfas/project-kit/issues/3274) builds points 1 to 3,** and lands before the first release that lets a brand hold axes of its own. Whoever maintains the capability holds that release until then, and every candidate cut from the default branch with it.
  - **The check.** The finding that refuses an axis of a brand's own by a shared axis's name comes to refuse one whose name does not take the mark, which leaves none that can take a shared axis's name. A finding refuses an axis of the foundations whose name takes it. The check keeps no name apart for the axis of font profiles.
  - **The release's comparison** reads every new shared axis as an addition, with no exception by name.
  - **The capability's pages** that describe a brand's axes, the names the capability keeps, the check's findings and what a release compares say so. The release's pending note on a brand's own axes, which says a new shared axis breaks, comes to say that a brand's own axis takes the mark and that a new shared axis breaks nothing.
  - **The tests** give each axis of a brand's own a name with the mark, and show an axis of a brand's own without it failing, an axis of the foundations with it failing, and a new shared axis read as an addition.
  - **No migration.** No release has carried a brand's own axis, so no project holds one to rename.
- **Should that release ship first,** the mark can bind only the brands built on a later major of the foundations (Rationale), and this record is revised to say so before it is accepted.
- **The record of font profiles,** drafted under [project-kit#3275](https://github.com/aleskalfas/project-kit/issues/3275), declares the axis this record names (point 4), and decides its kind, its modes and its default, how a brand gives a profile, and which plugins are handed it, written code among them.
- **Left open:** a mode a brand adds to a shared axis, which DEC-021's Implications leave open, would meet a later shared mode as an unmarked axis of a brand's own meets a shared axis. The change that allows such a mode decides whether it carries a mark too.
