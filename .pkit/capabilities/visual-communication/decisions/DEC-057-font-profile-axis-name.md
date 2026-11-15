---
id: DEC-057
title: The name `font-profile` is kept for the shared axis of font profiles
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand gives each group of renderers its fonts, such as a whiteboard service that draws only fonts of its own, as the modes of one shared axis. Once a brand may hold axes of its own, any new shared axis could meet one of them by its name, so every new shared axis breaks. The capability keeps the name of the axis of fonts, `font-profile`, from the release that lets a brand hold axes of its own: no brand's own axis may take it, so the foundations' axis of that name is an addition when it comes. Written code does not carry the axis, and stays drawn in the brand's own fonts.

## Context

The record of brands makes a brand's font profiles the modes of one shared size axis. A *font profile* is the set of fonts a brand gives a group of renderers, and the default profile measures and draws the brand's own font files ([visual-communication:DEC-004-brands-and-notations] points 2 and 9). A renderer names the profile it draws in ([visual-communication:DEC-005-engine-and-plugins] point 10). No version of the foundations declares the axis. Its modes, and how a brand gives a profile, wait for a record of their own, which the Feature of drawing for a whiteboard service without signing in plans ([project-kit#2569](https://github.com/aleskalfas/project-kit/issues/2569)).

A brand that builds on no other may hold axes of its own from the capability's next release ([project-kit#2983](https://github.com/aleskalfas/project-kit/issues/2983)). Once it can, a new shared axis breaks the foundations, since its name may meet an axis a brand holds of its own, and that brand then fails (DEC-004 point 5). So the axis of font profiles, declared after that release, would need a major of the foundations, and every library built on them would follow it.

The capability already keeps names where a later name could meet them. No library takes `component`, the group of component tokens (DEC-004 point 7). No axis takes a name the engine holds, such as `width` ([visual-communication:DEC-021-size-and-shape] point 3).

## Decision

**The capability keeps the name `font-profile` for the shared axis of font profiles. No brand's own axis takes it, from the first release that lets a brand hold axes of its own. So the release's comparison reads the foundations' new axis of that name as an addition. Written code does not carry that axis.**

### 1. The shared axis of font profiles is named `font-profile`

- **The name.** The axis whose modes are a brand's font profiles takes the name `font-profile` when the foundations declare it.
- **Only the name is decided here.** The axis's kind, its modes and its default, and how a brand gives a profile, are the record of font profiles' to decide.
- **Under another name,** the axis is a new shared axis like any other, which breaks (DEC-004 point 5).

### 2. No brand's own axis takes the name

- **Refused.** An axis of a brand's own named `font-profile` fails validation, whichever version of the foundations the brand is checked with, at the severity the record of files and validation sets ([visual-communication:DEC-002-files-and-validation] point 7).
- **From the first release that reads a brand's own axes.** So no brand ever holds an axis of that name. Keeping a name in a later release would refuse a brand the format accepted, which the format does not do while it changes only by additions ([visual-communication:DEC-003-change-over-time] point 3). So after that release, a new shared axis by a name not kept waits for a major of the foundations.
- **A brand built on another** adds no axis by any name (DEC-004 point 6), so the kept name changes nothing for it.

### 3. The foundations' axis of that name is an addition

- **Read as an addition.** The release's comparison reads a new shared axis named `font-profile` as an addition, where a new shared axis by any other name breaks (DEC-004 point 5). No brand's own axis can hold the name, which is the one reason a new shared axis breaks.
- **Once declared, compared as every shared axis is.** Removed, or of another kind or another default, it breaks, and a new mode of it is an addition (DEC-004 point 5).

### 4. Written code does not carry the axis

- **Written in the default profile.** Each code writer writes every combination in the default profile, from the brand's own font files, and no key it writes names a mode of the axis. So the JSON writer's document gains none of its keys, though it gains those of a brand's other size axes, and the CSS writer reports no loss for it, though it reports each token another size changes (DEC-021 point 8).
- **So a font profile changes no written code.** A profile a brand gives, changes or ceases to give leaves every name in code as it was.
- **Carrying it later is an addition.** The JSON writer's document may gain keys and keep its form (DEC-021 point 8). Carried and then dropped, the axis would break code outside the capability, which no lock protects (DEC-004 point 5).

## Rationale

**Why keep a name.** Each other way out costs more (Alternatives considered). A kept name costs a brand one name for its own axis. In return the axis of font profiles lands as an addition, as the size axis `device` did while no brand could hold an axis of its own (DEC-021 point 9).

**Why `font-profile`.** It is what the record of brands already calls the thing. `profile` alone is how the capability speaks of a picture's colour profile ([visual-communication:DEC-025-picture-files] point 5), and one word for two things would mislead every reader, as the record of brands says of an axis for an audience (DEC-004 point 2). A brand's own axis named `profile` stays allowed.

**Why in that release.** Before a brand may hold an axis of its own, no brand holds one by the name, so keeping it refuses nothing. After that release, keeping it would refuse brands the format accepted.

**Why written code does not carry it.** A font profile serves a medium that draws in fonts of its own, such as a whiteboard service (DEC-004 point 9). Written code serves a live view, such as a web page or a game's runtime, which draws in the brand's own fonts, as every renderer that can draw them does (DEC-005 point 10). A key of profiles in written code would name values none of its readers draws, and turn each profile into a name that code outside the capability may come to rely on. Leaving the axis out costs nothing, and carrying it later breaks nothing, while the reverse breaks.

### Alternatives considered

- **A major release of the foundations when the axis comes.** Rejected. Every brand and component library built on them would move to the new major, and every lock with them, for an axis whose name could be kept.
- **The capability's release held until the axis lands.** Rejected. A brand's own axes, and every other change of that release, would wait for a record not yet drafted, and for its build.
- **The axis declared now.** Rejected. Its modes are not decided, and an axis with one mode is not declared (DEC-004 point 2).
- **A new shared axis that breaks only where a brand holds its name.** Rejected. The comparison reads two versions of the foundations, and the brands built on them are released by their own owners, out of its sight.
- **A mark that sets every brand's own axis apart,** such as a word that each of their names starts with. It would make every later shared axis an addition. Rejected. A name holds no group, so the mark would have to be kept out of every shared axis's name too, and it would lengthen each key and each name in code that names such an axis. One shared axis is foreseen, so one name is kept.
- **The name `profile`.** Rejected, for the reason above.
- **Written code that carries the axis,** as it carries a brand's other size axes. Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). Each refines its record in place.
  - **DEC-004 point 2, "The foundations name the shared axes"** comes to say that no axis a brand adds of its own takes the name `font-profile`.
  - **DEC-004 point 2, "Fonts for a group of renderers are one size axis"** comes to name the shared axis of font profiles `font-profile`.
  - **DEC-004 point 5, "Breaking changes"** comes to leave the shared axis `font-profile` out of the new shared axes that break, and **"Not breaking"** comes to add it, since no brand's own axis takes its name.
  - **DEC-004 point 11, "Fails validation"** comes to add an axis of a brand's own named `font-profile`.
  - **DEC-004's Rationale, "Why a key leaves defaults out"** comes to say that a new shared axis waits for a major unless its name was kept for it, as `font-profile` is.
  - **DEC-021 point 8, "Written code"** comes to add that no code writer carries the axis of font profiles, so written code is drawn in the default profile and its keys name none of the axis's modes.
- **Read against this record, and left as they stand:**
  - DEC-004 point 3, since a key leaves a default mode out, so the axis changes no key that existed.
  - DEC-004 point 6, since a brand built on another adds no axis by any name.
  - DEC-005 points 6 and 10, since a renderer still names its profile, and a piece names none.
  - DEC-025 point 5, since a picture's colour profile keeps its word.
- **[project-kit#3274](https://github.com/aleskalfas/project-kit/issues/3274) builds points 2 and 3,** and lands before the first release that lets a brand hold axes of its own. The check refuses the name with the finding it gives an axis of a brand's own that takes a shared axis's name, and the comparison reads the axis as an addition. The capability's pages of checks and of files say so.
- **The Task that declares the axis builds point 4,** since no code writer meets the axis before it.
- **Left open, to the record of font profiles:** the axis's kind, modes and default, how a brand gives a profile, and whether a brand that ceases to give one breaks, since no written code reads it.
- **Revisit this record** if the record of font profiles makes them no shared axis. Giving the name back then refuses nothing.
