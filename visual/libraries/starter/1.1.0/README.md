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
        - .pkit/capabilities/visual-communication/design-knowledge/colour.md
        - tests/test_visual_communication_neutral.py
      record:
        - visual-communication:DEC-003#6
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
        - visual-communication:DEC-011#3
        - visual-communication:DEC-012#1
        - visual-communication:DEC-012#2
        - visual-communication:DEC-021#4
        - visual-communication:DEC-022#4
        - visual-communication:DEC-022#5
        - visual-communication:DEC-022#6
        - visual-communication:DEC-025#1
        - visual-communication:DEC-025#4
        - visual-communication:DEC-032#1
        - visual-communication:DEC-032#2
        - visual-communication:DEC-032#3
        - visual-communication:DEC-032#4
        - visual-communication:DEC-032#8
        - visual-communication:DEC-036#2
        - visual-communication:DEC-036#3
        - visual-communication:DEC-036#6
        - visual-communication:DEC-036#8
        - visual-communication:DEC-038#1
        - visual-communication:DEC-038#3
        - visual-communication:DEC-038#6
      artefact:
        - .pkit/capabilities/visual-communication/files.md#the-foundations
        - .pkit/capabilities/visual-communication/files.md#content-files
        - .pkit/capabilities/visual-communication/components.md#breaking-lines
        - .pkit/capabilities/visual-communication/components.md#values-states-and-colour
        - .pkit/capabilities/visual-communication/files.md#the-neutral-brand
        - .pkit/capabilities/visual-communication/checks.md#scenes
---

# The starter

The starter is the component library to start from (visual-communication DEC-007). Its *patterns* arrange items, each for one job a visual does. Its *blocks* draw those items, or stand alone in content. Its *web parts* draw a site's pages, each for one job on a page. The starter holds the forms, and a brand gives them their look.

Bring it into the location beside the foundations:

```
pkit visual add starter
```

A released version of it never changes: a change is a new version (visual-communication DEC-003 point 6). Every component is experimental, so a later version may change it, and a piece that draws one is told so.

## The patterns, by the question they answer

Each pattern answers one question a visual answers. Choose a pattern by its question, not by its look.

| Pattern | Its question | Take another pattern when |
|---|---|---|
| `layers` | What rests on what? As steps, also: what few rest on what many? | the items are of equal standing, in no order: `list` |
| `list` | What are the items? | each item rests on the next: `layers`; the items belong to groups: `groups`; the items say what a piece's colours stand for: `legend` |
| `groups` | Which items belong together? | the items belong to no group: `list`; what matters is what ties them: `network` |
| `network` | What is connected to what? | the items are only grouped: `groups` |
| `panels` | Which views, side by side, show one point? | the views are items of one kind: `list` |
| `legend` | What does each colour and sign stand for? | the items are what the piece shows, not a key to it: `list` |

### `layers`: what rests on what?

