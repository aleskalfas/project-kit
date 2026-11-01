# visual-communication: a prototype of the first slice

A working prototype of the planned `visual-communication` capability (the planning note beside this
folder, `2026-10-30-visual-work-capability.md`). It draws pieces, a deck slice and a doc figure, from
their content only. A piece takes its look from data libraries: components, a brand and a notation.
The engine knows no component by name.

It is a prototype in the scratchpad and is never shipped. It has no capability scaffold, no decision records
and no changeset. The real capability is built after it has been tried.

## Try it

Run from this folder. You need `uv`, and `rsvg-convert` for the PDF and the Mural pictures
(`/opt/homebrew/bin`).

- `uv run --script visual.py render pieces/friday-slice` writes an SVG of every page in every language, brand
  and mode the piece allows, into `pieces/friday-slice/previews/`. It also writes `previews/index.html`, one page with buttons
  for language, brand and mode. Previews are never committed.
- `uv run --script visual.py export pieces/friday-slice` writes `exports/friday-slice.v<N>.<lang>.pdf` and records the
  version in `exports/versions.yaml`: the time, the state, the libraries, the font profile and the content hash. A draft's PDFs
  are added to `exports/.gitignore`.
- `uv run --script visual.py mural pieces/friday-slice --lang en --out /path/to/map.yaml` writes a
  mural-boards map with plain `objects:` and its pictures in `map-images/` beside it. `--board <ws>.<n>`
  sets the mural id, which is `new-board.0` until then. Nothing is pushed.
- `uv run --script visual.py check pieces/friday-slice` prints only problems and exits 1 if there are any.
- `uv run --script visual.py render pieces/sockets-figure` draws the connect slide's picture alone, as a figure, in light
  and dark.
