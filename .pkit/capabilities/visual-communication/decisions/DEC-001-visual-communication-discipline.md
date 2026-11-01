---
id: DEC-001
title: Visual work keeps its content and its look as data, and renderers only project it
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a piece of visual work, such as a talk's slides or a figure in a documentation page, keeps what it shows as content and takes its look from shared libraries. A brand holds values, a component library holds structure, and a notation holds what a subject's concepts look like. An engine computes one drawing from them, and each renderer only draws that drawing in its medium, adding no design of its own. A piece names the exact versions of the libraries it uses, so a release changes nothing until a person looks. What the engine cannot compute, a program makes while the piece is prepared, and its output is checked like the rest.

## Context

A project makes visual work: the slides of a talk, the figures in its documentation, a poster or a handout. Drawn piece by piece in one tool, each piece's look lives in that tool, and the tool's limits shape it. A second language, another brand or another medium means drawing it again, and what was made before is rarely reused.

One talk shows both what helps and what is missing, as the capability's design work found ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)). It had 24 slides in two languages, drawn on a whiteboard service (Mural) by a generator script, with its text kept in a file apart from the drawing.
- **The second language was cheap.** It reused every visual with other text, since the text was apart.
- **The design lived in code.** The script placed each box of most slides, and the board's own library of parts played a small part.
- **The tool's limits shaped it.** The service had no monospace font, so each terminal was drawn as a picture. It exported only a whole board, so another script cut out each page.
- **Small parts were reused, and arrangements were not.** The talk started from an earlier talk's library of 26 parts, and used 6 of them: the page frame and a few small blocks, two of them 15 and 17 times. It used none of that library's larger components, such as its steps, and drew each arrangement anew.
- **An edit on the board could not come back.** A comparison of the board with the files traced a changed title to its field, among 2,479 objects. The script wrote in one direction only, so its next run overwrote the edit.

The design was also tested beyond talks: on a figure in a documentation page, several views of one system, a kind of work a project adds, and work about several subjects under any brand. One more case was a platform whose games each restyle the platform's look within its limits.

The core layer supplies the capability itself, an opt-in installable discipline (COR-017) with an origin (COR-031). It also supplies the test of what every project needs (COR-014), data files checked by their schemas (COR-023), one validation that a capability joins (COR-055), rule sets (COR-051) and connection points between components (COR-052, COR-053). This record decides what the capability is for, and the model every later record of the capability builds on.

## Decision

**A piece of visual work keeps what it shows as content, and takes its look from shared libraries. Both are data. An engine computes a drawing from them, and each renderer only projects that drawing into its medium, adding no design of its own. One model binds every component, and every drawn part traces back to where it came from.**

### 1. What the capability is for

The capability is for *visual work*: items made to show something to people, such as a talk's slides, a figure in a documentation page or a poster, and any other kind a project adds. Its discipline is *visual communication*: making such work say the right thing, and look right. It serves a project whose visual work should share one look, reuse what was made before, appear in more than one language or under more than one brand, be drawn in more than one medium, and be checked like the rest of its work.
- **Made from reusable parts.** A piece is built from components that libraries share (points 4 to 6), so what was made once is not made again.
- **Drawn by several renderers.** The same piece can be drawn as a vector picture, a web page or objects on a whiteboard service, and handed out as a file such as a PDF. Each shows the same design, within what its medium can draw (point 2).
- **No kind of work is built into the engine.** A deck or a figure is a component a library defines (point 4), so a project adds a kind of work, such as a handout, as a component of its own.
- **The discipline's know-how ships with it.** The capability carries its view of good visual communication as rules a reviewer judges, and agents that make, review and translate pieces. Records of their own decide them.

### 2. The logical layer is the source, and renderers only project it

The capability has two layers, and the first is the source of the second.
- **The logical layer** holds a piece's content, the layout its components define, and the libraries that give it its look.
- **The engine** is the capability's code that computes the *scene* from the logical layer: each element's final place, size and values, and where each came from. A scene is computed, never edited. The record of the engine and its plugins decides what it holds.
- **A renderer** draws the scene in one medium: it *projects* the scene. It decides nothing the scene sets, so it adds no place, size, colour or font of its own.
- **What a renderer may decide is bounded.** Its medium may need a choice the scene leaves open, such as where a line breaks within the width the scene measured, or how pages lie on a board. The renderer declares each such choice.
- **What a renderer cannot draw** as the scene sets it, it approximates, draws as a picture or refuses, and it reports what it lost.
- **A different look comes only from the logical layer,** from another brand or another library, never from a renderer.
- **An edit made in a renderer,** where the medium can be edited, changes the source only when it is taken back into the logical layer, as a change a person reviews. The formats leave room for that from their first version (point 3).
- **Plugins.** They are of three kinds: renderers draw a scene, producers make pictures while a piece is prepared (point 8), and code writers write a brand's values out as code (point 9). Each says what it supports and reports what it lost. Every plugin the capability ships is part of it, and none is a capability of its own. The record of the engine and its plugins decides whether a project may add a plugin of its own.