- **Form:** levels stacked one on another, the top first, as a stack of one width or as steps that narrow to the top. Each level is shaded by its place, from the order's first end at the top to its last at the foot. Notes may stand to the right of the stack, sharing its height, for what holds across the levels. Ties join a note or a level to another, and end at a level's drawn edge.
- **Source:** Nancy Duarte's structure (*slide:ology*, chapter 3). Lohse, Biolsi, Walker and Rueter's structure diagrams, and Yuri Engelhardt's lining up in an order, check it. Its shades follow Cynthia Brewer's sequential schemes, which show an order by lightness ([*An order's steps*](#an-orders-steps)).
- **Options:**
  - `shape`, its words `stack` and `steps`. With `stack`, the default, each level is as wide as the stack. With `steps`, each level is one step narrower than the one under it, centred on it: the last level is as wide as the stack, and a step is the stack's width over twice the number of levels, so the top stays wider than half the stack. Each level's frame is its step, so a tie into it ends at its edge (visual-communication DEC-038 points 1, 3 and 6). A level takes the width of its step and breaks its text to it (the capability's `components.md`, under *Breaking lines*), so a narrow level that holds more text stands taller than a wide one.
  - `shade`, its words `steps` and `plain`. With `steps`, the default, each level's place takes a step of the order, spread evenly between the two ends the brand gives over the levels drawn, the first end at the top (visual-communication DEC-032 points 3 and 4). With `plain`, a level takes no colour from its place, so each takes its own component's family. Either way, a level that names a concept takes its concept's family, so the levels of a page whose point is an order name none.
- **Lists:**
  - `levels`, each drawn by the `level`, unless the component field `level` names another;
  - `notes`, each drawn by the `card`, unless the component field `note` names another;
  - `ties`, a list of ties with the end fields `from` and `to`, each drawn by the `connector`, unless the component field `tie` names another.
- **Its boundaries:** a level rests on the one below it, where a list's items have no order. Layers say nothing of time, where steps follow one another. As steps, each level also stands narrower than the one it rests on, the few on the many; where the levels are of one breadth, a stack says so. Its shades never show the order alone: each level's place shows it too, and as steps its width.

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
- **Ends:** an end names its item by its key path, such as `right[groups].groups[project-management].items[doc-check]` (visual-communication DEC-011 point 3). So a tie reaches an item that a pattern in a column draws, such as an item of a group.
- **Its boundaries:** ties say what is connected, where groups say only what belongs together. The content sets each item's column and its place there, and no tie moves an item.

### `panels`: which views, side by side, show one point?

- **Form:** panels side by side in one row, each as tall as the tallest. Each panel is any component, a pattern included, such as a network beside a code block. Under the panels, across the whole width, stands the component the content places in `under`, where it places one.
- **Source:** Yuri Engelhardt's lining up, of whole views.
- **Options:** none.
- **Lists:** `panels`, each drawn by the `card`, unless the component field `panel` names another.
- **Arrangement field:** `span`, on each panel, its words `normal` and `wide`. A `normal` panel, the default, takes two shares of the row, and a `wide` one three.
- **Its boundaries:** each panel is a view of its own, where a list's items are items of one kind. Panels set views beside each other, and say nothing of how their items are connected: a network does.

### `legend`: what does each colour and sign stand for?

- **Form:** entries side by side in one row, each as large as it asks. Each entry names a concept, so it shows that concept's colour family and sign, as any item does, beside a label that says what the concept stands for (visual-communication DEC-036 point 6).
- **Source:** the legend of a chart, as Vega-Lite draws one and IBM Carbon's data visualisation guides it: a mark in each colour beside its label. The showcase deck's install slide, whose last line named its colours, is the evidence (project-kit#2843).
- **Options:** none.
- **Lists:** `entries`, each drawn by the `tag`, unless the component field `entry` names another.
- **Its labels are content,** given in each language, as any text is. A notation gives a concept no label, so nothing checks a legend's entries against what the page shows.
- **Its boundaries:** a legend's entries say what the piece's colours and signs stand for, where a list's items are what the piece shows. It places no item of its own.

## The blocks

A block draws one item of a pattern, or stands alone where content places it.

### `card`

- **Form:** a box with rounded corners that holds a head, a tag and a text, one under another, each where the content gives it.
- **Source:** Material Design's card, IBM Carbon's tile and the GOV.UK Design System's summary card.
- **Fields:** `head`, `tag` and `text`, each optional. `text` is a field of runs, its words `plain` and `strong`, `plain` the default.
- **Options:**
  - `fill`: `plain`, the default, lies on the surface; `tint` lies on its colour family's fill, its texts in the family's text.
  - `bar`: `none`, the default; `top` or `left` draws a bar in the family's line along that side. A top bar moves nothing the card holds, so the heads of a row of cards stand at one height, whichever bar each has.

### `level`

- **Form:** one level of an order, such as a level of `layers`: a box with rounded corners on its colour family's fill, which holds a head and a text, one under another, each where the content gives it, both in the family's text. On a step of an order the step is its family, so its fill shows where it stands, and its texts take the order's text.
- **Source:** the levels of Nancy Duarte's pyramid (*slide:ology*, chapter 3), each a band in a shade of one colour, and Material Design's filled card, which its fill alone sets apart from the page.
- **Fields:** `head` and `text`, each optional. `text` is a field of runs, its words `plain` and `strong`, `plain` the default.
- **Options:** none. It is a tinted card kept to what a level holds, so the levels of `layers` show their steps by default. A level that needs a tag or a bar is a `card` with `fill: tint`, which content names in `layers`' field `level`.

### `tag`

- **Form:** a short label on a small box with rounded corners, all in its colour family: its fill, its edge and its text. It is as large as its label, on one line.
- **Source:** the GOV.UK Design System's tag, IBM Carbon's tag and Material Design's chip.
- **Fields:** `label`, required.
- **Options:** none. Placed alone or in a list, it takes its concept's family. A card's tag stays `neutral`, even on a tinted card.

### `group`

- **Form:** a box with rounded corners on its colour family's fill, edged in the family's line. It holds a head, a tag and its items, one under another, the head and the tag where the content gives them. Its items stand in a column, each as wide as the group.
- **Source:** Yuri Engelhardt's containment, which also checks the `groups` pattern.
- **Fields:** `head` and `tag`, each optional, and the list `items`.
- **Lists:** `items`, each drawn by the `card`, unless the component field `item` names another.
- **Options:** none. A group's tag stays `neutral`, as a card's does.

### `code`

- **Form:** code as a terminal or a file shows it, in a monospace type. It lies on a box with rounded corners, on its colour family's fill, under a head where the content gives one. Each line stands as written, never broken, so the block is as wide as its widest line or its head, and its sign ([*Signs*](#signs)).
- **Fields:** `head`, optional, and `text`, required. `text` is a field of runs, its words `plain`, `prompt`, `command` and `comment`, `plain` the default.
- **Options:** none.

### `aside`

- **Form:** a box with rounded corners on its colour family's fill, with a bar in the family's line along its left side. It holds a head, a command and a text, one under another, each where the content gives it. The command stands in a `code` block, as one plain run.
- **Fields:** `head`, `command` and `text`, each optional.
- **Options:** none. Its code block stays `neutral`, as a card's tag does.

### `connector`

- **Form:** a line from where a tie starts to where it ends, in its colour family's text, with arrowheads where the content asks. Its turns are drawn round, so a route with corners reads as one smooth path. It routes around nothing, so a tie best joins items set apart, with nothing between them.
- **Source:** Yuri Engelhardt's linking by a connector.
- **Ends:** it takes the two ends a pattern's list of ties gives it, so a pattern draws it as a tie.
- **Options:**
  - `route`: `straight`, the default, or `corners`.
  - `arrow`, where its arrowheads stand: `end`, the default, `start`, `both` or `none`.

## The web parts, by their job on a page

The web parts draw the pages of a site (visual-communication DEC-022 point 4). Each does one job on a page, a job public design systems share, and cites them. Choose a part by its job.

| Part | Its job on a page | Take another part when |
|---|---|---|
| `header` | Says whose site the page belongs to, and leads to its other pages | the links stand alone, with no title: `navigation` |
| `navigation` | Leads to the site's other pages | the links head every page, beside the site's title: `header` |
| `section` | Says one thing, beside a picture where it has one | the facts fall into rows and columns: `table` |
| `sections` | Lays sections down a page, in their order | the page says one thing: `section` |
| `form` | Takes a reader's answer | the reader answers nothing: `section` or `table` |
| `table` | Shows facts in rows and columns, on a page or, with no inset of its own, on a slide | each fact needs a sentence of its own: `section`; on a slide, the items share no columns of facts: `list` |

Each web part fits every size the brand gives: a desktop, a tablet, a phone and a projector. Its widths come from the width it gets, never from a number of its own. Where a size leaves it too little room, it changes its shape at that size. A row whose items ask for more than it gets is reported at that size (visual-communication DEC-022 point 5).

- **Their inset.** A part placed in a page's header, main part or footer is as wide as the page. `header`, `section`, `form` and `table` each set their own inset, so a tinted part's fill reaches the page's edge. A table whose `inset` is `none` sets none, as on a slide ([`table`](#table)). The inset is `starter.margin` on a desktop and a tablet, and `starter.inset` on a phone. `navigation` keeps the same inset at either side alone, since a header places it. `sections` sets none, since each section sets its own.
- **The length of a line.** The text of a section, the head and the fields of a form, and a table's head run no longer than `size.line`, which the capability's `files.md` describes under *The foundations*.
- **At rest.** A part is drawn as a page stands before anyone uses it. A form is never sent and a link never followed, and no part shows a hover, a focus or a press (visual-communication DEC-022 point 6).

### `header`

- **Form:** a band across the top of the page, with a rule along its foot. On a desktop the brand's logo, the site's title and its navigation stand in one row, the navigation at the row's end. On a tablet and a phone the navigation moves under the title, and the title takes the whole row.
- **Source:** the GOV.UK Design System's header and its service navigation, and the U.S. Web Design System's header.
- **Fields:** `title`, required, the site's name. `links`, optional, the links of its navigation, each with the fields of the `link`.
- **Options:** `fill`: `plain`, the default, lies on the page's background; `tint` lies on its colour family's fill, its title in the family's text.
- **Its logo** is the picture the brand gives `picture.logo`, no wider than `starter.logo`. Under a brand that gives none, the header draws no logo, and its title starts at the inset.
- **On a desktop** the title stands on one line, so a long title belongs in a section, not the header.

### `navigation`

- **Form:** links in a row on a desktop and a tablet, each as wide as its label, at the row's start or at its end. On a phone the links stand one under another.
- **Source:** the GOV.UK Design System's service navigation.
- **Options:** `align`, its words `start`, the default, and `end`, where the links of a row stand. A column on a phone always starts at the start.
- **Lists:** `links`, each drawn by the `link`, unless the component field `link` names another.
- **Too many links.** Links that ask for more than the row's width are reported at that size. Fewer links, or shorter labels, mend it.

### `section`

- **Form:** a head and a text beside a picture, on the page's background or on its family's fill. On a desktop the words and the picture stand side by side, the picture taking the width the text leaves. On a tablet and a phone the picture stands under the text, across the whole width.
- **Source:** the U.S. Web Design System's media block, a picture beside a text.
- **Fields:** `head`, `text` and `picture`, each optional. `picture` names a picture file of the piece, by its bare name, such as `screen.png`. A section that names none draws its words alone, at the start.
- **Options:**
  - `fill`: `plain`, the default, or `tint`, as a header's.
  - `side`: `right`, the default, stands the picture to the right of the text on a desktop; `left` stands it to the left.

### `sections`

- **Form:** sections one under another, in their order, each across the page's whole width. Each more section makes the page taller.
- **Source:** the U.S. Web Design System's landing page template, whose sections stand one under another.
- **Options:** none.
- **Lists:** `sections`, each drawn by the `section`, unless the component field `section` names another.

### `form`

- **Form:** a head, its fields one under another, and its buttons under them. The buttons stand in a row on a desktop and a tablet, and one under another on a phone. A form holds no action: each field shows the text its content gives it.
- **Source:** the GOV.UK Design System's question pages, its text input and its button group.
- **Fields:** `head`, optional.
- **Options:** none.
- **Lists:**
  - `fields`, each drawn by the `field`, unless the component field `field` names another;
  - `buttons`, each drawn by the `button`, unless the component field `button` names another. The first button is the one that sends the form.

### `table`

- **Form:** a head, then its rows, one under another, each across the table's width. Each row's cells share its width, and their text breaks to the cell's width, so a row is as tall as its tallest cell. A row more makes the table taller.
- **Source:** the GOV.UK Design System's table, and the U.S. Web Design System's table.
- **Fields:** `head`, optional.
- **Options:** `inset`, its words `own` and `none`. With `own`, the default, the table sets its own inset, as [*Their inset*](#the-web-parts-by-their-job-on-a-page) says. With `none`, it sets none, so its head and its rows reach the edges of the width it gets. On a slide, whose layout keeps the margin, its first column then starts on the slide's margin.
- **Lists:** `rows`, each drawn by the `row`, unless the component field `row` names another.
- **Its columns.** A row cannot read the table's columns, so each row gives its cells the same spans, and the columns line up. A table keeps its columns on a phone, so a word in a narrow column must fit a phone's width.

## The web blocks

A web block draws one item of a web part's list.

### `link`

- **Form:** a label in the accent colour, on one line, as wide as the label.
- **Source:** the GOV.UK Design System's links.
- **Fields:** `label`, required.
- **Options:** none.

### `button`

- **Form:** a label on a box with rounded corners, all in its colour family: its fill, its edge and its label. It is as large as its label, on one line.
- **Source:** the GOV.UK Design System's button, and Material Design's filled tonal button, which lays a family's text on the family's fill.
- **Fields:** `label`, required.
- **Options:** none. Its family is `blue`.
- **States:** `disabled`, a button that cannot be pressed, takes the `neutral` family. It loses its colour, but its label stays as strong as any button's.

### `field`

- **Form:** a label, a box that holds the text the content gives the field, and a note under the box where the content gives one. The box is edged in its family's text, so it stands out against the page.
- **Source:** the GOV.UK Design System's text input, its hint and its error message. Material Design's text field, whose leading icon stands inside the box, gives its sign's place.
- **Fields:** `label`, required, `value`, the text the field shows, and `note`, such as a hint or what is wrong.
- **Options:** none. Its family is `neutral`.
- **States:** `error`, a field whose text is wrong, takes the `red` family, its box and its text.

### `row`

- **Form:** cells side by side, sharing the row's width, and a rule along its foot.
- **Source:** the rows of the GOV.UK Design System's table and of the U.S. Web Design System's table, as for the `table`.
- **Lists:** `cells`, each drawn by the `cell`, unless the component field `cell` names another.
- **Arrangement field:** `span`, on each cell, its words `normal`, `narrow` and `wide`. A `normal` cell, the default, takes two shares of the row, a `narrow` one one, and a `wide` one three.
- **Options:** none.

### `cell`

- **Form:** a head in a strong type, a text, or both, one under the other, each broken to the cell's width.
- **Source:** the cells of the GOV.UK Design System's table and of the U.S. Web Design System's table, as for the `table`.
- **Fields:** `head` and `text`, each optional. A first row of heads names the table's columns.
- **Options:** none.

## Colours

Each component's file declares its own colour family, or none. An item that names a concept takes the concept's family instead, and an item whose place in its list takes a family or a step of an order takes that before its component's. A state may then change it (visual-communication DEC-010 point 6).

- **`neutral`:** the blocks `card`, `level`, `tag`, `group`, `code`, `aside` and `connector`, the web parts `header` and `section`, and the web block [`field`](#field). A field in `error` takes `red`.
- **`blue`:** the web block [`button`](#button). A `disabled` button takes `neutral`.
- **None:** the patterns, the web parts `navigation`, `sections`, `form` and `table`, and the web blocks `link`, `row` and `cell`. None of them takes a colour from a family.

A text in a family's text lies on that family's fill, whose contrast the capability's `files.md` describes under *The foundations*. On the surface, a card's texts take the shared roles `text-primary` and `text-secondary` instead. So a run of a card's text reads the family only where the card is tinted.

A level, a group, a code block and an aside always lie on their family's fill, so their heads read the family's text. So do a level's and an aside's text and a code block's plain runs. A code block's prompts and comments take `text-secondary`, and its commands `accent`, whatever its family.

A header and a section lie on the page's `background`, or on their family's fill where tinted. A link takes `accent`, and a field's note `text-secondary`. A button and a field's box lie on their family's fill, and their text reads the family's text.

A connector's line takes its family's text, not its line. Nothing beside the line shows the tie, so it needs a contrast of 3 to 1 against what it lies on (WCAG 2.1, success criterion 1.4.11). A family's line edges a fill, and may be faint: the neutral family's is the shared `line`. A family's text is the member a brand makes legible, since the foundations pair it with the family's fill.

## An order's steps

`layers` gives each of its levels a step of an order by default, and is the starter's only pattern whose point is an order (visual-communication DEC-032 point 3). A brand gives the order two ends in each of its modes, the first the furthest from the page, and the engine spreads them evenly over the levels drawn, in lightness, as Cynthia Brewer's sequential schemes show an order. A brand that gives no ends draws every step as the neutral family's fill, so every level alike. A step paints as a family: a part painted from its family's fill or line takes the step's colour, and a part painted from its family's text takes the order's text, which the brand keeps legible on both ends (the capability's `files.md`, under *The foundations*).

- **What does not show a step.** A part painted from its family's line over its own fill takes the fill's colour there, so a tinted card's and a level's edge, a card's bar on a tinted card, and an aside's bar do not show it. A card with `fill: plain` lies on the surface, so only its bars show it. A component that declares its own family keeps it inside a level, as on any family's fill: a card's or a group's tag, a group's items, and an aside's code block.
- **What may fail on one.** A step may lie far in lightness from every family's fill, so a part that keeps its contrast on every family may fall below it on a step, measured as drawn (the capability's `components.md`, under *Values, states and colour*). The starter's owner audited each component that paints from its family on the steps, for the two kinds of part that may fail:
  - **A part painted with a shared role over the step.** A code block's prompts and comments, in `text-secondary`, and its commands, in `accent`, and a tinted header's links, in `accent`. Under the neutral brand (the capability's `files.md`, under *The neutral brand*) each falls below its contrast, so a code block or a tinted header drawn as a level fails there.
  - **A part painted with the order's text over a fill outside its family,** such as a card's text on the surface. None of the starter's components draws one on a step: a plain card's texts take shared roles, and the parts that paint their family's text off its fill, a sign and a field's edge, are drawn on a step only within the step's own fill, or, for a sign, only for a concept, which a step never names.
- **The default passes.** The `level`, which draws the levels, and a `card` with `fill: tint`, a `tag`, a `group`, an `aside`, a `button`, a `field` and a `section` with `fill: tint` paint each text and sign that lies on the step itself in the order's text, which the neutral brand keeps legible on every step. The check finds what falls below its contrast where it is drawn, as for any family (the capability's `checks.md`, `contrast-drawn`).

## Signs

A concept that a piece shows by its colour shows a sign beside it too, so colour is never the only thing that tells it apart (visual-communication DEC-036 point 2). Each component that paints a part from its colour family draws, in a part of its own, the sign of the concept whose family it takes. Where its family comes from no concept, or the concept maps no sign, that part is not drawn, and has no size.

| Component | Where its sign stands |
|---|---|
| `card`, `level`, `group`, `code`, `aside` | at the end of the head's row, centred on the row, so the heads of a row of blocks stand at one place across, whichever draws a sign |
| `card`, `level`, `code`, `aside` with no head | at the end of the first row of what the block holds, which leaves room for it, so the block grows no taller for its sign |
| `group` with no head | alone in the head's row, and the items start under it |
| `tag`, `button` | before the label |
| `field` | in the box, before the text |
| `header` | before the title |
| `section` | before the head |
| `connector` | on the line, halfway along it |

- **Its size** is the starter's own role `starter.sign`, the side of a square the sign fills whole. A web part's or a web block's sign is no wider than the room it gets: a header's than the room inside its insets, a section's than its text, a field's than the field, and a button's than its label.
- **Its paint** is its family's text, the member a brand makes legible, since a sign, as a connector's line, needs a contrast of 3 to 1 against what it lies on (visual-communication DEC-036 point 8). A state changes its paint, never its sign.
- **The gap** between a sign and the text after it, in a tag, a button, a field, a header and a section, is the shared role `space.sign-gap`, the gap a run's sign keeps. Between a block's sign and what stands before it, the gap is `space.2`.
- **A run's sign.** A run of a card's or a level's text, or a plain run of a code block's text, that names a concept with a sign starts with that sign, in the run's paint (visual-communication DEC-036 point 3). A code block's prompts, commands and comments take shared roles, not a family, and draw no sign.
- **A legend** says in words what each sign and colour stands for ([`legend`](#legend-what-does-each-colour-and-sign-stand-for)).

## Shared roles, and the starter's own

A component reads a shared role where the starter means just that role, such as the body's type or the surface. It reads one of its own roles where a brand may want the starter's look apart, such as a card's corners.

- **Colours** are always shared: `surface`, `line`, `text-primary`, `text-secondary`, `accent`, and each family's `fill`, `line` and `text`. The starter declares no colour role, and so no contrast pair.
- **Shared sizes and types:** `type.body` sets a card's and a level's plain text, a tag's label and an aside's text. `space.1` and `space.2` lie around a tag's label. `space.2` lies between a block's head, tag, command and text, and before the sign at the end of its first row. It is also the least a card keeps between a top bar and what it holds. So a brand's thick bar lowers every card's head alike.
- **For the web parts:** `type.strong` sets a button's and a field's label. They also read `size.line` and `picture.logo`, which [*The length of a line*](#the-web-parts-by-their-job-on-a-page) and [`header`](#header) describe.
- **Three more shared roles:** `stroke.thick`, `type.strong` and `type.code`, roles of the foundations (the capability's `files.md`, under *The foundations*). None has a default, so every brand gives each a value (visual-communication DEC-008 point 2).
- **The starter's own roles,** each with a default whose chain ends at a shared role:

| Role | What it sizes or sets | Its default |
|---|---|---|
| `starter.corner` | the radius of a block's corners | `space.1` |
| `starter.button.corner` | the radius of a button's corners | `starter.corner` |
| `starter.inset` | the space between a block's edge and what it holds | `space.3` |
| `starter.gap` | the space between a pattern's items, or a group's | `space.3` |
| `starter.margin` | the wider spaces within a web part, and its inset where [*Their inset*](#the-web-parts-by-their-job-on-a-page) says | `space.4` |
| `starter.logo` | the width of a header's logo, as [`header`](#header) says | `space.4` |
| `starter.bar` | how thick a card's or an aside's bar is | `space.1` |
| `starter.edge` | how wide a block's edge is | `stroke.thin` |
| `starter.connector` | how wide a connector's line is | `stroke.thick` |
| `starter.turn` | the radius a connector's turns are drawn round at | `space.2` |
| `starter.type.head` | the type of a block's head and a list's head | `type.heading` |
| `starter.type.strong` | the type of a strong run in a card's or a level's text | `type.strong` |
| `starter.type.code` | the type of a code block's text | `type.code` |
| `starter.sign` | the side of the square a component draws its concept's sign in, as [*Signs*](#signs) says | `space.3` |

A brand that does not name the starter draws it at these defaults, in the brand's own values for the shared roles. A brand that names the starter by its major, 1, may give any of these roles a value of its own (visual-communication DEC-008 point 4).

At the defaults a connector's line is as wide as a line drawn on its own, not as an edge. A strong run keeps the body's size and line height, in a heavier weight, so it stands out without breaking its line. A code block's text is in a monospace type, so the columns of its lines stay in line.

## What the starter leaves out, for now

- **Notes to the left of the stack.** `layers` places them to the right only.
- **A colour family for each place** of a list (project-kit#3129). An order's levels take its steps instead ([*An order's steps*](#an-orders-steps)).
- **A legend in a column,** or one the engine fills from the concepts a page names. A legend's entries stand in one row, and content lists each (visual-communication DEC-036 point 6).
- **The other patterns and blocks** of the starter's second wave (project-kit#3129).
- **Other arrangement fields.** A panel's `span` and a cell's are the only ones, so no other item chooses its own size or place in its list.
- **A menu that folds the links away.** On a phone a header lists its links under its title, where a design system shows a menu button.
- **A table that scrolls across,** or stacks its cells on a phone. A table keeps its columns at every size.
- **A muted button, and an error message in red.** A state changes only a part's colour family, and a family's text lies on its own fill. So a button that cannot be pressed keeps its label's strength, and a field's note stays in `text-secondary`.
