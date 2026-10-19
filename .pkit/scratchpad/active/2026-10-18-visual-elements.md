---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-18
---

# Visual elements: diagrams, images, captured output and callouts

## The question

How do software-analysis and living-docs show diagrams and other visual elements, and keep them true as the software changes? And how does each project choose how they look? Issue #1770 asks for the design, and for the maintainer's decisions one at a time.

- **The elements:** diagrams, images and screenshots, console output, and callouts.
- **For each element:** how it is written, checked, kept true by anchors and friction, and drawn, and which component owns it.
- **The two layers:** content, which is true and neutral, and presentation, which each project configures.

The decisions the maintainer must take are at the end, in "Decisions for the maintainer".

## What the maintainer has decided

Three statements of 18 October, in the issue's body and its comments, bind this design. They are constraints here, not open questions.

- **The direction, in the issue's body:**
  - software-analysis supports diagrams by default.
  - living-docs supports at least images and diagrams, and other media where needed.
  - Rendering is configurable, and generated images are allowed.
  - Screenshots, console output and callouts are wanted.
- **A diagram is a view of truth held elsewhere:**
  - Its truth lies in decisions, requirements, use cases or code.
  - It states nothing that has no other home, and it anchors what it shows.
  - It is generated from that home where it can be.
  - Its text form is what gets edited and rendered.
- **Content and presentation stay apart:**
  - **Content stays neutral and true:** plain Markdown, diagram text, captured outputs and the standard callout syntax. Agents write, anchor and keep it true, and it carries no styling.
  - **Presentation is a layer each project configures:** its theme, how diagrams are drawn, how callouts and screenshots look, and optionally a documentation site.
  - **A sensible default needs no setup,** and reads right on GitHub as it is.
  - The note brings concrete choices, such as which site generator and how a theme reaches diagrams, each with a recommendation.

The issue's body also asks whether rendering is a role that a capability or the project provides (COR-053).

## Where things stand

The repository already holds several pieces this design builds on.

- **The backbone generates diagrams already.** `pkit process graph --mermaid` and `pkit connections graph --mermaid` print Mermaid from the wiring. They print on demand and store nothing.
- **software-analysis computes a view already.** `pkit analysis met-by` lists what meets each requirement. The requirement never stores the list (software-analysis DEC-002 point 7).
- **Only a Markdown file is a document.** The backbone's discovery reads no other file as an artefact (`friction_discovery.py`, citing ADR-056 point 2). So an image in a place is never a page, and never an unclassified document. A path anchor still reaches an image, by its bytes (COR-050 point 5).
- **A tool reads an analysis artefact's front matter only.** A body's parts serve readers and the check, never another tool (software-analysis DEC-001 point 1).
- **Views of the solution stay outside the analysis.** An architecture view, a context view included, names analysis artefacts by id, states none of their facts, and never anchors them (software-analysis DEC-001 point 11).
- **Only what a page anchors grounds its statements** (living-docs DEC-001 point 3, RS-LDOC-001).
- **A fact's home is a decision record the page anchors, or a page.** Any other artefact as a fact's home, "such as a rule, an analysis artefact or code", is "Not taken yet. It waits for a page that needs it" (living-docs DEC-001, Alternatives considered).
- **living-docs never runs the product.** Executed checks that follow the documentation belong to another component. Their results arrive through living-docs' reading-evidence point (living-docs DEC-001 points 6 and 7).
- **What living-docs' validation settles** is listed: a page's sections and its reader (living-docs DEC-001 point 6).
- **The checks skip fences and block quotes.** living-docs' structure check reads no `#` line in fenced code or a block quote as a heading. software-analysis's forms judge a list part by its items only (`_lib/forms.py`).
- **A generated copy may be stored where staleness fails validation.** The generated `depends-on` list is the precedent, "the discipline lock files follow" (COR-053 point 4). A journey's anchors, written from its steps and checked to match, are another (software-analysis DEC-001 point 4).
- **A component may keep held documents.** They are files of its own that are no artefacts, such as the analysis's revalidation records. No place reads them, and no measure counts them (COR-050 point 1).
- **A script-owned region can sit inside an agent-written body.** The provenance footer is the precedent: strip every copy, then write exactly one at the end (ADR-037).
- **A new accepted rule needs a new major of its set.** Every project's pin on that set then falls behind. No rule binds through it, and validation fails where enforced, until the project reviews the set and updates its pin (COR-051 point 7).
- **A capability's set may inherit another capability's set** only with a required dependency on it (COR-051 point 7). The backbone ships no method rule set yet.
- **A project cannot provide a role yet.** Roles a project publishes are left to a later refinement (COR-053 point 1). A project may fill a data point today, with a project file (COR-052 point 2).
- **demo-recording records terminal demos as video.** Its storyboard is executable Markdown (demo-recording DEC-001). Its parser, runner and validator run anywhere. Only its recording plugin needs macOS, iTerm2 and screen-recording permission (DEC-004).
- **Neither capability mentions diagrams yet.** The one exception is the analysis stamp, which ignores a file named like `UC-800-flow.svg` when it numbers.

## Established practice

Practice agrees on one point: the text source is the truth, and a picture is drawn from it.

- **Docs-as-code.** Documentation lives in the repository as plain text, is reviewed in pull requests, and is built by continuous integration. Text shows its changes in a diff. An image does not, so a reviewer cannot see what changed in it.
- **C4 and Structurizr.** C4 draws an architecture at four levels: system context, containers, components and code.
  - **A C4 system context** shows the system with the people and other systems around it. It is a view of the solution.
  - **Structurizr** keeps one model and derives every view from it, so two views never disagree.
- **Requirements models.** UML's use-case diagram draws actors joined to the use cases they take part in. A context diagram in requirements engineering, as Wiegers and BABOK use it, draws the system as one box among its external entities. Both describe the problem, not the solution.
- **arc42 and 4+1.** Both keep views of the solution apart from the requirements, with scenarios as the bridge. software-analysis DEC-001 point 11 follows them.
- **Diagram-as-code tools.**
  - **Mermaid:** text in a fenced block. GitHub and GitLab draw it with no build step. Site generators draw it with a plugin or a setting. A diagram carries an accessible title and description (`accTitle`, `accDescr`). Where no host draws it, the fence still reads as text.
  - **PlantUML, D2 and Graphviz:** text drawn by a renderer the project installs. GitHub draws none of them. PlantUML and D2 can include other files, C4-PlantUML often from a remote address.
  - **Structurizr DSL:** a C4 model, exported to the languages above or drawn by its own tools.
  - **Kroki:** one service, hosted or run locally, that draws most of these languages.