### 3. A piece and its content

A *piece* is one finished item of visual work, such as a deck, a standalone diagram, a figure in a documentation page or a poster. It holds its own content in each of its languages, and names the libraries it uses.
- **Content** is what a piece shows, in one language: its text, its pictures, and which component shows each part. A list in it holds *items*, such as the steps of a flow. It holds no literal position, size, colour or font. It chooses only among what its libraries declare: layouts, components, options, roles, states and concepts. A second language is a second content of the same shape, with the same ids.
- **Ids and traces.** An item, or any other component the content places, that another part of the piece names carries a stable id, written as text, such as the step a panel lines up with. So does an element of shared content that a view names. Every part the engine draws traces back to the component that drew it, and to the content field it shows where it shows one. An edit made in a renderer is taken back through them (point 2). An item without an id is found by its place in its list only while the list is as it was at the render, and an edit that cannot be placed is reported.
- **What a piece declares.** A piece declares, as fields, what a check or a reviewer selects it by. They say who it is for, where it is shown, the language it is first written in and the files it is handed out as. They also say whether it explains, and name its brand and notations. The fields are the same for every kind of work, and the capability's schema for a piece names them.
- **Shared content.** A piece may also read content it shares with other pieces from a source it names, such as a model of one system that several views read. What it reads stays where it lives.
- **Two levels of checking.** The capability's own files bind to the schemas it ships, as the core binds data files (COR-023). The fields of a piece's content are checked against the schemas of the components they fill, by the capability's check, within the project's one validation (COR-055).
- **A picture made elsewhere is content,** such as a screenshot or a drawing from another tool. It does not follow a brand, and switching the brand reports it.

### 4. Components are data, and the engine knows none by name

A *component* is anything from a small block, such as a card or a connector, to the arrangement of a whole page, such as a pyramid of layers. It is data: its fields, its options, its parts and how they are placed, checked by a schema. It is built from other components and from the engine's primitives, such as a box, a text, a line and an image.
- **A library component** is one a library publishes. **A local component** is made inside one piece, for that piece alone. Both are the same kind of data.
- **The engine knows no component by name.** Its computing lives in a small set of general tools that every component uses, such as repetition over a list, formulas, connectors, text measuring and layout operators.
- **The engine knows no kind of work either.** A piece's top component, such as a deck or a figure, is a component in a library like any other. It declares its *layouts*, the forms its pages take, such as a deck's cover and slide or a figure's frame with its caption. Each layout has *slots*, the places content fills.
- **A need that data cannot express** is met in one of two ways. For one piece, a helper meets it while the piece is prepared (point 8). A need that recurs becomes a general tool of the engine, built and tested once in the capability. A component never carries code, and a project cannot add a tool to the engine itself.

### 5. Libraries hold values, structure or meaning

A *library* is a named, versioned set that pieces share, released by one owner. It names the libraries it builds on, those whose names it uses or whose values it takes, each by the major version it fits.
- **The foundations,** a component library the capability ships, declare the role names that every library shares, and the layouts and slots of the top components the capability ships. A library that adds a top component declares its layouts.

Each library holds one of three kinds of content:
- **A brand holds values:** what each role looks like, such as colours, fonts, sizes, spacing and pictures, in each of its *modes*, such as light and dark. It may also hold the form that is its own: how it draws the layouts of the kinds of work it serves, and the few parts that no shared component has. A brand may build on another brand. It keeps its base's form and every value it does not change, and changes only the values its base lists as open to change.
- **A component library holds structure:** components, which name roles and never raw values. The capability ships component libraries, and anyone may publish another.
- **A notation holds meaning:** it maps each *concept* of a subject to colour roles, and perhaps to an icon or a shape. It keeps the subject's own marks, such as its logo. A piece may name several notations.

