---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/package.yaml
        - .pkit/capabilities/visual-communication/scripts/check.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/scripts/produce.py
        - .pkit/capabilities/visual-communication/scripts/write-code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/findings.py
        - .pkit/capabilities/visual-communication/scripts/_lib/fingerprint.py
        - .pkit/capabilities/visual-communication/scripts/_lib/reading.py
        - .pkit/capabilities/visual-communication/scripts/_lib/files.py
        - .pkit/capabilities/visual-communication/scripts/_lib/location.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/libraries.py
        - .pkit/capabilities/visual-communication/scripts/_lib/tokens.py
        - .pkit/capabilities/visual-communication/scripts/_lib/notations.py
        - .pkit/capabilities/visual-communication/scripts/_lib/values.py
        - .pkit/capabilities/visual-communication/scripts/_lib/env.py
        - .pkit/capabilities/visual-communication/scripts/_lib/text.py
        - .pkit/capabilities/visual-communication/scripts/_lib/layout.py
        - .pkit/capabilities/visual-communication/scripts/_lib/scene.py
        - .pkit/capabilities/visual-communication/scripts/_lib/framing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/exports.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/seam.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/svg_declaration.py
        - .pkit/capabilities/visual-communication/schemas/findings.schema.json
        - .pkit/capabilities/visual-communication/schemas/defs.schema.json
      record: ["visual-communication:DEC-002", "visual-communication:DEC-003", "visual-communication:DEC-004", "visual-communication:DEC-005", "visual-communication:DEC-006"]
      artefact:
        - .pkit/capabilities/visual-communication/components.md#a-components-file
        - .pkit/capabilities/visual-communication/components.md#breaking-lines
        - .pkit/capabilities/visual-communication/components.md#errors
        - .pkit/capabilities/visual-communication/components.md#fields
        - .pkit/capabilities/visual-communication/components.md#layouts
        - .pkit/capabilities/visual-communication/components.md#placing-a-component-use-and-slot
        - .pkit/capabilities/visual-communication/components.md#primitives
        - .pkit/capabilities/visual-communication/components.md#trace-ids
        - .pkit/capabilities/visual-communication/components.md#values-states-and-colour
        - .pkit/capabilities/visual-communication/components.md#what-an-element-asks-for-and-what-it-gets
        - .pkit/capabilities/visual-communication/files.md#brands
        - .pkit/capabilities/visual-communication/files.md#content-files
        - .pkit/capabilities/visual-communication/files.md#how-the-files-are-read
        - .pkit/capabilities/visual-communication/files.md#reserved-words
        - .pkit/capabilities/visual-communication/files.md#the-binding
        - .pkit/capabilities/visual-communication/files.md#the-library-folder
        - .pkit/capabilities/visual-communication/files.md#the-location
        - .pkit/capabilities/visual-communication/files.md#the-lock
        - .pkit/capabilities/visual-communication/files.md#notations
        - .pkit/capabilities/visual-communication/files.md#what-the-location-holds
        - .pkit/capabilities/visual-communication/outputs.md#accepting-a-loss
        - .pkit/capabilities/visual-communication/outputs.md#produced-pictures
        - .pkit/capabilities/visual-communication/outputs.md#the-loss-report
        - .pkit/capabilities/visual-communication/outputs.md#the-record-beside-the-code
        - .pkit/capabilities/visual-communication/outputs.md#the-record-of-a-produced-output
        - .pkit/capabilities/visual-communication/outputs.md#the-record-of-exports
        - .pkit/capabilities/visual-communication/outputs.md#what-refuses-an-export
        - .pkit/capabilities/visual-communication/outputs.md#written-code
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#validate
        - .pkit/lifecycle/README.md#how-a-registered-command-is-run
---

# What the check reports

`pkit visual check` judges a project's visual work and draws nothing. Each problem it finds is a *finding*. `pkit validate` runs the same check as one of its members. What the command reads, prints and exits with is under *Commands* in the README. The examples come from the capability's test files: the test brand `test-brand` and the test library `tests` exist for the tests only.

## Contents

