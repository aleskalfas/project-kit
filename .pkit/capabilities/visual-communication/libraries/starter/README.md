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
        - visual-communication:DEC-005#2
        - visual-communication:DEC-007
        - visual-communication:DEC-008#1
        - visual-communication:DEC-008#2
        - visual-communication:DEC-008#3
        - visual-communication:DEC-008#4
        - visual-communication:DEC-008#6
        - visual-communication:DEC-010#1
        - visual-communication:DEC-010#2
        - visual-communication:DEC-010#3
        - visual-communication:DEC-010#4
        - visual-communication:DEC-010#6
        - visual-communication:DEC-011#1
        - visual-communication:DEC-012#1
        - visual-communication:DEC-012#2
      artefact:
        - .pkit/capabilities/visual-communication/files.md#the-foundations
        - .pkit/capabilities/visual-communication/files.md#content-files
        - .pkit/capabilities/visual-communication/files.md#the-library-folder
---

# The starter

The starter is the component library to start from (visual-communication DEC-007). Its *patterns* arrange items, each for one job a visual does. Its *blocks* draw those items, or stand alone in content. The starter holds the forms, and a brand gives them their look.

Bring it into the location beside the foundations:

```
pkit visual add starter
```

A released version of it never changes: a change is a new version ([The library folder](../../files.md#the-library-folder)). Every component is experimental, so a later version may change it, and a piece that draws one is told so.

## The patterns, by the question they answer

Each pattern answers one question a visual answers. Choose a pattern by its question, not by its look.

| Pattern | Its question | Take another pattern when |
|---|---|---|
| `layers` | What rests on what? | the items are of equal standing, in no order: `list` |
| `list` | What are the items? | each item rests on the next: `layers`; the items belong to groups: `groups` |
| `groups` | Which items belong together? | the items belong to no group: `list`; what matters is what ties them: `network` |
| `network` | What is connected to what? | the items are only grouped: `groups` |
| `panels` | Which views, side by side, show one point? | the views are items of one kind: `list` |

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
- **Its boundaries:** a list's items have no order, where layers rest one on another and steps follow one another. Items that belong to groups take `groups`.

### `groups`: which items belong together?

- **Form:** groups side by side in one row, each as wide as the others and as tall as the tallest. Each group is a box that holds its items under its head.
- **Source:** Nancy Duarte's cluster (*slide:ology*, chapter 3). Yuri Engelhardt's containment and clustering check it.
- **Options:** none.
- **Lists:** `groups`, each drawn by the block `group`, unless the component field `group` names another. Each group holds a list of its own, its `items`.
- **Its boundaries:** a group's items belong together, where a list's belong to no group. Groups say what belongs together, and a network what is connected to what.

### `network`: what is connected to what?

- **Form:** items in two columns, or three, each column centred on the pattern's height, with a lane between the columns. Ties join any two items, drawn over the columns.
- **Source:** Lohse, Biolsi, Walker and Rueter's network charts. Yuri Engelhardt's linking by a connector checks it.
- **Options:** `columns`, its words `two` and `three`. With `two`, the default, the network draws `left` and `right`. With `three`, it draws `middle` between them.
- **Lists:**
  - `left`, `middle` and `right`, each drawn by the `card`, unless the component field `item` names another;
  - `ties`, a list of ties with the end fields `from` and `to`, each drawn by the `connector`, unless the component field `tie` names another.
- **Ends:** an end names its item by its key path, such as `right[groups].groups[project-management].items[doc-check]` ([Content files](../../files.md#content-files)). So a tie reaches an item that a pattern in a column draws, such as an item of a group.
- **Its boundaries:** ties say what is connected, where groups say only what belongs together. The content sets each item's column and its place there, and no tie moves an item.

### `panels`: which views, side by side, show one point?

- **Form:** panels side by side in one row, each as tall as the tallest. Each panel is any component, a pattern included, such as a network beside a code block. Under the panels, across the whole width, stands the component the content places in `under`, where it places one.
- **Source:** Yuri Engelhardt's lining up, of whole views.
- **Options:** none.
- **Lists:** `panels`, each drawn by the `card`, unless the component field `panel` names another.
- **Arrangement field:** `span`, on each panel, its words `normal` and `wide`. A `normal` panel, the default, takes two shares of the row, and a `wide` one three.
- **Its boundaries:** each panel is a view of its own, where a list's items are items of one kind. Panels set views beside each other, and say nothing of how their items are connected: a network does.

## The blocks

A block draws one item of a pattern, or stands alone where content places it.

### `card`

- **Form:** a box with rounded corners that holds a head, a tag and a text, one under another, each where the content gives it.
- **Fields:** `head`, `tag` and `text`, each optional. `text` is a field of runs, its words `plain` and `strong`, `plain` the default.
- **Options:**
  - `fill`: `plain`, the default, lies on the surface; `tint` lies on its colour family's fill, its texts in the family's text.
  - `bar`: `none`, the default; `top` or `left` draws a bar in the family's line along that side. A top bar moves nothing the card holds, so the heads of a row of cards stand at one height, whichever bar each has.

### `tag`

- **Form:** a short label on a small box with rounded corners, all in its colour family: its fill, its edge and its text. It is as large as its label, on one line.
- **Fields:** `label`, required.
- **Options:** none. Placed alone or in a list, it takes its concept's family. A card's tag stays `neutral`, even on a tinted card.

### `group`

- **Form:** a box with rounded corners on its colour family's fill, edged in the family's line. It holds a head, a tag and its items, one under another, the head and the tag where the content gives them. Its items stand in a column, each as wide as the group.
- **Fields:** `head` and `tag`, each optional, and the list `items`.
- **Lists:** `items`, each drawn by the `card`, unless the component field `item` names another.
- **Options:** none. A group's tag stays `neutral`, as a card's does.

### `code`

- **Form:** code as a terminal or a file shows it, in a monospace type. It lies on a box with rounded corners, on its colour family's fill, under a head where the content gives one. Each line stands as written, never broken, so the block is as wide as its widest line or its head.
- **Fields:** `head`, optional, and `text`, required. `text` is a field of runs, its words `plain`, `prompt`, `command` and `comment`, `plain` the default.
- **Options:** none.

### `aside`

- **Form:** a box with rounded corners on its colour family's fill, with a bar in the family's line along its left side. It holds a head, a command and a text, one under another, each where the content gives it. The command stands in a `code` block, as one plain run.
- **Fields:** `head`, `command` and `text`, each optional.
- **Options:** none. Its code block stays `neutral`, as a card's tag does.

### `connector`

- **Form:** a line from where a tie starts to where it ends, in its colour family's text, with arrowheads where the content asks. It routes around nothing, so a tie best joins items set apart, with nothing between them.
- **Source:** Yuri Engelhardt's linking by a connector.
- **Ends:** it takes the two ends a pattern's list of ties gives it, so a pattern draws it as a tie.
- **Options:**
  - `route`: `straight`, the default, or `corners`.
  - `arrow`, where its arrowheads stand: `end`, the default, `start`, `both` or `none`.

## Colours

Each starter block declares the colour family `neutral`, which the concept an item names replaces with the concept's own. A text in a family's text lies on that family's fill, a pair the foundations declare. On the surface, a card's texts take the shared roles `text-primary` and `text-secondary` instead. So a run of a card's text reads the family only where the card is tinted.

A group, a code block and an aside always lie on their family's fill, so their heads read the family's text. So do an aside's text and a code block's plain runs. A code block's prompts and comments take `text-secondary`, and its commands `accent`, whatever its family.

A connector's line takes its family's text, not its line. Nothing beside the line shows the tie, so it needs a contrast of 3 to 1 against what it lies on (WCAG 2.1, success criterion 1.4.11). A family's line edges a fill, and may be faint: the neutral family's is the shared `line`. A family's text is the member a brand makes legible, since the foundations pair it with the family's fill.

## Shared roles, and the starter's own

A component reads a shared role where the starter means just that role, such as the body's type or the surface. It reads one of its own roles where a brand may want the starter's look apart, such as a card's corners.

- **Colours** are always shared: `surface`, `line`, `text-primary`, `text-secondary`, `accent`, and each family's `fill`, `line` and `text`. The starter declares no colour role, and so no contrast pair.
- **Shared sizes and types:** `type.body` sets a card's plain text, a tag's label and an aside's text. `space.1` and `space.2` lie around a tag's label. `space.2` lies between a block's head, tag, command and text. It is also the least a card keeps between a top bar and what it holds. So a brand's thick bar lowers every card's head alike.
- **Three more shared roles:** `stroke.thick`, `type.strong` and `type.code`, roles of the foundations ([The foundations](../../files.md#the-foundations)). None has a default, so every brand gives each a value (visual-communication DEC-008 point 2).
- **The starter's own roles,** each with a default whose chain ends at a shared role:

| Role | What it sizes or sets | Its default |
|---|---|---|
| `starter.corner` | the radius of a block's corners | `space.1` |
| `starter.inset` | the space between a block's edge and what it holds | `space.3` |
| `starter.gap` | the space between a pattern's items, or a group's | `space.3` |
| `starter.bar` | how thick a card's or an aside's bar is | `space.1` |
| `starter.edge` | how wide a block's edge is | `stroke.thin` |
| `starter.connector` | how wide a connector's line is | `stroke.thick` |
| `starter.type.head` | the type of a block's head and a list's head | `type.heading` |
| `starter.type.strong` | the type of a strong run in a card's text | `type.strong` |
| `starter.type.code` | the type of a code block's text | `type.code` |

A brand that does not name the starter draws it at these defaults, in the brand's own values for the shared roles. A brand that names the starter by its major, 1, may give any of these roles a value of its own (visual-communication DEC-008 point 4).

At the defaults a connector's line is as wide as a line drawn on its own, not as an edge. A strong run keeps the body's size and line height, in a heavier weight, so it stands out without breaking its line. A code block's text is in a monospace type, so the columns of its lines stay in line.

## What the starter leaves out, for now

- **A stepped pyramid,** whose levels narrow towards the top.
- **Notes to the left of the stack.** `layers` places them to the right only.
- **A colour for each place,** such as a tint that deepens down the levels (project-kit#2576).
- **A legend and icons,** so that colour is never the only sign (project-kit#2576).
- **The other patterns and blocks** of the first wave (project-kit#2576).
- **Other arrangement fields.** A panel's `span` is the only one, so no other item chooses its own size or place in its list.
