---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/schemas/config.schema.json
        - .pkit/capabilities/living-docs/templates/space-definition.md
        - .pkit/capabilities/living-docs/rule-sets/ldoc.md
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/_lib/binding.py
        - .pkit/capabilities/living-docs/scripts/validate.py
      record: ["living-docs:DEC-001", "living-docs:DEC-002", COR-049, COR-050, COR-051, COR-056]
      artefact:
        - RS-LDOC-001
        - RS-LDOC-002
        - RS-LDOC-003
        - RS-LDOC-004
        - RS-LDOC-005
        - RS-LDOC-006
        - RS-LDOC-007
        - RS-LDOC-008
        - .pkit/schemas/README.md#the-friction-block
        - .pkit/cli/README.md#configuration-file
        - .pkit/cli/README.md#config-set-key-value---yes
        - .pkit/schemas/README.md#rule-set-files
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#friction-artefacts---at-rev---json
        - .pkit/cli/README.md#docs-record-location-capability-name---dry-run
        - .pkit/cli/README.md#rule-sets-reach-path---at-rev---preview---json
        - .pkit/capabilities/living-docs/pages.md#types
---

# Spaces

Where a project's documentation spaces lie, the definition each space's pages follow, and the shared method every definition inherits, `LDOC` ([living-docs:DEC-001-living-docs-discipline] points 1 to 3).

## Contents

