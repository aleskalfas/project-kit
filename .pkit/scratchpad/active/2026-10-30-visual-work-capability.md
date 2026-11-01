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
6. ~~**How a renderer plugs in.** Plugins inside the one capability, as `demo-recording` does, or a capability per renderer that fills a role (COR-052, COR-053). Also the name: pkit already says "adapter" for a harness adapter (COR-005), so these are "renderers". The critic suggested (31 October) checking whether `demo-recording`'s plugin interface can serve as the renderer contract (COR-007).~~ Decided by point 18c: plugins inside the one capability, called renderers.
7. ~~**Its origin.** Shipped by project-kit, or incubated in a project first (COR-031).~~ Decided (31 October): shipped by project-kit, built directly in it (see point 23).
8. **The starter library and themes.** Which graphical elements and themes the capability ships, from the talk's 26 masters, its kinds of visual, and the three themes. In discussion (1 November): the starter is built wide from the beginning, by the job a visual does; a component enters as experimental and becomes stable when its library's owner marks it (see "Discussion", point 8).
9. **The agents.** ~~Which agents.~~ Decided: `graphic-designer`, `graphic-design-reviewer` and `translator` (see "Discussion", point 9). Open: each one's tools and limits in detail, and the overlay category for the designer's writes.
10. **The skills.** The build loop (change, generate, render, verify) as a skill, and how a deck or a diagram is authored.
11. ~~**The rules.** Which of the talk's style rules the capability ships, and which stay a project's own.~~ Decided (31 October): two method rule sets, `COMM` and `VISUAL`, grounded in a decision record of the capability for its rules; the content stays YAML and pkit is fixed (#2416); project-kit's set inherits `WRITE` too (see "Discussion", point 11).
12. ~~**Credentials, permissions and the sandbox**, per renderer that talks to a service. Since renderers stay plugins of one capability (point 18c), it decides how the Mural plugin's network access and credentials reach only the projects that use it.~~ Decided (31 October): one sign-in per service, kept per person outside every repository, shared by every capability through the backbone; a service's hosts allowed, each by its exact name, once a project turns on the Mural renderer (#2418, #2419; see "Discussion", point 12).
13. **Output.** PDF, images, a set per language, and the translation workflow. **Decided (31 October):** every export kept and numbered in the piece's folder; a layered glossary; translations anchored to their source, with the translator as their fixer (see "Discussion", point 13). The maintainer asked (31 October) that the capability carry both, the know-how included:
    - **Outputs.** Preparing what is handed out, such as a PDF of a deck, one per language, a page per slide in order. The Friday talk needed a script of its own for it, because Mural exports only the whole board (`2026-10-29-friday-talk-tools/export_pdf.py`; use case 8).
    - **Variations per language.** The same work in several languages, from material of the same structure (use case 7).
    - **Translation know-how, shipped in the capability.** What the Czech version taught: translate a slide from its meaning, not word for word, one translator per slide; keep the English words developers say (capability, engine, slot); build each sentence the target language's way; one glossary, one word for one thing; a review by a native speaker. The lessons are in the Friday talk's note, "The Czech version".
14. ~~**The workarounds.** What to fix in the Mural renderer rather than carry beside it: the duplicates left after retries, monospace text rendered as images.~~ Decided (31 October): the renderer never retries a create blindly; it finds what a failed create made by its marker (see "Discussion", point 14).
15. ~~**Moving in.** Tests, versions, and moving today's user-level skill into pkit.~~ Decided (31 October): the delivered Friday talk and the skill stay as they are until the renderer covers what the talk used; the slice rebuilds four slides on a new board; the maintainer signs in again (see "Discussion", point 15).
16. ~~**Names.** A naming pass with the maintainer before any record or code fixes a name.~~ Decided (31 October): the capability `visual-communication`; a piece, its content, local components, patterns, layouts, slots and frames; a brand, a component library and a notation; foundations and the starter; the states draft, delivered, living and adapted; the rest kept or chosen by the agent at the maintainer's word (see "Names", the naming pass).
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
23. ~~**Where the first slice's code lives.**~~ Decided (31 October), then reversed the same day. First: a new repository of its own, incubating the capability (COR-031), nothing shipping to anyone, as the architect advised. **Reversed by the maintainer during point 11:** a new repository is an unnecessary delay; the capability is built directly in project-kit, at `.pkit/capabilities/visual-communication/`, as living-docs and software-analysis were, starting at 0.1.0 and opt-in like every capability. What follows:
    - **What ships:** each release carries the capability as it stands, at 0.x, installed only by a project that asks for it, as the other capabilities started. The architect's wish to prove the first slice outside the shipped tree is given up for speed.
    - **What never ships:** project-kit's own pieces (the Friday talk) and its own libraries (the IBM brand, the pkit notation) live in project-kit's project-owned files, never inside the capability's folder (COR-014, COR-001).
    - **Easier:** project-kit's set for its pieces inherits its `WRITE` directly (point 11), and the fix for YAML artefacts (#2416) lands in the same repository as its first user.
    - **Unchanged:** the Mural plugin reuses the mural-boards tool's client, sign-in, pacing and sync record, and the mural-boards skill keeps working until the capability replaces it (point 15). Point 7, the capability's origin, is settled: shipped by project-kit.
24. **A protocol between capabilities.** How a consumer such as software-analysis declares a contract, how visual-work is connected to it, and whether pkit's slots and connection points can carry a request with input or need a core decision. Use case 13; not built now.
25. **Anchors on a piece's facts.** Whether a piece, or its content, carries pkit's anchors (COR-050), so a doc figure is flagged when the code or decision it shows changes, and `graphic-design-reviewer` becomes the fixer of pieces (project-management DEC-056). Came from point 9.

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
- add recipes and kinds, component tokens, and extra modes or scales only when a real talk needs them. (Revised by point 8 for patterns: the starter adds them ahead of need, each entering as experimental.)

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
version: 2.0.0                  # the library's content, semver: major removes or renames, minor adds, patch fixes (for stable components, point 8)
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

### 9. The agents: which ones (31 October)

**The question.** Which agents the capability ships, and what each is for. Their tools and limits in detail follow; Mural's credentials are point 12.

**What the Friday talk shows, by kind of work.**

- **Designing and building:** the main session chose each slide's visual, wrote all 38 per-slide diagrams, pushed, verified fit, removed duplicates and exported PDFs. It also wrote the words and checked every fact against the repository: counts, real command output from throwaway installs.
- **Reading as the room:** the maintainer set the rules one by one (keep the flow, plain words, no self-reference, big picture before detail, say why, say what comes wired; the talk's note, lines 63 to 70). The writing session checked its own slides, and the maintainer still caught misses.
- **Translating:** separate helpers translated slide by slide and still wrote "translated English"; three fresh translators then rewrote it from one brief (a glossary, the words kept in English, Czech sentence building and typography), and the maintainer reviewed it.

**The agent's first draft:** a designer writing only inside its piece, a read-only reviewer with the talk's rules as its lens, and a translator owning each language's content file, the designer later declared the fixer of pieces.

**The critic's review (31 October).** The split by kind of work held; the write scopes and the reasons did not:

1. **No agent could write a library,** yet use cases 2, 3, 6, 10, 11, 12 and 13 need it: improving a component, a new brand, a pattern, the shared model, a top component with its layouts, a notation, drawing another capability's visuals. Promotion is the agent's work by the naming pass. The draft was shaped like one talk.
2. **The designer could not be a fixer:** project-management's DEC-056 point 1 refuses a fixer that claims paths or may change files or start agents; living-docs' fixer owns nothing. And a library release is no drift: `upgrade` already handles it (4i). The drift a fixer is for is a piece's facts going stale against their sources, such as a doc figure about code, which needs pieces to carry anchors.
3. **The translator's file sat inside the designer's folder:** two owners of one path, which `pkit refs validate` flags, and several translators writing one file at once.
4. **The reviewer's rules were the talk's, written into the agent:** which rules ship is point 11, and a shipped agent must not carry one project's taste (COR-006, COR-014). living-docs' reader review reads its rules only from the rule sets.
5. **No one checked the facts but the writer,** though the talk's work was largely facts.
6. Also: an audience needs a place to be declared; a reviewer that renders must leave no record and push nothing; the translator's real gain was the brief and narrow tools, not a fresh context; the designer must work when dispatched too, since project-manager may hold the session (DEC-059), and dispatch others only when it holds the `Agent` tool, always without a name.

**The agent's revised recommendation.** Three agents, by kind of work, none per discipline (4f):

| Agent | What it does | What it may write |
|---|---|---|
| `graphic-designer` | Turns an intent and its facts into a piece: content, local components, helper scripts, render, fit, sending to renderers through `pkit visual` only. Builds the project's own libraries: promotes local components, adds a brand or a notation, implements another capability's contract. Shows the person any write to a library in another repository first (core rule 19). Booted as the session's agent or dispatched; dispatches the other two when it can. | the project's pieces, its own libraries and shared models, through an overlay category; never the fetched copies, never credentials |
| `graphic-design-reviewer` | Reads a whole piece, rendered, as its audience: every language, and a doc figure as its page's reader (living-docs' readers). Checks the piece's facts against the repository. Takes its rules only from the rule sets (point 11). | nothing; it renders into its workspace only |
| `translator` | Translates a page from its meaning, from a brief the capability ships (point 13), and returns the text with notes on length. The native speaker's review stays the person's. | nothing; the designer writes the file |

**The names.** The maintainer asked why the reviewer's name did not match the producer's. pkit's own pair names a producer by its role and a reviewer by the work it reads (`software-engineer`, `code-reviewer`), so a reviewer stays independent of whoever made the work: the agent, a person editing on the board, another pull request. He proposed `design-reviewer`, which a developer reads as a review of a software design, the architect's ground; and `graphic-reviewer`, where "graphic" alone means a picture or "explicit". `graphic-design-reviewer` keeps the fixed term whole and matches the producer. "Designer" alone means user-interface design; "art director" directs and decides, while the reviewer only reports.

**Outcome (31 October).** The maintainer agreed to the three agents, `graphic-designer`, `graphic-design-reviewer` and `translator`. It adds three things:

- an `audience:` field in a piece;
- a render into the agent workspace that leaves no record and sends nothing;
- a new question, point 25: whether a piece's facts carry pkit's anchors, so a doc figure is flagged when what it shows changes; the reviewer would then be the fixer of pieces.

### 11. The rules (31 October)

**The question.** Which of the talk's style rules (the talk's note, lines 59 to 70) the capability ships to every adopter, which stay a project's own, and how a piece comes under rule sets at all (COR-051), since `graphic-design-reviewer` reads its rules only from them (point 9).

**The agent's first draft:** the look as library data; a method rule set `VIS` of seven rules; the project's taste in the project rule set the install creates, project-kit inheriting its `WRITE`; `piece.yaml` made an artefact so rules bind on it, which, the draft said, would also decide point 25.

**The critic's review (31 October).** The shape held; four things did not:

1. **Point 25 is not decided by it.** An artefact without anchors is reported and counted, never refused (COR-050 point 8). Pieces as artefacts are only the place where anchors could later live.
2. **The wrong file.** A plain YAML file is never an artefact (ADR-056 point 2), and the rules judge titles, leads, words and facts, which live in the content. As drafted, a change to a slide's words brought no rule into play, while every lock bump of a draft piece would have altered the artefact.
3. **Deck rules shipped as universal.** "The lead answers the title" fails on a cover, a section slide, a poster or a map of a system; "big picture before any example" was narrower than the maintainer's own rule ("shown through something the room knows"). Pieces cannot be scoped by discipline, so the wording must fit every discipline.
4. **Inheriting `WRITE` whole** brings document-structure rules that do not fit slides, leaves its word counts to a lint that never reads content, and never reaches the incubation repository.

Also: a "use your libraries" rule was missing; checks such as fit and contrast must always run, not only where `VIS` binds; a doc figure's audience is its page's reader; rules about libraries (a notation's icons, a brand's footer size) are library validation; a rule set per piece is heavy; `VIS` needs a decision record of the capability's own, not this note.

**The agent's revised recommendation,** discussed point by point at the maintainer's request:

1. Each kind of rule has its own home.
2. `VIS` holds eight rules worded for every discipline.
3. Each language's content becomes a document, `content.<language>.md`, the content as its front matter and the piece's brief and notes in its body; `piece.yaml` stays plain YAML, outside the rules.
4. project-kit writes its own set for its pieces with the talk's plain-words rules, rather than inheriting `WRITE` whole.
5. `VIS` is grounded in a decision record of the capability, in its own repository.

**Point 1: each kind of rule has its own home. Agreed (31 October),** after the example of the slide "Permissions on day one":

| What | Home | Example on that slide |
|---|---|---|
| The look | the libraries: brand, patterns, notation | the terminal (a starter component), the yellow note (a starter component; named with the blocks, point 8), the limit line (the `limit` slot of the brand's slide layout) |
| What needs no judgment | the engine's checks, run on every render | a card's text spilling out; text too pale on its background; a raw colour |
| What any piece needs, judged | `VIS`, the capability's rule set | does the lead answer the title, and the picture show it? |
| The project's taste | the project's rule set, which the install creates | is the lead under 25 words, with no semicolons? |
| One piece's goals | the piece's brief, read by the reviewer as its intent | does the slide say what comes wired? |

The reason: in the talk all of these were rules a person had to catch by reading; here only two need a reader, the look cannot drift, the checks always run, a project's taste stays its own, and one talk's goals do not become rules that outlive it.

**Point 2: the shipped rules come from the canon, in two sets. Agreed (31 October).** On the first rule ("the lead answers the title, and the main visual shows that answer") the maintainer said such rules are not a project's taste but core knowledge of good design: nobody wants the opposite, and no adopter should have to write them again. The capability gives its opinion of good visual communication; adopters add their own on top. So the shipped rules are taken from the established canon, each with its source, and the talk is only the example that confirms them. They fall into two kinds, shipped as two method rule sets, both inherited by the project set the install creates:

- **`COMM`: does it say the right thing?** One point per page, stated and then shown (Michael Alley's assertion-evidence); the answer and the big picture first (Barbara Minto's pyramid principle; Shneiderman's "overview first, details on demand"); each page following from the one before; words that fit the audience; facts with a named source (Tufte, "thoroughly describe the evidence").
- **`VISUAL`: does it look right?** One focal point per page (visual hierarchy); related things grouped and aligned (proximity and alignment, Robin Williams); nothing that does not help the message (Tufte's chartjunk; Mayer's coherence principle); the same thing drawn the same way, through the library's patterns (consistency); readable where it is shown (Nancy Duarte's glance test); colour never the only signal (WCAG 1.4.1).

Why two sets: a finding says which kind of failure it is ("no point" against "no focal point"), fixed by different people; and `COMM` is not visual at all, so documents could use it too. Moving it into pkit's core is a question for when a second user appears (COR-007), not now. The set names are working names.

The rules are then taken one at a time, `COMM` first.

- **RS-COMM-001, one point per page. Agreed (31 October):** "Where a page has a title and a lead, the lead answers the title, and the main visual shows that answer." A doc figure's caption counts as its lead. A page without a lead (a cover, a section slide, the questions) is not judged by it. The talk's example: the lead "Decisions are the source: everything else in pkit carries them out…" under "How pkit fits together", which the maintainer found did not answer the title.
- **`COMM` binds only on pieces that explain. Agreed (31 October).** The maintainer asked whether these rules suit every kind of design or only explanation, wanting a curated base that suits his case without over-fitting. Tested against the use cases: `VISUAL` fits every visual piece; `COMM` fits pieces that explain or argue (a talk, a handout, a doc figure, an explainer diagram, a poster's one message), but not a reference map such as a C4 view (it has no single point), a workshop board people fill in, or a user-interface mockup. Data visualisation has the established split: explanatory against exploratory (Cole Nussbaumer Knaflic). pkit's scopes select by path and type, never by what a file says, so a piece declares whether it explains, in one field of `piece.yaml` (explaining by default), each `COMM` rule applies only to an explaining piece, and the reviewer reads the field. The field's name and values are left to the decision record.
- **RS-COMM-002, the big picture first. Agreed (31 October):** "A piece, and each part of it, says what a thing is and why it matters before any detail of it. For something the audience has never seen, the big picture shows it through something they already know." Sources: Barbara Minto's pyramid principle (the answer, then the arguments, then the detail); Ben Shneiderman's "overview first, zoom and filter, then details on demand". The talk's examples: Part 3 once opened with one skill's ties before the room knew what skills are for, and was rebuilt with "Where skills come from"; "What schemas and processes look like" shows real files before the task board, as the maintainer asked for something the room has never seen.
- **RS-COMM-003, the story in order. Agreed (31 October):** "In a piece read in order, its leads read one after another tell its story: each follows from the one before. A page outside that order, such as an appendix or a backup slide, is marked as one." Source: consulting's horizontal logic (the headlines alone, in order, tell the story; vertical logic, each slide supporting its headline, is RS-COMM-001). The talk's examples: the flow checks the maintainer asked for on "Decision records" and "Decided once, found later"; Part 2's last limit, "A rule is advice: an agent can still break it", answered by Part 3. A single figure, a poster or one diagram is one page, and the rule says nothing of it.
- **RS-COMM-004, words for the audience. Agreed (31 October):** "The words fit the audience the piece declares. They use the terms that audience knows, explain once the ones it does not, and are as plain as that audience needs. A doc figure's audience is the reader of its page." Sources: audience analysis, the first rule of rhetoric and technical writing; ISO 24495-1 (2023), plain language. The talk's examples: a slide the maintainer read again and again without getting it; "What every session is told" rebuilt because it used the records' own wording; "capability" defined once ("optional parts, called capabilities"); English terms kept in the Czech version where Czech developers say them in English. The concrete limits (25 words a sentence, no semicolons, no idioms) stay the project's.
- **RS-COMM-005, facts with their source. Agreed (31 October):** "Each fact a piece shows is true against a source the piece names, on the page or in its notes: for a number, a quote or a command's output, where it was measured; for a claim of how something works, the record or file that decides it. Made-up data is marked as an example. A delivered piece holds as of its delivery; a living piece holds now." Sources: Edward Tufte's principles of analytical design ("thoroughly describe the evidence", *Beautiful Evidence*); attribution in journalism. The talk's examples: counts from a throwaway install on the evidence lines; real `pkit friction check` output replacing a made-up box; "no slide may say every move is logged" (COR-033 point 7). Where it meets point 25: anchors would let pkit flag a living piece when a source changes.

`COMM` is complete with these five rules. `VISUAL` follows, one rule at a time; it judges every visual piece, whatever its purpose.

- **RS-VISUAL-001, one focal point. Agreed (31 October):** "Each page has one focal point: what matters most is what is seen first. Size, weight, colour and position rank the rest below it." Source: visual hierarchy, and the designer's squint test. The talk's examples: "Decision records", where the key message sat "very small" in a box and nobody could see it; "Where ideas start", where the move from scratchpad to decisions did not stand out; the paths emphasised at the maintainer's request. `COMM` asks whether a page says its point; this rule asks whether the eye finds it first.
- **RS-VISUAL-002, grouped and lined up. Agreed (31 October):** "What belongs together is placed together and lined up; what is separate is set apart. Steps are joined in the order they are read." Sources: the Gestalt principles of proximity and connection; Robin Williams' proximity and alignment (*The Non-Designer's Design Book*). The talk's examples: "Decided once, found later", rebuilt as three cards with each picture inside its card, joined by arrows, after "I don't have mentally connected the boxes together"; COR and PRJ placed together, then ADR, then DEC; "Where ideas start" moved to the left, where readers expect the flow to begin. Lining up to the grid is mostly the engine's (layouts and layout operators place everything); which things belong together is the reviewer's to judge.
- **RS-VISUAL-003, nothing extra. Agreed (31 October):** "Everything on a page helps it do its job; what does not is left out. Decoration never competes with the content." Sources: Edward Tufte's chartjunk; Richard Mayer's coherence principle. The talk's examples: the cover icon that "looks childish", replaced by project-kit's name and its link; the counts moved from the decisions slide into its notes; the "Scratchpad notes" box, to be removed or given a place of its own. "Its job", not "its message", so the rule fits pieces that do not explain: a workshop board's empty areas, a C4 view showing only what is in its scope.
- **RS-VISUAL-004, the same meaning looks the same. Agreed (31 October):** "The same meaning looks the same everywhere. A concept keeps the colour, icon and shape its notation gives it. Where a library has a component for the job, the piece uses it rather than drawing its own. (Worded "pattern" when agreed; "component" since point 8, 1 November.) A new message may look new; it is not forced into the picture of the one before." Sources: Robin Williams' repetition; Jakob Nielsen's "consistency and standards"; design systems. The talk's examples: one style for every command line; COR in pkit's purple, ADR in the architecture role's green; and the other side, the maintainer turning down a third "Where … come from" table ("I don't want to recycle the graphic again") and wanting a new picture to keep the room's attention. The middle sentence is the "use your libraries" rule the critic found missing: a piece drawing its own terminal panel beside the `terminal` pattern is reported.
- **RS-VISUAL-005, readable where it is shown. Agreed (31 October):** "Everything on a page can be read where the piece is shown: projected in a room, on a screen, or printed. A page is taken in at a glance." Sources: Nancy Duarte's glance test (*slide:ology*); legibility minimums per medium (Guy Kawasaki's 10/20/30 rule for projected slides). The talk's examples: the main visual "big enough to read from the room"; the decisions slide's key message "very small". The engine checks the smallest text size for the piece's medium, which `piece.yaml` declares (`medium: projected`, `screen` or `print`); the reviewer judges the glance test, which no size check catches.
- **RS-VISUAL-006, colour never alone. Agreed (31 October):** "Colour is never the only signal. Whatever a colour tells apart is also told by a label, an icon, a shape or a line style." Source: WCAG 1.4.1, use of colour; contrast (WCAG 1.4.3) stays an engine check. The talk's examples: broken ties red and dashed; the answer tags with their words; and the cost the maintainer accepted, the install slide's listing, where pkit's files (purple) and the project's (blue) are told apart by a legend line only and would need a second marker. A notation gives each concept a colour and an icon or shape (4g), so pieces that use it pass; the rule mostly catches local components that colour-code by hand.

`VISUAL` is complete with these six rules. Points 3 to 5 of the recommendation follow.

**Point 3: the content stays YAML, and pkit is fixed. Decided by the maintainer (31 October).** The agent recommended wrapping each language's content as `content.<language>.md`, the YAML between two `---` lines, because pkit attaches rules and anchors only to a Markdown document with front matter or a collection entry (COR-050 point 1); "any other plain YAML data file in a declared place is not a document" (ADR-056 point 2), so `pkit rule-sets reach` would answer "no rules" for `content.en.yaml`. The maintainer asked why a data file must look like a document, and decided: the content stays a YAML data file, with the brief as a field (`brief:`), and pkit core is fixed so that a YAML data file can be an artefact too, its whole content being its data. No workaround. The fix is a core change: what an artefact is (COR-050 point 1, ADR-056 point 2), how artefacts are found, how rule sets reach them, where the `pkit` container with its friction block sits in a YAML file, and how an anchor names a part of one (by key, where Markdown uses headings). `piece.yaml` stays plain data outside the rules either way: its lock moves on every render of a draft. The maintainer also asked whether the YAML data files have JSON Schemas: yes, as point 20 decided, each file of the capability's own format binds its schema the pkit way (COR-023), with one `schema_version` shared by all of them, and a content file's fields are checked by the schemas of the components it uses (4f). Filed in project-kit as Feature #2416, "A YAML data file can be an artefact, so rules and anchors attach to it" (under EPIC #1474), with its first Task, #2417, the core decision, started the same day.

**Point 4: project-kit's set for its pieces inherits `WRITE`. Agreed (31 October).** The critic had advised against inheriting `WRITE` whole, as it brings rules for documents. Checked rule by rule against a slide, it fits: the sentence rules (005, 006, 008, 009, 010, 011, 013, 018) are the talk's plain-words rules already; 001 (open with what matters most) is a slide's lead; 002 (parallel labels) fits parallel cards and columns; 003, 007 and 017 fit the notes; 014, 015 and 016 mostly find nothing to judge; 004 (side matter last, under *Note*) is no conflict, since a slide's limit line is part of its message, not side matter. So project-kit's set for its pieces inherits `WRITE`, `COMM` and `VISUAL`, and adds only what `WRITE` lacks: no idioms and no phrases such as "the why"; never a record's own wording; the piece never uses itself as content; a piece that shows what pkit does also says why. With the capability built in project-kit (point 23), no copy is needed. `WRITE`'s counts belong to project-kit's prose lint, which reads only Markdown today. The maintainer asked whether the lint would read every value or only the prose: only the prose, which the component's schema marks (`title`, `lead`, `text`, `notes`; never an id, a reference, a layout's name or a terminal's lines), the same fields the translator translates. Since every YAML artefact judged by prose rules has this question, it was added to the core fix: to #2417 (the decision says how a rule finds a YAML artefact's prose) and to #2416 (the prose lint reads those fields).

