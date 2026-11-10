---
id: DEC-008
title: A library's own role may default to another role, so a brand that does not name the library still draws it
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component library, such as the starter, may declare roles of its own, such as the colour of its connectors. Each may carry a default: another role it stands in for until a brand gives it a value, such as the shared colour for lines. So a brand that has never heard of the library still draws its components, in the brand's own colours and sizes. A brand that names the library may give its roles values of their own. A default always names a role, never a value, so a component library still holds no look of its own. A library may leave a role without a default where no role is a fair stand-in. Every role of the starter ends, through its defaults, at a role every brand gives a value.

## Context

The record of brands and notations lets each library add roles of its own, under a group named after the library ([visual-communication:DEC-004-brands-and-notations] point 7). It gives defaults to two kinds of role:
- **A component token** carries a default that aliases a role, so no brand has to give the token a value.
- **A shared role the foundations add after their first version** carries a default that aliases an older role, so every brand already released still draws it.

It says nothing of a library's own roles. Without a default, each role of the starter would need a value from every brand that draws the starter. The starter is the first component library a project meets ([visual-communication:DEC-007-starter-library], Context), so every project's brand would have to know it, or fail. A brand released before a library could never draw that library.

The capability's next slice ships the starter and a neutral brand, which rest on this choice ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)). Before this record, the capability reads the roles of the foundations alone, though its schema already gives every role an optional default, written as an alias. Until validation accepts files at an older format number, the format grows only by additions that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3).

## Decision

**A library's own role may carry a default: an alias to another role of its own library or to a role of a library it builds on, the shared roles included, never to a value. The role takes its default wherever no brand gives it a value. Each library's owner chooses a default as a fair stand-in, and every role of the starter ends, through its defaults, at a shared role. A brand reaches a library's roles only where it names that library. A library's contrast pairs, at its defaults, rest on the pairs the foundations declare.**

### 1. A library's own role may carry a default, below every brand's value

- **Its own roles.** A library's *own roles* are the roles a library other than the foundations declares, under a group of its name (DEC-004 point 7). A shared role's default stays as that record has it, and a chain of defaults may pass through one.
- **A default** is an alias to another role. The role takes it wherever no brand gives the role a value. A library is *at its defaults* under a brand that gives none of the library's roles a value.
- **Below every brand.** In each combination of modes, the defaults lie under the base's tokens and the brand's own sources. The aliases are resolved after the merge, as for a base (DEC-004 point 6). So a brand's value wins in the combinations its sources cover, and the default holds elsewhere.
- **A default follows the brand.** It aliases a role, so it takes the value the brand gives that role. A brand that does not name the starter draws the starter's connectors in its own colour for lines.
- **Resolved with a lock.** A piece draws with the versions of the libraries its lock names, and written code with those its declaration locks. A brand checked alone is resolved with the newest version the project holds of each major it names ([visual-communication:DEC-005-engine-and-plugins] point 7).
- **A role with no default** takes a value only from a brand, as every shared role of the foundations' first version does.
- **A brand's own roles** stay as the record of brands and notations has them (DEC-004 points 5 to 7). The brand gives each a value, and a default on one reads the same way as a library's.

### 2. A default is a fair stand-in, and every starter role ends at a shared role