- **GitHub's own drawing.** GitHub draws Mermaid fences in files, issues and pull requests, and chooses their colours itself. It has no include, so one file's text never shows inside another file.
- **The standard callout syntax.** A block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`. GitHub draws it as a callout, and so do Obsidian and VitePress. Other site generators read it with a plugin. Where nothing draws it, it reads as a block quote with a marker line.
- **Generated diagrams.** A tool draws from a model the project keeps anyway, as `pkit process graph` draws the wiring. Nobody edits the diagram, so it cannot drift.
- **Captured console output, in two families.**
  - **Test the page:** the page holds each command and its expected output. A runner runs the commands and compares. Python's doctest, cram and trycmd work this way. trycmd reads `console` fences in Markdown files, and can overwrite the expected output.
  - **Generate into the page:** a marked region holds or names a generator, and a command fills the region. cog, markdown-magic and embedme work this way, and cog has a check mode for continuous integration.
  - **Output that varies** from run to run, such as times and paths, is marked with placeholders or normalised before it is written.
- **Screenshots and recordings from scripts.** VHS runs a `.tape` script without a screen and writes a GIF, a video or a still. asciinema records a terminal as text. Playwright takes screenshots of web pages, and can mark elements on them. Each re-runs on demand, so a new capture proves the flow still works.
- **Documentation sites.**
  - **Material for MkDocs** entered maintenance mode in November 2025. Its team's successor, Zensical, reads `mkdocs.yml`. Both draw Mermaid in the site's fonts and colours, light and dark, from the site's settings.
  - **VitePress** reads the standard callout syntax natively, and draws Mermaid with a plugin.
  - **Docusaurus** reads MDX by default, draws Mermaid with its own theme package, and reads the standard callout syntax with a plugin.
- **Accessibility.** An image that carries meaning needs a text alternative (WCAG success criterion 1.1.1). A decorative one needs an empty alternative, so a screen reader skips it. Time-based media need one of their own (WCAG 1.2). Mermaid's `accTitle` and `accDescr` give a diagram its alternative.

## Forces

- **Agents write text.** An agent writes, diffs and reviews a diagram's text source. It cannot edit an image reliably.
- **Reviewers read diffs.** A changed image shows as a binary change. A changed source shows what moved.
- **GitHub is the default reader's view.** What GitHub draws needs no build step. Anything else needs a rendering step and a committed image, or a published site.
- **Committed images cost.** Each re-render adds an image to the history for good.
- **Friction reads bytes.** A path anchor on an image flags its page at every re-render, even when nothing the page says has changed.
- **Each capability stands alone.** living-docs works without software-analysis, and the reverse (living-docs DEC-001 point 9, software-analysis DEC-001 point 10). A page that shows an analysis diagram must not make either depend on the other.
- **Checks run offline and alike everywhere.** Validation and the friction checks reach no network, and give one answer for the same inputs (COR-050 point 2). A check whose answer depends on which renderer is installed breaks that.
- **Universal applicability.** What a capability ships must suit any adopter (COR-014).
- **Nothing ahead of need.** A mechanism is extracted when it recurs (COR-007).
- **Rule majors cost every adopter.** Each new major of `LDOC` or `SAN` stops its rules binding in every project until the project updates its pin (COR-051 point 7). So rule changes ride together.

## The two layers

The maintainer's split decides where each part of a visual element goes.

| Content: true and neutral | Presentation: each project configures |
|---|---|
| a diagram's Mermaid text, its `accTitle` and `accDescr` | colours, fonts, light and dark, how a diagram is drawn |
| a diagram source in another language | the renderer and its settings file |
| an image file and its alt text | framing, size and shadow on a site |
| a capture script, and the image or output it writes | the capture's window size, scale and theme |
| a `console` fence with commands and output | how a code block looks |
| a callout in the standard syntax | how a callout looks |
| | a documentation site, and its navigation |

**What follows:**

- **No styling in content.** No `%%{init}%%` directive, `classDef` or `style` line in a fence. A theme change is then never a content change, so it flags nothing.
- **GitHub's default is GitHub's look.** A project cannot theme what GitHub draws without styling in content. The default reads right as it is, which is what the maintainer asked.
- **A theme reaches a diagram through the presentation layer only:**
  - **On a site,** through the site's settings. Zensical and Material draw Mermaid in the site's own colours.
  - **In a committed image,** through the renderer's settings file, which the image's fingerprint covers ("How a produced file relates to its source").
- **A site keeps the spaces apart.** A site for the user space never includes the internal root, since user navigation never leads into technical material (living-docs DEC-001 point 1). So a site is built per space.
- **A site serves its whole space, wherever its files lie.** A generator such as Zensical serves only the files under its one folder of pages. Three cases cross that folder:
  - **A page outside its space's root,** such as the top-level README a project assigns to the user space.
  - **A user-space image or page** that a technical page shows or links. The separation rule runs one way, so this is allowed.
  - **A technical site's link to a user page,** which must reach the user site.

  So a site's build gathers its space's pages and the assets they show, and a generator that cannot is ruled out (decision 8).

## The pieces

Each piece below says how it is written, checked, kept true and drawn, and which component owns it.

| Piece | Written as | Checked by | Kept true by | Drawn by |
|---|---|---|---|---|
| Diagram in a page or an artefact | a `mermaid` fence | its `accTitle` and `accDescr`, offline | anchors on the homes of what it shows | GitHub, or the site |
| Diagram source file and its image | a source file, and an image a renderer writes | the renderer, and a fingerprint compared offline | anchors on the source, never on the image | the project's renderer |
| Diagram generated from the analysis | nothing: a command writes it | a fresh copy compared offline | computed from front matter | GitHub, or the site |
| Image or screenshot | an image file, shown with `![alt](path)` | reader-review | anchors on what the image shows | everywhere |
| Console output | a `console` fence a runner fills | a re-run that compares, as a test | anchors on the code whose output it shows | everywhere |
| Callout | the standard callout syntax | reader-review | the page's anchors | GitHub, or the site |

### 1. A diagram written in a page or an artefact

The fence is the source, and the page or artefact holds it.

- **Written:** a `mermaid` fence in a page, or in an analysis artefact's part that takes free text. It carries no styling.
- **What it may state:** only facts with a home elsewhere, by the maintainer's rule, and the page anchors what grounds them. Which homes count is decision 2.
- **Checked:**
  - **A text alternative,** by a rule's checkable part: `accTitle` and `accDescr` in the fence. They travel with the diagram into every renderer.
  - **Syntax:** not by validation. A check whose answer depends on whether Mermaid's parser is installed breaks the same-answer obligation (COR-050 point 2). A project may run one in continuous integration.
- **Kept true:**
  - **The fence is content.** A change to what it draws flags the page through the page's anchors. A change to the fence flags whatever anchors that part of the page.
  - **A wide diagram,** such as one of containers, draws most of the repository. Anchoring all of it is the over-broad anchor COR-050 point 7 warns about. It anchors the records that decide its parts, or one entry file for each box.
- **Drawn:** by GitHub with no build step, and by a site in the project's theme.
- **Owner:** living-docs, for pages. software-analysis, for a diagram inside an artefact.
- **In an analysis artefact:**
  - **It shows only what its artefact states,** in its own parts or front matter. A use case's diagram of its main path restates its steps, for example. Anything wider goes in the overview (piece 3) or on a page.
  - **Why no wider:** the analysis's anchors are fixed by its lists. A journey's use-case anchors match its steps and relies-on exactly, and a use case's requirement anchors match its list (DEC-001 point 4, DEC-002 point 7). A use case that anchored a journey it takes part in would close a cycle (COR-050 point 5).
  - **No new part.** A shipped diagram part would make every artefact carry it as `None.`, and every live artefact would need a migration (software-analysis DEC-001 point 1). A project that wants one adds a part of its own.
  - **Where a fence fits today:** in a part's free text, after a blank line. Two places fail the forms check. A fence right under a journey's step joins the step's line. A fence beside `None.` makes the part more than `None.`, and its form then finds no items. The build either mends the forms or says so in the hints.

### 2. A diagram source in a file of its own, and its rendered image

A separate source serves a language GitHub does not draw, such as D2 or PlantUML.

- **Written:** a source file beside the page, such as `deploy.d2`. The page shows the image a renderer writes, `![Deployment](generated/deploy.svg)`.
- **Checked:**
  - **Syntax:** the renderer refuses a bad source when it renders.
  - **Freshness:** the image records a fingerprint of what it was drawn from. A check compares it with a fresh fingerprint, offline, with no renderer installed. A stale image fails validation.
  - **The limit:** a fingerprint proves which source the image came from. It does not prove that nobody edited the image. Only rendering again proves that, where the renderer is installed.
- **Kept true:**
  - **The page anchors the source file and the homes of what it shows.** An edit to either flags the page.
  - **The image is never anchored.** It flags nothing, since only a Markdown file is an artefact.
- **What the fingerprint covers:** the source, every file it includes, and the renderer's settings file. A source that includes from a remote address cannot be fingerprinted, so such a source is refused.
- **The costs:**
  - **The cascade stops at the page.** A source edit flags the page, which may answer `unchanged`, since its own text did not change. The cascade goes on only where a revalidation changes content (COR-050 point 6). So the page's dependants learn of a changed diagram only if its alt text changed with it.
  - **A contributor without the renderer** cannot mend a stale image. The finding names the render command, and continuous integration may render for them.
  - **Images outside living-docs' places,** such as in an architecture record, go unchecked by living-docs' validator. That is the second consumer that would move the check to the backbone (COR-007).
- **Drawn:** by the renderer the project chooses, run by a command, never by hand. The image is committed so that GitHub shows it, or a site renders it at build time.
- **Owner:** the project, for the renderer. living-docs, for the contract and the freshness check.

### 3. A diagram generated from the analysis

A command draws it from the analysis's front matter, so it cannot drift. This is where the maintainer's "generated from that home where it can be" applies first.

- **What it can draw:** only relations the front matter holds (software-analysis DEC-001 point 1), and only artefacts in force, as `met-by` does.
  - **A use-case diagram:** each actor and the use cases it takes part in, inside the system's boundary. It is drawn from each use case's `actor` and `other-actors`, and each journey's `actor`. It is UML's diagram of that name, without include or extend.
  - **A journey's flow:** its `steps` in order. Its `relies-on` is a set, and which step needs which outside use case lies only in the body. So those use cases show as one group of their own, or not at all.
  - **A requirement map:** the use cases and journeys that list each requirement, the requirements it `refines`, and its `actors`.
- **What it cannot draw today:** a use case's main path, its variants or a journey's seams. They lie in the body, which no tool reads. A refinement of DEC-001 point 1 could let the capability's own query read parts by their permanent id, as its check already does (decision 3).
- **The context diagram the issue names.** The issue asks for "a context diagram from actors and use cases". A diagram drawn from actors and use cases is a use-case diagram, and it shows the system's boundary with the actors around it.
  - **A requirements context diagram,** the system as one box among its actors, is what Wiegers and BABOK call a context diagram.
  - **It clashes with software-analysis DEC-001 point 11.** That point defines a context view by what it shows, "the system among the people and systems around it". It keeps such views out of the analysis, and a title does not change what one shows. So drawing one in the analysis refines point 11 (decision 4).
- **Written:** by nobody. A query prints Mermaid, as `pkit process graph --mermaid` does. It carries `accTitle` and `accDescr`, and no styling.
- **Where it shows:**
  - **On demand,** in a terminal or an agent's context.
  - **In a generated overview,** a held document in the analysis area (COR-050 point 1). Readers on GitHub then see the analysis's diagrams with no setup (decision 5).
  - **Later, in a region of a living-docs page,** through a data point ("Generation is not rendering", below).
- **The generated overview, in detail:**
  - **Its folder:** a folder of held documents of its own, since a held folder never equals or encloses a place (COR-050 point 1). That changes the analysis's layout, software-analysis DEC-001 point 2.
  - **How it starts:** install writes it, as install writes the project's rule set (software-analysis DEC-001, Implications). A migration writes it for a project that installed the capability before (COR-010).
  - **How it stays fresh:** the stamp rewrites it whenever it writes an artefact. After a hand edit of a drawn field, a command rewrites it. The validator fails a stale overview, and the finding names the command.
  - **Opting out:** a project that deletes it is reported, never failed. So an upgrade breaks nothing.
  - **What it costs:** every change to a drawn field owes a rewrite: `actor`, `other-actors`, `steps`, `relies-on`, `requirements`, `refines` and `actors`. Two branches that each change one conflict on the overview, as on a lock file, and the merge rewrites it.
  - **Not like `depends-on`.** The generated `depends-on` is refreshed in the capability's own source, and an adopter's validation only reads it (COR-053 point 4). The overview is refreshed in each adopter's analysis, so the burden is new.
  - **How it "anchors what it shows":** a held document may carry no friction block, and validation fails one that does (COR-050 point 12). The overview stays true by being generated from its home and checked fresh, not by anchors. This reads the maintainer's rule, so decision 5 asks the maintainer to confirm it.
- **Where it never shows:**
  - **Inside an analysis artefact.** Each relation already has one home, in the front matter that lists it (COR-006). A copy in another artefact's body would change its content on every edit elsewhere, and flag its dependants. The closer precedent is DEC-002 point 7: the requirement never stores what meets it.
  - **In a view of the solution,** such as an architecture page or a record. A view states none of an analysis artefact's facts (DEC-001 point 11), and a generated diagram states them.
- **Owner:** software-analysis.
- **Two Mermaid writers.** A capability's script reaches the backbone only by running it, never by importing it (ADR-057 point 1). So software-analysis writes its own node ids and escaping beside `process_graph.render_mermaid`. Two copies are the recurrence COR-007 names. The build either adds a backbone command that turns a graph into Mermaid, or records why it keeps two.

### 4. Images and screenshots

A hand-made image and a captured screenshot are written alike, and kept true differently.

- **Written:** an image file, shown with `![alt](path)`. A capture script writes a screenshot. Marks on a screenshot, such as arrows, come from the script. A screenshot marked by hand counts as hand-made, and falls short of "produced by a script".
- **Checked:** by reader-review against the text-alternative rule. An image that carries meaning has alt text. A decorative one has an empty alt text, which WCAG asks for. No check tells the two apart, so none fails an image. A recording or a GIF needs an alternative of its own, such as a transcript or its storyboard.
- **Kept true:**
  - **The page anchors what the image shows,** such as the code of the screen it pictures. A change to that code flags the page, and whoever answers looks at the image too.
  - **A hand-made image:** the page may also anchor the image file, so that replacing it asks whether the text still agrees. Such an image changes rarely, so the flag costs little.
  - **A captured image:** the page anchors the capture script, never the image. Each new capture rewrites the image's bytes, and would flag the page for nothing.
- **Where it lives:**
  - **Beside the page that shows it,** in the page's space. Produced images sit in a folder or under a name of their own, apart from hand-made ones.
  - **An image both spaces show** lives in the user space. A user page never reaches into the internal root (living-docs DEC-001 point 1). A technical page may show a user-space image, since the rule runs one way only. A site built per space must then serve it ("The two layers").
  - **An external image,** such as a badge, lives at its own address.
- **How it looks:** the capture script's window size, scale and theme, and a site's framing, are presentation.
- **Drawn:** as an image, everywhere.
- **Owner:** living-docs, for the rule. The project, for the capture tool: Playwright for web pages, VHS for terminal stills, or its own script.
- **The cost:** each new capture adds an image to the history. A capture that runs only when its inputs changed avoids it.
- **Recordings** follow the same contract. A page anchors demo-recording's storyboard, never the video it produced.

### 5. Console output

A script produces it, and the page shows exactly what a reader would type and see.

- **Written,** in one of two shapes:
  - **C1, test the page:** a `console` fence holds `$ command` lines, each followed by its output. The fence is both what the reader sees and the test. A runner runs each command and compares. With an overwrite flag, it writes the new output into the fence. Output that varies is written as readable placeholders, such as `<path>`, which the runner matches.
  - **C2, generate into the page:** a marked region names a capture, and a command fills the region. The capture's command lives in a file of its own.
- **Checked:** by running the commands again and comparing. That runs the product, so it cannot be validation. It is a test, run in continuous integration.
- **Kept true:**
  - **The fence is content,** not a produced file, so F1 below does not apply to it. The page anchors the code whose output it shows. A change to that code flags the page, and the runner shows whether the output moved.
  - **A new capture changes the page's content,** which flags whatever anchors that part of the page.
- **Drawn:** as a code block, everywhere.
- **Owner of the written form:** living-docs, as guidance in its `docs-author` skill.
- **Owner of the runner:** not living-docs, which never runs the product (living-docs DEC-001). Candidates:
  - **A project's own script,** run as a test. project-kit's own `pkit` docs would be the first case.
  - **A non-recording plugin on demo-recording's runner,** which runs anywhere. demo-recording DEC-003 names exactly such a plugin as the trigger to split its format from its recording. But its parser reads storyboards, an H1 and `## Step N` headings, and a page is not one.
  - **A capability for executed documentation checks,** once a second project wants one (COR-007).
