---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-30
---

# A capability for visual work, drawn by different renderers

## The question

What should a capability for visual work hold, so that any project using pkit can make presentations, concept diagrams and designs with an agent of its own? It starts from the `mural-boards` tool and what building the Friday talk on Mural taught us. Since the first discussion, Mural is one renderer among several, not the centre (see "Discussion", point 1). The note was opened as `mural-boards-capability`, and renamed before its first commit.

The note is worked through with the maintainer, one aspect at a time. Each outcome is recorded under "Discussion" with its date and its reason.

## What exists today

### The tool: `mural-boards`

It is a user-level Claude Code skill at `~/.claude/skills/mural-boards`, on one machine. It is its own git repository with 20 commits, from 28 September to 1 October 2026, and it has no remote. Its `SKILL.md` already says that its layout mirrors a capability's, and that it could become `pkit mural-boards …` once it has proven itself.

- **One script**, `scripts/mural_boards.py`, 2,959 lines, run with `uv run --script` (it needs only pyyaml and jsonschema). Its sections:
  - helpers;
  - themes;
  - configuration and tokens: OAuth with PKCE against an app the user registers with Mural, with tokens refreshed on their own;
  - the API client: at most 20 requests a second, parallel workers, and retries only where a repeat is harmless;
  - the map model: templates, composites, layouts, formulas, regions, zones and the library layout;
  - 14 commands: `login`, `init`, `list`, `status`, `verify`, `pull`, `push`, `adopt`, `forget`, `remove`, `zones`, `audit`, `theme`, and `push --verify`.
- **The map file** (`board-map.schema.json`, 652 lines) is the source of truth for the objects it describes, and the board is their rendering. Objects the map does not describe are never touched.
- **Templates and the library.** A template may name a *master*: an instance in a library frame on the board, whose layout and style define the template. A person designs in the master, `pull` takes the design into the template, and `push` carries it to every instance that did not override it. Text never travels from a master.
- **Themes**: `carbon-light`, `teal-calm` and `warm-paper`. They hold colour roles, fonts, a type scale, a grid, spacing and named slide regions. Each declares the text and background pairs that must reach WCAG contrast 4.5, and `push` refuses a theme that fails.
- **Checks**: `verify` covers sync, zones, overlaps, text that will not fit its box, contrast, and objects styled by hand or off the theme.
- **Tests**: 48 offline tests against a fake Mural API.
- **Credentials** live in `~/.config/mural-boards/`. The agent never reads them.

### How the Friday talk used it

- **Three layers.** The content is data: `slides.yaml` and `slides.cs.yaml`, one entry per slide, with a header that explains every field. A generator, `gen.py` (1,823 lines), turns the slides into instances in the board map, and the tool pushes the map to the board.
- **The library played a small part.**
  - The board's library holds 26 masters in three groups: Slides 3, Components 13, Diagrams 10.
  - Of the talk map's 76 templates, 26 follow a master, and 38 are made per slide by the generator. The generator places every box and arrow of those 38 in code, in about 25 "kinds" of visual: `pyramid`, `sockets`, `wired`, `slice`, `fanout`, `ties`, `files`, `board`, `answers`, and others.
  - The new cover was also made by the generator, not from its master.
  - So most of the design work lived in Python, not on the board.
- **Tools the talk needed beside the tool**, in `2026-10-29-friday-talk-tools/`:
  - `stray_duplicates.py`: when the board service failed a request after it had made the object, the tool's retry left a second copy behind, invisible but in the way of `remove`. This script deletes those copies.
  - `make_row_icons.py`: recolours Carbon pictograms to the theme's roles.
  - `mural_fonts.py`: lists the 12 fonts Mural accepts. None of them is monospace, so the generator renders each terminal panel to a PNG in IBM Plex Mono with `rsvg-convert`.
  - `export_pdf.py`: Mural's API exports only the whole board, as one PDF page. This script cuts it into one PDF per language, with a page per slide.
- **A second language.** The Czech set sits on the board under the English one, built from a second slides file with the same keys. Revisers rewrote it slide by slide, from a shared brief of terms and Czech sentence building.
- **The writing and flow rules** are in the talk's hand-off note, "The deck's style". Read aloud, each slide's lead answers its title and follows from the slide before. Show the big picture before any detail. Say why. Say what comes wired. Use plain words for non-native speakers. Never refer to the talk itself.
- **Lessons about the board**, from the same note:
  - Areas cannot move, so a moved slide is rebuilt.
  - Template colours take eight hex digits.
  - `pull` before editing, because the maintainer edits on the board.
  - Text that will not fit shows as `FIT` lines.

## What pkit already decides that bears on this

- A capability is one optional folder with its decisions, schemas, skills, agents, permissions and scripts (COR-017). Its dependencies are declared (COR-030).
- A capability is either shipped by the methodology or incubated in a project's own repository (COR-031).
- An agent belongs in the capability that owns its discipline (COR-026). Agents are persistent roles (COR-013).
- What every project needs goes in core, and the rest does not (COR-014). Mural is a choice some projects make, so this belongs in a capability.
- The permission model decides which tools and files an agent may use, and what the sandbox lets out to the network (COR-028).
- `demo-recording` is a precedent: a capability for presentation-like output. It has a generic format, a plugin interface, and one plugin, for macOS.

## Forces

- **A third-party service.** Each adopter registers an OAuth app with Mural and keeps its secrets outside the repository. The agent must never read them, and the sandbox must let requests out to `app.mural.co`.
- **One vendor.** The tool is Mural through and through: areas cannot move, colours have their own formats, and the API has its own limits. Its ideas, though, would fit any board: a map as the source of truth, templates with masters, themes, and checks.
- **Where design lives.** Designing on the board, in library masters, lets a person design and an agent fill in content. Designing in code, as the talk did, lets an agent draw complex diagrams exactly, but a person cannot change them on the board.
- **Content discipline.** Much of the talk's quality came from rules about content, not from the board: flow, plain words, big picture first. Some of these suit any deck, and some suit only this one.
- **The tool's state today.** It is single-user, has no remote, and lives on one machine. Moving it into pkit makes pkit its owner.

## Use cases to support

The maintainer asked to track the use cases as the discussion goes (30 October). Each says where it came from. Once the capability is decided, they can become use cases in the project's analysis (software-analysis), where the project manager plans from them.

