---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-adapter, name: adapter}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-component, name: component}
      - {id: TERM-data-point, name: data point}
      - {id: TERM-documentation-root, name: documentation root}
      - {id: TERM-install, name: install}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-system, name: system}
      - {id: TERM-version, name: version}
      - {id: TERM-version-pin, name: version pin}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.
          - Put a figure in a documentation page that follows the page's light or dark mode, and stays current as the page changes.
          - Draw several views of one system from one model, so each fact is written once and every view shows it the same way.
          - Add a new kind of visual to a piece as data, without code, where no library component fits.
          - Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.
          - Give a piece another brand or another mode, and see its look change while its content stays the same.
          - Draw a piece through another renderer, such as a web page instead of a board, and learn what that renderer could not draw.
          - Take what people changed where my piece is drawn, such as on a board, back into its content when I ask.
          - Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.
          - Hand out a piece as a PDF, one for each language, with the piece's pages in order, such as its slides.
          - Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.
          - Add a kind of piece that the capability does not ship, such as a poster, without changing the capability.
          - Make a brand for a look, with its values in each mode of the axes it needs, such as a colour scheme or a device.
          - Build a brand on another brand, changing only what that brand lets me change, and give my brand its own library versions.
          - Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.
          - Take in a library that another project shares, by its link, and take in its newer library versions when I choose.
          - Add a library component to a library my project owns, and mark it stable once I judge that pieces can rely on it.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Have another capability's diagrams drawn in my libraries' look, the rest drawn that capability's own way, and see how much my libraries cover.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-operator
        name: Operator
TERM-axis:
  name: axis
  status: active
  definition: "switch of a brand along which its modes lie, such as its colour scheme or the device a piece is shown on"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-004#2
TERM-brand:
  name: brand
  status: active
  definition: "library that holds the values pieces are drawn in, such as their colours, fonts and sizes"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#5
          - visual-communication:DEC-004#1
TERM-content:
  name: content
  status: active
  definition: "what a piece shows, such as its titles, texts and lists, kept as data apart from how the piece looks"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#3
TERM-content-slot:
  name: content slot
  status: active
  definition: "named place in a layout, a library component or a local component that a piece fills with what it shows, such as a slide's title"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#4
TERM-draft:
  name: draft
  status: active
  definition: "still being made, its lock moving at each drawing to the newest library versions present within its major numbers, unless a person pinned it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#8
TERM-experimental:
  name: experimental
  status: active
  definition: "in its library and not yet marked ready by its library owner, so that any later library version may rename, reshape or remove it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#7
TERM-export:
  name: export
  status: active
  definition: "file a piece is handed out as, such as a PDF of one language, numbered by the run that made it, never overwritten"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-006#7
TERM-final:
  name: final
  status: active
  definition: "handed out and marked so by a person, with a lock that never moves again and the exports handed out kept as they were"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#8
TERM-helper-script:
  name: helper script
  status: active
  definition: "project's own program, run while a piece is prepared and never while it is drawn, that writes a local component or a picture for it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#8
          - visual-communication:DEC-006#1
TERM-layout:
  name: layout
  status: active
  definition: "named arrangement of a page that a kind of piece declares, such as a presentation's cover or slide, and that a brand draws"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#4
TERM-library:
  name: library
  status: active
  definition: "shared set that pieces take their look from, of one of three kinds: parts that arrange and draw content, a brand, or a notation"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#5
TERM-library-component:
  name: library component
  status: active
  definition: "reusable part that arranges and draws the content it is given, from a small block to a whole page, shared by pieces"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#4
TERM-library-owner:
  name: library owner
  status: active
  definition: "project that keeps a brand, a notation or another shared set pieces take their look from, numbers its states and marks its parts ready"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#5
          - visual-communication:DEC-003#7
TERM-library-version:
  name: library version
  status: active
  definition: "numbered state, such as 2.1.0, of a brand, a notation or a shared set of parts, kept whole and never changed once released"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#1
          - visual-communication:DEC-003#6
TERM-local-component:
  name: local component
  status: active
  definition: "part that arranges and draws the content it is given, made inside one piece and used by that piece alone"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#4