- **Where results go:** a failing test. living-docs' reading-evidence point comes later. Its filler is a query that changes nothing and runs within a time bound (COR-052 point 6, ADR-057 point 3). So it cannot run the commands, only read results someone kept, and no record says where those live.

### 6. Callouts

A callout highlights a note, a tip or a warning, in the standard syntax the maintainer named.

- **Written:** a block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`. The issue's "info" is NOTE.
- **Checked:** by reader-review, against guidance on when to use each type, such as WARNING only where a step can lose data. No offline check yet. An unknown type shows as a plain block quote, which costs little.
- **Kept true:** content, grounded by the page's anchors like prose.
- **How it looks:** GitHub's own look by default. A site draws it in the project's theme.
- **Owner:** living-docs, as guidance in `docs-author`.
- **Why one syntax suits every adopter:** it degrades to a readable block quote wherever nothing draws it, which is what universal applicability asks (COR-014). The look, which differs by host, is presentation.
- **In the analysis:** not needed. Each part already carries a label and a hint.

## How a produced file relates to its source, for friction

Anchors name sources and homes, never what a tool produces from them. A produced file is a rendered image, a captured screenshot, a recording or a generated overview. Console output in a fence is content, not a produced file.

| Produced | From | Freshness checked by |
|---|---|---|
| A rendered image | a diagram source, what it includes, and the render settings | a fingerprint compared offline, in validation |
| A generated overview | the analysis's front matter | a fresh copy compared offline, in validation |
| A screenshot or a recording | a run of the product | a new capture, as a test |

Three ways to treat a produced file:

- **F1. Never anchor the output, and check its freshness.** The output is a generated file, like a lock file (COR-053 point 4). A stale output fails, and a re-render flags nothing.
  - **No exclusion is needed for friction.** An image is never an artefact, so it flags nothing unless something anchors it.
  - **An exclusion is needed for the measures,** where the project's declared surface covers an output. Nothing anchors an output, so it would count as uncovered surface (COR-050 point 8). Excluded paths are the project's to set (COR-050 point 14).
  - **An exclusion also makes a slip loud.** An anchor that matches only excluded paths is a dead anchor, an error (COR-050 point 7).
- **F2. Anchor the output.** Every re-render or new capture flags the page, though nothing the page says changed. People learn to answer blindly, which the warning on over-broad anchors exists to prevent (COR-050 point 7).
- **F3. Commit no output.** A site renders at build time. GitHub then shows Mermaid, and the raw source of every other language.

**The freshness check,** under F1:

- **Its kind:** the mechanism's own invariant, as the generated `depends-on` is. It is not a rule's checkable part. Said plainly, the rule-set reviewer does not read it as a check kept beside a rule, which COR-051 rejects.
- **Its home:** the validator of the component that keeps the pair. living-docs' for images its pages show, software-analysis's for its overview. It fails, since the project can correct it in its own files (COR-055 point 1).
- **How a fingerprint is computed:** over files with their line endings normalised, or as git's own hash of each file. A checkout that converts line endings then passes.
- **Where it is kept:** inside an SVG, in a PNG's text chunk, or in a file beside the image.
- **When to render:** only when stale, so that a render adds no history when nothing changed.

## Generation is not rendering

Rendering turns a diagram's source into an image. Generation turns the analysis into a diagram's source. They need different homes.

**Rendering is a project command, with settings a project or a capability supplies.**

- **The command runs outside the checks.** A renderer writes an image, may reach a hosted service, and may write different bytes each run. A query, a filler or a validator may do none of these (COR-050 point 2, COR-052 point 6).
- **Not an event.** Edits by hand emit no events (COR-053 point 9), and most diagrams are edited by hand.
- **Not a role the project provides.** A project cannot provide a role yet (COR-053 point 1). A capability the project incubates in its own repository can (COR-031), at the cost of keeping a capability.
- **The settings can be a data point today.** living-docs could accept a point of renderers: for each source language, its file extensions, its command and its settings file. A project file fills it, or a renderer capability contributes to it (COR-052 point 2). The filler supplies settings and renders nothing, so it keeps the query contract.
  - **The command:** a living-docs render command runs what the point resolves to, and stamps the fingerprint. The fingerprint covers the resolved entry.
  - **Inert policy `fail`.** The freshness check reads the resolved entry, so it enforces, and an enforcing use fails closed (COR-052 point 6). A renderer capability out of step with the point's version then fails the freshness check of every rendered image until it catches up.
  - **What it gives:** the issue's "a capability or the project provides", with no change to a core record.
  - **The alternative:** a key in living-docs' own configuration, which only the project writes. It refines living-docs DEC-001 point 1, whose configuration now holds only the spaces' settings.
- **When:** with the first page that needs a language GitHub does not draw. Until then, "configurable" is met by the presentation layer: a site draws Mermaid in the project's theme.

**Generation onto a living-docs page, later, is a data point too.**

- **The point:** living-docs accepts diagrams, each an id, a title, a description and its Mermaid text.
- **The fillers:** software-analysis fills it from its front matter, as it fills the readers point today (software-analysis DEC-001 point 8).
- **The page:** a marked region names an entry by id. A living-docs command fills the region, and validation compares it with the resolved point.
- **What it gives:** neither capability names the other, and a page names a diagram, not a command.
- **Why later:** the overview held by software-analysis shows the analysis's diagrams first, and needs no point. A page that must show one too is the trigger (COR-007).
- **What it needs when built:**
  - **A refinement of the rule on grounding (RS-LDOC-001).** A region states facts the page does not anchor. Their home is an analysis artefact, which is an admitted home only if decision 2 takes option B.
  - **The maintainer's confirmation** that a region kept fresh "anchors what it shows" through its generation, as for the overview (decision 5).
  - **Inert policy `fail`,** since a stale region fails validation, and an enforcing use fails closed (COR-052 point 6). An analysis edit that changes a drawn relation then fails the page's validation until someone refills the region.
  - **One entry per view.** A filler takes no parameter (COR-052 point 6), so each filtered view, such as one requirement's map, is an entry of its own.
  - **Output that is the same byte for byte,** with sorted nodes, stable ids and one line ending.
  - **Markers of their own,** since several regions in a page's middle cannot use ADR-037's strip-and-write-one-at-the-end. A damaged marker is a validation finding, never a silent repair. An architecture record decides the marker grammar.
  - **A judgement rule** that no view of the solution shows a generated region.

## Where the issue meets accepted records

Each point below needs a choice before the build, or a refinement the build carries.

1. **"A context diagram from actors and use cases."** A diagram drawn from actors and use cases is a use-case diagram. A requirements context diagram matches software-analysis DEC-001 point 11's context view by what it shows, so drawing one refines that point. Decision 4 settles it.
2. **"Written diagrams, such as an architecture view," in software-analysis.** DEC-001 point 11 keeps views of the solution outside the analysis. An architecture view is a page of the technical space, or a document the architect keeps. It names analysis artefacts by id only.
3. **"Generated from that home where it can be."** A use case's steps and a journey's seams lie in the body, which no tool reads (DEC-001 point 1). Decision 3 settles whether the capability's own query may read them.
4. **"It states nothing that has no other home."** living-docs DEC-001 admits only a decision record or a page as a fact's home. Any other artefact or code as a home is "Not taken yet". Decision 2 settles the refinement.
5. **"It anchors what it shows."** A generated overview is a held document, which may carry no anchors (COR-050 point 12). Decision 5 asks the maintainer to confirm that generation and a freshness check meet the rule instead.
6. **A domain model.** By the analysis's membership test, a change to the software can make a domain model false, so it belongs in the analysis. No kind holds one, and a new kind needs a decision of its own (DEC-001 point 11). It waits for a project that asks for one.
7. **Console output and screenshots produced by a script.** Producing them runs the product, which living-docs rejected for itself (living-docs DEC-001). So the runner lives outside living-docs.
8. **Rendering as a role.** A project cannot provide a role yet (COR-053 point 1). A data point filled by a project file or a capability gives the same freedom today.
9. **New and tightened rules.** Each raises a new major of `LDOC` or `SAN`, and a rule has one status (COR-051 points 4 and 7). Each needs an accepted record as its origin (COR-051 point 5). A new checkable part refines living-docs DEC-001 point 6, which lists what its validation settles.
10. **The analysis's layout.** The overview's folder of held documents changes software-analysis DEC-001 point 2.

## Where the recommendations fall short of the direction

The recommendations below stage the work. This list says where a stage falls short, and the option that would meet it in full.

- **"Rendering is configurable."** The first build configures how Mermaid looks on a site, not a renderer for other languages. To meet it now: build the renderers point, its command and the freshness check in the first build (decision 6, built now).
- **"Generated images are allowed."** The contract allows them from the first build. The freshness check that guards them comes with the first page that needs one. To meet it now: the same as above.
- **"Produced by a script, never pasted," for console output.** The first build runs project-kit's own `console` fences, and gives adopters guidance only. An adopter's fences may still be pasted. To meet it now: ship a runner as a capability (decision 7, option C).
- **"Produced by a script, never pasted," for screenshots.** A screenshot marked by hand counts as hand-made. To meet it in full: refuse marks by hand, and ask the capture script for every mark.
- **"Generated from that home where it can be."** The query reads front matter only, so it draws no use case's steps and no journey's seams. To meet it now: decision 3, option B.
- **"It anchors what it shows," for generated diagrams.** A generated overview carries no anchors. It stays true by generation and a freshness check. To meet the rule word for word: show generated diagrams on demand only (decision 5, option A).

## The architect's recommendation

The architect reviewed the first draft of this note on 18 October, before the maintainer's two comments were read into it. This section gives that recommendation in short. Most corrections are folded into the sections above.

- **Who owns what:**
  - **living-docs:** one new `LDOC` rule on text alternatives, with its checkable part. The contract for rendered pairs and their freshness check. Guidance in `docs-author` for diagrams, images, `console` fences and callouts.
  - **software-analysis:** an on-demand query that prints Mermaid. No new part in any kind.
  - **The project:** the renderer, the capture tools, the console runner and any Mermaid syntax check.
  - **The backbone:** nothing new, and no new key in its configuration (COR-048).
  - **demo-recording:** nothing new. Its recordings follow F1.
- **Rendering is a project command,** not a role. "Configurable" means inline Mermaid by default, and a project's render command for each other language.
- **F1, with two corrections.** No exclusion is needed for friction, and none is living-docs' to make. A separate source stops the cascade at the page, which makes inline Mermaid the right default. F2 is rejected, and F3 is a project's choice for a space.
- **The freshness check** is the validator's own invariant, failing, and moves to the backbone only at a second consumer.
- **What software-analysis generates:** a use-case diagram, a journey's flow and a requirement map, on demand. "Context diagram" must be renamed. A stored copy may come later, only on a page that is not a view, through a data point, once the grounding rule is refined.
- **Callouts:** the dialect in each space's definition, not in `LDOC`, since one host's dialect does not suit every adopter (COR-014).
- **Wait (COR-007):**
  - the render command and its settings
  - the data point and page regions
  - a console-runner capability and a callout check
  - a domain-model kind
  - any backbone engine for regions or freshness
- **Where it is recorded:** a new living-docs record on visual elements, rather than more points in living-docs DEC-001, which is already long. An architecture record follows when regions are built.
- **Escalation:** yes, at the weight of refinements. The design refines living-docs DEC-001 points 1, 3 and 7, `LDOC`, and software-analysis DEC-001 points 8 and 11. The issue's "a role the project provides" would need a core change, and the architect recommends dropping it.

**Where this note now departs from it,** after the maintainer's comments and the critic's review:

- **Callouts:** the maintainer named "the standard callout syntax" as content. So one syntax ships, and its look is presentation, rather than a dialect in each space.
- **Generated diagrams by default:** a held overview in the analysis area shows them to readers with no setup. It needs no data point and no refinement of the grounding rule. It does need the maintainer to confirm that it "anchors what it shows" by generation, and it costs adopters a rewrite on each drawn change. The architect weighed only a file of no kind there.
- **A fact's home:** opening anchored artefacts and code as homes, for every statement, answers the maintainer's "truth held elsewhere". The architect proposed no change to the homes, before that comment was read.
- **Renderer settings:** a data point keeps "a capability or the project provides" without a core change. The architect weighed only a key in living-docs' configuration.
- **Text alternatives:** the checkable part covers only Mermaid fences. Images are left to reader-review, since an empty alt text is right for a decorative image.

## The critic's review

The critic reviewed the note twice on 18 October. Each pass's findings follow, with what the note did with each.

### First pass, on the second draft

- **Red flag 1, the maintainer's two comments of 18 October were missing.** Confirmed, word for word. "What the maintainer has decided" now holds them, and "The two layers" covers presentation. Decisions 2, 5 and 8 to 10 answer them.
- **Red flag 2, the direction narrowed without saying so.** "Where the recommendations fall short of the direction" now names each gap, with the option that closes it. The generated overview meets "supports diagrams by default", and project-kit's own runner gives "never pasted" a first real case. The context diagram is now its own option (decision 4).
- **Red flag 3, the text-alternative rule hid its cost.** Confirmed: a new accepted rule needs a new major, and every pin falls behind until reviewed (COR-051 point 7). Decision 12 now times the changes. Two corrections:
  - Two copies are needed because neither capability's set may inherit the other's without a required dependency. A set binds wherever an inheriting set reaches.
  - The `SAN` copy takes a software-analysis record as its origin (decision 13).
- **Red flag 4, the checkable part failed ordinary pages.** Confirmed.
  - **Images:** the checkable part drops them, since an empty alt text is right for a decorative image. A badge at an external address is no longer failed.
  - **Mermaid:** the alternative of a sentence before the fence is dropped, so the check and the rule agree.
  - **Paths:** the check that a path resolves is dropped, since it belongs to no rule on text alternatives. A rule of its own can come later.
- **Gaps.** Each is now answered where it belongs:
  - **One home:** decision 2.
  - **How a theme reaches Mermaid:** "The two layers" and decision 9.
  - **Wide diagrams:** piece 1.
  - **Includes, missing renderers and images outside living-docs' places:** piece 2.
  - **The measures:** F1.
  - **Shared images, marks on screenshots and recordings:** piece 4.
  - **The forms check:** piece 1, as found, with the build to mend it or say so.
  - **The SAN check and a filler with no parameter:** the build list and "Generation is not rendering".
- **Contradictions.** Console output is content, not a produced file. One threshold now applies: a second copy is the trigger to weigh extracting.
- **Weak reasoning.**
  - **demo-recording** is corrected: only its recording needs macOS, and DEC-003 anticipates a non-recording plugin.
  - **Storing a generated diagram in an artefact** is now ruled out by one home per relation and DEC-002 point 7, not by DEC-001 point 11.
  - **Rendering as a data point** is now an option.
  - **The cascade argument** for inline Mermaid now states its limit: alt text that changes with a separate source carries the cascade on.
  - **Keeping a syntax check out of validation** now rests on the same-answer obligation.
  - **Practice:** Rust's documentation tests no longer count as output comparers, and cog's region now holds its generator. The claims about site generators and GitHub's theme are softened.
- **Straw-man options** are replaced by options someone would choose.

### Second pass, on the third draft

The critic found the four red flags resolved in substance, and five new ones.

- **New red flag 1, generated diagrams drop "it anchors what it shows".** Confirmed: a held document may carry no friction block (COR-050 point 12). The overview now says it stays true by generation and a freshness check. Decision 5 asks the maintainer to confirm that reading, and its option A keeps the rule word for word. The contradiction over "Not taken yet" is mended in "Generation is not rendering".
- **New red flag 2, the old decision on homes could not be met.** Confirmed in both halves.
  - **In the analysis,** a diagram showing more than its artefact states needs anchors that the analysis's matched lists refuse, or that close a cycle. Piece 1 now limits such a diagram to what its artefact states.
  - **In `LDOC`,** homes for diagrams only made one fact's home depend on its form. Decision 2 now offers the homes for every statement, beside the critic's option, "a diagram is never the only statement of a fact".
  - **The listed homes** were the maintainer's illustration, not a closed list. Decision 2's option B now admits any record, artefact, captured source or code the page anchors.
- **New red flag 3, the overview's cost was unstated.** Confirmed. Piece 3 now says how it starts, through install and a migration. A project that deletes it is reported, never failed. It states what each drawn change owes, and that branches conflict on it as on a lock file. The precedent of `depends-on` is corrected, and the folder of its own refines DEC-001 point 2.
- **New red flag 4, the rule mechanics were wrong.** Confirmed in three places.
  - An accepted rule cannot be tightened as proposed. Decision 12 now stages a tightening as a proposed successor under a new id.
  - Decision 13 no longer rejects one record for a false reason.
  - Its list of refinements now adds software-analysis DEC-001 points 2 and 11.
- **New red flag 5, shared images break a site per space.** Confirmed. "The two layers" now asks a site's build to gather its space's pages and the assets they show, wherever they lie. Decision 8 rules out a generator that cannot.
- **Order.** The generator's reading now comes before what it draws. Decision 2 no longer argues its cost from the later timing decision. Decision 8 is the capability's, and project-kit's own choice of a generator moves to a project record.
- **Smaller points.** The renderers point now states its inert policy `fail`. The roles bullet now names the incubated capability. Decision 12 says that `SAN`'s major waits on its five proposed rules.

### Where the note does not follow the critic

- **A backbone method set for text alternatives** (its CA5) is an option of decision 11, but not recommended. It needs a core record and the backbone's first method set for one rule (COR-007).
- **Reading the body's parts** (its CA3) is an option of decision 3, but not recommended for the first build. It refines an accepted point, and the first build draws what is asked without it.

## Decisions for the maintainer

Thirteen decisions, ordered so that each builds on the ones before it. Each gives two or three options and a recommendation. The maintainer's three statements of 18 October are settled, and nothing below reopens them.

### 1. The default form of a diagram

- **A. Mermaid in a fenced block, inside the page or the artefact, with no styling.** GitHub draws it with no setup. Another language is used only where a project renders it.
- **B. No default language.** Each space's definition names the languages its pages use.
- **C. Mermaid, also rendered to a committed SVG for every diagram,** so every diagram looks the same everywhere.

**Recommended: A.** It meets "a sensible default needs no setup, and reads right on GitHub". Agents write it, reviewers read its diff, and it reads as text where nothing draws it. Its fence is content, so friction's cascade reaches what rests on the page. B leaves a project with nothing that works on day one. C commits an image per diagram, and puts every diagram behind a renderer.

### 2. Where the facts a diagram shows have their home

The maintainer settled that a diagram states nothing that has no other home. What remains is which homes count.

- **A. Today's homes, and a diagram is never the only statement of a fact.** Each fact a diagram shows is also stated in a decision record the page anchors, or in prose on a page, its home. Nothing else changes.
- **B. Any record, artefact, captured source or code a page anchors may be a fact's home, for every statement, prose or diagram.** A diagram is never a fact's home. This takes up living-docs DEC-001's "Not taken yet" home, for every statement alike.
- **C. Those homes for diagrams only.**

**Recommended: B.** It is the maintainer's "truth held elsewhere, in decisions, requirements, use cases or code". It reaches stated facts as a decision record already does: a change to the home flags every page that anchors it. A costs a sentence of prose for each arrow a diagram draws. C gives one fact two homes on one page, when the page states it in prose and draws it too. B tightens RS-LDOC-002, and `SAN` gains the same judgement rule for diagrams in the analysis.

### 3. What the generator may read

- **A. Front matter only,** as software-analysis DEC-001 point 1 says. It draws relations, not a use case's steps or a journey's seams.
- **B. Front matter, and body parts read by their permanent id,** by the capability's own queries only. It also draws a use case's flow and a journey's seams.
- **C. Steps and seams moved into front matter,** so a tool reads them without reading a body.

**Recommended: A for the first build, B as its next refinement.** A needs no change to an accepted point. B meets "generated from that home where it can be" for flows. It refines point 1, and the check already parses those parts by id. C moves the readers' text into data, which DEC-001 point 1 keeps apart.

### 4. What software-analysis draws, and what each diagram is called

Under decision 3's option A. Option B adds a use case's flow and a journey's seams to either.

- **A. A use-case diagram, a journey's flow and a requirement map.** The use-case diagram shows the system's boundary with the actors around it, which answers "a context diagram from actors and use cases".
- **B. A, and a requirements context diagram:** the system as one box among its actors. It refines software-analysis DEC-001 point 11, which defines a context view by what it shows.

**Recommended: A.** It draws what the issue asked for, from actors and use cases, under a name that does not clash with point 11. B is the right choice if a project wants the system's scope without its use cases. Its cost is refining a point accepted on 17 October.

### 5. Where generated diagrams show by default

- **A. On demand only,** printed by a query. Nothing is stored, and the maintainer's "anchors what it shows" holds word for word.
- **B. A, and a generated overview** that software-analysis keeps as a held document in the analysis area. Install writes it, the stamp rewrites it, and validation fails a stale one.
- **C. B, and regions on living-docs pages,** filled through a data point, built now.

**Recommended: B.** It meets "supports diagrams by default" for a reader on GitHub. Taking it confirms that a generated diagram "anchors what it shows" through its generation and a freshness check, since a held document carries no anchors. Its cost is a rewrite on each change to a drawn field, and a conflict when two branches each make one. A meets the anchoring rule word for word, but shows nothing on GitHub. C needs refinements of the grounding rule and a data point no page needs yet (COR-007).

### 6. Rendered images: where renderer settings come from

All three keep F1: never anchor an output, and check its freshness offline.

- **A. A living-docs data point of renderers,** filled by a project file or a renderer capability. A living-docs command runs the resolved renderer and stamps the fingerprint. Its inert policy is `fail`.
- **B. Renderer settings in living-docs' own configuration,** written by the project only.
- **C. No renderer in the methodology.** A project renders in its own build, and the methodology checks only the fingerprint.

**Recommended: A, built with the first page that needs a language GitHub does not draw.** It gives the issue's "a capability or the project provides" with no core change. B shuts out a renderer capability. C leaves the fingerprint's format and settings to each project, so no shared check can read them. Build it now instead, if "rendering is configurable" must hold from the first build.

### 7. Console output and screenshots

- **A. A `console` fence** holding commands and their output. project-kit's own script runs its `pkit` docs' fences as a test, and can overwrite them. Screenshots come from each project's capture script, which the page anchors. living-docs gives adopters guidance.
- **B. A, with the runner as a non-recording plugin of demo-recording.** That is the second backend demo-recording DEC-003 names as the trigger to split its format from its recording.
- **C. A capability for executed documentation checks,** shipped now, reporting through reading evidence once a record says where results are kept.

**Recommended: A.** The page shows what the reader types and sees, and the same fence is the test. project-kit's own docs are the first real case (COR-007). B splits demo-recording for a runner whose input, a page, is not a storyboard. C waits for a second project that wants it.

### 8. Documentation sites: what living-docs ships

All three keep GitHub as the default with no site.

- **A. The criteria a site must meet, and two worked examples.** Zensical for a Python toolchain, and VitePress for a Node toolchain.
- **B. The criteria only.**
- **C. A ready configuration for one generator,** which a project copies.

**The criteria:**
- the site reads content as written: its front matter, Mermaid fences and the standard callout syntax
- a theme reaches diagrams and callouts from one place, light and dark
- one site per space, which gathers its space's pages and the assets they show, wherever they lie

**Recommended: A.** The maintainer asked for concrete choices. Zensical is Material for MkDocs' successor, from the same team. It draws Mermaid in the site's own colours from its settings. VitePress reads the standard callout syntax natively. Neither is confirmed against every criterion, so the build checks them first. C binds every adopter to one toolchain (COR-014). project-kit's own choice, likely Zensical, is a project record when project-kit wants a site.

### 9. How a theme reaches diagrams, callouts and screenshots

- **A. Through the presentation layer only.** On GitHub, GitHub's own look. On a site, the site's settings. In a committed image, the renderer's settings file, which the fingerprint covers. In a screenshot, the capture script's settings.
- **B. A, and one theme file the project owns,** read by the site and by the renderer, so a site and a committed image look alike.
- **C. Styling directives in each fence,** such as `%%{init}%%`, so GitHub shows the project's theme too.

**Recommended: A, with B once a project both renders images and runs a site.** C puts styling in content, which the maintainer ruled out, and makes a theme change flag every page that shows a diagram.

### 10. The callout syntax

- **A. The standard syntax,** `[!NOTE]` and its four siblings, as the one form in content. Its look is presentation.
- **B. Each space's definition names its dialect,** such as a site generator's admonitions.
- **C. The standard syntax, and a check that each type is one of the five** at the top level.

**Recommended: A.** It is the "standard callout syntax" the maintainer named, and it degrades to a block quote anywhere (COR-014). B was the architect's recommendation before the maintainer's comment, and puts a host's syntax into content. C adds a check that guards a cosmetic failure (COR-007).

### 11. The text-alternative rule

- **A. One rule in `LDOC` and one in `SAN`:** a diagram, an image or a recording that carries meaning has a text alternative, and a decorative image an empty one. Its checkable part: a Mermaid fence carries `accTitle` and `accDescr`. Images are left to reader-review.
- **B. One rule in a new backbone method set,** which `LDOC` and `SAN` both inherit, with a core record as its origin.
- **C. Guidance only,** in `docs-author` and `analysis-author`.

**Recommended: A.** Each capability's validator reads only its own artefacts, and neither set may inherit the other's without a required dependency (COR-051 point 7). B needs a core record and the backbone's first method set for one rule (COR-007). C leaves a gap that grows with every diagram. The new checkable part refines living-docs DEC-001 point 6.

### 12. When the rule changes bind

Decisions 2 and 11 add rules and tighten RS-LDOC-002. Each needs a new major of its set, and every project's pin then falls behind until reviewed (COR-051 point 7). A rule has one status (COR-051 point 4).

- **A. Stage, then accept in one major for each set.** New rules land as proposed. The tightening lands as a proposed successor of RS-LDOC-002 under a new id. Each set's next major accepts them, and supersedes RS-LDOC-002. `SAN`'s major also accepts its five proposed rules, so it waits until they are ready.
- **B. Accept now,** in a major of each set with the build.
- **C. Write nothing into the sets** until a major is due for another reason. Guidance carries the rules meanwhile.

**Recommended: A.** One major for each set is one review for each adopter. Proposed rules bind nothing, but the reviewer can preview them. B costs `SAN`'s adopters two majors where one would do. C leaves the rules unwritten, so nothing previews them.

### 13. Where the decisions are recorded

- **A. One new record in each capability.**
  - **A living-docs record on visual elements** refines living-docs DEC-001 points 1, 3, 6 and 7.
  - **A software-analysis record on diagrams** refines software-analysis DEC-001 points 1, 2, 8 and 11 as the decisions reach them.
  - Each is the origin of its own capability's new rules.
- **B. One living-docs record,** with software-analysis DEC-001 refined in place and the origin of its new rules.
- **C. A core record on visual elements,** both capabilities' records citing it.

**Recommended: A.** One topic, one record, as software-analysis DEC-002 did for requirements. Both DEC-001 records are already long. B works as well, and is the choice if fewer records matter more. C puts capabilities' choices in the core, though nothing here is a mechanism every component needs.

## What gets built, once decided

With the recommendations taken, the first build is these tasks:

- **living-docs:** the record of decision 13. In `LDOC`, the proposed successor of RS-LDOC-002 and the proposed text-alternative rule, with the validator's checkable part for Mermaid fences (decisions 2, 11 and 12).
- **living-docs:** `docs-author` guidance for inline Mermaid, images, `console` fences and the standard callout syntax (decisions 1, 7 and 10). It also gives the criteria for a site, with its two worked examples (decision 8).
- **software-analysis:** the record of decision 13, and the query that prints the three diagrams (decisions 3 and 4).
- **software-analysis:** the generated overview, in a folder of held documents. Install, a migration and the stamp write it. Its command rewrites it, and the validator checks it fresh (decision 5).
- **software-analysis:** in `SAN`, the proposed rule on a diagram's facts and the proposed text-alternative rule, with the validator's checkable part. The forms check is mended, or its hints say, where a fence cannot sit.
- **project-kit:** a script that runs its own docs' `console` fences as a test (decision 7).

The renderers point, its command and the freshness check of rendered images come later. They come with the first page that needs a language GitHub does not draw (decision 6). The majors of decision 12 come when each set is ready for one.
