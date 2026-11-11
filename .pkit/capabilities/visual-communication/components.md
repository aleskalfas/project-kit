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
        - .pkit/capabilities/visual-communication/scripts/_lib/env.py
        - .pkit/capabilities/visual-communication/scripts/_lib/pipeline.py
        - .pkit/capabilities/visual-communication/scripts/_lib/tokens.py
        - .pkit/capabilities/visual-communication/scripts/_lib/checks.py
        - .pkit/capabilities/visual-communication/scripts/_lib/exports.py
        - .pkit/capabilities/visual-communication/scripts/_lib/plugins/seam.py
        - .pkit/capabilities/visual-communication/libraries/foundations/components/figure.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/components/deck.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/components/site.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/library.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/steps.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/card.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/callout.yaml
        - tests/fixtures/visual-communication/libraries/tests/1.0.0/components/picture.yaml
        - tests/fixtures/visual-communication/drawings/cover.yaml
        - tests/visual_engine.py
        - tests/test_visual_communication_scene.py
      record:
        - visual-communication:DEC-001#4
        - visual-communication:DEC-001#6
        - visual-communication:DEC-003#7
        - visual-communication:DEC-004#2
        - visual-communication:DEC-004#3
        - visual-communication:DEC-004#7
        - visual-communication:DEC-004#9
        - visual-communication:DEC-004#10
        - visual-communication:DEC-005#1
        - visual-communication:DEC-005#2
        - visual-communication:DEC-005#3
        - visual-communication:DEC-005#4
        - visual-communication:DEC-005#5
        - visual-communication:DEC-005#6
        - visual-communication:DEC-005#14
        - visual-communication:DEC-006#7
        - visual-communication:DEC-007#1
        - visual-communication:DEC-008#1
        - visual-communication:DEC-008#4
        - visual-communication:DEC-008#9
        - visual-communication:DEC-009#1
        - visual-communication:DEC-009#2
        - visual-communication:DEC-009#3
        - visual-communication:DEC-009#5
        - visual-communication:DEC-009#6
        - visual-communication:DEC-010#1
        - visual-communication:DEC-010#2
        - visual-communication:DEC-010#3
        - visual-communication:DEC-010#4
        - visual-communication:DEC-010#5
        - visual-communication:DEC-010#6
        - visual-communication:DEC-011#1
        - visual-communication:DEC-011#2
        - visual-communication:DEC-011#3
        - visual-communication:DEC-011#4
        - visual-communication:DEC-011#5
        - visual-communication:DEC-012#1
        - visual-communication:DEC-012#2
        - visual-communication:DEC-012#3
        - visual-communication:DEC-012#4
        - visual-communication:DEC-016#5
        - visual-communication:DEC-017#3
        - visual-communication:DEC-021#5
        - visual-communication:DEC-021#7
        - visual-communication:DEC-022#3
        - visual-communication:DEC-025#1
        - visual-communication:DEC-025#3
        - visual-communication:DEC-025#4
        - visual-communication:DEC-025#6
        - visual-communication:DEC-025#7
        - visual-communication:DEC-031#2
        - visual-communication:DEC-034#1
        - visual-communication:DEC-034#2
        - visual-communication:DEC-034#3
        - visual-communication:DEC-034#5
        - visual-communication:DEC-034#6
        - visual-communication:DEC-034#7
        - visual-communication:DEC-034#8
        - visual-communication:DEC-035#1
        - visual-communication:DEC-035#2
        - visual-communication:DEC-035#3
        - visual-communication:DEC-035#4
        - visual-communication:DEC-035#5
      artefact:
        - .pkit/capabilities/visual-communication/files.md#what-the-location-holds
        - .pkit/capabilities/visual-communication/files.md#shapes
        - .pkit/capabilities/visual-communication/files.md#the-binding
        - .pkit/capabilities/visual-communication/files.md#pieceyaml
        - .pkit/capabilities/visual-communication/files.md#the-lock
        - .pkit/capabilities/visual-communication/files.md#the-foundations
        - .pkit/capabilities/visual-communication/files.md#rolesyaml
        - .pkit/capabilities/visual-communication/files.md#picture-roles
        - .pkit/capabilities/visual-communication/files.md#picture-files
        - .pkit/capabilities/visual-communication/files.md#reserved-words
        - .pkit/capabilities/visual-communication/files.md#content-files
        - .pkit/capabilities/visual-communication/files.md#what-a-release-compares
        - .pkit/capabilities/visual-communication/files.md#fonts
        - .pkit/capabilities/visual-communication/files.md#keys-of-combinations
---

# Components

