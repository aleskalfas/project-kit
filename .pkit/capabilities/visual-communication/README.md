---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/package.yaml
        - .pkit/capabilities/visual-communication/scripts/status.py
        - .pkit/capabilities/visual-communication/scripts/check.py
        - .pkit/capabilities/visual-communication/scripts/add.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/scripts/produce.py
        - .pkit/capabilities/visual-communication/scripts/export.py
        - .pkit/capabilities/visual-communication/scripts/write-code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/files.py
        - .pkit/capabilities/visual-communication/scripts/_lib/copies.py
        - .pkit/capabilities/visual-communication/scripts/_lib/location.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/root.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/__init__.py
      record: ["visual-communication:DEC-001", "visual-communication:DEC-002", "visual-communication:DEC-003", "visual-communication:DEC-004", "visual-communication:DEC-005", "visual-communication:DEC-006", "visual-communication:DEC-007", "visual-communication:DEC-013", COR-017, COR-023, COR-031, COR-055]
      artefact:
        - .pkit/capabilities/visual-communication/checks.md
        - .pkit/capabilities/visual-communication/checks.md#the-findings-record
        - .pkit/capabilities/visual-communication/checks.md#when-the-check-reads-it
        - .pkit/capabilities/visual-communication/checks.md#what-each-run-judges
        - .pkit/capabilities/visual-communication/components.md
        - .pkit/capabilities/visual-communication/files.md
        - .pkit/capabilities/visual-communication/files.md#a-piece
        - .pkit/capabilities/visual-communication/files.md#brands
        - .pkit/capabilities/visual-communication/files.md#notations
        - .pkit/capabilities/visual-communication/files.md#the-binding
        - .pkit/capabilities/visual-communication/files.md#the-clones-local-folder
        - .pkit/capabilities/visual-communication/files.md#the-foundations
        - .pkit/capabilities/visual-communication/files.md#the-libraries-the-capability-ships
        - .pkit/capabilities/visual-communication/files.md#the-library-folder
        - .pkit/capabilities/visual-communication/files.md#the-list-librariesyaml
        - .pkit/capabilities/visual-communication/files.md#the-location
        - .pkit/capabilities/visual-communication/files.md#the-lock
        - .pkit/capabilities/visual-communication/files.md#what-the-location-holds
        - .pkit/capabilities/visual-communication/outputs.md
        - .pkit/capabilities/visual-communication/outputs.md#exports
        - .pkit/capabilities/visual-communication/outputs.md#plugins
        - .pkit/capabilities/visual-communication/outputs.md#previews
        - .pkit/capabilities/visual-communication/outputs.md#produced-pictures
        - .pkit/capabilities/visual-communication/outputs.md#the-declaration
        - .pkit/capabilities/visual-communication/outputs.md#the-svg-renderer
        - .pkit/capabilities/visual-communication/outputs.md#what-refuses-an-export
        - .pkit/capabilities/visual-communication/outputs.md#written-code
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#validate
---

# visual-communication capability

Visual work made from reusable parts. A *piece*, such as a presentation or a figure in a documentation page, keeps its content as data. Libraries give it its look: components that arrange and draw the content, brands that hold the values (colours, fonts, sizes), and notations that say what a thing is. Several renderers draw the same piece, as a vector picture, a web page or objects on a whiteboard service, and a piece is handed out as a file such as a PDF. A project installs the capability when its visuals should share a look, reuse what was made before, appear under more than one brand or in more than one language, and be checked like the rest of its work.

## What this capability ships