- Tests: `uv run --no-project --with pytest --with pyyaml --with jsonschema --with fonttools --with uharfbuzz --with uniseg --with pypdf pytest tests -q`
  (prints the pass test's line counts at the end).

## What is here

```
visual.py                  the entry point (PEP 723; uv installs its dependencies)
engine/                    model (libraries, brands, pieces), formula, tokens (DTCG), text (fonts, line breaking),
                           layout (components as data), scene, render_svg, render_html, export (PDF),
                           render_mural, checks, cli
libraries/
  foundations/0.1.0/       the interface: roles.yaml, the top components deck.yaml and figure.yaml
  starter/0.1.0/           patterns panels, layers, groups, network, list; blocks card, node, connector,
                           code, text, aside, tag
  ibm/0.1.0/               brand: Carbon's palette (White, Gray 100), IBM Plex (OFL), square corners
  neutral/0.1.0/           brand: teal-calm and warm-paper, light and dark; Source Sans Pro and
                           Source Code Pro (OFL), rounded corners
  pkit/0.1.0/              notation: concepts.yaml (concept -> colour family, icon), glossary.yaml
pieces/
  friday-slice/            deck: permissions, fits, install, connect; en (source) and cs
  sockets-figure/          figure: the connect network alone; en and cs
tests/                     pytest
```

## The format in brief

**A library** is a folder `libraries/<name>/<version>/` with a `library.yaml` file. That file holds `schema_version: 1`, the `name`,
the `version`, the `kind` (`component library`, `brand` or `notation`), the `status` and `requires`. Every other YAML file in a
component library that has `kind: block | pattern | top` is a component.

**A component** is data:

- `fields` is a JSON Schema for the content it takes. A prose field carries `x-pkit-prose: true`.
  Every item may also carry `id`, `concept`, `state`, `use` and `override`.
- `options` are one-word choices, each from a declared list, with the first word as the default. For example,
  `fill: [plain, tint]`. An option may take an item: `line-up: {item: <id>}`.
- `states` maps a state to a colour family, or to `null` to keep the family. A state also changes a second
  signal in the parts, such as a dashed line.
- `colour` is the default colour family. A concept from the notation overrides it, and then a state does.
- `parts` are drawn in order. A part is one of these:
  - a primitive: `box`, `ellipse`, `text` (or `runs`), `line` or `image`;
  - a component: `use: starter/code` with its fields beside it, or `use: "{field}"` for content that names its
    own component, or `use: item` for what the item draws;
  - a `slot: <field>`, which is text or a component taken from the content;
  - a repeat over a list: `repeat: <field>, draw: item`, with `stack:` or `row:`;
  - `ties:`, connectors between items found by their ids.
- `when:` makes a part optional. It takes a field, `!field`, `option=a|b`, or a list of these. A missing part has
  zero size at its place, so `y: "=head.bottom + min(head.height, @space.03)"` loses its gap with the head.
- `{by: <option or field>, <word>: …, else: …}` switches any value.
- `values:` names numbers. `preferred: {width, height}` is the size the component asks for. The size it gets comes from its
  parent, and is by default what it asks for. One owner per value: a parent gives a size before anything reads it.
- `define:` holds local components. `draws:` names the components a pattern draws its items with, such as
  `item: starter/card` or `relation: {use: starter/card, marker: dot}`. Content can replace one: `item: {use: starter/card, fill: tint}`.
- `exposes:` lists the parts a parent may read below this component. A parent always reads the component's
  frame and `preferred.*`.

**A formula** is a string that starts with `=`. It allows numbers, `+ - * /` (`× ÷ −` too), parentheses, `min`,
`max`, `round`, tokens `@space.05`, and names. A name can be `width`, `height`, `index`, `count`, `page.*` (in a layout), a value, or a part's
`x y width height right bottom center middle`. It can also be `<text>.lines.<n>.middle`, `<repeat>.first|last|<id>.<frame>`,
`<repeat>.count` or `<component>.preferred.height`. No comparison and no loops. A loop of references is refused, naming it.
In a YAML flow mapping, quote a formula that has a comma.

**Operators:**

- `stack: {gap, align: start|center|end, item-width: <formula with index, count>, equal: height, fill: <length>, distribute: <length>}`
- `row: {gap, shares: [3, 2], equal: height, align: top|middle|bottom|item, connector}`
- `ramp: level` gives the items `level-1…5`.
- `ties: <field>, spread: [out, in], gap`
- `line-up: {item: <id>}` in `panels` lines the other panels up with that item and draws the arrow.

**Colours** are always roles: `surface`, `text-secondary`, `code.prompt`, and `tone.fill|line|ink|solid|on`
for the instance's family. A raw value is refused. `override: {<part>: <role>}` in content changes one part through a
role. A text run that is named by a concept (`[core/, core]`) takes the concept's `ink`.

**A brand** has DTCG token files (`$value`, `$type`, aliases `{a.b}`). It has `base` files, a file per theme and
mode that holds colours only (the engine refuses anything else, so a mode never moves anything), and a file per font
profile. The `standard` profile (svg, html, pdf) measures committed font files. The `mural` profile has
proxima-nova `measure: estimate`, the monospace font with `render: image`, and inline code in proxima-nova. A brand
gives every role in `foundations/roles.yaml` a value. It supplies layouts per entry point (`layouts/deck.yaml`,
`layouts/figure.yaml`), with parts, slots, `bounds` and a `define` of its own (`notice`).

**A notation** maps concepts to colour families and icons (`concepts.yaml`) and holds the words of its subject
(`glossary.yaml`, whose `never:` words `check` reports in prose fields).

**A piece** is `piece.yaml`, which holds the top, the brand entry point, the notations, the languages, the source, the medium,
the state, the outputs, `lock` and `previews`. It has one `content.<lang>.yaml` per language, with the same structure and the same ids.

**The scene** is one per language, brand entry point and font profile. It is a tree of groups with a trace id from the
path of instances, parts and item keys, the component and its version, and the content path. Its primitives
are box, ellipse, line (its points and tips), image (fit, tint) and text. A text carries its lines and runs, its style, and how it
was measured (file and sha256, or the estimate's rule). Colours stay roles until a renderer resolves them in
a mode.

**Text** is measured with HarfBuzz from committed font files only and broken greedily at Unicode's break
opportunities. In Czech a one-letter word never ends a line (`vlna`'s rule: a non-breaking space). Line
height is explicit.

## Checks

| Kind | Reported when |
|---|---|
| `FIT` | a text is wider or taller than its box, a component gets less than it asks for, or a slot reaches past its layout's `bounds` (every language, brand and font profile, the Mural estimate included) |
| `CONTRAST` | a non-decorative run against the topmost filled shape under it is below 4.5, in any mode |
| `FONT` | a face has no glyph for a character, or a font file is missing |
| `REF` | a tie, `line-up` or concept leads nowhere, a layout or slot is missing, a role has no token, an id is repeated on a page, or a translation is not shaped as its source |
| `SCHEMA` | a field a component does not take, an option word not in its list, a state it does not declare, or content against the top's schema |
| `TERM` | a glossary's `never:` word appears in a prose field |

## The pass test (the architect's)

Lines are counted non-blank and not comments. Docstrings and `about:` texts are left out. The board's templates and our
brand layouts and tokens are also left out.

| | data: components used + content | gen.py: function + helpers it calls | the talk's own data |
|---|---|---|---|
| fits | 123 (104 + 19) | 69 (pyramid 51 + 18) | 46 |
| connect | 256 (203 + 53) | 145 (sockets 57 + 88) | 32 |
| both, shared components once | 315 (243 + 72) | 212 | 78 |

Measured this way, the data is larger than the code. The components carry what the code left implicit: a
JSON Schema per component, options and states, and the slots for any content. They are shared, though. A new slide of the
same kinds costs its content only, 19 and 53 lines here. gen.py's numbers are fixed for those two slides, and its
own data for them adds 46 and 32 lines.

## Known gaps

- **A board edit is not taken back.** The Mural map is one-way: the engine writes no `renders/` record (ids,
  hashes per property) and has no `pull` into content. An edit made on the board is lost at the next map.
- **Versions and locks are only recorded.** `lock` picks the library versions, and `versions.yaml` records each
  export. Nothing upgrades a lock, freezes a delivered piece, keeps a living piece's unnumbered copy, or fails when a
  committed export no longer matches its content.
- **No agents, rules or skills.** There is no sign-in through pkit and no `pkit visual …` command. The prototype is a standalone script.
- **The Mural metrics are not calibrated.** proxima-nova is measured by gen.py's per-character estimate, so
  Mural's own wrapping may differ. Arrows are not attached to objects (`from`/`to`).
- **Translations are kept in step by hand.** Anchoring to the source (#2416) is not built. Only the notation's glossary
  exists, with no brand or piece glossary and no merged list for a translator.
- **Overlap is not checked**, only overflow and layout bounds.
- **Lines are broken greedily**, with no hyphenation and no widow control (a last word can stand alone). IBM Plex is committed in Regular only, so the IBM brand has no bold.
- **SVG text is placed run by run** from the measured advances. Kerning across a run boundary is lost.
- **Notation icons are not drawn.** `concepts.yaml` names them, and no starter component draws them yet. The neutral brand has no
  attention picture, so its `aside` draws none (the missing part takes no room).
- **The figure exports a PDF.** The piece says `outputs: [svg]`, and `export` ignores `outputs`. Its previews are the SVGs.
- **The HTML renderer is the preview index**, the SVGs in one page. It is not HTML layout.
- **The pages differ from the delivered PDF in their font.** The delivered PDF came from Mural in proxima-nova, and the IBM previews use
  IBM Plex Sans, so widths and line breaks differ slightly. The pyramid's levels are a little lower (150 against 172)
  because the node block is shared with the connect slide's slots.
- **The engine reads `requires: {visual-communication: …}` only against its own version string.**
- **Content can still name a colour in words.** The install listing's last line says "purple: pkit's · blue: yours", and the
  warm-paper brand draws pkit's concept in rust. A legend drawn from the notation (RS-VISUAL-006) would say it instead.