TERM-lock:
  name: lock
  status: active
  definition: "list kept with a piece of the library version it is drawn with, one for each library it uses, those they build on included"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#7
TERM-mode:
  name: mode
  status: active
  definition: "one setting on one axis of a brand, such as dark on its colour scheme, with the values that differ in it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-004#2
TERM-model:
  name: model
  status: active
  definition: "file of a subject's elements, such as a project's parts, and the relations between them, written once for several pieces to draw from"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#3
          - visual-communication:DEC-006#1
TERM-notation:
  name: notation
  status: active
  definition: "library that says what each thing of a subject is, and how every piece marks it, such as by a colour family or an icon"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#5
          - visual-communication:DEC-004#10
TERM-option:
  name: option
  status: active
  definition: "choice that a library component declares, such as a card's tone, made where a piece uses it from the values the library component lists"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#6
TERM-piece:
  name: piece
  status: active
  definition: "visual item, such as a presentation or a documentation page's figure, that keeps its content as data and takes its look from libraries"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#3
TERM-pinned:
  name: pinned
  status: active
  definition: "held in place, said of a draft's lock, so that it moves only when a person moves it, never each time the piece is drawn"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#8
TERM-published:
  name: published
  status: active
  definition: "in use where others rely on it, with a lock that moves only through a reviewed change showing the piece before and after"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#8
TERM-renderer:
  name: renderer
  status: active
  definition: "part of the system that draws a piece in one medium, such as an SVG picture, a web page, a PDF or an online board"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-001#2
TERM-stable:
  name: stable
  status: active
  definition: "marked ready by its library owner, so that only a library version with a new major number may break it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-003#7