- **The owner's choice.** A default is the role its library's owner judges the fairest stand-in: the one whose value best serves the role's use under a brand that never gave it one. The owner judges it in review, as the starter's bar for entry is judged ([visual-communication:DEC-007-starter-library] point 3). No check judges meaning.
- **For a size, a number or a font,** a nearby role usually serves, such as a small spacing for the radius of a card's corners.
- **For a colour that marks a meaning,** such as a warning, only a role of that meaning serves. Colour says what a thing is ([visual-communication:DEC-001-visual-communication-discipline] point 6), so a colour of another meaning would mislead unseen. Where no role carries the meaning, the owner may leave the role without a default. A brand that gives it no value then shows the gap as a finding, not a wrong meaning.
- **Every role of the starter ends at a shared role.** Its chain of defaults ends at a role of the foundations, so any brand draws the starter. The starter's tests hold it to that.
- **A meaning the starter needs that no shared role carries** becomes a shared role of the foundations, and each way costs something:
  - *Before the foundations' first release,* the role needs no default. Every brand that takes that version of the foundations gives it a value, or fails.
  - *After it,* the role carries a default that aliases an older role (DEC-004 point 7), which may be of another meaning until a brand gives the role a value. That record makes the same trade for every shared role. The only other way is a major release of the foundations, since a new shared role with no default breaks every brand (DEC-004 point 5). A picture role needs neither a default nor a major, since no brand owes it a value (refinement per [visual-communication:DEC-025-picture-files] point 4).

### 3. A default aliases a role the library names, never a value

- **What it may alias:** another of the library's own roles, or a role of a library it builds on, the foundations' shared roles included. A library names the libraries it builds on, by major (DEC-001 point 5).
- **Of the same type** as the role.
- **Never a value.** Only a brand holds a raw value (DEC-001 point 5), so a component library still holds none.
- **Never a component token.** A component token narrows a role for one part (DEC-004 point 7). So the defaults run one way: from a part to a library's role, and on to a shared role.
- **A chain of defaults ends,** never in a loop. A role draws under every brand only where its chain ends at a shared role.
- **A component token's default** may alias a library's own role, as it aliases what a library's own role's default may alias, and never a component token (DEC-004 point 7; refinement per [visual-communication:DEC-035-component-tokens]). So a brand that gives the role a value restyles the part too.

### 4. A brand reaches a library's roles only where it names the library

- **Named by major.** A brand reaches a library's own roles, and the component tokens of its components, only where it names that library among those it builds on, by the major it fits (DEC-001 point 5). To reach one is to give it a value, open it or alias it. So a brand's values never meet roles of a major they were not tuned for.
- **What it owes a library it names.** It gives a value, in every combination, to each of that library's roles without a default, as it gives every shared role but a picture role one (refinement per [visual-communication:DEC-025-picture-files] point 4). Each token it holds under that library's name gives one of the library's roles a value of its type, so its private tokens lie elsewhere. A token it holds under `component.<library>` is judged as one under that library's name, but for one under `component.<its own name>` (refinement per [visual-communication:DEC-035-component-tokens]).
- **Where it names none,** the library is at its defaults under that brand. A token the brand holds under that library's name gives the library nothing, and stays private, as a brand's other tokens do (DEC-004 point 5). So does one under `component.<library>`, but for one under `component.<its own name>` (refinement per [visual-communication:DEC-035-component-tokens]).
- **Built on a base,** a brand gives a library's role a value only where both name the library and the base opens the role (DEC-004 point 6). A base may open a role of a library it names, whether or not it gives the role a value. So a base that does not name a library leaves the library at its defaults for every brand built on it.
- **What naming costs.** Every project that uses the brand holds the library, and every piece that uses the brand locks it, even a piece that draws none of its components (DEC-003 point 8). Moving to a new major of the library is a breaking change of the brand (DEC-003 point 6), and along a chain the base and every brand built on it move together. So a brand names a library only to give its roles values.

### 5. A brand exports the library roles it gives values, and code sees every role locked with it

The record of brands and notations makes a brand's exported names public (DEC-004 point 5). Two sets follow:
- **A brand's exports** hold, beside the shared roles and its own, each role of a library it names that it gives a value, as they hold the component tokens it gives values. They leave out a shared picture role the brand gives no value (refinement per [visual-communication:DEC-025-picture-files] point 4). A brand built on a base exports what its base exports, its base's values included (DEC-004 point 4). The brand promises these names under its own versions.
- **The document of resolved values under a lock** also holds every other role and component token of the libraries locked with the brand, at the brand's values or at their defaults (DEC-005 point 7). Those names are promised by their own libraries, by major, and code that reads them names that library's major in its lock.