**Point 5: the rules' reasons live in a decision record of the capability, for its rules alone. Agreed (31 October).** Every accepted rule must record why it exists: inline, in the decider's words; by citing a decision record, for a reason longer than a line; or by citing a captured source (COR-051 point 5). The reasons behind `COMM` and `VISUAL` are long: the canon each rule rests on, why there are two sets, why `COMM` binds only on pieces that explain. So the capability gets a decision record for its rules alone, apart from the record of how the tool works (levels, libraries, renderers), which changes for other reasons and covers some 25 aspects. It has a point per group of rules. Each rule cites the record as its origin and anchors to the point it rests on, as living-docs' rules do (`origin: {decision: "living-docs:DEC-001"}`, anchored to `living-docs:DEC-001#3`), so a change to that point flags the rule for revalidation. For example, RS-VISUAL-006 would anchor to the point saying why colour is never the only signal: about one man in twelve cannot tell some colours apart, a projector washes colours out, a print may be grey (WCAG 1.4.1). Inline reasons in the maintainer's words were set aside: adopters would read "the maintainer said so" as the reason for a rule shipped to them, and the canon would have no home. The acceptance gate orders the work: the record is accepted before the rules that cite it.

Point 11 is decided.

### 12. Sign-in and network access (31 October)

**The question.** How the Mural renderer signs in to Mural and reaches it over the network, without agents seeing the secrets, and only in projects that use it.