TERM-starter-library:
  name: starter library
  status: active
  definition: "set of shared parts that arrange and draw content, which visual-communication gives every project for jobs most pieces have, such as showing layers or steps"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
        record:
          - visual-communication:DEC-007#1
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`.
  - **Term:** [adapter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-adapter--adapter)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [component](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-component--component)
  - **Term:** [data point](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-data-point--data-point)
  - **Term:** [documentation root](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-documentation-root--documentation-root)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Term:** [version](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-version--version)
  - **Term:** [version pin](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-version-pin--version-pin)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.
    - Put a figure in a documentation page that follows the page's light or dark mode, and stays current as the page changes.
    - Draw several views of one system from one model, so each fact is written once and every view shows it the same way.
    - Add a new kind of visual to a piece as data, without code, where no library component fits.
    - Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.
    - Give a piece another brand or another mode, and see its look change while its content stays the same.
    - Draw a piece through another renderer, such as a web page instead of a board, and learn what that renderer could not draw.
    - Take what people changed where my piece is drawn, such as on a board, back into its content when I ask.
    - Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.
    - Hand out a piece as a PDF, one for each language, with the piece's pages in order, such as its slides.
    - Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.
    - Add a kind of piece that the capability does not ship, such as a poster, without changing the capability.
    - Make a brand for a look, with its values in each mode of the axes it needs, such as a colour scheme or a device.
    - Build a brand on another brand, changing only what that brand lets me change, and give my brand its own library versions.
    - Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.
    - Take in a library that another project shares, by its link, and take in its newer library versions when I choose.
    - Add a library component to a library my project owns, and mark it stable once I judge that pieces can rely on it.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Have another capability's diagrams drawn in my libraries' look, the rest drawn that capability's own way, and see how much my libraries cover.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [Operator](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-operator.md)

## TERM-axis — axis

**Example:** A game platform's brand has four axes: a colour scheme, a device, an audience and a contrast. Light and dark are the modes of its colour scheme.

**Distinctions:**

- **Colours or sizes:** the modes of one axis alter only values that move nothing on the page, such as the colours and pictures of a colour scheme. The modes of another may alter any value, sizes and spacing among them, such as those of a device. A piece is laid out again only for the second kind.

## TERM-brand — brand

**Example:** A talk about the project is drawn in its company's brand. Drawn in a client's brand, the same talk looks different, and its content stays the same.

**Distinctions:**

- **Theme:** a set of values alone. A brand also holds the layouts it draws each kind of page in, and parts that only it uses.
- **Mode:** one setting on one axis of a brand, such as dark on its colour scheme. A brand holds its values in each of its modes.

## TERM-content — content

**Example:** A slide's title and its lead are content, and so are the levels that a pyramid of layers shows.

**Distinctions:**

- **Layout:** where content goes and how it looks, which libraries give. Content holds none of it.

## TERM-content-slot — content slot

**Example:** A slide's layout has a content slot for its title and one for its picture. The slide's content gives the title, and a library component it names fills the picture.

**Distinctions:**

- **Data point:** the core's place where a component takes what other components contribute, which the core once called a slot ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md)). The analysis never says slot alone, so the two never share a word.
- **Placeholder:** PowerPoint's word for a layout's content slot, which a reader may also take for mock text.

## TERM-draft — draft

**Example:** A talk being written for next month is a draft. Each time it is drawn, it takes the newest library versions the project holds, within the major numbers its lock names.

**Distinctions:**

- **Pinned:** said of a draft's lock that a person pinned. The piece is still a draft, and its lock moves only when a person moves it.
- **Published:** said of a piece whose lock moves only through a change that shows it before and after.

## TERM-experimental — experimental

**Example:** A new timeline enters the starter library experimental. A piece that uses it is drawn, with a note that it may still change.

**Distinctions:**

- **Proposed:** a proposed record or rule binds nothing. A piece still uses an experimental library component, and is only told that it may change.

## TERM-export — export

**Example:** After a talk, its third export run made a PDF in English and one in Czech, both numbered 3.

**Distinctions:**

- **What a renderer drew:** a board or a page changes each time the piece is drawn again. An export stays as it was made, and its PDF is written from the piece, never from a board.

## TERM-final — final

**Example:** A talk is marked final once it was given, with the PDFs that were handed out. No later library version changes its look, and those PDFs stay as they were.

**Distinctions:**

- **Pinned:** said of the lock of a final piece's copy, taken up again for a new audience. The copy is a draft, and its lock moves when a person moves it. The final piece stays as it was.
- **Published:** said of a piece that stays in use, whose lock moves through a change a person reviews. A final piece's lock never moves.

## TERM-helper-script — helper script

**Example:** Items set around a circle need what data cannot say. A helper script places them, and writes their places as data, with every text taken from the content.

**Distinctions:**

- **Renderer:** draws a piece each time it is shown. A helper script runs only while the piece is prepared, and what it writes is checked like any data.

## TERM-layout — layout

**Example:** A presentation's slide layout has a title, a lead and a picture. A client's brand draws it with the title at the top left, and each slide's content fills it.

**Distinctions:**

- **Library component:** a part that arranges and draws content, from a small block to a whole page. The top library component of a kind of piece declares its layouts, and a library component may fill a content slot of one.
- **Template:** a file one starts from and then changes. A brand draws its layouts, and a piece never copies one.

## TERM-library — library

**Example:** A project's pieces take their look from the libraries it uses, such as its company's brand and the notation of its own subject.

**Distinctions:**

- **Capability:** a library is data that visual-communication reads, never a capability of its own. Its library owner needs no package of the system to give it a library version.

## TERM-library-component — library component

**Example:** A card with a heading, and a pyramid of layers filled with a slide's levels, are both library components.

**Distinctions:**

- **Component:** the core's word for a part of the system with a version of its own, such as a capability. A library component is no such part.
- **Local component:** a part made inside one piece, for that piece only. It becomes a library component once it moves into a library.

## TERM-library-owner — library owner

**Example:** project-kit is the library owner of the starter library. A project that makes a brand of its own is that brand's library owner.

**Distinctions:**

- **A file's owner:** the core gives each file one owner, the methodology or the project. A library's copy taken in is among the project's files, while its library owner is still the project that shares it.

## TERM-library-version — library version

**Example:** A client's brand at 2.0.0 and at 2.1.0 are two library versions of one library. A piece drawn at 2.0.0 keeps that look until it moves to 2.1.0.

**Distinctions:**

- **Version:** the core's word for the number of a state of a top-level part of the system, such as a capability. A library is data the system reads, never such a part, so a numbered state of it is a library version.
- **Major number:** a library version's first number. A brand built on another names the major number of the brand it fits. A stable library component breaks only in a library version whose major number rose.

## TERM-local-component — local component

**Example:** A talk needs a pyramid of layers whose widths step down, which no library holds. It is made inside the talk, for the talk's slides only.

**Distinctions:**

- **Library component:** a part a library shares with every piece that uses it. A local component becomes one once it moves into a library, generalised on the way.
- **One-off:** a local component drawn for one page of a piece, whose cost the founding record measures ([DEC-001](../../../.pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md), Implications).

## TERM-lock — lock

**Example:** A talk's lock names a client's brand at 2.0.0 and the starter library at 1.2.0. The talk keeps their look until its lock moves.

**Distinctions:**

- **The project's list of libraries:** each library's link and the library versions the project holds. A lock names one of them for each library a piece uses.

## TERM-mode — mode

**Example:** A figure in a documentation page is drawn in the light mode and in the dark mode of its brand's colour scheme. The page shows the one its reader chose.

**Distinctions:**

- **Theme:** a whole set of values. A mode gives only the values that differ on its axis.
- **Light or dark:** the two modes of one axis, the colour scheme. A brand may have more axes, each with modes of its own.
- **A reader's mode:** the light or dark setting of a reader's site. A figure follows it by showing its brand's mode of the same name.

## TERM-model — model

**Example:** A project's model holds its parts and how they connect. An overview for newcomers and a closer view of one part both draw from it.

**Distinctions:**

- **Permission model:** the core's limits on what an agent may read, write and reach ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md)). It shares the word, and is another thing.
- **Content:** what one piece shows. A fact of the model serves every piece that draws it, and no piece holds it.

## TERM-notation — notation

**Example:** A project's notation says which colour family and which icon mark a decision, on every slide and in every figure about the project.

**Distinctions:**

- **Legend:** the key that a figure shows its reader. A notation is the set of meanings behind it.
- **Brand:** the values, such as colours. A notation names the colour family that marks each thing, never a value, so each brand colours it its own way.

## TERM-option — option

**Example:** A card declares its tone, with three values. A slide's card takes one of them, and the card's border and fill change with it.

**Distinctions:**

- **Variant:** a use case's branch in this analysis. A choice a library component declares is an option, never a variant.
- **Local component:** a piece may also give one part of a library component another name the brand gives a value to. A change beyond that is made as a local component, copied into the piece.

## TERM-piece — piece

**Example:** A talk's presentation, in English and in Czech, is one piece. So is a diagram shown in a page of the documentation.

**Distinctions:**

- **Deck:** a presentation, one kind of piece.
- **Talk:** a presentation given to an audience, one kind of piece. The word never stands for every piece.

## TERM-pinned — pinned

**Example:** A talk given in October is given again to another team. Its copy is a draft with its lock pinned, so it keeps the talk's library versions until a person moves them.

**Distinctions:**

- **Final:** said of a piece that was handed out. Its lock never moves, while a pinned lock moves when a person moves it.
- **Version pin:** the core's directive that names the release a project's commands run at. A pinned lock names library versions, and is no version pin.

## TERM-published — published

**Example:** A figure of the project's parts, shown in its documentation, is published. A new library version reaches it only once a change that shows the figure before and after lands.

**Distinctions:**

- **Final:** said of a piece that was handed out, whose lock never moves. A published piece stays in use, and its lock moves through a change a person reviews.

## TERM-renderer — renderer

**Example:** One renderer draws a piece as a web page, and another draws the same piece on an online board.

**Distinctions:**

- **Adapter:** the core's word for what fits the system to a harness. A renderer fits a piece to a medium.

## TERM-stable — stable

**Example:** The starter library's card is stable. A library version that removes one of its options, and keeps its major number, is refused.

**Distinctions:**

- **Used widely:** how many pieces use a library component never makes it stable. Only its library owner marks it.
- **A new look:** a stable library component may look different in a library version that keeps its major number. Breaking it means removing or renaming a field, an option or a part, or changing what one means.

## TERM-starter-library — starter library

**Example:** A new project draws its first presentation with the starter library's cards and layers, before it makes a library component of its own.

**Distinctions:**

- **Brand:** the starter library holds no values. A brand gives its library components their colours, fonts and sizes.