<!-- pkit:contents -->
- [Severities](#severities)
- [What a finding says](#what-a-finding-says)
- [What each run judges](#what-each-run-judges)
- [Findings by area](#findings-by-area)
- [The findings record](#the-findings-record)
- [The fingerprint](#the-fingerprint)
- [In `pkit validate`](#in-pkit-validate)
<!-- /pkit:contents -->

## Severities

Each finding takes one of three levels (DEC-002 point 7). Validation reads each level as one of its severities.

| Level | When | Severity in `pkit validate` |
|---|---|---|
| fails | An invariant a record of the capability owns is broken in a file the project can correct, or the check owed an answer and gave none. | `error` |
| asks for attention | Someone is expected to act. Where the tables below name who, the finding names them too. | `warning` |
| states a fact | No act is expected. | `info` |

Only an `error` fails `pkit validate` ([CLI reference](../../cli/README.md#validate)).

**A released library version.** A finding the project cannot correct in its own files never fails (DEC-002 point 7). A finding that lies in a library version names that version. Where the project's list of libraries marks the version released, and the version still matches its release, a finding that would fail there asks for attention instead, and names the library's owner as who acts: only the owner corrects it, in a new release. This level, and who it names, are worked out each time the check reads a finding, and are never stored. A released version whose folder no longer matches its release is the project's copy to restore, so its findings fail, `library-changed` among them (DEC-002 point 7, DEC-003 point 9). The list and its `released` field are described in [The files of the visual work](files.md#the-library-folder).

A few findings that lie in a library folder name no version, and always fail: `library-folder` and the findings on the list itself.

## What a finding says

- **A label,** a short name of what was found, such as `text-overflow`. Each label is in the tables below.
- **A location:** `<file>#<where>`, or `<file>` where nothing within the file is named, or `.` where no file is. The file is relative to the project root. `<where>` is one of:
  - a key path in a YAML file: its keys joined by `.`, an item of a list as `[<id>]`, or as `#<place>` from 1 where it has no id, such as `body.steps[plan].head`;
  - a key path in a component's file, such as `parts.head.height`;
  - a trace id of the scene, such as `figure/body/steps[plan]/head` ([trace ids](components.md#trace-ids));
  - a token path of a brand, such as `space.5`.
- **A message:** what was found. Then ` — for <who>` where someone is named, and ` — <fix>` where the finding names its fix.

## What each run judges

Without a piece named, each run judges, in order: the configuration, the location, the binding of each file of the capability's format in the location, the library folder and its list, then each piece, then each declaration of written code. For each piece it judges, in order, the ids of its content, its lock, its brand, the names of the libraries its lock names, its notations, its content against the components it fills, its produced pictures and its scenes.

`pkit visual check <piece>` judges that piece alone: the binding of its own files, and all of the above for it. It judges neither the library folder, nor its list, nor written code.

Some findings stop a piece. A piece that cannot be read is judged no further. A lock with a finding stops it before its brand. A brand that cannot be read, or a mode the brand lacks, stops it before its notations, its content, its produced pictures and its scenes. A notation's findings stop nothing. An error the check does not expect stops the piece where it arises (`unexpected-error`), and the check goes on to the next piece. The summary counts such a piece as not checked.

Where the configuration records no location and the default folder holds no visual work, the summary says so, and only the configuration is judged. Where the configuration records a location that is refused or missing, or an empty `location:`, the check reports `location`, and judges nothing but the configuration.

## Findings by area

In the tables, `<piece>/` is the piece's folder, `<location>/pieces/<piece>/`, and `<version>/` is a library version's folder, `<location>/libraries/<library>/<version>/` ([The files of the visual work](files.md#what-the-location-holds)). *Fails* is the level where the project can correct the file.

### Files and binding

| Label | What it means | Level | Where it points | What to do |
|---|---|---|---|---|
| `location` | The configuration records a location that is refused or missing, or a `location:` line with no value. | fails | the configuration, `.pkit/capabilities/visual-communication/project/config.yaml` | Restore the folder, or change the `location:` line; write the folder on an empty one, or remove it ([files](files.md#the-location)). |
| `files-unlisted` | git cannot list the location's files. | fails | `.` | The message gives git's error. |
| `file-unreadable` | The configuration, or a file of the capability's format, cannot be read ([how files are read](files.md#how-the-files-are-read)). | fails | the file | Mend the file. |
| `binding` | The file names no schema, or another schema than its name and place call for. A file at another format number is the core's data validation's to report. | fails | the file | Write the binding the message names ([the binding](files.md#the-binding)). |
| `piece-missing` | `pkit visual check <piece>` names a piece the location does not hold. | fails | `<location>/pieces` | Name a piece of the location. |
| `piece-unreadable` | `piece.yaml` or a content file cannot be read as a piece: a field of the wrong shape, a language with no content file, or a mode the brand lacks. Not reported where a `binding` finding names one of the piece's files. | fails | `<piece>/piece.yaml` | The message names the file and the field. |
| `unexpected-error` | The check of a piece stopped on an error it does not expect, such as one the engine raises on data it does not guard against. The message names the error. | fails | `<piece>/piece.yaml` | Mend what the error names in the piece's files or the components they use. Where none is at fault, report the error as a fault of the capability. |

### Libraries and locks

These follow DEC-003 point 9, and `library-name` DEC-004 point 7. A lock finding never names a library version, so it always fails.

| Label | What it means | Level | Where it points | What to do |
|---|---|---|---|---|
| `list-missing` | The library folder holds versions but no list. | fails | `<location>/libraries/libraries.yaml` | Write the list. |
| `list-unreadable` | The list cannot be read, or `libraries` is not a mapping. | fails | the list | Mend the list. |
| `library-folder` | A folder that holds a `library.yaml` is not named `X.Y.Z`. | fails | the folder | Name it after the version its `library.yaml` gives. |
| `version-unlisted` | The folder holds a version the list does not name. | fails | the list, `#libraries.<library>.versions` | Add the version. |
| `version-missing` | The list names a version the folder does not hold. | fails | the list, `#libraries.<library>.versions.<version>` | Restore the folder, or take the version off the list. |
| `library-unreadable` | The installed capability cannot read a version: its `library.yaml` cannot be read, names another library or version than its folder, or needs a newer release of the capability. | fails | `<version>/library.yaml` | Mend the file, or upgrade the capability. |
| `library-changed` | A released version's folder no longer matches the fingerprint the list keeps of it. The message names each file that changed. | fails: the project restores its own copy | `<version>/` | Restore the folder as it was released. |
| `library-name` | A library a piece's lock names takes a reserved word, or the name of a top group of the shared roles of the foundations that lock names (DEC-004 points 7 and 11). Reported once for each version. | fails, or asks the library's owner for attention in a released version | `<version>/library.yaml#name` | Rename the library, in a version of its own, and lock that version ([reserved words](files.md#reserved-words)). |
| `lock-missing` | The piece has no lock yet. | fails | `<piece>/piece.yaml#lock` | Run `pkit visual render <piece>`. |
| `lock-version`, `lock-not-held`, `lock-unreadable`, `lock-incomplete`, `lock-majors` | A lock entry is no version; or the lock names a version the project does not hold, or one the installed capability cannot read; or it leaves out a library the piece uses, or one a locked library builds on; or a locked library builds on another major of a library than the lock names. | fails | `<piece>/piece.yaml#lock` | Run `pkit visual render <piece>`, which moves a draft's lock. For a pinned piece, change the lock by hand, or unpin it and render it ([the lock](files.md#the-lock)). |

### Content against components

Each content file is read against the `fields` and `options` of each component it fills ([fields](components.md#fields), [content files](files.md#content-files)). Each finding fails, at `<piece>/content.<language>.yaml#<key path>`.

| Label | What it means | What to do |
|---|---|---|
| `id-shape` | An id is not of the id shape. | Write an id of that shape. |
| `id-twice` | An id appears twice in one list. | Make each id unique in its list. |
| `id-languages` | A list lacks ids it holds in the piece's first language, or holds ids it lacks there. The message names each. The order is free: a translation may order a list's items its own way. An id twice in one list is `id-twice`. | Give each item the same id in every language ([content files](files.md#content-files)). |
| `content-key` | A key that is no field or option of the component, and no reserved key ([content files](files.md#content-files)). The message names the nearest known key, where one is close. | Rename or remove the key. |
| `content-required` | A required field is missing. | Add the field. |
| `content-type` | A value is of another type than the field's. | Change the value. |
| `content-value` | A value is not one the field's `enum` or `const` allows. | Change the value. |
| `content-count` | A list holds fewer items than `minItems`, or more than `maxItems`. | Add or remove items. |
| `content-option` | A word the option does not take. The message names the nearest word, where one is close. | Name a word of the option. |

### Brands, tokens and contrast

The check reads the brand each piece locks, once for each brand version, against the foundations' `roles.yaml` ([brands](files.md#brands)). Each of these findings names the version it lies in, so it asks for attention in a released one. A finding marked *stops the brand* leaves the brand unread: no piece that locks it is judged further. A finding points at the file at fault, or at `<version>/` where no one file is, with the key path or token path after `#`.

| Label | What it means | Level |
|---|---|---|
| `roles-unreadable`, `roles-shape`, `role-name`, `role-type`, `role-default`, `axes-shape`, `axis-shape`, `families-shape`, `family-shape`, `pairs-shape`, `pair-shape` | The foundations' `roles.yaml` cannot be read, or one of its roles, axes, families or pairs is not of its shape. Stops the brand. | fails |
| `brand-unreadable` | The brand's `library.yaml` cannot be read. Stops the brand. It names the version its folder holds, `<version>/`, since the file cannot give it, so it asks for attention in a released one, as the others do. | fails |
| `brand-kind`, `brand-dtcg` | The library is not a brand, or names a DTCG version other than `2025.10`. Stops the brand. | fails |
| `resolver-unreadable`, `resolver-shape`, `brand-file` | The Resolver document cannot be read, holds what format 1 does not read, or names a file the version folder does not hold. Stops the brand. | fails |
| `brand-axis` | A modifier is no shared axis, lacks a context for one of the axis's modes, or has another default than the axis. Stops the brand. | fails |
| `tokens-unreadable`, `tokens-shape`, `token-name`, `token-type`, `token-value`, `token-shared-group` | A token file cannot be read, or holds a key, a name, a type or a value format 1 does not read, or a brand's own token in a group of the shared roles. Stops the brand. | fails |
| `role-missing`, `role-type` | The brand gives a shared role no value, or a value of another type, in some combination. Stops the brand. | fails |
| `alias-loop`, `alias-dangling`, `alias-type` | Aliases make a loop, lead to a token the brand does not hold, or lead to a token of another type. Stops the brand. | fails |
| `value-axis-changes-size` | A mode of a value axis changes something other than a colour. Stops the brand. | fails |
| `open-shape`, `open-unknown` | `open` in the brand's `library.yaml` is not a list, or names no role the brand exports, nor a group of them. | fails |
| `font-shape` | The capability's extension on a font token is not of its shape, or gives one family two files. | fails |
| `font-missing` | A font family the brand names has no file, or names a file the version folder or the location's `fonts/` does not hold. | fails |
| `pair-contrast` | A declared pair is below the contrast its level needs, in some combination of the brand's axes (DEC-004 points 8 and 11). | fails |
| `pair-translucent` | The colour under a declared pair is translucent in some combination, so its contrast depends on what lies under it. | asks for attention |

### Notations

The check reads each notation a piece names, once for each notation version and foundations version, against the colour families of the foundations the piece locks ([notations](files.md#notations)). Each of these findings names the version it lies in, so it asks the notation's owner for attention in a released one, and fails otherwise. None stops the piece, and content that names a concept the notation cannot read takes no finding of its own.

| Label | What it means | Where it points |
|---|---|---|
| `notation-kind` | A library the piece names under `notations` is not of kind `notation`. | `<version>/library.yaml#kind` |
| `notation-unreadable` | The notation's `library.yaml` or `notation.yaml` cannot be read, or is missing, or its `concepts` is not a mapping. The check leaves it out where a `file-unreadable` or `binding` finding names the file. | the file, or `<version>/notation.yaml#concepts` |
| `concept-shape` | A concept's name is not a name, or the concept does not map to `{colour: <family>}` with a family the foundations declare: it maps to a value, to a role, or to a family they do not declare. | `<version>/notation.yaml#concepts.<concept>` |

### Scenes

Computing a piece's scenes, one for each language, finds these (DEC-005 point 14). `pkit visual render` keeps them in the findings record, and the check reads them from it or computes them ([the findings record](#the-findings-record)). Each points at the file a person edits to mend it:

- **A finding in a component** points at that component's file: a library's in the locked version, `<version>/components/<component>.yaml`, and the piece's own at `<piece>/components/<component>.yaml`.
- **A finding in what a component's part gave** the component it places, or left out, points at the file of the component whose part it is.
- **A finding in what the content gave** points at the content file, `<piece>/content.<language>.yaml`, a value a part passed on from the content included.

Each fails, unless its row says otherwise.

| Label | What it means | Where it points |
|---|---|---|
| `component-shape` | A component holds a key, a part, an option or an exposed name its format does not allow ([a component's file](components.md#a-components-file)). | the component, `#<key path>` |
| `two-owners` | A text part gives a `height`, which its measured text sets ([primitives](components.md#primitives)). | the component |
| `formula-unreadable`, `formula-reach`, `formula-dimension`, `unknown-role` | A formula cannot be read, reads what it may not reach, has dimensions that disagree, or reads a role the brand gives no value ([errors](components.md#errors)). | the component |
| `unknown-component` | The piece's top, a part or an item names no component. A component whose file is present and cannot be read is `component-unreadable`, and what names it takes no finding. | the top's, `<piece>/piece.yaml#top`; a part's or an item's, the content or the component that names it, `#<trace>` |
| `component-unreadable` | A component's file is present and cannot be read: the message gives the reader's error, or says the file is not a mapping ([how the files are read](files.md#how-the-files-are-read)). Nothing is drawn where it is placed. The check leaves it out where a `file-unreadable` or `binding` finding names the file. | the component's file |
| `not-top` | The piece's top declares no layouts. | the top's component |
| `places-itself` | A component places itself, directly or through others ([placing a component](components.md#placing-a-component-use-and-slot)). | the component |
| `page-in-page` | A slot of pages lies inside a page, so what it places is a page inside a page. A top component with no slot of pages is part of the page that holds it, never a page inside it ([layouts](components.md#layouts)). | the content, `#<trace>` |
| `option-word`, `option-missing`, `unknown-item`, `unknown-state`, `override`, `content-shape` | What a component was given does not fit it: a word its option does not take, a missing option that names an item, an item no list holds, a state it does not declare, an `override` that names no painted part or no role, a field of the wrong shape. | the content, a value a part passed on from it included; else the component whose part gave it, or left it out |
| `loop` | References make a loop. The message names every element in it. | the component |
| `no-size` | A component asks for no size and is given none, or a list shares its size equally and is given none. | the component |
| `division-by-zero` | A formula divides by zero. | the component |
| `missing-exposed` | A formula reads an exposed part, point or item that is missing. | the component |
| `no-colour` | A part paints `:colour.<member>`, and the instance has no colour family, from its concept or by default, or has one the foundations do not declare, or one with no such member ([values, states and colour](components.md#values-states-and-colour)). | the component, `#<trace>` |
| `unknown-concept` | The content names a concept that is not `<notation>/<concept>`, that comes from a notation the piece does not name under `notations`, or that its notation does not hold ([values, states and colour](components.md#values-states-and-colour)). | the content, or the component whose part gave it, `#<trace>` |
| `unknown-role`, `role-type` | A text's style role has no value, or is no typography. | the component, `#<trace>` |
| `gets-less` | A component gets less width or height than it asks for ([what an element asks for](components.md#what-an-element-asks-for-and-what-it-gets)). | the content, `#<trace>` |
| `text-overflow` | A word is wider than its text's width. Text never shrinks to fit ([breaking lines](components.md#breaking-lines)). | the content, `#<trace>` |
| `missing-picture` | The piece has no produced output the content names. Left out where a produced-picture finding already reports that output. The fix is `pkit visual produce <piece> <output>`. | the content, or the component whose part gave it, `#<trace>` |
| `picture-variants` | The variants of a picture differ in pixel size or in the places of their points, and one scene holds them all. | as above |
| `font-missing` | A font family has no committed file, or no family measures a character. Nothing is laid out (DEC-004 point 9). The check reports it where it computes the scenes. `pkit visual render` refuses instead, and writes no record. | `<piece>/piece.yaml#brand` |
| `contrast-drawn` | A text is below WCAG's contrast against the fill under it, in a combination the piece names (DEC-004 point 8). A text of 24 px or more, or of 18.66 px or more with a weight of 700 or more, needs 3; any other text needs 4.5. The fill under each line is the last box or ellipse drawn before the text that holds the line's middle, a translucent fill laid over the one under it. A text over a picture, or over nothing, is not measured. | `<piece>/piece.yaml#<trace>` |
| `unknown-colour` | An element paints its fill or stroke with a role that is no colour role of the brand. | `<piece>/piece.yaml#<trace>` |
| `component-experimental` | The piece uses an experimental component, which its library may change in any release (DEC-003 point 9). States a fact. | `<piece>/piece.yaml#<trace>` |
| `component-deprecated` | The piece uses a deprecated component. Asks the piece's author for attention: replace it with the component its library names in its place. | `<piece>/piece.yaml#<trace>` |

The check reports `contrast-drawn`, `unknown-colour` and the two statuses at `piece.yaml`, and they name no library version. So they never take the rule of a released version.

### Losses

| Label | What it means | Level | Where it points | What to do |
|---|---|---|---|---|
| `loss` | The SVG renderer, which draws every piece's previews and exports, does not draw an element's kind (it refuses it) or one of its properties (it leaves it out). The check knows this from the renderer's declaration, before it runs (DEC-005 point 9). Or a producer reported a loss, which its output's record keeps. | asks the piece's author for attention | `<piece>/piece.yaml#<trace>`; a producer's, `<piece>/piece.yaml#produced.<output>` | Accept it under the piece's `accept-losses` ([accepting a loss](outputs.md#accepting-a-loss)), or change what draws it. An accepted loss is not reported. |

A loss of written code is `code-loss`, below. What a renderer finds only while it draws is the renderer's to report ([the loss report](outputs.md#the-loss-report)). A producer's losses are read from its record, since the check never runs a producer.

### Produced pictures

A produced picture and its record are described in [What is made from a piece](outputs.md#produced-pictures). These follow DEC-006 point 8. The fix is `pkit visual produce <piece> <output>`, unless a row says otherwise.

| Label | What it means | Level | Where it points |
|---|---|---|---|
| `produced-undeclared` | `produced/<output>/` holds files, and the piece declares no such output. Declare it under `produced:` in `piece.yaml`, or remove the folder. | asks the piece's authors for attention | `<piece>/produced/<output>` |
| `produced-record-missing` | A declared output has no record, so its picture can be neither drawn nor checked. | fails | `<piece>/produced/<output>/record.yaml#produced.<output>` |
| `produced-record-unreadable` | The record cannot be read, or is not bound. | fails | the record |
| `produced-variant-missing` | The record names a variant whose file is missing. | fails | the record, `#variants.<key>` |
| `produced-variant-changed` | A variant's file is not the one the producer wrote: its hash differs from the record's. | fails | the variant's file, `#variants.<key>` |
| `produced-unverified` | The picture cannot be checked against what it was made from. It fails where the fault lies in the piece's declaration of the output; mend it, then produce. Otherwise, as when the lock or the brand cannot be read, it asks the piece's authors for attention. | fails, or asks for attention | `<piece>/piece.yaml#produced.<output>`, or the record |
| `produced-stale` | The picture is stale ([what makes an output stale](#what-makes-an-output-stale)). The message names each change. | asks the piece's authors for attention | the record, `#fingerprint` |
| `produced-points` | A point is missing from a variant, names a variant that does not exist, is not two numbers, or lies outside the variant's pixels; or variants one scene holds differ in pixel size or in a point's place. | fails | the record, `#points` |

### Written code

Written code, its declaration and its record are described in [What is made from a piece](outputs.md#written-code). These follow DEC-006 points 4 and 8. The fix is `pkit visual write-code <name>`, unless a row says otherwise. Who is asked for attention is the project, which keeps the declaration.

| Label | What it means | Level | Where it points |
|---|---|---|---|
| `code-name` | A declaration's file name is not a name. Rename the file. | fails | `<location>/code/<name>.yaml` |
| `code-out` | `out` names no file the code may go to. Name a file of the project's tree. | fails | the declaration, `#out` |
| `code-unchecked` | The code cannot be checked, as when the brand at the declaration's lock cannot be read. Mend the declaration, then write the code. | fails | the declaration |
| `code-loss` | The writer has no form for a token, which it leaves out, and the declaration does not accept the loss. Accept it under `accept-losses` ([accepting a loss](outputs.md#accepting-a-loss)), or have the code read the value another way. | asks for attention | the declaration, `#<token path>` |
| `code-not-written` | Neither the code nor its record is present. | states a fact | the declaration |
| `code-record-missing` | The code has no record beside it. | fails | the code's file |
| `code-missing` | The record names code that is missing. | fails | `<out>.record.yaml` |
| `code-record-unreadable` | The record cannot be read, is not bound, or keeps no fingerprint and hash. | fails | the record |
| `code-edited` | The code is not what its record says was written: it was edited, or written by something else. A checkout's CRLF line endings are read as LF. Change the brand or the declaration, and write it again. | fails | the code's file |
| `code-stale` | The code is stale by a value or by its declaration ([what makes an output stale](#what-makes-an-output-stale)). | fails | the record |
| `code-stale-writer` | The code is stale only by its writer's version. Its values still hold. | asks for attention | the record |

### Exports

The check reports no finding on exports. It checks the binding of a piece's `exports.yaml`, under [Files and binding](#files-and-binding). An export refuses a stale or missing produced picture itself ([what refuses an export](outputs.md#what-refuses-an-export)).

## The findings record

`findings.yaml` in the piece's folder keeps what computing the piece's scenes found (DEC-005 point 13). `pkit visual render` writes it at each render, replacing the one before. A refused render writes none. Commit it, so the check reads it on a fresh clone.

It holds the scene findings, the losses among them. The findings on files, libraries, locks, brands, notations, content, produced pictures and written code are not in it: the check works them out at every run. Its fields:

- `pkit_schema: visual-communication:findings` and `schema_version: 1`.
- `key`: a fingerprint of every file the scenes were computed from ([input sets](#the-input-set-of-each-kind)).
- `findings`: each finding, with its `code` (its label), its `level` (`fails`, `attention` or `fact`, the level where the project can correct the file), its `message` and its `where`. It may hold `file`, `fix`, `library` (`<library>@<version>`, where it lies in a library version) and `who`.
- A finding's `file` is relative to the piece's folder, or, where it lies in a library version, to that version's folder. So the record holds when the location moves or the piece is copied. The check gives each file relative to the project root.

The record of the test piece `flow`, with a word too wide for its card, trimmed:

```yaml
pkit_schema: visual-communication:findings
schema_version: 1
key:
  form: 1
  hash: sha256
  format: 1
  value: b9492f2342da8abf3282f55b53644e4a2a3df64544d631c10dd11465fb25cabc
  inputs:
    - file: content.en.yaml
      sha256: 3eeb969325991cb4f61075bf821753e3c0268895b07d047a8a96b80add7ff239
    - file: piece.yaml
      sha256: bf975523102ee6d20fbc3c580a3c5971670f75f37a3a2e34de91c5016acb542a
    - library: foundations
      version: 1.0.0
      path: roles.yaml
      sha256: 439695a0673cb3a57d31976625bf7f90ffeb8435b8f6283a4d0f1ef1aed9e798
    # ... every other file of each locked version
findings:
  - code: text-overflow
    level: fails
    message: "figure/body/steps[plan]/head: a word of content:body.steps[plan].head is wider than the text's width 288.0 px: 3431.04 px"
    file: content.en.yaml
    where: figure/body/steps[plan]/head
```

### When the check reads it

For each piece whose lock and brand let its scenes be computed:

- **The record verifies.** Its key verifies against the files as they are now, so its findings are the piece's scene findings. The summary counts the piece as read from its findings record.
- **It is missing, or does not verify.** The check computes the piece's scenes in that run, from the files alone, and counts the piece as computed now. A record that cannot be read, or is not bound, does not verify.

The key holds no version of the engine. A new release of the capability reaches a piece's scene findings at the next render a person runs (DEC-005 point 13).

### The validation's bound

`pkit validate` runs each member under a fixed bound, and tells the check its deadline in `PKIT_COMMAND_DEADLINE`, in seconds since the epoch ([the lifecycle README, "How a registered command is run"](../../lifecycle/README.md#how-a-registered-command-is-run)). Computing scenes takes time, so the check stops computing them one second before the deadline. Each piece left whose record is missing or does not verify fails as `not-checked`, at `<piece>/findings.yaml`. The fix: run `pkit visual render <piece>`, and commit its findings record. The summary counts the piece as not checked. Without a deadline, as when a person runs `pkit visual check`, the check computes every piece that needs it.

## The fingerprint

A *fingerprint* says what an output was read from, so the check can tell when the output is stale (DEC-006 points 5 and 6). A command writes it. Nobody writes one by hand. Form 1 has these fields:

| Field | Holds |
|---|---|
| `form` | `1`, the form's version. |
| `hash` | `sha256`. |
| `format` | `1`, the format number its inputs were read at. |
| `value` | The SHA-256 of the canonical text of `inputs`, in lower-case hexadecimal. |
| `inputs` | Each input: its identity, and the `sha256` of what was read. They are sorted by the canonical text of their identity, and no identity appears twice. |

### An input's identity

An identity says what was read, apart from where the work lies. So moving the location, or copying a piece, makes nothing stale.

| Identity | What was read | Its `sha256` is the hash of |
|---|---|---|
| `{file}` | A file of the piece, by its path within the piece's folder. | the file's reading |
| `{file, keys}` | A part of a file of the piece, by the keys that lead to it. | the part's canonical text |
| `{library, version, path}` | A file of a library version, by its path within the version's folder. | the file's reading |
| `{font}` | A font of the location's `fonts/`, by its SHA-256. | the font's bytes |
| `{plugin, version}` | A producer's or a code writer's version. | the identity's canonical text |
| `{value, key}` | A brand's value at a token path, in the combination a key names. | the value's canonical text |
| `{pixels, width, height}` | A variant's pixel size. | the identity's canonical text |
| `{code}` | A declaration of written code, by its name. | the file's reading |
| `{frame}` | An element's measured frame, by its trace id. No input set of form 1 holds one. | the frame's canonical text |

### The reading

A file is read once, one way, so the same file gives the same hash on every machine. YAML and JSON are read as [How the files are read](files.md#how-the-files-are-read) says.

- **A YAML file of the capability's format** is read as its value, at the format number the fingerprint names. Its hash is taken of the value's canonical text. So a comment, the order of keys or the quoting changes nothing. Format 1 has no converter: a file at another number cannot be read, and the fingerprint does not verify.
- **A JSON file** is read as its value, and hashed as its canonical text.
- **Any other file,** a YAML file not of the format or one that does not parse included, is hashed as its bytes.
- **A brand's value** is hashed in its resolved form. A colour is `colorSpace`, `components` and `alpha`, the alpha `1` where the token gives none, and its `hex` left out. A dimension is `value` and `unit`, a font family a list of names. So a value written another way gives the same hash.
- **Canonical text** is the JSON Canonicalization Scheme (RFC 8785). Keys come in the order of their UTF-16 code units, with no white space. Strings are escaped as ECMAScript's `JSON.stringify` escapes them. Numbers are written as ECMAScript writes them, so `1.0` is `1`. An integer beyond 2⁵³ − 1 is refused. Its text is hashed as UTF-8.

### The input set of each kind

| Kind | Kept in | Its inputs |
|---|---|---|
| A piece's findings | `findings.yaml`, as `key` | The piece's own files. Every file of each version the lock names. Each font of the location's `fonts/` that its scenes read. |
| A produced picture | the output's `record.yaml` ([its record](outputs.md#the-record-of-a-produced-output)) | The part of `piece.yaml` at `produced.<output>`. Each value its inputs name, in each combination the piece names. Each variant's pixel size. The producer's version. |
| Written code | `<out>.record.yaml` ([its record](outputs.md#the-record-beside-the-code)) | The declaration's file. Each value written, in each combination of the brand's axes. The code writer's version. |
| An export | each version of `exports.yaml` ([the record of exports](outputs.md#the-record-of-exports)) | As a piece's findings, and the part of `piece.yaml` at `exports`. |
| A released library version | its entry in the list, as `hash` ([files](files.md#the-library-folder)) | Every file of the version's folder. |

A piece's *own files* are the files of its folder as git lists them, tracked or untracked but not ignored. They leave out `findings.yaml` and `exports.yaml`. Under `produced/`, only each output's `record.yaml` is one of them, since it holds the hash of each of its pictures. A library version's files are listed the same way.

### How a fingerprint verifies

The check works out the input set again from the files as they are now, under the form the fingerprint names. It compares each input's hash with the one kept, and names each input that changed, is no longer read, or is read now. A fingerprint does not verify where any of these differs. Nor does one whose `value` is not the hash of its own `inputs` (it was edited), or whose form, hash or format number the capability does not read.

### What makes an output stale

- **A produced picture** is stale when its fingerprint does not verify, or when a combination the piece names maps to no variant in its record. Its inputs are values, not the engine's version, so a release of the capability makes no picture stale; the producer's version is compared (DEC-006 point 5).
- **Written code** is stale when its fingerprint does not verify. Where it verifies with the writer's version the fingerprint names, the code is stale only by its writer's version, and asks for attention (`code-stale-writer`). Otherwise it fails (`code-stale`).
- **Never compared:** the outside programs a producer called, the machine, the time and the capability's release. A record keeps them beside the fingerprint (DEC-006 point 5).

## In `pkit validate`

The capability registers its check as the validator `check` in the `validators` block of its `package.yaml`. So `pkit validate` runs it as the member `visual-communication:check`, with `--json`, from the project root (DEC-002 point 6). The check reads only the project's files: it is offline, writes nothing and runs no program of the project's. `pkit sync` provisions its dependencies.

With `--json` it prints one document. `summary` holds one line. `findings` holds each finding with its `severity`, its `location`, its `message` (who and fix included) and its `label`:

```json
{"summary": ["1 piece(s) in `visual`: the scenes of 1 read from their findings record, of 0 computed now, of 0 not checked."],
 "findings": [
   {"severity": "error",
    "location": "visual/pieces/flow/content.en.yaml#figure/body/steps[plan]/head",
    "message": "figure/body/steps[plan]/head: a word of content:body.steps[plan].head is wider than the text's width 288.0 px: 3431.04 px",
    "label": "text-overflow"}]}
```
