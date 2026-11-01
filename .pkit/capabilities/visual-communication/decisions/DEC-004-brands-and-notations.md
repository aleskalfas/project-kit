---
id: DEC-004
title: A brand gives roles their values on axes of modes, and a notation gives concepts their roles
status: accepted
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand keeps its values, such as colours, fonts and sizes, as design tokens in the format design tools share. Its modes, such as light and dark or a high contrast, lie on separate axes, so no value is copied for each combination of them. A brand may build on one other brand, and change only what that base opens to it. The names a brand exports are public, since code outside the capability reads them, and one naming rule turns them into names in code. A notation says which colour roles, icons or shapes stand for the concepts of one subject, never which values.

## Context

The capability's founding record makes a brand the library that holds values, and a notation the library that holds meaning ([visual-communication:DEC-001-visual-communication-discipline] point 5). Components name roles, and only a brand gives a role a value. A name is read with its library. A brand may build on another brand, and changes only the values its base lists as open to change. A brand's values can leave the capability as code, which live views read ([visual-communication:DEC-001-visual-communication-discipline] point 9). This record decides the formats of brands and notations.

Design systems keep such values as *design tokens*: named values, each with a type, which may alias one another. The W3C Design Tokens Community Group (DTCG) published the first stable version of its format, 2025.10. Its *Resolver* module describes modes as data. A Resolver document holds token files as *sets*, each way the values vary as a *modifier* with its *contexts* and a default, and an order that says which source wins. Design tools import and export the format.

The capability's design work ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)) found what the formats must hold:
- **Concepts were coloured by hand.** Two talks by one author gave one project's concepts the same colours, as raw values of one company's palette, in every slide that showed them.
- **A prototype kept a file for each theme and mode.** Every combination copied its values, and nothing said which colours must stay readable together.
- **Light and dark are not enough.** A platform for online board games varies its look by colour scheme, contrast, device and audience. Each game restyles the platform's controls within the platform's limits, and the game's own owner releases it. The games' runtimes need the values as code. Nothing of the platform is built. It is the case the format is tested against, approved with the capability's plan ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)).

## Decision

**A brand keeps its values as design tokens and its modes as one Resolver document, in the DTCG format. Its modes lie on axes that vary apart. An axis that changes only colours and pictures moves nothing on the page, and one that changes sizes needs scenes of its own. A brand may build on one other brand, and gives values only to the roles that base declares open. The names a brand exports are public, and one naming rule turns them into names in code. A notation maps each concept, read with the notation's name, to roles, never to values.**

### 1. A brand's values are design tokens in the DTCG format

- **Each role is a token,** at the path its name gives, of the type its declaration gives.
- **A value may alias another token.** A chain of aliases ends in a value, never in a loop.
- **What the format cannot say goes in its own extension point,** under one name the capability keeps for itself. Examples are a picture given as a value, how a font is measured, and whether an axis changes values or sizes. So a brand's files stay valid DTCG, and other tools read them.
- **The modes are one Resolver document.** It holds the brand's token files as sets, each axis as a modifier, each mode as one of its contexts, a default for each axis, and the order in which sources win.
- **The brand's library file** names the version of the DTCG format its tokens follow, 2025.10 first, and holds its open roles (point 6). The engine keeps reading every DTCG version a released brand may name, since a library copy is never rewritten.
- **A brand's own form,** its layouts and the parts no shared component has, is made of components. They take the format every component has, and are read with the brand's name (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 4).

### 2. Modes lie on axes, and each axis changes values or sizes

An *axis* is one way a brand's values vary apart from the others, such as the colour scheme, the contrast or the device. A *mode* is one value on one axis, such as dark on the colour scheme. A *combination* takes one mode on each axis.
- **The foundations name the shared axes** and their common modes, as they name the shared roles. So a piece that names a mode keeps it when its brand is switched. A brand has the shared axes it needs, and may add axes of its own. An axis with one mode is not declared.
- **A value axis** changes only values that move nothing, such as colours and pictures. The capability's schema for a brand names those kinds of value, member by member for a token made of several. Every mode of a value axis is drawn from one scene, so a page can switch between them while open.
- **A size axis** may change any value, sizes, spacing, the type scale and fonts among them. Each combination of its modes needs a scene of its own.
- **Fonts for a group of renderers are one size axis.** A *font profile* is the set of fonts a brand gives a group of renderers. The profiles are the modes of a shared axis, and the default profile measures and draws the brand's own font files. Which profile a renderer draws in is the record of the engine and its plugins' ([visual-communication:DEC-005-engine-and-plugins] point 10).
- **Looks that share a form are modes, not brands.** Two palettes of one owner that share every layout are two modes of one value axis. A look with another owner, or a form of its own, is a brand, perhaps built on the first.
- **An axis for the people a look is tuned for,** such as an age group, is named apart from the piece's field that says who the piece is for (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 3). One word for two things would mislead every reader.