**What it needs.** The Mural app's client id and secret; a sign-in token that lasts 15 minutes and refreshes itself; network access to `app.mural.co` and to the storage host an image is uploaded to (Mural names it on each upload); one sign-in in the browser, through a callback on `localhost`.

**What pkit has.** With the sandbox on, a toolkit allows the hosts a tool needs; the backbone ships toolkits for the GitHub and Anthropic APIs, a project can add its own, and a capability cannot ship one yet. project-kit runs with the sandbox off, which is why the Friday talk's pushes worked. The sandbox blocks reads of `~/.ssh`, `~/.aws`, `~/.config/gh` and `~/.netrc`, which on macOS broke `gh` itself, since `gh` reads its own token inside the sandbox (#312); the Mural renderer would meet the same. A capability can ship denies that keep its agents from commands, as project-management does.

**Where the credentials live. Decided (31 October).** Per person, outside every repository, in `$XDG_CONFIG_HOME/pkit/credentials/<service>/` (`~/.config/pkit/credentials/mural/` by default). Set aside: the system keychain (safest at rest, but a dependency, no keychain on a machine without a desktop or in CI, and its command would need a deny too; possibly an option later), and a git-ignored folder in the repository (every agent's file tools reach it, and one missing ignore line commits a secret). The maintainer asked whether the path should follow the capability or the service: the service. A sign-in is the person's Mural account and the app they registered, not something of one capability, as `gh`'s sign-in serves every tool that uses GitHub. The path is the part that is hard to change once it exists on every machine, and one root for every service lets one rule keep agents out of all of them. A second account of one service gets its own folder later.

**Sign-in is shared code from the start, in the backbone. Decided by the maintainer (31 October).** The agent first proposed that the Mural renderer own the sign-in until a second capability needed it. The maintainer asked to count with shared sign-in code from the beginning, and two facts agreed: a capability's scripts never import pkit's own code or another capability's (COR-017, COR-021), so sharing later would change how every capability gets its token; and only one place may refresh a token, since where a service issues a new refresh token on each refresh, two programs refreshing at once invalidate each other. So:
- a person signs in once per service (`pkit sign-in mural`, with a sign-out and a list of sign-ins that never shows a secret);
- a capability declares each service it uses as data: its sign-in addresses, the permissions it asks for, the hosts it reaches; two capabilities' declarations of one service combine their permissions;
- pkit's command dispatcher refreshes a token and hands it only to the command of a capability that declared the service; nothing prints it, and agents are kept out of the credentials folder;
- the calls to Mural's API (pacing, retries, the board sync) stay in the capability's Mural renderer.
A token's power matters more than hiding its value (#340): each sign-in asks only for the permissions its capabilities need, and keeping a token out of view guards against leaks into transcripts and logs, not against a compromised agent. Filed as Feature #2418, "One sign-in per web service, shared by the capabilities that use it" (under EPIC #372, a capability's dependencies on what lives outside pkit), with its first Task, #2419, the core decision. It does not block the first slice: the engine and SVG go ahead, and the Mural push comes when sign-in lands.

