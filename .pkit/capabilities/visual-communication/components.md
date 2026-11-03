---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/schemas/component.schema.json
        - .pkit/capabilities/visual-communication/schemas/component.yaml
        - .pkit/capabilities/visual-communication/schemas/defs.schema.json
        - .pkit/capabilities/visual-communication/scripts/_lib/names.py
        - .pkit/capabilities/visual-communication/scripts/_lib/formula.py
        - .pkit/capabilities/visual-communication/scripts/_lib/layout.py
        - .pkit/capabilities/visual-communication/scripts/_lib/scene.py
        - .pkit/capabilities/visual-communication/scripts/_lib/text.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/seam.py
        - .pkit/capabilities/visual-communication/libraries/foundations/components/figure.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/components/deck.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/library.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/steps.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/card.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/callout.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/picture.yaml
        - tests/visual_engine.py
        - tests/test_visual_communication_scene.py
      record: ["visual-communication:DEC-001", "visual-communication:DEC-003", "visual-communication:DEC-004", "visual-communication:DEC-005", "visual-communication:DEC-007", "visual-communication:DEC-008", "visual-communication:DEC-009", "visual-communication:DEC-010"]
      artefact:
        - .pkit/capabilities/visual-communication/files.md
        - .pkit/capabilities/visual-communication/files.md#the-foundations
        - .pkit/capabilities/visual-communication/files.md#rolesyaml
        - .pkit/capabilities/visual-communication/files.md#reserved-words
        - .pkit/capabilities/visual-communication/files.md#content-files
---

# Components

A *component* is data that says how a piece's content is arranged and drawn: the fields it takes, its options, and its parts, each placed by formulas. The *engine* is the capability's code that computes a *scene* from a piece's content and the components that draw it. It knows no component by name (DEC-001 point 4). Where a component's file lies, in a library or in a piece, is in [files](files.md).

The examples come from the foundations' `figure`, which ships, and from `tests`, a component library the capability's own tests draw with. No project locks `tests`.

