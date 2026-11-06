---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/package.yaml
        - .pkit/capabilities/visual-communication/scripts/add.py
        - .pkit/capabilities/visual-communication/scripts/render.py
        - .pkit/capabilities/visual-communication/scripts/export.py
        - .pkit/capabilities/visual-communication/scripts/produce.py
        - .pkit/capabilities/visual-communication/scripts/write-code.py
        - .pkit/capabilities/visual-communication/scripts/look.py
        - .pkit/capabilities/visual-communication/scripts/pages.py
        - .pkit/capabilities/visual-communication/scripts/_lib/viewing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/viewing_tool.py
        - .pkit/capabilities/visual-communication/scripts/_lib/root.py
        - .pkit/capabilities/visual-communication/scripts/_lib/location.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/exports.py
        - .pkit/capabilities/visual-communication/scripts/_lib/framing.py
        - .pkit/capabilities/visual-communication/scripts/_lib/values.py
        - .pkit/capabilities/visual-communication/scripts/_lib/keys.py
        - .pkit/capabilities/visual-communication/scripts/_lib/code.py
        - .pkit/capabilities/visual-communication/scripts/_lib/copies.py
        - .pkit/capabilities/visual-communication/scripts/_lib/before_after.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/layout.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/__init__.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/seam.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/svg.py
        - .pkit/capabilities/visual-communication/scripts/_lib/canvas.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/svg_declaration.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/pdf.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/pdf_declaration.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/css.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/css_declaration.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/json.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/json_declaration.py
        - .pkit/capabilities/visual-communication/schemas/defs.schema.json
        - .pkit/capabilities/visual-communication/schemas/piece.schema.json
        - .pkit/capabilities/visual-communication/schemas/exports.schema.json
        - .pkit/capabilities/visual-communication/schemas/produced-record.schema.json
        - .pkit/capabilities/visual-communication/schemas/code.schema.json
        - .pkit/capabilities/visual-communication/schemas/code-record.schema.json
        - .pkit/capabilities/visual-communication/schemas/values.schema.json
      record:
        - visual-communication:DEC-001#2
        - visual-communication:DEC-002#1
        - visual-communication:DEC-002#8
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#5
        - visual-communication:DEC-005#7
        - visual-communication:DEC-005#8
        - visual-communication:DEC-005#9
        - visual-communication:DEC-005#10
        - visual-communication:DEC-005#12
        - visual-communication:DEC-006#1
        - visual-communication:DEC-006#2
        - visual-communication:DEC-006#3
        - visual-communication:DEC-006#4
        - visual-communication:DEC-006#5
        - visual-communication:DEC-006#7
        - visual-communication:DEC-006#8
        - visual-communication:DEC-008#5
        - visual-communication:DEC-011
        - visual-communication:DEC-012
        - visual-communication:DEC-013#5
        - visual-communication:DEC-015#1
        - visual-communication:DEC-015#2
        - visual-communication:DEC-015#3
        - visual-communication:DEC-015#4
        - visual-communication:DEC-015#5
        - visual-communication:DEC-015#6
      artefact:
        - .pkit/capabilities/visual-communication/components.md#exposes
        - .pkit/capabilities/visual-communication/components.md#options
        - .pkit/capabilities/visual-communication/components.md#primitives
        - .pkit/capabilities/visual-communication/components.md#trace-ids
        - .pkit/capabilities/visual-communication/components.md#what-a-scene-holds
        - .pkit/capabilities/visual-communication/files.md#keys-of-combinations
        - .pkit/capabilities/visual-communication/files.md#rolesyaml
        - .pkit/capabilities/visual-communication/files.md#shapes
        - .pkit/capabilities/visual-communication/files.md#the-clones-local-folder
        - .pkit/capabilities/visual-communication/files.md#the-lock
---

# What is made from a piece

Plugins make what the capability gives out. A renderer draws a piece's scenes as previews and exports. A producer makes a picture a piece shows. A code writer writes a brand out as code. What each command reads, writes and refuses as a whole is under *Commands* in the README.

## Contents