<!-- pkit:contents -->
- [Declaring the spaces](#declaring-the-spaces)
- [Each definition's scope](#each-definitions-scope)
- [The definitions location](#the-definitions-location)
- [The space-definition template](#the-space-definition-template)
- [The shared method: `LDOC`](#the-shared-method-ldoc)
<!-- /pkit:contents -->

## Declaring the spaces

Where the documentation lives is declared in two files, joined by path:

- **The backbone configuration** (`.pkit/project/config.yaml` <!-- unanchored: named as the file that holds these keys, whose meaning rests on the CLI reference's Configuration file section, which the page anchors -->) names the two documentation roots (`docs.user`, `docs.internal`). It names every place outside them that holds pages (`friction.places`), and the paths the friction checks leave out (`friction.exclude`). The CLI reference's "Configuration file" section documents those keys.
- **This capability's project configuration** (`.pkit/capabilities/living-docs/project/config.yaml` <!-- unanchored: named as the file, whose shape is schemas/config.schema.json, which the page anchors -->) holds what only living-docs needs: each space's audience, entry point and definition, and which space each place belongs to.

```yaml
pkit_schema: living-docs:config
schema_version: 1
spaces:
  user:                                        # who it serves, where they start, the space's rules
    audience: users
    entry-point: README.md
    definition: docs/living-docs/rule-sets/user.md
  technical:
    audience: maintainers
    entry-point: CONTRIBUTING.md
    definition: docs/living-docs/rule-sets/technical.md
places:                                        # place → space, the place written as in friction.places
  README.md: user
  CONTRIBUTING.md: technical
```

**A space's `audience`** says, in words, who the space serves. DEC-001 gives the user space users and the technical space maintainers. A space the project adds serves an audience neither serves, such as `integrators who call the HTTP API`, and its entry names it. `pkit validate` refuses an audience that is not text, or is blank.

**Which places are listed:**

- **A place inside a root** belongs to that root's space. It is listed under `places` only to assign it elsewhere.
- **A place outside every root** must be listed, unless it is declared to hold rule sets and gives no type. Such a place gives no space until it is listed. A document only it holds, such as its `README.md`, is then neither a page nor an unclassified document (DEC-001 point 1).
- **A place of rule sets** is one whose path has a `rule-sets` segment ([the schemas reference, "Rule-set files"](../../schemas/README.md#rule-set-files)). So is the old folder that `pkit config set docs.internal` declares to keep the sets found. One that gives a type must be listed as any other.
- **Each place names exactly one space,** and a project place never equals or encloses a root.

The file's shape is `schemas/config.schema.json`, which `pkit validate` applies.

**Trees a sync copies into a repository are never places.** In a repository where those trees are the authored source, they may be (the lifecycle README, "The ownership predicates"). The backbone's friction validation enforces this for every declared place, the project's or a capability's, as its `synced-place` finding (the schemas README, "The friction block").

## Each definition's scope

A space's definition carries a scope that selects the space's pages, written with the definition (DEC-001 point 2). Through it, `LDOC` and the space's own rules bind on those pages. Validation checks the parts of them it enforces as soon as the definition exists.

- **Before a definition exists,** no rule binds on the space's pages, and validation reports the space instead. No space has a definition when the capability is installed.
- **A definition with no scope** selects no page, so no rule binds on the space's pages through it. `pkit living-docs validate` reports such a definition, and names the scope to give it: the space's root and the places assigned to it, by the page type.
- **Pages a scope leaves out** are reported too, unless the join with the assignment, below, fails them. A scope may leave part of a space out on purpose, with `exclude`, so a page it leaves out is reported, never failed.
- **A place assigned later.** A place assigned to the space after its definition was written must be added to the scope's paths by hand. Otherwise validation fails each of its pages, which lie outside the scope.
- **A placeholder left in the scope's paths,** the template's `<root>`, names no file, and is reported as soon as the definition exists.

**The scopes and the assignment.** A scope selects artefacts by path and by type (COR-051 point 2). Where a space's definition carries one, the scope and the assignment both say where the space's pages lie. Validation holds them to each other (DEC-001 point 1):

- Each page an assigned place gives a space lies in that space definition's scope, and in no other space definition's scope. Validation reads the scopes covering each page from `in_scope_of` in [`pkit friction artefacts --json`](../../cli/README.md#friction-artefacts---at-rev---json).
- Where a definition selects by type, `types` in its scope, each assigned place outside every root gives the page type ([the page on pages, "Types"](pages.md#types)). Such a place that names no type fails, before it holds any page.

A definition with no scope selects nothing itself, so nothing is held to it. The places assigned to its space are checked only against the scopes of the other spaces' definitions. A space with no definition yet is checked the same way. Validation's summary names the spaces whose definitions carry a scope.

## The definitions location

The capability declares, in its package metadata, the two roots as the default places of their spaces, everything under each, each giving the page type. It declares its **definitions location** too, `living-docs/` under the internal root, which gives the template type. With the default root, that is `docs/living-docs/`.

- **The definitions** go in the location's `rule-sets/` folder, where the core reads them as the project's rule sets.
- **Recorded on first use.** The location is recorded the first time a definition is placed there, in `.pkit/capabilities/living-docs/project/docs-locations.yaml` <!-- unanchored: named as where the location is recorded, which COR-049 decides and the page anchors --> (`locations: {definitions: docs/living-docs}`). So changing a root later moves nothing already written (COR-049 point 5).
- **Who records it.** `pkit living-docs new space` records it (DEC-001 point 2). For a definition written by hand, `pkit docs record-location living-docs definitions` records it, and says what it recorded, the root it was derived from, and where to change it.

## The space-definition template

`templates/space-definition.md` is the template of a space's definition. A definition is a project rule set that inherits `LDOC`, carries a scope that selects the space's pages, and holds the space's own rules. Each rule carries its friction block in its own container.

- **Its stamp.** `pkit living-docs new space` writes it with the set named and its scope written, and names the file as the space's `definition` (DEC-001 point 2).
- **The scope's paths** are the space's root, everything beneath it, and each place assigned to the space outside that root.
- **The scope's type.** The scope selects by the page type too, `types: [living-docs:page]`, so the definitions, records and rules under the root stay outside it.
- **The user space's own rule:** its readers' paths stay unbroken (DEC-001 point 3).

A template copied into the definitions location takes the template type there, so it is never a page.

## The shared method: `LDOC`

`rule-sets/ldoc.md` is a method rule set (COR-051), cited `living-docs:LDOC`. Its accepted rules are those point 3 of [living-docs:DEC-001-living-docs-discipline] states, with that decision as their origin and their anchor. Its two proposed rules come from [living-docs:DEC-002-visual-elements]:

| Rule | Statement |
|---|---|
| `RS-LDOC-001` | A page's anchors ground every statement it makes, and only what the page anchors grounds one. |
| `RS-LDOC-002` | Each fact has one home. For a page that anchors a decision record, the record is the home of the facts it decides. The page may state them with no link to another page. A fact whose home is another page is stated only as a summary, however short. The summary links to the home, and anchors its section. A name that gives none of a thing's facts needs neither. |
| `RS-LDOC-003` | Each page names its reader and says only what that reader needs. |
| `RS-LDOC-004` | Pages of a kind follow one format, with a template per kind. |
| `RS-LDOC-005` | An index-like file is a signpost to what a folder holds, never a summary of its contents. |
| `RS-LDOC-006` | Nothing is created ahead of the need for it. |
| `RS-LDOC-007`, proposed | Each fact has one home, and a diagram is never it. Besides a page, a fact's home may be what the page anchors that decides or states it. The first of these is its home: an accepted record or rule, an artefact in force or a section of one, a captured source, code. A page of the user space anchors such a home under the internal root, and links nothing there. |
| `RS-LDOC-008`, proposed | A diagram, an image or a recording that carries meaning has a text alternative, and a decorative image has an empty one. |

`RS-LDOC-007` and `RS-LDOC-008` bind nothing yet. A major of `LDOC` accepts both, and `RS-LDOC-007` then supersedes `RS-LDOC-002` (DEC-002 point 10). The definitions' pins then fall behind until the project reviews the new major (core rule sets, COR-051 point 7).

**`LDOC` is never edited.** A space's definition inherits it, pinned to its major (`inherits: [living-docs:LDOC@1]`), and `pkit validate` reports when a new major arrives. Rules about how rules are named and inherited are the core's (COR-051), so they are not repeated here.

**Where `LDOC` binds.** `LDOC` takes no scope, as no shipped rule set does. So its rules bind on a page only through a project rule set whose scope selects the page (DEC-001 points 2 and 3).

- **That set** is the page's space definition, or a documentation rule set of the project's that inherits `LDOC`.
- **A page no such scope selects** is bound by none of `LDOC`'s rules. Neither is a page reached only through a pin behind `LDOC`'s major. So each definition's pin decides when a new major of `LDOC` starts binding on its space's pages.
- **Where to read it.** `pkit rule-sets reach` lists the rules that bind on each page.

**What validation settles.** `LDOC` declares, under `checks`, the parts of its rules that this capability's validator, `living-docs:validate`, enforces (COR-051 point 2, DEC-001 point 6):

- `RS-LDOC-003`: the page names its reader in its `reader` field, one the readers point holds.
- `RS-LDOC-004`: the page's body carries the sections its kind's structure declares, in order where order matters.
- `RS-LDOC-008`: each `mermaid` fence in the page's body carries an `accTitle` and an `accDescr`, each followed by text that is not blank.

A reader-review leaves those parts to validation, and judges the rest of each rule (DEC-001 point 6). A declaration is no part of a rule's content, so it flags nothing anchored to the rule. `pkit rule-sets reach` lists each part on the rule wherever `LDOC` binds. 

Validation checks each part only on the pages where its rule binds, as that answer gives it. On any other page, it reads none of them.