### 6. A library's contrast pairs hold at its defaults

A library declares the pairs of colours that involve its own roles (DEC-004 point 8).
- **At its defaults.** In a pair, replace each of the library's own roles by the role its default aliases. The pair that results is one that the foundations, the library itself or a library it builds on declares, in either order, at a level that needs as much contrast or more. Each such step holds in turn, so every pair at its defaults rests on a pair the foundations declare, which every brand is checked against.
- **Where a brand's values reach the pair,** it is judged at that brand in every combination. A brand's values reach a pair where they change either role from what its defaults or the brand's base give, through the brand's own values or the roles they alias.
- **A pair with a role that has no default** is judged only at the brands that give that role a value.
- **Drawn text is still measured** against the fill under it, in every combination a piece is drawn in (DEC-004 point 8).

### 7. What breaks a library's own roles

The record of change over time already counts a removed or renamed role as a breaking change of any library ([visual-communication:DEC-003-change-over-time] point 6). Beyond it:
- **A role promises what the components that read it promise.** One that only experimental components of its own library read, directly or through a default, may change in any release, as they may (DEC-003 point 7). Once a stable component reads it, the rules below hold.
- **Breaking:** a change after which a role's chain of defaults no longer ends at a shared role, where it did. A default removed, or pointed at an own role whose chain does not end at a shared role, is such a change. So is a new own role whose chain does not end at a shared role, since every brand that names the library must then give it a value.
- **Breaking, for any library, the foundations included:** a declared pair removed, or its level lowered, since the pairs of the libraries built on it may rest on it (point 6).
- **Not breaking:** a new own role whose chain ends at a shared role, a default pointed at another role along such a chain, or a new pair. These change the look, or what a brand's values are checked against, not what a brand must write. A brand that names the library meets them when it is checked with the new version, and a piece only when a person moves its lock.

### 8. What this adds to the format, and what still holds

- **Added.** The capability reads the own roles of each library it resolves, from that library's `roles.yaml`, where it read the foundations' alone before. It resolves their defaults, a brand's values for them, their exports and their pairs under points 1 to 6.
- **No schema changes.** The format already gives every role an optional `default`, written as an alias. It stays optional, so no field becomes required, and no value a schema accepted is refused (DEC-003 point 3).
- **What "still holds" means.** Every file is read and resolved as before: the foundations' roles, every brand's values for the shared roles and every piece. Validation's results may still change, in the cases below, since the check now judges files it did not read before by rules the record of brands and notations already sets (DEC-004 points 7 and 8).
- **Read for the first time.** Before this record, the capability read no library's own roles, so every part that read one was reported. Now such a role draws where it has a default, or where a brand gives it a value. A library of the project's own, not yet released, may meet a finding in its roles for the first time. In a released version such a finding asks for attention (point 9).
- **A brand's tokens under a library's name.** The capability kept them private before. Where the brand names that library, they now give its roles values, and one that fits none of its roles is a finding (point 9).
- **One finding moves.** A part that reads a library's role whose chain gives no value under the brand was found in the part's component before. It asked only for attention where that component lay in a released version. It is now found at the lock that combines the brand and the library, since neither alone is at fault, and there it fails (point 9).

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7). Elsewhere, as in a released library version, it asks for attention and names who can correct it.
- **Where each lies.** A finding in a library's `roles.yaml` lies in that library's version. A finding of a brand against a library it names lies in the brand's version, judged when the brand is checked alone (point 1). A fault that only a lock's combination of versions shows lies at that lock, which the project chose.
- **Fails validation:**
  - a default that is no alias, or aliases a component token, a role of another type, or a role of a library its library does not build on
  - a default that leads nowhere, or a loop of defaults
  - a pair of a library that, at its defaults, falls on no pair declared at a level as strict
  - a brand that names a library and gives one of its roles without a default no value in some combination
  - a brand's token under the name of a library it names, or under `component.<library>` for such a library, that gives none of the library's roles a value, since it names none or is of another type (refinement per [visual-communication:DEC-035-component-tokens])
  - at a lock, a part that reads a library's role whose chain gives no value under the brand, where the brand does not name the library