**Network access, only where Mural is used. Agreed (31 October).** A service's declaration lists its hosts, and pkit allows them through the path toolkits use, reported in the sandbox status like `api.github.com`, since a host list bounds well-behaved traffic but is no security boundary. They are allowed once a project turns on the Mural renderer, not when the capability is installed, so a project that renders only SVG and HTML opens no access to Mural. Every host is named exactly, never by a wildcard: the upload host is an Azure storage account, and allowing all of Azure storage would let an agent upload to anyone's account. The short Mural test before building records the real upload host. Added to #2418 and #2419.

Point 12 is decided.

### 14. The workarounds (31 October)

**The question.** What the Friday talk carried beside the mural-boards tool, and what the capability fixes instead of carrying.

**Three are covered by decided points.** `make_row_icons.py` recoloured Carbon pictograms: the engine tints an image (4h). `mural_fonts.py` listed the fonts Mural accepts: the Mural renderer checks its font profile against that list (5, 18d), and for monospace text the brand chooses a substitute font or the image fallback (18d). `export_pdf.py` made a PDF per language: outputs, point 13.

**The duplicates are fixed in the renderer. Agreed (31 October).** Mural sometimes makes an object and then answers its create with a 502 or 503; the tool retries, and a second, invisible copy stays, which blocks `remove` until `stray_duplicates.py` deletes it. In the capability, every object the Mural renderer creates carries its own id as a hidden marker, as the tool's template parts already do. A create that fails in a way that may have made the object is never retried blindly: the renderer lists the board, takes over what it finds by marker, and creates only what is missing. `verify` still reports any duplicate it sees, as a problem. Set aside: a sweep built into every push (it deletes after the fact, and a duplicate blocks `remove` until it runs), and never retrying a create (safe, but on Mural's bad days a push would stop often).

### 15. Moving in (31 October)

**The question.** How today's tool moves into pkit: the user-level `mural-boards` skill, its tests, and the Friday talk made with it.

**Settled along the way.** The capability starts at 0.1.0 (point 23). Its tests live in project-kit's `tests/`, as every capability's do, and the tool's offline suite, which runs against a fake Mural API, comes with it.

**The Friday talk stays as it is. Agreed (31 October).** The talk was given on 30 October, so it is delivered: locked, with its exports as the real freeze (4d, 18a). Its board, its map file and the `mural-boards` skill stay untouched. For the first slice, four of its slides are made again as a new piece from the talk's content and pushed to a new board, so the delivered board is never at risk. The skill keeps working until the capability's Mural renderer covers everything the talk used; then the maintainer retires it. If the talk is given again, it is converted then, as an adapted piece (4d). Set aside: converting the whole talk now and taking over its board (some 30 slides and 38 one-off diagrams converted before the slice proves anything, with the delivered board at risk), and converting it onto a new board (safe, but most of the work, for a result nobody needs yet).

**The maintainer signs in again. Agreed (31 October).** The current sign-in sits in `~/.config/mural-boards/`, which no agent may read. `pkit sign-in mural` asks for the app's client id and secret in the terminal, hidden as they are typed, then opens the browser once; the same Mural app serves, its callback address unchanged. Nothing reads the old folder, and the maintainer deletes it when the skill retires. If #2419 decides that project-kit registers one app for everyone, only the browser step stays. Set aside: pkit taking the old sign-in over, which would teach pkit's code another tool's secret files to save a minute.

**The tool's code splits as it moves.** Its sign-in goes to the backbone (#2418); its client, pacing, retries and sync record go to the capability's Mural renderer (point 23), with point 14's fix for duplicates.

Point 15 is decided.

### 13. Outputs, languages and translation (31 October)

**The question.** What is handed out and how it is made; where the glossary for translations lives; how a translation stays in step with the English. Taken one part at a time.

**What was known.** Mural exports only a whole board, so the Friday talk needed `export_pdf.py` for a PDF per language, a page per slide in order. Tools are adopted, never built (the architect's review): `rsvg-convert` gives a PDF with real, selectable text from SVG, headless Chromium a tagged PDF that screen readers follow, `resvg` pictures. pkit does not install them; the capability checks for them (17). A delivered piece's exports are its real freeze (18a).

**Outputs: every export kept, numbered, in the piece's folder. Agreed (31 October).**
- A piece lists the outputs it wants in `piece.yaml` (`outputs: [pdf, png]`), each made once per language, from the scene through the SVG renderer, never from Mural, so a PDF never depends on a board. The PDF comes from `rsvg-convert`; a piece asks for a tagged PDF through Chromium with `pdf: tagged`.
- **Versions by default, at the maintainer's wish.** Every export is kept and none is overwritten. One export run is one version number, shared by all its languages and formats, so `v3` in English and `v3` in Czech match: `friday-talk.v3.en.pdf`, `friday-talk.v3.cs.pdf`. A record, `exports/versions.yaml`, says what each version is: its date and time, the piece's state then (draft or delivered), its lock, a hash of its content. A number rather than a timestamp: it is short, sorts, and is easy to say ("send me v3"), and the record holds the time; two branches making the same number for one piece is rare, and the merge shows it.
- **A living piece also keeps an unnumbered current copy** (`friday-talk.svg`), which a doc page links to, since a link cannot follow a moving number. A check fails when a committed export no longer matches the piece's content.
- **Committed:** the delivered versions (the freeze), a living piece's current copy (a repository host shows only committed files), and the record. Large files stay in git's history forever, so a draft version stays on the machine that made it, out of git, until it is delivered.
- **In the piece's folder, not one folder for all.** The maintainer asked which: the piece's folder (`visual/pieces/<piece>/exports/`). A piece is one folder, what it is, its content and what it produced, so it is copied, archived or removed in one step, as its images, renders and local components already are. The file name still carries the piece's name, since an exported file travels alone. Seeing every handout is a command (`pkit visual exports`, listing each piece's versions from their records), and publishing them together is a step that copies them out.
- **A correction to the agent's first proposal.** It said `renders/` would hold previews and never be committed. That contradicted 4h: `renders/` holds each renderer's record of what it last drew (ids, a hash per property, the commit), which must be committed so another clone updates the same board and an edit made there can be taken back (point 3). Previews and working pictures go to `previews/` instead, never committed; the reviewer renders into the agent workspace (9).

**The glossary: layered, like the libraries. Agreed (31 October).** The Czech version taught that terms must be fixed before anyone translates: one word for one thing; "capability" stays English in Czech, feminine and not declined; never "add-on"; "čistá instalace" for a fresh install. The talk kept them in the Czech file's header, where translators read them and nothing checked them.
- **A notation holds the words of its subject**, per language, beside the colour and icon it gives each concept, so every piece about that subject says it the same way. A notation for software work, which the starter could ship, holds that Czech developers say "pull request" and "commit" in English, and "větev" and "repozitář" in Czech; the pkit notation holds "capability", "záznam o rozhodnutí" and "jádro pkitu".
- **A brand holds its company's voice** (in Czech, the formal "vy", in lower case), and **a piece only its own terms** (`glossary.yaml` in its folder: "čistá instalace").
- **The translator reads one merged list**: the piece over the brand over the notations. A term two notations define differently is reported, and the piece settles it.
- **A glossary may say which words are never used** (`never: [add-on, plugin]`). The engine checks them in the prose fields, with no judgment (`TERM content.en.yaml slides/install/lead: "add-on"; the pkit notation says "capability"`); the reviewer judges whether each term is used in its meaning.