1. **Build a presentation from reusable components.** Build a presentation from components that already exist, and reuse the same components in several presentations, each filled with its own data. Nothing already built is made again. *(The maintainer, 30 October.)*
2. **Improve a component.** Improve a component, and the presentations that use it benefit, without one presentation's improvement breaking another. *(The maintainer, 30 October. How is point 4c.)*
3. **Switch the theme.** Give the same material a different theme, and see it look different. *(Point 2.)*
4. **Render through another renderer.** Render the same material through another renderer, such as HTML instead of Mural. *(Point 1.)*
5. **Take back edits made in a renderer.** Take edits made in an editable renderer back into the material, on demand. *(Point 3.)*
6. **Add a new kind of visual.** Add a new kind of visual as data, without code. *(Point 4a; the talk needed 19 kinds for 24 slides.)*
7. **Give the presentation in a second language.** The same presentation in a second language, from a second set of material with the same structure. *(The Friday talk's Czech version.)*
8. **Hand out a PDF.** Hand out the presentation as a PDF, one per language, with a page per slide in order. *(The Friday talk.)*

Use cases 1 to 8 all come from presentations. The maintainer warned (31 October) that the capability may serve documentation and other content too, so decisions must not over-fit the two talks. Use cases 9 to 12 are proposed for that reason, to test each decision against:

9. **Put a figure in a documentation page.** A diagram in a doc page, rendered to HTML or SVG, follows the site's light or dark mode, and stays current as the page changes. It is never "delivered". *(Proposed, 31 October.)*
10. **Draw several views of one system.** Several diagrams of one system share its concepts and their look. A concept restyled once changes every view. *(Proposed, 31 October; Structurizr's "model once, many views" in the research.)*
11. **Add a discipline the capability does not ship.** An adopter adds a discipline of its own, such as a one-page handout or a poster, with its own top component and layouts, without changing the capability. *(Proposed, 31 October.)*
12. **Work about several subjects, under any brand.** A deck about two projects, or a deck in a client's brand about your own project. *(Proposed, 31 October.)*
13. **Draw another capability's visuals.** Another capability, software-analysis first, has all its diagrams drawn by visual-work in the style of the selected libraries, through a contract it declares. A library that covers only part of the contract still works: what it lacks is drawn the old way, and the coverage is reported. *(The maintainer, 31 October.)*

## Aspects to discuss

Taken one at a time, in this order. The order may change as the answers come. Points 1 to 3 are decided; points 4 to 6 came from them.

1. ~~**What the capability is for.**~~ Decided: visual work in two layers, with renderers (see "Discussion", point 1).
2. ~~**Where layout lives.**~~ Decided: in the logical layer, with its own libraries and themes; renderers only project it (see "Discussion", point 2).
3. ~~**Edits made in a renderer.**~~ Decided: an on-demand import writes the exact matches and reports the rest (see "Discussion", point 3).
4. **The logical model.** What the logical layer holds, and in what format: the material per discipline (a deck, a diagram, a design); the kinds of visual with their data, such as the talk's `pyramid` and `sockets`; the primitives a scene is made of; the library of graphical elements; the themes. Taken in parts:
   - ~~4a. How a kind of visual is defined.~~ Decided: as data only; computing lives in the engine's general tools (see "Discussion", point 4a).
   - ~~4b. Whether a kind of visual and a library element are one concept or two.~~ Decided: one concept, components all the way down (see "Discussion", point 4b).
   - ~~4c. How the library will be used: its levels and scopes.~~ Decided: eight levels in three scopes, built lean (see "Discussion", point 4c, its outcome at the end). The name of level 8 went to the naming pass (point 16), which chose "piece".
   - ~~4d. How a change reaches a talk.~~ Decided: drafting follows the latest, delivered is locked, reused is upgraded on purpose with a preview (see "Discussion", point 4d).
   - ~~4e. Variants of a component.~~ Decided: options the component declares, with overrides through roles only, and a one-off for anything beyond (see "Discussion", point 4e).
   - ~~4f. The material's format per discipline, and how it binds to a component.~~ Decided: one shape for every discipline; the engine knows no discipline (see "Discussion", point 4f).
   - ~~4g. How pieces group into libraries, so a context can share them, such as "IBM Deck" or "IBM Diagram". Came from 4f.~~ Decided: libraries by owner, holding values, structure or meaning (see "Discussion", point 4g, its outcome at the end).
   - ~~4j. The lifecycle of work that is never delivered, such as a figure in a doc page (point 4d revisited). Came from the over-fitting check of 4g.~~ Decided: every piece of work has a lock, and a fourth state, living, moves it through a reviewed proposal (see "Discussion", point 4j). Taken before 4i, which came up next.
   - ~~4h. The scene's primitives, and how each traces back to the model.~~ Decided: a tree of groups with traced primitives whose names map onto SVG, with SVG and HTML as the reference renderer (see "Discussion", point 4h).
   - ~~4i. Where a library lives and how another adopter gets it; whether pkit's capability dependencies (COR-030) or incubation (COR-031) carry it. Came from the critic's review of 4g.~~ Decided: libraries are the capability's data, kept as a read-only folder per version, with a lock per piece (see "Discussion", point 4i).
5. **Text and fonts.** A layout made before rendering must know how much room text takes, and every renderer must draw it in the fonts it was measured with (its profile's fonts, point 18d). Mural accepts only 12 fonts, none of them monospace. Decided on 31 October: measure only from committed files, the engine breaks lines with language rules, Mural wraps within the measured width, estimate first (see "Discussion", point 5).
6. **How a renderer plugs in.** Plugins inside the one capability, as `demo-recording` does, or a capability per renderer that fills a role (COR-052, COR-053). Also the name: pkit already says "adapter" for a harness adapter (COR-005), so these are "renderers". The critic suggested (31 October) checking whether `demo-recording`'s plugin interface can serve as the renderer contract (COR-007).
7. **Its origin.** Shipped by project-kit, or incubated in a project first (COR-031).
8. **The starter library and themes.** Which graphical elements and themes the capability ships, from the talk's 26 masters, its kinds of visual, and the three themes.
9. **The agents.** A designer agent: its job, its limits, its tools. Whether a reviewer reads a deck for flow and plain words.
10. **The skills.** The build loop (change, generate, render, verify) as a skill, and how a deck or a diagram is authored.
11. **The rules.** Which of the talk's style rules the capability ships, and which stay a project's own.
12. **Credentials, permissions and the sandbox**, per renderer that talks to a service. Since renderers stay plugins of one capability (point 18c), it decides how the Mural plugin's network access and credentials reach only the projects that use it.
13. **Output.** PDF, images, a set per language, and the translation workflow. The maintainer asked (31 October) that the capability carry both, the know-how included:
    - **Outputs.** Preparing what is handed out, such as a PDF of a deck, one per language, a page per slide in order. The Friday talk needed a script of its own for it, because Mural exports only the whole board (`2026-10-29-friday-talk-tools/export_pdf.py`; use case 8).
    - **Variations per language.** The same work in several languages, from material of the same structure (use case 7).
    - **Translation know-how, shipped in the capability.** What the Czech version taught: translate a slide from its meaning, not word for word, one translator per slide; keep the English words developers say (capability, engine, slot); build each sentence the target language's way; one glossary, one word for one thing; a review by a native speaker. The lessons are in the Friday talk's note, "The Czech version".
14. **The workarounds.** What to fix in the Mural renderer rather than carry beside it: the duplicates left after retries, monospace text rendered as images.
15. **Moving in.** Tests, versions, and moving today's user-level skill into pkit.
16. **Names.** A naming pass with the maintainer before any record or code fixes a name (see "Names").
17. ~~**The runtime and outside programs.**~~ Decided: Python, with no Node; outside programs are called only on the path that needs them, and the capability checks for them (see "Discussion", point 17).
18. **The architect's four revisions of decided points**, taken one at a time:
    - ~~18a. What a delivered piece locks (4d).~~ Decided: library versions only; the exports are the real freeze (see "Discussion", point 18a).
    - ~~18b. Where the core library's versions live (4i).~~ Decided: the core holds only the interface, a starter library holds the opinionated components, and all three shipped libraries are copied into the project like any other (see "Discussion", point 18b).
    - ~~18c. How renderers plug in without connection points (point 6).~~ Decided: plugins inside the one capability, never a capability per renderer (see "Discussion", point 18c).
    - ~~18d. A scene per font profile (point 2, with point 5).~~ Decided: font profiles set by the context, one scene per profile (see "Discussion", point 18d).
19. ~~**References between elements.** One element using another's measured size, one owner per dimension, cycles refused.~~ Decided: two sizes per element, public anchors, list operations as layout operators (see "Discussion", points 19 and 20).
20. ~~**Format numbers** on every file from its first commit, read by the engine forever.~~ Decided: pkit's `schema_version` for breaking changes, `requires` for added features, semver for each library's content (see "Discussion", points 19 and 20).
21. ~~**An escape for hand-drawn one-offs**, such as an area the renderer leaves alone; the architect's largest risk to the product.~~ Decided: the risk is a missing tool; four tools are added, and helper scripts run while preparing write checked data (see "Discussion", points 21 and 22).
22. ~~**Graphs:** graph layout as an engine tool, or relation graphs left to Mermaid as software-analysis does.~~ Decided: a helper arranges graphs while preparing, views share one model file, and other capabilities connect later through a contract with fallback (see "Discussion", points 21 and 22).
23. ~~**Where the first slice's code lives,** outside project-kit's shipped tree.~~ Decided (31 October): a new repository of its own, which installs pkit and incubates the capability in its own `.pkit/capabilities/` (COR-031), nothing shipping to anyone. The Mural plugin reuses the mural-boards tool's client, sign-in, pacing and sync record, and the mural-boards skill keeps working unchanged until the capability replaces it (point 15). Whether the capability later moves into project-kit or stays in its own repository is point 7. The repository is created when building starts, in a session rooted there or with the maintainer's confirmation (the cross-repository rule), and its name comes from the naming pass (point 16).
24. **A protocol between capabilities.** How a consumer such as software-analysis declares a contract, how visual-work is connected to it, and whether pkit's slots and connection points can carry a request with input or need a core decision. Use case 13; not built now.

## Discussion

*(Outcomes are recorded here as they are decided, newest last.)*

### 1. What the capability is for (30 October)

**Outcome.** The capability is about visual work, not about Mural. It has two layers.

- **Visual work, at the logical level.** It is split into disciplines and sub-disciplines: presentations, diagrams, designs, and others later. The material says what to show, not how it looks.
- **Renderers** draw that material. Mural is one renderer. HTML is another and may matter most: "who needs the Mural at the end". Figma might be one, but it works very differently.

What matters most is that it is built cleverly. A project can switch colour themes easily. The same material can be rendered by different renderers, and may look completely different in each, while it stays the same at the logical level.

The maintainer also asked whether producing visual work inside tools such as Mural is becoming obsolete. That is why HTML is a first-class renderer, not an afterthought.

**Options that were on the table.**

- A Mural tool capability, with content discipline left to projects.
- Visual work with Mural as its only renderer.
- Two capabilities, an engine and visual work.

The maintainer went further than all three, to renderer independence.

**What the Friday talk shows for this.**

- The seam already half exists. `slides.yaml` is close to the logical level: a title, a lead, the kind of visual, and its data. `gen.py` mixes layout with Mural's own constraints: areas, eight-digit colours, and terminals as PNGs because Mural has no monospace font.
- The Czech set reused every kind of visual with other text. Once the material is separate, a second rendering costs little.
- An HTML renderer would have removed two of the talk's workarounds. It has monospace fonts, so terminals need not be images. It prints to PDF, so no cutting of a whole-board export is needed.

**To check.** As far as the agent knows, Figma's public REST API reads files but cannot create layers. Writing goes through a plugin that runs inside Figma. If so, a Figma renderer needs a plugin bridge. This is not a reason to rule Figma out, only a cost to know.

### 2. Where layout lives (30 October)

**Outcome.** The logical layer defines the layout, and renderers only *project* it. The logical layer also owns its libraries of graphical elements and its themes, in the capability's own format, so nothing depends on one technology.

- **A renderer adds no design of its own.** It turns what the logical layout defines into its medium: shapes on a Mural board, elements in an HTML page, layers in Figma.
- **A different look comes from the logical layer.** It comes from another theme or another library, and never from the renderer. This is how "the same material, a completely different look" from point 1 is reached.
- **Where a renderer cannot draw something natively,** it still projects it faithfully. For example, it can place an image that the capability renders from the logical description, as the talk did with terminals on Mural.

**Options that were on the table.**

1. Each renderer lays out each kind of visual itself.
2. A shared layout makes a neutral scene, and thin renderers paint it.
3. Both, with a renderer free to draw a kind in its own native way.

The agent recommended 3, built as 2 first. The maintainer chose 2 in its pure form, and widened it: the libraries and themes are the logical layer's too.

**What this changes from today's tool.**

- In `mural-boards`, the library lives on the board. Masters are designed in Mural, and `pull` takes the design into the map.
- Under this outcome, the library's source is the capability's own format, and a board's library is one more projection of it. Whether a person may still design on a board is part of point 3.
- The talk's `gen.py` already does most of the work of a shared layout. What it lacks is a renderer-neutral output: today it writes Mural map objects.

**A parallel with pkit itself.** pkit's pyramid has the same shape. The decisions are the source, and every layer below carries them out and is checked against them (COR-065). Here the logical layer is the source, and each renderer carries it out. A check, such as `verify` today, can confirm that a rendering matches its source.

**Costs to keep in view.**

- The logical layout must measure text before any renderer draws it. Every renderer must then use the same fonts (point 5).
- A browser's own text flow, or Figma's auto-layout, goes unused, because the logical layout has already placed everything.

### 3. Edits made in a renderer (30 October)

**The maintainer's ask.** Where a renderer can be edited, as Mural can, the capability should detect the changes made there and update the logical model from them, on demand.

**Outcome.** An on-demand import does three things.

- **It writes the exact matches into the logical model.** An edit that has exactly one place to go is written there. Git is the review: the person reads the diff, and commits or reverts it.
- **It stops on a conflict.** If a field changed both in the renderer and in the logical model since the last render, the import writes neither, and reports it.
- **It reports the rest and changes nothing for them.** These are edits that have no exact place to go. For each one, a person or the agent chooses: make it an explicit override, change the theme or the library, or drop it.

**Options that were on the table.**

1. Write every edit that maps.
2. Propose every edit, and write only what is accepted one by one.
3. Write the exact matches, stop on conflicts, and report the rest.

The agent recommended 3, and the maintainer agreed. A separate proposal step adds little, because git already shows everything that was written.

**Evidence from the Friday board.** `status` compared the 2,479 objects it describes and found one difference. It traced that difference to its field, `T-cs-cover.title`: "Vývoj s AI podle rozhodnutí v…" in the map, "Decision driven AI development" on the board. Detection already works.

**Where each kind of edit lands.**

| Edit in the renderer | Where it lands |
|---|---|
| Text that came from a field of the material: a title, a lead, a card | That field. Today's `pull` already reverses a template's text pattern. |
| A library element's design, changed in its master on a board | The library. Today's `pull` already does this for masters. |
| A colour picked by hand, off the theme | No exact place. Reported. |
| A moved box, where the layout is computed (the layers of a pyramid, an arrow) | No exact place: no field holds that position. Reported. |
| A new object drawn by hand, or a deleted one | No exact place: no element matches. Reported. |

**What this asks of the design.** Every rendered object must trace back to its element and field in the logical model. Today the trace stops at the board map. The talk's generator writes the map in one direction only, so a pulled title would be overwritten by the next build.

### 4a. How a kind of visual is defined (30 October)

**Outcome.** A kind of visual is data only: a declarative layout in YAML, checked by a schema. The computing lives in the engine, as a few general tools that every kind can use:

1. **Repetition** over a list in the material, such as "one box for each layer".
2. **Formulas**: plain arithmetic over an item's index, the count of items, and theme tokens.
3. **Connectors** between named elements, with routing options such as "spread the ends evenly".
4. **Text measuring**, so a box can size itself to its text.

When a kind needs something data cannot say, the engine gains a new general tool, shipped and tested once in the capability. A kind never carries code.

**The limit accepted with it.** A project cannot add a tool to the engine itself. It asks for one, and the question is revisited if that need actually comes up.

**Options that were on the table.**

1. Kinds as code: a function per kind, as in `gen.py`.
2. Kinds as data: a declarative layout.
3. Both: data, with code kinds called by name as elements, the way a custom component works in HTML.

The agent first recommended 3. The maintainer leaned to 2 and asked how 3 would mix data with code. Reading the talk's hardest kinds showed that 2 is enough, so the agent changed its recommendation to 2 with the rule above, and the maintainer agreed.

**Evidence from the talk.**

- Its 24 slides use 19 different kinds. Only `wired` (4 slides) and `map` (3 slides) were reused. A new kind must therefore be cheap to make, and an agent can write data correctly against a schema.
- Most kinds are arrangements: rows, columns and grids of cards, panels and terminals (`wired`, `map`, `files`, `checklist`, `rules`, `install`, `answers`).
- The two hardest kinds need only arithmetic:
  - `pyramid`: for each layer, width = `top_w + i × step`, x = `centre − width / 2`, y = `top + i × (height + gap)`.
  - `sockets`: each arrow's end = `slot middle + (k − (n − 1) / 2) × 32`, which spreads n arrows evenly around a slot, plus "connect this box to that slot".
- The Mural tool already evaluates formulas over theme tokens, such as `=@grid.margin + @space.10`.

### 4b. Kinds of visual and library elements (30 October)

**Outcome.** They are one concept: components all the way down.

- A tag, a card, the pyramid and a whole slide are all *components*. A component is data with parameters, built from other components and from the scene's primitives.
- A library is a set of components.
- A discipline's "kinds of visual" are simply the components its material may name at the top. Being a kind is a role, not a separate concept.
- A parameter's value may come from the material. That is how any component, not only a kind, takes the material's data.

**Options that were on the table.**

1. One concept.
2. Two concepts, elements and kinds, each with its own schema and rules.

The agent recommended 1, and the maintainer agreed. The reasons:

- There is one schema and one way to compose, for the agent and for adopters alike.
- It is already how the Mural tool works: a template can contain other templates.
- A library can hold anything from a tag to a complete slide layout, and a theme or a library change reaches all of it the same way.

**The maintainer's aim, said with it.** Build reusable components, and build presentations from them, each filled with its own data, so that nothing already made is made again. Improve components over time, perhaps with versions or variants. This became use cases 1 and 2 and points 4c and 4d.

### 4c. How the library will be used (30 October, open)

**What the agent proposed.** Three answers to "how does an improved component reach the presentations that use it". First, no versions: a presentation follows its components, and a change flags every presentation that uses them, as pkit's anchors do (COR-050). Second, one version per library, with compatible ranges. Third, one version per component.

**The maintainer stepped back.** Re-rendering an existing presentation when a component improves may not be wanted at all. The question is first how the library is used.

- **Some parts change rarely.** Slide layouts may change once a year. There may be one template library per context, such as one for DAM and another for IBM internal projects.
- **Content elements will evolve.**
- **Is it evolution or extension?** The Friday talk seemed to create completely different elements from the Mockingbird talk. Each talk describes different things, so it may be too early to say what was reused, or should have been.
- **Updating is hard.** Looking at the Mockingbird board now, the maintainer would not dare update its components.
- **The aim:** keep freedom for creativity, and still have a library of reusable components that compose.
- **A missing concept?** Perhaps there should be a design language, defined in one unified way, with the components as its projection. The maintainer feels short of background in design, and asked for research.

**Evidence: what the Friday talk took from the Mockingbird talk.** The two board maps were compared: Mockingbird's (`mockingbird/.pkit/scratchpad/active/2026-09-28-living-docs-board.yaml`, its board `ibmresearchdesign6459.1790595606038`) and the Friday talk's.

- **The Friday talk started from Mockingbird's whole library.** It has the same 26 templates and the same 26 masters in the same groups. 22 are identical, and 4 were changed: `actor`, `artefact`, `cover` and `role_badge`.
- **It used only 6 of them**, counted per language set:

  | Template | What it is | Uses per set |
  |---|---|---|
  | `slide` | the frame | 24 |
  | `section` | the frame | 5 |
  | `notice` | the frame: the bottom evidence line | 20 |
  | `stage` | a building block | 15 |
  | `link` | a building block: the arrow joint | 17 |
  | `artefact` | a building block | 3 |

- **Mockingbird's content components went unused.** None of `card`, `tile`, `stat`, `listrow`, `branch`, `actor`, `label`, `step`, `compare` or `timeline` appears in the Friday talk. Mockingbird used them 4 to 20 times each.
- **The Friday talk added 50 templates.** 38 were made per slide by the generator: one-off diagrams. 12 are new reusable pieces: `terminal`, `term_image`, `highlight`, `pstage`, `step_card`, `kind`, `kind_group`, the tree's `tree_bar`, `tree_tag` and `tree_note`, `divider`, and `talk_cover`.

**What the evidence suggests.**

- **The frame was reused unchanged.** The frame is the slide, the section, the evidence line and the theme.
- **A few small building blocks were reused heavily:** a box with a heading, and an arrow.
- **Content components were mostly not reused.** New ones were made for the new subject.
- **Most of the work was one-off compositions,** one per slide.

So reuse happened at the bottom (tokens, the frame, small building blocks) and not in the middle (content components). The top (compositions) is new in every talk. That matches the maintainer's sense that the talks "describe different things".

**The research the maintainer asked for (30 October).** Five researchers covered:

1. the vocabulary and design tokens;
2. systems that serve several brands;
3. reuse, governance and versioning;
4. presentation tools;
5. diagrams as models and views.

The synthesis is kept beside this note, with its sources: `2026-10-30-visual-work-capability.research.md`, "Share the grammar, lock every delivered talk". What it says for this note:

- **The missing concept has a name: design tokens.** The design language stored as named data, in three tiers:
  - raw values;
  - roles, such as accent, surface or primary text;
  - an optional value for one part of one component.

  There is a standard file format, the W3C Design Tokens Community Group's 2025.10, stable since 28 October 2025. Its Resolver module describes themes and modes as data. Adopt it rather than invent one.
- **Components bind to the design language; they are not its projection.** A component names roles, never raw values, and a theme swaps the values behind the role names (Carbon: "Tokens are universal and never change across themes"). "Projection" stays the word for the logical layer → renderer relation, as in point 2. The second half of the missing concept is the split between a component's *specification* and its *implementation*. The specification is data in the logical layer: parts and slots, options, states, and which token each part uses. The implementation is one per renderer. Adobe's Spectrum Design Data, still a draft, is the closest precedent.
- **The two talks follow the expected curve.**
  - Reuse gathers in the foundations: the theme and the frame. It also gathers in small components free of any message.
  - Content components tied to a message do not travel.
  - The 38 diagrams are healthy one-offs ("snowflakes", Brad Frost). They belong in a labelled place inside the talk.
  - A shape is promoted to the library once it has appeared about three times. The measures that matter are how cheap a one-off is to make, and how fast a repeated one-off becomes shared.
- **A grammar, not a catalogue.** The shared layer gives primitives, layout operators (stack, align, distribute, repeat), defaults and a few kinds. Wickham's grammar of graphics, Vega-Lite and Penrose are the precedents. This supports point 4a. The research adds three conditions:
  - Formulas stay a restricted language, as Vega's has no loops or assignment.
  - Layout is deterministic and local; Bluefish dropped a global constraint solver.
  - Manual overrides are keyed by stable ids.
- **"All the way down" must not tax the one-off.** If a one-off is painful to write as data, it escapes the tool. A sanctioned way out is needed: a picture or a renderer-native object embedded as it is, which then does not follow the theme. A copied-and-changed part records where it came from.
- **A theme carries values, never structure.**
  - A frame is a per-context template: the slide, the section slide, the footer, the grid.
  - Switching context swaps both the theme and the frame. Switching mode, such as light or dark, swaps values only.
  - Context, mode and output scale are separate axes, as in Adobe Spectrum.
- **A context library is values, a frame and a few brand-only parts. It is not a fork of the components** (Infinum's case study). For the IBM context, Carbon's values already exist.
- **Rendering to several renderers has no prior art.** No tool found renders one component definition natively into HTML, a slide tool and a design tool at once. The contract with a renderer should be:
  - layout names and slot roles;
  - a declared list of the features each renderer supports;
  - a report of what each render lost.

  Whether Mural knows variables or themes is unknown. Tokens are likely resolved into literal values before a push, as the tool does today.
- **Updates are pulled, never pushed.** In visual work every change shows, so semver's "a patch is safe" does not hold for pictures. The proposed lifecycle:
  - A talk being drafted follows a version range.
  - A delivered talk locks exact versions of every library and of the renderer, and keeps a static export.
  - A talk reused for a new audience is copied, then upgraded explicitly, with a before-and-after preview per slide.
  - There is one version per library: one for the shared core, and one per context.
  - The yearly frame change is a major release.
  - A part is deprecated in any release and removed in the next major one.
  - A migration note per breaking change is enough.
- **The proposed levels**, eight in three scopes (shared core, per context, per talk):

  | Level | Scope |
  |---|---|
  | 1. Tokens | role names in the core, values per context |
  | 2. Themes | per context |
  | 3. Primitives and layout operators | core |
  | 4. Components | core |
  | 5. Recipes and kinds | core or per context, after about three uses |
  | 6. Frame (named "layouts" in the naming pass) | per context, changes about yearly |
  | 7. One-offs | per talk, never shared |
  | 8. Talk | per talk, frozen once delivered |

  A brand guide (logo, imagery, tone) sits above the logical layer, and the renderers sit below it.

**Questions the research left open.** It found:

- no documented practice for freezing a delivered presentation;
- no reuse data for slide or diagram libraries;
- nothing on Mural's support for variables;
- nothing that confirms which tools support the Resolver module.

**The levels on one real slide (worked example, 30 October).** The maintainer found the levels too abstract and asked for examples. Take the Friday talk's "How capabilities work together", slide 23 of 24:

| What you see on the slide | Level | Why it sits there |
|---|---|---|
| The yellow of the capability boxes, the purple arrows, the grey text | 1. Tokens | The box names the role `capability`, never `#F1C21B`. The IBM theme says `capability = yellow-30 = #F1C21B`. |
| All those colours and fonts together | 2. Theme | The IBM theme, today `carbon-light`. A DAM theme gives the same roles other values. Dark mode flips `text-primary` and `background`. |
| Boxes, text, arrows; slots stacked one under another; one slot repeated per entry; the three "why" cards spread across | 3. Primitives and layout operators | box, text, connector; stack, repeat, distribute. |
| The grey `doc-check` chip; a box with a heading; the "Limit" note with its blue bar | 4. Components | They are small and say nothing on their own, so every talk can use them. |
| Terminal panels with tie cards (`wired`, 4 slides); a table (`map`, 3 slides) | 5. Recipes and kinds | Each recurs, so each is a candidate to be promoted once a third talk needs it. |
| The title at top, the lead under it, the evidence line and "23 / 24" at the foot; the cover; the section slides | 6. Frame | It is the IBM context's template. A DAM frame would have another cover, logo and footer. |
| The diagram of capabilities plugging into slots | 7. One-off | It was drawn once, for this message. It lives in the talk. |
| The title, lead, slot names, contributors, "why" texts, notes; the Czech set; the lock | 8. Talk | The talk's material and what it is locked to. |

What each change does:

- **Switching the mode** to dark changes level 1's values only.
- **Switching the context** to DAM changes levels 1, 2 and 6. The talk's material and its one-offs stay the same.
- **Improving the chip in the core** reaches every talk still being drafted. A delivered talk keeps the chip it was locked to:

  ```yaml
  talk: friday-talk
  delivered: 2026-10-30
  uses: {core: 1.3.0, context-ibm: 2.0.0, renderer-mural: 0.9.0}
  export: [friday-talk.en.pdf, friday-talk.cs.pdf]
  ```

- **A third talk that needs a stepped pyramid** promotes the Friday talk's one-off `pyramid` to a kind in the core. (Revised by point 18b and the naming pass: it goes to a structure library or the starter, since the core holds only the interface.)

**Outcome (30 October).** The maintainer accepted the eight levels in three scopes, after the worked example. It is built lean:

- start with token roles and values, one frame per context, a small shared core, and one-offs inside each talk;
- add recipes and kinds, component tokens, and extra modes or scales only when a real talk needs them.

**On the terms** (the maintainer asked whether "one-off" and "talk" are design terms):

- **One-off** is informal, but established in design-system writing.
  - Brad Frost writes "one-off components" (2018), and suggests a folder named `/one-offs` or `/departures` for them.
  - He later names the tier "snowflakes" (2021): parts that "don't really get reused outside of their first use case".
  - A Figma copy that has left its library is a "detached instance".
  - The note keeps "one-off": it is plain English, and Frost uses it too.
- **Talk** is not a design term. It is this note's word for the Friday talk.
  - Atomic Design calls this level a *page*: a template filled with real content.
  - Presentation tools call it a *deck* or a *presentation*.
  - Since the capability covers diagrams and designs too, level 8 needs a name that fits every discipline. The naming pass (point 16) chose "piece".

### 4d. How a change reaches a talk (30 October)

**Outcome.** The maintainer accepted the lifecycle the research proposed:

| State | What it follows |
|---|---|
| Drafting | The latest shared core and context library. An improvement shows at the next render. |
| Delivered | Exactly what it used, locked (for example `core 1.3.0, context-ibm 2.0.0, renderer-mural 0.9.0`), with its exports kept. Nothing changes unless a person asks. *Revised by point 18a: only library versions are locked; the exports are the real freeze.* |
| Reused for a new audience | The talk is copied, then upgraded on purpose, with a before-and-after preview of each slide. Any change can be undone. |

Behind the lifecycle:

- There is one version per library: one for the shared core, and one per context. Components are not versioned one by one.
- A yearly frame change is a major version of its context.
- Old versions stay available for locked talks to render. Each version is a git tag, and a lock points at it.
- The machinery large design systems need for many teams is not needed for one author: committees, notice periods, upgrade scripts. A migration note per breaking change is enough.

### 4e. Variants of a component (30 October)

**Outcome.** A component declares its options, and a talk picks from them. Each value of an option points the component's parts at different roles. For example, a card declares `tone: pkit | yours | capability`, and tone `capability` sets the border to `capability` and the background to `capability-bg`. A fix to the card reaches every tone, and a new tone is a small change to the card.

- **A talk may also override a part, but only through a role.** It may say "this border is `accent`", and never give a raw `#hex`, so the theme still reaches the part.
- **Anything beyond that is a one-off.** The component is copied into the talk, and its origin is recorded.

**Options that were on the table.**

1. Options the component declares.
2. A separate component per variant, which means copies.
3. Free overrides where the component is used.

The agent recommended 1 with a narrow form of 3, and the maintainer agreed. Figma works the same way: declared variants, limited overrides, and detach.

**The Friday talk's examples.** The cards in three tones (pkit purple, yours blue, capability yellow; `CARD_TONES` in `gen.py`), and the pairs diagram in two styles, plain and tinted (`PAIR_STYLES`). "Variant" and "option" are working names (see "Names").

### 4f. The material's format (31 October)

**Outcome.** One shape for every discipline. The material is a tree of components with their data (point 4b).

- A presentation's top is a deck component, whose fields are its title, author, parts and slides. A slide is a component whose fields are its title, lead, visual, limit, notes and minutes.
- A standalone diagram is a single component with its data, such as `sockets` with its provider and contributors. A diagram drawn for a slide can be lifted out unchanged as a diagram of its own, or put into a document.
- Each component's schema checks its fields, so a presentation's file still reads like the Friday talk's `slides.yaml` does today.
- Layout leaves the material. Today's `font_size: 22` in a visual becomes an option of its component (point 4e).

**Options that were on the table.**

1. One shape for every discipline.
2. A format per discipline (a presentation file, a diagram file, a design file), each with its own schema and its own reader.

The agent recommended 1, and the maintainer agreed.

**The maintainer's addition.** The engine knows no discipline: "deck" and "diagram" are components in libraries, not code. Yet libraries per discipline must be possible, with an opinion on how pieces group, so that a context can share, for example, "IBM Deck" or "IBM Diagram". That opinion is point 4g.

The name of level 8 is not settled here. The naming pass (point 16) chose "piece".

### 4g. How pieces group into libraries (31 October)

**The agent's first recommendation** (superseded by the revised one below). A library is what is shared and versioned: a named set of pieces that names the libraries it builds on. Pieces group on two axes, brand and discipline:

| Library | Holds | Builds on | Made by |
|---|---|---|---|
| `base` | primitives, layout operators, small components (chip, card), the token roles | nothing | the capability |
| `deck` | the deck and slide components, a plain cover and section slide | `base` | the capability |
| `diagram` | the diagram component, nodes, connector styles | `base` | the capability |
| `ibm` | IBM's token values, its themes (light, dark), logo and fonts | `base` | the IBM context |
| `ibm-deck` | IBM's slide frame (cover, section slide, footer, grid), IBM's deck recipes | `deck`, `ibm` | the IBM context |
| `ibm-diagram` | IBM's diagram notation and recipes | `diagram`, `ibm` | the IBM context |

A DAM context adds `dam` and `dam-deck`. A presentation names one library, `uses: ibm-deck`, and gets the libraries it builds on. `uses: dam-deck` switches the context.

The rules of the grouping:

- **A brand library holds values only, no layout.** IBM Deck and IBM Diagram share one IBM look, and a brand refresh is one change.
- **A discipline library holds structure only, through roles, never values.** IBM Deck and DAM Deck share one slide component, so a fix to it reaches both.
- **Each library has its own version.** The yearly change of IBM's slide frame is a major version of `ibm-deck`, and `ibm-diagram` does not move. This refines point 4d, which said one version per context.
- **The engine does not hold the grouping in code.** A check can verify the two content rules: no raw values in a discipline library, no layout in a brand library.
- **Built lean, as in 4c.** The capability ships `base` and `deck` first, and `diagram` when a real diagram needs it. A context starts with its brand library plus one library for each discipline it uses.

It listed two other options: one library per context with a folder per discipline, and no opinion at all. It left one edge for later: a structure only IBM uses, in both decks and diagrams, had no home.

**The critic's review.** The maintainer asked for the critic's opinion. The critic kept the basic idea: values apart from structure, components bound to roles, no discipline in the engine. It found four problems with the first recommendation.

1. **Splitting deck from diagram cuts through the reuse that happened.** The Friday talk's most reused blocks are diagram parts used inside slides: `stage` (15 uses), `link` (17) and `artefact` (3). With the split, `uses: ibm-deck` could not reach them, and a slide's diagram could not be lifted out unchanged (point 4f).
2. **A version per library reverses point 4d and buys nothing that shows.** Drafting follows the latest, delivered is locked, and reuse is previewed, so in no state does a diagram see a difference. It adds a diamond of dependencies (`ibm-deck` builds on `deck` and `ibm`, both on `base`) and the version ranges between them.
3. **The two content rules leave the combined library unclassified.** IBM's slide grid (3200 wide, 16 columns, margin 128) is numbers, it is IBM's, and it is the deck's. "Raw value" was not defined. A token name such as `@grid.span.16` carries IBM's 16 columns into shared components.
4. **Nothing says how one library overrides another.** If `ibm-deck` replaces `deck`'s cover and slide by name, a fix to `deck`'s reaches no IBM talk, and the frame is the only part reused today.

It also found gaps:

- **A third axis, the subject.** Both talks carry the same colours for pkit's concepts as raw Carbon values: `role_agents`, `role_checks`, `role_code`, `role_people`, `role_admin`, `role_experimenter`, `role_neutral`, each with its `_bg` partner. The Friday talk added `role_architecture` and `role_addon`. They are about the subject, neither about IBM nor about a discipline, and point 4e forbids raw values in a talk. The project's logo on the cover is the same kind.
- **Parts only a brand uses are the normal case, not an edge.** Today's library is Carbon-flavoured throughout ("Carbon tile", "Carbon inline notification").
- **Switching the context works only for names both contexts have.**
- **The lean start cannot render.** The core holds no values, and the neutral themes (`teal-calm`, `warm-paper`) had no home.
- **Where a library lives and how another adopter gets it** is not designed, though sharing is the aim. pkit already has versioned dependencies between capabilities (COR-030) and incubation (COR-031).
- **Fonts and the type scale change layout**, and differ per discipline and per renderer.

Its counter-proposals: separate the unit you version from the unit you use (C1); ordered layers, where a talk lists a stack and the later layer wins (C2); the frame as an interface each context implements (C3); and, named to be declined, a context library as an incubated capability (C4).

**The agent's revised recommendation** (C1 with C3, and the subject as its own library). One library per owner, one version each, so point 4d stands:

| Library | Holds | Made by |
|---|---|---|
| core | role names (with neutral category roles `category-1` …), primitives, layout operators, components for every discipline (chip, card, `stage`, `link`, connectors), the deck and diagram top components, and the frame's interface: named layouts (cover, section, slide) with their slots | the capability |
| neutral context | neutral values (today's `teal-calm`, `warm-paper`) and a plain frame, so the core renders out of the box | the capability |
| a context, such as `ibm` | IBM's values (colours, fonts, logo, type scale, light and dark), its frame (every named layout the core declares, with its grid), and parts only IBM uses (Carbon tile, notice), in folders such as `deck/` and `diagram/` | the IBM context |
| a subject, such as `pkit` | what each of pkit's concepts maps to (agents → `category-3`), and the project's logo; roles only, no values | the project the work is about |

A presentation says `uses: {context: ibm/deck, subject: pkit}`. `ibm/deck` and `ibm/diagram` are named entry points into one library, so "IBM Deck" can still be named and shared.

The rules:

- **One version per library.** A library is split only when a real second user needs part of it alone. Old versions stay as tags, so splitting later is cheap.
- **A raw value is a literal colour, font or image file.** Only a context holds raw values. Geometry is not a raw value.
- **The frame is an interface.** The core names the layouts and their slots. Every context supplies each of them, with the same parameters, and a check confirms it. A context never replaces a core component by name: it supplies the frame and adds its own parts. Quarto works this way for PowerPoint templates.
- **Switching the context reports every name the new context lacks**, such as a Carbon tile the presentation used.
- **The core's names carry no brand.** A width is a fraction or a named width, not `span.16`.

Left for other points: where a library lives and how it is shared (point 4i); fonts, the type scale per discipline and the output scale (point 5).

**Options now on the table.**

1. The revised recommendation.
2. Ordered layers (C2): a presentation lists a stack, `uses: [core, ibm, pkit]`, and for each name the later layer wins; a check reports every name overridden. One simple mechanism, but a context may replace any core piece, so a fix to the core can be shadowed.
3. The first recommendation.

**The over-fitting check (31 October).** The maintainer asked whether the critic, working from the two talks, over-fitted the proposal to them. The agent tested each part against use cases 9 to 12.

Parts that hold beyond the talks:

- One library per owner, one version each. It does not depend on a discipline.
- Values apart from structure, with components bound to roles.
- The subject as its own axis. It holds even more for documentation than for talks: Structurizr styles elements by tag, so the model says what an element is and the styles say how it looks, and its icon themes (such as AWS) are libraries of that kind.
- A neutral context; a context switch that reports what is missing; splitting a library only when needed.

Four parts were shaped by the talks, each with its correction:

1. **The core was the only home for structure.** A documentation team wants components of its own with no brand: a callout, a figure with a caption. Correction: anyone may publish a structure library. A name is read with its library (`core/card`, `docs-kit/callout`), so no library replaces another's piece. This settles overriding for every library, not only the core.
2. **The frame's interface was the deck's.** Cover, section and slide are slide words. A doc figure's frame is a caption and a number; a poster has one page. Correction: each top component (deck, figure, poster) declares its own named layouts, and a context's entry point (`ibm/deck`) supplies those of its discipline only. A context that only serves documentation supplies no slide layouts.
3. **"A raw value is a colour, font or image" was too narrow, and inconsistent.** It came from the grid problem. A context also sets spacing, corner radius and border widths, and the subject's logo is an image. Correction: a context gives values to tokens of any type (colour, font, size, spacing, picture). A component uses a token for anything a context may change. A subject's own marks (logo, icons) are its assets. Images that are content, such as a screenshot in a doc, belong to the material.
4. **The subject mapped concepts to colours only, one subject at a time.** Diagrams also mark concepts by icon and shape, and colour alone should not carry meaning. Correction: a subject maps a concept to roles of any kind (colour, icon, shape), and a piece of work may name several subjects.

**Found outside 4g.** Point 4d's lifecycle (drafting, delivered, reused) is a talk's. A doc figure is never delivered: it follows its page, and may be locked per release of the docs. Taken up as point 4j.

**Outcome (31 October).** The maintainer chose the revised recommendation with the four corrections. Put together:

- **Libraries by owner, one version each.** Point 4d stands. A library is split only when a second user needs part of it alone.
- **A library holds one of three kinds of content:**
  - **Values.** A context, such as IBM, DAM, or the neutral one the capability ships, gives values to tokens of any type: colour, font, size, spacing, picture, in each of its modes (light, dark). It also holds its frame (the named layouts of each discipline it serves) and the parts only its brand uses.
  - **Structure.** Components, and each discipline's top component with its named layouts and their slots. The capability ships the core; anyone may publish another, such as a docs team's `docs-kit`. A component uses a token for anything a context may change.
  - **Meaning.** A subject, such as `pkit`, maps each of its concepts to roles (colour, icon, shape) and carries its own marks (logo, icons).
- **A name is read with its library** (`core/card`, `docs-kit/callout`). No library replaces another's piece.
- **A context's entry point** (`ibm/deck`, `ibm/diagram`) supplies the named layouts of its discipline. A check confirms each is there, with the same parameters.
- **A piece of work names** its context's entry point, its subjects, and any structure libraries beyond the core, for example `uses: {context: ibm/deck, subjects: [pkit], libraries: [docs-kit]}`.
- **Switching the context reports** every name the new context lacks.
- **Images that are content belong to the material.**
- **Left to other points:** where a library lives and how it is shared (point 4i); fonts, the type scale per discipline and the output scale (point 5); the lifecycle of work that is never delivered (point 4j).

### 4j. Work that is never delivered (31 October)

**The question.** Point 4d has three states: drafting follows the latest libraries, delivered is locked, reused is upgraded on purpose. A figure in a doc page (use case 9) is never delivered. It lives as long as its page, in git, and the docs may be released in versions. When a library changes, should the figure change?

**The agent's recommendation.** Every piece of work has a lock: the exact versions of the libraries it used. The states differ only in who moves the lock. A fourth state, living, is added:

| State | Who moves the lock |
|---|---|
| Drafting | Every render moves it to the latest. |
| Delivered | Nobody. It is frozen, with its exports. |
| Living (new) | When a library releases a version, the tool proposes moving the lock, with a before-and-after preview of each figure it changes. The proposal is accepted like any other change. |
| Reused | A person, on purpose, with a preview. |

Why:

- **A published page does not change without anyone looking.** A shared component's change reaches the docs only through a reviewed change.
- **An old release of the docs renders as it was.** Its lock is in git, at that release.
- **The docs do not drift away from the current look.** Every library release brings a proposal, so the figures keep up.
- **A text edit and a library change stay apart.** Re-rendering a page after its text changed does not pull in a new library at the same time.

**The alternative.** Living work follows the latest, as drafting does, and a check after each library release reports what broke. It is simpler, but a library change reaches published pages unreviewed, and an old release of the docs no longer renders as it was.

**Outcome (31 October).** The maintainer agreed: every piece of work has a lock, and a fourth state, living, moves it through a proposed change with a before-and-after preview. He then asked how a library is released and taken in at all (point 4i), which may refine where the lock lives.

### 4i. How a library is shared and upgraded (31 October)

**The maintainer's view.** Someone gives you a link to their library. That connects your copy to theirs, and commands upgrade your copy when a new version exists. It sounds like npm packages. It should not be over-engineered, but taking in new versions must be easy.

**What pkit already decides.** Content shared between repositories is pulled whole from a git source, pinned to a version; an upgrade is moving the pin; sync brings the copy to exactly the pinned content, never by merging; the copy has one owner, the source; there is no registry (COR-041, realised by ADR-040). COR-041 names "a company house-style shipped as one" capability as a use, and prefers reusing the capability to inventing a new kind of artefact. The same content is incubated in its author's repository (COR-031) and pulled by everyone else. The compatibility gate reads the fetched package, and a source that cannot be reached warns loudly and never stops the command. The code knows the `externally-sourced` origin, but the fetch from a git source does not appear to be built yet.

**The agent's recommendation.**

- **A shared library is a capability, pulled as externally-sourced content (COR-041).** The visual-work capability defines a point that libraries contribute to (COR-053), so installing `ibm-visual` makes its libraries available.
- **The author** keeps the library in a repository of their own, incubated there. A release is a version tag through pkit's release flow. A breaking change ships a migration that rewrites the consumers' material where it can, such as a renamed component, as every capability's breaking change must (COR-010).
- **The consumer** adds it by its link and a version, and `pkit capabilities upgrade <name>` moves the pin. Before anything is written, the visual-work capability shows the before-and-after of every living piece the move changes (point 4j). Delivered pieces do not move.
- **A library used only in its own project** is a folder there: no package, no pin.
- **No registry, and one compatibility range.** A library says which major version of the visual-work capability it fits (`requires_capabilities`), checked when it is added and upgraded.
- **What this means for the lock (point 4j).** A project holds one copy of each library, at its pin. Drafting and living work follow the project's pin, and moving the pin is the reviewed change of 4j. A delivered piece's lock is the commit where it was delivered: git keeps the library's copy as it was then, so the piece can render again from there.

**The alternative.** The visual-work capability keeps its own list of libraries (a link and a version each), with its own fetch and upgrade commands, following COR-041's rules. It is lighter per library, with no package file, but repeats what pkit already decides for capabilities: fetching, sign-in, the pin, the compatibility gate, loud failure, migrations and release.

**The maintainer's objection (31 October).** A library should not be on the same level as a capability. The capability is the system being designed; libraries are that system's data. The agent agrees:

- A capability is a discipline of the method, with its decisions, skills, agents and scripts (COR-017). A library is content the capability's engine reads, as an issue is to project management, or a use case to software analysis.
- The "company house-style" that COR-041 names is a house style of the method (its rules and conventions), not a set of colours and components.
- A library's author, perhaps a designer, should not need a package file, changesets and pkit's release flow to publish a version.

So the recommendation moves to the alternative: libraries are the visual-work capability's data, with a list of their own, kept by the capability's commands. They follow COR-041's rules of sharing (pulled whole, pinned, upgraded by moving the pin, never merged, no registry), without its container. The critic's review, running when the objection came, is folded into the revised recommendation.

**The critic's review (31 October).** It confirmed that the fetch from a git source is not built: `manifest.py` says so. Its main finding: a capability gives one version per project, which is right for code but wrong for data that pieces lock to. Its findings:

1. **One pin per project quietly replaced the lock per piece (4j).** A new version that improves figure A and breaks figure B cannot be taken for A alone. A typo fix in a delivered talk renders with the new libraries. Docs kept as a folder per version (as Docusaurus does) render their old figures with today's libraries.
2. **The core escaped the preview.** It ships inside the capability, so a pkit upgrade taken for something else would restyle every figure, with no before-and-after.
3. **The migration sentence was wrong.** Content pulled from an external source runs no migrations (COR-059 point 3). Rewriting a project's own content is a separate operation with a reviewed diff (COR-059 point 10). And 4d said a note per breaking change is enough.
4. **"Reuse what pkit has" rested on what pkit does not have:** no fetch, no install from a link, no upgrade to a new version, and no tag for a release of a component alone.

It also found gaps:

- The preview had no mechanism before the upgrade writes.
- An edit taken back from a board (point 3) cannot be written into a library copy owned by its source.
- Nothing says a new version exists.
- project-kit's own build ships everything under `.pkit/capabilities/`, so a library it consumes there would ship to every adopter.
- A library made in the project had no version for a lock to name.
- A brand's own published tokens file could not be used without wrapping it.
- A palette should not declare compatibility with pkit's backbone, only with the visual-work format.
- A lock that names a commit is fragile (squashed branches, dirty trees), and loses the readable `uses: {core: 1.3.0, …}` line.

Its recommendation (CA1): copies kept by version, with a lock per piece, owned by the visual-work capability.

**The agent's revised recommendation.** The critic's CA1, which the maintainer's objection also points to.

- **A library's version is a folder.** Each version that a lock names is a read-only folder, `<library>/<version>/`. It is fetched whole at its tag, never edited, and checked by a hash. The folders are committed, so rendering needs no network and CI needs no sign-in. They live in the project's own tree, never under `.pkit/capabilities/`, so project-kit never ships a library it only uses.
- **A project's list of libraries** is one small file: each library's link, and the versions present.
- **Each piece's lock names versions,** readably: `uses: {core: 1.4.0, ibm: 2.0.0, pkit: 1.1.0}`. Drafting work moves to the newest version present at every render. Living work moves through the preview. Delivered work never moves. Old versions stay as long as a lock names them.
- **A release is a git tag** in the author's repository, `<library>/v<version>` where a repository holds several libraries.
- **A library's own file** gives its name, its version, and the one number of the visual-work format it fits.
- **The commands** (working names):
  - `add <link>` fetches a version into its folder and lists the library;
  - `outdated` lists libraries with newer tags (read-only);
  - `upgrade <library>` fetches the new version beside the old, renders each living and drafting piece with both, shows the before-and-after, and moves each accepted piece's lock. A piece may stay behind;
  - `prune` removes versions no lock names.
- **The core's versions also sit side by side** inside the capability. A pkit upgrade adds a version and moves no lock.
- **A breaking change ships a note.** On request, a command rewrites the material to follow it, and the diff is reviewed like any change. No migrations, as 4d decided.
- **Taking back edits (point 3)** never writes into a fetched library. It reports the edit and names the library's repository, or offers to make it a one-off in the piece.
- **A library made in the project** has a version too. Sharing it means tagging its folder in a repository, and its name stays.
- **Later, when needed:** a brand's own tokens file (W3C format) used through a small file that maps its tokens to roles; and the fetch as a pkit primitive, if pkit builds ADR-040's fetch, which visual-work would then use.

**The alternatives now.**

1. Versioned copies with a lock per piece (above).
2. One copy per library at a project-wide pin. It is simpler, but it gives up the lock per piece of 4j, and all pieces move at once.
3. Git submodules: the "clone linked to its remote" feel, but one version per path, extra steps for cloning and CI, and validation cannot see inside them.

**Outcome (31 October).** The maintainer chose versioned copies with a lock per piece. Libraries are the visual-work capability's data, not capabilities. Each version a lock names is a read-only folder, fetched whole at its tag and committed; each piece's lock names its versions; `add`, `outdated`, `upgrade` (piece by piece, after a before-and-after) and `prune` keep them. It refines point 4j: the lock is per piece, and an upgrade may leave a piece behind.

### 4h. The scene and its primitives (31 October)

**The question.** Between the engine and the renderers sits the scene: what the engine computed, which every renderer draws. What does it hold, which primitives does it use, and what happens when a renderer cannot draw one?

**What the Friday talk showed.** Mural has no monospace font, so the generator drew every terminal and code chip as an image (`gen.py`). Mural's API cannot update an area, so a changed area is rebuilt. Mural's shapes come in few kinds.

**The agent's draft recommendation.**

- **The scene is a tree.** Its inner nodes are component instances: the component's name, its library version and its options. Its leaves are primitives, with their final position (relative to their parent) and size. A renderer with components of its own, such as Mural's masters or Figma's components, can map an instance to one; the others draw the leaves.
- **A component may mark itself a page,** such as a slide or a poster. Outputs such as a PDF cut by pages (point 13).
- **Each value keeps its token beside it,** such as `@accent = #8a3ffc`. A renderer with variables (Figma) can bind the token, and the import (point 3) can tell an off-theme colour.
- **Each leaf carries its trace:** the piece, the path of instances down to it, the part, the material field it shows (if any), and which of its values were computed and which were given. Point 3's import reads it.
- **A small set of primitives to start:** box (rectangle, rounded corners, fill, border), ellipse, text (the box it wraps in, its font role, size, colour, alignment), line (points, heads, straight, orthogonal or curved, attached ends), image, and group (a container, which may clip).
- **Each renderer declares what it can draw,** primitive by primitive and property by property. Before rendering, the engine checks the scene against it and reports what cannot be drawn. A renderer may declare a fallback, such as drawing text in a missing font as an image, which the Friday talk did by hand.
- **A new primitive is a new engine tool** (point 4a), added when a real need appears, with each renderer's support declared.
- **Left to point 5:** the engine measures text to lay it out, and each renderer draws it in its own fonts.

**The alternatives.**

1. The draft above.
2. Only what every renderer can draw, with no fallbacks. The scene is then bound by the weakest renderer: HTML could never show a terminal as monospace text.
3. A rich set (paths, gradients, shadows) that every renderer must draw. Mural could not be a renderer.

**The critic's review (31 October).** It kept the core: a computed scene with final positions, a trace on each leaf, and a list per renderer of what it can draw. It found two conflicts with point 2:

- **Fonts.** Point 2 says every renderer uses the same fonts; the draft said each renderer draws text in its own fonts. If text is measured in one font and drawn in another, every box is the wrong size.
- **Native components.** Letting a renderer map an instance to its own component brings back point 2's rejected option 3: two sources of geometry. On Mural there is nothing native to map to anyway. The tool's masters are a convention of plain widgets with markers.

It found gaps, most important first:

- **The trace cannot say where a value came from.** A value may come from a material field, an option, an override, a fetched library's default, a one-off, a token or a subject. Only some of these may be written back (point 4i).
- **No stable ids.** An item found by its index gets the wrong edit after the material reorders its list. The trace must also name the language file (`slides.cs.yaml`).
- **A line's shape was left to the renderer.** Mural draws its own curve through the points, and re-routes attached arrows by itself.
- **Text had no runs.** It could not mix bold, inline code or links in one box, which docs need.
- **The fallback's cost was not weighed.** An image of text cannot be edited, taken back or searched in a PDF, and must be uploaded again on every theme switch. Mural cannot make the image itself.
- **The renderer's list covered drawing only,** not updating in place or reading back, which point 3 needs.
- **"A component marks itself a page" breaks.** A diagram is a page alone and not inside a slide; a doc figure is a fragment; a poster needs a physical size.
- **Modes.** A docs page switching to dark mode while open needs every mode's values; a mode that changes sizes needs its own scene.
- **Missing pieces:** where the last render is kept, a version for the scene format, and the same scene on every run (for the preview of 4i).
- **Missing primitives and properties:** icons that follow the theme (a tint), a path for non-rectangular shapes, draw order, meaning for docs and searchable PDFs (alt text, headings, lists, tables), rotation, border style, image fit.
- **Copies.** A widget duplicated on the board copies its trace.

Its counter-alternatives: the scene as a subset of SVG, or names that map onto SVG, with SVG as the reference renderer (C1); a renderer profile as a token axis, so the context says how monospace text looks on Mural (C2); a flat list with no instance nodes (C3, which it would not take). It also suggested that point 6 check the `demo-recording` capability's plugin interface as a renderer contract.

**The agent's revised recommendation.** The critic's lean start.

- **The scene is a tree of groups, each with a frame.** A group may say which component it came from (`core/card@1.4.0`, with its options). A renderer may wrap a group's leaves in a container of its own, but never replaces them with its own component.
- **The root says what the scene is:** the piece, its lock, its language and material file, its mode, and the scene format's version. A scene is an output unit: a set of pages, or a fragment such as a doc figure. Sizes have units.
- **Pages are declared by a top component's slot.** A deck says its `slides` slot holds pages. The same diagram is then a page alone, and part of a page inside a slide. A page inside a page is an error. How pages lie on a board is the renderer's setting.
- **Primitives:** box (radius, border style), ellipse, text, line and image, with `path` reserved. Property names map onto SVG. Draw order is tree order.
  - **Text** holds paragraphs of runs, each with a style role and maybe a link. It names the exact font it was measured with, its measured line breaks and height, and marks overflow.
  - **A line** carries its full shape: every corner, or the curve's control points. Its attached ends are hints for renderers with native connectors.
  - **An image** has a fit, and a tint by role, so icons follow the theme.
  - **Meaning** for docs and PDFs: alt text, reading order, and roles such as heading, list, table and caption.
- **Each value carries its token and its value.** A snapshot of every mode's token values travels once beside the scene. A mode that changes sizes gives a scene of its own.
- **The trace:** stable ids, made from the path of instances, the part and a key per list item, never from render order; and a source per property. The import writes only to the material and the piece's own one-offs, and reports the rest. Two board objects with one trace are a copy, to adopt or report.
- **Each renderer declares, per primitive and property,** whether it draws it, updates it in place, recreates it, and reads it back. A loss is approximated, an image, or refused. A piece may accept a known loss, so the check does not repeat it.
- **One fallback:** the part is drawn through the SVG renderer and placed as an image. The fields under it are marked as not to be taken back from that renderer.
- **Fonts:** a renderer without the measured font declares a loss and never swaps it silently. Whether a context may set fonts per renderer (C2) is point 5.
- **The scene is derived and never committed.** Each render target keeps a small record of what it last drew (ids, a hash per property, the commit), as `.state.json` does today. Ordering and rounding are fixed, so two scenes compare.
- **Two renderers to start:** SVG and HTML as the reference, and Mural.
- **Later:** native components, Figma's variables, checks of whole libraries per renderer.

**Outcome (31 October).** The maintainer chose the revised recommendation. He added that he does not understand these things deeply: he does not want to reinvent the wheel, nor to depend on a technology that does not cover the needs. He asked whether to consult the architect now. The agent agreed: the design so far is a new component with new abstractions, so the architect reviews the whole of it, with a check per layer of what existing technology could carry it (see "Architect's review").

### 17. The runtime (31 October)

**Outcome.** The maintainer chose Python, as the architect recommended. pkit and the Mural tool are Python, and pkit sync installs a capability's Python dependencies. Most visual tools run on Node (Style Dictionary, Terrazzo, elkjs, Bluefish, Satori, Slidev, tldraw), which would put it on every adopter's machine. An outside program is called only where it is one stable executable, on the path that needs it, such as rsvg-convert or Chromium for a PDF and resvg for pictures. pkit does not install them, so the capability checks for them and says what is missing, as demo-recording does.

### 18a. What a delivered piece locks (31 October)

**Outcome.** The maintainer agreed with the architect's first revision. A delivered piece locks its library versions only, such as `uses: {core: 1.3.0, ibm: 2.0.0, pkit: 1.1.0}`. The engine and the renderers ship inside the capability, and a pkit upgrade moves them (COR-017, COR-059 point 7), so no piece can lock them. The real freeze of delivered work is its exports, kept as they were handed out. A delivered piece drawn again uses today's engine with its locked libraries, and any difference shows in a before-and-after. This revises point 4d, whose example lock named `renderer-mural`.

**Options that were on the table.** Locking the engine too, which needs pkit to keep old capability versions installed, a change to pkit's own rules; and drawing a delivered piece again from the commit where it was delivered, which is fragile.

### 18b. Where the core's versions live, and what the core holds (31 October)

**The architect's revision.** The core's versions cannot sit side by side inside the capability (4i): the files are pkit's, a project cannot prune them, and the capability cannot know which versions locks name. The agent recommended copying the core into the project's library folder like any other library, the neutral context too, so a pkit upgrade brings a newer core but changes no figure until `upgrade core`.

**The maintainer's question.** Is the core only primitives, or does it bring opinions, such as a card? The agent's answer: as 4g described it, it brings opinions. (The 4g table also listed primitives and layout operators under the core; they are the engine's code, per 4a and 4h.) There are three levels:

| Level | Example | Opinion |
|---|---|---|
| Engine (code) | box, text, line, image; repetition, stack, distribute | none: the alphabet |
| Interface (data) | role names (`accent`, `surface`); the deck's layouts cover, section and slide, with slots for title, lead, visual and footer | a little, and it must be shared: it lets a piece switch from IBM to DAM. PowerPoint's layouts ("Title Slide", "Section Header", "Title and Content") are the same idea. |
| Components (data) | the card (heading on top, body below, a bar in its tone's colour), the "Limit" note, the chip, `stage` | a design choice. A context changes colours, radius and spacing, not that a card has its heading on top. |

**The agent's recommendation.** Split along this line:

- **The core holds only the interface:** role names, and each discipline's top component with its named layouts and slots. It changes rarely, and every library builds on it.
- **Opinionated components go into a starter library** the capability ships (point 8). An adopter uses it, ignores it, or uses their own instead. It may improve faster without touching the interface, and pieces lock it like any library.
- **The Friday talk's Carbon-flavoured components go into the maintainer's IBM library,** not the starter (COR-014).

**The alternative.** One core with the components: one library fewer, but every adopter carries the capability's opinions, and every change to a card changes the library everything builds on.

**Outcome of the split (31 October).** The maintainer agreed. The capability ships three libraries: the core (the interface only), the starter (opinionated components) and the neutral context (values). This refines point 4g. Where the libraries' versions live is the remaining question of 18b.

**Outcome (31 October).** The maintainer agreed with the architect's revision. The capability ships only the newest version of the core, the starter and the neutral context. Each is copied into the project's library folder (`core/1.4.0/`, `starter/1.2.0/`, `neutral/1.0.0/`), like any other library, and locked per piece. A pkit upgrade brings newer versions but changes no figure until `upgrade` moves a piece, after its before-and-after. `prune` removes versions nothing uses. This revises point 4i, which kept the core's versions inside the capability.

### 18c. How a renderer plugs in (31 October)

**Outcome.** Renderers are plugins inside the one capability, behind a clean seam, as in demo-recording: a neutral core, knowledge flowing one way, one check at each plugin's edge. The contract between the engine and a renderer is the scene, the renderer's list of what it can draw, update and read back, and its report of what it lost. Two plugins come first: SVG/HTML and Mural. This settles point 6.

The agent had suggested deciding at point 12 whether Mural might later split into a capability of its own. The maintainer ruled it out: a separate capability for Mural would make this capability miss its point, which is one system with several renderers. Point 12 therefore decides how the Mural plugin's network access and credentials reach only the projects that use it, inside the one capability.

**Options that were on the table.** A capability per renderer joined through connection points, which pkit's points cannot carry (a filler takes no input, a subscriber uses no network); and a renderer capability that depends on the engine (COR-030), split from the first day.

### 18d. Fonts per renderer (31 October)

**Outcome.** The maintainer agreed to font profiles set by the context. A font profile is the set of fonts for a group of renderers, such as `standard` (SVG, HTML, PDF: IBM Plex Sans and IBM Plex Mono) and `mural` (`proxima-nova`, since Mural accepts 12 fonts and none is IBM Plex or monospace). The context, not the renderer, sets each profile's fonts, so design stays in the logical layer. The engine computes one scene per profile, measuring text in that profile's fonts, so text fits in every renderer; the scenes differ only in measured text and box sizes. For monospace on Mural, the context chooses a substitute font (text stays editable and searchable) or the image fallback (looks right, cannot be edited); point 5 settles the details. This revises point 2's "every renderer uses the same fonts": every renderer uses its profile's fonts, which the context sets.

**Options that were on the table.** One scene with only fonts every renderer has, which lets the weakest renderer limit all; and one scene with the renderer swapping fonts, which 4h ruled out because boxes would not fit.

### 5. Text and fonts (31 October)

**What is settled already.** Text is measured by the engine with HarfBuzz and fontTools (the architect's review); the engine computes one scene per font profile, with the fonts the context sets (point 18d); a text leaf names the exact font it was measured with, its runs and its measured line breaks, and a renderer without that font declares a loss (point 4h).

**What was found (31 October).** Mural accepts these 12 fonts, asked of its API with `mural_fonts.py`: `adelle`, `blambot-casual`, `blambot-pro`, `lint-mccree`, `marker-felt`, `museo-slab`, `proxima-nova`, `shark-water`, `abc-social`, `stk-bureau-serif`, `ey-interstate`, `itc-garamond-condensed`. Most are commercial, and none is an open-licence font the capability could ship. This machine has IBM Plex installed as files, but not `proxima-nova`. So the engine can measure the `standard` profile exactly, but has no file to measure the `mural` profile with. Today's tool estimates a width as the number of characters times 0.58 of the size, and `verify` reports the boxes Mural grew past their planned height (`FIT`).

**The agent's draft recommendation.**

- **The engine fixes the line breaks.** It breaks every text into lines by the language's rules (in Czech, a one-letter preposition never ends a line), and the scene carries the lines. Each renderer draws the lines as given, with an explicit break at each, in a box a little wider than the longest measured line. A renderer never wraps text itself, so a small error in a width can no longer move words to other lines and push the boxes below.
- **Where the measurements come from, per font of a profile:**
  - a font file in the context library, where its licence allows shipping it (IBM Plex, under the SIL Open Font License);
  - a font file on the machine, where the project's people hold a licence;
  - a metrics table, for a renderer's own fonts that nobody has as files, such as Mural's. It holds each glyph's width and the line height, not the font itself. It is made once by calibration against the renderer (text pushed to Mural and its size read back), never by hand, and shipped with the renderer's plugin.
- **The check stays.** `verify` keeps reporting a box the renderer grew past its planned size, which also tells when a metrics table is off.
- **Monospace on Mural, by default:** inline code is drawn as text in a substitute font with the code style's background, so it stays editable and searchable; a terminal, whose columns must line up, is drawn as an image. A context may choose otherwise.

**The alternatives.**

1. The draft above.
2. Keep the estimate (characters times a constant) for fonts without a file, with a wider safety margin. Simple, but boxes are often too large or too small.
3. Measure in a browser that has the font, for every renderer. Exact for HTML, but heavy, and Mural's fonts are not in a browser either.

**The critic's review (31 October).** It kept the core: the engine measures, the scene carries the lines, `verify` guards. It found:

- **Fonts found on the machine break the same scene on every run** (4h) and the before-and-after (4i): two machines, or CI, would measure differently. Measure only from committed files, and refuse when a font is missing.
- **Forced line breaks on Mural damage taking edits back** (point 3). The tool writes each line as its own `<div>`, so a pulled text comes back with the engine's breaks inside it, and a person's added words wrap raggedly until the next render.
- **The draft said how text is measured, not how each renderer gets the font to draw it.** rsvg-convert looks fonts up by name on the machine and swaps a missing one silently; an SVG shown as an image cannot load outside fonts.
- **The Mural calibration rests on an untested assumption.** Only a grown height comes back from Mural, never a width, and it is not known whether Mural computes it on its server or only when a browser opens the board.
- Also: the output scale (slide, doc, narrow screen) handed over by 4g; alignment when a box is widened; how each text was measured (file, table or estimate); characters a font lacks; where the Czech rule lives (a non-breaking space after one-letter words, as the Czech TeX tool `vlna` does; Unicode line breaking through `uniseg`, pure Python); explicit line height; inline code on Mural, never tested with a background; IBM Plex's licence (ship the files unchanged with their licence; the name "Plex" is reserved for unmodified files).
- **The estimate was dismissed without evidence.** Checked the same day: `verify` on the Friday talk's board, 2,479 objects in two languages built with gen.py's estimate per kind of character, reports 6 texts estimated to wrap past their box.

**The agent's revised recommendation.** The critic's leanest start, with Mural wrapping its own lines (its C1).

- **Measure only from committed files.** A context library commits its font files, unchanged with their licence (IBM Plex), or a widths file: taken from a licensed font with fontTools, from a calibration, or an estimate. Never a font found on the machine; a missing font refuses the render. The scene records how each text was measured: a file and its hash, a table and its date, or an estimate.
- **The engine breaks lines** with Unicode's rules (`uniseg`) plus each language's rules, kept as data in the engine: in Czech, a non-breaking space after each one-letter word. It breaks against the planned width minus a small margin and draws in the planned width, so centred and right-aligned text stay put. A word longer than its box breaks after a `/` or is marked as overflowing. No hyphenation and no justified text at first.
- **Per renderer:**
  - SVG, HTML and PDF draw the engine's lines, in the library's fonts: embedded or linked in SVG, loaded by HTML from the library, and rsvg-convert and resvg pointed at the library's font folder with system fonts off. A check fails when the drawn font is not the measured one.
  - Mural gets the measured width minus the margin and wraps the text itself. The non-breaking spaces keep the Czech rule, and edits come back as clean text: the import turns them back into ordinary spaces. Mural draws text in text boxes, never inside shapes.
- **Mural is measured by estimate at first:** widths per kind of character, as gen.py does, recorded as "estimated" and guarded by `FIT`. A calibrated table is built only if `FIT` keeps firing.
- **Every character is checked** against its font or table, and a missing one is reported.
- **Line height is explicit** in the scene, and every renderer uses it.
- **Monospace on Mural, by default:** inline code in a substitute font or colour, with no background, declared as a loss; a terminal as an image. The default lives in the neutral context's font profile, not in the Mural plugin.
- **Named, not built yet:** the output scale (slide, doc, narrow screen) as an axis giving a scene of its own, like a font profile; calibration; hyphenation; backgrounds for inline code.
- **First, a short Mural test:** whether a grown height comes back with no browser open; whether a line break stays apart from a paragraph after a person edits; whether `&nbsp;` is kept; whether part of a text can have a background.

**The alternatives now.**

1. The revised recommendation.
2. Every renderer, Mural too, draws the engine's lines. Exact on Mural within the margin, but edits taken back carry the breaks, and an edited line wraps raggedly.
3. Build the calibrated Mural table first. More exact than the estimate, but it rests on the untested assumption, and the estimate left 6 warnings on 2,479 objects.

**Outcome (31 October).** The maintainer agreed to the revised recommendation: the lean start, with Mural wrapping its own lines within the measured width.

### 19 and 20. References between elements, and format numbers (31 October)

**19. The question.** Point 4a's formulas see an item's index, the count and the tokens, but not another element's measured size. So a card's body cannot start under a heading that wrapped to two lines, and a note cannot sit under the tallest of three cards. Today's tool has such references one by one (`anchor`, `align: <slot>`, `wrap: <part>`, `below: <instance>`).

**19. The agent's draft recommendation.** References between elements, kept local:

```yaml
card:
  parts:
    heading: {text: "{title}", x: 24, y: 24, width: =root.width - 48}       # height: measured
    body:    {text: "{body}", x: 24, y: =heading.bottom + @space.04, width: =heading.width}
  root: {height: =body.bottom + 24}
```

- **A formula may read another element's computed frame** (`x`, `y`, `width`, `height`, `right`, `bottom`, `center`), but only inside the same component: its own parts, and the outer frames of the components in its slots. Elements in different components line up through their parent's layout operator (stack, align, distribute, equal heights), never by reaching across.
- **One owner per value** (Bluefish's rule). Each of an element's `x`, `y`, `width` and `height` is set by exactly one thing: the component, the measured text, or the parent's layout. A second writer is an error.
- **The engine orders the computation by the references,** and refuses a loop (A's height from B's, B's from A's), naming the loop.
- **The formula language stays closed:** numbers, the four operations, parentheses, tokens, index, count, `min`, `max`, `round`, and now references to frames.

**19. The alternatives.**

1. The draft above.
2. A constraint solver, such as Cassowary (behind Apple's Auto Layout): relations are declared and a solver finds the positions. Powerful, but results are hard to predict, and a conflict is hard to explain.
3. Layout operators only, no references: simpler, but no "a note under the tallest card" or "an arrow from this box's bottom".

**20. The question.** A breaking change to a file's format cannot be migrated inside a fetched library (read-only) or a delivered piece (frozen), so pkit's usual migrations (COR-010) cannot reach them (the architect's fit issues 7 and 8).

**20. The agent's draft recommendation.**

- **Every file the capability reads carries its format number from its first commit:** material, component, library, context, subject, lock (for example `format: 1`).
- **The engine reads every format number it ever shipped.** An old file is converted in memory when it is read, never rewritten on disk. A project's own files may be rewritten to the new format on request, with the diff reviewed (as point 4i decided for breaking library changes).
- **A library declares the format it was written for,** and that number also covers the engine tools it uses: a library using a tool added in format 3 says `format: 3`, and an older engine refuses it with a clear message.
- **The scene has a format number of its own**, which each renderer declares it reads (point 4h).

**20. The alternatives.**

1. The draft above.
2. One version number for the whole capability, named in each library: simpler, but a library would have to change whenever anything in the capability changes.
3. No format numbers until the first breaking change: the first change then has to guess which files are old.

**The critic's review of 19 (31 October).** The idea holds (read computed sizes, one owner per value, refuse loops), but:

- **The draft's own card broke its rule.** The card sets its height, and a row with equal heights sets it again: two writers. Yet gen.py takes the tallest item in about seven kinds (`wired`, `sockets`, `why_row`, `board`, `answers`, `code2`, `roles`). Fix: each element has the size it asks for (from its content) and the size it gets (from its parent, by default what it asked for), as Flutter and CSS do. The one-owner rule applies to the size it gets.
- **An arrow could not reach a part inside another component.** `sockets` draws arrows to slots two levels down inside the provider box, and use case 10 needs relations between parts of different containers. Today's tool allows it. Fix: a component marks some parts as public anchors, which an ancestor may read at any depth, never sideways or upward. The reason for locality, unstated in the draft: a component's inner parts stay private, so a library can change them without breaking anyone.
- **Gaps:** compute value by value, like spreadsheet cells, so a parent's width and a child's measured height are no loop; make a text's natural width (on one line) readable; reach the tallest, the first or last, or a keyed item of a list; say what a missing part and a division by zero give; rows lining up across sibling cards (a later operator, like CSS subgrid); report overflow per scene, never shrink text; with references, the scenes of two font profiles differ in positions too, which rewords 18d.
- **Counter-alternative:** list operations ("the tallest", "the item with this key", alignment) belong in layout operators, keeping formulas to arithmetic plus reading a frame, so the grammar stays small.

**The agent's revised recommendation for 19.**

```yaml
card:
  anchors: [heading, body]                 # public: an ancestor may point here
  parts:
    heading: {text: "{title}", x: 24, y: 24, width: =root.width - 48}
    body:    {text: "{body}", x: 24, y: =heading.bottom + @space.04, width: =heading.width}
  asks: {height: =body.bottom + 24}        # what it asks for; its parent may give more
row:
  layout: {stack: across, equal: height}   # gives each card the tallest card's height
```

- **Two sizes per element:** the size it asks for and the size it gets. One owner per value applies to the size it gets. A part reads the size its container gets.
- **What a formula may read:** its own component's parts, and the public anchors of components below it, at any depth. Never sideways, never upward. Renaming or removing a public anchor is a breaking change, with a note (4i).
- **Lists through layout operators:** stack, align, distribute, equal sizes, and a list item by its stable key, the first or the last. Formulas stay arithmetic plus reading a frame, including a text's natural width.
- **Computed value by value,** in the order the references give; a loop is refused, naming it.
- **Missing and impossible values:** a missing part has zero size at its place; dividing by zero is an error naming the formula.
- **Overflow** is reported per scene, never fixed by shrinking text.
- **Later:** rows lining up across sibling cards; baselines.

**Outcome of 19 (31 October).** The maintainer agreed to the revised recommendation: two sizes per element, public anchors, and list operations as layout operators. With references, the scenes of two font profiles differ in positions too, not only in measured text and box sizes (a rewording of 18d).

**The critic's review of 20 (31 October).** Numbering from the first commit is right, but the draft built a second versioning system beside pkit's. pkit data files carry `schema_version`, which `pkit data validate` checks (COR-023). The maintainer's content-conversions design (`2026-10-09-content-upgrades.md`, decided 10 October, filed as #1431 to #1445, not yet a record) already covers reading an old format through an optional conversion, a reviewed rewrite of a project's own files, and validation over a range of versions. Also: one number for the whole format, not one per kind of file (4i already says so); the list of files was wrong (W3C token files, fonts and images cannot carry it); "reads" is not "draws the same" (18a: the exports are the freeze); an edit taken back into an old file should be refused, naming the conversion; and the lowest format a library needs can be computed from the tools it uses and checked against what it declares.

**The agent's revised recommendation for 20.** Use pkit's own version field, and line up with the content-conversions design without building on it as authority until it is a record.

- **Each file of the capability's own format binds to its schema the pkit way,** with `schema_version` (COR-023), so `pkit data validate` and editors check it. W3C token files, fonts and images carry no number: they are in other formats.
- **The capability's schemas share one version number,** raised together on a breaking change, because the files refer to each other. A library's file names that number, and the engine checks it against the lowest number the library's tools need.
- **A breaking change ships a converter from the previous version.** Converters chain (1 → 2 → 3), convert shapes only, and keep sample files of each old version in the tests. The engine converts in memory when it reads a fetched library folder, which it never rewrites. A project's own files are rewritten on request, as a diff a person reviews, the files that share keys together (`slides.yaml` with `slides.cs.yaml`). That is the content-conversions design's optional conversion.
- **Reading an old file is not drawing it the same:** today's engine may draw it differently; the exports stay the freeze (18a).
- **An edit taken back into a file of an old version is refused,** naming the conversion, so an edit and a format change never mix.
- **What is needed from pkit:** validation that accepts a range of versions, from the content-conversions arc (#1431 to #1445). It is not needed until the first breaking change; version 1 needs nothing new.

**The alternative.** The capability's own `format:` field, outside pkit's data binding, with its own validation. Independent of pkit's plans, but a second versioning system, without pkit's validation and editor support.

**The maintainer's question (31 October).** Would semver be better, since it says whether a change is breaking? The agent's answer: semver's information is wanted, and it already has places in pkit; a semver string in the format field would leave pkit's convention, where `schema_version` is an integer that validation compares exactly (`.pkit/schemas/README.md`). The three numbers, each with one job:

```yaml
# ibm/2.0.0/library.yaml
version: 2.0.0                  # the library's content, semver: major removes or renames, minor adds, patch fixes
schema_version: 1               # the shape of the files: rises only on a breaking change, the format's major
requires: {visual-work: "1.4"}  # the oldest capability release with the tools the library uses, the format's minor
```

- **A breaking change to the shape** raises `schema_version` and ships a converter.
- **An additive change,** such as a new engine tool or a new optional field, leaves `schema_version` alone. It arrives in a minor release of the capability, which pkit already versions in semver through changesets (PRJ-002). A library that uses it names that release in `requires`, which the engine computes from the tools used and checks against the declaration.
- **The library's own version** stays semver, as 4i decided. For pictures it is a signal, not a promise: the lock and the before-and-after protect each piece whatever the number says.

So the format's major and minor are carried by `schema_version` and `requires`, the split Rust uses (its edition and its `rust-version`), without a second versioning scheme.

**Outcome of 20 (31 October).** The maintainer agreed: pkit's integer `schema_version`, one number shared by the capability's schemas, rising only on a breaking change, with a converter; `requires` naming the oldest capability release whose tools a library uses, computed and checked by the engine; semver for each library's content. The rest of the revised recommendation stands: converters chain, fetched folders are converted in memory, a project's own files are rewritten on request as a reviewed diff, and an edit taken back into an old-version file is refused.

### 21 and 22. An escape for hand-drawn one-offs, and graphs (31 October)

**21. The question.** Point 4a makes every one-off data. The Friday talk's 38 one-off diagrams were most of its work, written as Python in `gen.py`. If writing a one-off as data is slow, people go around the tool: the architect's largest risk to the product. No escape is decided for something drawn by hand.

**21. The agent's draft recommendation.** Data stays the norm, with two escapes that need no code:

- **A foreign drawing.** A part that shows a drawing made elsewhere (Figma, Inkscape, Excalidraw, draw.io, a scan), as an SVG file or an image beside the material. It is drawn as given in every renderer (on Mural through the image fallback). An SVG may use the role colours through CSS variables or `currentColor`, so a theme switch reaches it; otherwise it is declared as not following the theme. Its trace names its file but no fields, so the import reports an edit to it instead of taking it.
- **A reserved area.** On an editable renderer, the engine draws an empty, labelled frame and leaves what is inside to people, such as a workshop's sticky notes on a slide. The import never takes what is inside, and a push never touches it, as today's tool already refuses to rebuild an area with hand-made content. Other renderers draw the empty frame, or a picture cut from the board's export (as `export_pdf.py` cuts slides).
- **The designer agent writes one-offs as data** (point 9). In the Friday talk the agent, not the maintainer, wrote all 38 in `gen.py`. The first slice measures whether `pyramid` and `sockets` are shorter as data than as code; if not, the engine lacks a tool.

**21. The alternatives.**

1. The draft above.
2. Code as an escape: a one-off as a Python function in the piece, producing scene elements. Fast to write, but it breaks 4a (kinds are data), cannot be checked by a schema, and runs a project's code inside the engine.
3. No escape: everything is data. The purest, and the largest risk.

**22. The question.** Use case 10 (several views of one system) needs graphs laid out automatically, which arithmetic cannot do. The architect named two ways: a graph-layout tool in the engine (ELK), or relation graphs left to Mermaid, as software-analysis does (its DEC-003). ELK runs on Java or JavaScript, which point 17 (Python, no Node) rules out as a library.

**22. The agent's draft recommendation.** Graphs are out of the first slice, with the door kept open: when a real graph is needed, graph layout becomes an engine tool that calls Graphviz (`dot`), one stable outside program on the path that needs it (point 17). Graphviz returns node positions and edge routes, which go into the scene, styled from the tokens like any other part, so a graph renders to Mural too. Mermaid stays software-analysis's way of showing its own analysis graphs, outside this capability.

**22. The alternatives.**

1. The draft above.
2. Graph layout now, with Graphviz, in the first slice: use case 10 proved early, at the cost of a larger slice.
3. Relation graphs always left to Mermaid: no layout to build, but no tokens, no Mural, no trace.

**The critic's review of 21 (31 October).** The two escapes did not match the evidence. The critic read every one-off in `gen.py`, about 19 per language: none was drawn by hand or in another tool. Each is code placing boxes from the material.

- **About 14 are arrangements** (rows, columns and grids of cards and terminals with equal heights: `map` ×3, `wired` ×4, the card row, the caption, `files`, `answers`, `roles`, `slice`, `board`), which the tools of 4a and 19 cover.
- **3 are connector diagrams** (`sockets`, `ties`, `ideas`), which spread connectors and public anchors cover.
- **A few need a tool nobody has decided:** a part shown only when its field is given (the optional "why" rows, in about six kinds); a terminal placed so its first line is level with a marked step (`checklist`); a file tree (`install`); colours stepping by position (the pyramid's purple ramp, raw values in the material today).
- **None needs a foreign drawing.** The only outside drawings were Carbon icons, which 4h's tinted image covers.

So the real risk is "my one-off needs a tool the engine lacks", which "the agent writes them as data" hides: an agent then types fixed numbers (which break in Czech and in the Mural profile) or writes a script nobody governs, and an adopter cannot add a tool at all (4a). Also:

- **The reserved area does not work.** On Mural a slide is an area, and an area with hand-made content cannot be rebuilt, so one sticky note freezes the whole slide. A picture cut from the board needs Mural's sign-in and network on every render, against 4i. No use case asks for it.
- **The foreign drawing is mostly decided** (4g: content images belong to the material; 4h: an image has a fit and a tint). CSS variables reach an SVG only when it is inline in the page; Figma and Inkscape export fixed colours; text inside it cannot be translated, and fails point 5's font rule unless outlined.
- **The slice tests only the easy kinds** (`pyramid`, `sockets`). It should include the hardest (`install`'s tree, `checklist`, `board`, a `map` with its optional row), and count the tries an agent needs for a one-off it has not seen, in both languages and both font profiles.

Counter-alternatives: a one-off generator run while authoring, never by the engine, whose output is a normal one-off component, committed and checked, with a fingerprint saying when it is stale (A); a drawing turned into data by the import, its text into material fields and its colours to the nearest roles (B); hand nudges as a layer keyed by stable ids (C, which changes point 3).

**The critic's review of 22 (31 October).** Graphviz would run before the scene is made, not after it: its version and its own text measuring would change the scene between machines, against point 5 and 4h. Its curves need a stated loss on Mural. `dot` cannot pin a node. Deferring graphs defers the wrong half of use case 10: what is missing is one model that several pieces read, not automatic layout. Counter-alternatives: run Graphviz while authoring and commit its positions, keyed by a hash of the graph and the Graphviz version (A); a small layered layout in Python (B); hand-placed views over a shared model first (C).

**One rule across both** (the critic's): what the engine's closed set of tools cannot compute may be computed outside, while authoring, and committed as data with a check that it is fresh. It held in seven cases tested, except where the output holds fixed numbers, which break in Czech and in the Mural profile: the output must use references, or be made once per language and profile.

**The agent's revised recommendation for 21.**

- **The risk is a missing tool, not hand drawing.** Add the few tools the talk shows are missing: a part shown only when its field is given; a text's lines as readable frames, so another part can line up with one line; a tree layout operator; and colour by position through a role ramp (`level-1` … `level-n`), not raw values.
- **The sanctioned escape is an authoring-time generator** (the critic's rule). A person or the agent runs it while authoring; the engine never runs it. Its output is a normal one-off component in the piece: committed, checked by the schema, no raw values, text taken from material fields, with a fingerprint of its inputs that says when to run it again. Its output uses formulas and references, not fixed numbers, so it fits every language and font profile. Generators never go into libraries, since one-offs are never shared.
- **A drawing made elsewhere is a content image** (4g, 4h): one file per language, with alt text; its text outlined or in the library's fonts, which a check confirms; reported at every theme, mode or context switch, since it does not follow them.
- **The reserved area is dropped.** Workshops on a board would be a use case of their own.
- **Later:** turning a drawing into data through the import (B), and hand nudges as a layer (C, a change to point 3).
- **The first slice adds the hardest one-offs** (`install`'s tree, `checklist`, `board`, a `map` with its optional row), and measures the tries an agent needs for a one-off it has not seen.

**Outcome of 21 (31 October).** After the agent explained each tool on the talk's own slides, the maintainer agreed:

- **Four tools are added to the engine:**
  - an optional part, shown only when its field is given (the "why" panel of "Where skills come from": `when: why`);
  - lining up with one item of a list or one line of a text (the terminal level with the marked step of "One skill, step by step": `=steps[mark].middle`);
  - a tree (folders indented by depth, coloured by owner, joined by lines, as `gen.py`'s `tree()` drew them);
  - a colour ramp by level (`level-1` … `level-n` roles with readable text colours, replacing the pyramid's raw values).
- **Helper scripts are allowed while preparing, never run by the engine.** For a picture no tool can build, such as the cycle ring (a circle needs sine and cosine, which the formula language lacks), a script writes an ordinary one-off component beside the material. It is checked like everything else: no raw colours, text from the material, positions as formulas relative to the frame, and a fingerprint of its inputs that says when to run it again. A script needed again and again becomes a tool (about three uses, 4c).
- **A drawing made elsewhere is a content image,** one per language, reported at every theme switch.
- **The reserved area is dropped.**

**The agent's revised recommendation for 22.**

- **Automatic graph layout follows 21's rule.** When a graph is needed, a helper runs while preparing (Graphviz, or a small layered layout in Python), never inside the engine. The engine gives it each node's measured size; it writes the positions into a committed file, with a fingerprint of the graph, the helper's version and the font profile, one file per profile. Lines are straight or right-angled, which Mural draws as given; a curve is declared as a loss on Mural. A person may move a node in that file.
- **A shared model is a file of its own.** For several views of one system (use case 10), the system's elements and relations live in one material file, and each view names the elements it shows by their stable ids and places them, by hand with the layout tools or through the helper. A view never holds facts the model lacks, so a fact lives in one place. The model is the project's own file: a change to it is reviewed like any change, and drafting and living views follow it.
- **Mermaid stays software-analysis's,** for the analysis's own diagrams (its DEC-003). A project's docs then show two looks, which is an accepted cost. Reading a model from where its facts already live, such as the analysis, comes later.
- **Not built in the first slice.** The principle is fixed now, so the formats leave room for it.

**The alternatives.**

1. The revised recommendation.
2. Graph layout inside the engine, calling Graphviz at every render: the scene would change with Graphviz's version and its own text measuring, between machines and in CI.
3. Relation graphs always left to Mermaid: nothing to build, but Mermaid's command-line renderer needs Node (point 17), it lays out by itself (the architect's trap), and it cannot feed Mural.

**The maintainer's addition (31 October).** He leans to yes, and wants, in the end, to connect visual-work to software-analysis, so that all of the analysis's diagrams and visuals are drawn by visual-work, in the style of the selected libraries. software-analysis would then declare an interface, a contract: the kinds of visual it needs drawn, and constraints such as the output format and the smallest and largest sizes. Preparing a library that covers the whole contract could take a while, so a connection must work in an incomplete state: where the library lacks a kind the analysis needs, nothing fails, and that diagram is drawn the old way. No integration now, but the design should count with collaboration between capabilities and a protocol for it.

**The agent's recommendation for the addition.** One mechanism, a contract, of which the frame (point 18b) is already the first case:

- **A contract is a list of named kinds,** each with the schema of the data it receives and its constraints (output formats, smallest and largest size, modes, accessibility). software-analysis's would hold its four diagrams (its DEC-003): the use-case diagram, a journey's flow, the requirement map and the chain of use cases.
- **A library declares which kinds of a contract it implements,** and with which component, as a context supplies the core's named layouts.
- **Coverage is reported, never assumed.** For example: "software-analysis needs 4 kinds; your libraries draw 2; 2 are drawn the old way." The library grows one kind at a time.
- **A missing kind falls back to the consumer's own drawing,** which the contract names: for software-analysis, its plain Mermaid. Nothing fails.
- **The data stays where it lives.** visual-work reads the analysis's front matter through the contract; a diagram never becomes a fact's home, which matches software-analysis's own rule (DEC-003 point 1) and 22's shared model.
- **The wiring in pkit is not designed yet.** pkit's slots and connection points (COR-052, COR-053) carry data and events, not a request with input, such as "draw this from that data" (the architect's concern 3). A protocol between capabilities may need a core decision when it is built.

With that, Mermaid's look beside the libraries' look in a project's docs is a transitional state, not a permanent cost.

**Outcome of 22 (31 October).** The maintainer agreed: graphs are arranged by a helper while preparing, never by the engine, with positions committed per font profile and a fingerprint; several views share one model file, and a view never holds a fact the model lacks; other capabilities connect later through a contract, with the coverage reported and a fallback to their own drawing for any kind not covered (use case 13, point 24). Nothing of it is in the first slice; the formats leave room for it.

## Architect's review (31 October)

The maintainer asked, after 4h, whether to consult the architect. It reviewed points 1 to 4j as a whole, read-only, with a check per layer of what to adopt, wrap or build. Sources it fetched that day are named in its report; claims from its own knowledge are marked as such there.

**Adopt, wrap or build, per layer.**

| Layer | Verdict |
|---|---|
| Runtime | Python, as pkit and the Mural tool are. No Node in the first version: most visual tools (Style Dictionary, Terrazzo, elkjs, Bluefish, Satori, Slidev, tldraw) would put it on every adopter's machine. Call a separate program only where it is one stable executable, on the path that needs it. |
| Tokens | Adopt the W3C DTCG format; build a small Python reader for aliases and the Resolver. The JavaScript tools do not yet support the 2025.10 format fully. The format has no type for a picture or logo (`$extensions`, or outside the tokens). |
| Component specifications | Build: nothing existing covers parts, slots, options and formulas with geometry. Borrow Spectrum's words, Bluefish's rule (one owner per dimension), and Vega's limited expressions. Fix the formula grammar in a record, so it never grows into a programming language. |
| Material | Build on YAML and JSON Schema. Deck formats such as Slidev, Marp and Quarto know about slides, against point 4f. Every list item an edit can return to needs a stable `id` now. |
| Layout | Build repetition, formulas and small stack, align and distribute operators (flexbox's names where they match). Build only simple connector routing; never routing around obstacles (adopt libavoid if ever needed). ELK lays out whole graphs, which fits use case 10, not the talk's diagrams. |
| Text measuring | Adopt HarfBuzz (through uharfbuzz) for shaping and fontTools for font metrics; build only the line-breaking rules, such as Czech one-letter prepositions. It replaces today's estimate of a width as characters times a constant. The thinnest point of the stack: building it ourselves is the most likely mistake. |
| Scene | Build our own JSON with SVG names, as 4h decided; the SVG output carries each trace id as a `data-` attribute. tldraw's format needs a licence key; Excalidraw's is too flat. |
| Renderers | Build SVG and HTML (SVG in a page, CSS variables per mode). Wrap the Mural tool's API client, sign-in, pacing and state, fed plain objects. Defer Figma: creating layers needs a plugin run inside Figma, and variables need an Enterprise plan. Worth adding later: PowerPoint (python-pptx) and an Excalidraw file, a cheap test of point 3. Slidev, Marp and reveal.js lay out with CSS, against point 2. |
| Sharing | A thin layer over git, built once a second repository uses a library; move onto pkit's own fetch (ADR-040) when it is built. |
| Outputs | Adopt; never build a PDF writer. rsvg-convert gives a PDF with real text from SVG; headless Chromium gives a tagged PDF (headings, reading order, alt text) for accessibility. resvg for pictures (fallback images, previews, test snapshots), identical on every platform. |
| Charts | Vega-Lite later, as an engine tool, fed the context's tokens (vl-convert, no Node). D2, Mermaid, Structurizr, Typst, Penrose: not the engine. |

The trap in adopting is a tool that lays out or styles by itself (Slidev, Marp, reveal.js, Quarto, Typst, D2, Mermaid, tldraw): as the engine it would break point 2, and none could feed Mural.

**Concerns that revise decided points**, so the maintainer decides each:

1. **A delivered piece cannot lock the engine or a renderer** (4d's example names `renderer-mural: 0.9.0`). A project holds one version of a capability, and a pkit upgrade moves it (COR-017, COR-059 point 7). Only libraries lock per piece; the real freeze of delivered work is its exports.
2. **The core library cannot keep its versions side by side inside the capability** (4i). Those files are pkit's, the project cannot prune them, and pkit would ship every version forever. Copy the core into the project's library folder like any other library.
3. **A renderer cannot be a capability joined through connection points** (COR-052, COR-053). A filler takes no input and a subscriber uses no network, and a renderer needs both. Plugins inside one capability, or renderer capabilities that depend on the engine (COR-030), fit pkit as it is.
4. **Mural's 12 fonts break "one scene for every renderer"** (point 2). Compute one scene per font profile, with the context naming the fonts for Mural, as 4h does for a mode that changes sizes.

**Fit issues.**

5. Formulas cannot stack boxes that size to their text: the engine needs references between elements, with one owner per dimension and cycles refused.
6. Use case 10 needs automatic graph layout: add it as an engine tool (ELK), or leave relation graphs to Mermaid, as software-analysis does (its DEC-003).
7. A breaking format change cannot be migrated in fetched libraries or delivered pieces: every file carries a format number from its first commit, and the engine keeps reading old numbers.
8. A library's format number must also cover the engine's tools it uses.
9. pkit does not install outside programs (resvg, rsvg-convert, Chromium): the capability checks for them, as demo-recording does.

**Out of date in this note.** Point 3's second row, a master's design on the board flowing into the library, cannot happen now (4h defers native components; 4i forbids writing into a fetched library). Point 4d's example lock names a renderer. Point 4a lists four tools, but 4c's example uses stack and distribute.

**Tensions across points.**

- The import into a delivered piece changes frozen material: it should refuse, or copy the piece into the reused state first.
- No escape is decided for a hand-drawn one-off, such as an area the renderer leaves alone. The talk's 38 one-off diagrams were most of its work, so this is the largest risk to the product.
- Previews are part of the main loop (4i, 4j), so a reproducible rasteriser comes in early.
- Rendered doc figures must be committed for a repository host to show them, while 4h never commits the scene. Committed outputs need a freshness check, as software-analysis's generated overview has.

**The decided points with the most risk:** point 2 in its pure form, with 4h (text and fonts on the critical path); 4a's data-only one-offs; 4i (the most to build for the least proven need: one author, one repository today); 4j (it depends on previews).

**Fit in pkit.** It fits the capability pattern (COR-017) and agent placement (COR-026). Renderers are plugins under `scripts/`, not COR-017 variants. demo-recording's interface does not fit as the renderer contract (its own DEC-003 tested a tree rendered to HTML), but its pattern does: a neutral core, knowledge flowing one way, one check at the plugin's edge. A fetched library folder should be described as a project file the capability keeps equal to its tag by a hash, not as owned by its source, which would invent a third owner (COR-001). Anything under `.pkit/capabilities/` in project-kit ships to every adopter, so the first slice is proved outside the shipped tree. The IBM context and the pkit subject must not ship (COR-014). Only two things would need a core decision, and both can be avoided: renderers joined through connection points, and delivered pieces locking the engine.

**To decide before building, in this order:** the runtime and outside programs (new); text and fonts (point 5); references between elements (new); format numbers (new); how a renderer plugs in, at its smallest (point 6); the names inside files (part of point 16); where the slice's code lives (parts of points 7 and 15). The rest can wait, including 4i's commands, 4j's previews and Figma.

**The smallest first slice.** Four slides of the Friday talk, each testing one part: a plain slide with a long lead (frame, tokens, text measuring); `pyramid` (repetition and formulas, colours as roles); `sockets` (connectors and references between elements); a terminal slide (Mural's missing monospace font and the image fallback). Each in English and Czech, in `carbon-light` and `teal-calm`, as one scene rendered to SVG and pushed to Mural; then a PDF from the SVG, and a board edit taken back. Optionally `sockets` lifted out as a doc figure in light and dark. It passes when one scene feeds both renderers with no Mural-only geometry, text fits on both, the data for `pyramid` and `sockets` is no longer than `gen.py`'s code for them, a theme switch changes only values, and a Czech edit on the board lands in the Czech material file. Left out: fetching, versions, locks, states, previews, Figma, agents.

## Names

**Names are confirmed together with the maintainer** (30 October). The note's terms are working names until the maintainer confirms them. The maintainer said to be careful about picking names such as "one-off" or "talk".

| Working name | Meaning | Status |
|---|---|---|
| visual work | what the capability is about | working |
| logical layer | the source: content, components, libraries | working |
| content | what to show, in one language: text, lists, image references, no layout; "material" in the points before the naming pass | decided (naming pass) |
| renderer, projection | what draws the logical layer; the relation between the two | working ("adapter" ruled out, as pkit uses it for the harness) |
| component | anything from a tag to a whole slide layout (point 4b) | working; established term |
| kind | a component the content may name at the top | working |
| option, variant | a choice a component declares, such as a card's tone | working (Figma says "variants" and "component properties") |
| design tokens, raw values, roles, component tokens | the design language as data | established terms (W3C Design Tokens) |
| theme, mode, context | a set of values; light or dark; DAM or IBM | working |
| frame | an element's box: `x`, `y`, `width`, `height` (points 4h, 19); before the naming pass, also level 6 | decided (naming pass): this meaning only |
| recipe | a recurring arrangement, promoted after about three uses | working (Brad Frost's term) |
| one-off | level 7 before the naming pass | replaced by "local component" (naming pass) |
| local component, library component | a component made inside one piece, in its `components/` folder (level 7); a component a library publishes. A local component that recurs about three times is promoted to a library component | decided (naming pass; Figma's terms) |
| talk | level 8 in the first drafts | replaced by "piece" (naming pass) |
| deck | the top component of a presentation | working (Slidev, Marp and Keynote users say "deck") |
| library | a named, versioned set of pieces that is shared, and names the libraries it builds on | working |
| values, structure, meaning | the three kinds of content a library holds (point 4g) | working |
| core, interface, starter | the core holds only the interface (role names, top components, named layouts, slots); the starter holds the capability's opinionated components (point 18b) | working |
| subject | what the work is about, such as pkit; its concepts mapped to roles (point 4g) | working |
| layouts, slot, entry point | level 6: the layouts a top component declares and a context supplies, such as a deck's cover, section and slide ("named layouts" before the naming pass); a place in a layout; a named way into a library, such as `ibm/deck` (point 4g) | layouts and slot decided (naming pass); entry point working |
| shared core, per context, per piece | the three scopes | working |
| drafting, delivered, reused | the states of point 4d | working |
| living | the fourth state: work that is never delivered, such as a doc figure (point 4j) | working |
| piece | level 8: one finished item made from components, such as a deck, a standalone diagram, a doc figure or a poster; its content plus its lock | decided (naming pass) |
| lock | the library versions a piece uses (points 4j, 4i, 18a) | working |
| engine | the code that computes the scene: tools, formulas, text measuring | working |
| scene | what the engine computes and every renderer draws (point 4h) | working |
| font profile | the fonts for a group of renderers, set by the context (point 18d) | working |
| asks, gets | an element's two sizes: the size it asks for, the size it gets (point 19) | working |
| public anchor | a part a component lets others point at (point 19) | working |
| helper script | a script run while preparing, writing a checked one-off (point 21) | working |
| model | the file of a system's elements and relations that several views read (point 22) | working |
| contract, coverage, fallback | the kinds another capability needs drawn; how many a library draws; the drawing used for the rest (point 22) | working |

A naming pass with the maintainer comes before any record or code fixes a name. It starts with the names that appear inside files (the architect's review), one decision at a time: the capability's name first, which is also the repository's.

**The naming pass (31 October).**

- **The capability: `visual-communication`,** with the command `pkit visual`; the repository takes the same name. Chosen by the maintainer: the established name of the discipline that covers presentations, diagrams, infographics and figures ("vizuální komunikace" in Czech). Ruled out: `visual-design` (usually the look of user interfaces), `information-design` (less known, and seems to leave out presentations), `visuals` and `visual-work` (not names of a discipline).
- **The rule for the pass:** prefer the established terms of the domain. A clash with a pkit term is flagged, not avoided at any cost: the maintainer expects the context to show which meaning is meant, as with pkit's process composition (COR-036).
- **Level 8: "piece",** one finished item made from components: a deck, a standalone diagram, a doc figure, a poster. Chosen by the maintainer: the countable word designers and marketing use for one finished item ("a print piece", "a portfolio piece", "a collateral piece"). It is plain for non-native speakers and clashes with no pkit term. Its everyday sound was the one cost. Ruled out:
  - "composition": he leaned to it first, but once he saw it as folder and file names, it read as too technical. A designer's composition is the arrangement inside one frame, and pkit already uses the word for process composition (COR-036).
  - "artwork": print production's word for the finished, print-ready file. It suggests illustration and a file going to print, which does not fit a deck being drafted or a living doc figure.
  - "art": in publishing it means the pictures, as in "the story needs art", "line art" or "key art". Here that is a piece's content images, so the word names the wrong level. It also does not count ("two arts"), and non-designers hear fine art.
  - "deliverable": collides with the states, which would give "a delivered deliverable" and "a living deliverable".
  - "design": collides with design tokens and the design system.
  - "work": too general, and pkit uses it everywhere.
  - "asset": a DAM word, which collides with the logos, images and fonts inside a piece.
- **What to show: "content",** the file `content.<language>.yaml`. Chosen by the maintainer: the established term in design systems and content design, and in PowerPoint's and Keynote's content placeholders. Its opposite, layout, is the split this capability makes, and "content images" (point 21) already use it. The points before the naming pass say "material"; read it as content. Ruled out:
  - "material": every designer hears Google's Material Design, a design system close to what this capability builds.
  - "copy": only the text.
  - "data": fits charts, but undersells slides and words.
- **Level 7: "local component",** in the folder `components/` inside the piece; its counterpart is a library component. Chosen by the maintainer: Figma's terms for a component defined in the file and one published in a library, which is this split. The points before the naming pass say "one-off"; read it as local component. Ruled out: "one-off" and "snowflake" (Brad Frost's), which name an attitude rather than where the component lives, read as slang to non-native speakers, and contradict promotion.
- **Promotion of a local component,** as the maintainer asked how it works. It follows from points 4c, 4i, 18b and 21:
  1. It goes to a library its author owns: a structure library, or the starter if every adopter could use it, or a context library if it is one brand's only. Never the core, which holds only the interface.
  2. A small building block becomes a component (level 4); a whole arrangement filled with content becomes a recipe or kind (level 5).
  3. It is generalised on the way: fixed texts become content fields, one-time choices become options, and every colour a role.
  4. It is added in the library's own repository and released as a new version, since a project's copies are read-only.
  5. Each piece switches on purpose: `upgrade` brings the version, the content's `use: components/pyramid` becomes `use: <library>/pyramid` after a before-and-after, and the local copy is removed. Delivered pieces keep theirs.
  6. A local component a helper script wrote waits for its script to become an engine tool (point 21), then is promoted as data.

  No `promote` command is planned: generalising needs judgment, so it is the agent's work (aspect 9).
- **Level 6: "layouts"; "frame" keeps one meaning, an element's box.** Chosen by the maintainer after an example. The note had used "frame" for both a context's templates (4c, 4g) and an element's computed box (4h, 19), and a designer also hears Figma's frame, any container. "Layouts" is PowerPoint's, Keynote's and Google Slides' word ("Title Slide", "Section Header"), and the note already called each one a named layout. The core declares a top component's layouts and their slots; a context supplies how each is drawn; the content picks a layout per page and fills its slots; the scene gives each element a frame. Ruled out: "master" (PowerPoint's parent of the layouts, and InDesign renamed its master pages parent pages) and "template" (a file one starts from; atomic design's page skeleton; every component in today's mural-boards tool).

  ```yaml
  # libraries/core/1.4.0/deck/deck.yaml: which layouts a deck has
  layouts:
    cover:   {slots: [title, subtitle, author, link]}
    section: {slots: [number, title]}
    slide:   {slots: [title, lead, visual, footer]}

  # libraries/ibm/2.0.0/deck/layouts.yaml: how IBM draws one of them
  slide:
    size: {width: 3200, height: 1800}
    slots:
      title:  {x: =@grid.offset.1, y: =@region.title_y, width: =@grid.span.14, style: "@style.heading"}
      visual: {x: =@grid.offset.1, y: =@region.content_y, width: =@grid.span.14}
    parts:
      number: {text: "{n} / {total}", align: right}

  # pieces/friday-talk/content.en.yaml: a layout per slide, its slots filled
  deck:
    slides:
      - {layout: section, number: 2, title: What the agent knows}
      - {layout: slide, title: How pkit fits together, visual: {use: components/pyramid}}

  # the scene, computed: each element's frame
  - {id: fits/visual/pyramid/level-1, frame: {x: 340, y: 520, width: 1200, height: 140}}
  ```
- **"Slot" stays,** for a named place in a layout or a component that content fills. Chosen by the maintainer: the established term of component design (web components, Vue, Svelte, and the design systems built on them), and one word for layouts and components alike. Ruled out: "placeholder", PowerPoint's word for a layout's slot, which designers also hear as mock text or an empty field's hint, and which fits layouts only. Flagged clash: pkit's capability slots (point 24); the context tells them apart, "a layout's slot" against "a capability slot".

**A draft of the files** (31 October, not decided; it follows the decided points). `pkit visual new piece friday-talk --top deck --context ibm/deck --subject pkit` writes two files; the rest appear when they are needed:

```
visual/                                  the capability's place in the project (a setting)
├── libraries.yaml                       each library's link and the versions present (4i)
├── libraries/                           read-only copies, fetched whole at their tag (4i, 18b)
│   ├── core/1.4.0/  starter/1.2.0/  neutral/1.0.0/  ibm/2.0.0/  pkit/1.1.0/
└── pieces/
    └── friday-talk/
        ├── piece.yaml                   written by `new`: what it is, what it uses, its lock, its state
        ├── content.en.yaml              written by `new`: what to show, with the top component's fields to fill
        ├── content.cs.yaml              when a language is added: the same keys, in Czech (use case 7)
        ├── components/                  local components, made for this piece only (4c, level 7)
        │   ├── pyramid.yaml
        │   ├── cycle.py                 a helper script (21)
        │   └── cycle.yaml               the checked data it writes, with its fingerprint
        ├── images/                      content images, one per language where they hold text (21)
        ├── exports/                     what was handed out, kept as delivered (18a)
        └── renders/                     each renderer's record of what it last drew (4h)
```

`piece.yaml`:

```yaml
schema_version: 1
top: core/deck                    # its top component (4f)
context: ibm/deck                 # the context's entry point (4g)
subjects: [pkit]
languages: [en, cs]
state: drafting                   # drafting, delivered or living (4d, 4j)
lock: {core: 1.4.0, starter: 1.2.0, ibm: 2.0.0, pkit: 1.1.0}   # (4i, 18a)
renderers:
  svg: {}
  mural: {board: ibmresearchdesign6459.1790595606038}
```

`content.en.yaml`, what to show and nothing else:

```yaml
schema_version: 1
deck:
  title: Decision-driven AI development
  author: Aleš Kalfas
  parts: [{id: P1, title: Why pkit}]
  slides:
    - id: fits
      part: P0
      title: How pkit fits together
      lead: In five layers, from your decisions down to your code.
      visual: {use: components/pyramid, levels: [{head: Decisions, text: Choices you accepted, and why.}]}
```

The scene is not among them: it is computed at every render and never committed (4h). A shared model (22) is a file of its own beside the pieces, since several pieces read it.
