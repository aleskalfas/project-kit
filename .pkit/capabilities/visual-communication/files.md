---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/package.yaml
        - .pkit/capabilities/visual-communication/scripts/status.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/scripts/produce.py
        - .pkit/capabilities/visual-communication/scripts/export.py
        - .pkit/capabilities/visual-communication/scripts/write-code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/root.py
        - .pkit/capabilities/visual-communication/scripts/_lib/location.py
        - .pkit/capabilities/visual-communication/scripts/_lib/config_text.py
        - .pkit/capabilities/visual-communication/scripts/_lib/names.py
        - .pkit/capabilities/visual-communication/scripts/_lib/files.py
        - .pkit/capabilities/visual-communication/scripts/_lib/reading.py
        - .pkit/capabilities/visual-communication/scripts/_lib/records.py
        - .pkit/capabilities/visual-communication/scripts/_lib/libraries.py
        - .pkit/capabilities/visual-communication/scripts/_lib/tokens.py
        - .pkit/capabilities/visual-communication/scripts/_lib/keys.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/layout.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/framing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/exports.py
        - .pkit/capabilities/visual-communication/scripts/_lib/code.py
        - .pkit/capabilities/visual-communication/schemas/defs.schema.json
        - .pkit/capabilities/visual-communication/schemas/config.schema.json
        - .pkit/capabilities/visual-communication/schemas/piece.schema.json
        - .pkit/capabilities/visual-communication/schemas/content.schema.json
        - .pkit/capabilities/visual-communication/schemas/libraries.schema.json
        - .pkit/capabilities/visual-communication/schemas/library.schema.json
        - .pkit/capabilities/visual-communication/schemas/roles.schema.json
        - .pkit/capabilities/visual-communication/libraries/foundations/library.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/roles.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/components/figure.yaml
        - tests/visual_communication_project.py
        - tests/test_visual_communication_pipeline.py
        - tests/test_visual_communication_layout.py
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/steps.yaml
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/library.yaml
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/test-brand.resolver.json
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/tokens/base.tokens.json
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/tokens/palette.tokens.json
      record: ["visual-communication:DEC-001", "visual-communication:DEC-002", "visual-communication:DEC-003", "visual-communication:DEC-004", "visual-communication:DEC-007"]
---

# The files of the visual work

Where a project's visual work lies, what each of its files holds, and who writes each one. The examples come from the shipped foundations library and from the capability's test files. The test brand `test-brand` and the test library `tests` exist for the tests only: no brand ships.

## Contents