A *component* is data that says how a piece's content is arranged and drawn: the fields it takes, its options, and its parts, each placed by formulas. The *engine* is the capability's code that computes a *scene* from a piece's content and the components that draw it. It knows no component by name (DEC-001 point 4). Where a component's file lies, in a library or in a piece, is in [What the location holds](files.md#what-the-location-holds).

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
- **An item component** draws one item of a list. The pattern names its default in `draw`. Content may name another for the whole list, in a field the pattern declares for the list ([Lists](#lists)). An item may name its own in `use`, a pattern included. Which of them draws an item is in [Repeating over a list](#repeating-over-a-list-row-and-column).
- **A block** is a small component, such as a card, that a pattern draws its items with, or that content places alone (DEC-007 point 1). `tests/card` and `tests/picture` are blocks.
- **A top component** declares `layouts`. A piece names one as its top ([`piece.yaml`](files.md#pieceyaml)). The foundations' `figure` is one, with one layout. Their `deck` is one whose layouts are the forms its pages take, a cover and a slide. Their `site` is one too, whose pages are web pages ([The foundations](files.md#the-foundations), [Layouts](#layouts)).
- **A local component** belongs to one piece. Its `use` is `piece/<component>`, and a library component's is `<library>/<component>` ([Shapes](files.md#shapes)). The lock alone says which version of a library is read ([The lock](files.md#the-lock)).

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
| `pkit_schema`, `schema_version` | The binding: `visual-communication:component` and `1` ([The binding](files.md#the-binding)). Required. |
| `status` | `experimental`, `stable` or `deprecated`, below. Required, but on a drawing, which carries none. |
| `about` | What the component is for, in words. Required. |
| `fields` | The content it takes, in a fixed subset of JSON Schema. |
| `options` | Its options, by name. |
| `states` | Its states, by name. |
| `colour` | Its default colour family. |
| `values` | Its named numbers, each a formula or a switch of formulas. |
| `preferred` | `width` and `height`, the size it asks for, each a formula. |
| `parts` | What it draws and places, by name, in drawing order. |
| `lists` | On a pattern: for each list it repeats over, the field in which content names the list's component, its items' arrangement fields, and a list of ties' end fields. |
| `exposes` | The parts a component that places it may read. |
| `ends` | `true` where the component takes ends, so a pattern may draw a tie with it ([Ties and connectors](#ties-and-connectors)). |
| `tokens` | Its component tokens, by name, each with its type and default ([Tokens](#tokens)). |
| `physical-size` | On a page alone, or a top whose layouts are its pages' forms: the size its pages print at, `{width, height}` in millimetres ([A physical size](#a-physical-size)). |
| `layouts` | On a top component only: its layouts and their slots, and, where they are its pages' forms, each layout's own drawing. |
| `draws` | On a brand's component only: `{top: <library>/<component>, layout: <layout>}`, the top and the one layout it draws, which makes the component a drawing ([A brand's drawing](#a-brands-drawing)). A drawing holds none of `fields`, `options`, `states`, `colour`, `lists`, `layouts` and `ends`. |

Every name in the file takes the capability's name shape ([Shapes](files.md#shapes)).

The status says what the component's library promises (DEC-003 point 7), which a release checks ([What a release compares](files.md#what-a-release-compares)). An experimental component may change in any release, renamed, reshaped or removed. A stable one changes in a breaking way only in a major release of its library. A deprecated one may be removed only in a major release. A drawing carries no status: nothing names one, so its library promises nothing of it, and a change of its look breaks nothing (DEC-034 point 8).

### Fields

`fields` is the JSON Schema of the content the component takes. At every level it takes these keys only:

- **`type`:** `string`, `number`, `integer`, `boolean`, `object`, `array` or `null`, or a list of them.
- **`properties` and `required`:** the fields, by name. No field takes a reserved key's name: `id`, `use`, `concept`, `state`, `override` or `pkit` ([Reserved words](files.md#reserved-words)).
- **`items`, `minItems` and `maxItems`:** what a list holds, and how many. **`enum` and `const`:** the values a field may hold.
- **`description`,** and **`x-pkit-prose: true`,** which marks a field that holds prose. No command reads the mark.
- **`x-pkit-pages: true`,** which marks the list field of a top that holds its pages, where its layouts are its pages' forms ([Layouts](#layouts)).
- **`x-pkit-runs: [<word>, ...]`,** which marks a *field of runs*, below.
- **`$ref`:** a reference that starts with `#/`, read within the component's own `fields`.
- **`additionalProperties`:** only `false`. Leaving it out means the same.

A field whose `type` is `array`, or a list of types that holds it, such as `[array, null]`, is a *list field*. A `repeat` part draws its items, and an option may name one of them. How content is judged against `fields` is in *checks*.

A *field of runs* is a field of text whose content may give it as *runs*: spans of its text, each set in a style of its own, such as the prompt, the command and the comment of a terminal's line (DEC-012 points 1 and 2). How content gives runs is in [content files](files.md#content-files).

- **The mark** `x-pkit-runs` lists the words of the field's *run styles*, such as `[command, prompt, comment]`. Each word is a name, never `by`, and appears once. The first is the default: a run that names no style takes it, and so does a field given as text. Another field may declare other words.
- **Only on a field of text.** The mark lies on one of the component's own fields, or on a slot of a layout that is a page's form ([Layouts](#layouts)), never on a schema within a field, such as a list's items, nor on the schema of all the fields. No `$ref` leads to a marked schema. The field's `type` is `string` and no other, and it holds no `enum`, `const` or `$ref`.
- **Shown by a text part alone.** A text part of the component shows the field, and a `when` may read whether it is filled. No other part reads it: no `slot` places it, no `image` names it, and no `use` part passes it on, for now. At least one text part of a field of more than one word chooses its role, its paint or both by the words ([Switches](#switches)).

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
- **A run's family.** A run of a field of runs that names a concept takes that concept's family, before its instance's own. A run that names none takes its instance's family. A state with a `colour` replaces the family of each run of the instance too, a run's concept included (DEC-012 point 3).
- **A paint `:colour.<member>`** paints with the role the foundations map that member of the instance's family to, or, for a run, of the run's family. Where the instance has no family, its family is none the foundations declare, or the family has no such member, the part paints nothing there, and is reported.
- **The content's `override: {<part>: <role>}`** points one part's paint at another role, never at a component token: the `fill` of a box, an ellipse or a text, every run of the text included, the `stroke` of a line.
- **A run's concept shows** where its paint reads the run's family. A run painted with a role, by its style or by an `override`, shows its concept in no colour, and is reported.
- **Run styles that read a family** are painted from it only where their text lies on that family's own fill, the starter's included. The foundations promise a family's `text` on its `fill` alone, and declare no member of a family promised on the shared surfaces ([The foundations](files.md#the-foundations)). Elsewhere, the contrast as drawn alone guards the colour a run's concept gives it (*checks*).

### Tokens

A *component token* is a role one component declares for what its parts draw, so that a brand may restyle that component alone (DEC-004 point 7, DEC-035 points 1 and 2). A card in a library named `ui` could declare tokens for its box:

```yaml
tokens:
  fill: {type: color, default: '{surface}'}
  gap: {type: dimension, default: '{space.1}'}
parts:
  box:
    x: "=@component.ui.card.gap"
    box: {fill: component.ui.card.fill, stroke: line}
```

- **`tokens`** maps each token's name to `{type, default}`. The name is one segment of the name shape ([Shapes](files.md#shapes)), and the component's file gives the rest of its path, `component.<library>.<component>.<name>`. The card's tokens above are `component.ui.card.fill` and `component.ui.card.gap`.
- **Its type** is any type a role takes but `picture`. **Its default** is always given, and aliases a role of that type: an own role of the component's library, or a role of a library it builds on, the shared roles included. It never aliases a component token, the component's own included.
- **A token names what it styles, not a part.** Several of the component's parts may read one token, such as a box's edge and a divider line that a brand restyles as one.
- **Its own parts read it by its full path,** wherever they read a role. A paint names it, as in `fill: component.ui.card.fill`. So does a text's style, and a formula reads it as `@component.ui.card.gap` ([References](#references)). No other component reads it, and nothing a piece writes names one. A part that reads a token its own component does not declare, in a paint, a text's style or a formula, is reported as `component-token-undeclared`, and the engine keeps what the part reads, the formula included (*checks*).
- **Its value** is a brand's, where the brand names the library and gives it one, and else its default's, as for a library's own role ([`roles.yaml`](files.md#rolesyaml)).
- **A local component declares no token.** Where it would want one, let its parts read the role the token's default would alias.

### Parts

`parts` maps each part's name to one part. The parts are drawn in the order written. A part holds exactly one key that names its kind, and the keys that kind takes:

| Kind | Its other keys | Required |
|---|---|---|
| `box` | `x y width height` | `width height` |
| `ellipse` | `x y width height` | `width height` |
| `text` | `x y width` | |
| `line` | `x1 y1 x2 y2`, or `connect` | all four, or `connect` alone |
| `image` | `x y width height` | `width` |
| `use` | `x y width height fields options` | |
| `slot` | `x y width height` | |
| `repeat` | `x y width height draw colour`, and `row` or `column` | `draw`, and one of `row` and `column`, except over a list of ties, which takes neither |

- **Places and sizes** are formulas that give a length, in the component's own frame. A missing `x` or `y` is zero.
- **`when`** draws the part only while a condition holds. It names a field, and holds while the content fills it: the field is not missing, empty text, an empty list or an empty mapping. A field of runs is filled where one of its runs holds text. Or it is `{<option>: [<word>, ...]}`, and holds while the option takes one of the words. Or it is a switch on a size, or, in a drawing of a layout, on `:as`, each branch `true`, `false` or a `when` of the two forms above ([Switches](#switches)). A part not drawn has zero size, at its place, so a formula that reads its frame holds.

The figure draws its caption only when the content gives one:

```yaml
  caption:
    when: caption
    text: {content: caption, style: type.body, fill: text-secondary}
    x: "=body.x"
    y: "=body.bottom + min(caption.height, @space.2)"
    width: "=body.width"
```

A text part may show a fact of the export it is drawn for, where it would show a field. It names the fact by `fact`, in place of `content`:

```yaml
  line:
    text: {fact: version, style: type.body, fill: text-secondary}
    width: "=:width"
```

- **`fact`** takes `version`, the version's number, `date`, its date, `language`, or `state`, the piece's state. It takes no switch.
- **One of the two.** A text part names `content` or `fact`, never both and never neither.
- **A fact's text** is one run, in the role `style` names. It takes no run styles.
- **What a scene shows for each fact** is in [The facts of an export](#the-facts-of-an-export).

### Switches

A value may be a *switch*: `{by: <option>, <word>: <value>, ...}`. It names an option of words, and gives a value for each of its words, no more and no fewer. A branch may be a switch itself. A paint's branch may be `null`, which paints nothing. A switch serves wherever a part takes a formula, a paint, a style, a word of `text-anchor` or of an operator, or a placed component's option, and in `values` and `preferred`. `values.gap` of `tests/steps` above is a switch.

**A switch on a size,** `{by: ":<axis>", <mode>: <value>, ...}`, chooses by the mode of a size axis. It names the axis after `:`, as a formula reads `:width`. It serves wherever a switch on an option does, and as a `when` ([Parts](#parts)). `tests/steps` could space its steps closer on a phone:

```yaml
values:
  gap: {by: ":device", desktop: "=@space.2", phone: "=@space.1"}
```

- **What it reads.** The mode the scene's key holds, else the axis's default. So a piece that names no size draws the default's branch ([How the engine computes a scene](#how-the-engine-computes-a-scene)).
- **The default is named, and takes what is left out.** The switch names the axis's default. A mode it leaves out takes that branch, so `tablet` above takes `desktop`'s. A new mode draws as the default does until a component names it.
- **Only a size axis a piece can name.** The foundations declare it ([`roles.yaml`](files.md#rolesyaml)). A value axis is refused, since one scene serves each of its modes.
- **The size is the page's.** A component reads the size the piece is drawn at, whatever room its placer gives it. It answers to its slot only by formulas on `:width`, and a drawing of a layout also by `:as`, below.
- **What is refused,** at any depth: a marked name that reads no size axis a piece can name, other than `:as` in a drawing of a layout, and a branch that is no mode. So is a switch with no branch for the axis's default.

**A switch on `:as`,** `{by: ":as", page: <value>, part: <value>}`, chooses by whether the instance is a page. Only a drawing of a layout reads it, the top's own or a brand's ([Layouts](#layouts)). It serves wherever a switch on a size does, and as a `when`. A drawing of the figure could draw a backdrop only where the figure is a page:

```yaml
  backdrop:
    when: {by: ":as", page: true, part: false}
    box: {fill: surface}
    width: "=:width"
    height: "=:height"
```

- **Its values.** `page`, where the instance is a page, and `part`, where it lies inside another page, as a figure in a slide's slot does. The engine sets it from where the instance lies in its piece, and no content gives it. So the piece's top that is a page alone reads `page`, and so does each page of a deck.
- **The default is named, and takes what is left out.** The switch names `page`, the default, and `part` takes that branch where the switch leaves it out.
- **What is refused,** at any depth: a switch on `:as` in a component that is no drawing of a layout, a branch that is no value of it, and a switch with no branch for `page`.

**A switch on a field's run styles,** `{by: <field>, <word>: <value>, ...}`, names the field of runs a text part shows, and gives a value for each of its words, no more and no fewer. Only that text part's `style` and `fill` take one: each run of the text then takes the typography role and the paint its style chooses (DEC-012 point 2). No other property, part, value or option switches on a field's run styles, nor a text part that shows another field. A field of more than one word needs at least one text part of the component, a top's own drawing of a layout included, that chooses by them. Another text part may show the field in one look, and draws every run in it. A terminal's line, whose command is set in the heading's role:

```yaml
fields:
  type: object
  properties:
    line: {type: string, x-pkit-runs: [command, prompt, comment]}
parts:
  line:
    text:
      content: line
      style: {by: line, command: type.heading, prompt: type.body, comment: type.body}
      fill: {by: line, command: text-primary, prompt: accent, comment: text-secondary}
    width: "=:width"
```

### Lists

`lists` declares, for each list field that a `repeat` part of the component repeats over, what the items of that list carry for the component, apart from its own fields and options (DEC-010 points 1 to 4, DEC-011 point 1). Its entry for a list takes three keys, each optional:

- **`component`:** the list's *component field*, a field of the component's own that holds no list. Content names a component in it as it places one, by `use` ([content files](files.md#content-files)), yet nothing is placed there, so no part places the field or passes it on. Which items that component draws is in [Repeating over a list](#repeating-over-a-list-row-and-column). The item takes each key the field gives that the item does not give itself, and a value it takes names the field as its source ([Sources](#sources)).
- **`arrangement`:** the items' *arrangement fields*, by name, each `{words: [<word>, ...]}`. An item gives one of the words, and one that leaves the field out takes the first. A name is no reserved key's, and the words follow an option's rules ([Options](#options)). The component reads an arrangement field, and the component that draws the item never does.
- **A weight** is an arrangement field that also gives `shares`: a number above zero for each of its words, and for no other. A `repeat` part with `sizes: shares` shares its line among the items in proportion to their shares ([Repeating over a list](#repeating-over-a-list-row-and-column)). A list has one weight at most.
- **`ends`:** two *end fields*, `[<start>, <end>]`, which make the list a *list of ties*. Every item of it is a *tie*, and gives both end fields, the first where the tie starts. Each is a name, no reserved key's and no arrangement field's of the list ([Ties and connectors](#ties-and-connectors)).

A pattern that lets content choose the component of its steps, and give a step twice the width of another, could declare:

```yaml
fields:
  type: object
  properties:
    steps: {type: array, items: {type: object}}
    step: {type: object}
lists:
  steps:
    component: step
    arrangement:
      span:
        words: [narrow, wide]
        shares: {narrow: 1, wide: 2}
parts:
  steps:
    repeat: steps
    draw: tests/card
    width: "=:width"
    row: {gap: "=@space.2", sizes: shares}
```

- **A key both declare.** Where an item's component declares a field or an option named as an arrangement field of the item's list, neither reads the key on that item. The component's field stays unfilled, and the arrangement field takes its default. Named as an end field, the tie lacks that end, and is left out. The check reports such a key (*checks*).
- **What is refused** when the component is read: an entry for a list no part of the component repeats over, or for the field that holds a top's pages ([Layouts](#layouts)); a component field that is no field of the component, holds a list, takes runs, or is placed or passed on by a part; an arrangement field with no word, a word twice, or a reserved key's name; a weight whose shares miss a word, name another, or are not above zero; a second weight; and `sizes: shares` on a part whose list has no weight. So is `ends` that are not two names, no reserved key's, each once, and none an arrangement field of the list.

### Exposes

`exposes` lists the parts a component that places this one may read in its formulas. Every other part stays private, so its library may change it freely. Removing or renaming an exposed part is a breaking change (DEC-005 point 3). An exposed `image` part of a produced output also exposes its picture's points, each read as a part of zero size of the component itself. An image of a picture file has no points (DEC-025 point 7). `tests/picture` holds one part, `image`, and declares `exposes: [image]`.

### Layouts

A top component declares `layouts`, by name. Each layout has a *drawing*, the parts that draw the top in it, and the top's own drawing of a layout is the layout's default (DEC-009 point 1). A top declares its layouts in one of two ways.

**One layout for the whole top.** The layout holds its `slots`, each a field of the top that the content fills, and the top's `parts` are its drawing. A slot marked `pages: true` holds pages: each item of its list, or the component placed in it, is a page.

- **A top component with no slot of pages** is a page alone, and part of the page that holds it (DEC-005 point 5). The figure declares `layouts: {frame: {slots: {body: {}, caption: {}}}}`, with no slot of pages. As a piece's top it is one page. Placed in a slide's slot, it is part of that slide.

**Layouts that are its pages' forms** (DEC-010 point 5). The top marks one list field of its own `x-pkit-pages: true`: the field that holds its pages, which lies in no layout. Each layout then takes these keys:

- **`slots`:** the fields a page in that layout fills, each written as a field of `fields` is. They are a page's fields, not the top's. No slot takes a reserved key's name, nor `layout`, the key by which a page names its layout, nor the name of a field of the top. No slot holds pages.
- **`required`:** the slots a page in that layout must fill.
- **`lists`:** the fields of each list among its slots that its drawing repeats over, as a pattern declares them ([Lists](#lists)). They lie in the top's file, and content gives them as it gives the slots (DEC-011 point 5).
- **`preferred`:** the height of a page in that layout, `preferred: {height: <formula>}`, by a formula on its drawing's parts (DEC-022 point 3). A layout says it where the top asks for no height, and may say it where the top asks for one, by a formula or through its [physical size](#a-physical-size). It never says a width.
- **`parts`:** the layout's drawing, which draws one page. Every layout has one. It takes the page's slots, the top's other fields and the words of the top's options, as the content gives them to the top, and the states, colour and values the top declares (DEC-009 point 5). Its `:width` and `:height` are the page's size. A part that shows a slot is named after the slot, as the deck's are, so what the slot places keeps one trace id under every drawing ([A brand's drawing](#a-brands-drawing)).

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

- **The top draws nothing around its pages.** It has no `parts` of its own. Each page is a page of its own, drawn by its layout's drawing at the top's origin. The top is not a page.
- **A page names its form.** It names its layout with `layout`, and fills that layout's slots, or names the component that draws it with `use` ([content files](files.md#content-files)).
- **A page gets the top's width** (DEC-022 point 3). It gets the top's height where the top asks for one, as the deck does, by its `preferred` or through its [physical size](#a-physical-size). Otherwise it gets the height it asks for: its layout's `preferred`, or the component that draws it.
- **A page that asks for more than the top's height** gets the top's, and is reported as an element that gets less than it asks.
- **The top's own frame** in the scene is as large as it asks. Where it asks for no height, it is as tall as its tallest page, and the height names `engine` as its source.
- **A slot that holds one page** places it as every slot places a component, by `use`, and names no layout. The key `layout` belongs to a page of a top whose layouts are its pages' forms, which places no component.
- **A top that is a page alone keeps one layout,** as the figure does. Its content is the top's own mapping, whose keys are the top's fields, and a top with one layout may declare a field named `layout`. So the key cannot choose among forms of such a top without refusing a file format 1 accepts.

A page inside a page is reported: what a slot of pages places, where that slot lies inside a page, and each page of a top whose layouts are its pages' forms, where that top lies inside one.

**A drawing may choose by whether its instance is a page** (DEC-034 point 7). A layout's drawing, the top's own or a brand's, reads `:as` in a switch or a `when` ([Switches](#switches)): `page` where its instance is a page, and `part` where the instance lies inside another page. So one drawing of the figure may draw page dressing, such as a backdrop or the brand's mark, where the figure is the piece's top, and leave it out where the figure is placed in a slide. A drawing that reads no `:as` draws alike in both.

The site is a top whose layouts are its pages' forms, and which asks for its width alone ([The foundations](files.md#the-foundations)). So its layout `standard` says its page's height, by its lowest part. Each page is as tall as its content. The site's file, trimmed, its descriptions and its background left out:

```yaml
preferred:
  width: "=@size.site"
layouts:
  standard:
    slots:
      main: {type: object}
    required: [main]
    preferred:
      height: "=footer.bottom"
    parts:
      header: {slot: header, width: "=:width"}
      main: {slot: main, y: "=header.bottom", width: "=:width"}
      footer: {slot: footer, y: "=main.bottom", width: "=:width"}
```

A part placed from such a page's foot, such as `y: "=:height - footer.height"`, reads the height its own place gives, and is refused as a loop.

#### A brand's drawing

A brand may hold a drawing of its own of a layout of a top, as a component of the brand. Its file names, under `draws`, the top and the layout it draws (DEC-034 point 1). Where the piece's brand holds one, it draws each instance of that layout it fits, in place of the top's own drawing (DEC-009 point 2). An instance is a page where the layout is a page's form, and the whole top where the top has one layout.

- **What it takes.** It declares nothing the content gives. It takes the layout's slots and the lists the layout declares for them, the top's other fields, its options with their words, its states and its colour, so its file holds none of `fields`, `options`, `states`, `colour`, `lists`, `layouts` and `ends`. Content is written against the top, whichever drawing draws it.
- **What it holds.** Its `about`, its `parts`, its own `values`, its own `tokens`, the parts it `exposes`, by the names the top exposes them by, and the size it asks for. It reads none of the top's component tokens ([Tokens](#tokens)), and carries no `status` ([A component's file](#a-components-file)).
- **The sizes it writes** (DEC-034 point 2). A drawing of a page's form writes its page's height alone, `preferred: {height: <formula>}`, as the layout's own drawing does. It must write it where the top asks for no height, and may where the top asks for one, by a formula or through its [physical size](#a-physical-size). It writes no width, since a page gets the top's. A drawing of a top whose one layout is the whole top writes its own `preferred`, whole: the top's parts are that layout's drawing, so the size the top asks for is its drawing's. Where that top declares a physical size, the drawing writes no height: the engine sets it from the width the drawing asks for, in the size's proportion, and a height the drawing writes is refused and not read.
- **What shows a field is named after it** (DEC-034 point 5). Each field it shows is shown by a part named after the field, and a part named after a field shows that field. A part *shows* a field where it places the field's component, draws its text or the picture it names, or repeats over it. A field shown only through a component it places by `use`, which shows it one level down, breaks the rule.
- **Where it fits.** It *takes* a field where a part of it shows the field, or passes it on, where the content gives it; a word the content chose for an option, where a switch or a `when` of it reads that word; a part the content's `override` points at another role, where it paints that part; each part the top exposes, where a component places the top; a run's word, where a text that shows the field chooses by the field's words, and the first word alone where none does; and each end of the ties it draws, where the end is found under it. A part that a `when` leaves out at a key, such as one a size hides, takes nothing there. A drawing takes every state, since a state gives its colour by the top's states. It *fits* an instance where it takes all of it in every language the piece holds and at every key over the size axes the piece names (DEC-034 point 6).
- **Where it does not fit,** the top's own drawing draws that instance, whole, in every language and at every key, and the piece states it ([Checks](checks.md)). The engine places the piece in each language and at each key before it draws any scene, so a preview of one language at one size is drawn by the drawing chosen for the whole piece.
- **Where it draws nothing.** Two drawings of one layout in one brand draw neither, and a drawing of a top whose library the brand does not name draws nothing (DEC-009 points 2 and 3). The test brand's drawing of the deck's cover, trimmed to its title:

```yaml
draws: {top: foundations/deck, layout: cover}
values:
  margin: "=@space.4"
parts:
  band:
    box: {fill: accent}
    width: "=:width"
    height: "=@space.2"
  title:
    text: {content: title, style: type.heading, fill: text-primary}
    x: "=margin"
    y: "=band.bottom + margin"
    width: "=:width - 2 * margin"
```

Content, or a component, that places a drawing by `use`, and a piece whose top is one, are refused: a drawing draws only in place of its top's own drawing (DEC-009 point 5).

### A physical size

A top whose pages print at one size, such as a poster, declares it under `physical-size`: its trim width and height, the size the printed sheet is cut to, in millimetres, each a positive number (DEC-034 point 3). A poster at A1, upright:

```yaml
preferred:
  width: "=@size.figure"
physical-size: {width: 594, height: 841}
```

- **Which tops.** A page alone, or a top whose layouts are its pages' forms, and each of its pages takes the size. A top whose slot holds pages gives each page its size by the parts that place it, so it declares none. Nor does any other component, a brand's drawing among them: a drawing of a page alone prints at its top's ([A brand's drawing](#a-brands-drawing)).
- **The top's alone.** No brand gives it a value, and no formula reads it.
- **The height follows the proportion.** The top asks for its width under `preferred`, as any top does, and for no height there. The engine sets its height from the width it asks for and the size's proportion, and names itself as the height's [source](#sources). So a poster 640 px wide at A1 is 906.13 px tall.
- **Its pages.** In a top whose layouts are its pages' forms, each page gets the top's width and that height, so its pages are fixed pages. A layout may still say its page's height, and a page that asks for more than it gets is reported.
- **The width sets the scale.** An export whose format has a physical page, as PDF has, draws each page at the size, so the page's width, a brand's value, sets how large the brand's type and spacing print.
- **Placed elsewhere,** in another component's slot or as a page of another top, it asks for its size as it does alone, its height in the proportion, and gets what its placer gives. Only the piece's top prints at its size.

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
| `{start}.<measure>`, `{end}.<measure>` | in a component that takes ends, a measure of an end it is given as a tie |

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
- **A component token** reads as a library's role does, by its full path, such as `@component.ui.card.gap`, and only in the component that declares it ([Tokens](#tokens)).

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
- **It reads a role** that has no value under the brand, a length in a unit other than `px`, or a role that is neither a length nor a number. A role has none where no library the piece locks declares it, or where it is a library's role that neither the brand nor its chain of defaults gives a value ([`roles.yaml`](files.md#rolesyaml)). A part reads no value from a picture role, whether the brand gives it a file or not ([Picture roles](files.md#picture-roles)). A library's role with no value, a component token among them, is found at the piece's lock, not in the component. Where the brand, or a base below it, names the library, the part takes no finding: that brand's `library-role-missing`, or its library's own finding where a default does not hold, reports it.

It finds these when it computes the scene: a division by zero, `:index` or `:count` in a component that is no item, a path to an exposed part, a point, an item or an end that is missing, and a loop. A value that cannot be computed is zero. The check reports each problem as a finding (*checks*).

## Layout operators and drawing primitives

The engine knows the five primitives, the two ways to place a component, the one way to repeat one and the connector tool, below. It has no other primitive and no other layout operator.

### Primitives

A primitive's properties lie in its own mapping, under SVG's names.

| Primitive | Its properties | What it draws |
|---|---|---|
| `box` | `fill`, `stroke`, `stroke-width`, `rx` | a rectangle in its frame |
| `ellipse` | `fill`, `stroke`, `stroke-width` | an ellipse in its frame |
| `text` | `content` or `fact` (one of the two required), `style` (required), `fill`, `text-anchor` | the text of a field or of a fact of its export, in lines, each run in its own role and paint |
| `line` | `stroke` (required), `stroke-width`, `marker-start`, `marker-end` | a straight line from `x1 y1` to `x2 y2`, or a connector between its component's ends |
| `image` | `produced`, `content`, `file` or `role` (exactly one required) | the picture of a produced output of the piece, a picture file, or the file the brand gives a picture role |

- **A paint,** `fill` or `stroke`, is a colour role's token path, `:colour.<member>`, or a switch. `stroke-width` and `rx` are formulas that give a length.
- **A text** shows the field `content` names, or the fact `fact` names ([Parts](#parts)), in the typography role `style` names. A text that shows a field of runs draws each run in the role and the paint its style chooses ([Switches](#switches)). Its height is always its measured text's: a text that gives a `height` is reported as a value with two owners. With a `width`, its lines are broken to that width; without one, each paragraph is one line, and the text is as wide as its widest. `text-anchor` is `start`, the default, `middle` or `end`: where each line stands in the text's width.
- **A line's frame** comes from its ends: it starts at the lesser of the two `x` and of the two `y`, and is as wide and as tall as the distance between them. A connector's frame holds every point of its route.
- **An arrowhead,** `marker-start` or `marker-end`, is `none`, the default, or `arrow`, or a switch. It is drawn at that end of the line, pointing away from it, in the line's stroke.
- **An image** names exactly one of four properties, each a source of its picture (DEC-025 point 1):
  - **`produced`** names a field whose value is a produced output of the piece (*outputs*).
  - **`content`** names a field whose value is the bare name of a picture file of the piece ([Content files](files.md#content-files)). A field the content leaves empty draws nothing, and the part has zero size at its place.
  - **`file`** gives the bare name of a picture file of the component's own library ([Picture files](files.md#picture-files)).
  - **`role`** names a picture role, such as `picture.logo`. The image shows the file the brand gives that role, in each mode and at each size ([Picture roles](files.md#picture-roles)).
- **An image's frame.** It needs a `width`. Where it gives no `height`, its height keeps the picture's proportions. A picture role's files share one proportion at each size, so its height is the same in every value mode. The picture is drawn whole, centred, as large as its frame allows, at every size (DEC-025 point 6). A produced output's points are mapped into the frame the same way. The variants of one picture share one pixel size and the same points, and the engine reads the first variant key in order.
- **An image not drawn.** An output the piece lacks is not drawn, and is reported. So is a picture file that is missing or cannot be read ([Picture files](files.md#picture-files)).
- **A picture role the brand gives no file** is not drawn, and the part has zero size at its place. No piece takes a finding for it, since no brand owes one.
- **A `role` that names no picture role** is refused in the component, whether it names no role or a role of another type.
- **Another file at a size** takes a part for each file, each with a `when` by the size ([Switches](#switches)).

### Placing a component: `use` and `slot`

- **`use: <library>/<component>`** places that component. `fields` maps each of its fields to a field of this component, whose content it passes on. `options` gives each of its options a word, or a switch on an option of this component.
- **A component never places itself,** directly or through others. The engine reports the chain of components.
- **`slot: <field>`** places the component the content gives in that field: `{use: <library>/<component>}`, with that component's fields and options beside `use`. Where the field is empty, the slot is not drawn.

### Repeating over a list: `row` and `column`

A `repeat` part draws a component for each item of a list field, in the content's order. **What draws an item** is the component its own `use` names, else the one its list's component field names, else `draw` ([Lists](#lists)). An item that is not a mapping, repeats an id, or names no component, is reported and left out. It takes no place among the items drawn, so `:index` and `:count` do not count it, and its trace id keeps its place in the content's list. `colour` gives the items' default colour family.

The part's *layout operator*, `row` or `column`, lays the items along a line, across or down. Its settings take the names of CSS flexible layout:

| Setting | Takes | Default | What it does |
|---|---|---|---|
| `gap` | a formula that gives a length | zero | the space between two items along the line |
| `sizes` | `own`, `equal`, `shares` | `own` | `own`: each item takes the size it asks for along the line. `equal`: the items share the part's size along the line, less the gaps, equally. `shares`: they share it in proportion to the shares their list's weight gives them, and equally where every share is the same ([Lists](#lists)). With `equal` or `shares`, the part must give that size. |
| `justify-content` | `start`, `center`, `end`, `space-between` | `start` | Where the items lie along a line longer than they ask for. `space-between` widens each gap instead. |
| `align-items` | `stretch`, `start`, `center`, `end` | `stretch` | `stretch`: each item is as large across as the line, that is the part's size across, else the largest size an item asks for. Where the stretch goes inside the item is in [What an element asks for, and what it gets](#what-an-element-asks-for-and-what-it-gets). Otherwise each item takes the size it asks for across, at the start, the centre or the end of the line. |

- **The part's own size,** where it gives none, is what its items ask for: along the line, their sizes and the gaps; across, the largest.
- **In the tests' figure,** where `@space.2` is 8 px, `tests/steps` lays three steps with `row: {gap: "=gap", sizes: equal, align-items: stretch}` in a row 608 px wide. Each step is 197.33 px wide, and as tall as the tallest.
- **Over a list of ties,** the part takes neither `row` nor `column`. Each tie lies in the part's whole frame, by default the component's, and is drawn between its ends ([Ties and connectors](#ties-and-connectors)). A tie whose component takes no ends is left out.

**A list that changes direction** has two `repeat` parts over it, a `row` and a `column`, each with a `when` by a size ([Switches](#switches)). At each mode, exactly one of them says yes, so each item is drawn once. `tests/steps` could lay its steps down a phone:

```yaml
parts:
  across:
    repeat: steps
    when: {by: ":device", desktop: true, phone: false}
    draw: tests/card
    width: "=:width"
    row: {gap: "=gap", sizes: equal, align-items: stretch}
  down:
    repeat: steps
    when: {by: ":device", desktop: false, phone: true}
    draw: tests/card
    width: "=:width"
    column: {gap: "=gap"}
preferred:
  height: "=across.height + down.height"
```

- **At `tablet`,** which neither part names, both take their `desktop` branch, so the steps lie in a row.
- **What it costs.** No option names an item of the list, as of any list two parts repeat over ([Options](#options)). An item's trace id names the part that draws it, so it differs by size ([Trace ids](#trace-ids)). A formula that reads the list's frame reads both parts, and the hidden one has zero size.
- **An item a size hides** is missing at that size. A formula that reads it fails there, and so does a tie that ends at it ([Ties and connectors](#ties-and-connectors)). Content drawn at one size and not at another is stated as a fact (*checks*).
- **What is refused** when the component is read: parts over one list where not exactly one may be drawn at some mode. A list is judged where one of its parts has a `when` by a size, and then every part over it counts:
  - **A part with no `when`** is drawn at every mode.
  - **A `when` that names a field or an option's words** may draw its part at every mode, as the content or the option decides.
  - **A `when` by a size** reads the mode's branch: `true` draws its part, and a field or an option's words may draw it.
  - **A `when` by `:as`,** in a drawing of a layout, may draw its part at every mode where its branch for `page` or for `part` may, since its instance may lie as either ([Switches](#switches)).

### Ties and connectors

A *tie* is an item that its pattern draws as a connector between two other items, its *ends* (DEC-011 point 1). The pattern declares the list of ties and its two end fields under `lists`, and draws it with a `repeat` part of its own ([Lists](#lists)). Content names each end by a key path ([content files](files.md#content-files)).

- **A component that takes ends** declares `ends: true`. Its pattern gives each tie it draws two ends, `start` and `end`: the element drawn for each end's item, or the point an end names. It declares no option `start` or `end`.
- **Reading an end.** A formula reads an end as `{start}` or `{end}`, then a measure, in the tie's own frame. Nothing below an end may be read, since an end names no part.
- **The connector tool** is a `line` part that gives `connect` in place of its ends: `straight`, or `corners`, or a switch. It runs from the start to the end, and never around anything (DEC-005 point 2).
- **Where it meets an end.** It leaves each end's frame by the side that faces the other end. That is the left or the right side where the two frames lie further apart across than down, else the top or the bottom.
- **Several ties on one side** of one item spread evenly along it. They are ordered by where the centres of their other ends lie along that side, then as their lists hold them.
- **A point.** A tie that names a point ends at that point, which its item's component exposes ([Exposes](#exposes)). One that names a point its item does not expose, as of a picture file, is left out and reported.
- **With corners,** the connector leaves and meets each end square to its side, and turns twice, halfway between them. Where the two ends lie in one line, it is straight.
- **Found once.** An end is the element drawn for its item, wherever a component below the pattern draws it. It is found where that item is drawn exactly once, on the tie's page.
- **Left out.** A tie whose end is not found, or that does not lie on one page with both its ends, is left out and reported. The rest of its list is drawn.
- **Computed like any value.** The frames of the ends are computed in the order the references give, and a loop through them is refused ([How the engine computes a scene](#how-the-engine-computes-a-scene)). Where they cannot be computed, as in a loop, the scene holds no connector for the tie, and the finding says why.
- **Items that overlap.** Two ends whose items overlap in the drawing are drawn as they lie, and are no finding. The connector routes around nothing, so the drawing shows the overlap as it is.

A pattern that ties its steps, and an arrow that draws each tie:

```yaml
# The pattern
lists:
  links:
    ends: [from, to]
parts:
  links:
    repeat: links
    draw: piece/arrow
# piece/arrow
ends: true
parts:
  arrow:
    line: {stroke: line, marker-end: arrow}
    connect: corners
```

Content then ties two steps. Inside a flow mapping, YAML reads `[` as the start of a list, so a key path there takes quotes. In a block mapping it needs none:

```yaml
links:
  - {id: plan-build, from: {item: "steps[plan]"}, to: {item: "steps[build]"}}
  - id: build-note
    from: {item: "steps[build]"}
    to:
      item: steps[note]
```

### What an element asks for, and what it gets

- **Each element asks** for its `preferred` size, and **gets** one (DEC-005 point 3). It gets a size from what places it. A top component gets what it asks for. A page of a top whose layouts are its pages' forms gets the size [Layouts](#layouts) gives it.
- **A brand's drawing writes what its instance asks for, and the top what a page gets** (DEC-034 point 2). Each size is the drawing's or the top's by the file it is written in. A page drawn by a brand's drawing asks for the height its drawing writes, and gets the top's width, and the top's height where the top asks for one. A top whose one layout is the whole top, drawn by a brand's drawing, asks for the drawing's `preferred`. A component placed by `use` or `slot` gets its part's size, else what it asks for, unless [a stretch reaches it](#what-an-element-asks-for-and-what-it-gets). An item gets what the operator gives it. A formula reads the size it gets as `:width` and `:height`.
- **A stretch reaches the part drawn last.** An item that `stretch` makes larger across than it asks for passes the rest on to the last part it draws. That part takes it where it places a component by `use` or `slot` and gives no size across. Its component gets as much more, and passes it on the same way. So a panel that holds panels of its own ends where the row's other panels end.
  - **What the item asks for is unchanged.** Its formulas still read that part at the size the part asks for.
  - **The size passed on names `engine` as its source** ([Sources](#sources)).
  - **Only a stretch passes on.** A component that a part's formula gives more than it asks for keeps its parts as they ask.
- **A top with a physical size asks for its height through it,** wherever it lies: the width it asks for, in the size's proportion ([A physical size](#a-physical-size)). Its height names `engine` as its source, and so does the height of a page that gets it, or of a part that places it and gives none.
- **Each value has one owner:** a part's formula, its measured text, or its parent's layout.
- **A component that gets less than it asks for** is reported.

## How the engine computes a scene

The *scene* is every element's final frame, values and source, for one language and one key over the size axes. The engine computes it from the piece's content, the components that draw it, the roles of its brand, and the fonts and pictures they name. The commands compute a scene for each language and each key over the size axes the piece names, or for those asked for.

- **A size axis** is an axis of kind `size` ([`roles.yaml`](files.md#rolesyaml)). A scene's key names the modes of the size axes alone ([Keys of combinations](files.md#keys-of-combinations)).
- **Each scene reads each role at its key.** So a frame, a width or a text's lines may differ from one size to another.
- **And each switch on a size at its key.** So a part drawn at one size may be hidden at another, and a list may change direction ([Switches](#switches)).
- **A piece drawn only in each size axis's default** has one scene for each language, at the key `default`.
- **A picture role stays its role,** as a colour does. For each combination it draws, the engine takes the role's file from the brand's values, and hands it to the renderer (DEC-025 point 7).

A scene is computed, never committed. Under one release of the capability, the same files and facts give the same scene on every machine.

- **Built from the content.** The engine places the top component with the content, then builds each part, item and placed component below it.
- **Fonts first.** Before it computes any place or size, a font family with no file, or a character no family measures, refuses the scene ([Text](#text)).
- **Value by value.** Each size, place, value, list arrangement and text's lines is computed on first use, in the order the references give, as a spreadsheet computes its cells. So a parent's width and a child's measured height form no loop.
- **A loop** is refused, naming every element in it. Each problem is a finding, and a value that cannot be computed is zero. A tie's connector whose ends cannot be computed is left out instead ([Ties and connectors](#ties-and-connectors)).

### The facts of an export

A component may show the facts of its export ([Parts](#parts)). A scene takes them as inputs, beside the files.

- **`language` and `state`** come from the piece's files. A scene shows them as the files hold them, such as `en` and `draft`.
- **`version` and `date`** come from no file. A scene shows what the command that computes it fills them with.

Each fact takes one form in every language. A *stand-in* is a fixed text for a fact that no file holds. Each stand-in is wide enough that a usual real value fits:

| Fact | Its form | Its stand-in |
|---|---|---|
| `version` | `v<N>`, with `<N>` the version's number | `v88` |
| `date` | `YYYY-MM-DD` | `2088-08-28` |

Which text fills `version` and `date`:

- **The check, and a render's findings,** take the stand-ins. So the same files give the same answer on every machine, on any day.
- **What a person looks at** shows real text: a preview, a before-and-after and the viewing step. Each fills what this clone's next export would: its next number, and the date of the run. Another clone may show another number.
- **An export** shows one number and one date in every file of its version, those its record of exports keeps: its number, and the date of the time it records. Its fingerprint reads neither, so a new number makes nothing stale.
- **Where there is no next number,** what a person looks at takes the stand-ins, and the command says so, and why. A record of exports that cannot be read gives none, as one that conflicts on a merge. A final piece has none, since it takes no export.
- **A stand-in that overflows** is a finding at the element that shows it, and it names the component. It fails where the project can correct that component, and asks for attention in a released library.
- **A real text that overflows in a preview** is said in the render's output, and no record keeps it.
- **A new stand-in** reaches a piece as a new engine does, at a render.

### What a scene holds

The scene's root holds `piece`, its `lock`, the `language`, the `size-key`, its key over the size axes, `seam` (the version of the seam its plugins read), `pages` (the trace ids of its pages, in order: a top that is a page alone, what a slot of pages places, or each page of a top whose layouts are its pages' forms), `fixed-pages`, `physical-size` and `children`. `fixed-pages` says whether the pages are *fixed pages*: `true` where the top's layouts are its pages' forms and it asks for a height, by a formula or through its physical size, which each page then gets, as a deck's slides do (DEC-031 point 2). A site's pages take their own height, and a page alone and what a slot of pages places are none, so it is `false` for them. So a scene's pages are all fixed pages or none is, and the top's name decides nothing. `physical-size` holds the physical size of the piece's top, `{width, height}` in millimetres as the top declares it, or `null` where it declares none, and every page of the scene takes it ([A physical size](#a-physical-size)). Each element holds its `type`, `group` or a primitive's kind, and its `id`, its trace id. It holds its frame, `x y width height`, relative to its parent, in px, rounded to 1/100 px, half away from zero. Then come its properties, `sources`, where each came from, and on a group its `children`, in drawing order.

A placed component's group adds `component` (its `use`), `version` (its library's, none for a local component), `options` (the value each option takes) and, on a page, `page: true`. A top whose layouts are its pages' forms holds no `page`. Its group holds its pages, each a group with `page: true`, whose `component` is the top's where its layout's drawing draws it, else the one the page names. A `repeat` part is a group too, holding its items. A `box`, an `ellipse` and a `line` add their paints and lengths, and a line its ends. A line adds `marker-start` and `marker-end` where it draws an arrowhead there. A tie's connector adds these:

- **`points`:** where its route turns, every point of it, its ends first and last. A connector whose route does not turn holds no `points`, and keeps its ends as `x1 y1 x2 y2`.
- **`attached`:** for each end, `start` and `end`, the trace id of the element it meets, with the `side` it meets, or the image part with the `point` it ends at.
- **Its ends' sources:** the end fields that name them, such as `content:body.links[plan-build].from`.

A `text` adds the rest of what [Text](#text) describes:

- **The text's own:** `text-anchor`, `line-height`, the greatest among the typography roles its runs take, `text`, its runs' texts joined, and `measured-height`, the number of its lines times its line height, with `overflow: true` where it overflows.
- **`paragraphs`:** the text split at its line feeds, each paragraph a list of its runs' parts. A run that goes on past a line feed is a run of each paragraph it reaches. Each holds its `text`, its paint `fill`, its typography role `style`, its `font-family`, `font-size` and `font-weight`, the `fonts` that measured it, each family's file and its sha256, how it was `measured`, and the `sources` of each. A text of one run holds one run in each paragraph.
- **`lines`:** each line's `text`, its drawn `width`, its `baseline` below the line's top, its `paragraph`, from 0, and its `spans`, each the part of one run on it: the run's place among its paragraph's runs, from 0, its text and its width.

An `image` adds `preserveAspectRatio` (`xMidYMid meet`), and what it shows (DEC-025 point 7):

- **A produced output:** `output`, `variants` by key with each file and pixel size, and `points` mapped into its frame.
- **A picture file:** `file`, its bare name, and `library`, where it lies: `piece`, or the library's version as `<library>@<version>`. It holds no variants and no points.
- **A picture role:** `role`, its token path. It holds no file, no variants and no points, so one scene serves every value mode.

Colours stay role names. A renderer takes their values from the brand's resolved values, so one scene serves every mode of the value axes at its key (*outputs*). This is the first step's head in a scene of the figure, trimmed. Its field takes no runs, so it is one run:

```json
{"type": "text", "id": "figure/body/steps[plan]/head",
 "x": 8.0, "y": 8.0, "width": 181.33, "height": 22.4,
 "text-anchor": "start", "line-height": 22.4, "text": "Plan the work",
 "paragraphs": [[{"text": "Plan the work", "fill": "text-primary", "style": "type.body",
   "font-family": ["Source Sans Pro"], "font-size": 16.0, "font-weight": 400,
   "fonts": [{"family": "Source Sans Pro", "file": "SourceSansPro-Regular.otf", "sha256": "6b096b47…"}],
   "measured": "file",
   "sources": {"fill": "default:tests/card", "font-size": "role:type.body", "style": "default:tests/card",
               "text": "content:body.steps[plan].head"}}]],
 "lines": [{"text": "Plan the work", "width": 91.97, "baseline": 16.89, "paragraph": 0,
            "spans": [{"run": 0, "text": "Plan the work", "width": 91.97}]}],
 "measured-height": 22.4,
 "sources": {"height": "engine", "line-height": "role:type.body", "text": "content:body.steps[plan].head",
             "x": "role:space.2"}}
```

### Trace ids

Every element carries its *trace*, an id that comes from the path of instances, parts and items, never from the order of drawing (DEC-005 point 5).

- **The top component's** id is its component's name: `figure`.
- **A part's** id is its component's id, `/`, and the part's name: `figure/body`. A component placed by `use` or `slot` takes its part's id.
- **An item's** id is its `repeat` part's id followed by `[<id>]`, or by `#<place>`, from 1, where the item has no id: `figure/body/steps[plan]`, `figure/body/steps#2`.
- **A page of a top whose layouts are its pages' forms** takes the top's id, `/`, and the field that holds the pages, followed by `[<id>]` or `#<place>` as an item's: `deck/slides[cover]`. Each part of its drawing takes the page's id: `deck/slides[cover]/title`.
- **Under every drawing** (DEC-034 point 5). An instance of a layout keeps its id whichever drawing draws it, the top's own or a brand's: the top's name, or its page's path, never the drawing's name. What a field shows keeps the instance's id and the field's name, `deck/slides[cover]/title`, since each drawing shows it by a part named after the field. A drawing's other parts take ids of their own, which differ between drawings. The instance's group names the drawing that drew it as its `component`, `test-brand/cover`, with its brand's version, so each element traces back to its drawing.

### Sources

Each drawn property names its source in `sources`:

- **`content:<field path>`:** a field of the content, such as `content:body.steps[plan].head`. The path names the keys the content file writes, joined by `.`, an item of a list as `[<id>]`, or as `#<place>` from 1 where it has no id. It names the list field, where a trace id names the `repeat` part. Under a `use` part that passes a field on under another name, at any depth, it keeps the name the content file writes. A value an item takes from its list's component field names that field, such as `content:body.kind.tone`. A run of a list of runs is named by its place among its field's runs, as an item with no id: `content:body.say#2`. The run's style comes from `<its source>.style` where it names one, and its family from `<its source>.concept`.
- **`fact:<word>`:** a fact of the export a text shows, such as `fact:version`, whether a stand-in or real text fills it ([The facts of an export](#the-facts-of-an-export)).
- **`option:<name>`:** a value a switch on that option chose.
- **`size:<axis>`:** a value a switch on that size axis chose, such as `size:device`.
- **`:as`:** a value a switch on `:as` chose, by whether its instance is a page ([Switches](#switches)). It is a kind of its own, and names neither value.
- **`default:<library>/<component>`:** the component's own value, such as the picture file an image names by `file`. A field that a `use` part does not pass on is the placing component's, which gives it nothing.
- **`role:<token path>`:** a formula that reads one role and nothing else, such as `"=@space.2"`, a run's typography role, or the role whose line height a text takes. It is also the source of the picture role an image shows.
- **`engine`:** a value the engine computed, such as a text's measured height, an item's frame or the height a top asks for through its [physical size](#a-physical-size), or one the component leaves to the engine's default, such as `text-anchor` on a text that gives none.

## Text

- **The default font profile.** The engine measures every text from the committed font files that the brand names for each family, never from a font found on the machine. Each run records this as `measured: file`. How a brand names its files is in [Fonts](files.md#fonts).
- **Runs.** A text is one or more runs, joined in order. A text whose field takes no runs, or is given as text, is one run. Each run is measured in the typography role its style chooses (DEC-012 point 4).
- **The typography role** that `style` names gives `fontFamily`, one family or a list, `fontSize` in px, `lineHeight` as a ratio of the size, `fontWeight`, and a `letterSpacing` of zero, if any. A role that names no family, gives another letter spacing, a size in another unit or no line height as a number is reported, and the text is not drawn.
- **Several families.** The first family measures each character it has, the next the rest, and so on.
- **One file a family.** A family's one file measures the text, whatever its weight. A brand that gives a weight a family of its own, as the test brand's heading is, has that weight measured and drawn from its own file.
- **Refused before layout.** A family with no committed file, a file the engine cannot measure from, or a character no family measures refuses the scene. The message names it.
- **Shaped from the file.** Each piece of a run in one family is shaped with HarfBuzz, with the font's default features. A line's width is the sum of its advances, each at its own run's font size. Spaces at its end do not count.
- **The line height** is the font size times `lineHeight`. A text takes the greatest line height among the roles its runs take, so its lines lie evenly, and **the measured height** is the number of lines times that line height.
- **The baseline** of each line lies below the line's top. Where the line's runs take one role, the space above and below its letters is split evenly, from the first family's metrics, as a text of one run is placed. Where they take several, it is split evenly around the greatest ascent and the greatest descent among their first families, so the line's runs stand on one baseline.

### Breaking lines

- **Paragraphs.** The text is split into paragraphs at its line feeds. A run whose text holds a line feed goes on into the next paragraph. With no width, each paragraph is one line.
- **A width:** the engine breaks each paragraph where Unicode's line-breaking rules (UAX #14) allow it and the language's own rules do not forbid it. It fills each line with as much as fits in the width less 2 % of the font size, and places the line in the whole width. So a renderer's slightly different metrics move no word. A text of several runs takes the margin at the greatest font size among the roles its runs take (DEC-005 point 4, DEC-012 point 4).
- **Across runs.** The engine finds where a paragraph may break in its whole text, whichever runs hold it, and measures each part of a line in its own run's role. So a word whose letters lie in two runs stays one word.
- **The language's rules** are read by the primary subtag of the scene's language. In Czech, `cs`, a one-letter word never ends a line: it moves to the next line with the word after it, whichever runs hold them. Other languages follow Unicode's rules alone.
- **A word wider than its line** may break after a `/` in it. A word still wider stays whole, and the text overflows: it holds `overflow: true`, and the check reports it.
- **Never shrunk.** The engine never makes text smaller to fit, and never hyphenates.
