# Starting a piece

A piece is a folder under the location's `pieces/`. It holds `piece.yaml`, which says what the piece is, and a content file for each language, which says what it shows ([A piece](../../files.md#a-piece)). It may keep a brief too, which says what the piece must show and why its design is as it is ([The brief](../../files.md#the-brief)). You bring its libraries first, write its files by hand, and let the first render write the lock.

## 1. Bring the libraries

`pkit visual add <library>` copies a library the capability ships into the location's library folder, and lists it in `libraries/libraries.yaml`. A piece reads a library from that folder alone, so bring each one it needs.

| Library | Bring it when |
|---|---|
| `foundations` | Always, first. Every piece's lock names it, and it holds the tops. |
| `neutral` | The piece needs a brand, and the library folder holds none. |
| `starter` | The content will draw a pattern or a block of the starter. |

```
pkit visual add foundations
pkit visual add neutral
pkit visual add starter
```

- **The location.** The first command that writes records the location in the capability's configuration. With none recorded, it takes `visual/` at the repository's top.
- **Another folder.** `--location <path>` names it, on that first command. Once a location is recorded, a command refuses a `--location` that names another folder ([How a command finds it](../../files.md#how-a-command-finds-it)).
- **A folder in the way.** Where `visual/` already holds other files, the command refuses and names it. Name another folder.

A copy is the project's file, and you never edit it ([What the location holds](../../files.md#what-the-location-holds)).

## 2. Choose what the piece is

Name the piece first. Its name takes the name shape, such as `first-talk`, and its folder is `pieces/<piece>/` ([Shapes](../../files.md#shapes)).

Then choose each field of `piece.yaml`:

| Field | How to choose |
|---|---|
| `top` | `foundations/deck` for a presentation, one page for each slide. `foundations/figure` for a figure in a documentation page, one page alone. `foundations/site` for a web page, or a portal of several pages. |
| `brand` | `neutral`, or a brand the library folder already holds. A brand gives every value the piece draws in. |
| `notations` | Leave it out unless the content names concepts. No notation ships, so name only one the library folder holds ([Notations](../../files.md#notations)). |
| `languages` | The first is the source language, such as `[en]`. Each language needs its content file. |
| `audience` | Who the piece is for, in one sentence. Name the reader and what they already know, since the build loop reads the pages as that reader does. |
| `shown` | Where the piece is shown, in words: the place and the medium. |
| `explains` | `true` where the piece explains, rather than only shows. A figure of how parts relate explains. A title page only shows. |
| `exports` | The formats an export makes. `pdf` makes one file for each language and combination of modes, which suits a presentation. `svg` makes one file for each page, which suits a figure. `html` makes a page file a browser opens, which suits a web page. `[]` makes none yet. |
| `state` | `draft`. A draft's lock moves at each render. |
| `modes` | Leave it out to draw each axis in its default. Name an axis to draw more, such as `colour-scheme: [light, dark]` ([Axes and modes](../../files.md#axes-and-modes)). A web page names the sizes it is shown at, such as `device: [desktop, tablet, phone]`, and the brand gives each size. Each combination adds a drawing to read, so name only what the piece is shown in. |

**A web page** is a site of one page, and a portal is a site of several. Its content holds its pages under `pages`, each naming the layout `standard` and filling its slot `main`. The site's `header` and `footer` are optional. Each is written once, and every page takes it. Each page is as wide as its size, and as tall as its content. The site and the axis `device` come with the foundations' version 1.1.0 ([The foundations](../../files.md#the-foundations)).

Write no `lock`: the first render writes it. Write no `pinned` either, since a pinned draft with no lock is refused.

## 3. Write `piece.yaml`

Write `pieces/<piece>/piece.yaml`. Its first two fields are the binding, which every file of the capability's format carries ([The binding](../../files.md#the-binding)). For the piece `first-talk`:

```yaml
pkit_schema: visual-communication:piece
schema_version: 1
top: foundations/deck
brand: neutral
languages: [en]
audience: New members of the team, who have not seen the project yet.
shown: On a screen, at the team's weekly meeting.
explains: true
exports: [pdf]
state: draft
modes:
  colour-scheme: [light, dark]
```

## 4. Write the brief

The brief, `pieces/<piece>/brief.yaml`, is written for whoever makes or reviews the piece, and no reader sees it ([The brief](../../files.md#the-brief)). It keeps what the content does not: what each picture must make visible, and why the design is as it is. So a reviewer can fail a page that loses the point, and a later designer can change one choice without breaking another.

- **When to keep one.** Keep one for a piece that explains, or whose pictures carry an order, a flow or a grouping a reader must see. A quick figure needs none. Nothing that draws or checks a piece needs one.
- **The intent first, from whoever asks.** Before you design, write the `goals` and the `relations` from what whoever asked for the piece says, and show them to that person. A relation says in words what a picture must make visible between its parts, such as levels that each rest on the one below. A goal says what the audience must be able to do after the piece.
- **A part for each page.** `piece` holds what concerns the whole piece, and `pages` a part for each page, keyed by the page's id in the content. A page's part names a page the content holds. Until you start a page in step 5, write its intent under `piece`, and move it under `pages` once the page has its id. A figure keeps all of its brief under `piece`.
- **A takeaway only where the page has no lead.** Where the page's content states its point, such as a slide's `lead`, that is its takeaway, and the brief does not repeat it. A cover often has none.
- **The reasons as you design.** Write each reason as you make the choice it explains, in step 5 and in the build loop. List them in the order the choices are made: `structure`, `form`, `hierarchy`, `type`, `colour`, `space`. Each names the principle it rests on, by its name and its source. A reason with no principle is taste, which nobody can judge.
- **Words, ids and key paths alone.** A key path names a part of the content as a tie's end does, by the keys and ids that lead to it, each item of a list by its id: from the page in a page's part, as `lead`, and from the content's top in the piece's part, as `slides[parts].visual.items[brand]`. Write no value, no layout and no text the content shows. A brand's values and a component's look are theirs, and a requirement for more than this piece is a rule.
- **Its binding,** `pkit_schema: visual-communication:brief` and `schema_version: 1`, opens it, as every file of the capability's format.

The brief of the deck in step 5, once its pages hold their ids:

```yaml
pkit_schema: visual-communication:brief
schema_version: 1
piece:
  goals:
    - A new member of the team can name the three parts of a piece, and what each is for.
pages:
  parts:
    relations:
      - text: The three parts are kinds of one thing side by side, none ranked above the others.
        relates: [visual.items]
    reasons:
      - aspect: structure
        about: visual.items
        text: The parts are three kinds of one thing, with no order among them.
        principle:
          name: Categorical and ordered attributes
          source: Tamara Munzner, Visualization Analysis and Design
      - aspect: form
        about: visual.items
        text: Items of one size and one colour, so that no part reads as more than another.
        principle:
          name: Ordered visual variables
          source: Jacques Bertin, Semiology of Graphics
```

The slide `parts` states its point in its `lead`, so its part holds no takeaway.

No command writes the brief, and nothing that draws the piece reads it. The check fails a page or a key path it names that the content does not hold: an id you renamed in the content leaves it naming what is gone ([The brief](../../checks.md#the-brief)).

## 5. Write the content

Write `pieces/<piece>/content.<language>.yaml` for each language. The content says what the piece shows, and names no position, size, colour or font ([Content files](../../files.md#content-files)).

- **What it may hold.** Open the top's file in the location, under `libraries/foundations/<version>/components/`. A figure takes the fields `body` and `caption`. A deck takes `slides`, and a site takes `pages`. Each slide or page names a `layout`, whose `slots` are what it may fill, or the component that draws it, with `use`.
- **What draws a visual.** A mapping with `use` places a component. Choose a pattern by the question the visual answers, never by its look ([The patterns, by the question they answer](../../libraries/starter/README.md#the-patterns-by-the-question-they-answer)). Its page says which fields and options it takes.
- **Ids.** Give each slide and each item an `id`, unique in its list. A second language is a second file of the same shape, with the same ids.
- **Concepts.** Where the piece names a notation, `concept: <notation>/<concept>` gives a component its colour family.
- **A picture of the piece's own,** such as a photo, is a PNG or a JPEG in `pieces/<piece>/pictures/`. In each language, the field of the image that shows it gives the file's bare name, with no folder before it ([Picture files](../../files.md#picture-files)).

The content of a deck, one cover and one slide:

```yaml
pkit_schema: visual-communication:content
schema_version: 1
slides:
  - id: cover
    layout: cover
    title: How a piece is built
    subtitle: Three parts, and what each is for
  - id: parts
    layout: slide
    title: A piece has three parts
    lead: Each part does one job, and none depends on the others' look.
    visual:
      use: starter/list
      items:
        - id: content
          head: Content
          text: What the piece says.
        - id: components
          head: Components
          text: How the piece is arranged.
        - id: brand
          head: Brand
          text: How the piece looks.
```

The same list as a figure, with `top: foundations/figure` and `exports: [svg]` in `piece.yaml`:

```yaml
pkit_schema: visual-communication:content
schema_version: 1
body:
  use: starter/list
  items:
    - id: content
      head: Content
      text: What the piece says.
    - id: brand
      head: Brand
      text: How the piece looks.
caption: Two of the parts of a piece.
```

Where no library component fits, write the rest first, then write a local component ([A local component](build-loop.md#a-local-component)).

## 6. Draw it once

`pkit visual render <piece>` draws the piece. For a piece with no lock yet, it also writes the lock.

- **What it writes.** It takes the newest version the location holds of each library the piece uses, and of each library those build on. It adds them to `piece.yaml` as a `lock:` block, and keeps every other byte of the file ([The lock](../../files.md#the-lock)).
- **Before this render,** the check reports `lock-missing`, and `pkit visual look` and `pkit visual pages` refuse.
- **Where it refuses,** its message names what to mend:

| It says | Do |
|---|---|
| The project holds no version of a library | Run `pkit visual add <library>`, or name a library the project holds. |
| A content file does not exist | Write it, or take the language out of `languages`. |
| A value is not a mode of an axis | Name a mode the axis has. |
| A file names no schema | Write the binding at its top. |
| No font family measures a character | Take the character out of the content. |

Then go on to `build-loop.md`.