### 3. One key names a combination of modes

A *key* names a combination of modes over a set of axes. A scene's key spans its size axes, and a picture's key spans the axes whose values it reads.
- **It leaves default modes out.** For each axis whose mode is not its default, it holds the axis's name and the mode's name. The combination of every default has a reserved key that no other key can spell.
- **Axes come in the order of their names,** so no order is declared, kept or broken.
- **So a key stays the same when an axis with a default is added.** Every combination that existed takes the new axis's default, which the key leaves out.
- **Everything that names a combination uses its key:** a scene, an export and a name in code.
- **A picture's variant takes the first key it serves.** A *variant* is one version of a picture made while preparing, which serves one or more combinations. It takes the first of their keys: the one that holds the fewest axes, and among those the first in the order of its spelling. The reserved key holds none, so it comes first. Adding an axis with a default adds only keys that hold one axis more than a key that existed, so a variant's key stays the same too.

### 4. One naming rule turns a brand's names into names in code

A name in code has two parts: a *token path*, a token's place in the brand's tree of tokens, and a key.
- **Both are made of segments.** Each segment of a path names one group or token. Each segment of a key is one axis with its mode.
- **Every name that enters a path or a key has one shape:** lower-case words of letters and digits, joined by hyphens. Roles, component tokens, axes, modes, and the names of libraries and components all take it. It is stricter than the rule of the record of files and validation, that no name holds a path mark ([visual-communication:DEC-002-files-and-validation] point 4), and holds beside it.
- **Each code writer spells both parts in its language.** It keeps a segment apart from the words inside it, and the path apart from the key, so no two names spell the same. It may spell the key into the name, or as the context its language switches modes by. CSS, for example, keeps one variable for each token path and gives each value axis's modes a selector, so a page switches modes while open.
- **Each code writer's spelling is public,** since code outside the capability names what it spells. How a spelling is versioned is the record of the engine and its plugins' ([visual-communication:DEC-005-engine-and-plugins] point 8).
- **A brand built on another is written out whole,** the values it keeps from its base included.

### 5. The names a brand exports are public

A brand exports its roles, the component tokens it gives values, and its axes, modes and keys. Code outside the capability reads them, such as a game's runtime, and no lock protects that code (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 7). A brand's other tokens, such as a palette its roles alias, stay private: never exported, never open.
- **Breaking changes,** beyond what the record of change over time counts for every library ([visual-communication:DEC-003-change-over-time] point 6):
  - removing or renaming an exported token, or changing its type
  - removing or renaming an axis or a mode, or changing an axis's default
  - turning a value axis into a size axis, or the reverse
  - for a base, taking a role off its open roles (point 6)
  - for the foundations, a new shared role with no default (point 7), or a new shared axis, whose name may meet a brand's own axis
- **Not breaking:** a new role with a default, a new mode, a newly opened role, or a brand's own new axis with a default. Nor is a changed value, an alias pointed elsewhere included. A piece meets a changed value only when a person moves its lock. A base's new mode gives a brand built on it combinations its values were not tuned for, which that brand's checks then cover.

### 6. A brand may build on one other brand, within the roles its base declares open

- **One base, by major version.** A brand marks one of the libraries it builds on as its base, named by the major version it fits (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 5). It has at most one base. Its base may build on a brand in turn, so brands form chains.
- **The base declares its open roles:** the list of its roles that a brand built on it may give values. The list names roles, component tokens (point 7) or groups of them, a group matched by whole segments of its path. A value given to any other role fails validation.
- **Merged before aliases are resolved.** A value the brand gives an open role, for every mode or for some, wins over its base's in the combinations it covers. Its base's value holds elsewhere. Every token that aliases the role follows it.
- **Its aliases reach only what its base exports,** so its base may reshape its private tokens freely.
- **In a chain, each link narrows.** A brand's own open roles name only roles open to it, and its own.
- **It varies its values on its base's axes,** by their names and modes, in its own Resolver document. It adds no axis and no mode, and changes no default. So pieces, pictures and code switch between the same combinations under the base and every brand built on it.
- **What it keeps:** every value it is not open to change, and its base's axes, layouts and parts.
- **What it may add:** roles of its own, parts of its own with their component tokens, and the layouts of a kind of work its base does not serve. It never replaces a layout or a part its base has.
- **The engine resolves the base first,** then the brand's own values over it. What a lock does when its libraries need two majors of one base is the record of change over time's ([visual-communication:DEC-003-change-over-time] point 8).