```yaml
# libraries/pkit/1.1.0/glossary.yaml
capability:
  meaning: an optional part of pkit that a project installs
  en: {use: capability, never: [add-on, plugin]}
  cs: {use: capability, note: stays English; plural capabilities; feminine, does not decline}
decision record:
  meaning: a file that records one decision and why it was made
  cs: {use: záznam o rozhodnutí}
```

Set aside: a glossary per piece only (every pkit piece repeats it, and the copies drift), and the project's glossary from software-analysis (it says what a term means, not how to translate it, and reading it would join two capabilities, point 24's work; later, a notation's term could anchor to the analysis term it translates).

**A translation anchors to its source. Agreed (31 October).** After the Czech version was made, an edit to an English slide left its Czech page out of date without a sign. pkit already has the means: an artefact anchors to what it rests on, the change check flags it when that changes, and an anchor can name a part of a YAML file by its key path (COR-071, proposed in PR #2420).
- **`piece.yaml` names the source language** (`source: en`); the others are its translations.
- **Each translation anchors to its source, page by page** (`content.en.yaml#slides/install`), written by the capability when a language or a page is added, never by hand.
- **An edit to an English page flags the Czech file**, naming the page.
- **The translator is the fixer of translations** (DEC-056): it is read-only and owns no files, as a fixer must. After a merge it proposes the new Czech for each flagged page, and the person accepts, rewords or refuses each one in a batch, which is the native-speaker review (9).
- **A delivered piece does not move**, being locked; a draft's pages are translated again on demand.
- **It needs #2416 built.** The first slice keeps its two languages in step by hand.

Set aside: a record of the capability's own, a fingerprint of the English kept with each translated page and listed by `pkit visual check` (it works before #2416, but it is a second mechanism beside pkit's, unseen by the reviewers and the fixers), and no tracking at all (every change translates the whole file again, rewriting reviewed Czech).

Point 13 is decided.

### 8. The starter library (1 November)

**The question.** Which components the capability ships in its starter library, how it decides each one, and which themes the neutral brand ships.

**The maintainer's direction (31 October).** The agent first proposed a small starter: six blocks, no patterns, each pattern added once a local component had recurred about three times. The maintainer wants a wide starter from the beginning, since a wide library is more likely to be reused, built carefully, logically, justifiably, and ahead of need.

**The agent's first draft.** The starter organised by the job a visual does, from PowerPoint's SmartArt categories, Dan Roam's "when" and Gene Zelazny's comparison: ten patterns (`list`, `steps`, `cycle`, `tree`, `layers`, `hub`, `connections`, `matrix`, `compare`, `timeline`) and eight blocks (`card`, `chip`, `connector`, `note`, `stat`, `quote`, `terminal`, `figure`), with data charts named as a later wave. Each component would carry a written justification and pass an admission bar, and would have a status, `experimental` or `stable`.