What holds across the three:
- **Roles stand between structure and values.** A *role* is a named purpose a value serves, such as an accent colour or a surface. A component names roles, and a brand gives each role its value. A *raw value* is a literal a role could stand for, such as a colour code or a font file, and only a brand holds one. A notation's marks, a library's plain files and the pictures in content are files of their own, not values a role stands for.
- **A name is read with its library,** so no library replaces another library's component. A brand gives a shared component its values, and never keeps a changed copy of it.
- **Switching the brand changes how a piece looks,** and leaves its content and its components as they are. What the new brand lacks, such as a layout it does not draw, is reported.

### 6. A pattern arranges items, and an item says what it is

One model binds every component, whichever library publishes it, a local component included. A pattern and an item component are roles a component plays, not two kinds of data (point 4).
- **A pattern arranges items.** A *pattern* is a component that lays out one or more lists of items, such as the steps of a flow or the levels of a pyramid. It decides their order, direction and numbering, the arrows between them, and their sizes.
- **An item component draws each item.** For each list, the pattern names the component that draws its items by default. Content may name another for the whole list, and an item may name its own, a pattern included, so a row of cards may end in a note. An item's fields are its item component's, with any the pattern declares for its arrangement, each checked by the schema that declares it.
- **What content places says what it is, and its component decides how that looks.** An item, or any other component the content places, may carry a *state* its component declares, such as marked or broken. It may name a concept, read with its notation (point 5). Its component gives each state its look, through roles of any kind, such as a colour or a line's style.
- **Options are declared, never free.** A component's *option* takes a word from a list the component declares, or names something in the piece: an item by its id (point 3), or a named point of a picture made while preparing (point 8). It never takes a free number, a size or a raw value. A pattern's options choose only its arrangement, the colour each place gives its item included. The rest of an item's look is its item component's.
- **Colour says what a thing is.** An item's colour comes from the concept it names, and each of its parts takes its role from that colour. Where it names none, a default applies: the pattern's for the item's place, else its item component's, else that of the component it sits in. A state may change the colour. Content may also point one part at another role, never at a value.

### 7. A piece's libraries change only when a person moves its lock

Each piece names the exact version of each library it uses, the libraries those build on included: its *lock*.
- **A library's release never changes a piece others rely on,** such as one handed out or a figure in published documentation. A person moves its lock, after a before-and-after of what the move changes.
- **A piece being drafted** may follow the newest versions the project holds, since its author sees each render.
- **The engine and the renderers move with the capability.** A new release of them reaches a piece only at a render a person runs, whose difference shows. So a piece handed out keeps its exports as they were handed out, and they are its real freeze.
- **The record of change over time** decides the states a piece moves through, and how each state moves its lock.

### 8. What the engine cannot compute is computed while preparing

Some pieces need what the engine's tools cannot compute, such as items placed on a circle, the layout of a graph, or a picture made by a program, such as a 3D render. Such work runs while a piece is prepared, never inside the engine.
- **Who runs it, and what it writes.** A person or an agent runs a program: a *helper*, which is a script of the project's own, or one of the capability's producers (point 2). It writes a local component, as data, or a picture.
- **Checked like everything else.** Its output is kept beside the piece. A local component it writes holds no raw values and takes its text from the content. It places its parts by formulas, or is written once for each scene it is drawn in, so it fits each language and set of fonts. A picture takes its values from the brand alone, holds none of the piece's words, and may name points in its pixels, so the piece places a label at one as its own text.
- **A record of its inputs says when its output is stale,** so the program runs again when any of them changes.
- **The engine runs no helper, no producer and no other program,** and reads neither the machine's fonts nor the network. It computes only from the project's files, so the same files give the same scene on every machine, and its check can run within validation.
- **A helper needed again and again** is a sign that the engine lacks a general tool (point 4).

### 9. What is outside the capability

- **Live views.** A view that draws itself while it runs, such as a game's board, a web application's screens or a phone app, is not a projection of a scene. It stays outside. It may read a brand's values, which a code writer writes out as code (point 2), so it shares the brand with the pieces.
- **Making the art.** Drawing an illustration, modelling a 3D scene or editing a photograph is done in the tools made for it. A piece places their output, as content (point 3), or as a picture a producer makes from a model (point 8).
- **Any one project's taste.** The capability ships principles and libraries that serve any project. A project's own brand, notations, pieces and rules of style are the project's (COR-014).

### 10. Independent, and connected to others later

