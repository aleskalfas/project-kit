---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/visual-communication/libraries/starter/library.yaml
        - .pkit/capabilities/visual-communication/libraries/starter/roles.yaml
        - .pkit/capabilities/visual-communication/libraries/starter/components/*.yaml
        - .pkit/capabilities/visual-communication/libraries/foundations/roles.yaml
        - .pkit/capabilities/visual-communication/scripts/add.py
      record:
        - visual-communication:DEC-003#7
        - visual-communication:DEC-003#9
        - visual-communication:DEC-004#10
        - visual-communication:DEC-007
        - visual-communication:DEC-008
        - visual-communication:DEC-010
        - visual-communication:DEC-011
        - visual-communication:DEC-012
      artefact:
        - .pkit/capabilities/visual-communication/files.md#the-foundations
---

# The starter

The starter is the component library to start from (visual-communication DEC-007). Its *patterns* arrange items, each for one job a visual does. Its *blocks* draw those items, or stand alone in content. The starter holds the forms, and a brand gives them their look.

Bring it into the location beside the foundations:

```
pkit visual add starter
```

Its version 1.0.0 is not released yet. Every component is experimental, so a later version may change it, and a piece that draws one is told so.

## The patterns, by the question they answer

Each pattern answers one question a visual answers. Choose a pattern by its question, not by its look.

| Pattern | Its question | Take another pattern when |
|---|---|---|
| `layers` | What rests on what? | the items are of equal standing, in no order: `list` |
| `list` | What are the items? | each item rests on the next: `layers` |

### `layers`: what rests on what?

- **Form:** levels stacked one on another, the top first, each as wide as the stack. Notes may stand to the right of the stack, sharing its height, for what holds across the levels. Ties join a note or a level to another.
- **Source:** Nancy Duarte's structure (*slide:ology*, chapter 3). Lohse, Biolsi, Walker and Rueter's structure diagrams, and Yuri Engelhardt's lining up in an order, check it.
- **Options:** none.
- **Lists:**
  - `levels`, each drawn by the `card`, unless the component field `level` names another;
  - `notes`, each drawn by the `card`, unless the component field `note` names another;
  - `ties`, a list of ties with the end fields `from` and `to`, each drawn by the `connector`, unless the component field `tie` names another.
- **Its boundaries:** a level rests on the one below it, where a list's items have no order. Layers say nothing of time, where steps follow one another.

### `list`: what are the items?

- **Form:** items of equal standing, in no order, side by side in one row, under a head where the content gives one.
- **Source:** Yuri Engelhardt's lining up, with no order.
- **Options:** `widths`, its words `equal` and `own`. With `equal`, the default, each item is as wide as the others and as tall as the tallest. With `own`, each takes the size it asks for, as a row of tags does.
- **Lists:** `items`, each drawn by the `card`, unless the component field `item` names another.
- **Its boundaries:** a list's items have no order, where layers rest one on another and steps follow one another. Items that belong to groups need a pattern of groups.

## The blocks

A block draws one item of a pattern, or stands alone where content places it.

### `card`

- **Form:** a box with rounded corners that holds a head, a tag and a text, one under another, each where the content gives it.
- **Fields:** `head`, `tag` and `text`, each optional. `text` is a field of runs, its words `plain` and `strong`, `plain` the default.
- **Options:**
  - `fill`: `plain`, the default, lies on the surface; `tint` lies on its colour family's fill, its texts in the family's text.
  - `bar`: `none`, the default; `top` or `left` draws a bar in the family's line along that side.

### `tag`

- **Form:** a short label on a small box with rounded corners, all in its colour family: its fill, its edge and its text. It is as large as its label, on one line.
- **Fields:** `label`, required.
- **Options:** none. Placed alone or in a list, it takes its concept's family. A card's tag stays `neutral`, even on a tinted card.

### `connector`

- **Form:** a line from where a tie starts to where it ends, in its colour family's text, with arrowheads where the content asks. It routes around nothing, so a tie best joins items set apart, with nothing between them.
- **Source:** Yuri Engelhardt's linking by a connector.
- **Ends:** it takes the two ends a pattern's list of ties gives it, so a pattern draws it as a tie.
- **Options:**
  - `route`: `straight`, the default, or `corners`.
  - `arrow`, where its arrowheads stand: `end`, the default, `start`, `both` or `none`.

## Colours

Each starter block declares the colour family `neutral`, which the concept an item names replaces with the concept's own. A text in a family's text lies on that family's fill, a pair the foundations declare. On the surface, a card's texts take the shared roles `text-primary` and `text-secondary` instead. So a run of a card's text reads the family only where the card is tinted.

A connector's line takes its family's text, not its line. Nothing beside the line shows the tie, so it needs a contrast of 3 to 1 against what it lies on (WCAG 2.1, success criterion 1.4.11). A family's line edges a fill, and may be faint: the neutral family's is the shared `line`. A family's text is the member a brand makes legible, since the foundations pair it with the family's fill.

## Shared roles, and the starter's own

A component reads a shared role where the starter means just that role, such as the body's type or the surface. It reads one of its own roles where a brand may want the starter's look apart, such as a card's corners.

- **Colours** are always shared: `surface`, `line`, `text-primary`, `text-secondary`, and each family's `fill`, `line` and `text`. The starter declares no colour role, and so no contrast pair.
- **Shared sizes and types:** `type.body` sets a card's plain text and a tag's label. `space.1` and `space.2` lie around a tag's label, and between a card's head, tag and text.
- **Two more shared roles:** `stroke.thick` and `type.strong`, roles of the foundations ([The foundations](../../files.md#the-foundations)). Neither has a default, so every brand gives each a value (visual-communication DEC-008 point 2).
- **The starter's own roles,** each with a default whose chain ends at a shared role:

| Role | What it sizes or sets | Its default |
|---|---|---|
| `starter.corner` | the radius of a card's and a tag's corners | `space.1` |
| `starter.inset` | the space between a card's edge and what it holds | `space.3` |
| `starter.gap` | the space between a pattern's items | `space.3` |
| `starter.bar` | how thick a card's bar is | `space.1` |
| `starter.edge` | how wide a card's and a tag's edge is | `stroke.thin` |
| `starter.connector` | how wide a connector's line is | `stroke.thick` |
| `starter.type.head` | the type of a card's head and a list's head | `type.heading` |
| `starter.type.strong` | the type of a strong run in a card's text | `type.strong` |

A brand that does not name the starter draws it at these defaults, in the brand's own values for the shared roles. A brand that names the starter by its major, 1, may give any of these roles a value of its own (visual-communication DEC-008 point 4).

At the defaults a connector's line is as wide as a line drawn on its own, not as an edge. A strong run keeps the body's size and line height, in a heavier weight, so it stands out without breaking its line.

## What the starter leaves out, for now

- **A stepped pyramid,** whose levels narrow towards the top.
- **Notes to the left of the stack.** `layers` places them to the right only.
- **A colour for each place,** such as a tint that deepens down the levels (project-kit#2576).
- **A legend and icons,** so that colour is never the only sign (project-kit#2576).
- **The other patterns and blocks:** the patterns `panels`, `groups` and `network` with the blocks `code` and `aside` (project-kit#2565), and the rest of the first wave (project-kit#2576).
- **Arrangement fields.** No pattern declares one yet, so no item chooses its own size or place in its list.