### 7. Roles a library adds lie under its own name

- **Shared roles** are the foundations'. Each other library's own roles lie under a group named after the library, so a role a base adds never meets one a brand built on it adds. No library takes the name of a top group of the shared roles.
- **A component token** is a role one component declares for one of its parts, such as a control's fill, so a brand can style that part apart from a shared role. All component tokens lie under one group, `component`, then the component's library and name.
- **A component token's default aliases a role, never a value.** So a component library holds no raw value, and no brand has to give the token a value.
- **A shared role the foundations add after their first version** carries a default that aliases an older role. Every brand already released still gives it a value.
- **A base may open a component token alone,** so a brand built on it restyles that one part without changing the shared role everywhere. A component declares one only where a brand needs to differ.
- **How far a brand reaches into a component.** A brand reaches a component only through the roles it names and the component tokens it declares. So a component that names a role for its corners, its strokes or its fonts lets each brand draw them its own way. Its parts, their arrangement and its options stay the component's.

### 8. Pairs of colours that must contrast

- **Declared pairs.** The foundations declare the pairs of shared colour roles that must contrast, such as body text on a surface. Each pair names the contrast it must reach, by WCAG's levels for text and for other marks. A library declares the pairs that involve its own roles.
- **Checked in every combination of the axes that change a colour.**
- **Checked as drawn.** The engine also measures each text a scene draws against the fill under it, at WCAG's level for the text's size, in every combination the piece is drawn in. Content may point a part at another role (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 6), which no declared pair foresees. A text its component marks as decorative is not measured. Nor is a text over a picture, which a reviewer judges.

### 9. Fonts come from committed files, and a missing font refuses the render

- **A font role gives a list of families.** The first family measures each character it has, and the next measures the rest.
- **Each font profile says how each font is measured:** from font files, from a table of widths, or by an estimate. The default profile measures and draws from files. A table or an estimate stands only for a font a medium holds itself, such as a whiteboard service's. That table ships with the renderer for the medium, and the scene records how each text was measured.
- **A font file is committed unchanged with its licence,** where its licence allows. A font the brand may not ship is a file the project commits in the capability's location (the record of files and validation, [visual-communication:DEC-002-files-and-validation] point 1), which the brand names by a hash. A project that may not commit it either cannot draw in that profile.
- **Never a font found on the machine,** since the engine reads only the project's files (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 8).
- **A missing font refuses the render,** before anything is laid out, naming the font. Every character is checked against the families that measure it.

### 10. A notation maps concepts to roles, read with its name

- **What a concept maps to.** A notation lists the concepts of one subject. Each maps to a *colour family*, a group of colour roles that paints one thing, such as its line, its fill and the text on it, which the foundations declare. A concept may also map to an icon among the notation's marks, and to a shape from a list the foundations declare. It never maps to a value, so each brand colours a concept its own way.
- **Colour is never the only sign.** The foundations' families bound how many concepts one piece tells apart by colour. An icon or a shape tells the rest apart.
- **An icon follows the brand,** tinted by a role of its concept's family.
- **A concept is read with its notation's name,** as a component is read with its library's. A piece uses concepts only from the notations it names.
- **A notation's file** is of the capability's format, checked by its schema. Its marks, such as a logo, are files it holds. The words it gives its subject, for translators, are decided with translation, later.

### 11. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it (COR-055 points 1 and 4). A final piece's drawing is not judged, as that record decides.
- **Fails validation:**
  - a value given to a role its base does not open, an open role its base does not have, or an alias to a token its base keeps private
  - a brand built on another that adds an axis or a mode, or changes a default
  - a role with no value in some combination, an alias that leads nowhere, or a loop of aliases
  - a token of another type than its role's, or a value axis that changes what may move something
  - a name that does not take the shape of point 4, or a library named after a top group of the shared roles
  - a declared pair, or a drawn text, below the contrast it must reach in some combination
  - a font file, or a table, that a profile names and nothing holds, or a character no family measures
  - a concept that its notation does not hold, or that comes from a notation the piece does not name
- **Stated as a fact:** a text measured from a table or by an estimate.

## Rationale

**Why the DTCG format and its Resolver.** A stable format exists, and design tools read and write it. A format of the capability's own would have no tool behind it. The extension point keeps what the format lacks inside valid files.