The capability works with no other capability installed.
- **A figure in a documentation page** is, to that page, an image produced from a source: the piece's content. This capability is then what living-docs calls the image's renderer, the tool that produces it from its source, and the piece's libraries and lock are that renderer's settings ([living-docs:DEC-002-visual-elements] points 1 and 4). A change of brand changes no content, as living-docs asks of a change of theme, since content names only what its libraries declare and never a value. Where such an image lies, and how its freshness is checked, the records of this capability's outputs and files settle with that capability's rules on images ([living-docs:DEC-002-visual-elements] points 2 and 5).
- **Another capability's visuals,** such as an analysis's diagrams, may later be drawn by this one, through a contract that names what is to be drawn. This capability reports what it cannot draw. What the other capability does then, and how the two connect, is decided with that capability.

### 11. Shipped with the methodology, and a project's work stays the project's

The capability is shipped by the methodology (COR-031), and a project installs it only when it asks for it (COR-017).
- **A project's own pieces and libraries** live in its own files, never in the capability's folder. So no project's work ships with the capability.
- **Every copy of a library in a project** is the project's file, whoever releases the library, a shipped library's copy included (COR-001). A *library copy* is a released version of a library, held whole in the project. A copy that a lock names is never rewritten, so an update of the capability changes no piece's libraries.

## Rationale

**Why two layers, and why a renderer adds no design.** A look decided in one place reaches every medium. If each renderer laid a piece out its own way, each would be a second source of the design, and a piece would need fixing in each. The talk's script shows the cost of the reverse: it mixed layout with one service's limits, so its slides could be drawn nowhere else. Where a medium must decide something, the renderer declares it, and where it cannot draw something, it reports the loss, so each difference stays in sight.

**Why every plugin is part of one capability.** The capability's point is one design drawn by several renderers. A renderer takes a scene as its input, and one that draws on a web service needs the network. The connection points between components carry neither: a data point's filler takes no input, an event's subscriber must need no network, and a process point's predicates answer about one subject (COR-052, COR-053). Inside one capability, the seam between the engine and a renderer needs no new kind of connection. Another capability already keeps its plugins inside itself, behind one seam ([demo-recording:DEC-002-three-layer-plugin-architecture], [demo-recording:DEC-003-single-capability-deferred-split]).

**Why content holds no layout.** Once what a piece shows is apart from how it looks, a second language, brand or renderer costs little, as the talk's second language did. The same content can also be lifted out of a slide into a documentation page unchanged.

**Why ids are text, and every drawn part traces back.** An edit taken back from a renderer must know which field it changes. The comparison of the talk's board already found that field for a changed title, but nothing could write the edit back. An item's place in the drawing or in its list moves when an item is inserted, so an edit placed by it is safe only while nothing moved. An id written as text stays with its item in every language and render.

**Why a piece declares what it is selected by.** A rule set's scope selects artefacts by the paths of their files and by their types (COR-051 point 2). Even once a piece is an artefact, its path and type cannot say whether it explains or where it is shown, since one piece has one of each and these facts vary apart. So a rule says in its wording which pieces it judges, as a rule for pieces that explain does, and a check or a reviewer reads that from the piece's fields.

**Why components are data.** A schema checks data, and an agent writes data against it. Code inside a component could not be checked, and would run a project's code in the engine. Data costs more the first time: in a prototype, two of the talk's slides took 123 and 256 lines of data, against 69 and 145 lines of the script's code. The data carries what the code left unsaid, such as a schema, options and slots. But it is shared, so a new slide of the same kinds costs its content alone, 19 and 53 lines. Most of the talk's visuals were rows, columns and grids that general tools cover, and the hardest needed a few more general tools, not code of their own.

**Why values are kept apart from structure.** A brand's refresh is then one change, and a component fixed once is fixed under every brand. This is how design systems keep their design tokens: a component names a role, and a theme swaps the value behind it. The talk's reuse points the same way. It reused the page frame and small blocks free of any message, and none of the components tied to the earlier talk's message.

**Why three kinds of library, each with one owner.** Values, structure and meaning change for different reasons, and different people release them: a company its brand, a team its components, a project its concepts. Kept apart, each is released on its own. The shared role names are what let a brand switch. A notation keeps one concept looking the same in every piece about it, and gives it an icon or a shape, so colour is never its only sign.

**Why a library names its bases by major version, and a base lists what may change.** A base and a brand built on it have different owners, such as a platform's brand and each game's own, and each releases alone. Held as one more mode of the platform's brand, every game's values would sit in the platform's library, and no game could release alone. A base that lists what may change keeps a fix to the rest of it reaching every brand built on it. A major version says which releases of a base fit, without the version ranges a capability declares (COR-030), since a piece's lock names one version of each library anyway (point 7).