**The critic's review.** The direction was taken as given. Its findings:
- **The evidence was mapped wrongly.** `fanout` is a pipeline with one parallel stage (gen.py, lines 70 to 72), not a hub. `files` shows real files side by side (lines 1088 to 1091), not a tree. The only kinds that recurred, `wired` (4 slides) and `map` (3 slides, a table), had no family. Nor did the structure the talk repeated most: a list or diagram beside a real exhibit (a terminal, a file), joined by ties, in eight kinds (`wired`, `rules`, `checklist`, `sockets`, `answers`, `files`, `install`, `slice`). That is evidence shown beside its claim (Michael Alley), which RS-COMM-001 already rests on.
- **The diagnosis was contradicted.** The draft blamed the generator for making one-offs easier than components, but gen.py offered Mockingbird's components as ready kinds (`cards`, `compare`, `actors`, `code`, `steps`), one line of YAML away, and no slide used them. Likelier causes: the job never came up; the forms did not fit the message (`step_card` was made from `stage` rather than use `step`); and "a new message may look new" (RS-VISUAL-004).
- **Some patterns cannot be library data yet.** A `cycle` and a radial `hub` need sine and cosine, which the formula language lacks (point 21); `connections` is a graph, whose positions come from a helper (point 22); a top-down `tree` needs a tree layout, while the tree tool of point 21 is the indented file tree.
- **Jobs were missing:** a table; an exhibit with notes on it; containment and boundaries; groups; pairs, such as problem and answer; a flow that branches or splits and joins; a visual equation (A + B = C, as in `wired`); overlap; and, for docs, sequence, swimlane and state diagrams. Use case 13's four diagrams must be checked too.
- **Blocks were missing:** `artefact` (one of the three blocks the talks reused), a legend (RS-VISUAL-006 needs one), source code, a callout, an icon. `figure` clashes with the figure top component, whose layout has a caption slot.
- **Nothing bounds the options**, so a pattern could grow into a small language; and the admission bar rested on what is not built (the reviewer, #2416, the output scale, the Mural font profile, the neutral brand).
- **The IBM library could duplicate the starter.** If `stage`, `link` and `artefact` stay IBM components while the starter adds its own, the maintainer's pieces use IBM's and the starter goes unused, as Mockingbird's components did. A brand is "not a fork of the components" (4g).
- **The taxonomy was thin and leaned to slides.** Better: Lohse, Biolsi, Walker and Rueter, "A classification of visual representations" (Communications of the ACM, 1994), eleven categories found by people sorting graphics; Yuri Engelhardt's syntactic principles (linking, containment, grouping, lining up, proportional size) as a check of the grammar; SmartArt, Google Slides and Nancy Duarte's *slide:ology* as the practitioners' cross-check.
- **A status as rules have it is a false analogy:** a proposed rule binds nothing, so an experimental component would be unusable. Better precedents: GOV.UK's and Carbon's experimental components, with `deprecated` added.
- **COMM cannot judge a block**, which says nothing on its own (4c); and a shipped library is tested in stress languages (long compounds, diacritics), not project-kit's English and Czech.
- Its alternatives: two gates (C1); versions per library only, with a `starter-labs` library (C2); a mapping table of all the evidence against the taxonomy (C3); a log of misses (C4); patterns as thin defaults over layout operators (C5); a build order tied to the first slice (C6).

**The agent's revised plan (1 November)**, decided one part at a time:
1. **A list of jobs** from Lohse et al., cross-checked with SmartArt, Google Slides and Duarte, with a table in this note mapping all the evidence to it: the Friday talk's kinds, Mockingbird's components, software-analysis's diagrams, typical doc figures. Jobs with evidence come first; the others are the wave built ahead of need.
2. **A status per component** (decided below).
3. **Patterns as thin defaults over layout operators.** A page that does not fit is built from blocks and operators.
4. **A log of misses:** for each local component, which starter pattern its designer considered and why it did not fit. It measures whether the breadth works. (Skipped by the maintainer, see below.)
5. **A build order:** blocks; then the patterns that need only decided tools; then those that need new tools (a circle, a top-down tree, graph positions).
6. **The IBM library styles the starter's blocks** rather than keep its own.

**A component's status is its library owner's mark. Decided by the maintainer (1 November).** The agent proposed two gates: a component enters as `experimental` with no use needed, and becomes `stable` once about three pieces use it, across at least two kinds of work. The maintainer disagreed with the count: a component becomes stable when its author marks it stable. This follows GOV.UK's and Carbon's practice, where the team that owns a component decides it is ready.
- A component enters a library as `experimental`, once it passes the admission bar: its job, the established form it follows and its source, its fields and options, the machine checks, its reference renders, and a review. It needs no use first.
- It becomes `stable` when the library's owner marks it so, in its file. No count of uses and no check decides it. How many pieces use a component is information the owner may look at, never a condition.
- The owner may mark it `deprecated` in any release, and it is removed in the next major one (4c).
- This holds for every library: the starter's owner is project-kit, a project's own library's owner is that project.
- **It revises decided points.** 4c's outcome added patterns "only when a real talk needs them": the starter now adds them ahead of need, each entering as experimental. The Names section promoted a local component once it recurred about three times: recurring is a reason to promote it, not a condition, and the owner judges. Point 21's rule, a helper script becoming an engine tool after about three uses, is about the engine's code and stays.

**What each status promises. Agreed (1 November).** The critic noted that a wide starter needs this settled first: if an experimental component could change only in a major release, every pattern built ahead of need would be a promise from its first day.
- **Experimental** may change in any release of its library: renamed, reshaped or removed. A piece that uses one is told so when it renders, as a note, never a failure; its lock protects it as it protects every piece.
- **Stable** changes in a breaking way only in a major release of its library. Breaking means removing or renaming a field, an option or a part, or changing what one means. A change to how it looks may come in a minor release; a piece moving to it still gets the before-and-after (4j, 4i).
- **The promise is checked, not trusted.** When a library is released, a check compares each stable component's fields, options and parts with the previous version's, and refuses a breaking change outside a major release, as Carbon's snapshot tests do.
- **It narrows point 20:** "a major removes or renames" holds for stable components; an experimental one may be renamed or removed in a minor release.
- Set aside: experimental components changing only with a migration note in a minor release (the cost of every wide addition comes back to the starter's owner), and no status at all, with unproven components in a separate `starter-labs` library that pieces lock like any other.

**The evidence, slide by slide (1 November).** The first list of jobs failed the critic's review: it mapped slides by what the generator could draw, or by how they look, not by what each delivered slide shows. So every slide of the Friday talk was broken into the arrangements, blocks and layout operators it uses, read from its content and from the branch of the generator its fields take; with Mockingbird's components, software-analysis's four diagrams and project-kit's own doc figures beside it (kept in the agent's workspace while point 8 is open). What it found:
- **A real exhibit is the talk's main structure.** 15 of 23 slides carry a terminal: as the whole picture on 6, beside a diagram on 6, inside a part on 6.
- **13 of 23 slides have a second row under the picture:** reasons on 6 (lined up with the columns only on the 3 `map` tables), cards on 5, exhibits on 2.
- **Tables have the most evidence across sources:** 5 Friday pictures and 4 Mockingbird slides.
- **No delivered slide needs** a circle, a graph layout, a chart or a drawing made elsewhere; point 21's tree tool has no delivered use (`install` shows `tree` output as text).
- **project-kit's doc figures are all graphs:** 59 Mermaid fences (28 flowcharts, 22 class diagrams, 9 state diagrams), of which only the 8 linear ones fit the decided operators; the rest need point 22's helper.
- **Gaps in the decided tools** the slides show: rows lining up across sibling cards (point 19's later), setting one item apart (the marked step, the first outcome), and wrapping into rows.
- **Sources, verified:** Duarte's abstract concepts (*slide:ology*, chapter 3: flow, structure, cluster, radiate) fit the jobs best; Lohse et al.'s structure and process diagrams describe physical objects, so they set only the scope (what is a pattern, a chart, a map or a picture); Engelhardt's own terms are lineup, linking by a connector, containment by a container, spatial clustering, separation by a separator, positioning in a meaningful space, superimposition.

**A picture with something beside it and a row under it: a starter pattern, `panels`. Decided by the maintainer (1 November).** The second list of jobs made "beside" and "under" optional slots of every layout. The critic found it fails on the case it cited: on the `skills` slide the command's output lines up with the marked step and an arrow joins them, and a layout, drawn by a brand that cannot know which pattern fills its `visual` slot, can do neither; a component reaches only its own parts and those below it (point 19). It would also have changed the foundations' layouts, which change rarely, and made every brand draw each layout with and without each slot.
- **What it is:** a starter pattern in the layout's one `visual` slot, holding a row of panels, each with an optional heading and any component in it, and an optional row under them across the whole width. It computes the widths (equal, or one wide and one narrow, by name), the gaps and the heights, and lines a panel up with the one beside it, by its top, middle or foot, or with a marked item, drawing the arrow to it. Since it contains both panels, it may.
- **Data, like every component** (4a): the engine knows nothing called `panels`. It is written with the engine's general tools (repeat, stack, align, equal sizes, references, lining up with one item or one line), so a project may ignore it, write its own or publish another, and a better one is a library release.
- **It covers** about 14 of the talk's 23 slides: every one with something beside the picture, a row under it, or files side by side. The 3 `map` tables' reasons, lined up with their columns, are the table's own part (point 21's optional part). It works the same in a deck, a doc figure or a poster, and lifts out whole (4f). Panels go in one row with one row under; anything placed otherwise is a local component, and one `panels` may sit in a panel of another.
- **The name:** the talk's own word for these parts; Engelhardt's multipanel display; a figure's panels (a), (b), (c) in a paper, as in comics and dashboards. The terminal block is never called a "terminal panel". Set aside: `layout` (level 6's name since the naming pass, so `layout: slide` and `use: starter/layout` would sit in one file), `arrangement` (what every pattern is, by the definition of level 5), `multipanel` (jargon), `split` and `columns` (two, and no row under; `columns` also collides with the layout grid), `grid` (the layout grid), `composition` (too general, and pkit's process composition), `exhibit` (one kind of content).
- **Set aside:** optional `beside` and `under` slots in every layout, and both together, the slots for placing and `panels` for tying across (two ways to do one thing).

**The starter's patterns, by job. Agreed (1 November).** Built from the evidence above, by Duarte's forms, after two reviews by the critic. The second found citations mapped wrongly, boundaries that broke on cases chosen to break them (a 2 × 2 by quadrant is a table; Now, Next, Later is a timeline; a fan-out that never joins again is `branches`), and the task board covered by no pattern.

Wave 1 has evidence and needs only decided tools (F a Friday slide, M Mockingbird, SA software-analysis, D project-kit's docs):

| Pattern | The question it answers | Form | Evidence | Options |
|---|---|---|---|---|
| `panels` | What goes beside the picture, and under it? | multipanel (Engelhardt) | about 14 F slides | widths; line-up; a row under |
| `steps` | In what order does it happen? | Flow: linear | F `found`, `agents`, `skills`, `pm`; M P2-04, P2-10; SA journey flow; D 5 journey flows, 2 linear lifecycles | across or down; numbered; one step marked; a stage done in parallel |
| `branches` | Where does one thing lead to several that do not join again? | Flow: divergent | F `ideas`; M P2-04 | outcomes labelled; one set apart |
| `equation` | What do these parts make together? | Flow: convergent | F `agentswired`, `se`; M P1-05, P1-07 | the signs; any component as a part |
| `layers` | What rests on what? | Structure: layers; pyramid | F `fits`, `sessions` | stepped or straight; relations beside |
| `table` | What is in each row and column? | Structure: matrix; grid | F the 3 maps, `addons`, `docs`, `opening`; M P1-04, P1-06, P2-09, P3-01 | arrows none, between heads or across rows; a colour per column or row; reasons under each column |
| `groups` | Which items belong together? | Cluster: enclosed | F `decisions`, `schemaslook`, `connect`; SA the journey's group, the chain's areas | a container, or a heading with a bar |
| `network` | What is connected to what? Nodes in columns | Cluster: linked; relationship | F `checked`, `connect` | two or three columns; one tie set apart; tips or none |
| `list` | What are the items, each of equal standing? | list | F reasons on `docs`, `addons`, `connect`; cards on the 4 `wired` slides, `pm`; M P1-01, P1-03, P2-02, P2-03 | a colour bar; numbered; an aside as the last item, through its own component |
| `timeline` | When does each thing happen? | timeline | M P3-03, P1-09 | periods evenly spaced, each labelled; items under each |

Wave 2 is built ahead of need on decided tools, each with a named use: `tree` (indented: a file tree with owners, an outline); `annotations` (what each line of an artefact means: a config file explained in a doc; M P2-05); `overlap` (what two or three things share; outlines until the scene has opacity); a cycle, as `steps` with an arrow back (plan, do, check, act).

- **Boundaries:** a list has no sequence (a ranking is a numbered list), steps follow one another, a timeline says when; steps may split and join again, branches split for good, an equation makes one of several; a table holds values in named rows and columns (a 2 × 2 by quadrant is a table with its headings as axes), groups show belonging by enclosing, a tree parent and child by indentation, a network any relation by lines; layers are whole levels; `panels` shows a picture with what proves it, `annotations` an artefact with a note per line.
- **Left out on purpose:** what waits for a tool, as points 21 and 22 decided (a ring and a hub on a circle, a top-down tree, free graphs, which are most of project-kit's doc figures, a timeline to scale, charts); software notation (states, classes, sequence, use cases, C4), the open question of a notation for software work; the task board (F `schemas`), a local component.
- Each pattern is tested before it enters in stress languages (long compounds, diacritics), not only project-kit's English and Czech.

**A pattern arranges; an item component draws each item; the item says what it is. Decided (1 November).** The question was how one item of a list is set apart (the marked step, the dropped outcome, a broken tie, the aside ending a row of cards) and how each item gets its own colour. The agent first proposed two mechanisms: values carried on the item, and an option on the pattern naming one item by key, which the engine would draw marked. The critic found that one mechanism covers every case in the evidence with no new engine tool, that the draft's colour option listed pkit's own concepts in a starter component (against 4g and COR-014), and that the aside is a block of its own, not a list item. The maintainer then proposed that a pattern take the component that draws its items as a parameter. Put together:
- **A pattern arranges its items:** their order, direction, numbers, the arrows between them, equal heights.
- **An item component draws each item.** The pattern names a default (`item: starter/card`); an item may name its own (`use: starter/note`), so the aside ending a row of cards is the row's last item drawn by another component. Each item's fields are the item component's fields, checked by its schema (4f). It is Figma's instance-swap property, and React's `renderItem`. It answers the evidence: the talk reused small blocks (`stage` 15 times, `link` 17) and rebuilt arrangements, even making `step_card` from `stage` rather than use Mockingbird's `step`; now one `steps` draws stages, cards with a picture, or a local component.
- **The item says what it is; the item component decides how it looks.** An item carries a state its component declares (`marked`, `broken`, `dropped`), whose look is roles of any type: colour, a dashed line, space (4e, 4g correction 3). Or it names a concept from the piece's notation (`concept: agent`), which the notation maps to a colour and an icon; the starter never lists a project's concepts.
- **A component that must reach one item names it by its id,** with point 19's lookup: `panels` with `line-up: {item: create}`. On the skills slide the id appears twice, on the marked step and in the line-up; a check warns when they differ.
- **What a pattern needs from its items:** most need only the frame every component has (arrows attach to its edges, `panels` lines up with its middle). A pattern that needs more, such as `annotations` needing each line of its artefact, declares it, and the check refuses an item component that does not expose it (19).
- **Nothing new in the engine:** no new tool, no comparison in formulas, no fixed names the engine knows. Ids are required on items that can be reached, and unique within their list; the engine checks both, since JSON Schema cannot.
- **It revises the agreed list:** `list`'s option "the last set apart" is gone; the aside is an item with its own component.
- Set aside: the pattern naming the item (`mark: create`), drawn marked by a new engine tool (the id once, but two places setting one item's look); comparisons in formulas (the start of a programming language, which the architect's review ruled out).

**Point 11's wording says "component". Agreed (1 November).** RS-VISUAL-004's middle sentence said "where a library has a pattern for the job", and its own example is the terminal, which the levels make a building block, not a pattern; point 11's table called the terminal and the yellow note patterns. "Component", which the naming pass defines as anything from a tag to a whole layout, widens the rule back to what it was meant to catch. The rule's other point stands: a new message may look new, and a piece makes a local component where no library component fits. "Takeaway" is dropped as the yellow note's name: it is an aside, not the slide's main message; its name comes with the blocks. Set aside: keeping "pattern" with a second sentence for blocks.

**The first slice builds starter components. Agreed (1 November).** What the slice's four slides need is built as experimental starter components: the patterns `layers` (the pyramid), `panels`, `groups` (the capability holding its slots), `network` (contributors joined to the slots) and `list` (the reasons), and the blocks they draw with (a card, the terminal, a connector). The slice is the cheapest test of what point 8 decided: patterns arranging items an item component draws, `panels` lining a terminal up beside a diagram, one pattern inside another, states and notation concepts; local components would test the engine and leave the model unproven. Being experimental, they may still change with what the slice teaches. The length test against `gen.py` counts the pattern files with the content, so no length hides in the library. `sockets` is made a second time as a doc figure, in light and dark, from content alone, to show the patterns serve a second piece. The rest of the starter is built after the slice passes. Set aside: local components first, promoted later (the work twice, the model untested); the pyramid as a pattern and `sockets` local (it is the slide that tests composition).

**How far a pattern's options go. Agreed (1 November).** The critic warned that a pattern per job with options can grow into a small language, and every option multiplies the reference renders.
- A pattern's options choose only its arrangement: direction, numbering, which arrows, widths, a row under. How an item looks is its item component's, so looks never add pattern options.
- Each option is one word from a declared list, never a free number or size (4e).
- About four options is the guide, not a limit. Past it, the pattern probably does two jobs and is split; a page that needs more than a pattern offers is a local component built from the starter's pieces. The library's owner judges, as with stable; the reviewer flags a pattern past the guide.
- Reference renders cover each option value once, plus the combinations the evidence uses, never every combination.
- The agreed patterns fit: `steps` (direction, numbered, a stage in parallel, an arrow back), `table` (arrows, a colour per column or row, reasons under each column), `panels` (widths, line-up, a row under).
- Set aside: a hard limit enforced by a check (it would refuse a fifth option that is right), and no guide.

**No log of misses, for now. Decided by the maintainer (1 November).** The agent proposed that each local component record which library component it considered and why it did not fit, listed across pieces for the library's owner. The maintainer finds it unnecessary for now and skipped it. Whether the breadth works is judged by the owner, as stable is.

**The build order, and the tools each pattern needs. Agreed (1 November).** Each pattern was checked against the decided tools: all fit but `list`, which needs one new layout operator, wrap (items flow into the next row when one is full; Mockingbird's five cards in rows of three and two needed it). `table` works with equal columns or named shares; columns sized to their content need rows lining up across siblings, which point 19 left for later.
1. The first slice, as decided: `layers`, `panels`, `groups`, `network`, `list` in one row, and the card, terminal and connector blocks.
2. The rest of wave 1: `steps`, `table`, `branches`, `equation`, `timeline`; wrap is added here, with `list`, under flexbox's name, as the architect advised for the layout operators.
3. Wave 2: `tree`, `annotations`, `overlap`, and `steps`' arrow back.

Set aside: no wrap (a long list becomes a table or a local component); building by job rather than by evidence.

**Still open in point 8, in this order:** where the Friday talk's twelve new reusable pieces go (`terminal`, `term_image`, `highlight`, `pstage`, `step_card`, `kind`, `kind_group`, `tree_bar`, `tree_tag`, `tree_note`, `divider`, `talk_cover`); whether a notation for software work ships, and as which kind of library; a legend and icons, so colour is never the only signal (RS-VISUAL-006); the neutral brand's themes (`teal-calm`, `warm-paper`, their modes) and fonts.

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

**The smallest first slice.** Four slides of the Friday talk, each testing one part: a plain slide with a long lead (frame, tokens, text measuring); `pyramid` (repetition and formulas, colours as roles); `sockets` (connectors and references between elements); a terminal slide (Mural's missing monospace font and the image fallback). Each in English and Czech, in `carbon-light` and `teal-calm`, as one scene rendered to SVG and pushed to Mural; then a PDF from the SVG, and a board edit taken back. Optionally `sockets` lifted out as a doc figure in light and dark. It passes when one scene feeds both renderers with no Mural-only geometry, text fits on both, the data for `pyramid` and `sockets` is no longer than `gen.py`'s code for them, a theme switch changes only values, and a Czech edit on the board lands in the Czech material file. Left out: fetching, versions, locks, states, previews, Figma, agents. (Refined by point 8, 1 November: the slice builds what its slides need as experimental starter components, the length test counts the pattern files, and `sockets` as a doc figure is no longer optional.)

## Names

**Names are confirmed together with the maintainer** (30 October). The note's terms are working names until the maintainer confirms them. The maintainer said to be careful about picking names such as "one-off" or "talk".

| Working name | Meaning | Status |
|---|---|---|
| visual communication | what the capability is about; "visual work" before the naming pass | decided (naming pass) |
| logical layer | the source: content, components, libraries | kept (naming pass) |
| content | what to show, in one language: text, lists, image references, no layout; "material" in the points before the naming pass | decided (naming pass) |
| renderer, projection | what draws the logical layer; the relation between the two | kept (naming pass; "adapter" ruled out, as pkit uses it for the harness) |
| component | anything from a tag to a whole slide layout (point 4b) | kept (naming pass) |
| pattern | level 5: a library component that is a whole arrangement filled with content, such as a pyramid, a timeline or a comparison; "recipe" and "kind" before the naming pass | decided (naming pass) |
| option, variant | a choice a component declares, such as a card's tone | kept (naming pass; Figma says "variants" and "component properties") |
| design tokens, raw values, roles, component tokens | the design language as data | kept (naming pass; DTCG; Material 3's "colour roles") |
| theme, mode | a set of values; light or dark | kept (naming pass) |
| brand | the values library a piece names, such as IBM, DAM or neutral: its token values, layouts, logo and brand-only parts; "context" before the naming pass | decided (naming pass) |
| frame | an element's box: `x`, `y`, `width`, `height` (points 4h, 19); before the naming pass, also level 6 | decided (naming pass): this meaning only |
| recipe, kind | level 5 before the naming pass | replaced by "pattern" (naming pass) |
| one-off | level 7 before the naming pass | replaced by "local component" (naming pass) |
| local component, library component | a component made inside one piece, in its `components/` folder (level 7); a component a library publishes. A local component that recurs about three times is promoted to a library component (revised by point 8: recurring is a reason to promote, not a condition; the library's owner judges) | decided (naming pass; Figma's terms) |
| experimental, stable, deprecated | a library component's status: entered and may still change; marked ready by its library's owner; on its way out, removed in the next major release (point 8) | decided (point 8; GOV.UK's and Carbon's labels) |
| talk | level 8 in the first drafts | replaced by "piece" (naming pass) |
| deck | the top component of a presentation | kept (naming pass; Slidev, Marp and Keynote users say "deck") |
| library | a named, versioned set of components, values or notation that is shared, and names the libraries it builds on | kept (naming pass) |
| brand, component library, notation | the three kinds of library (point 4g): values, structure and meaning before the naming pass | decided (naming pass) |
| foundations, interface, starter | the foundations hold only the interface (role names, top components, layouts, slots); the starter holds the capability's opinionated components (point 18b); "core" before the naming pass | foundations decided (naming pass); interface and starter kept |
| notation | the meaning library a piece names, such as pkit: each of its concepts mapped to roles (colour, icon, shape), and its own marks (logo, icons); "subject" before the naming pass | decided (naming pass) |
| layouts, slot, entry point | level 6: the layouts a top component declares and a brand supplies, such as a deck's cover, section and slide ("named layouts" before the naming pass); a place in a layout; a named way into a library, such as `ibm/deck` (point 4g) | layouts and slot decided, entry point kept (naming pass) |
| shared, per brand, per piece | the three scopes; "shared core" before the naming pass | decided (naming pass) |
| draft, delivered, living, adapted | a piece's states: its lock follows the newest at every render; never moves; moves through a proposal after a library release; moves only when a person upgrades it on purpose (points 4d, 4j); "drafting" and "reused" before the naming pass | decided (naming pass) |
| piece | level 8: one finished item made from components, such as a deck, a standalone diagram, a doc figure or a poster; its content plus its lock | decided (naming pass) |
| lock | the library versions a piece uses (points 4j, 4i, 18a) | kept (naming pass) |
| engine | the code that computes the scene: tools, formulas, text measuring | kept (naming pass) |
| scene | what the engine computes and every renderer draws (point 4h) | kept (naming pass) |
| font profile | the fonts for a group of renderers, set by the brand (point 18d) | kept (naming pass) |
| preferred size, actual size | an element's two sizes: the one it prefers, from its content, and the one its parent gives it (point 19); "asks" and "gets" before the naming pass | decided (naming pass) |
| exposed part | a part a component lets its ancestors point at (point 19); "public anchor" before the naming pass | decided (naming pass) |
| helper script | a script run while preparing, writing a checked local component (point 21) | kept (naming pass) |
| model | the file of a system's elements and relations that several views read (point 22) | kept (naming pass) |
| contract, coverage, fallback | the visuals another capability needs drawn; how many a library draws; the drawing used for the rest (point 22) | kept (naming pass) |
| graphic-designer, graphic-design-reviewer, translator | the capability's agents: the producer, the reviewer of pieces, and the translator that returns text (point 9) | decided (point 9) |

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
  1. It goes to a library its author owns: a component library, or the starter if every adopter could use it, or a brand library if only that brand uses it. Never the foundations, which hold only the interface.
  2. A small building block becomes a component (level 4); a whole arrangement filled with content becomes a pattern (level 5).
  3. It is generalised on the way: fixed texts become content fields, one-time choices become options, and every colour a role.
  4. It is added in the library's own repository and released as a new version, since a project's copies are read-only.
  5. Each piece switches on purpose: `upgrade` brings the version, the content's `use: components/pyramid` becomes `use: <library>/pyramid` after a before-and-after, and the local copy is removed. Delivered pieces keep theirs.
  6. A local component a helper script wrote waits for its script to become an engine tool (point 21), then is promoted as data.

  No `promote` command is planned: generalising needs judgment, so it is the agent's work (aspect 9).
- **Level 6: "layouts"; "frame" keeps one meaning, an element's box.** Chosen by the maintainer after an example. The note had used "frame" for both a brand's templates (4c, 4g) and an element's computed box (4h, 19), and a designer also hears Figma's frame, any container. "Layouts" is PowerPoint's, Keynote's and Google Slides' word ("Title Slide", "Section Header"), and the note already called each one a named layout. The foundations declare a top component's layouts and their slots; a brand supplies how each is drawn; the content picks a layout per page and fills its slots; the scene gives each element a frame. Ruled out: "master" (PowerPoint's parent of the layouts, and InDesign renamed its master pages parent pages) and "template" (a file one starts from; atomic design's page skeleton; every component in today's mural-boards tool).

  ```yaml
  # libraries/foundations/1.4.0/deck/deck.yaml: which layouts a deck has
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
- **"Brand" for the values library a piece names** (IBM, DAM, neutral), as `brand: ibm/deck`. Chosen by the maintainer. The design-tokens format the capability adopts (DTCG's Resolver, point 4f) uses "context" for one setting of any switch, light, dark or brandA alike, so the old word would mean light in the token files and IBM in the pieces. "Brand" is the word of multi-brand design systems, of DTCG's own examples, of Quarto's `_brand.yml` and of the research's Infinum case, and matches "brand-only parts" and the brand guide. DAM is a client's brand; neutral is an unbranded one. The points before the naming pass say "context"; read it as brand. Ruled out: "theme" (the values only, without layouts and logo) and "system" (Spectrum's switch, which collides with design system).
- **"Notation" for the meaning library a piece names** (pkit), as `notations: [pkit]`. Chosen by the maintainer. It is the established word of diagramming for a fixed set of symbols and what each means (UML, BPMN, C4, ArchiMate, crow's foot), and it names what the library brings rather than the piece's topic, which "subject" suggested. A piece about two projects names two notations. The points before the naming pass say "subject"; read it as notation. Ruled out: "theme" (Structurizr's word for its icon sets, but ours is values), "encoding" (information design's word, which developers hear as text encoding) and "legend" (the visible key on a figure, not the rules behind it).
- **The three kinds of library: a brand, a component library, a notation** (point 4g's values, structure and meaning). Chosen by the maintainer for the structure kind, such as the foundations, the starter or a docs team's `docs-kit`: the established term (NN/g's parts of a design system; Carbon's and Material's own), which says what is inside and pairs with "library component". Ruled out: "kit" (Figma's "UI kit", Material's and Carbon's design kits), the one-word term, because it clashes closely with project-kit's "kit-owned" and "kit-shipped"; "stencil" (diagrams only); "components" (uncountable as a name, the content of every library, and the piece's `components/` folder); "structure" (says nothing of what is inside).
- **The established names are kept,** confirmed by the maintainer as one batch: component, library, deck, theme, mode, design tokens, roles, component tokens, variant, option, renderer, scene, lock, model, engine, helper script, font profile, contract, coverage, fallback, starter. The table marks them "kept".
- **The maintainer left the remaining names to the agent** (31 October), trusting its choices from the domain and his preferences: established terms, plain for non-native speakers, one word where one serves, a clash with pkit flagged rather than avoided. The agent chose:
  - **The states: draft, delivered, living, adapted.** "Draft" is the state's name everywhere work is written (documents, content systems, pull requests). "Delivered" stays: a talk is delivered, and so is a client's file. "Living" stays: the established "living document" and "living style guide". "Adapted" replaces "reused", which named an action: a piece copied from a delivered one and adapted for a new audience, its lock moved only when a person upgrades it. Ruled out: "final" and "published" for delivered (final suggests it can never be taken up again; published fits pages, which are living), and "repurposed" for adapted (marketing jargon). Flagged clash: pkit's harness adapter, a different word and meaning.
  - **Level 5: "pattern",** a library component that is a whole arrangement filled with content, such as a pyramid, a timeline or a comparison. The design-system term for a reusable arrangement of components (Carbon's and Atlassian's patterns; the pattern library NN/g names beside the component library). It replaces two names for one level: "recipe" (Brad Frost's, less known) and "kind". The points before the naming pass say "kind" or "recipe"; read it as pattern, and "kinds are data" (4a) as "patterns are data". Flagged clash: pkit's pattern extraction (COR-007), a related meaning.
  - **"Foundations" for the core,** the library that holds only the interface: role names, top components, layouts and slots (`foundations/deck`). The design-system term for the base layer every other part builds on (Carbon's, Atlassian's and Material's foundations). "Core" clashed head-on with pkit's own core (core records, core-owned files): a "core" library shipped by a capability would not be core-owned. The scope "shared core" becomes "shared". The points before the naming pass say "core" for this library; read it as foundations.
  - **"Preferred size" and "actual size"** for an element's two sizes (point 19), with the key `preferred:` in a component (`preferred: {height: =body.bottom + 24}`). The established pair of layout systems (the preferred size of CSS sizing, Swing and GTK; WPF's desired and actual size), plain for non-native speakers. The actual size is what a formula reads, so it needs no key. Ruled out: "asks" and "gets" (verbs, not names), "intrinsic" (from content only, while a preferred size may be a formula) and SwiftUI's "proposed" and "chosen" (the parent proposes, the reverse of ours).
  - **"Exposed part"** for a part a component lets its ancestors point at (point 19), with the key `exposes: [heading, body]`. Figma lets a component expose its nested instances to the outside, the same idea. "Public anchor" clashed with pkit's anchors (what an artefact rests on, under `anchors:` in front matter), and a key `anchors:` in a component file could be taken for them.
  - **Kept without a change:** "logical layer", "projection", "entry point" (a named way into a library, such as `ibm/deck`), "raw value" (a literal value, such as `#F1C21B`, which only a brand holds).

**A draft of the files** (31 October, not decided; it follows the decided points). `pkit visual new piece friday-talk --top deck --brand ibm/deck --notation pkit` writes two files; the rest appear when they are needed:

```
visual/                                  the capability's place in the project (a setting)
├── libraries.yaml                       each library's link and the versions present (4i)
├── libraries/                           read-only copies, fetched whole at their tag (4i, 18b)
│   ├── foundations/1.4.0/  starter/1.2.0/  neutral/1.0.0/  ibm/2.0.0/  pkit/1.1.0/
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
        ├── exports/                     every export, numbered, never overwritten (13)
        │   ├── versions.yaml            each version's date, state, lock and content hash
        │   ├── friday-talk.v1.en.pdf    delivered: committed, the freeze (18a)
        │   └── friday-talk.v1.cs.pdf
        ├── previews/                    working pictures and previews, never committed (13)
        └── renders/                     each renderer's record of what it last drew, committed (4h)
```

`piece.yaml`:

```yaml
schema_version: 1
top: foundations/deck             # its top component (4f)
brand: ibm/deck                   # the brand's entry point (4g)
notations: [pkit]
languages: [en, cs]
source: en                        # the language the others translate (13)
audience: developers new to pkit, mostly non-native English speakers   # who it is for (9)
medium: projected                 # where it is shown: projected, screen or print (11)
state: draft                      # draft, delivered, living or adapted (4d, 4j)
outputs: [pdf]                    # made per language, numbered in exports/ (13)
lock: {foundations: 1.4.0, starter: 1.2.0, ibm: 2.0.0, pkit: 1.1.0}   # (4i, 18a)
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