<!-- pkit:contents -->
- [Patterns, blocks and top components](#patterns-blocks-and-top-components)
- [A component's file](#a-components-file)
- [Formulas](#formulas)
- [Layout operators and drawing primitives](#layout-operators-and-drawing-primitives)
- [How the engine computes a scene](#how-the-engine-computes-a-scene)
- [Text](#text)
<!-- /pkit:contents -->

## Patterns, blocks and top components

One model binds every component. A pattern, an item component and a block are roles a component plays, not kinds of file (DEC-001 points 4 and 6).

- **A pattern** arranges items. It has a `repeat` part over a list of the content, and decides how its items lie. `tests/steps` is a pattern.
- **An item component** draws one item of a list. The pattern names it in `draw`. An item may name its own in `use`, a pattern included.
- **A block** is a small component, such as a card, that a pattern draws its items with, or that content places alone (DEC-007 point 1). `tests/card` and `tests/picture` are blocks.
- **A top component** declares `layouts`. A piece names one as its top ([files](files.md)). The foundations' `figure` is one, with one layout. Their `deck` is one whose layouts are the forms its pages take, a cover and a slide ([Layouts](#layouts)).
- **A local component** belongs to one piece. Its `use` is `piece/<component>`, and a library component's is `<library>/<component>`. The lock alone says which version of a library is read.

## A component's file

A component is a YAML file bound to the schema `visual-communication:component`. This is `tests/steps`, a pattern, its `about` left out:

```yaml
pkit_schema: visual-communication:component
schema_version: 1
status: experimental
fields:
  type: object
  required: [steps]
  properties:
    steps:
      type: array
      minItems: 1
      items: {type: object}
options:
  spacing: [normal, wide]
values:
  gap:
    by: spacing
    normal: "=@space.2"
    wide: "=@space.2 * 2"
parts:
  steps:
    repeat: steps
    draw: tests/card
    width: "=:width"
    row: {gap: "=gap", sizes: equal, align-items: stretch}
preferred:
  height: "=steps.height"
```

The file takes these keys and no other:

| Key | What it holds |
|---|---|
| `pkit_schema`, `schema_version` | The binding: `visual-communication:component` and `1`. Required. |
| `status` | `experimental`, `stable` or `deprecated`, below. Required. |
| `about` | What the component is for, in words. Required. |
| `fields` | The content it takes, in a fixed subset of JSON Schema. |
| `options` | Its options, by name. |
| `states` | Its states, by name. |
| `colour` | Its default colour family. |
| `values` | Its named numbers, each a formula or a switch of formulas. |
| `preferred` | `width` and `height`, the size it asks for, each a formula. |
| `parts` | What it draws and places, by name, in drawing order. |
| `exposes` | The parts a component that places it may read. |
| `layouts` | On a top component only: its layouts and their slots, and, where they are its pages' forms, each layout's own drawing. |

Every name in the file takes the capability's name shape ([files](files.md)). The status says what the component's library promises (DEC-003 point 7). An experimental component may change in any release, renamed, reshaped or removed. A stable one changes in a breaking way only in a major release of its library. A deprecated one may be removed only in a major release.

### Fields

`fields` is the JSON Schema of the content the component takes. At every level it takes these keys only:

- **`type`:** `string`, `number`, `integer`, `boolean`, `object`, `array` or `null`, or a list of them.
- **`properties` and `required`:** the fields, by name. No field takes a reserved key's name: `id`, `use`, `concept`, `state`, `override` or `pkit` ([Reserved words](files.md#reserved-words)).
- **`items`, `minItems` and `maxItems`:** what a list holds, and how many. **`enum` and `const`:** the values a field may hold.
- **`description`,** and **`x-pkit-prose: true`,** which marks a field that holds prose. No command reads the mark.
- **`x-pkit-pages: true`,** which marks the list field of a top that holds its pages, where its layouts are its pages' forms ([Layouts](#layouts)).
- **`$ref`:** a reference that starts with `#/`, read within the component's own `fields`.
- **`additionalProperties`:** only `false`. Leaving it out means the same.

A field whose `type` is `array`, or a list of types that holds it, such as `[array, null]`, is a *list field*. A `repeat` part draws its items, and an option may name one of them. How content is judged against `fields` is in *checks*.

### Options

An option takes a value from what the component declares, never a free number or a raw value (DEC-001 point 6). The content, or the part that places the component, gives it.

| Declared as | The content gives |
|---|---|
| a list of words, such as `spacing: [normal, wide]` | one of the words; the first is the default |
| `{item: <list field>}` | `{item: <id>}`: an item of that list, by its id |
| `{item: <list field>, point: true}` | `{item: <id>, point: <name>}`: an item, and a point its picture exposes |

- **Names and words.** An option's name is no field's and no reserved key's. A word is never `by`, and appears once in its list.
- **An option that names an item** needs exactly one part that repeats over its list. `tests/callout` declares `at: {item: pictures, point: true}`: the picture, and the point, its label stands at. Where no part repeats over the list, or two do, the option is reported when the component is read, and so is each formula that reads it ([errors](#errors)).
- **A word the option lacks** is reported, and the engine draws with the first word. An item option the content leaves out, or whose id its list lacks, is reported too.

### Values, states and colour

- **`values`** holds named formulas, or switches of them. A formula reads a value by its name alone. A value and a part never share a name. A switch's branches give one dimension.
- **`preferred`** holds `width` and `height`, each a formula that gives a length. A component placed with no size given, and that asks for none, is reported.
- **`colour`** names the component's default colour family. A *colour family* is a group of colour roles that paints one thing, such as its line, its fill and the text on it. The foundations declare each family in their `roles.yaml`, as a mapping of its members to colour roles (DEC-004 point 10; [the foundations](files.md#the-foundations)).
- **`states`** maps each state to `{colour: <family>}`, the family the state paints with, or to `{}`, which keeps the instance's family. The content names a state as `state: <name>`.
- **An instance's family** is the family its concept maps to, where the content names one as `concept: <notation>/<concept>` ([content files](files.md#content-files)). Else it is the `colour` of the `repeat` part that draws it as an item, else its component's `colour`, else the family of the component that places it. A state with a `colour` then replaces it. A concept the piece's notations do not hold is reported, and the instance takes its family as if it named none.
- **A paint `:colour.<member>`** paints with the role the foundations map that member of the instance's family to. Where the instance has no family, its family is none the foundations declare, or the family has no such member, the part paints nothing there, and is reported.
- **The content's `override: {<part>: <role>}`** points one part's paint at another role: the `fill` of a box, an ellipse or a text, the `stroke` of a line.

### Parts

`parts` maps each part's name to one part. The parts are drawn in the order written. A part holds exactly one key that names its kind, and the keys that kind takes:

| Kind | Its other keys | Required |
|---|---|---|
| `box` | `x y width height` | `width height` |
| `ellipse` | `x y width height` | `width height` |
| `text` | `x y width` | |
| `line` | `x1 y1 x2 y2` | all four |
| `image` | `x y width height` | `width` |
| `use` | `x y width height fields options` | |
| `slot` | `x y width height` | |
| `repeat` | `x y width height draw colour`, and `row` or `column` | `draw`, and one of `row` and `column` |

- **Places and sizes** are formulas that give a length, in the component's own frame. A missing `x` or `y` is zero.
- **`when`** draws the part only while a condition holds. It names a field, and holds while the content fills it: the field is not missing, empty text, an empty list or an empty mapping. Or it is `{<option>: [<word>, ...]}`, and holds while the option takes one of the words. A part not drawn has zero size, at its place.

The figure draws its caption only when the content gives one:

```yaml
  caption:
    when: caption
    text: {content: caption, style: type.body, fill: text-secondary}
    x: "=body.x"
    y: "=body.bottom + min(caption.height, @space.2)"
    width: "=body.width"
```

### Switches

A value may be a *switch*: `{by: <option>, <word>: <value>, ...}`. It names an option of words, and gives a value for each of its words, no more and no fewer. A branch may be a switch itself. A paint's branch may be `null`, which paints nothing. A switch serves wherever a part takes a formula, a paint, a style, a word of `text-anchor` or of an operator, or a placed component's option, and in `values` and `preferred`. `values.gap` of `tests/steps` above is a switch.

### Exposes

`exposes` lists the parts a component that places this one may read in its formulas. Every other part stays private, so its library may change it freely. Removing or renaming an exposed part is a breaking change (DEC-005 point 3). An exposed `image` part also exposes its picture's points, each read as a part of zero size of the component itself. `tests/picture` holds one part, `image`, and declares `exposes: [image]`.

### Layouts

A top component declares `layouts`, by name. Each layout has a *drawing*, the parts that draw the top in it, and the top's own drawing of a layout is the layout's default (DEC-009 point 1). A top declares its layouts in one of two ways.

**One layout for the whole top.** The layout holds its `slots`, each a field of the top that the content fills, and the top's `parts` are its drawing. A slot marked `pages: true` holds pages: each item of its list, or the component placed in it, is a page.

- **A top component with no slot of pages** is a page alone, and part of the page that holds it (DEC-005 point 5). The figure declares `layouts: {frame: {slots: {body: {}, caption: {}}}}`, with no slot of pages. As a piece's top it is one page. Placed in a slide's slot, it is part of that slide.

**Layouts that are its pages' forms** (DEC-010 point 5). The top marks one list field of its own `x-pkit-pages: true`: the field that holds its pages, which lies in no layout. Each layout then takes these keys:

- **`slots`:** the fields a page in that layout fills, each written as a field of `fields` is. They are a page's fields, not the top's. No slot takes a reserved key's name, nor `layout`, the key by which a page names its layout, nor the name of a field of the top. No slot holds pages.
- **`required`:** the slots a page in that layout must fill.
- **`parts`:** the layout's drawing, which draws one page. Every layout has one. It takes the page's slots, the top's other fields and the words of the top's options, as the content gives them to the top, and the states, colour and values the top declares (DEC-009 point 5). Its `:width` and `:height` are the top's size. A part that places a slot is best named after the slot, as the deck's are, so what the slot places keeps one trace id under every drawing.

The deck's field of pages, and its slide trimmed to two of its slots, their descriptions left out:

```yaml
fields:
  type: object
  required: [slides]
  properties:
    slides:
      type: array
      minItems: 1
      items: {type: object}
      x-pkit-pages: true
layouts:
  slide:
    slots:
      title: {type: string, x-pkit-prose: true}
      lead: {type: string, x-pkit-prose: true}
    required: [title]
    parts:
      title:
        text: {content: title, style: type.heading, fill: text-primary}
        x: "=margin"
        y: "=margin"
        width: "=:width - 2 * margin"
      lead:
        when: lead
        text: {content: lead, style: type.body, fill: text-secondary}
        x: "=margin"
        y: "=title.bottom + @space.3"
        width: "=:width - 2 * margin"
```

- **The top draws nothing around its pages.** It has no `parts` of its own. Each page is a page of its own, drawn by its layout's drawing at the top's origin, as large as the top. The top is not a page.
- **A page names its form.** It names its layout with `layout`, and fills that layout's slots, or names the component that draws it with `use` ([content files](files.md#content-files)). A page drawn by its own component is as large as the top too.
- **A slot that holds one page** places it as every slot places a component, by `use`, and names no layout. The key `layout` belongs to a page of a top whose layouts are its pages' forms, which places no component.
- **A top that is a page alone keeps one layout,** as the figure does. Its content is the top's own mapping, whose keys are the top's fields, and a top with one layout may declare a field named `layout`. So the key cannot choose among forms of such a top without refusing a file format 1 accepts.

A page inside a page is reported: what a slot of pages places, where that slot lies inside a page, and each page of a top whose layouts are its pages' forms, where that top lies inside one.

## Formulas

A *formula* is text that starts with `=` and computes one number (DEC-005 point 1). It holds no comparison, condition, loop or text.

| Written | What it is |
|---|---|
| `2`, `0.5` | a number with no unit |
| `+ - * /` and `( )` | the four operations, `*` and `/` before `+` and `-` |
| `min(a, b, …)`, `max(a, b, …)` | the least or the greatest of two or more |
| `round(a)` | the nearest whole number, half away from zero |
| `@<token path>` | a role, such as `@space.2`: a length or a number |
| `:width`, `:height` | the size the component gets |
| `:index`, `:count` | an item's place among the items its list draws, from 1, and how many it draws |
| `<value>` | a value of the component, by its name alone, such as `gap` |
| `<part>.<exposed>….<measure>` | a measure of a part's frame, or of a part exposed below it |
| `{<option>}.….<measure>` | a measure of the item, or the point, an option gives |

- **A function's name** is followed at once by its `(`.
- **The engine's names** are marked with `:`, which no name holds. A name the engine lacks, such as `:size`, is refused.
- **Spacing.** A binary minus has a space on each side, since names hold hyphens: `a-b` is one name, and `=a - b` subtracts. `=2-3`, `=a -b` and `=a- b` are refused. A minus that negates needs no space: `=-@space.1`, `=2 * -3`. Other spaces are free.

### References

A *path* reads one measure of a frame. A *frame* is an element's place and size.

- **The measures** are `x`, `y`, `width`, `height`, `right` (x plus width), `bottom` (y plus height), `center` (x plus half the width) and `middle` (y plus half the height). Each is in the frame of the component that reads it.
- **The last step is always the measure.** `width.x` reads the `x` of a part named `width`. A name alone, with no measure, reads a value.
- **The first step** is a part of the component itself. Each step below names a part that the component placed there exposes, one name a step. A component placed by `use` or `slot`, and an item, are read this way.
- **A step into a list** names the `repeat` part, then the item: `<list>:first`, `<list>:last`, or `<list>[<id>]` by the item's id. `steps:first.x` reads the first item's place. A step below a list names an item first. Without one, `steps.height` reads the whole list's frame.
- **What a step may not reach.** Nothing lies below a `box`, an `ellipse`, a `text` or a `line`. Below an `image` lies only a point of its picture, and nothing lies below a point.
- **`{<option>}`** starts a path with what an option gives: its item, as `<list>[<id>]`, or its item's point. Only the measure follows a point. `tests/callout` places its label beside the point: `x: "={at}.x + @space.1"`.
- **A role,** shared or a library's own, reads its value in the brand the piece locks: the brand's value, or, for a library's role the brand gives none, its default ([`roles.yaml`](files.md#rolesyaml)). A dimension in `px` is a length, and a number is a number with no unit. Format 1 measures in `px` alone.

### Dimensions

Each term is a number with no unit or a length (a power of length). The engine checks a formula's dimensions when it reads the component.

- **A sum's terms,** and the arguments of `min` and `max`, share one dimension. So a number scales a length, and is never added to one: `=:width - 6` is refused.
- **A product** adds the powers, and **a quotient** subtracts them: `=:width / @space.1` is a number.
- **A place, a size, a line's end, `preferred`, `stroke-width`, `rx` and `gap`** each give a length.

### Errors

A formula is refused with a message that names it and says why, such as "the formula `=:width - 6` subtracts a number with no unit (`6`) from a length (`:width`)". The engine finds these when it reads the component:

- **It cannot be read:** it does not start with `=`, is empty, ends too early, or holds a sign or a term where none belongs. Or it breaks a rule of the grammar: a binary minus without its spaces, an engine name that does not exist, `min` or `max` with fewer than two arguments, `round` with other than one, or a path that ends in no measure.
- **It reads what it may not:** a value, a part or an option the component lacks, an option that names an item of a list over which not exactly one part repeats, or below where a step may reach.
- **Its dimensions disagree,** or it gives another dimension than its key needs.
- **It reads a role** that has no value under the brand, a length in a unit other than `px`, or a role that is neither a length nor a number. A role has none where no library the piece locks declares it, or where it is a library's role that neither the brand nor its chain of defaults gives a value ([`roles.yaml`](files.md#rolesyaml)).

It finds these when it computes the scene: a division by zero, `:index` or `:count` in a component that is no item, a path to an exposed part, a point or an item that is missing, and a loop. A value that cannot be computed is zero. The check reports each problem as a finding (*checks*).

## Layout operators and drawing primitives

The engine knows the five primitives, the two ways to place a component and the one way to repeat one, below. It has no other primitive and no other layout operator.

### Primitives

A primitive's properties lie in its own mapping, under SVG's names.

| Primitive | Its properties | What it draws |
|---|---|---|
| `box` | `fill`, `stroke`, `stroke-width`, `rx` | a rectangle in its frame |
| `ellipse` | `fill`, `stroke`, `stroke-width` | an ellipse in its frame |
| `text` | `content`, `style` (both required), `fill`, `text-anchor` | the text of a field, in lines |
| `line` | `stroke` (required), `stroke-width` | a straight line from `x1 y1` to `x2 y2` |
| `image` | `produced` (required) | the picture of a produced output of the piece |

- **A paint,** `fill` or `stroke`, is a colour role's token path, `:colour.<member>`, or a switch. `stroke-width` and `rx` are formulas that give a length.
- **A text** shows the field `content` names, in the typography role `style` names. Its height is always its measured text's: a text that gives a `height` is reported as a value with two owners. With a `width`, its lines are broken to that width; without one, each paragraph is one line, and the text is as wide as its widest. `text-anchor` is `start`, the default, `middle` or `end`: where each line stands in the text's width.
- **A line's frame** comes from its ends: it starts at the lesser of the two `x` and of the two `y`, and is as wide and as tall as the distance between them.
- **An image** shows the produced output that the field `produced` names (*outputs*). It needs a `width`. Where it gives no `height`, its height keeps the picture's proportions. The picture is drawn whole, centred, as large as its frame allows, and its points are mapped into the frame the same way. The variants of one picture share one pixel size and the same points, and the engine reads the first variant key in order. An output the piece lacks is not drawn, and is reported.

### Placing a component: `use` and `slot`

- **`use: <library>/<component>`** places that component. `fields` maps each of its fields to a field of this component, whose content it passes on. `options` gives each of its options a word, or a switch on an option of this component.
- **A component never places itself,** directly or through others. The engine reports the chain of components.
- **`slot: <field>`** places the component the content gives in that field: `{use: <library>/<component>}`, with that component's fields and options beside `use`. Where the field is empty, the slot is not drawn.

### Repeating over a list: `row` and `column`

A `repeat` part draws a component for each item of a list field, in the content's order. Each item is drawn by the component its own `use` names, else by `draw`. An item that is not a mapping, repeats an id, or names no component, is reported and left out. It takes no place among the items drawn, so `:index` and `:count` do not count it, and its trace id keeps its place in the content's list. `colour` gives the items' default colour family.

The part's *layout operator*, `row` or `column`, lays the items along a line, across or down. Its settings take the names of CSS flexible layout:

| Setting | Takes | Default | What it does |
|---|---|---|---|
| `gap` | a formula that gives a length | zero | the space between two items along the line |
| `sizes` | `own`, `equal` | `own` | `own`: each item takes the size it asks for along the line. `equal`: the items share the part's size along the line, less the gaps, equally. The part must then give that size. |
| `justify-content` | `start`, `center`, `end`, `space-between` | `start` | Where the items lie along a line longer than they ask for. `space-between` widens each gap instead. |
| `align-items` | `stretch`, `start`, `center`, `end` | `stretch` | `stretch`: each item is as large across as the line, that is the part's size across, else the largest size an item asks for. Otherwise each item takes the size it asks for across, at the start, the centre or the end of the line. |

- **The part's own size,** where it gives none, is what its items ask for: along the line, their sizes and the gaps; across, the largest.
- **In the tests' figure,** where `@space.2` is 8 px, `tests/steps` lays three steps with `row: {gap: "=gap", sizes: equal, align-items: stretch}` in a row 608 px wide. Each step is 197.33 px wide, and as tall as the tallest.

### What an element asks for, and what it gets

- **Each element asks** for its `preferred` size, and **gets** one (DEC-005 point 3). It gets a size from what places it. A top component gets what it asks for. A component placed by `use` or `slot` gets its part's size, else what it asks for. An item gets what the operator gives it. A formula reads the size it gets as `:width` and `:height`.
- **Each value has one owner:** a part's formula, its measured text, or its parent's layout.
- **A component that gets less than it asks for** is reported.

## How the engine computes a scene

The *scene* is every element's final frame, values and source, for one language. The engine computes it from the piece's content, the components that draw it, the roles of its brand, and the fonts and produced pictures they name. The commands compute one scene for each language of the piece, at the size key `default`, since format 1 has no size axis (keys: [files](files.md)). A scene is computed, never committed. Under one release of the capability, the same files give the same scene on every machine.

- **Built from the content.** The engine places the top component with the content, then builds each part, item and placed component below it.
- **Fonts first.** Before it computes any place or size, a font family with no file, or a character no family measures, refuses the scene ([Text](#text)).
- **Value by value.** Each size, place, value, list arrangement and text's lines is computed on first use, in the order the references give, as a spreadsheet computes its cells. So a parent's width and a child's measured height form no loop.
- **A loop** is refused, naming every element in it. Each problem is a finding, and a value that cannot be computed is zero.

### What a scene holds

The scene's root holds `piece`, its `lock`, the `language`, the `size-key`, `seam` (the version of the seam its plugins read, 1), `pages` (the trace ids of its pages, in order: a top that is a page alone, what a slot of pages places, or each page of a top whose layouts are its pages' forms) and `children`. Each element holds its `type`, `group` or a primitive's kind, and its `id`, its trace id. It holds its frame, `x y width height`, relative to its parent, in px, rounded to 1/100 px, half away from zero. Then come its properties, `sources`, where each came from, and on a group its `children`, in drawing order.

A placed component's group adds `component` (its `use`), `version` (its library's, none for a local component), `options` (the value each option takes) and, on a page, `page: true`. A top whose layouts are its pages' forms holds no `page`. Its group holds its pages, each a group with `page: true`, whose `component` is the top's where its layout's drawing draws it, else the one the page names. A `repeat` part is a group too, holding its items. A `box`, an `ellipse` and a `line` add their paints and lengths, and a line its ends. An `image` adds `output`, `preserveAspectRatio` (`xMidYMid meet`), `variants` by key with each file and pixel size, and `points` mapped into its frame.

Colours stay role names. A renderer takes their values from the brand's resolved values, so one scene serves every mode of the value axes (*outputs*). This is the first step's head in a scene of the figure, trimmed:

```json
{"type": "text", "id": "figure/body/steps[plan]/head",
 "x": 8.0, "y": 8.0, "width": 181.33, "height": 22.4,
 "text-anchor": "start", "fill": "text-primary", "style": "type.body",
 "font-family": ["Source Sans Pro"], "font-size": 16.0, "font-weight": 400,
 "line-height": 22.4, "baseline": 16.89, "text": "Plan the work",
 "lines": [{"text": "Plan the work", "width": 91.97}], "measured-height": 22.4, "measured": "file",
 "fonts": [{"family": "Source Sans Pro", "file": "SourceSansPro-Regular.otf", "sha256": "6b096b47…"}],
 "sources": {"fill": "default:tests/card", "font-size": "role:type.body", "height": "engine",
             "text": "content:body.steps[plan].head", "x": "role:space.2"}}
```

### Trace ids

Every element carries its *trace*, an id that comes from the path of instances, parts and items, never from the order of drawing (DEC-005 point 5).

- **The top component's** id is its component's name: `figure`.
- **A part's** id is its component's id, `/`, and the part's name: `figure/body`. A component placed by `use` or `slot` takes its part's id.
- **An item's** id is its `repeat` part's id followed by `[<id>]`, or by `#<place>`, from 1, where the item has no id: `figure/body/steps[plan]`, `figure/body/steps#2`.
- **A page of a top whose layouts are its pages' forms** takes the top's id, `/`, and the field that holds the pages, followed by `[<id>]` or `#<place>` as an item's: `deck/slides[cover]`. Each part of its drawing takes the page's id: `deck/slides[cover]/title`.

### Sources

Each drawn property names its source in `sources`:

- **`content:<field path>`:** a field of the content, such as `content:body.steps[plan].head`. The path names the keys the content file writes, joined by `.`, an item of a list as `[<id>]`, or as `#<place>` from 1 where it has no id. It names the list field, where a trace id names the `repeat` part. Under a `use` part that passes a field on under another name, at any depth, it keeps the name the content file writes.
- **`option:<name>`:** a value a switch on that option chose.
- **`default:<library>/<component>`:** the component's own value. A field that a `use` part does not pass on is the placing component's, which gives it nothing.
- **`role:<token path>`:** a formula that reads one role and nothing else, such as `"=@space.2"`, or a text's typography role.
- **`engine`:** a value the engine computed, such as a text's measured height or an item's frame, or one the component leaves to the engine's default, such as `text-anchor` on a text that gives none.

## Text

- **The default font profile.** The engine measures every text from the committed font files that the brand names for each family, never from a font found on the machine. A text records this as `measured: file`. How a brand names its files is in [files](files.md).
- **The typography role** that `style` names gives `fontFamily`, one family or a list, `fontSize` in px, `lineHeight` as a ratio of the size, `fontWeight`, and a `letterSpacing` of zero, if any. A role that names no family, gives another letter spacing, a size in another unit or no line height as a number is reported, and the text is not drawn.
- **Several families.** The first family measures each character it has, the next the rest, and so on.
- **One file a family.** A family's one file measures the text, whatever its weight.
- **Refused before layout.** A family with no committed file, or a character no family measures, refuses the scene, and the message names it.
- **Shaped from the file.** Each run of text in one family is shaped with HarfBuzz, with the font's default features. A line's width is the sum of its advances at the font size. Spaces at its end do not count.
- **The line height** is the font size times `lineHeight`, and **the measured height** the number of lines times the line height.
- **The baseline** is the first baseline below a line's top, with the space above and below the letters split evenly, from the first family's metrics.

### Breaking lines

- **Paragraphs.** The text is split into paragraphs at its line feeds. With no width, each paragraph is one line.
- **A width:** the engine breaks each paragraph where Unicode's line-breaking rules (UAX #14) allow it and the language's own rules do not forbid it. It fills each line with as much as fits in the width less 2 % of the font size, and places the line in the whole width. So a renderer's slightly different metrics move no word.
- **The language's rules** are read by the primary subtag of the scene's language. In Czech, `cs`, a one-letter word never ends a line: it moves to the next line with the word after it. Other languages follow Unicode's rules alone.
- **A word wider than its line** may break after a `/` in it. A word still wider stays whole, and the text overflows: it holds `overflow: true`, and the check reports it.
- **Never shrunk.** The engine never makes text smaller to fit, and never hyphenates.