- **Asks for attention, never failing:** a brand's token under the name of a library a piece locks with it, or under `component.<library>` for such a library, but for one under `component.<its own name>`, where the brand does not name that library (refinement per [visual-communication:DEC-035-component-tokens]). The token stays private, and gives the library nothing.
- **Stated as a fact:** a library's own role whose chain of defaults does not end at a shared role, so that only a brand that gives it a value draws it.

## Rationale

**Why defaults.** A component library serves every brand, and anyone may publish one (DEC-001 point 5). A brand cannot know the libraries published after it. Without defaults, every brand would have to name every library its pieces use, and give each of its roles a value. The starter would ask that of every project's brand. A role that defaults to a fair stand-in asks nothing of a brand that does not care, as a component token's default already does (DEC-004 point 7).

**Why an alias, never a value.** A component library holds structure, and only a brand holds values (DEC-001 point 5). A default value would give the library a look of its own. A brand that does not name the library would then draw it in colours foreign to the brand. An alias draws the library in each brand's own values, so switching the brand still changes the whole look.

**Why the owner judges, and why a role may have none.** Whether a stand-in fits is a judgment of design, which no check can make. For sizes and fonts a near value looks a little off at worst. A colour that marks a meaning misleads when it shows another, while a missing value is reported. A required default would also make a field required, which the format cannot do yet (DEC-003 point 3).

**Why every starter role ends at a shared role.** Any project may meet the starter, with a brand written before it or for another purpose. A starter that asked every brand for values would fail most of them. A meaning the starter needs that no shared role carries recurs across libraries, so it belongs to the foundations. After their first release, a new shared role carries the nearest default. The record of brands and notations already makes that trade for every shared role, since a major release of the foundations would move every library and brand.

**Why a default may alias a role of its own library, or of one it builds on.** One role can then lead several, such as a small gap that follows the library's gap, so a brand that gives one a value restyles all. A library built on the starter follows the starter's roles, so a brand that restyles the starter restyles it too. Both reach only names the library already names (DEC-001 point 5), and a breaking change to them waits for a major release.

**Why never a component token.** A component token is the narrowest role, for one part. A library's role that followed one part would invert the narrowing, and let one component reshape the whole library.

**Why defaults lie under the brand, and aliases resolve after the merge.** A default is the library's stand-in, and a brand's value is the brand's choice, so the brand wins. Resolved after the merge, a default takes the brand's value for the role it aliases, which is what makes the library look like the brand.

**Why a brand names the library, despite the cost.** A brand's values for a library's roles are tuned to one major of it. Named by major, they never meet roles that a new major renamed or reshaped. A library already names those whose names it uses (DEC-001 point 5), so this adds no mechanism. The cost falls only on a brand that gives the library values. A brand that leaves the library at its defaults stays free of its majors.

**Why a brand exports only the library roles it gives values.** A brand promises its exports under its own versions, and narrowing a public set later breaks code while widening it breaks nothing (DEC-004 point 5). A role the brand leaves at its default is the library's promise, kept by the library's major, so the brand need not promise it again. It is the rule the record of brands and notations already sets for component tokens.

**Why a role takes the promise of the components that read it.** The starter's components enter as experimental, so they may change while they are tried ([visual-communication:DEC-007-starter-library] point 3). A role only they read is part of that trial. Fixed from its first release, it would make every early rename a major release of the starter, and of every brand that names it.

**Why a library's pairs hold at its defaults.** A library cannot test the brands it will meet. The foundations' pairs are what every brand is checked against. A library whose defaults land on declared pairs passes that check on to every brand that leaves it at its defaults. Checked at each lock instead, a weak pair would fail a project for a fault only the library's owner can correct (DEC-002 point 7).

