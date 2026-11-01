---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-install, name: install}
      - {id: TERM-project, name: project}
      - {id: TERM-system, name: system}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.
          - Put a figure in a documentation page that follows the page's light or dark mode, and stays current as the page changes.
          - Draw several views of one system from one model, so each fact is written once and a look changed once changes every view.
          - Add a new kind of visual to a piece as data, without code, where no library component fits.
          - Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.
          - Give a piece another brand or another mode, and see its look change while its content stays the same.
          - Draw a piece through another renderer, such as a web page instead of a board, and learn what that renderer could not draw.
          - Take what people changed where my piece is drawn, such as on a board, back into its content when I ask.
          - Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.
          - Hand out a piece as a PDF, one for each language, with a page for each slide in order.
          - Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.
          - Add a kind of piece that the capability does not ship, such as a poster, without changing the capability.
          - Make a brand for a look, with its values in each mode of the axes it needs, such as a colour scheme or a device.
          - Build a brand on another brand, changing only what that brand lets me change, and give my brand versions of its own.
          - Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Have another capability's diagrams drawn in my libraries' look, the rest drawn that capability's own way, and see how much my libraries cover.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-operator
        name: Operator
TERM-brand:
  name: brand
  status: active
  definition: "library that holds the values pieces are drawn in, such as their colours, fonts and sizes"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-content:
  name: content
  status: active
  definition: "what a piece shows, such as its titles, texts and lists, kept as data apart from how the piece looks"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-library:
  name: library
  status: active
  definition: "shared set that pieces take their look from, of one of three kinds: parts that arrange and draw content, a brand, or a notation"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-library-component:
  name: library component
  status: active
  definition: "reusable part that arranges and draws the content it is given, from a small block to a whole page, shared by pieces"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-notation:
  name: notation
  status: active
  definition: "library that says what each thing of a subject is, and how every piece marks it, such as by a colour"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-piece:
  name: piece
  status: active
  definition: "visual item, such as a presentation or a documentation page's figure, that keeps its content as data and takes its look from libraries"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
TERM-renderer:
  name: renderer
  status: active
  definition: "part of the system that draws a piece in one medium, such as an SVG picture, a web page, a PDF or an online board"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/visual-communication/README.md
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`.
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Build a presentation from library components that exist, filled with my own content, so nothing made once is made again.
    - Put a figure in a documentation page that follows the page's light or dark mode, and stays current as the page changes.
    - Draw several views of one system from one model, so each fact is written once and a look changed once changes every view.
    - Add a new kind of visual to a piece as data, without code, where no library component fits.
    - Put a picture that a program makes, such as a 3D render, in any piece, in the colours of its brand.
    - Give a piece another brand or another mode, and see its look change while its content stays the same.
    - Draw a piece through another renderer, such as a web page instead of a board, and learn what that renderer could not draw.
    - Take what people changed where my piece is drawn, such as on a board, back into its content when I ask.
    - Give a piece in a second language, from content of the same structure, and learn which pages to translate again when the source changes.
    - Hand out a piece as a PDF, one for each language, with a page for each slide in order.
    - Improve a library component so the pieces that use it can benefit, without an improvement for one piece breaking another.
    - Add a kind of piece that the capability does not ship, such as a poster, without changing the capability.
    - Make a brand for a look, with its values in each mode of the axes it needs, such as a colour scheme or a device.
    - Build a brand on another brand, changing only what that brand lets me change, and give my brand versions of its own.
    - Use a brand's values in the code of a web page, a game or an app that must look like my project's pieces.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Have another capability's diagrams drawn in my libraries' look, the rest drawn that capability's own way, and see how much my libraries cover.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [Operator](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-operator.md)

## TERM-brand — brand

**Example:** A talk about the project is drawn in its company's brand. Drawn in a client's brand, the same talk looks different, and its content stays the same.

**Distinctions:**

- **Theme:** a set of values alone. A brand also holds the layouts it draws each kind of page in, and parts that only it uses.
- **Mode:** one value on one axis of a brand, such as dark on its colour scheme. A brand holds its values in each of its modes.

## TERM-content — content

**Example:** A slide's title and its lead are content, and so are the levels that a pyramid of layers shows.

**Distinctions:**

- **Layout:** where content goes and how it looks, which libraries give. Content holds none of it.
- **Material:** the planning note's word for content before its naming pass.

## TERM-library — library

**Example:** A project's pieces take their look from the libraries it uses, such as its company's brand and the notation of its own subject.

**Distinctions:**

- **Capability:** a library is data that visual-communication reads, never a capability of its own. Its owner needs no package of the system to give it a version.

## TERM-library-component — library component

**Example:** A card with a heading, and a pyramid of layers filled with a slide's levels, are both library components.

**Distinctions:**

- **Component:** the core's word for a part of the system with a version of its own, such as a capability. A library component is no such part.
- **Local component:** a part made inside one piece, for that piece only. It becomes a library component once it moves into a library.

## TERM-notation — notation

**Example:** A project's notation says which colour and which icon mark a decision, on every slide and in every figure about the project.

**Distinctions:**

- **Legend:** the key that a figure shows its reader. A notation is the set of meanings behind it.
- **Brand:** the values, such as colours. A notation says which of them marks what.

## TERM-piece — piece

**Example:** A talk's presentation, in English and in Czech, is one piece. So is a diagram shown in a page of the documentation.

**Distinctions:**

- **Deck:** a presentation, one kind of piece.
- **Talk:** the planning note's first word for a piece, from the presentation the work began with.

## TERM-renderer — renderer

**Example:** One renderer draws a piece as a web page, and another draws the same piece on an online board.

**Distinctions:**

- **Adapter:** the core's word for what fits the system to a harness. A renderer fits a piece to a medium.