<!-- pkit:contents -->
- [The location](#the-location)
- [What the location holds](#what-the-location-holds)
- [Names, ids and the binding](#names-ids-and-the-binding)
- [A piece](#a-piece)
- [The library folder](#the-library-folder)
- [Brands](#brands)
- [Keys of combinations](#keys-of-combinations)
<!-- /pkit:contents -->

## The location

The *location* is the one folder of the repository that holds the project's visual work: its libraries, its pieces, its declarations of code and its fonts (DEC-002 point 1). None of it lies in the capability's own folder. The default location is `visual/`, at the repository's top.

### Where it is recorded

The capability's configuration, `.pkit/capabilities/visual-communication/project/config.yaml`, records the location under the key `location`, as a path relative to the repository's top. In format 1 the configuration holds nothing else. A command records the location the first time it writes there, so a later change of the default moves no recorded location (DEC-002 point 1). A configuration as a command creates it:

```yaml
pkit_schema: visual-communication:config
schema_version: 1

location: visual
```

The command adds the line as text at the end of the file. It keeps every other byte: comments, order, line endings and a byte-order mark. Where the file records another location already, the command refuses, since a command never moves the location. To move the work, move the folder and change the `location:` line by hand.

A `location:` line with no value, such as `location:` alone or `location: null`, records no folder. Every command refuses it, and the check reports it as `location`, each saying how to mend it: write the folder that holds the work there, such as `location: visual`, or remove the line.

### How a command finds it

- **A command that writes in the location** (`render`, `produce`, `export`) reads `location:`. Where none is recorded, it takes `visual/` if that folder is absent, holds no file, or holds the marker. It records `visual` before its first write in the location. Otherwise it refuses, naming the folder.
- **`--location <path>`** names the location where none is recorded. The path is relative to the working directory, or absolute. The command records it. `--location visual` confirms the default.
- **With a location recorded,** a command refuses a `--location` that names another folder. It also refuses when the recorded folder is missing.
- **The check and the commands that only read** take the recorded location. With none recorded, they take `visual/` only where it holds the marker; otherwise there is no visual work. A recorded location whose folder is missing fails.

The *marker* tells that a folder holds the capability's work. It is the list of libraries, `libraries/libraries.yaml`, or any YAML file whose `pkit_schema` names one of the capability's schemas.

A location is refused when it is the repository's top itself, lies outside the repository, lies under `.pkit/` or under any folder whose name starts with `.`, is reached through a symbolic link, or is a file. The configuration's path is refused when it is absolute, holds a `\`, or has an empty segment, such as a trailing `/`.

The commands list the location's files as git sees them: tracked files, and untracked files that git does not ignore. A file git ignores is no part of the visual work. A symbolic link is never listed. Outside a git repository, the commands walk the folder.

## What the location holds

The location holds four folders: `libraries/`, the library folder; `pieces/`, one folder for each piece; `code/`, one file for each declaration of code; and `fonts/`, the fonts a brand names by their hash. What people write lies apart from what commands rewrite (DEC-002 point 5). No command writes a content file, a library version or a declaration. The table names the schema each file binds to (see [The binding](#the-binding)).

| File, in the location | Schema | Written by |
|---|---|---|
| `libraries/libraries.yaml` | `libraries` | a person; no command writes it |
| `libraries/<library>/<version>/library.yaml` | `library` | the library's owner |
| `libraries/<library>/<version>/roles.yaml` | `roles` | the library's owner |
| `libraries/<library>/<version>/components/<component>.yaml` | `component` | the library's owner |
| a brand's token files, Resolver document and fonts | none: DTCG, or a font's own format | the brand's owner |
| `pieces/<piece>/piece.yaml` | `piece` | a person; `pkit visual render` rewrites its `lock` alone |
| `pieces/<piece>/content.<language>.yaml` | `content` | a person |
| `pieces/<piece>/components/<component>.yaml` | `component` | a person, or a script of the project's own (DEC-001 point 8) |
| `pieces/<piece>/produced/<output>/record.yaml`, and a PNG for each variant | `produced-record` | `pkit visual produce` |
| `pieces/<piece>/findings.yaml` | `findings` | `pkit visual render` |
| `pieces/<piece>/exports.yaml` | `exports` | `pkit visual export` |
| `code/<name>.yaml` | `code` | a person |
| `fonts/<file>` | none | a person, who commits the font |

The code that `pkit visual write-code` writes lies where its declaration names, with its record beside it. A component's file is described in *Components*; produced pictures, exports, declarations of code and the code itself in *What is made from a piece*; `findings.yaml` in *What the check reports*.

### The clone's local folder

`.pkit/capabilities/visual-communication/project/local/` holds what a command makes that is never committed (DEC-002 point 1). The capability's `package.yaml` declares the folder local to each clone, so git ignores it. It holds:

- `previews/<piece>/`: the SVG previews `pkit visual render` draws;
- `exports/<piece>/`: the files `pkit visual export` makes;
- `handover/<piece>/`: what `pkit visual produce` hands a producer, and what the producer writes, until the command keeps it in the piece's folder.

*What is made from a piece* names the files in each.

## Names, ids and the binding

### Shapes

| Shape | Pattern | Who takes it |
|---|---|---|
| name | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, and none of `y n yes no on off true false null` | a library, a component, a field, an option and its words, a state, a concept, a layout, a slot, an exposed part or point, an axis, a mode, a piece, a produced output, a declaration of code |
| token path | segments `^[a-z0-9]+(-[a-z0-9]+)*$` joined by `.` | a role or a token; a segment may start with a digit, as in `space.3` |
| id | `^[A-Za-z][A-Za-z0-9_-]*$`, and none of `y n yes no on off true false null` in any case | an item, or another component content places, that something names |
| language | `^[a-z]{2,3}(-[a-z0-9]{2,8})*$` | a language of a piece, such as `en` or `pt-br`; always lower-case |
| use | `<library>/<component>`, or `piece/<component>` | a component, read with its library; never a version |
| version | `X.Y.Z`, X at least 1 | a library version |
| release | `X.Y.Z` | a release of the capability |

So a name holds no `.`, `/` or `#`, and starts with a letter, so YAML never reads it as a number. Nor is a name or an id a word that a YAML reader takes for a yes or a no, or for nothing, such as `no`, `on` or `null`, so either keeps its meaning wherever it is written unquoted, as a key or as a value. The schemas and the commands refuse the same words. The names that enter a token path or a key take the name shape, so a code writer can spell them in code (DEC-004 point 4).

### Reserved words

- **In every mapping that places a component,** an item included: `id`, `use`, `concept`, `state` and `override`. No component declares a field of these names, so each means the same everywhere (DEC-002 point 4).
- **`pkit`** is kept for the methodology's container, at a content file's top and in every mapping that places a component. No component declares a field of that name, and the capability never reads or writes anything under it (DEC-002 point 4).
- **At a file's top:** `pkit_schema` and `schema_version`, the binding.
- **Library names:** no library takes `piece`, the word by which `use` names the piece itself, nor `component`, the token group of component tokens, which holds no shared role. Nor does a library take the name of a top group of the shared roles, such as `space` or `font` (DEC-004 point 7).

### The binding

Every file of the capability's format names its schema and its format number in its first fields:

```yaml
pkit_schema: visual-communication:piece
schema_version: 1
```

The schema is `visual-communication:<kind>`, one of `config`, `piece`, `content`, `library`, `component`, `roles`, `libraries`, `produced-record`, `code-record`, `findings`, `exports` and `code`. The format number is `1`, shared by every schema of the capability (DEC-003 point 1). The command that creates a file writes both fields, and a person who writes a file by hand writes them too (DEC-002 point 3).

No path binds a file, and the capability writes no line that points an editor at a schema (DEC-002 point 3). The core's data validation checks each bound file's shape against the schema it names. The check finds the configuration, and each file of the location's table that has a schema, by its name and place. It reports one whose binding is missing or names another schema (*What the check reports*). Token files, the Resolver document, fonts and pictures carry no binding: each keeps its own format.

### How the files are read

- **YAML** is read as YAML 1.2. So `no`, `yes` and `on` are text, and `2025.10` is a number: quote a value that must stay text. A `%YAML` line that names another version is refused. A duplicate key, a second document, a key that is not text, an infinity, a binary or a set is refused too. A date or a time is read as the text it is written as.
- **JSON** is read as its value. A duplicate key, `NaN` and the infinities are refused.

## A piece

A *piece* is one finished item of visual work, such as a figure (DEC-001 point 3). Its sources are one folder, `pieces/<piece>/`, named with the name shape. The folder holds `piece.yaml`, a content file for each language, and the piece's local components.

### `piece.yaml`

A draft from the capability's tests, a figure in English drawn in both colour schemes:

```yaml
pkit_schema: visual-communication:piece
schema_version: 1
top: foundations/figure
brand: test-brand
languages: [en]
audience: Tests.
shown: Nowhere.
explains: false
exports: [svg]
state: draft
modes:
  colour-scheme: [light, dark]
lock:
  foundations: 1.0.0
  test-brand: 1.0.0
  tests: 1.0.0
```

| Field | Required | What it holds |
|---|---|---|
| `top` | yes | The piece's top component, as a use. |
| `brand` | yes | The brand the piece is drawn in, by its library's name. |
| `languages` | yes | The languages of its content, each once. The first is its source language. Each has its `content.<language>.yaml`. |
| `audience` | yes | Who the piece is for, in words. |
| `shown` | yes | Where the piece is shown, in words. |
| `explains` | yes | `true` where the piece explains, rather than only shows. |
| `exports` | yes | The formats an export makes (*What is made from a piece*). |
| `state` | yes | The piece's stage of life. Format 1 takes `draft` alone. |
| `modes` | no | For each axis, the modes the piece is drawn in. An axis it leaves out is drawn in its default. |
| `pinned` | no | `true` pins the lock. |
| `produced` | no | Each picture a producer makes for the piece (*What is made from a piece*). |
| `accept-losses` | no | The losses of a plugin a person accepted (*What is made from a piece*). |
| `lock` | no | The version of each library the piece uses. A render writes it. |

### The lock

A piece's *lock* names one version of each library it uses, those they build on included (DEC-001 point 7). A piece uses its top's library, its brand, and each library its content names in a `use`, other than `piece`. Through `builds-on`, it also uses every library those build on. The lock must name `foundations`, since a brand's values are read against the foundations' roles. The test brand brings it in: it builds on `foundations` 1.

**A draft** that is not pinned moves its lock at each render (DEC-003 point 8). The render takes the newest versions the location holds that the installed capability reads and that fit together. It stays within the major each library's locked version has, the library's *line*. A library the lock does not name yet takes its newest version of any major that fits. The render tries the newest versions first, and backs off library by library. Where no combination fits, it refuses and names the conflict, such as two libraries that build on two majors of one library: a piece locks one version of each library. A library the piece no longer uses leaves the lock. A draft may lock a version not yet released. To take a new major on purpose, write a version of that major in the lock; the next render moves within it.

**A pinned draft,** `pinned: true`, keeps its lock: a render checks it and never changes it. The lock must name every library the piece uses, each a version the location holds and the installed capability reads, and they must fit together. A pinned piece with no lock is refused: unpin it for its first render. To move a pinned lock, change it by hand, or unpin the piece and render it.

The render writes the lock into `piece.yaml` as text, as a top-level block mapping, one library a line, in the order of their names. Every other byte of the file stays: comments, order, line endings and a byte-order mark. Where the result would not read back as the file with that lock, the render refuses: write `lock:` as a block mapping, one library a line.

### Content files

A content file, `content.<language>.yaml`, holds what the piece shows in one language. It names no position, size, colour or font. It chooses only among what its libraries declare: components, options, states and roles (DEC-001 point 3). A second language is a second file of the same shape, with the same ids. The content from the capability's tests for the piece above:

```yaml
pkit_schema: visual-communication:content
schema_version: 1
body:
  use: tests/steps
  steps:
    - id: plan
      head: Plan the work.
    - id: build
      head: Build it.
caption: The flow.
```

- **The top** holds the fields of the piece's top component: `foundations/figure` takes `body` and `caption`.
- **A mapping with `use`** places the component it names. Its other keys are that component's fields and options, and the reserved keys. A field the component fills through a slot, as the figure's `body`, takes such a mapping.
- **A list the component repeats** holds items, each a mapping. The component names the component that draws each item, `tests/card` for `tests/steps`. An item may name its own with `use`.
- **`use: piece/<name>`** names a local component, `components/<name>.yaml` in the piece's folder.
- **An option** takes one word from the list the component declares, such as `spacing: wide` on `tests/steps`. An option that names an item takes `{item: <id>}`, or `{item: <id>, point: <name>}` for a point the item exposes.
- **`state`** names a state the component declares, such as `state: marked`.
- **`override`** points a painted part of the component at another role, by its token path, never at a value. `override: {b: accent}` paints the part `b` with `accent`.
- **`concept`** is reserved.
- **An id** marks an item, or another component the content places, that another part of the piece names (DEC-001 point 3). It is unique in its list. Each list holds the same ids in every language as in the source language, in any order.

Each key must be a field or an option of the component, or a reserved key. How a component declares its fields, options, states, slots and lists is in *Components*.

## The library folder

The *library folder* is `libraries/` in the location (DEC-003 point 4). It keeps one list of the project's libraries, and each version a lock may name, whole. A piece reads a library from the library folder alone.

Each version is a folder, `libraries/<library>/<version>/`, named after the version its `library.yaml` gives. The location *holds* a version when git lists that `library.yaml`. A version stays while a lock names it (DEC-003 point 4). A released version never changes: a change is a new version (DEC-003 point 6).

### The list, `libraries.yaml`

The list names each library's source, the versions present, which of them are released, and a fingerprint of each released one. The list from the capability's tests:

```yaml
pkit_schema: visual-communication:libraries
schema_version: 1
libraries:
  foundations:
    source: {kind: shipped}
    versions: {1.0.0: {released: false}}
  test-brand:
    source: {kind: project}
    versions: {1.0.0: {released: false}}
```

- **`source.kind`** is `shipped`, `project` or `repository`. A `repository` source names its `url` and `ref`; the others name neither.
- **`versions`** maps each version to `released: true` or `false`. A released version carries `hash`, its fingerprint over every file of its folder (*What the check reports*). A version not released carries none.
- **One library to a name:** a second library of one name is refused (DEC-003 point 4).

### `library.yaml`

The test brand's file:

```yaml
pkit_schema: visual-communication:library
schema_version: 1
name: test-brand
version: 1.0.0
kind: brand
needs-release: 0.1.0
builds-on:
  - {name: foundations, major: 1}
dtcg: "2025.10"
resolver: test-brand.resolver.json
open: [accent, space]
```

| Field | What it holds |
|---|---|
| `name` | The library's name. It matches the folder's. |
| `version` | Its version, `X.Y.Z` with X at least 1. It matches the folder's. A major release carries a breaking change, a minor one an addition or a change of look, a patch a fix (DEC-003 point 1). |
| `kind` | `components`, a component library, or `brand`. |
| `needs-release` | The oldest release of the capability whose tools and fields it uses. A version that needs a newer release than the installed one, the `version` of the capability's `package.yaml`, cannot be read. |
| `builds-on` | Each library it builds on, as `{name, major}`, the major an integer from 1. |
| `dtcg` | A brand's DTCG version, `"2025.10"`, quoted, since YAML reads `2025.10` as a number. |
| `resolver` | A brand's Resolver document, a path within its version folder. |
| `open` | A brand's open roles ([Open roles](#open-roles)). |

Every field is required, `builds-on: []` included. `dtcg`, `resolver` and `open` are required of a brand, and refused in a component library.

### The foundations

The capability ships the foundations at `.pkit/capabilities/visual-communication/libraries/foundations/`: version 1.0.0, of kind `components`, needing release 0.1.0, building on nothing, and not yet released. A piece reads them from the library folder alone, so the project copies the folder whole to `libraries/foundations/1.0.0/` and lists it with `source: {kind: shipped}`. No command copies it. The foundations hold:

- `library.yaml`;
- `roles.yaml`, the shared roles, axes, colour families and contrast pairs that every library shares (DEC-004 points 2, 7 and 8);
- `components/figure.yaml`, the top component `figure`, for a figure in a documentation page. The top components the capability ships are the foundations' (DEC-007 point 1).

Their shared roles are the colours `background`, `surface`, `text-primary`, `text-secondary`, `accent` and `line`; the dimensions `space.1` to `space.4`, `stroke.thin` and `size.figure`; the font families `font.body` and `font.heading`; and the typographies `type.body` and `type.heading`. They declare no colour family.

### `roles.yaml`

From the foundations, trimmed:

```yaml
pkit_schema: visual-communication:roles
schema_version: 1
roles:
  text-primary: {type: color}
  space.1: {type: dimension}
  type.body: {type: typography}
axes:
  colour-scheme: {kind: value, modes: [light, dark], default: light}
  contrast: {kind: value, modes: [standard, high], default: standard}
families: {}
pairs:
  - {text: text-primary, under: background, level: text}
```

- **`roles`** maps each role's token path to its `type`: `color`, `dimension`, `fontFamily`, `fontWeight`, `number` or `typography`. A role carries no value: a brand gives it one. A role's `default`, `{<role>}`, aliases an older role of the same type that has no default of its own (DEC-004 point 7). A role is never also a group of other roles.
- **`axes`** maps each axis to its `kind`, `value` or `size`; its `modes`, two or more, each once; and its `default`, one of them.
- **`families`** maps each colour family to its members, each naming a colour role.
- **`pairs`** lists the colour roles that must contrast (DEC-004 point 8): `text` drawn on `under`, at a WCAG `level`. `text` needs 4.5, `large-text` and `marks` need 3. The capability measures each pair, under each brand, in every combination of the axes, and the check reports a pair below its level (*What the check reports*).

The capability reads the `roles.yaml` of the foundations alone.

## Brands

A *brand* is a library of kind `brand`: it holds values (DEC-001 point 5). It keeps them as design tokens in the DTCG format, version 2025.10, and its modes as one Resolver document (DEC-004 point 1). The capability reads the subset of DTCG below, and refuses the rest. The test brand's `library.yaml` is shown under [`library.yaml`](#libraryyaml).

### Token files

A token file is a JSON file of the brand's version folder. It holds groups and tokens. From the test brand, trimmed:

```json
{
  "palette": {
    "$type": "color",
    "white": {"$value": {"colorSpace": "srgb", "components": [1.0, 1.0, 1.0], "hex": "#ffffff"}}
  },
  "scheme": {"$type": "color", "paper": {"$value": "{palette.white}"}},
  "background": {"$type": "color", "$value": "{scheme.paper}"},
  "space": {
    "$type": "dimension",
    "1": {"$value": {"value": 4, "unit": "px"}}
  },
  "font": {
    "$type": "fontFamily",
    "body": {
      "$value": ["Source Sans Pro"],
      "$extensions": {"pkit.visual-communication": {
        "files": {"Source Sans Pro": "fonts/SourceSansPro-Regular.otf"},
        "measure": "file"
      }}
    }
  }
}
```

- **A token** has `$value`, and may have `$type`, `$description`, `$extensions` and `$deprecated`. A group may have the same keys but `$value`. The file's top may also have `$schema`.
- **A group's `$type`** passes to the tokens below it, in the same file only.
- **Each key** of a group is a segment of a token path.
- **The types:** `color` is sRGB, `{colorSpace: srgb, components, alpha, hex}`: three `components` and an `alpha`, each from 0 to 1. `alpha` and `hex` (`#rrggbb`) may be left out. `dimension` is `{value, unit: px}`. `fontFamily` is a name, or a list of names. `fontWeight` is a number from 1 to 1000. `number` is a number. `typography` holds exactly `fontFamily`, `fontSize`, `fontWeight`, `letterSpacing` and `lineHeight`.
- **An alias**, `{a.b}`, takes another token's value, of the same type. A typography's member may alias too. An alias that leads nowhere, or a loop of aliases, fails.
- **One path,** a token in one file, is never a group in another.

### The Resolver document

The Resolver document holds `version` (`2025.10`), `sets`, `modifiers` and `resolutionOrder`, and may hold `name` and `description`. From the test brand, trimmed:

```json
{
  "version": "2025.10",
  "sets": {
    "base": {"sources": [{"$ref": "tokens/base.tokens.json"}]}
  },
  "modifiers": {
    "colour-scheme": {
      "contexts": {"light": [], "dark": [{"$ref": "tokens/dark.tokens.json"}]},
      "default": "light"
    }
  },
  "resolutionOrder": [{"$ref": "#/sets/base"}, {"$ref": "#/modifiers/colour-scheme"}]
}
```

- **A set** holds `sources`, and may hold `description`. A source is `{"$ref": "<token file>"}`, a file of the brand's version folder.
- **A modifier** is a shared axis. Its `contexts` hold one list of sources for each mode of the axis. Its `default` is the axis's default.
- **`resolutionOrder`** names each set and each modifier once, as `{"$ref": "#/sets/<name>"}` or `{"$ref": "#/modifiers/<name>"}`. A later source wins.

For each combination of modes, the capability merges the brand's sources in resolution order, over the shared roles' defaults, then resolves the aliases. A brand built on another merges its sources over its base's tokens instead ([Open roles](#open-roles)). Every shared role must have a value of its declared type in every combination. The brand *exports* the shared roles. Its other tokens, such as a palette its roles alias, are private. They lie in groups of their own, outside the top groups of the shared roles.

### Fonts

A `fontFamily` token names each family's font file in the capability's extension key, `pkit.visual-communication`, as `font.body` does above. `files` maps each family to a file of the brand's version folder, or to `{"hash": "sha256:<hex>"}`. A family named by its hash is a font the brand may not ship. The project commits it in the location's `fonts/`, where the capability finds it by the hash of its bytes (DEC-004 point 9). `measure` is `file`: the font is measured from its file. A font file is committed unchanged with its licence, where its licence allows (DEC-004 point 9).

### Open roles

A brand may build on one other brand, its *base*, and change only what the base opens to it (DEC-004 point 6). It marks the base in `builds-on` with `base: true`, by the major it fits. It marks at most one, and the base is a brand. The base is one of the libraries the brand builds on, so a piece's lock names it too ([The lock](#the-lock)). The capability's tests build the test edition, `test-edition`, on the test brand:

```yaml
builds-on:
  - {name: foundations, major: 1}
  - {name: test-brand, major: 1, base: true}
open: [accent]
```

A brand's `open` lists the roles that a brand built on it may give values: roles it exports, or groups of them by whole segments of their paths. Each entry names a shared role, or a group of them, such as `space`. The test brand opens `accent` and `space`.

The capability reads the base first, at the version the lock names, and its own base before it. In each combination of modes:

- **The base's tokens come first,** then the brand's own sources, in its resolution order. The aliases are resolved after the merge.
- **A value the brand gives an open role wins** in the combinations its sources cover, and the base's value holds elsewhere. Every token that aliases the role follows the merged value, the base's tokens included. The test edition gives `accent` a value in the dark colour scheme and at high contrast, so the test brand's accent holds in the light scheme at standard contrast.
- **A value for a role the base does not open** fails, and the base's value holds.
- **An alias reaches only the shared roles and the brand's own tokens.** An alias to a token the base keeps private fails. Each brand's private tokens are its own, so a palette of one name in the base and in the brand never meets.
- **The brand varies values on its base's axes,** by their names and modes, in its own Resolver document. A modifier for another axis, a context for another mode, or another default fails.
- **Each link of a chain narrows.** A base may build on a brand in turn. A brand's `open` names only roles its base opens to it. An entry that names more fails, and opens only what the base opens.

A brand's findings hold its base's too, each naming the base's version. A declared pair or a font is judged at the brand only where the brand's values change what the base gives.

### Axes and modes

An *axis* is one way a brand's values vary, such as the colour scheme. A *mode* is one value on one axis, such as `dark` (DEC-004 point 2). The foundations declare the shared axes: `colour-scheme`, with `light` and `dark`, and `contrast`, with `standard` and `high`. Both are value axes. The foundations declare no size axis.

- **A brand varies an axis** through a modifier of its Resolver document. It may leave out an axis it does not vary. It adds no axis of its own, and changes no default.
- **A value axis** changes only colours. A mode of a value axis that changes another value fails.
- **A piece** chooses the modes it is drawn in under its `modes`.

## Keys of combinations

A *combination* takes one mode on each axis. Its *key* names it (DEC-004 point 3).

- **A key names the modes that are not their axis's default,** each as `<axis>.<mode>`, the axes in the order of their names, joined by `+`.
- **The combination of every default** is `default`. No other key spells it, since every other key holds a `.`.
- **The shared axes give four keys:** `default`, `colour-scheme.dark`, `contrast.high` and `colour-scheme.dark+contrast.high`.
- **A key that names a default mode,** or names its axes out of order, is no key.
- **Adding an axis with a default** changes no key: every combination that existed takes the new axis's default, which its key leaves out.
- **Keys are kept in one order** wherever a list of them is kept: by their count of segments, then by their spelling. `default` comes first.

A key names a combination in the names of previews, exports and produced pictures, and in written code (*What is made from a piece*).