**Why a brand's findings against a library are judged with the brand alone.** The brand's owner corrects them, so they lie in the brand's version, judged once for each version. Judged at every lock, they would multiply with the versions of each library, and lie where the brand's owner does not look. What only a combination draws wrong is still found at its lock.

### Alternatives considered

- **No defaults for a library's own roles.** Rejected. Every brand would have to name every library its pieces use, and a brand released before a library could never draw it.
- **A default that holds a value, as a component library often ships a theme of its own.** Rejected. A component library would hold a look, against the founding record ([visual-communication:DEC-001-visual-communication-discipline] point 5), and a brand would draw it in foreign colours.
- **A default required on every own role.** Rejected. It would make a field required (DEC-003 point 3), and force a misleading colour where no role carries the right meaning.
- **No own roles: shared roles and component tokens only.** Rejected. A library could add a meaning only through the foundations, which one owner releases. A component token restyles one part, not every part of a library at once.
- **A default that aliases a shared role only.** Rejected. No role could lead another within a library, and a library built on the starter could not follow it.
- **Another brand's values, such as a neutral brand's, where a brand gives none.** Rejected. One piece would mix the looks of two brands, and lock two brands.
- **A brand that gives a library's roles values without naming it.** Rejected. Its values could meet a major they were not tuned for.
- **A thin brand that names the library, built on a base that does not.** Rejected. The base would not control what the brands built on it change. A fix the base makes to a shared role that a default follows could be hidden, which the record of brands and notations refuses ([visual-communication:DEC-004-brands-and-notations], Alternatives considered).
- **A brand's values for a library kept apart for each of its majors.** Rejected. It frees a piece to lock a new major before the brand moves, but adds a new shape to every brand. Leaving a library at its defaults already frees a brand of its majors.
- **A brand exporting every role of each library it names.** Rejected. The brand would promise names whose fate its library decides, and could never narrow the set.
- **A library's own roles fixed from the first release, whatever reads them.** Rejected. An experimental starter could rename no role without a major release, against the reason its components enter as experimental.
- **A library's pairs judged at each lock.** Rejected. A project would fail for a fault only the library's owner can correct.

## Implications

- **The capability's reference** describes every library's own roles, their defaults, what a brand gives them, its exports and the findings of point 9. The `roles` schema keeps its shape, and its description follows this record.
- **The check of a library's `roles.yaml`** also carries out the record of brands and notations (DEC-004 points 7 and 8). Its own roles lie under its name, none under the group of component tokens, and each pair names one of its own roles. Their findings fail as point 9's do. Which other declarations a library other than the foundations may hold, such as a brand's own axes, is left to the change that builds them.
- **The document of a brand's resolved values** holds the own roles of the component libraries resolved with it, at the brand's values or their defaults, as it holds their component tokens (DEC-005 point 7).
- **The release's comparison** of a library's components with its previous version (DEC-003 point 7) also compares the own roles that a stable component reads.
- **The starter** gives each of its own roles a default whose chain ends at a shared role, and its tests check it. Where no role is a fair stand-in, the foundations gain a shared role.
- **A type the shared roles lack,** such as a font weight, gives a library's role of that type no chain that ends at a shared role. The foundations declare a shared role of that type when a library needs one.
- **The neutral brand** need not name the starter. It draws the starter at its defaults, and names it only to give a role a value. It gives a value to every shared role, those the starter adds to the foundations included.
- **Layouts are not roles.** Whether a top component's layouts take a default that a brand may replace is decided apart ([visual-communication:DEC-009-layout-defaults]). It shares the first half of point 4's rule: a brand draws a top's layouts only where it names the top's library. A base opens no layout to the brands built on it, since a brand keeps its base's layouts and adds those of a kind of work its base does not serve (DEC-004 point 6).