- **The commands** `pkit visual …`, also reachable as `pkit visual-communication …`. Each is described under [Commands](#commands).
- **The file formats,** format 1: a schema for each kind of file a piece, a library or a command writes, under `schemas/`. Each file names its schema in its first lines ([The binding](files.md#the-binding)), so `pkit validate` checks its shape.
- **The foundations library,** under `libraries/foundations/`: a few shared roles, two axes, six colour families, and two top components: `figure`, for a figure, and `deck`, for a presentation ([The foundations](files.md#the-foundations)). Its version is not released yet, so it may change in any release of the capability.
- **Two plugins:** the SVG renderer, which draws the previews and the exports, and the CSS code writer, which writes a brand out as CSS variables ([Plugins](outputs.md#plugins), [The SVG renderer](outputs.md#the-svg-renderer), [Written code](outputs.md#written-code)).
- **The check,** the `visual-communication:check` member of `pkit validate`.
- `decisions/DEC-NNN-*.md`: the principles every piece, library and renderer follows.

No brand, notation or producer ships ([Brands](files.md#brands), [Notations](files.md#notations), [Plugins](outputs.md#plugins)). A project writes its own brand and notations, and `pkit visual produce` has no producer to run yet, so a piece that declares a produced picture cannot be given one ([Produced pictures](outputs.md#produced-pictures)).

The pages beside this README are the reference:

- [The files of the visual work](files.md): the working folder, the piece, its content, libraries, brands, notations and keys.
- [Components](components.md): a component's file, formulas, layouts and how text is measured.
- [What is made from a piece](outputs.md): renderers, exports, produced pictures and written code.
- [What the check reports](checks.md): every finding, its severity, the findings record and the fingerprint.

## Adopter setup

Install the capability, then sync, so the check's dependencies are in place before `pkit validate` runs it offline:

```
pkit capabilities install visual-communication
pkit sync
```

The visual work lies in one folder of the repository, the *location*: `visual/` at the top of the repository, unless the project names another. Nothing needs configuring before the first command: the first command that writes there records the location in the capability's configuration. [The location](files.md#the-location) says how it is found and recorded.

Every piece uses the foundations, so bring them into the location first:

```
pkit visual add foundations
```

A library the capability ships reaches the location only through [`pkit visual add`](#pkit-visual-add-library). No install, sync or upgrade of the capability writes there, so an upgrade alone changes no piece's look ([What the location holds](files.md#what-the-location-holds)). Run the command again after an upgrade to take the newest released version, and to bring each copy of the library up to date.

## Drawing a piece

1. **Bring the libraries.** [`pkit visual add <library>`](#pkit-visual-add-library) copies a library the capability ships, such as the foundations, into the location's library folder, and lists it in `libraries/libraries.yaml`. Put each other library version a piece uses there yourself, and list it ([The library folder](files.md#the-library-folder)). A piece needs a brand, and none ships, so the project writes its own ([Brands](files.md#brands)).
2. **Write the piece.** A piece is a folder under `pieces/`: its `piece.yaml` names its libraries, languages, modes and exports, and its content names the components that draw it ([A piece](files.md#a-piece)).
3. **Draw it.** `pkit visual render <piece>` writes the piece's lock, computes its scenes, keeps their findings in `findings.yaml`, and draws an SVG preview of each scene. Open the previews under `.pkit/capabilities/visual-communication/project/local/previews/<piece>/` ([The clone's local folder](files.md#the-clones-local-folder)).
4. **Check it.** `pkit visual check <piece>`, or `pkit validate`, reports what the piece breaks ([What the check reports](checks.md)).
5. **Commit the piece's folder:** `piece.yaml`, the content and `findings.yaml`. The previews stay local to the clone ([The clone's local folder](files.md#the-clones-local-folder)).
6. **Hand it out.** `pkit visual export <piece>` makes a numbered export in each format the piece declares, and records the version in the piece's `exports.yaml`. Commit `exports.yaml`; the exported files stay local until they are handed out.

A brand's values reach code the same way: a declaration under the location's `code/` folder names the brand and where the code goes, and `pkit visual write-code <name>` writes it ([Written code](outputs.md#written-code)).

## Commands

Every command runs from anywhere in the project: it finds the project root as the nearest folder, from where it runs upwards, that holds the installed capability. `add`, `render`, `produce` and `export` write in the location, so where none is recorded they take `visual/` and record it, or the path `--location <path>` names. A command prints `error: …` and exits 1 when it refuses, or when a write fails. Every check that can refuse runs before its first write, so a refused command has written nothing. Where a write fails, the error names the file the command could not write and why, and the command leaves every file as it was before the run: it removes each file the run made, writes back each file it changed, puts back each folder it replaced, and takes back the location it recorded. It names each file it could not put back. `produce` alone writes before it can refuse: it hands the producer its inputs in the capability's local folder, outside the location, and that hand-over stays as it was written ([Produced pictures](outputs.md#produced-pictures)).

### `pkit visual status`

Shows where the visual work lies, and each piece with its state and its lock.

- **Prints** the location, and whether the configuration records it or it is the default, not recorded yet. Then each piece under `pieces/`, with its state, whether it is pinned, and the version of each library its lock names. A piece with no lock yet says that its first render writes one.
- **Writes** nothing.
- **Exits** 1 when the configuration cannot be read, or records a location that is refused or missing; 0 otherwise.

### `pkit visual add <library>`

Copies a library the capability ships into the location's library folder, lists it, and brings every copy of it up to date.

- **Takes** the newest released version the capability ships ([The libraries the capability ships](files.md#the-libraries-the-capability-ships)). `pkit visual add <library>@<version>` names another released version, and `--being-built` asks for the version being built. Where the library has no released version, it takes the version being built. Asked for the version being built while it carries a released number, it takes that released version.
- **Copies** the version whole to `libraries/<library>/<version>/`, beside the versions the location holds. `pkit visual add foundations` makes `libraries/foundations/1.0.0/`.
- **Lists it** in `libraries/libraries.yaml` with the source `shipped`. A released version is listed `released: true`, with the hash the library's record keeps, as it is. The version being built is listed `released: false`, with no hash. Every other byte of the list stays ([The list, `libraries.yaml`](files.md#the-list-librariesyaml)).
- **Brings every copy of the library up to date** in the same run ([What the location holds](files.md#what-the-location-holds)):
  - A copy the list marks not released, of a number the capability ships, is replaced whole by what the capability ships under that number. Where that number is released, the list then marks the copy released, with its hash.
  - Such a copy is replaced only where every lock that names it is the lock of a draft that is not pinned, which moves at each render. Under a pinned draft's lock, or written code's, the copy stays as it is. The command names each such piece or declaration, and goes on with the rest of the run. A lock it cannot read counts as one that moves only on purpose, and the command names its file. It reads only a piece's `lock`, `pinned` and `state`, so a fault in the piece's content stops nothing.
  - A released copy whose files no longer match its hash is restored as released. One that matches is not written.
  - A copy of a number the installed capability does not ship stays as it is, and so does a version folder the list does not name.
  - A version the list names whose folder is missing is brought in as a copy of its kind is: a released one restored, one not released replaced, under the same locks.
- **Prints** each copy it writes, as copied, replaced or restored, with each piece and declaration whose lock names it. Then each copy it leaves, with why, and each version it lists.
- **Refuses** a library the capability does not ship, naming the ones it ships, and a released version it does not ship. It refuses files the capability ships that no longer match the hash the library's record keeps, or whose files of the capability's format lack their binding ([The binding](files.md#the-binding)). It refuses a hash the list keeps for a released version that differs from the one the capability records, naming both. It refuses a version folder the list does not name, where the version is to be copied, and a library the list names from another source, since one name ties one library to its source.
- **Exits** 0 when it wrote each copy, or left it with why; 1 when it refused, with nothing written, or a write failed ([Commands](#commands)).

Running it is the consent for each copy it writes. A change the project made in a copy it replaces or restores is lost, as the project's diff shows: a shipped library changes where it is authored, never in a copy.

### `pkit visual render <piece>`

Draws a piece in each of its languages and each combination of modes it names.

- **Moves the lock** of a draft to the newest versions the project holds that fit together, within the lines the lock names, and writes it into `piece.yaml`, every other byte kept. A pinned piece's lock is checked, never moved ([The lock](files.md#the-lock)).
- **Computes every scene.** A font with no file, or a character no font family can measure, refuses the render before anything is laid out.
- **Writes `findings.yaml`** beside `piece.yaml`: what computing the scenes found, keyed by a fingerprint of every file they were computed from ([The findings record](checks.md#the-findings-record)).
- **Draws the previews** with the SVG renderer, one file for each page, language and combination of modes, in `.pkit/capabilities/visual-communication/project/local/previews/<piece>/`. They replace the piece's previews from before ([Previews](outputs.md#previews)).
- **Prints** the lock, each finding, and each loss the renderer reports that the piece does not accept.
- **Exits** 0 when it drew the piece, findings or not; 1 when it refused, with nothing written, or a write failed ([Commands](#commands)).

### `pkit visual check [<piece>]`

Checks every piece of the location, or the one named, without drawing anything.

- **Reads** every file of the capability's format in the location, the library folder and its list, the newest version of each major of each library checked alone, each piece's lock and the libraries it locks, its content against the components it fills, and its scenes. With a piece named, it checks no version alone but to tell where a finding under the piece's lock lies ([What each run judges](checks.md#what-each-run-judges)). A piece's scenes are read from its `findings.yaml` while the record's key still verifies; otherwise they are computed now ([When the check reads it](checks.md#when-the-check-reads-it)).
- **Prints** a summary, then each finding with its severity, where it points and what it says. `--json` prints the findings document `pkit validate` reads.
- **Writes** nothing, runs no program of the project's, and needs no network.
- **Exits** 1 when a finding fails; 0 otherwise. With `--json` it always exits 0, as `pkit validate` requires.

### `pkit visual produce <piece> <output>`

Runs the producer a piece declares for one of its produced outputs, and keeps its picture.

- **Makes the variants:** it resolves the roles the producer's inputs name in every combination the piece names, under the piece's lock, and makes one variant for each distinct set of values.
- **Keeps the picture** only when no input changed during the run and every variant is a PNG of the declared pixel size, exposing the same points. Then it writes each variant and the record in the piece's folder, under `produced/<output>/`, and removes a variant file left from before.
- **Prints** each loss the producer reports that the piece does not accept.
- **Refuses** a piece with no lock yet (run `pkit visual render <piece>` first), and a producer that reaches a service or calls an outside program this machine lacks, before it runs. What a producer is handed and returns is under [Produced pictures](outputs.md#produced-pictures).
- **Exits** 0 when it wrote the variants and their record; 1 when it refused, with nothing written in the location, or a write failed ([Commands](#commands)).

### `pkit visual export <piece>`

Makes a numbered export of a piece in each format it declares.

- **Numbers the run:** every file it makes carries the piece's next version number, as `<piece>.v<N>.<language>.<key>.svg`, in `.pkit/capabilities/visual-communication/project/local/exports/<piece>/`. A piece of more than one page makes one file for each page, which adds the page's number, from 1: `<piece>.v<N>.<language>.<key>.<n>.svg`. No file overwrites another ([Exports](outputs.md#exports)).
- **Records the version** in `exports.yaml`.
- **Uses the lock** `piece.yaml` holds, and never moves it.
- **Refuses** a piece with no lock yet, a lock that does not hold, and a produced picture that is missing or stale, unless `--use-stale <output>` names it. `--use-stale` may repeat. Every reason it refuses is under [What refuses an export](outputs.md#what-refuses-an-export).
- **Exits** 0 when it exported and recorded the version; 1 when it refused, with nothing written, or a write failed ([Commands](#commands)).

### `pkit visual write-code <name>`

Writes a brand out as code, as the declaration `code/<name>.yaml` in the location asks.

- **Writes** the code to the declaration's `out`, and its record beside it, `<out>.record.yaml`. Where the record verifies and the code is what the writer writes now, it writes nothing and says the code is up to date.
- **Never moves** the declaration's lock: a person moves it on purpose ([The declaration](outputs.md#the-declaration)).
- **Prints** each token the writer has no form for as a loss, unless the declaration accepts it under `accept-losses`.
- **Exits** 0 when it wrote the code or found it up to date; 1 when it refused, or a write failed ([Commands](#commands)); 2 on a usage error.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename
stem: `[visual-communication:DEC-001-<slug>]`. Other capabilities and adopter content
use the same form.

## Dependencies

No other capability. The commands run their scripts through `uv`, with the Python packages each script pins; `pkit sync` installs those of the check, so `pkit validate` runs it offline.