<!-- pkit:contents -->
- [Plugins](#plugins)
- [The SVG renderer](#the-svg-renderer)
- [The PDF renderer](#the-pdf-renderer)
- [Exports](#exports)
- [Produced pictures](#produced-pictures)
- [Written code](#written-code)
- [The viewing step](#the-viewing-step)
<!-- /pkit:contents -->

## Plugins

A *plugin* is code that meets the engine at one *seam*: what the engine hands it, and what it takes back. There are three kinds:

- A *renderer* draws a scene in one medium.
- A *producer* makes a picture while a piece is prepared. A person or an agent runs it with `pkit visual produce`. No render, check or export runs it.
- A *code writer* writes a brand's resolved values as code in one language.

Every plugin is the capability's, and a project adds none (DEC-005 point 12): no file, setting or environment variable adds one. The capability ships:

- the `svg` renderer, at version 1.0.1
- the `pdf` renderer, at version 1.0.0
- the `css` code writer, at version 1.0.0
- the `json` code writer, at version 1.0.0

No producer ships yet.

Each plugin declares what it can take, so the capability knows it without running the plugin. A renderer declares each primitive it draws, and each property of it. A producer declares its inputs, each a role of one *value type* (a token's DTCG type, such as `color`), and the value types it uses. A code writer declares the value types its language has a form for, the forms of its spelling, the kinds of axis it spells, and whether it takes a `prefix`.

Each plugin also declares what it needs beyond the project's files: the outside programs it calls (`programs`) and the services it reaches (`services`), each a list of names (DEC-005 point 9). The SVG and PDF renderers and the CSS and JSON code writers call no outside program and reach no service. A producer that names a service is refused before it runs, since a plugin that reaches a service runs only where the project's configuration turns it on, and format 1's configuration turns none on (DEC-002 point 8). So is a producer that names a program the machine lacks.

### Versions

- **A plugin's own version,** `X.Y.Z`, is apart from the capability's. It rises when the same input could give another output. Reference outputs pinned to it in the capability's tests catch a change made without a new version (DEC-005 point 9).
- **The seam's version** is 3. A plugin's declaration names the seam version it reads, and the capability refuses a plugin of another version. Version 2 hands a renderer a text's runs, each with its own paint and fonts ([What a scene holds](components.md#what-a-scene-holds)). Version 3 hands it a line's arrowheads, and a tie's connector with its points and the elements its ends meet (DEC-011). What a producer and a code writer are handed and return is as version 1 had it.
- **What rose with ties.** The seam rose to 3, since a renderer must read a line's new properties. The SVG renderer stays at 1.0.1, and the CSS code writer at 1.0.0. A scene of seam 2 holds no arrowhead and no connector, and each draws it as before. The PDF renderer reads seam 3 from its first version, 1.0.0.
- **The document of values** that producers and code writers read has its own version, 1 ([The hand-over](#the-hand-over)).
- **A code writer's spelling** has versions of its own, called *forms*. A declaration of written code names its form, and a writer keeps writing every form it shipped (DEC-005 point 8). The CSS writer writes form 1. The JSON writer writes form 1, which is version 1 of the document of values ([The JSON code writer](#the-json-code-writer)).
- **None of these versions** is the format number of the files a project keeps.

### The loss report

A *loss* is something a plugin cannot take as it is given. Every loss has one form:

| Field | What it holds |
|---|---|
| `plugin` | the plugin's name |
| `what` | what was lost: an element's [trace id](components.md#trace-ids), such as `figure/body/steps[plan]/box`, or a token path |
| `did` | what the plugin did instead: `approximated`, `picture` (drew it as a picture), `left-out` or `refused` |
| `why` | why, in words |

Before a plugin runs, the capability compares what the plugin is handed with its declaration, and reports what the plugin cannot take. A renderer also reports what it finds while it draws. An input a producer cannot take is refused before it runs ([Declaring a produced output](#declaring-a-produced-output)). What a producer could not make as it was handed, it returns with its picture, and its record keeps ([What a producer writes and returns](#what-a-producer-writes-and-returns)).

### Accepting a loss

A person accepts a known loss where the output is declared: a renderer's or a producer's under `accept-losses` in the piece's `piece.yaml`, a code writer's under `accept-losses` in the declaration of written code ([The declaration](#the-declaration)). Each entry names the plugin, what it loses, and a reason that is not blank:

```yaml
accept-losses:
  - plugin: svg
    what: figure/body/steps[plan]/box
    reason: Thin.
```

An entry matches a loss by its `plugin` and its `what` alone. The command that runs the plugin no longer prints an accepted loss, and the check no longer reports it (*Losses* in *What the check reports*).

## The SVG renderer

The `svg` renderer draws a scene as SVG files: one for each page, each language and each combination of modes the piece names. The previews and the SVG exports are its files.

- **Elements.** A group is drawn as `<g>`, a box as `<rect>`, an ellipse as `<ellipse>`, a line as `<line>`, a text as `<text>` and an image as `<image>`. A tie's connector whose route turns is drawn as `<polyline>`, through each of its points. Every element carries its trace id as `data-id`. A connector names the elements its ends meet, `data-start` and `data-end`. A group a component drew names it as `data-component`, and its library's version, if any, as `data-version`, the page's own group included.
- **The file.** The `<svg>` element names the piece, the page's trace id, the language, the combination's key, and the renderer with its version: `data-piece`, `data-page`, `data-language`, `data-key`, `data-renderer`.
- **Colours.** A colour stays a role in the scene. The renderer takes its value from the brand's resolved values in the combination it draws, as `#rrggbb`, with a `fill-opacity` or `stroke-opacity` where the colour is translucent.
- **Shapes and text.** A box's stroke lies inside its frame. An arrowhead is a `<marker>` that the page's `<defs>` holds once for each colour it is drawn in. It is a triangle five strokes long, its tip at the line's end, in the line's stroke. Each line of a text is drawn as the engine broke it, at its own baseline, anchored at the start, the middle or the end of the text's width. The `<text>` takes the font and the paint of the text's first run. Each run that looks otherwise, in its family, size, weight or paint, is drawn in a `<tspan>` of its own that names all four. So a text of one run is drawn as it was before runs.
- **Pictures.** A produced picture is embedded as PNG data: the variant that serves the combination drawn ([Variants](#variants)).
- **Fonts.** Each font the page draws in, for each family and weight a run is drawn in, is embedded as an `@font-face` rule, from the brand's committed font file, never from the machine's fonts, cut down to the characters drawn in it. The renderer draws in the brand's default font profile. A family's name is written as a CSS string in double quotes, in its `@font-face` rule and in each text's `font-family`. A `"` or a `\` takes a `\` before it. Each `<`, `>` and `&`, each control character and each character XML 1.0 does not allow is written as the escape of its code point: a `\`, the code point in hexadecimal, and a space. So no name a brand gives can end the drawing's `<style>` element, or leave the file malformed XML.
- **The same bytes.** Lengths are written to 1/100 px, and attributes in one order, so the same scene and values give the same file.

### Previews

A *preview* is a render for a person to look at, which `pkit visual render` draws. It takes no version number, and is never an export (DEC-006 point 7). The previews of a piece lie in `.pkit/capabilities/visual-communication/project/local/previews/<piece>/`, a folder local to the clone, of which no file is committed (DEC-002 point 1; [The clone's local folder](files.md#the-clones-local-folder)). Each is named `<piece>.<language>.<key>.svg`, such as `flow.en.colour-scheme.dark.svg`, where the key names the combination of modes ([Keys of combinations](files.md#keys-of-combinations)). A piece of more than one page adds the page's number, from 1: `<piece>.<language>.<key>.<n>.svg`. The scenes `pkit visual add` draws both ways take the same names ([The clone's local folder](files.md#the-clones-local-folder)).

### What the SVG renderer loses

Before it draws, the capability compares each scene with the renderer's declaration. An element of a type the declaration does not name is `refused`, and left out of the file. A property the declaration does not name for its type is `left-out`. The declaration names every primitive and property a scene of format 1 holds, so this finds no loss in format 1. While it draws, the renderer reports three losses of its own. Two are `left-out`:

- **a fill or a stroke** whose role has no colour under the brand in the combination drawn, a run's fill included. A fill is then `none`. A library's role the brand gives no value is drawn at its default ([`roles.yaml`](files.md#rolesyaml)), so it is lost only where its chain of defaults reaches no colour.
- **an image** whose produced picture has no variant for the combination drawn.

The third is `refused`: a line that holds neither its ends nor its points, which is left out of the file. Every line of a scene the engine computes holds its ends ([What a scene holds](components.md#what-a-scene-holds)).

## The PDF renderer

The `pdf` renderer draws a scene as one PDF file for each language and each combination of modes the piece names. The file holds the scene's pages in order, one PDF page for each. It draws the exports a piece declares as `pdf` ([Exports](#exports)); previews stay SVG.

- **Pages.** Each page is as large as its frame. Each px of the scene is 0.75 pt of the page, CSS's 96 px to the inch. Format 1's top components declare no physical size, so the renderer's declaration states this mapping as its `unit` (DEC-001 point 2).
- **Shapes and lines.** A box's stroke lies inside its frame, as in the SVG renderer. Rounded corners and ellipses are cubic Bézier curves. A line, or a tie's connector through each of its points, is stroked with SVG's miter limit. An arrowhead is the SVG renderer's triangle: five strokes long, its tip at the line's end, in the line's stroke.
- **Colours.** A colour stays a role in the scene. The renderer takes its value from the brand's resolved values in the combination it draws, as DeviceRGB. A translucent colour takes an opacity of its own.
- **Text.** Each line of a text is drawn as the engine broke it, at its own baseline, anchored at the start, the middle or the end of the text's width. Each run is drawn in its own font, size and paint. The renderer shapes each span again with HarfBuzz from the committed font file, as the engine shaped it (DEC-005 point 4). It places each glyph at the advance shaped, so kerning is kept.
- **Fonts.** Each family a run draws in is embedded once in the file, from the brand's committed font file, never from the machine's fonts. It is cut down to the glyphs the file draws in it. Each keeps a map from each glyph back to its characters, so the text can be searched and copied. A CFF font is embedded as CFF, and a TrueType font as TrueType. A font of other outlines is not embedded ([What the PDF renderer loses](#what-the-pdf-renderer-loses)).
- **The file** names its language, `/Lang`, and the renderer with its version, `/Producer`.
- **The same bytes.** The file holds no date, and its streams are not compressed. So the same scene and values give the same file on every machine.

### What the PDF renderer does not carry yet

The PDF is not tagged. It carries no alternative text, no reading order and no structure such as headings (DEC-005 point 5). Its declaration says so under `not-carried`, and a later version adds them ([project-kit#2570](https://github.com/aleskalfas/project-kit/issues/2570)).

### What the PDF renderer loses

Before it draws, the capability compares each scene with the renderer's declaration, as for the SVG renderer ([What the SVG renderer loses](#what-the-svg-renderer-loses)). The declaration names every primitive of format 1's scene but the image. So an image is `refused`, and left out of the file. No producer ships yet, so no piece can show a picture yet ([Produced pictures](#produced-pictures)); a later version draws it. The capability reports the loss before the renderer runs, unless the piece accepts it (DEC-005 point 9; *Losses* in *What the check reports*).

While it draws, the renderer reports three losses of its own:

- **a fill or a stroke** whose role has no colour under the brand in the combination drawn, `left-out`. It is not drawn, but a run's text is drawn unpainted, so it can still be searched.
- **a font file** whose outlines are neither CFF nor TrueType, such as CFF2, `left-out`. Its family is not embedded, and the text drawn in it is left out, keeping its place in the line. The renderer never draws that text in another font (DEC-005 point 10).
- **a line** that holds neither its ends nor its points, `refused`, and left out of the file.

## Exports

An *export* is a set of files a piece is handed out as. Each export run is one *version*, numbered within its piece (DEC-006 point 7).

- **Formats.** A piece names its formats under `exports` in its `piece.yaml`. Format 1 knows two: `svg`, which the SVG renderer draws, and `pdf`, which the PDF renderer draws.
- **What a run makes:** for `svg`, one file for each page, each language and each combination of modes the piece names; for `pdf`, one file for each language and combination, which holds every page in order. Each is drawn from the scenes under the lock `piece.yaml` holds.
- **The number.** A run takes the number one higher than the highest version the piece's `exports.yaml` records or any file of its exports folder carries, or 1 where there is none. Every file of the run carries it, so version 3 in English matches version 3 in Czech. A file the record does not name, such as one a failed run could not remove, is never overwritten, and refuses no later run.
- **The name:** `<piece>.v<N>.<language>.<key>.<format>`, such as `flow.v1.en.colour-scheme.dark.svg`. It carries the piece and the version, since an exported file travels alone. An SVG file of a piece of more than one page adds the page's number, from 1, as a [preview](#previews) does: `<piece>.v<N>.<language>.<key>.<n>.svg`, such as `deck.v1.en.default.2.svg`. A PDF holds every page, so its name carries none: `deck.v1.en.default.pdf`.
- **Where:** `.pkit/capabilities/visual-communication/project/local/exports/<piece>/`, local to the clone and never committed. No export overwrites another. What is committed is the record of exports, in the piece's folder.

### The record of exports

`exports.yaml` lies in the piece's folder. `pkit visual export` rewrites it, and nobody edits it. It holds one entry for each version, the oldest first. Here it is with its fingerprint left out:

```yaml
pkit_schema: visual-communication:exports
schema_version: 1
versions:
  - version: 1
    files:
      flow.v1.en.default.svg: 59e59277986cb50595fbea07b1a4ee396639d94e4bea63570b70232d8f6816e6
      flow.v1.en.colour-scheme.dark.svg: ed229c228ca2eaff8c0b5e30a09556b34010ed772f224a6fa54e3eb50fd13179
    recorded: {time: '2026-11-02T09:52:03Z', state: draft, capability: 0.1.0, renderers: {svg: 1.0.0}, used: {square: 7c4d18f3637685d8a16ab729007003c4a6b4536218d54ff7302fd7beb5850bd5}, used-stale: []}
```

| Field | What it holds |
|---|---|
| `version` | the version's number, from 1 |
| `fingerprint` | the version's fingerprint, whose inputs *The input set of each kind* in *What the check reports* lists |
| `files` | each file the run made, by name, with the SHA-256 of the file |
| `recorded` | only recorded, never compared, so a new release of the capability makes no export stale: the `time` in UTC, the piece's `state` then (`draft`, the only state of format 1), the release of the `capability`, each of the `renderers` with its version, each produced output the run used with the version of its picture, the `value` of its record's fingerprint (`used`), and each of those it used while it was stale (`used-stale`) |

### What refuses an export

An export run is refused, and writes nothing, when:

- the piece names no format under `exports`;
- the piece has no lock yet, or its lock does not hold: a version the project does not hold or cannot read, a library the piece uses that the lock leaves out, or a major that does not fit what a library builds on;
- the brand cannot be read, or the piece names a mode its brand lacks;
- a font has no file, or a character has no font family that can measure it;
- a produced picture the piece shows is missing: it has no record, or its record names a variant file that is missing;
- a produced picture is stale (*What makes an output stale* in *What the check reports*), unless `--use-stale <output>` names it;
- `--use-stale` names an output the piece does not declare under `produced`: the refusal names those it declares;
- the piece has no page in one of its languages, so the version would hold no file in it;
- a file the run would write, `exports.yaml` among them, is reached through a link;
- `exports.yaml` cannot be read, or holds no list of numbered versions.

Each of these is found before the first write, so a refused run records no location either. `--use-stale` naming a declared output that is not stale refuses nothing: the run uses the picture as it is, and says it was not stale.

## Produced pictures

A *produced picture* is a picture a producer makes for one piece while it is prepared, such as a 3D render (DEC-006 point 1). It takes every value from the brand, and holds none of the piece's words: the piece places each label as its own text (DEC-006 point 2).

No producer ships yet ([Plugins](#plugins)), so `pkit visual produce` refuses every producer a piece names, and no piece has a produced picture. What follows is the contract every producer meets. The capability's tests run a producer kept for them alone.

### Declaring a produced output

A piece declares each produced output under `produced` in its `piece.yaml`, by the output's name:

```yaml
produced:
  marker:
    producer: square
    inputs: {fill: accent}
    pixels: {width: 64, height: 64}
```

- **`producer`:** the producer's name.
- **`inputs`:** each input names a role of the brand by its token path, never a raw value. The producer must take the input, the brand must have the role, and the role must be of the value type the input takes. Every input the producer requires is given. The values come from the brand version the piece's lock names.
- **`pixels`:** the width and the height of every variant, in whole pixels from 1, fixed before the producer runs (DEC-006 point 3).

### Variants

A producer makes one picture for each distinct set of the values its inputs read, never one for each combination of modes. Each such picture is a *variant*. The command resolves each role in every combination the piece names, and the combinations that give the same values share one variant (DEC-006 point 3).

A variant is named by the first key it serves, in key order ([Keys of combinations](files.md#keys-of-combinations)). For example, the test brand's `accent` changes with the colour scheme, and not with contrast. A piece drawn in both modes of both axes has four combinations and two variants: `default` serves `default` and `contrast.high`, and `colour-scheme.dark` serves `colour-scheme.dark` and `colour-scheme.dark+contrast.high`.

### The hand-over

The *hand-over* is what a producer receives. The command writes it as JSON before the producer runs, at `.pkit/capabilities/visual-communication/project/local/handover/<piece>/<output>.json`, local to the clone.

It opens with the *document of values* of the roles the inputs name alone (DEC-005 point 7), which `document` and `version` name: `visual-communication/values`, 1. `lock` holds the versions of the brand and of the foundations library it builds on, and `keys` each combination the piece names, in key order. `tokens` holds each role by its token path, with its value type and its value in each combination. A value is in its DTCG form, made canonical: a colour with `alpha` and without `hex`, a font family a list of names. Three keys follow. `inputs` gives the token path each input reads. `variants` gives each variant's key, the combinations it serves, and its pixels. `frames` holds the measured frames of the scene a producer reads; format 1 hands over none. A variant's values are those of its own key:

```json
{
  "document": "visual-communication/values",
  "version": 1,
  "lock": {"foundations": "1.0.0", "test-brand": "1.0.0"},
  "keys": ["default", "colour-scheme.dark", "contrast.high", "colour-scheme.dark+contrast.high"],
  "tokens": {
    "accent": {
      "type": "color",
      "values": {
        "default": {"colorSpace": "srgb", "components": [0.0353, 0.4118, 0.8549], "alpha": 1},
        "colour-scheme.dark": {"colorSpace": "srgb", "components": [0.2667, 0.5765, 0.9725], "alpha": 1},
        "contrast.high": {"colorSpace": "srgb", "components": [0.0353, 0.4118, 0.8549], "alpha": 1},
        "colour-scheme.dark+contrast.high": {"colorSpace": "srgb", "components": [0.2667, 0.5765, 0.9725], "alpha": 1}
      }
    }
  },
  "inputs": {"fill": "accent"},
  "variants": {
    "default": {"serves": ["default", "contrast.high"], "pixels": {"width": 64, "height": 64}},
    "colour-scheme.dark": {"serves": ["colour-scheme.dark", "colour-scheme.dark+contrast.high"], "pixels": {"width": 64, "height": 64}}
  },
  "frames": {}
}
```

### What a producer writes and returns

The command runs the producer with the hand-over and an empty folder, `.pkit/capabilities/visual-communication/project/local/handover/<piece>/<output>/`.

- **It writes** one PNG for each variant, `<variant key>.png`, at the variant's pixels. Nothing else it writes is kept.
- **It returns** a mapping with `points`, each exposed point with its place in each variant; `programs`, each outside program it called with its version, which its declaration names; and `losses`, what it could not make as it was handed, each loss in the one form ([The loss report](#the-loss-report)) and naming the producer as its `plugin`. `programs` and `losses` may be left out. `programs` is only recorded. Any other key refuses the run.
- **Its losses** are kept in the record, each once. The command prints each one the piece does not accept, as `loss: the <producer> producer <did> `<what>`: <why>`, and the check reports it until the piece accepts it ([Accepting a loss](#accepting-a-loss)).

*Exposed points* are named points in a picture's pixels that the piece may point at, such as to place a label (DEC-005 point 5). They follow these rules (DEC-006 points 2 and 3):

- **A point's name** takes the name shape ([Shapes](files.md#shapes)).
- **Its place** in each variant is an `x` and a `y` in that variant's pixels, from the top-left corner, with `y` going down. `x` lies from 0 to the width, and `y` from 0 to the height.
- **Every variant** exposes the same points, by name. The variants one scene holds share one pixel size, and keep each point at the same place.

What `pkit visual produce` then keeps is under *Commands* in the README. Commit the `produced/<output>/` folder: the render and the check read the picture from it on a fresh clone (DEC-006 point 4).

### The record of a produced output

`produced/<output>/record.yaml` lies in the piece's folder, beside the variants. `pkit visual produce` writes it, never a person. Here it is with its fingerprint left out:

```yaml
pkit_schema: visual-communication:produced-record
schema_version: 1
variants:
  default: {file: default.png, pixels: {width: 64, height: 64}, sha256: 846391bd55eb7c3ca617975b950a628e2b19d5ed4a6d8d7789d06b9e0895bb26}
  colour-scheme.dark: {file: colour-scheme.dark.png, pixels: {width: 64, height: 64}, sha256: cccb5b8de0fa626953e4d7fbce1441a4911bd1050f9eebb4ce355c8722042258}
combinations:
  default: default
  colour-scheme.dark: colour-scheme.dark
  contrast.high: default
  colour-scheme.dark+contrast.high: colour-scheme.dark
points:
  tip: {default: {x: 32.0, y: 0}, colour-scheme.dark: {x: 32.0, y: 0}}
losses: []
recorded: {plugins: {square: 1.0.0}, programs: {}, machine: darwin arm64, time: '2026-11-02T07:33:38Z', capability: 0.1.0}
```

| Field | What it holds |
|---|---|
| `fingerprint` | the fingerprint of what the producer read (*The fingerprint* in *What the check reports*) |
| `variants` | each variant by its key: its `file`, its `pixels`, and the SHA-256 of the file |
| `combinations` | each combination the piece names, by its key, with the variant that serves it |
| `points` | each exposed point, with its place in each variant |
| `losses` | each loss the producer reported, in the one form ([The loss report](#the-loss-report)); empty where it lost nothing |
| `recorded` | only recorded, never compared: the producer with its version (`plugins`), each outside program it called with its version (`programs`), the `machine`, the `time` in UTC, and the release of the `capability` |

### A label at an exposed point

The piece places a label at an exposed point in its content, and the label stays ordinary text. The component that draws the picture exposes its image part, and so the picture's points ([Exposes](components.md#exposes)). The component that places the label declares an option that names an item and one of its points, and reads the point in a formula ([Options](components.md#options)). The content gives that option an item's id and a point's name. Here the test library's `callout` places its label `Here` at the point `tip` of the picture `square`:

```yaml
- id: note
  use: tests/callout
  pictures: [{id: square, output: square}]
  label: Here
  at: {item: square, point: tip}
```

The engine maps the point from the variant's pixels into the frame the picture fills, so the point scales with the picture (DEC-006 point 3). How a picture fills its frame is under [Primitives](components.md#primitives).

## Written code

*Written code* is a brand written out by a code writer, such as the CSS custom properties a web page reads. A project declares it in the location, as it declares a piece (DEC-002 point 1).

### The declaration

A declaration is `code/<name>.yaml` in the location. Its name is the file's name, of the name shape, and `pkit visual write-code <name>` writes the code it asks for:

```yaml
pkit_schema: visual-communication:code
schema_version: 1
writer: css
form: 1
brand: test-brand
lock:
  foundations: 1.0.0
  test-brand: 1.0.0
out: web/brand.css
```

| Field | What it holds |
|---|---|
| `writer` | the code writer: `css` or `json` |
| `form` | the form of the writer's spelling: `1` |
| `brand` | the brand, by its library's name |
| `lock` | a version of the brand and of every library it builds on, and of any other library whose roles the code holds, each one the project holds and the capability reads, whose majors fit what each builds on |
| `out` | where the code goes: a file of the project's tree |
| `prefix` | optional: a name that opens every name the code writes. The `json` writer takes none ([The JSON code writer](#the-json-code-writer)) |
| `accept-losses` | optional: the losses a person accepted ([Accepting a loss](#accepting-a-loss)) |

- **The lock is the declaration's own.** A person moves it on purpose, and no command moves it (DEC-005 point 7). So the code changes only when the declaration changes, or when the person names the declaration to `pkit visual add`. Naming it lets the command replace a copy not yet released that the lock names, under the same number ([The lock](files.md#the-lock), DEC-013 point 5). The run that leaves the copy prints the difference in the code first.
- **What the code holds:** the document of values under the lock: every token the brand exports, and every other role of each library of components the lock names, at the brand's value or at its default (DEC-008 point 5), in every combination of the brand's axes, at the versions the lock names. A library's role that has no value under the brand is left out. Code that reads a library's role names that library's major in its lock, since the library promises its names by major. A brand built on a base is read over the base the lock names. The code follows no piece's modes.
- **Where `out` may not lie:** outside the repository, under `.pkit/`, under a hidden folder, or in the location's library folder, its `code/` folder or its `pieces/` folder. Nor may it be reached through a link, or be a folder.
- **Committing the code** is the project's choice, as for any file its build writes. Its record goes with it (DEC-006 point 4).

### The record beside the code

`pkit visual write-code` writes a record beside the code, `<out>.record.yaml`, such as `web/brand.css.record.yaml`. After its binding, it holds the `fingerprint` of what the code was written from (*The fingerprint* in *What the check reports*), the `sha256` of the code as written, and what is only `recorded`, never compared: the writer with its version (`plugins`), the outside programs (`programs`, none), the `machine`, the `time` in UTC, and the release of the `capability`.

### The CSS code writer

The CSS writer writes one style sheet. Form 1 spells it as follows.

- **Names.** Each token path gives one custom property: `--`, then the `prefix` and `--` where the declaration names one, then the path's segments joined by `--`. A segment keeps its own single hyphens, so no two paths give one name: `space.1` gives `--space--1`, `text-primary` gives `--text-primary`, a library's role `test-parts.note` gives `--test-parts--note`, and `space.1` with the prefix `brand` gives `--brand--space--1`.
- **Values.** A `color` is `#rrggbb`, each channel rounded to 8 bits, half up, or `#rrggbbaa` where its alpha is not 1. A `dimension` is its number and `px`. A `fontFamily` is its names, each in double quotes, joined by `, `. A `fontWeight` or a `number` is the number, in the capability's canonical text, such as `1.4` or `16`.
- **Modes.** Each mode is switched by an attribute, `data-<axis>="<mode>"`, on one element: the page's root by default. An area that changes modes sets every axis's attribute on its own element; the root may leave out an axis at its default. Form 1 spells value axes alone, and refuses a brand with an axis of another kind.

The rules come in this order:

1. **`:root`** holds every token, at the combination of every default.
2. **One rule for each mode** of each axis, `[data-<axis>="<mode>"]`: the axes in the order of their names, each axis's modes in the order the foundations declare them. A mode that is not the default holds every token the axis changes in some combination, at that mode, with every other axis at its default. The default mode holds each token whose first axis that changes it, in name order, is this axis, at every default. So an area may set a default mode inside another area.
3. **One rule for each combination** of two or more modes that are not their axis's default, in key order, its selectors joined: `[data-colour-scheme="dark"][data-contrast="high"]`. It holds only the tokens whose value there differs from what the rules before it give. More attributes are more specific, so it wins over the rules of fewer.

A rule with no token is not written. A rule holds each token once, in the order of the token paths. A comment opens the sheet, and names the form and the lock. The test brand gives this sheet, its comment left out and its rules cut short:

```css
:root { --accent: #0969da; --font--body: "Source Sans Pro"; --space--1: 4px; }
[data-colour-scheme="light"] { --accent: #0969da; }
[data-colour-scheme="dark"] { --accent: #4493f8; }
[data-contrast="high"] { --line: #000000; }
[data-colour-scheme="dark"][data-contrast="high"] { --line: #ffffff; }
```

It holds no `[data-contrast="standard"]` rule: every token the contrast axis changes, the colour scheme changes too, and its name comes first. The writer writes each declaration on a line of its own.

**Losses.** A token of a value type the writer has no form for is left out, as a loss known before the writer runs. In form 1 that type is `typography`, such as the test brand's `type.body`.

### The JSON code writer

The JSON writer writes the [document of values](#the-hand-over) as one file, for a program that reads data, such as a game's runtime. It adds nothing to the document and leaves nothing out. A declaration names `writer: json`, `form: 1` and an `out` such as `game/brand.json`.

- **Its form.** Form 1 is version 1 of the document. The schema `.pkit/capabilities/visual-communication/schemas/values.schema.json` states that form, so a program can check the file against it. A later version of the document is a new form, and the writer keeps writing this one ([Versions](#versions)).
- **What it holds.** It holds what the code holds ([The declaration](#the-declaration)), in the fields the hand-over opens with, and no others.
- **Names.** A token keeps its path as the brand exports it, such as `space.1`. So the writer takes no `prefix`, and refuses a declaration that names one, saying why.
- **Modes.** A token's `values` holds its value under the key of each combination ([Keys of combinations](files.md#keys-of-combinations)). A program picks a set of values by its key. Value axes and size axes are written alike.
- **Values.** Each value is in its DTCG form, as in the hand-over.
- **The text.** Each key of an object lies on its own line, down to a token's values. Each value then keeps to one line, in the capability's canonical text. So a changed value changes one line, and the same document gives the same file on every machine.
- **Losses.** The writer takes every value type and every kind of axis, so it reports no loss.

The check reads this code as it reads any written code (*Written code* in *What the check reports*). The test brand gives this file, cut short:

```json
{
  "document": "visual-communication/values",
  "version": 1,
  "lock": {
    "foundations": "1.0.0",
    "test-brand": "1.0.0"
  },
  "keys": ["default","colour-scheme.dark","contrast.high","colour-scheme.dark+contrast.high"],
  "tokens": {
    "accent": {
      "type": "color",
      "values": {
        "default": {"alpha":1,"colorSpace":"srgb","components":[0.0353,0.4118,0.8549]},
        "colour-scheme.dark": {"alpha":1,"colorSpace":"srgb","components":[0.2667,0.5765,0.9725]},
        "contrast.high": {"alpha":1,"colorSpace":"srgb","components":[0.0353,0.4118,0.8549]},
        "colour-scheme.dark+contrast.high": {"alpha":1,"colorSpace":"srgb","components":[0.2667,0.5765,0.9725]}
      }
    }
  }
}
```

## The viewing step

The *viewing step* draws a piece's pages as images, for a person or an agent to read (DEC-015 point 1). `pkit visual look <piece>` runs it, and `pkit visual pages <piece>` lists what it can draw. It draws what the SVG renderer draws, and needs no network.

- **No render, and no export.** It moves no lock and keeps no findings. It takes no number, writes no `exports.yaml` and records no location.
- **Under the lock.** It reads the lock `piece.yaml` holds, and computes the piece's scenes under it (DEC-015 point 4).
- **It runs no program.** No helper or producer runs. A produced picture is drawn as it stands, stale or not. One with no variant for the key is left out, as a loss.
- **What it draws.** By default, every page in the piece's source language, in the first key in [key order](files.md#keys-of-combinations). That is the combination of defaults wherever the piece names it. `--page`, `--language` and `--key` pick others. `--every-language` and `--every-key` take them all.
- **The size.** An image takes 1568 pixels on its long edge, or more where the page's smallest text would land under 10 pixels.
- **The ground.** Where a page draws no ground of its own, its image lies on white, which the piece never set. Judge a text over nothing knowing this.
- **The fonts.** It draws from the fonts the page embeds, never one on the machine.
- **No promise about pixels.** An image may change with the tool, its version or the machine. It shows this tool's drawing, not a browser's (DEC-015 point 6).

### What a run writes

A run writes in `.pkit/capabilities/visual-communication/project/local/look/<piece>/`, local to the clone ([The clone's local folder](files.md#the-clones-local-folder)). It replaces what an earlier run left there, so the folder never mixes two runs.

| File | What it holds |
|---|---|
| `<piece>.<language>.<key>.png` | one page drawn. A piece of more than one page adds the page's number, from 1, to this name and the next: `<piece>.<language>.<key>.<n>.png` |
| `<piece>.<language>.<key>.frames.json` | beside each image, its language, key, page and pixels, and the lock it was drawn under. Then each element's frame in the image's pixels, with its [trace id](components.md#trace-ids) |
| `report.json` | [What the report says](#what-the-report-says) |

### What the report says

`report.json` says what the images cannot show as the renderer set it, and the command prints the same (DEC-015 point 3). It holds the piece, the lock, the tool and its version, and four lists. Each entry but an image's names the language, key and page it lies on.

- **`images`:** each image, with its frames' file and its pixels. `on-white` is true where the page draws no ground of its own.
- **`dropped`:** each text or run the tool drew nothing of, whatever the cause, with its element and its characters. `whole` is true for a whole text, and false for a run lost from a line. A text in the colour of what lies beneath it, or under a later element, was drawn, so it is not here.
- **`losses`:** each [loss](#the-loss-report) the renderer reports. `accepted` is true for one the piece [accepts](#accepting-a-loss), which the report names all the same.
- **`drawn-otherwise`:** each run measured in more than one family, with its element, its characters and the families. The tool may set the whole run on a line in one of them, where a browser sets only the characters the first family lacks.

### What refuses a run

A refused run leaves `look/<piece>/` as it was. The fonts it held in a temporary folder of the local folder are gone, and that folder itself may remain. Any fault that stops a piece being drawn refuses a run, such as:

- a piece with no lock, naming the render that writes one;
- a lock that does not hold, naming why;
- a page, a language or a key the piece does not have, naming those it has;
- a brand that cannot be read;
- a font with no file, or a character no font holds;
- a page with no size, or one past 134217728 pixels at [its size](#the-viewing-step). `pkit visual check <piece>` names what such a piece still owes, such as a picture never produced.