**Why a pattern takes its item component, and an item says what it is.** The talk reused small blocks and rebuilt each arrangement, even remaking a step from another block rather than use the library's own. A pattern that draws any item component keeps the arrangement while the items change, as an instance swap does in a design tool. An item naming its own component ends a row of cards with a note, and a state or a concept covers the other cases the talk set apart: a marked step, a dropped outcome, a broken tie. A component that listed concepts would carry one project's subject into every project (COR-014), so a notation names them.

**Why options are declared, and colour follows meaning.** A free number would make each pattern a small language, and no set of renders could show every value. A word from a declared list is checked by the schema, and drawn once for each value. The talk's tables coloured each column by the layer of a pyramid it stood for, so a colour says what a thing is, not where it sits. A state may still change it, as a broken tie turns red, and a default serves where no concept is named, so a pyramid with no notation still shades its levels by their place.

**Why a lock per piece.** In visual work every change shows, so a version's promise that a fix is safe does not hold for pictures. A published figure that changes with nobody looking, or a talk that looks different when it is given again, breaks trust. A lock per piece lets one piece take a library's improvement while another stays as it was. A library copy is the project's file, as every file in a project has one owner (COR-001), and a copy a lock names stays as it was fetched.

**Why work outside the engine runs while preparing.** If a local component is slow to write as data, people go around the tool, and that was the largest risk found in the design. Some work no general tool should do: most of one project's 59 documentation diagrams are graphs that need a layout, a ring of items needs sine and cosine, and a 3D render is a program's work. A program run while preparing keeps the engine's tools a closed set. Its output is kept and checked, so the scene does not change with the program's version or the machine.

**Why live views stay outside.** A renderer projects a scene the engine computed. A game draws its board many times a second, in its own runtime, from its own state. Drawing it would make the capability a runtime of its own. Such a view needs only the brand's values, and the brand written out as code gives them.

**Why independent.** A project that makes only slides needs no documentation capability, and an analysis keeps its own diagrams until a library covers them. A contract lets a library grow one kind of visual at a time, with nothing failing in between.

**Why shipped by the methodology from the start.** The alternative was a repository of its own, where the capability would be incubated until it proved itself (COR-031). The methodology defers moving an incubated capability into what it ships, so incubating first leaves no defined way in. A project meets the capability only when it asks for it, so shipping it early costs no project anything.

### Alternatives considered

- **A tool for one whiteboard service, with the content's discipline left to projects.** Rejected. Every piece would follow one vendor's limits, and could be drawn nowhere else.
- **Kinds of visual, such as a pyramid, and library parts, such as a card, as two concepts, or a file format for each kind of work.** Rejected. It means two ways to compose one idea, the engine would know the kinds, and a diagram drawn for a slide could not be lifted out unchanged.
- **Libraries split by kind of work, such as one for decks and one for diagrams.** Rejected. The parts the talk reused most were diagram parts inside slides, and the split cuts through that reuse.
- **Ordered layers, where a later library may replace any part of an earlier one.** Rejected. Where a later library replaced a part, a fix to the earlier library's part would no longer reach the pieces.
- **A pattern naming the item it sets apart, drawn marked by the engine.** Rejected. Two places would set one item's look, and the engine would gain a tool for one case.
- **A capability for each renderer, joined through connection points, or depending on the engine's capability (COR-030).** Rejected. The connection points cannot hand a renderer a scene, and a dependent capability splits one system in two from its first day.

## Implications

- **Projects** keep their own brands, notations, component libraries and pieces in their own files, never inside the capability.
- **From the first version,** every component follows the model of point 6, every library names its bases by major version, and the content and the scene carry the ids and traces of point 3.
- **What a one-off costs is measured, and it decides whether components stay data.** A *one-off* is a local component drawn for one page of a piece. Whoever maintains the capability measures two things on the pieces made with it. The first is what content costs per page once its components exist, in lines against the code that drew the same page, where code did. The second is the tries an agent needs to write a one-off of a kind it has not seen, until it renders right in every language and set of fonts. Where content stops costing less than that code, or an agent needs more than a few tries, the rule that components are data (point 4) is revisited.
- **Later records of this capability** decide its files and their checks, change over time, brands, the engine and its plugins, the work outside the engine with the outputs, and the component library it ships to start from.
- **Left to later records or refinements:** the rules of good visual communication with their reasons, the agents, translation, taking edits back from a renderer, and the contract with other capabilities. So is whether a content file is an artefact that rules and anchors attach to, and how its prose is marked.
