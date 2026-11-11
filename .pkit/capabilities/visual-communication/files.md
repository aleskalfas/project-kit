---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/package.yaml
        - .pkit/capabilities/visual-communication/scripts/status.py
        - .pkit/capabilities/visual-communication/scripts/add.py
        - .pkit/capabilities/visual-communication/scripts/release.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/scripts/produce.py
        - .pkit/capabilities/visual-communication/scripts/export.py
        - .pkit/capabilities/visual-communication/scripts/mark-final.py
        - .pkit/capabilities/visual-communication/scripts/upgrade.py
        - .pkit/capabilities/visual-communication/scripts/take-up.py
        - .pkit/capabilities/visual-communication/scripts/new.py
        - .pkit/capabilities/visual-communication/scripts/prune.py
        - .pkit/capabilities/visual-communication/scripts/write-code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/root.py
        - .pkit/capabilities/visual-communication/scripts/_lib/location.py
        - .pkit/capabilities/visual-communication/scripts/_lib/config_text.py
        - .pkit/capabilities/visual-communication/scripts/_lib/viewing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/names.py
        - .pkit/capabilities/visual-communication/scripts/_lib/files.py
        - .pkit/capabilities/visual-communication/scripts/_lib/reading.py
        - .pkit/capabilities/visual-communication/scripts/_lib/records.py
        - .pkit/capabilities/visual-communication/scripts/_lib/libraries.py
        - .pkit/capabilities/visual-communication/scripts/_lib/shipped.py
        - .pkit/capabilities/visual-communication/scripts/_lib/copies.py
        - .pkit/capabilities/visual-communication/scripts/_lib/before_after.py
        - .pkit/capabilities/visual-communication/scripts/_lib/full_read.py
        - .pkit/capabilities/visual-communication/scripts/_lib/comparison.py
        - .pkit/capabilities/visual-communication/scripts/_lib/tokens.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pictures.py
        - .pkit/capabilities/visual-communication/scripts/_lib/notations.py
        - .pkit/capabilities/visual-communication/scripts/_lib/keys.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/layout.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/framing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/exports.py
        - .pkit/capabilities/visual-communication/scripts/_lib/current_copy.py
        - .pkit/capabilities/visual-communication/scripts/_lib/marking.py
        - .pkit/capabilities/visual-communication/scripts/_lib/rebranding.py
        - .pkit/capabilities/visual-communication/scripts/_lib/proposals.py
        - .pkit/capabilities/visual-communication/scripts/_lib/taking_up.py
        - .pkit/capabilities/visual-communication/scripts/_lib/stamping.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pruning.py
        - .pkit/capabilities/visual-communication/scripts/_lib/rendering.py
        - .pkit/capabilities/visual-communication/scripts/_lib/fingerprint.py
        - .pkit/capabilities/visual-communication/scripts/_lib/code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/briefs.py
        - .pkit/capabilities/visual-communication/schemas/defs.schema.json
        - .pkit/capabilities/visual-communication/schemas/config.schema.json
        - .pkit/capabilities/visual-communication/schemas/piece.schema.json
        - .pkit/capabilities/visual-communication/schemas/content.schema.json
        - .pkit/capabilities/visual-communication/schemas/brief.schema.json
        - .pkit/capabilities/visual-communication/schemas/brief.yaml
        - .pkit/capabilities/visual-communication/schemas/libraries.schema.json
        - .pkit/capabilities/visual-communication/schemas/library.schema.json
        - .pkit/capabilities/visual-communication/schemas/roles.schema.json
        - .pkit/capabilities/visual-communication/schemas/notation.schema.json
        - .pkit/capabilities/visual-communication/libraries/foundations/library.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/roles.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/components/figure.yaml
        - .pkit/capabilities/visual-communication/libraries/**/*.yaml
        - .pkit/capabilities/visual-communication/libraries/neutral/neutral.resolver.json
        - .pkit/capabilities/visual-communication/libraries/neutral/tokens/*.tokens.json
        - .pkit/capabilities/visual-communication/releases/foundations/releases.yaml
        - .pkit/capabilities/visual-communication/releases/neutral/releases.yaml
        - .pkit/capabilities/visual-communication/releases/*/1.0.0/**
        - tests/visual_communication_project.py
        - tests/test_visual_communication_pipeline.py
        - tests/test_visual_communication_layout.py
        - tests/test_visual_communication_tokens.py
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/steps.yaml
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/library.yaml
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/test-brand.resolver.json
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/tokens/base.tokens.json
        - tests/fixtures/visual-communication/libraries/test-brand/1.0.0/tokens/palette.tokens.json
        - tests/fixtures/visual-communication/libraries/test-notation/1.0.0/library.yaml
        - tests/fixtures/visual-communication/libraries/test-notation/1.0.0/notation.yaml
        - tests/fixtures/visual-communication/libraries/test-parts/1.0.0/roles.yaml
      record:
        - visual-communication:DEC-001#3
        - visual-communication:DEC-001#5
        - visual-communication:DEC-001#7
        - visual-communication:DEC-001#8
        - visual-communication:DEC-001#11
        - visual-communication:DEC-002#1
        - visual-communication:DEC-002#2
        - visual-communication:DEC-002#3
        - visual-communication:DEC-002#4
        - visual-communication:DEC-002#5
        - visual-communication:DEC-003#1
        - visual-communication:DEC-003#4
        - visual-communication:DEC-003#5
        - visual-communication:DEC-003#6
        - visual-communication:DEC-003#7
        - visual-communication:DEC-003#8
        - visual-communication:DEC-004
        - visual-communication:DEC-007#1
        - visual-communication:DEC-008#1
        - visual-communication:DEC-008#3
        - visual-communication:DEC-008#4
        - visual-communication:DEC-008#5
        - visual-communication:DEC-008#6
        - visual-communication:DEC-008#7
        - visual-communication:DEC-009#7
        - visual-communication:DEC-010#1
        - visual-communication:DEC-010#2
        - visual-communication:DEC-010#3
        - visual-communication:DEC-010#5
        - visual-communication:DEC-010#7
        - visual-communication:DEC-011#1
        - visual-communication:DEC-011#2
        - visual-communication:DEC-011#3
        - visual-communication:DEC-011#4
        - visual-communication:DEC-011#6
        - visual-communication:DEC-012#1
        - visual-communication:DEC-012#6
        - visual-communication:DEC-013
        - visual-communication:DEC-014#1
        - visual-communication:DEC-014#2
        - visual-communication:DEC-014#5
        - visual-communication:DEC-015#2
        - visual-communication:DEC-015#4
        - visual-communication:DEC-016#3
        - visual-communication:DEC-017#1
        - visual-communication:DEC-017#2
        - visual-communication:DEC-017#3
        - visual-communication:DEC-017#5
        - visual-communication:DEC-017#6
        - visual-communication:DEC-017#7
        - visual-communication:DEC-017#8
        - visual-communication:DEC-018#4
        - visual-communication:DEC-019#1
        - visual-communication:DEC-019#2
        - visual-communication:DEC-019#3
        - visual-communication:DEC-019#4
        - visual-communication:DEC-019#6
        - visual-communication:DEC-019#7
        - visual-communication:DEC-019#9
        - visual-communication:DEC-019#10
        - visual-communication:DEC-019#11
        - visual-communication:DEC-020#7
        - visual-communication:DEC-021#1
        - visual-communication:DEC-021#2
        - visual-communication:DEC-022#1
        - visual-communication:DEC-022#2
        - visual-communication:DEC-022#3
        - visual-communication:DEC-022#8
        - visual-communication:DEC-025#1
        - visual-communication:DEC-025#2
        - visual-communication:DEC-025#3
        - visual-communication:DEC-025#4
        - visual-communication:DEC-025#5
        - visual-communication:DEC-025#8
        - visual-communication:DEC-025#9
        - visual-communication:DEC-025#10
        - visual-communication:DEC-029
        - visual-communication:DEC-030#6
        - visual-communication:DEC-034#3
        - visual-communication:DEC-035#1
        - visual-communication:DEC-035#2
        - visual-communication:DEC-035#3
        - visual-communication:DEC-035#4
        - visual-communication:DEC-035#6
        - visual-communication:DEC-035#7
---

# The files of the visual work

Where a project's visual work lies, what each of its files holds, and who writes each one. The examples come from the shipped foundations library, from the capability's test files, and from the reference instance of the brief's schema. The test brand `test-brand`, the test libraries `tests` and `test-parts` and the test notation `test-notation` exist for the tests only.

## Contents

<!-- pkit:contents -->
- [The location](#the-location)
- [What the location holds](#what-the-location-holds)
- [Names, ids and the binding](#names-ids-and-the-binding)
- [A piece](#a-piece)
- [Picture files](#picture-files)
- [The library folder](#the-library-folder)
- [Brands](#brands)
- [Notations](#notations)
- [Keys of combinations](#keys-of-combinations)
<!-- /pkit:contents -->

## The location

The *location* is the one folder of the repository that holds the project's visual work: its libraries, its pieces, its declarations of code and its fonts (DEC-002 point 1). None of it lies in the capability's own folder. The default location is `visual/`, at the repository's top.

### Where it is recorded

The capability's configuration, `.pkit/capabilities/visual-communication/project/config.yaml`, records the location under the key `location`, as a path relative to the repository's top. Beside it, the configuration may name a browser ([The browser](#the-browser)), and holds nothing else. A command records the location the first time it writes there, so a later change of the default moves no recorded location (DEC-002 point 1). A configuration as a command creates it:

```yaml
pkit_schema: visual-communication:config
schema_version: 1

location: visual
```

The command adds the line as text at the end of the file. It keeps every other byte: comments, order, line endings and a byte-order mark. Where the file records another location already, the command refuses, since a command never moves the location. To move the work, move the folder and change the `location:` line by hand.

A `location:` line with no value, such as `location:` alone or `location: null`, records no folder. Every command refuses it, and the check reports it as `location`, each saying how to mend it: write the folder that holds the work there, such as `location: visual`, or remove the line.

### How a command finds it

- **A command that writes in the location** (`add`, `render`, `produce`, `export`) reads `location:`. Where none is recorded, it takes `visual/` if that folder is absent, holds no file, or holds the marker. It records `visual` before its first write in the location. Otherwise it refuses, naming the folder.
- **`--location <path>`** names the location where none is recorded. The path is relative to the working directory, or absolute. The command records it. `--location visual` confirms the default.
- **With a location recorded,** a command refuses a `--location` that names another folder. It also refuses when the recorded folder is missing.
- **The check and the commands that only read** take the recorded location. With none recorded, they take `visual/` only where it holds the marker; otherwise there is no visual work. A recorded location whose folder is missing fails.

The *marker* tells that a folder holds the capability's work. It is the list of libraries, `libraries/libraries.yaml`, or any YAML file whose `pkit_schema` names one of the capability's schemas.

A location is refused when it is the repository's top itself, lies outside the repository, lies under `.pkit/` or under any folder whose name starts with `.`, is reached through a symbolic link, or is a file. The configuration's path is refused when it is absolute, holds a `\`, or has an empty segment, such as a trailing `/`.

The commands list the location's files as git sees them: tracked files, and untracked files that git does not ignore. A file git ignores is no part of the visual work. A symbolic link is never listed. Outside a git repository, the commands walk the folder.

### The browser

The configuration may name the browser of the viewing step, under the key `browser`, in place of the first browser it finds (DEC-020 point 7). Name a pinned build this way, for one:

```yaml
browser: ~/browsers/chromium/chrome
```

- **The path** names the program, not its folder. It is absolute, or starts `~/` in your home folder, or is relative to the repository's top.
- **Only here.** No flag and no environment variable names a browser. A command starts that program with no prompt, so the choice lies in a file the project reviews.
- **No command writes it.** Write the line by hand, and remove it to go back to the first browser found.

## What the location holds

The location holds four folders: `libraries/`, the library folder; `pieces/`, one folder for each piece; `code/`, one file for each declaration of code; and `fonts/`, the fonts a brand names by their hash. What people write lies apart from what commands rewrite (DEC-002 point 5). No command changes a content file, what a brief says, or a declaration. Two commands write a new piece's files, each into a folder of its own and never over a file: `pkit visual new` stamps a piece's first files from a person's choices ([A piece](#a-piece)), and `pkit visual take-up` copies a final piece ([The lock](#the-lock)). Three commands change the library folder, and no other does:

- **`pkit visual add`** changes the copies of a library the capability ships (DEC-013 point 5). It copies a version the capability ships, whole, into a folder of its own. It writes over a version the library folder holds only to bring a copy not yet released up to what the capability ships under its number, or to restore a released copy to its hash. No install, sync or upgrade of the capability writes in the location, so a shipped library reaches it only through this command (DEC-003 point 5).
- **`pkit visual release`** writes into a version of the project's own library the release it needs ([`library.yaml`](#libraryyaml)).
- **`pkit visual prune`** removes a version that lies behind, whole ([A version that lies behind](#a-version-that-lies-behind)).

The table names the schema each file binds to (see [The binding](#the-binding)), and who writes it.

| File, in the location | Schema | Written by |
|---|---|---|
| `libraries/libraries.yaml` | `libraries` | a person; `pkit visual add` lists each version it copies, and lists as released each copy it replaces with a released version; `pkit visual release` lists as released each version it releases; `pkit visual prune` takes out the entry of each version it removes |
| `libraries/<library>/<version>/`, a version's folder | each file's own | the library's owner; `pkit visual add` copies a version the capability ships, whole; `pkit visual prune` removes a version that lies behind, whole |
| `libraries/<library>/<version>/library.yaml` | `library` | the library's owner; `pkit visual add` copies, replaces or restores a version the capability ships; `pkit visual release` writes the release a version needs |
| `libraries/<library>/<version>/roles.yaml` | `roles` | the library's owner; `pkit visual add` copies, replaces or restores a version the capability ships |
| `libraries/<library>/<version>/notation.yaml` | `notation` | the library's owner; `pkit visual add` copies, replaces or restores a version the capability ships |
| `libraries/<library>/<version>/components/<component>.yaml` | `component` | the library's owner; `pkit visual add` copies, replaces or restores a version the capability ships |
| a brand's token files, Resolver document and fonts | none: DTCG, or a font's own format | the brand's owner; `pkit visual add` copies, replaces or restores a version the capability ships |
| `libraries/<library>/<version>/pictures/<file>`, a picture file | none: a PNG or a JPEG ([Picture files](#picture-files)) | the library's owner; `pkit visual add` copies, replaces or restores a version the capability ships |
| `pieces/<piece>/piece.yaml` | `piece` | a person; `pkit visual new` stamps it; `pkit visual render` and `pkit visual upgrade` rewrite its `lock` alone; `pkit visual mark-final` rewrites its `state` and `lock` alone |
| `pieces/<piece>/content.<language>.yaml` | `content` | a person; `pkit visual new` stamps it with each field of the top it can leave empty, empty |
| `pieces/<piece>/brief.yaml` | `brief` | a person ([The brief](#the-brief)); `pkit visual new` stamps it holding its binding alone |
| `pieces/<piece>/components/<component>.yaml` | `component` | a person, or a script of the project's own (DEC-001 point 8) |
| `pieces/<piece>/pictures/<file>`, a picture file | none: a PNG or a JPEG ([Picture files](#picture-files)) | a person |
| `pieces/<piece>/produced/<output>/record.yaml`, and a PNG for each variant | `produced-record` | `pkit visual produce` |
| `pieces/<piece>/findings.yaml` | `findings` | `pkit visual render`, of a piece that is not final; `pkit visual upgrade` |
| `pieces/<piece>/exports.yaml` | `exports` | `pkit visual export` and `pkit visual upgrade`; `pkit visual mark-final` adds the version handed out |
| `pieces/<piece>/current-copy/<file>` | none: a copy of a file an export made | `pkit visual export`, of a published piece; `pkit visual upgrade` |
| `pieces/<piece>/handed-out/<file>` | none: a file an export made | `pkit visual mark-final`, which moves it there from the clone's local folder |
| `pieces/<piece>/`, a new piece's folder | each file's own | `pkit visual new`, which stamps its first files; `pkit visual take-up`, which copies it from a final piece, but for that piece's past, and writes its `piece.yaml` |
| `code/<name>.yaml` | `code` | a person |
| `fonts/<file>` | none | a person, who commits the font |

The code that `pkit visual write-code` writes lies where its declaration names, with its record beside it. A component's file is described in *Components*; produced pictures, exports, a current copy, declarations of code and the code itself in *What is made from a piece*; `findings.yaml` in *What the check reports*.

### A version that lies behind

`pkit visual prune` removes each library version that lies behind, with its entry in the list (DEC-019 point 9). A version lies behind where all of these hold:

- **No lock names it.** That is a piece's lock in any state, written code's, or the lock of the version that wrote a piece's current copy (*The current copy* in *What is made from a piece*).
- **No lock that moves can still reach it.** A draft's lock moves, pinned or not, and so do a published piece's and written code's. Each of them that names the version's major names a newer version, or none names that major.
- **A final piece's lock** never moves, and an export's is only read. So each keeps only what it names.
- **A newer version of its major serves in its place.** The installed capability reads it, and it is released where the version is.
- **It holds no unreleased work.** It is no version of the project's own library not yet released.

So the command spares each of these, though no lock names it:

- a version the list does not name, since it cannot tell what the version holds;
- a version of the project's own not yet released. A copy of a shipped version not yet released goes where it lies behind;
- a version above a lock that moves, in that lock's major, since the lock may still move to it;
- a library's last version, since nothing newer stands. Taking a library out of the project is a person's act;
- the newest version of each major that the installed capability reads. A piece's first lock takes it, and so does a library whose `builds-on` names that major ([`library.yaml`](#libraryyaml));
- the newest release of each major, which the library's next release is compared with ([What a release compares](#what-a-release-compares)).

So in a major that no lock that moves names, only the newest version stays. The command reads no further:

- **A version only a kept export names goes.** The command names each such export. Marking one final leaves a finding until the version is back ([The lock](#the-lock)).
- **The working tree alone.** A lock on another branch that names a removed version fails the check once merged. Restoring the version mends it.
- **No version by name.** To remove a version it spares, take out its folder and its entry by hand. The check then reads what that leaves.
- **A way back.** A version removed comes back from version control, once committed. A shipped one comes back through `pkit visual add` too.

It removes each folder whole, then takes each entry out of the list as text ([The list, `libraries.yaml`](#the-list-librariesyaml)). It stages nothing, so the removal is a diff to review. Land it as a change of its own, after any proposed move of a lock lands, since a look back may draw its before from a version it removes.

### The clone's local folder

`.pkit/capabilities/visual-communication/project/local/` holds what a command makes that is never committed (DEC-002 point 1). The capability's `package.yaml` declares the folder local to each clone, so git ignores it. It holds:

- `previews/<piece>/`: the SVG previews `pkit visual render` draws;
- `exports/<piece>/`: the files `pkit visual export` and `pkit visual upgrade` make, but for the version `pkit visual mark-final` moved into the piece's folder;
- `before-after/<piece>/`: a piece's scenes drawn around a change to its lock's versions, in `before/` without the change and in `after/` with it;
- `handover/<piece>/`: what `pkit visual produce` hands a producer, and what the producer writes, until the command keeps it in the piece's folder;
- `look/<piece>/`: the images, the frames and the report `pkit visual look` writes.

*What is made from a piece* names the files in each. While `pkit visual look` runs, the folder also holds a temporary folder of the fonts it hands its tool, which the run removes.

## Names, ids and the binding

### Shapes

| Shape | Pattern | Who takes it |
|---|---|---|
| name | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, and none of `y n yes no on off true false null` | a library, a component, a field, an option and its words, a state, a concept, a layout, a slot, an exposed part or point, an axis, a mode, a piece, a produced output, a declaration of code |
| token path | segments `^[a-z0-9]+(-[a-z0-9]+)*$` joined by `.` | a role or a token; a segment may start with a digit, as in `space.3` |
| id | `^[A-Za-z][A-Za-z0-9_-]*$`, and none of `y n yes no on off true false null` in any case | an item, or another component content places, that something names |
| language | `^[a-z]{2,3}(-[a-z0-9]{2,8})*$` | a language of a piece, such as `en` or `pt-br`; always lower-case |
| use | `<library>/<component>`, or `piece/<component>` | a component, read with its library; never a version |
| concept | `<notation>/<concept>` | a concept of a notation, read with the notation; never a version |
| version | `X.Y.Z`, X at least 1 | a library version |
| release | `X.Y.Z` | a release of the capability |
| bare name | `^[a-z][a-z0-9-]*`, then `.png`, `.jpg` or `.jpeg` | a picture file, by its file name alone ([Picture files](#picture-files)) |

So a name holds no `.`, `/` or `#`, and starts with a letter, so YAML never reads it as a number. Nor is a name or an id a word that a YAML reader takes for a yes or a no, or for nothing, such as `no`, `on` or `null`, so either keeps its meaning wherever it is written unquoted, as a key or as a value. The schemas and the commands refuse the same words. The names that enter a token path or a key take the name shape, so a code writer can spell them in code (DEC-004 point 4).

### Reserved words

- **In every mapping that places a component,** an item included: `id`, `use`, `concept`, `state` and `override`. No component declares a field of these names, so each means the same everywhere (DEC-002 point 4).
- **`pkit`** is kept for the methodology's container, at a content file's top and in every mapping that places a component. No component declares a field of that name, and the capability never reads or writes anything under it (DEC-002 point 4).
- **At a file's top:** `pkit_schema` and `schema_version`, the binding.
- **Library names:** no library takes `piece`, the word by which `use` names the piece itself, nor `component`, the token group of component tokens, which holds no shared role. Nor does a library take the name of a top group of the shared roles, such as `space`, `font` or `family` (DEC-004 point 7).

### The binding

Every file of the capability's format names its schema and its format number in its first fields:

```yaml
pkit_schema: visual-communication:piece
schema_version: 1
```

The schema is `visual-communication:<kind>`, one of `config`, `piece`, `content`, `brief`, `library`, `component`, `roles`, `notation`, `libraries`, `produced-record`, `code-record`, `findings`, `exports` and `code`. The format number is `1`, shared by every schema of the capability (DEC-003 point 1). The command that creates a file writes both fields, and a person who writes a file by hand writes them too (DEC-002 point 3).

No path binds a file, and the capability writes no line that points an editor at a schema (DEC-002 point 3). The core's data validation checks each bound file's shape against the schema it names. The check finds the configuration, and each file of the location's table that has a schema, by its name and place. It reports one whose binding is missing or names another schema (*What the check reports*). Token files, the Resolver document, fonts and pictures carry no binding: each keeps its own format.

### How the files are read

- **YAML** is read as YAML 1.2. So `no`, `yes` and `on` are text, and `2025.10` is a number: quote a value that must stay text. A `%YAML` line that names another version is refused. A duplicate key, a second document, a key that is not text, an infinity, a binary or a set is refused too. A date or a time is read as the text it is written as.
- **JSON** is read as its value. A duplicate key, `NaN` and the infinities are refused.

## A piece

A *piece* is one finished item of visual work, such as a figure (DEC-001 point 3). Its sources are one folder, `pieces/<piece>/`, named with the name shape. The folder holds `piece.yaml`, a content file for each language, the piece's local components, and its picture files in `pictures/` ([Picture files](#picture-files)). It may hold the piece's brief too ([The brief](#the-brief)).

`pkit visual new <piece>` stamps a new piece's first files from a person's choices: its `piece.yaml`, a draft with no lock; a content file for each language, holding each field of its top it can leave empty, empty, a deck's or a site's pages being one page; and a brief holding its binding alone. Its first render writes the lock, as for a piece written by hand ([The lock](#the-lock)).

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
| `notations` | no | The notations its content names concepts from, each by its library's name, once ([Notations](#notations)). |
| `languages` | yes | The languages of its content, each once. The first is its source language. Each has its `content.<language>.yaml`. |
| `audience` | yes | Who the piece is for, in words. |
| `shown` | yes | Where the piece is shown, in words. |
| `explains` | yes | `true` where the piece explains, rather than only shows. |
| `exports` | yes | The formats an export makes, of `svg`, `svg-modes`, `pdf` and `html` (*Exports* in *What is made from a piece*). `svg` and `svg-modes` write files of one name, so a piece names one of them. `svg-modes` takes no mode of no pair it reads that parts the piece's combinations (DEC-018 point 4). |
| `state` | yes | The piece's stage of life, `draft`, `final` or `published`, which says who moves its lock ([The lock](#the-lock)). `pkit visual mark-final` sets `final`. A published piece owes a current copy, which each of its exports writes (*The current copy* in *What is made from a piece*). |
| `modes` | no | For each axis, the modes the piece is drawn in. An axis it leaves out is drawn in its default. |
| `pinned` | no | `true` pins a draft's lock. No other state reads it. |
| `produced` | no | Each picture a producer makes for the piece (*Declaring a produced output* in *What is made from a piece*). |
| `accept-losses` | no | The losses of a plugin a person accepted (*Accepting a loss* in *What is made from a piece*). |
| `copy-place` | no | The folder a published piece's current copy lies in, in place of the piece's folder. It is a path from the repository's root (*The current copy* in *What is made from a piece*). |
| `lock` | no | The version of each library the piece uses. A draft's render writes it. |

### The lock

A piece's *lock* names one version of each library it uses, those they build on included (DEC-001 point 7). A piece uses its top's library, its brand, each notation it names, and each library its content names in a `use`, other than `piece`. Through `builds-on`, it also uses every library those build on. The lock must name `foundations`, since a brand's values are read against the foundations' roles. The test brand brings it in: it builds on `foundations` 1.

**A draft** that is not pinned moves its lock at each render (DEC-003 point 8). The render takes the newest versions the location holds that the installed capability reads and that fit together. It stays within the major each library's locked version has, the library's *line*. A library the lock does not name yet takes its newest version of any major that fits. A library the piece no longer uses leaves the lock. A draft may lock a version not yet released. To take a new major on purpose, write a version of that major in the lock; the next render moves within it.

**Versions that fit together** build on one version of each library, since a piece locks one version of each. Where no combination does, the render refuses and names the conflict, such as two libraries that build on two majors of one library. Placed under the versions, the piece must also keep what it has under its lock (DEC-010 point 2, DEC-011 point 4):
- No item carries a key that both its component and its list declare, where it carries none under the lock.
- Each end of a tie that the lock finds is found: its item is drawn once, on the tie's page.

A clash or a lost end the piece shows under its lock holds nothing back, such as one in a tie just written. Nor does one under a library the lock does not name yet, as in a new piece's first lock. It is a finding (*Content against components* in *What the check reports*).

**The search** judges each whole combination it reaches by placing the piece under it, with no scene computed. It places it in each language, at each key over the size axes the piece names. It tries the newest versions first. It takes the piece's own libraries in the order of their names, then each library they build on, as it reaches it. Where a combination does not fit, it backs off first the last library in that order that the fault implicates. A clash implicates the libraries of the item's component and of each component the item lies in. A lost end implicates each library whose components the placing read. The render states each version it held back, with the item and the key, or the tie and the end. A fault at some size keys alone is stated for each of them, naming it.

A library moves no lower than the version the lock names while versions at or above those the lock names fit together. Where none do, it may move lower, within its line, and so may a library whose locked version the location lacks or the capability cannot read. The render states each library that moves below its lock.

**The search's bounds.** It tries at most 10 000 versions. Past that bound it refuses, naming the libraries it was choosing among. Name the line of each in the lock, or take the versions no piece needs out of the library folder, and render again. It also judges at most 50 combinations. Past that bound it keeps the lock, with the newest version that fits of each library the lock does not name yet. It states that, naming the libraries it was choosing among. Move the lock by hand, or take the versions no piece needs out of the library folder.

**A pinned draft,** `pinned: true`, keeps its lock: a render checks it and never changes it. The lock must name every library the piece uses, each a version the location holds and the installed capability reads, and they must fit together. A pinned piece with no lock is refused: unpin it for its first render. To move a pinned lock, change it by hand, or unpin the piece and render it. A copy of a final piece starts as a pinned draft, and may hold words later than the version handed out (DEC-003 point 8).

**A final piece** was handed out, and its lock never moves. **A published piece** stays in use where others rely on it. Its lock moves only through a change a person reviews, with a before-and-after of each page it changes, or when marked final (DEC-003 point 8). A render moves neither lock, whatever newer versions the location holds, and reads no `pinned` of either piece. It checks such a lock as it checks a pinned draft's, and its refusal says the piece's state. A published piece with no lock is refused: set it back to a draft for its first render. A final piece with no lock is refused too: write back the lock of the version handed out, which is no move of it.

**Final to every command.** A piece is final where its `state` says so, or where its record of exports names a version handed out. Where that record cannot be read, as on a conflicted merge, every command takes the piece as final. So setting `state` back from `final` holds only where no version is handed out, as for a piece set final by hand. No state leads out of final, and `pkit visual take-up` copies a final piece for new work (DEC-017 point 5).

**Marking a piece final.** `pkit visual mark-final <piece> <version>` names the version handed out (DEC-017 points 1 and 2). No change since that version stops it.

- **The lock.** It puts back the lock that version was made under, read from its fingerprint, whatever lock the piece holds. A published piece's lock goes back the same way, with no before-and-after.
- **Only the lock.** To bring the sources back too, restore them from history first.
- **What else changed.** It reads the piece as the version's fingerprint does, with the lock put back (*The input set of each kind* in *What the check reports*). It names each input that still does not verify.
- **A version made before an export left fields out of `piece.yaml`.** It read that file whole, so a pin or a change of state reads as a change. The run says the file was read whole.
- **A number or a date the version let through** is named too, and stops nothing. No check judges a final piece's drawing.
- **The version's files.** Each moves from the clone's local folder into `handed-out/`, in the piece's folder, under the name it carries. Commit them with the piece. Every other version stays in the clone that made it.
- **What it writes.** It writes `state` and `lock` as text, every other byte of `piece.yaml` kept, and the version in the record (*The record of exports* in *What is made from a piece*).
- **A lock that no longer holds** stops nothing, such as one that names a version gone, changed or not released. The run says so, and the piece carries the finding its lock takes.
- **A current copy** stays where it lies. The run says so where the version named did not write it.
- **A piece set final by hand** takes the command, which names its version.
- **It refuses** a file of the version that is missing from the clone's local folder, or whose hash differs from the record's, naming each. So a version is marked in the clone that made it.
- **It refuses** a version whose fingerprint is missing or no longer matches its own inputs, a piece that has a version handed out, and anything else that lies at `handed-out/`.
- **A mark made in error** is undone by reverting its change, and moving its files back to the clone's local folder by hand.

**Taking a final piece up again.** `pkit visual take-up <piece> <name>` copies a final piece as a new piece, a draft with its lock pinned, under a name no piece holds (DEC-017 point 8). So it draws as the piece it copies until a person moves its lock.

- **What it copies.** The piece's folder whole, as git sees it, but for what only its past holds: `exports.yaml`, `findings.yaml`, `handed-out/` and `current-copy/`.
- **The new `piece.yaml`.** It sets `state: draft` and `pinned: true`, and writes the lock of the version handed out, read from its fingerprint. It drops `copy-place`, since a draft writes no current copy. Every other byte stays, such as who the piece is for.
- **Later words.** Only the lock comes back (DEC-017 point 1). Where the sources changed since that version, the copy holds them as they stand. The run names each change, and the copy's lock may need a move before it draws.
- **The final piece** stays as it was.
- **It refuses** a piece with no version handed out. A piece set final by hand is one: mark it final first. It refuses a name taken or not a piece's name.
- **It refuses** a version whose lock cannot be read, and a file it copies or writes that is reached through a link.
- **It writes as one change.** A write that fails leaves no part of the new piece.

**Moving a published piece's lock.** `pkit visual upgrade <piece>` proposes the move (DEC-019). A *proposal* is what one run leaves in the working tree. The run commits nothing, makes no branch and opens nothing on a work tracker. Landing it is the review's yes. Discarding it is its no, and leaves only the version's numbered files in the clone's local folder.

- **What it carries.** The lock, written as a render writes it, and the findings record of a render under it, with no preview. A new version in the record of exports, made under that lock. The current copy written from it (*The current copy* in *What is made from a piece*).
- **A piece in another state** is refused. A draft's render moves a draft's lock, a hand moves a pinned one, and nothing moves a final piece's.
- **The lock it starts from** is the one `piece.yaml` holds, whoever wrote it. So it serves a piece an export refused for a lock written by hand.
- **The search** works as a draft's render does, among released versions alone. It stays within the lock's majors, and takes versions that fit. It states each newer version it did not take, with why.
- **A version named.** Each `<library>@<version>` moves what it names, and only what that needs. It may lie below the lock. A new major comes only by a name, or by a lock written by hand.
  - A name goes past a clash or a lost end, and each stands as a finding.
  - A name goes past nothing else. A version the project does not hold, one not released and one the installed capability cannot read are refused. So are libraries that build on two majors of one library.
- **No library version travels in it.** It moves only to versions the library folder holds. Bring one in first, or in the change that lands the proposal.
- **Nothing to move.** It would propose the lock the piece holds, and the version that wrote the copy was made under that lock. It says so and writes nothing.
- **An edit since the copy.** It compares the piece with the version that wrote its copy, reading "changed" as marking final does. It also leaves out the files of the lock's library versions, so a version gone from the project stops nothing. It stops, naming each input that changed.
  - The plain way on is an export under the lock the copy holds. The run then finds no edit.
  - Where the edit needs the move, `--edited <input>` names each input. A file goes by its path in the piece's folder, a font as the refusal writes it.
  - An input nobody named still stops, and the run prints the line that names them all.
- **A stale picture.** Under the moved lock a picture may read other values. The run stops, naming each output and what changed. It runs no program, since a program reads under the lock the piece holds.
  - `--use-stale <output>` carries the picture as it is. The picture and the copy made over it ask for attention until they are made again.
  - To make it again, run `pkit visual produce`, then an export, once the run has moved the lock. Land the change after the run or after that export. Between them the copy is stale, which fails.
  - Or write the lock by hand, run the program, then run the command, naming the picture's `record.yaml` with `--edited`. No copy is then made over a stale picture.
- **A fingerprint it cannot read** refuses, and names the record. Restore that record as version control last held it.
- **No copy standing.** Where no file of the copy stands, or the record holds no copy of the piece's own, the run goes on. It writes the copy whole and says no file stood, so the change shows only an after.
  - Where some files stand, each of those shows its two sides, and each missing one its after alone.
  - A file at a place the piece came to name since reads as new too, and the run names what it leaves behind.
  - An edit still stops the run where a version wrote the copy.
- **A finding that fails.** A version fits by what a lock can hold, not by how a page draws. So a move may bring a finding that fails, such as text that overflows. The run names each and stops on none, and each holds the landing. Mend the content in the same change and run an export, or discard the proposal.
- **The rest of an export's rules** hold the run. Only the refusal of a lock that differs does not (*What refuses an export* in *What is made from a piece*). Every stop comes before any write.
- **After it,** the version that wrote the copy was made under the lock the piece holds. So the next export runs, and the check raises no finding for the move itself.

**A move onto another brand.** A person changes a piece's `brand`, and the command that moves its lock onto the new brand says what does not follow it (DEC-025 point 8). The brand a lock names is the one no other brand it locks builds on. So an edition locked with its base names the edition.

- **Who says it.** The render of a draft that is not pinned says it, and so does `pkit visual upgrade`. An upgrade also says it where the lock its copy was made under names another brand. `pkit visual mark-final` says it where the lock it puts back names another brand than the lock it replaces.
- **The before-and-after says it too,** looking ahead or back, wherever its two locks name different brands. So a reviewer of a lock written by hand reads it there.
- **What it names,** in each language, each with its image's trace id (*Trace ids* in *Components*):
  - each picture file of the piece a scene shows, whether the content or a local component names it ([Picture files](#picture-files));
  - each picture role a part shows that the new brand gives no file, though the part is not drawn ([Picture roles](#picture-roles)).
- **At some sizes alone.** One shown or left out at some keys over the size axes alone names those keys ([Keys of combinations](#keys-of-combinations)).
- **What it leaves out.** A library's own file is part of the form its owner chose for every brand. A produced picture is no picture file.
- **Said, never kept.** No record keeps it, and the check is silent on it. A move that keeps the brand says none of it.

A copy not yet released that a pinned or a published lock names may fall behind what the capability ships under its number. `pkit visual add` replaces it only where a person names each pinned draft, each published piece and each declaration that locks it (DEC-013 point 5). Naming it is the move on purpose: the lock keeps its number, and what it draws changes only then. The run that leaves the copy draws the piece both ways first, so the person sees what the move changes (DEC-003 point 8). Under a final piece's lock it replaces such a copy with no piece named, since that changes none of the piece's exports.

The render writes the lock into `piece.yaml` as text, as a top-level block mapping, one library a line, in the order of their names. Every other byte of the file stays: comments, order, line endings and a byte-order mark. Where the result would not read back as the file with that lock, the render refuses: write `lock:` as a block mapping, one library a line.

### Content files

A content file, `content.<language>.yaml`, holds what the piece shows in one language. It names no position, size, colour or font. It chooses only among what its libraries declare: components, layouts, options, states, concepts, roles and the words of a field's run styles (DEC-001 point 3). A second language is a second file of the same shape, with the same ids. A field's runs are its value, so their number, order and styles may differ between languages, as its text does. The content from the capability's tests for the piece above:

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
- **A mapping with `use`** places the component it names. Its other keys are that component's fields and options, and the reserved keys. A field the component fills through a slot, as the figure's `body`, takes such a mapping. So does a list's *component field*, where the component that repeats over the list declares one, though it places nothing there: it names the component that draws each item of the list that names none (DEC-010 point 1). It gives words for that component's options, and perhaps `concept`, `state` and `override`, and no id and no field of that component, since an id names one thing and a field holds what one item shows.
- **A list the component repeats** holds items, each a mapping. The component names the component that draws an item by default, `tests/card` for `tests/steps`. Where the list has a component field, the component it names draws each item that names none, and the item takes each key the field gives that it does not give itself. An item may name its own with `use`, and then takes nothing from the field. An item may also give its list's *arrangement fields*, each one of the words the component declares for it, such as `span: wide`; an item that leaves one out takes its first word (DEC-010 points 2 and 3).
- **A page of a top whose layouts are its pages' forms** is a mapping in the list the top marks as holding its pages, `slides` for the foundations' `deck`. It names one of the top's layouts with `layout`, and holds that layout's slots and the reserved keys, nothing else: `{id: cover, layout: cover, title: Building with AI}`. Or it names the component that draws it with `use`, and its other keys are that component's. Every page names one or the other, and none takes a layout by default (DEC-010 point 5). How a layout declares its slots is in *Components*.
- **`use: piece/<name>`** names a local component, `components/<name>.yaml` in the piece's folder.
- **A picture file** of the piece is named by its bare name, in a field an image shows, such as `photo: team.jpg` ([Picture files](#picture-files)). Each language names its own file, as it gives its own text. A picture every language shows is named in each content file.
- **An option** takes one word from the list the component declares, such as `spacing: wide` on `tests/steps`. An option that names an item takes `{item: <id>}`, or `{item: <id>, point: <name>}` for a point the item exposes.
- **A tie's ends.** In a list of ties, every item is a tie, and gives both of its list's end fields (DEC-011 points 1 to 3). Each takes the shape of an option that names an item: `{item: <key path>}`, or `{item: <key path>, point: <name>}`. The *key path* starts at a field of the mapping that holds the tie's list. It names each field that leads to the item, joined by `.`, and in each list the item by its id, as `[<id>]`. It writes the keys the content file writes, so a component that passes a list on under another name changes nothing in it. `right[groups].groups[project-management].items[doc-check]` names an item of a list inside a component that the list `right` holds. An end never names a tie, the two ends never name one item, and neither leads through the other. An end's quotes in a flow mapping are in *Components*.
- **`state`** names a state the component declares, such as `state: marked`.
- **`override`** points a painted part of the component at another role, by its token path, never at a value or a component token. `override: {b: accent}` paints the part `b` with `accent`.
- **`concept`** names what the component it places stands for: a concept of a notation the piece names, as `<notation>/<concept>`, such as `concept: test-notation/store` ([Notations](#notations)). The concept gives the component its colour family; how a component paints with its family is in *Components*.
- **A field of runs,** one its component marks as taking runs (*Components*), takes text, as any field of text does, or a list of *runs*: spans of its text, each in a style of its own (DEC-012 point 1). A run is text, set in the field's first style, or a mapping of `text`, which holds text, and perhaps `style`, one of the words of the field's run styles, and `concept`, written as above, which gives the run its colour family. The format fixes these three keys on a run, which places no component, so a run holds no other key and no reserved key binds it. The runs' texts are joined as written, with nothing between them. YAML drops the spaces at the edges of a plain text, so a run with a space at its edge is written in quotes, and so is a run whose text YAML would read as another value, such as `null` or `true` ([How the files are read](#how-the-files-are-read)). The field is filled where one of its runs holds text. A run carries no id: a list of runs holds runs, not items, so no rule of ids reaches it. A terminal's line, its command in the field's first style: `line: [{text: "$ ", style: prompt}, pkit visual render deck, {text: "  # draws every page", style: comment}]`.
- **An id** marks an item, or another component the content places, that another part of the piece names (DEC-001 point 3). It is unique in its list. Each list holds the same ids in every language as in the source language, in any order.

Each key of a mapping that places a component must be a field or an option of that component, an arrangement field or an end field of its list where the mapping is an item, or a reserved key. A key that both an item's component and its list declare is read by neither (DEC-010 point 2, DEC-011 point 1). A key of a page in a layout must be a slot of that layout, `layout`, or a reserved key. How a component declares its fields, options, states, layouts, slots and lists is in *Components*.

### The brief

A piece may keep one *brief*, `brief.yaml` in its folder. It says what the piece must show, and why its design is as it is (DEC-029). The content says what the piece shows. The brief says what the content does not: what each picture must make visible, what the piece is for, and why each choice of its design was made. It is written for whoever makes or reviews the piece, and no reader of the piece sees it. It has no language: one brief serves every language of the piece, written in the language its makers work in, and is never translated. Nothing that draws or checks a piece needs one.

A brief of a deck whose slide `layers` shows how the levels of a method rest on each other, trimmed from the reference instance:

```yaml
pkit_schema: visual-communication:brief
schema_version: 1
piece:
  goals:
    - A newcomer can say where a decision lives, and which layer carries it out.
pages:
  cover:
    takeaway: The talk is about how the method's parts fit together.
  layers:
    relations:
      - text: >-
          Each level rests on the one below it, and the decisions are the source of all
          the others.
        relates: [visual.levels]
    reasons:
      - aspect: form
        about: visual.levels
        text: >-
          A stepped pyramid, narrowest at the top, so that width carries the order and the
          top reads as the source.
        principle:
          name: Ordered visual variables
          source: Jacques Bertin, Semiology of Graphics
```

- **`piece`** is the part for the whole piece. It holds what concerns the piece, or more than one of its pages. A piece of one page, such as a figure, keeps all of its brief here, its takeaway included. So does the intent of a page not yet in the content. Whoever starts the page gives it its id in the content, and its part can then lie under `pages`.
- **`pages`** holds a part for each page the brief speaks of, keyed by the id the page carries in the content, such as a slide's id. A page the brief names carries an id, as anything another part of the piece names does ([Content files](#content-files)).

Each part may hold these fields:

| Field | What it holds |
|---|---|
| `relations` | What a picture must make visible between the parts it shows, such as levels that each rest on the one below, a flow read one way, or kinds of one thing kept apart. Each relation gives its `text`, and perhaps `relates`, the parts of the content it relates, each by its key path. |
| `goals` | What the piece, or the page, must achieve with its audience, such as what the audience can do after it, one sentence each. |
| `takeaway` | The one point a reader should leave the page with, only where the page has no *lead*. A lead is the text the page's content gives to state its point, such as a slide's lead under its title. No field says which text that is, so whoever writes or reviews the page reads it from the content. Where the page has a lead, the lead is its takeaway, and the brief does not repeat it. A cover or a section page often has none. |
| `reasons` | Why each choice of the design was made, one reason for each choice, listed in the order of their aspects. |

A reason holds these fields:

| Field | Required | What it holds |
|---|---|---|
| `aspect` | yes | What the choice is about, one of six, in the order the choices are made. `structure`: what the content's structure is, such as levels or a sequence. `form`: the form chosen for it, and the *visual variables* that carry the structure, the properties of a mark that can carry a difference, such as its position, size, lightness or hue. `hierarchy`: what is seen first, and what is ranked below it. `type`, `colour` and `space`: the brand's roles of each that the page takes, and what each colour marks. |
| `about` | no | The part of the page the reason is about, by its key path; in the piece's part, the part of the content. Without it, the reason is about the whole page, or the whole piece. |
| `text` | yes | Why the choice was made. |
| `principle` | yes | The principle the choice rests on: its `name`, and its `source`, such as an author and a work. A reason that names no principle is taste, which nobody can judge. |

- **A key path** names a part of the content as a tie's end names its item ([Content files](#content-files)). It joins the keys the content file writes with `.`, and names each item of a list by its id, as `[<id>]`, never by its place. It may end at a field, a list's included. A page's part starts the path at its page, as `visual.levels`. The piece's part starts it at the content's top, as `slides[layers]`, or a site's `header`. A part inside a local component, or in shared content, takes no key path, since a key path reaches only the piece's own content: name it in the words.
- **What a brief never holds.** Nothing the content holds: its text, its pictures, the component that draws each part, and any value or layout. Nothing `piece.yaml` declares: who the piece is for, where it is shown, whether it explains, its libraries and its lock. No reason for a library's own choice, such as why a brand's accent is the colour it is, which lives with the library. No requirement that binds more than this piece, which lives in a rule set.
- **The methodology's container,** `pkit`, is kept free at the brief's top and in each mapping of it, as in a content file ([Reserved words](#reserved-words)). Its schema refuses every other key it does not declare.
- **Who writes it.** A person, or an agent working for one. `pkit visual new` stamps it holding its binding alone, and says nothing in it. Its goals and relations come from whoever asks for the piece, and its reasons from whoever designs it, as they design.
- **No command changes what it says.** No renderer, export or producer reads it. So a change to it moves no lock, changes no scene, and stales no output: no fingerprint reads it (*The input set of each kind* in *What the check reports*). `pkit visual take-up` copies it with the rest of a final piece's folder, as it is ([The lock](#the-lock)). An id renamed in the content leaves the brief naming what is gone, which the check fails until a person mends the brief.
- **What the check reads of it.** Its shape is the core's data validation's. The check fails a page or a key path the brief names that names nothing in the content of the piece's source language: `brief-page` and `brief-path`, under *The brief* in *What the check reports*. A final piece's brief goes unread, but for its binding. Whether the drawn pages show what the brief asks is no check's to say. The capability's reviewer reads them against it, and reports each part of the brief a page does not show as a brief finding (DEC-030 point 6; *The reviewer* in the capability's README).

## Picture files

A *picture file* is a PNG or a JPEG file in the `pictures/` folder of a piece, or of a library's version (DEC-025 point 2). An image shows a piece's file by the name a field of the content gives ([Content files](#content-files)). It shows a version's file by the name its component gives, the same in every mode and under every brand (DEC-025 point 3). A local component's name finds a file of the piece. How an image names either is in *Components*. A brand's picture role names one too ([Picture roles](#picture-roles)). What the check and a release report of a picture file is under *Picture files* in *What the check reports*.

### How a name finds its file

- **By its bare name,** its file name alone, of the shape [Shapes](#shapes) gives. `.png` names a PNG, and `.jpg` or `.jpeg` a JPEG. A bare name holds no `/`, so it names a file of `pictures/` itself, never one in a folder within.
- **By its exact name,** among the files of `pictures/` as the commands list them ([How a command finds it](#how-a-command-finds-it)). So `logo.png` never finds `Logo.png`, though some file systems hold the two as one file. A file git ignores is no picture, since no clone holds it.
- **No symbolic link.** A name that finds one fails, since a link may lead out of the folder, or to a file another clone lacks.
- **Its own bytes, committed.** A file git hands to a large-file store, by the attribute `filter=lfs`, is no picture. Nor is a store's pointer that lies in a picture's place. The engine reads no store.

### The encodings read

The capability reads a picture stored in a way that every output draws alike (DEC-025 point 5):

- **A PNG** of 8 bits or fewer for each sample, of any colour type, a palette with transparency included.
- **A JPEG** of 8 bits, in grey or in colour, baseline or progressive.
- **What its bytes are.** Its first bytes say whether it is a PNG or a JPEG, and its extension must say the same.
- **Its colour profile.** A picture may carry an ICC profile, in a PNG's `iCCP` chunk or in a JPEG's ICC segments. The profile is for the picture's own colours: grey for a grey picture, RGB for one in colour.

Every other encoding is refused, with its fix:

| Refused | Fix |
|---|---|
| A PNG of 16 bits for each sample, or an interlaced one | Save it at 8 bits for each sample, not interlaced. |
| An animated PNG | Save its first frame as a still PNG. |
| A JPEG in CMYK | Save it in RGB. |
| A JPEG whose orientation tag turns or mirrors it | Save it upright, with no orientation tag that turns it. |
| A picture whose colour profile is for other colours than its own | Save it with a colour profile for its own colours, or with none. |
| A JPEG named `.png`, or a PNG named `.jpg` or `.jpeg` | Rename it by what it is, and name it so. Or save it as its extension says. |
| Any other encoding, such as a JPEG of 12 bits | Save it as a PNG or a JPEG of 8 bits. |

A file cut short or damaged cannot be read, and fails too. Save it again as a PNG or a JPEG of 8 bits.

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
- **`versions`** maps each version to `released: true` or `false`. A released version carries `hash`, its fingerprint over every file of its folder (*The fingerprint* in *What the check reports*). A version not released carries none.
- **One library to a name:** a second library of one name is refused (DEC-003 point 4).

Three commands write the list:

- **`pkit visual add`** lists each shipped version it copies. A released version takes `released: true` and the hash the library's record keeps, copied as it is. The version being built takes `released: false`, with no hash. A copy not yet released that the command replaces with a released version is listed released, with its hash. Where the location holds no list, the command writes one whole, under a comment that says what the file is.
- **`pkit visual release`** lists a version of the project's own library released: `released: true`, with the version's `hash`.
- **`pkit visual prune`** takes out the entry of each version it removes ([A version that lies behind](#a-version-that-lies-behind)).

Where the list is there already, each command writes it as text:

- **A new entry goes last:** a library the list does not name yet under `libraries`, a new version under its library's `versions`. Where that mapping's entries lie on the lines below its key, the entry is written as block lines at their indent. Where the mapping is written in flow on its key's line, such as `versions: {}`, the entry is written in flow before the closing brace.
- **An entry listed released is written again in its place,** in the style it had. It stays on its own lines, or in flow where the list writes it so, as in `{1.0.0: {released: false}}`. A comment on its key's line stays.
- **An entry taken out loses its lines:** the line that opens it, and each line below that its value takes, with the comments among them. Its library's `versions` must be written as a block mapping, one version on a line of its own.
- **Every other byte of the file stays:** comments, order, line endings and a byte-order mark.
- **Where the result would not read back as the list with that entry, or without it,** the command refuses: write `libraries`, and the library's `versions`, as block mappings.
- **Where a key on the way is written in quotes,** such as `'1.0.0':`, the refusal names that key instead, to be written without them. The keys on the way are `libraries`, the library's name, `versions`, and the version of an entry listed released or taken out.

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
| `kind` | `components`, a component library; `brand`; or `notation` ([Notations](#notations)). |
| `needs-release` | The release of the capability the version needs. A released version names the capability's version installed in the project when it was released. Its release writes it into this file before it works out the version's hash, and no person does (DEC-014 point 1). Where that copy of the capability is what a release carried, the number never understates what the version uses (DEC-014 point 2). A version being built names any release the installed capability reads. A version that names a newer release than the installed one, the `version` of the capability's `package.yaml`, cannot be read. |
| `builds-on` | Each library it builds on, as `{name, major}`, the major an integer from 1. |
| `dtcg` | A brand's DTCG version, `"2025.10"`, quoted, since YAML reads `2025.10` as a number. |
| `resolver` | A brand's Resolver document, a path within its version folder. |
| `open` | A brand's open roles ([Open roles](#open-roles)). |

Every field is required, `builds-on: []` included. `dtcg`, `resolver` and `open` are required of a brand, and refused in a component library or a notation.

### The libraries the capability ships

The capability's own folder, `.pkit/capabilities/visual-communication/`, keeps for each library it ships (DEC-013 point 2):

- **The version being built,** `libraries/<library>/`, under a name that names no version. Every change to the library goes into it, so a change of its number moves no file. The libraries the capability ships are those with a version being built.
- **Each released version,** whole, as it was released, at `releases/<library>/<version>/`. Its release adds the folder, and nothing later renames, removes or changes a file in it.
- **The library's record,** `releases/<library>/releases.yaml`, beside its released versions. A library with no released version has no record.

The record is a list of libraries that holds the one library, in the shape of a location's list ([The list, `libraries.yaml`](#the-list-librariesyaml)). It names the source `shipped`, and each released version with `released: true` and its `hash`. The hash is the fingerprint over every file of the released version, its `library.yaml` with the release it needs included.

```yaml
pkit_schema: visual-communication:libraries
schema_version: 1
libraries:
  foundations:
    source: {kind: shipped}
    versions:
      1.0.0: {released: true, hash: {form: 1, hash: sha256, format: 1, value: …, inputs: […]}}
```

The released versions and the record lie outside the version being built, and each library's apart from every other's. So a release changes no file of the version being built. Only whoever maintains the capability releases a version, by a release of its own. A release of the capability releases none (DEC-013 point 1).

**How a version is released.** `pkit visual release <library> --shipped` releases the version being built as the last commit holds it, where the capability is authored. A change to it that is not committed refuses the release. It releases the version only:

- **Untouched since the capability's current version was released.** No change has touched the version being built since the release step's change that wrote the version the capability's `package.yaml` carries (DEC-013 point 1). That change is the one that added the changelog's entry for that version, and its tree holds the capability's own checks. Where that history is not at hand, as in a shallow clone, the release refuses. A change since waits for the next release that moves the capability's version. So no library is released while the capability carries a version no release wrote, as before the capability's first release.
- **Under a number of its own.** The number is not released already. It is below neither the newest released one nor one the version being built carried at an earlier release (DEC-013 point 3). A library's first release takes the number the version being built carries.
- **On released bases.** It is checked on the newest released version of each major of each library it builds on, a base released earlier in the same change included. A base with no released version of a major the library names is released first.
- **Read in full and compared** with its previous release ([What a release compares](#what-a-release-compares)). A finding that fails refuses it (*What each run judges* in *What the check reports*).

The release adds the released place, whole, its `library.yaml` naming the capability's current version as the release it needs. It adds the version's entry to the record, and changes no other file of the capability's folder (DEC-013 point 2). It writes the change's patch changeset for the capability, naming the library and the version.

Every change to a version the capability ships reaches a project that brings it in. So it comes with a new version of the capability, at least a patch (DEC-013 point 4).

**How parallel changes meet.** Changes to a library's version being built, and its releases, meet as DEC-013 point 4 decides:

- **Two changes that raise the number alike** write the same line of `library.yaml`, so they meet only where they change one file differently. Two that raise it differently meet on that line: the higher holds, and the second to merge reads the version again after its rebase.
- **A library's release, and a change to the library merged beside it.** Whichever lands second fails the capability's own checks (DEC-013 point 6). A change that lands after the release finds the version being built carrying a released number while it differs from that version, and fails until it raises the number. A release that lands after the change fails, and waits as *How a version is released* says.
- **A library's release, and a release of the capability.** A release of the capability may land between a library release's branch and its merge. It may have shipped, under the number the library's release fixes, files a change put into the version being built and a later change took back, which a look at the history made only on the branch would miss. So the checks read the history up to the change that brings the library's release in. Where no change touched the version being built since the release it names, the library's release passes though the capability's release landed, and names that older version of the capability.
- **Releases of two libraries** add two places under `releases/` and change two records, so they meet nowhere but in the capability's own checks, which read a library with its base. A base and a library built on it may each need the other's new version, as when the base's next version removes an experimental component the library's newest release uses, and the library's next version uses what the base adds. Release both in one change, the base first, and the checks read them together.

**What the released versions cost.** The methodology carries the capability's folder in each of its distributions, whether a project installs the capability or not. git stores a file that stays the same once; the distributions hold it once in each version.

- **The first releases.** The foundations' 1.0.0 holds about 10 KB, the starter's 1.0.0 about 38 KB, and the neutral brand's 1.0.0 about 620 KB, almost all of it the fonts the brand commits (DEC-004 point 9), which compression shrinks by less than half.
- **When DEC-013 is weighed again,** once the released versions of the libraries the capability ships pass 10 MB together, the revisit weighs holding a shipped brand's fonts once, apart from the versions (DEC-013, Implications).

### The foundations

The capability ships the foundations' released version 1.0.0 at `.pkit/capabilities/visual-communication/releases/foundations/1.0.0/` ([The libraries the capability ships](#the-libraries-the-capability-ships)). It is of kind `components`, needs release 0.3.0 and builds on nothing. Their version being built stays where it was, at `libraries/foundations/`. It carries 1.1.0, since it adds the size axis `device` ([Axes and modes](#axes-and-modes)), the top `site`, and the roles `size.site` and `size.line`. These are additions, which need a minor ([What a release compares](#what-a-release-compares)). It is not released yet, so only `pkit visual add foundations --being-built` takes it. A piece reads them from the library folder alone, so `pkit visual add foundations` copies the released version whole to `libraries/foundations/1.0.0/`. It lists it with `source: {kind: shipped}`, `released: true` and the hash the library's record keeps ([What the location holds](#what-the-location-holds)). The foundations hold:

- `library.yaml`;
- `roles.yaml`, the shared roles, axes, colour families and contrast pairs that every library shares (DEC-004 points 2, 7 and 8);
- `components/figure.yaml`, the top component `figure`, for a figure in a documentation page;
- `components/deck.yaml`, the top component `deck`, for a presentation: each of its slides is a page, in its layout `cover` or `slide`, or drawn by the component it names;
- `components/site.yaml`, the top component `site`, for a web page or a portal of several: each of its `pages` is a web page, in its layout `standard`, or drawn by the component it names (DEC-022 point 1).

A site of one page is a single web page. The layout `standard` has one slot, `main`. Its page lays the site's `header`, its `main` part and the site's `footer` one under another, each the page's whole width, on the page's background. Each part sets its own inset, so a colour it paints reaches the page's edge (DEC-022 point 2).

- **The header and the footer** are the site's own fields, each optional, each the component the content places there. Every page drawn in a layout takes them, so each is written once in each language. A page drawn by its own component takes neither.
- **Its size.** The site asks for its width alone, `=@size.site`, so every page is as wide as the brand's site at the size it is drawn at. Each page is as tall as its content, and the site as tall as its tallest page (DEC-022 point 3).

The top components the capability ships are the foundations' (DEC-007 point 1).

Their shared roles are the colours `background`, `surface`, `text-primary`, `text-secondary`, `accent` and `line`. The dimensions are `space.1` to `space.4`, `size.figure`, `size.slide`, a slide's width, and `size.site`, the width of a site's pages. Its default, `{size.slide}`, draws a site as wide as a slide where a brand gives it no value (DEC-022 point 3). `size.line` is the length of a line of text at most. Its default, `{size.figure}`, caps a line at a figure's width where a brand gives it no value. The strokes are `stroke.thin`, an edge's width, and `stroke.thick`, the width of a line drawn on its own. The font families are `font.body` and `font.heading`. The typographies are `type.body`, `type.heading`, `type.strong`, the body's size and line height in a heavier weight, and `type.code`, a monospace type for code. The one picture role is `picture.logo`, the brand's logo, which no brand owes a value ([Picture roles](#picture-roles)).

They declare six colour families: `neutral`, `blue`, `green`, `orange`, `purple` and `red` (DEC-004 point 10). Each has three members: `fill`, the colour of what it paints; `line`, its edge; and `text`, the text on its fill. Each member is a shared colour role of the family's own, `family.<family>.<member>`, such as `family.blue.fill`, with no default, so a brand gives each a value. Each family's text and fill are a pair at the level `text`.

### `roles.yaml`

A library's `roles.yaml` declares its roles. The foundations declare the *shared roles*, which every library shares, with the axes, the colour families and the pairs. Another library of components may declare roles of its own. From the foundations, trimmed:

```yaml
pkit_schema: visual-communication:roles
schema_version: 1
roles:
  text-primary: {type: color}
  family.blue.fill: {type: color}
  family.blue.line: {type: color}
  family.blue.text: {type: color}
  space.1: {type: dimension}
  type.body: {type: typography}
axes:
  colour-scheme: {kind: value, modes: [light, dark], default: light}
  contrast: {kind: value, modes: [standard, high], default: standard}
  device: {kind: size, modes: [desktop, tablet, phone], default: desktop}
families:
  blue: {fill: family.blue.fill, line: family.blue.line, text: family.blue.text}
pairs:
  - {text: text-primary, under: background, level: text}
  - {text: family.blue.text, under: family.blue.fill, level: text}
```

- **`roles`** maps each role's token path to its `type`: `color`, `dimension`, `fontFamily`, `fontWeight`, `number`, `typography` or `picture`. A role carries no value: a brand gives it one. A role of the type `picture` takes a picture file of the brand as its value ([Picture roles](#picture-roles)). Only the foundations declare one, with no default, and no brand owes it a value (DEC-025 point 4). A role may carry a `default`, `{<role>}`, which it takes wherever no brand gives it a value. A shared role's default aliases an older role of the same type that has no default of its own (DEC-004 point 7). A role is never also a group of other roles.
- **`axes`** maps each axis to its `kind`, `value` or `size`; its `modes`, two or more, each once; and its `default`, one of them. The foundations alone declare axes.
- **`families`** maps each colour family to its members, each naming a colour role. A notation maps a concept to a family by its name ([Notations](#notations)). The foundations alone declare families.
- **`pairs`** lists the colour roles that must contrast (DEC-004 point 8): `text` drawn on `under`, at a WCAG `level`. `text` needs 4.5, `large-text` and `marks` need 3. The capability measures each pair, under each brand, in every combination of the axes, and the check reports a pair below its level (*Brands, tokens and contrast* in *What the check reports*).

The capability reads the `roles.yaml` of the foundations, and of each other library of kind `components` it resolves with them: each library a piece's lock or a declaration of written code names, and each library a version checked alone is resolved with (*What each run judges* in *What the check reports*). A brand's `roles.yaml` is not read: format 1 has no brand's own roles.

**A library's own roles.** A library other than the foundations declares its *own roles* and their pairs alone (DEC-004 point 7, DEC-008 point 1). The capability's test library `test-parts`:

```yaml
roles:
  test-parts.ink: {type: color, default: '{text-primary}'}
  test-parts.paper: {type: color, default: '{background}'}
  test-parts.note: {type: color, default: '{test-parts.ink}'}
  test-parts.gap: {type: dimension, default: '{space.2}'}
  test-parts.warning: {type: color}
pairs:
  - {text: test-parts.ink, under: test-parts.paper, level: text}
  - {text: test-parts.warning, under: test-parts.paper, level: large-text}
```

- **Its roles lie under its name,** as `test-parts.ink` does, never under `component`, the group of component tokens.
- **A default aliases a role the library names** (DEC-008 point 3): another of its own roles, or a role of a library it builds on, the shared roles included where it builds on `foundations`. It is of the role's type, and is never a value or a component token. A chain of defaults ends, never in a loop.
- **A default lies below every brand's value** (DEC-008 point 1). The capability merges a brand's sources over the defaults, then resolves the aliases, so a default follows the value the brand gives the role it aliases. `test-parts.note` takes the brand's `text-primary` through `test-parts.ink`, wherever the brand gives neither its own value. A component token's default lies there too ([Tokens](components.md#tokens)): in each combination of modes, under the base's tokens and the brand's own sources, and the aliases are resolved after the merge.
- **A role with no default** takes a value only from a brand, as `test-parts.warning` does. A role whose chain of defaults ends at one, rather than at a shared role, has no value under a brand that gives none along it. Only a role whose chain ends at a shared role draws under every brand.
- **Each pair names one of its own roles.** At its defaults, each of the library's own roles replaced by the role its default aliases, a pair falls on one that the foundations, the library or a library it builds on declares, in either order, at a level that needs as much contrast or more (DEC-008 point 6). `test-parts.ink` on `test-parts.paper` falls on the foundations' `text-primary` on `background`. Under a brand, a library's pair is measured only where the brand's values reach it: a value the brand gives a library's role along either role's chain of defaults. It is then measured in every combination where both roles have a value.
- **It declares no `axes`, no `families` and no picture role,** which are the foundations' alone. What is wrong in the file stops nothing: a role or a pair that cannot be read is left out, and reported.

### What a release compares

The *comparison* reads two versions of one library, each in full with the versions it is checked with (DEC-014 point 1). It names each *break*, a change that breaks what the earlier version promises, and each *addition*. The later number needs a major for a break, at least a minor for an addition, and otherwise at least a patch (DEC-013 point 3). Whether a change of look makes a patch a minor is the owner's judgement.

`pkit visual release` runs it on the version it releases and the library's previous release, and prints what the number needs before it writes. It refuses a break in a version that keeps the previous release's major (DEC-003 point 7). A library's first release is compared with none.

A library the capability ships breaks nothing within a major ([The libraries the capability ships](#the-libraries-the-capability-ships)). Each of its versions keeps what the release before it in that major promises (DEC-013 point 6).

A change of how something looks breaks nothing (DEC-003 point 6). So it passes over a brand's values, a component's colour, the look of its states and parts, and each drawing. What it compares, kind by kind:

- **Every library.** A change of its kind breaks, and so does a library it builds on taken at a new major (DEC-003 point 6). A notation is compared by these alone.
- **A component library's components.** Only a component the earlier version marks stable or deprecated is compared (DEC-003 point 7). An experimental one may change in any release, so only a new component is named, as an addition (DEC-003 point 1). A stable or deprecated component removed breaks, and so does one marked experimental. One marked deprecated breaks nothing.
- **A compared component,** part by part:
  - **Its fields.** A field removed breaks, and so does one newly required, or new and required (DEC-003 point 6, DEC-009 point 7). A new optional field is an addition (DEC-009 point 7).
  - **What a field takes.** A field breaks where it no longer takes a type, a value or a count of items it took. A key below it, removed or newly required, breaks it too (DEC-003 point 6). Another change of its schema, such as its `description`, is neither a break nor an addition.
  - **Its options, states and exposed parts.** Each removed breaks, and so do an option's word removed and an option that comes to take another kind of thing (DEC-003 point 6). Each new one, and a new word, is an addition (DEC-009 point 7). An option's default word is neither.
  - **Its fields of runs.** A field that ceases to take runs breaks, and so do a change of its first word and a word removed (DEC-012 point 6). A field that comes to take runs, and a new word after the first, are additions.
  - **Its lists.** A list's component field removed or renamed breaks, and so does marking a field it held as one (DEC-010 point 7). So does an arrangement field or one of its words removed. A new component field, arrangement field or word is an addition. An arrangement field's default is neither.
  - **Its ties.** End fields declared for a list it held break, and so do its end fields swapped or one removed (DEC-011 point 6). So does a component that ceases to take ends. A new list of ties is an addition.
  - **A top's layouts.** A layout or a slot removed breaks, and so does a new required slot (DEC-003 point 6, DEC-009 point 7). A top that makes its layouts its pages' forms, or ceases to, breaks too (DEC-010 point 7). A new layout and a new optional slot are additions. A slot of a page's form is compared as a field is, and a slot that comes to hold pages, or ceases to, breaks.
  - **Whether a top asks for a height.** A top that starts or ceases to ask for one breaks, since every page's size changes with it (DEC-022 point 8). A layout's height, said, changed or dropped, breaks nothing. A page under a top that asks for a height gets that height.
  - **A top's physical size.** A top that comes to declare one, ceases to, or changes its proportion breaks, since every page's height follows it (DEC-034 point 3). Two sizes have the same proportion where one, scaled to the other's width, gives the other's height within the rounding of whole millimetres, each side of each size taken as any length within half a millimetre of it. So A2 after A1, or A3 after A4, keeps the proportion, and US Letter after A4 changes it. A size changed in the same proportion is a change of how the pages look, and breaks nothing: each page draws as before, only larger or smaller in print. A top that moves from a height by a formula to a physical size is named once, as coming to declare one.
  - **Its tokens** ([Tokens](components.md#tokens)). A token removed or of another type breaks, and so does one whose default's chain no longer ends at a shared role, where it did (DEC-035 point 6). A new token is an addition, whatever its chain ends at. Any other change, such as a default pointed at another role, or a part that starts or stops reading a token, is neither.
- **A library's own roles.** A role promises what the components that read it promise (DEC-008 point 7). So only an own role a stable or deprecated component reads, directly or through a default, a default of one of its tokens included, can break. It breaks where it is removed, changes type, or no longer ends its chain of defaults at a shared role, where it did. A new one such a component reads breaks where its chain ends at no shared role, and any other new own role is an addition.
- **Pairs.** Every pair a library declares is compared, the foundations' included, whatever reads it (DEC-008 point 7). A pair removed, or its level lowered, breaks, and a new pair is an addition. A pair written the other way round is the same pair.
- **The foundations' shared roles,** whatever reads them (DEC-004 point 5). A shared role removed, or of another type, breaks, and so does one that loses its default (DEC-004 point 7). A new shared role with no default breaks, since every brand must then give it a value. A new one with a default is an addition, and so is a new picture role, which no brand owes a value. A new top group of the shared roles breaks, even where each of its roles carries a default. No library takes its name (DEC-004 point 7), so it fails a library already named so (DEC-025 point 10).
- **The foundations' axes and colour families,** whatever reads them. An axis or a mode removed breaks, and so does an axis of another kind or default (DEC-004 point 5). A colour family or a member removed breaks (DEC-003 point 6). A new axis, mode, colour family or member is an addition.
- **A brand's exported names** (DEC-004 point 5): its token paths, the component tokens it gives values among them, its axes and modes ([Axes and modes](#axes-and-modes)), and its open roles ([Open roles](#open-roles)). A token removed or of another type breaks, as do an axis or a mode removed and an axis of another kind or default. So does a role taken off its open roles. A new token, axis, mode or open role is an addition. So a size a brand comes to give is an addition, and one it ceases to give breaks. So is a logo, since a brand exports a picture role only where it gives it a value ([Picture roles](#picture-roles)).

Where either version cannot be read with its bases, or the later one cannot read a component the earlier one promises, no comparison is made, and the release refuses.

## Brands

A *brand* is a library of kind `brand`: it holds values (DEC-001 point 5). It keeps them as design tokens in the DTCG format, version 2025.10, and its modes as one Resolver document (DEC-004 point 1). The capability reads the subset of DTCG below, and refuses the rest. The test brand's `library.yaml` is shown under [`library.yaml`](#libraryyaml).

The capability ships one brand to start from ([The neutral brand](#the-neutral-brand)). A project may write its own, and keeps it in its library folder as it keeps any library ([The library folder](#the-library-folder)).

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
- **A modifier** is a shared axis the brand varies. Its `contexts` hold one list of sources for each mode the brand gives, the axis's default among them. Its `default` is the axis's default. What a mode the brand leaves out takes is under [Axes and modes](#axes-and-modes).
- **`resolutionOrder`** names each set and each modifier once, as `{"$ref": "#/sets/<name>"}` or `{"$ref": "#/modifiers/<name>"}`. A later source wins.

For each combination of modes, the capability merges the brand's sources in resolution order, over the roles' defaults, then resolves the aliases. A brand built on another merges its sources over its base's tokens instead ([Open roles](#open-roles)). Every shared role but a picture role must have a value of its declared type in every combination. The brand *exports* the shared roles, and each role of a library it names that it gives a value ([A library's roles](#a-librarys-roles)). It exports a picture role only where it gives it a value ([Picture roles](#picture-roles)). Its other tokens, such as a palette its roles alias, are private. They lie in groups of their own, outside the top groups of the shared roles.

### Fonts

A `fontFamily` token names each family's font file in the capability's extension key, `pkit.visual-communication`, as `font.body` does above. `files` maps each family to a file of the brand's version folder, or to `{"hash": "sha256:<hex>"}`. A family named by its hash is a font the brand may not ship. The project commits it in the location's `fonts/`, where the capability finds it by the hash of its bytes (DEC-004 point 9). `measure` is `file`: the font is measured from its file. A font file is committed unchanged with its licence, where its licence allows (DEC-004 point 9).

### Picture roles

A *picture role* is a role whose value is a picture file of the brand's version (DEC-025 point 4). The foundations declare the shared picture roles in one group, `picture`. The first is `picture.logo`, the brand's logo. Only the foundations declare a picture role.

A brand gives a picture role its value as an empty group at the role's path. DTCG has no type for a file, so the group carries no `$type`. Its `$extensions` name the file in the capability's extension key, by its bare name:

```json
{
  "picture": {
    "logo": {"$extensions": {"pkit.visual-communication": {"file": "logo.png"}}}
  }
}
```

- **The file** lies in the `pictures/` folder of the brand's version, under its bare name. It is found and read as any picture file is ([Picture files](#picture-files)). Each finding on it lies in the brand's version (DEC-025 point 9).
- **The group holds nothing else** but a `$description` and a `$deprecated`. It aliases nothing, and no token aliases it.
- **It merges as a token's value does,** in the Resolver document's order of sources. So a value axis may give a dark mode its own logo, and a size axis a phone its own. A brand built on a base keeps its base's logo, unless the base opens the role ([Open roles](#open-roles)).
- **In every value mode, or in none.** Within one key over the size axes, a brand gives a picture role a file in every combination of the value axes, or in none. A brand that gives it in some and not in others is at fault.
- **One proportion within a key.** The files a picture role takes over the value axes, within one key, share one proportion of width to height. So a dark logo may hold twice the pixels, but never another shape.
- **No brand owes one a value.** A brand that gives it none is not at fault. Its version states that once, as a fact, and no piece states it (DEC-025 point 9).
- **It is exported only where the brand gives it a value** (DEC-004 point 5). So ceasing to give one breaks the brand ([What a release compares](#what-a-release-compares)).

### A library's roles

A brand reaches the own roles of a library, to give one a value, open it or alias it, only where it names that library in its `builds-on`, by the major of the version it is resolved with (DEC-008 point 4). So every piece that uses the brand locks that library too ([The lock](#the-lock)). It reaches the component tokens of the library's components the same way. Each lies in its component's file, at `component.<library>.<component>.<name>` ([Tokens](components.md#tokens)), so a brand holds its value under `component.<library>`, apart from the library's own roles.

- **What it owes a library it names:** a value, in every combination, to each of the library's roles that has no default. Each token it holds under the library's name gives one of the library's roles a value of its type, and each it holds under `component.<library>` gives one of its components' tokens one. A token there that names none of them, or is of another type, gives nothing, and is a finding.
- **Where it names none,** the library is at its defaults under the brand ([`roles.yaml`](#rolesyaml)). A token the brand holds under the library's name, or under `component.<library>`, stays private, and gives the library nothing. An alias to one of the library's roles fails.
- **Under `component.<its own name>`,** where its own components' tokens lie, a brand's token stays private, with no finding.
- **What it exports:** beside the shared roles, each role of a library it names that it, or its base, gives a value, a component token among them (DEC-008 point 5). A role it leaves at its default is not exported: its name is the library's, kept by the library's major.

The test brand itself builds on `foundations` alone. The capability's tests build a copy of it that names `test-parts`, with this `builds-on` and these tokens:

```yaml
builds-on:
  - {name: foundations, major: 1}
  - {name: test-parts, major: 1}
```

```json
{
  "test-parts": {
    "$type": "color",
    "ink": {"$value": "{scheme.strong-ink}"},
    "warning": {"$value": "{scheme.ink}"}
  }
}
```

It gives `test-parts.warning`, which has no default, a value, and changes `test-parts.ink`. `test-parts.note` follows the brand's ink through its default, and `test-parts.paper` stays at its default, the brand's `background`.

### Open roles

A brand may build on one other brand, its *base*, and change only what the base opens to it (DEC-004 point 6). It marks the base in `builds-on` with `base: true`, by the major it fits. It marks at most one, and the base is a brand. The base is one of the libraries the brand builds on, so a piece's lock names it too ([The lock](#the-lock)). The capability's tests build the test edition, `test-edition`, on the test brand:

```yaml
builds-on:
  - {name: foundations, major: 1}
  - {name: test-brand, major: 1, base: true}
open: [accent]
```

A brand's `open` lists the roles that a brand built on it may give values: roles it exports, or groups of them by whole segments of their paths. Each entry names a shared role, a role or a component token of a library the brand names, or a group of them, such as `space`, or `component.ui.card` or `component.ui` for the tokens of a library `ui`. A group under `component` opens only the tokens of the libraries the brand names. The test brand opens `accent` and `space`.

The capability reads the base first, at the version the lock names, and its own base before it. In each combination of modes:

- **The base's tokens come first,** then the brand's own sources, in its resolution order. The aliases are resolved after the merge.
- **A value the brand gives an open role wins** in the combinations its sources cover, and the base's value holds elsewhere. Every token that aliases the role follows the merged value, the base's tokens included. The test edition gives `accent` a value in the dark colour scheme and at high contrast, so the test brand's accent holds in the light scheme at standard contrast.
- **A value for a role the base does not open** fails, and the base's value holds.
- **A library's role** takes the brand's value only where both the brand and its base name the library, and the base opens the role (DEC-008 point 4). A base opens a role of a library it names, a component token included, whether it gives it a value or not. A base that names no library leaves the library at its defaults for every brand built on it.
- **An alias reaches only the shared roles, the roles of the libraries the brand names, and the brand's own tokens.** An alias to a token the base keeps private fails. Each brand's private tokens are its own, so a palette of one name in the base and in the brand never meets.
- **The brand varies values on its base's axes,** by their names and modes, in its own Resolver document. A modifier for another axis, a context for another mode, or another default fails.
- **Each link of a chain narrows.** A base may build on a brand in turn. A brand's `open` names only roles its base opens to it. An entry that names more fails, and opens only what the base opens.

A brand's findings hold its base's too, each naming the base's version. A declared pair or a font is judged at the brand only where the brand's values change what the base gives.

### Axes and modes

An *axis* is one way a brand's values vary, such as the colour scheme. A *mode* is one value on one axis, such as `dark` (DEC-004 point 2). The foundations declare the shared axes. Their release 1.0.0 declares two value axes: `colour-scheme`, with `light` and `dark`, and `contrast`, with `standard` and `high`. Their version being built, 1.1.0, adds the size axis `device`, with `desktop`, `tablet` and `phone`, and the default `desktop` (DEC-021 point 1).

- **A brand varies an axis** through a modifier of its Resolver document, in the modes it gives. It may leave out an axis it does not vary. It adds no axis of its own and no mode, and changes no default.
- **A value axis** changes only colours and pictures. A mode of a value axis that changes another value fails.
- **Every brand has each value axis whole** (DEC-004 point 2). A mode it does not give takes its values at the axis's default. In a brand built on another, its base's values hold there.
- **A size axis** may change any value. A brand has a shared size axis only where a modifier varies it, with the modes that modifier gives (DEC-021 point 2). A brand built on another has its base's sizes. So a brand that gives no size keeps its combinations and its written code.
- **A piece** chooses the modes it is drawn in under its `modes`. A mode its brand does not have fails, a size it does not give among them.

### The neutral brand

The capability ships `neutral`, a brand to start from, so a project can draw before it writes a brand of its own. Its released version 1.0.0 lies at `.pkit/capabilities/visual-communication/releases/neutral/1.0.0/` ([The libraries the capability ships](#the-libraries-the-capability-ships)). It is of kind `brand` and needs release 0.3.0. Its version being built stays where it was, at `libraries/neutral/`. It carries 1.1.0, since it gives the sizes of `device`, an addition, which needs a minor (DEC-013 point 3). It is not released yet, so only `pkit visual add neutral --being-built` takes it.

`pkit visual add neutral` copies the released version whole to `libraries/neutral/1.0.0/`. It lists it with `source: {kind: shipped}`, `released: true` and the hash the library's record keeps ([What the location holds](#what-the-location-holds)). A piece then names it as `brand: neutral` ([`piece.yaml`](#pieceyaml)).

- **Its values.** It gives every shared role a value in each of the four combinations of the shared value axes ([Keys of combinations](#keys-of-combinations)), but `picture.logo`. It has no logo, which its version states as a fact ([Picture roles](#picture-roles)). Each pair the foundations declare reaches its level in all four.
- **Its sizes.** Its version being built gives `desktop`, `tablet` and `phone`, each mode but the default from a token file of its own in `tokens/`. Its `size.site` is 1,280 px on a desktop, 768 px on a tablet and 390 px on a phone. No other value changes with the size, so a piece that names no size draws as under 1.0.0.
- **Its look.** Greys, with a blue accent. The colour families keep their hues in dark and at high contrast.
- **The libraries it names.** It builds on the foundations alone, so the starter draws at its defaults ([`roles.yaml`](#rolesyaml)), and a project need not hold the starter to use it.
- **Its open roles.** `open` is empty, so a brand built on it can change no value. A project that wants other values writes its own brand.
- **Its fonts.** Source Sans Pro draws the body, and its semibold the headings and strong text, each weight a family of its own. Source Code Pro draws code. Each file lies unchanged in the version's `fonts/`, beside its licence ([Fonts](#fonts)).

## Notations

A *notation* is a library of kind `notation`: the concepts of one subject, each mapped to a colour family the foundations declare (DEC-004 point 10). It maps a concept to a family, never to a value, so each brand colours the concept its own way. Its version folder holds its `library.yaml`, which builds on the foundations, and its `notation.yaml`. The test notation, `test-notation`, names the parts of a system.

No notation ships with the capability. A project writes its own, and keeps it in its library folder as it keeps any library ([The library folder](#the-library-folder)).

### `notation.yaml`

The test notation's:

```yaml
pkit_schema: visual-communication:notation
schema_version: 1
concepts:
  person: {colour: purple}
  service: {colour: blue}
  store: {colour: green}
```

- **`concepts`** maps each concept, by its name, to `{colour: <family>}`, one of the colour families of the foundations the piece locks ([The foundations](#the-foundations)). It holds at least one concept. A concept that maps to a value, to a role or to a family the foundations do not declare is refused (*What the check reports*).

How a piece names the notations it uses is under [`piece.yaml`](#pieceyaml), how its lock takes them under [The lock](#the-lock), and how its content names a concept under [Content files](#content-files) and [Shapes](#shapes).

## Keys of combinations

A *combination* takes one mode on each axis. Its *key* names it (DEC-004 point 3).

- **A key names the modes that are not their axis's default,** each as `<axis>.<mode>`, the axes in the order of their names, joined by `+`.
- **The combination of every default** is `default`. No other key spells it, since every other key holds a `.`.
- **The shared value axes give four keys:** `default`, `colour-scheme.dark`, `contrast.high` and `colour-scheme.dark+contrast.high`.
- **A key that names a default mode,** or names its axes out of order, is no key.
- **Adding an axis with a default** changes no key: every combination that existed takes the new axis's default, which its key leaves out.
- **Keys are kept in one order** wherever a list of them is kept: by their count of segments, then by their spelling. `default` comes first.
- **A file that holds several combinations** takes the first of their keys in that order.

A key names a combination in the names of previews, exports and produced pictures, and in written code (*What is made from a piece*).