**Why axes, and why each changes values or sizes.** Combinations are the product of the modes on each axis, so a file for each combination copies values, as the prototype's did. Adobe's Spectrum keeps such axes as separate switches. A value axis moves nothing, so one scene serves all its modes. A size axis may change anything, so a look tuned for children may change both colours and sizes on one axis. Font profiles change sizes for a group of renderers, so they need no mechanism of their own.

**Why a key leaves defaults out, names each axis, and sorts by name.** If a key held every axis, adding one would rename every picture, export and name in code. Naming the axis beside its mode keeps one axis's new mode from meeting another's. Sorting by name leaves no order to change. A variant takes the key with the fewest axes for the same reason: ordered by spelling alone, a new axis whose name sorts first would hand a variant one of its new keys. A shared axis the foundations add could meet a brand's own axis of that name, so it waits for a major release, which a lock moves on purpose.

**Why exported names are public, and the rest private.** A piece has its lock and its before-and-after. A game's runtime has neither, so a renamed token breaks it silently. A palette left private can be reshaped without a major release. Opening a token later breaks nothing, while closing one does.

**Why one base, and why now.** Two bases would each give every shared role a value, and draw every layout, so one would have to win everywhere. Their open roles and axes would have to be joined. A chain needs none of that: each link narrows the last. Every case known is a chain, such as a game built on its platform, and a game's tournament edition built on the game. What a brand may change, its axes and its keys all follow from one line of bases, so the rule is fixed before any brand relies on it.

**Why a brand built on another adds no axis.** Code written for the platform and for each game then has one shape, and a base that adds an axis meets no axis a game holds. An addition such as a role or a part cannot hide a fix in the base. A replacement would.

**Why the list is called the open roles.** The founding record calls a contract what another capability asks to have drawn ([visual-communication:DEC-001-visual-communication-discipline] point 10). The list holds roles, component tokens among them.

**Why a library's own roles, and component tokens, lie under names.** A base and a brand built on it are released by different owners. Without a group for each, a role a base adds could take the name of one a brand built on it holds. A component token gives a brand one control without changing a role everywhere. Infinum found role tokens alone made one brand hard to adjust, and would add component tokens earlier ([Infinum](https://infinum.com/blog/multibrand-design-system-tokens/)). A default that aliases a role asks nothing of a brand that does not care.

**Why contrast is checked in every combination.** Nobody looks at every combination by hand, and a dark mode with high contrast is where a palette breaks unseen.

**Why fonts come only from committed files.** A font found on the machine differs between machines and continuous integration, so the same files would give different scenes. Measuring in one font and drawing in another makes every box the wrong size, so a missing font refuses.

**Why a notation maps to roles.** A concept then keeps one meaning in every piece about it, and each brand gives it that brand's colour. A notation that held values would tie a subject to one brand.

### Alternatives considered

- **A file of values for each theme and mode.** Rejected. It copies values, and grows with every combination.
- **Every game as one more mode of the platform's brand,** as the Resolver's own examples do. Rejected. The platform's library would hold every game's values, and no game could release alone.
- **A brand built on another may change any value.** Rejected. A fix to the base could be hidden.
- **Two bases, or new axes in a brand built on another.** Rejected for the reasons above.
- **A key that holds every axis, or only mode names, or axes in an order each brand declares.** Rejected. The first renames everything when an axis is added, the second lets modes clash, and the third can be broken.
- **Every token exported.** Rejected. A palette's shape would become a promise.
- **Fonts chosen by a renderer, outside the brand.** Rejected. Fonts are design, which the logical layer sets (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 2). A renderer only names which of the brand's profiles it draws in.

## Implications

- **The foundations** declare the shared roles with their types, the shared axes with their common modes, the colour families, the shapes, and the contrast pairs among shared roles.
- **The capability's schema for a brand** names the extension point, the kinds of value a value axis may change, and how a key is spelled. The capability's reference gives each code writer's spelling.
- **The walking skeleton** reads a base brand and its open roles, and resolves two value axes, the colour scheme and the contrast. It writes the brand out as CSS under the naming rule, and checks contrast and missing fonts at the severities of point 11.
- **The record of the engine and its plugins** decides how text is measured, and the document of a brand's resolved values that code writers and producers read ([visual-communication:DEC-005-engine-and-plugins] points 4 and 7).
- **Later slices** build a brand built on another with its open roles checked, axes that change sizes in use, and the words a notation gives translators.
- **A brand for projects to lock is left to a later change.** The capability's tests, and the reference renders of the component library it ships to start from, draw with a brand kept for its tests, which no project locks. Whether the capability ships a brand that projects may lock, such as a neutral one to start from, is left to a later change.
