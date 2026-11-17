---
id: DEC-018
title: One file follows the reader's mode, and a copy holds its version's bytes
status: accepted
date: 2026-11-06
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a page shows a figure as any image, so the figure's own file has to follow the reader's light or dark mode. A format of its own has the SVG renderer draw one file that holds the modes and repaints itself by a rule the browser reads. The SVG format, the previews and the viewing step keep one file for each combination. The numbered version holds that same file, so a current copy is its bytes under a name with no number, and one hash serves both. The renderer's declaration pairs a shared mode with what a browser tells an image, so no library changes.

What the capability promises is a floor: a whole figure, in one of the piece's modes, unless a person lets a fault through an export. Which mode is the browser's to say, and the capability neither sets it nor sees it. A test on GitHub's page found Chrome and Firefox following the reader, and WebKit, Safari's engine, following only in part (Context). On an iPhone, browsers generally run on WebKit, so that engine stands for many readers. A figure that misses the mode stays readable where it paints its own ground.

Accepting this record accepts two judgements. One is how far browsers carry the reader's mode, the *reach* (point 5). The other is one reading of the documentation's rule on styling (point 6). The issue asked for a form that fits that rule and follows the reader, and each is a judgement on one half of that.

## Context

A published figure reaches a page as its piece's current copy. [project-kit#2700](https://github.com/aleskalfas/project-kit/issues/2700) asks how the figure follows "the reader's switch to another mode", the words the issue quotes from project-kit's use case of putting a figure in a page (UC-094 step 5). It asks for a form that fits the documentation's rules as they stand. Where no such form follows the reader's switch, the issue stops the record. The question then goes to a person as living-docs' own, since it reopens those rules.

The accepted records set these limits:
- **How a page shows an image.** It writes `![alt](path)`, and its content holds no styling, HTML attributes that theme an image included. A theme reaches an image a renderer writes through the renderer's settings ([living-docs:DEC-002-visual-elements] points 1 and 5).
- **What an export makes.** A format whose medium switches modes while open holds in one file the modes a reader's signal names. What becomes of any other mode is that format's own ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). The SVG renderer draws a file for each combination. That drawing serves the previews, the exports and the viewing step ([visual-communication:DEC-015-viewing-step-and-reviewer]).
- **Which signal names a mode.** A renderer's declaration names each of its formats that holds modes, with the signal pairs it reads. The pairs are settled once, for the colour scheme and the contrast. Each format reads those its medium reaches, and a new pair is a new version of its renderer, after a test ([visual-communication:DEC-023-html-page-modes] point 5). So a signal names a mode to a format only through a pair that format reads (DEC-023 point 1).
- **The current copy.** It is an unnumbered copy of each file an export makes (DEC-006 point 7). A page links it by name.
- **The axes.** The engine knows them as data ([visual-communication:DEC-004-brands-and-notations] point 2). The foundations declare the colour scheme. A change to them puts off their release, and that of every library built on them ([visual-communication:DEC-013-shipped-library-releases] point 1).
- **Freshness.** How an image is checked for freshness waits for the first page that needs it ([living-docs:DEC-002-visual-elements] point 2).

Two terms come from the record of the HTML page's modes (DEC-023, Context). A *reader's signal* is a CSS media feature that names a mode a reader wants, such as `prefers-color-scheme`. A *signal pair* joins a mode to the value of a signal that names it. This record adds the case of an image: for a file a web page shows as an image, the signal is what the browser tells that file, which the element that embeds it may set (point 5).

Two more serve the rest:
- A *switching file* is one file that holds several combinations of modes, and draws the one the reader's signal names.
- A *one-key file* is the file the SVG renderer draws of one combination, which a key names.

### What the test showed

On 6 November, three forms of the `sockets` figure stood on one temporary page on GitHub, since removed:
- a switching file, by `![alt](path)`
- a file for each mode, each with GitHub's fragment on its path, such as `#gh-dark-mode-only`, which its pages hide in the other mode
- a file for each mode, in a `<picture>`

The switching file was folded by hand from the figure's two previews, as the default drawing with one rule on it. The figure has one arrowhead colour, no translucent colour and no picture.

What GitHub does with them:
- **Its renderer keeps all three.** It keeps the fragment, and wraps `<picture>` in an element of its own. It removes an inline `<svg>`, and a `style` on an `<img>`.
- **It serves the file unchanged,** as `image/svg+xml`. The file's rule and its embedded fonts work inside an `<img>`.
- **Its documentation says little.** [Its writing guide](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#images) says only that `<picture>` is supported. Its changelog announced the fragment in 2021, and `<picture>` in 2022. Neither says what a theme does inside an image.

What each engine drew of the switching file:
- **Chrome 157, on GitHub's page.** It followed the system. It followed each GitHub setting written on the page over the system: light, dark, dark dimmed and a high-contrast theme of each. A change of setting in an open page repainted it with no reload.
- **Firefox 148.** On GitHub's page it followed the system, and repainted at a change of setting in an open page. It followed a light and a dark setting at load, on a saved copy of the page under GitHub's stylesheets.
- **WebKit on macOS 26.6, through a web view.** Under a light system it drew light, whatever GitHub's setting. Under a dark system it drew dark on 6 loads of 20 on GitHub's page, and on 21 of 48 on a local page. Each load kept what it first drew. No GitHub setting moved it.

What the other two forms did:
- **The fragment form** followed the system and a setting in all three engines, as it hides one image by the page's own rules. In WebKit that held on 4 loads of 4 under a dark system, and on one run of each setting. So it is the one form seen following both there. In an open page it swapped at a change of setting, in Chrome and Firefox.
- **`<picture>`** followed the system in all three, on 4 loads of 4 in WebKit. In Chrome a setting moved it at load, through GitHub's script. In Chrome and Firefox it kept its source at a change of setting in an open page.

Why GitHub's switch reaches the file:
- **GitHub's stylesheet writes CSS's `color-scheme`** on the page's root for each setting.
- **The draft of CSS's Media Queries 5** has an embedded SVG take `prefers-color-scheme` from the used colour scheme of the element that embeds it.
- **Chrome and Firefox do that.** On a local page, a root's single `color-scheme` beat the system, both ways. So did one on the `<img>` itself, in Chrome. A root that named both, `light dark`, left the file on the system.
- **WebKit did not,** so its miss of a setting is a gap against that draft.

What else it showed:
- **The same drawing.** At its natural size, in each mode, Chrome drew the switching file pixel for pixel as the file of that one combination. At the page's width the two differed by up to 14 of 255 in one band, which reads as where pixels fall, not as colour.
- **Its size.** For this vector figure it is 2% larger than one such file, so about half of the two.
- **A tool that reads no such rule.** resvg drew the default combination.
- **A picture's variants.** Two variants in one file switched in Chrome and Firefox, on a local page.
- **A second means.** CSS's `light-dark()` in the file drew as the rule did in Chrome, and varied as it did in WebKit.
- **Contrast.** Under Chrome's emulation its page saw `prefers-contrast`, and an image in that page did not.

How it was set up:
- **A system preference** was the browser's own setting or emulation, and in WebKit the view's appearance.
- **A GitHub setting** was written in the attributes GitHub's stylesheets read. Chrome took them as the page arrived, Firefox in a saved copy or in the open page, and WebKit at the page's end.

What a person saw on 9 November, signed in, on [the temporary page](https://github.com/aleskalfas/project-kit/blob/0db981c3f7644ec0c7bae528da45ae41f6277828/t2700-host-test/page.md) at commit `0db981c3`:
- **GitHub's own setting.** With GitHub's theme set to light and the system dark, the switching file drew light, matching GitHub's theme.
- **A real change of the system's mode.** With GitHub following the system, the switching file switched when the computer's mode was switched.
- **The browser.** The person named none.

What neither the test nor the person's look reached:
- **GitHub's other settings as a reader makes them.** The look saw a light setting over a dark system. It did not see a dark one over a light system, dark dimmed, a high-contrast theme, or a change of setting on an open page.
- **Safari itself,** on a Mac or on a phone. Every WebKit run was a web view in a small program, which may be what made its result vary. The person did not look in Safari either.
- **GitHub's other surfaces:** its mobile app, a repository's front page and a wiki. Nor Windows or Linux.
- **Any other host, and any documentation site.**

## Decision

**A page shows a published figure as any image, from one switching file that the SVG renderer draws in a format of its own. The numbered version holds the same file, and a current copy holds its bytes under a name with no number. The renderer's declaration pairs a mode with the reader's signal, and the file follows what the browser tells it. What renders an image answers for its freshness.**

### 1. One switching file, in a format of its own

A piece that a page shows in the reader's mode names a format of its own, in place of the SVG format.
- **Its renderer.** The SVG renderer draws it from the scene, since the drawing is SVG either way ([visual-communication:DEC-005-engine-and-plugins] point 9).
- **Its medium.** Its file is read in a web page, which switches modes while open. So this is the format DEC-006 point 7 gives one file. A file of the SVG format is read as one chosen mode.
- **What it draws.** One SVG file for each page, language and set of combinations that share a file (point 2). Its plain drawing is the first of those combinations, in the order a variant's key takes (DEC-004 point 3).
- **Its rules.** For each other combination it holds, a rule of the file repaints that drawing where the reader's signal names it.
- **What a rule changes.** Only what a value axis changes: a colour, and which variant of a produced picture shows (DEC-006 point 3). So layout, text and fonts are drawn once.
- **A tool that reads no such rule** draws the plain drawing, a whole figure in one mode.
- **The same drawing.** Read in a mode, the file paints each element as the one-key file paints it in that combination. An export compares the two element by element, with no browser.
- **A difference stops the export.** It names the element and writes nothing. The person who runs it may name that element to let it through, as for a number that overflows ([visual-communication:DEC-016-what-an-export-reads] point 6). A copy so made asks for attention, and names the capability as the fault's owner.
- **What stays.** The SVG format keeps a file for each combination. The previews and the viewing step keep drawing it one key at a time. So a person looks at each mode through the one-key drawing, and the export holds the file a page shows to that drawing.

### 2. A current copy's name holds the language and a key

A current copy's file takes its version's name with the number left out, in every format. `sockets.en.default.svg` is the copy of `sockets.v3.en.default.svg`. A page links that name.
- **The language.** Each language is a scene of its own (DEC-005 point 6), so a page links the file in its own language.
- **Which combinations share a file.** Combinations share a switching file where they differ only in modes of the pairs this format reads (point 4). A mode two combinations hold alike does not part them, whether or not this format reads its pair.
- **The key.** A switching file takes the first key it serves, as a variant does (DEC-004 point 3). So `default` holds the combination of defaults, as it does everywhere. A piece that names only the dark mode takes `colour-scheme.dark`.
- **A piece names one of the two formats.** The SVG format and this one write the same name. So a piece that names both fails validation, in a file the project can correct, and an export refuses it.

### 3. The numbered version holds the same file

- **The export makes the form.** The switching file is a file of its version, under its number. So the record of exports holds its hash, and marking final moves it with its version ([visual-communication:DEC-017-final-and-published-states] point 2).
- **A current copy is those bytes.** Whatever writes a current copy writes it from the file its version holds. Nothing draws a copy apart.
- **What the hash is taken of.** The whole file, with every mode it holds, as for any exported file. So the version's file and the copy's file keep one value (DEC-017 point 7).
- **So the freeze holds what the page shows.** Where the version marked final wrote the copy, the file handed out is the file the page shows, byte for byte.

### 4. A renderer's declaration pairs a shared mode with the reader's signal

The SVG renderer's declaration names this format with the signal pairs it reads ([visual-communication:DEC-023-html-page-modes] point 5). They are the colour scheme's: `light` and `dark`, with the same values of `prefers-color-scheme`.
- **In the declaration.** What a browser tells an image belongs to a file read in a web page, so it sits with what the renderer declares. DEC-005 point 10 already has a renderer name a mode of a shared axis, as its font profile.
- **A value axis only.** Each mode of a size axis takes a scene of its own (DEC-005 point 6), and a rule cannot redraw a scene.
- **Every mode it follows.** A pair names each mode, the axis's default included. So a rule can name any of them, whichever a brand's default is.
- **What reads it.** Computing a scene reads no pair, so axes stay data to the engine. The renderer reads the pairs to write its rules. The check and an export read them as plain data in the declaration, to refuse a piece (below).
- **No library changes,** so no release waits on this record (DEC-013 point 1).
- **What a pair relies on.** The names of a shared axis and its modes are public (DEC-004 point 5). A test holds each pair to what each shipped major of the foundations declares, the axis's kind included (DEC-013 point 2).
- **A mode of no pair this format reads.** In this format, two combinations a piece names may not differ in a value axis's mode of no pair this format reads. The format holds a value axis's modes in one file, the choice DEC-006 point 7 leaves to it, and a rule can reach only a mode of a pair this format reads. So such a piece fails validation, in a file the project can correct, and an export refuses it.
- **That is no loss.** It limits what the format takes from a piece, as point 2's rule on the two formats does.
- **What that leaves.** A mode the combinations hold alike parts nothing, so a neutral piece that names no contrast passes. High contrast takes a piece of its own.
- **Another pair it reads** is a new version of the renderer, after a test of its own.

### 5. The file follows what the browser tells it

- **One signal.** The file reads the reader's signal and nothing else. An image runs no script, and the page around it holds nothing for it (point 6).
- **So a reader's switch reaches the file as far as the browser carries it.** The reader's system preference sets the signal. A site's own switch sets it where the image's element takes a single CSS `color-scheme`, as it does from a page's root. The browser must also read that for an image.
- **The floor.** A browser that applies the rules and one that ignores them each show a whole figure, in one of the piece's modes. The rules repaint together, and an export holds each combination to its one-key file, unless a person let a difference through (point 1).
- **The reach.** Context says what a test and a person's look found, each on its date. Accepting this record accepts that reach, and what a reader is promised narrows to it (Implications).
- **A site that sets no single `color-scheme`** leaves the file on the system's preference. So a light site, read under a dark system, shows a dark figure on a light page.
- **A figure that misses the mode** stays readable where it paints its own ground. Where a file of this format has no ground of its own in a mode it holds, dark text could meet a dark page. So that asks for attention, names the page and asks the piece's owner for a ground. It never fails, and it repeats until a ground is there, as an estimated overflow does.
- **What a browser does is a fact.** One file may show another mode from one load to the next. That lies outside the same answer on every machine ([visual-communication:DEC-002-files-and-validation] point 6), which binds the capability's check. The project cannot correct it and nobody is expected to act, so no finding asks for attention ([visual-communication:DEC-002-files-and-validation] point 7). The capability's reference page states the reach, with its date.

### 6. A page shows a current copy as any image

- **The form.** `![alt](path)`, with the copy's path, no fragment and no HTML. Its alt text is the figure's text alternative ([living-docs:DEC-002-visual-elements] point 8).
- **It fits by one reading of the rule on styling.** A theme reaches an image a renderer writes through the renderer's settings. This capability is that renderer, and the format and the modes a piece names are among its settings ([visual-communication:DEC-001-visual-communication-discipline] point 10, by an edit below). The file's CSS rules are what the renderer wrote from them.
- **Accepting this record accepts that reading,** beside the reach, and no word of that rule moves.
- **A change of look flags no page.** A value a brand changes rewrites the file, which no page anchors ([living-docs:DEC-002-visual-elements] point 4).

### 7. This capability answers for the freshness of what it renders

- **The rule is living-docs'.** What renders an image a page shows answers for whether it is fresh. That fits any producer, so it lands in living-docs' record with its reason (Implications). A page anchors what produced the image, and a change there flags the page ([living-docs:DEC-002-visual-elements] point 4).
- **Here.** The accepted records already say how this capability answers. A published piece's stale current copy fails (DEC-006 point 8). Once its piece leaves that state, no check holds the copy (DEC-017 point 5).
- **What stays open.** A shared way to configure renderers waits for a project that runs two (COR-007).

## Rationale

**Why one file.** A page shows one path, in a form any Markdown renderer reads, so only the file can change with the mode. A file for each mode needs two paths in the page, and each way to write them breaks a rule (Alternatives considered). For a vector figure, one file also puts half the bytes into a history that keeps them for good (DEC-006, Rationale).

**Why a format of its own.** A file for each combination has jobs of its own. A person hands out one chosen mode, and looks at each mode in a preview. Changing the SVG format would move those jobs and every reference output. A format of its own is an addition, and leaves them alone.

**Why the same renderer.** The drawing is SVG either way, so a second renderer would add a second version, and a second drawing to keep equal. One renderer paints the same drawing two ways, and the comparison catches a slip. The cost is a shared version: each file names it, so a rise for one form rewrites both at the next export.

**Why the plain drawing comes first.** A tool that reads no rule then gets a whole figure. The file is the first combination's drawing with its paints made open to a rule, so one comparison can hold it to the one-key file.

**Why the name keeps a key, and the first it serves.** One rule then serves every format: the version's name less its number. The first key is a rule the records already hold for a variant, so a key gains no new meaning. It holds when an axis with a default is added, so a page's link holds too. A piece moving from the SVG format keeps its default file's name. One cost is a name that says `default` of a file that may show dark. Another is a name that changes where a dark-only piece gains the light mode.

**Why a piece names one of the two.** Both would write one name, and no case asks for both yet. A piece that needs one fixed mode as a file names the SVG format, and a second piece serves a page.

**Why the numbered version takes the form.** If only the copy took it, no version would hold the file. A piece marked final would then lack the file its page shows, and its freeze would differ from what readers saw.

**Why the pair lies in the renderer's declaration.** A signal belongs to where a file is read, and the foundations serve every such place. A change there would also hold back their release. A piece or a brand would repeat the pair, and could get it wrong. A renderer may declare a choice its medium needs (DEC-001 point 2), and the font profile's rule has one name a shared mode so.

**Why this format reads only the colour scheme's pairs.** Each format reads the pairs its medium reaches, and a new pair comes after a test (DEC-023 point 5). `prefers-contrast` did not reach an image in Chrome, so this format reads no contrast pair yet. GitHub's high-contrast themes wrote only the colour scheme, so such a reader got the light or the dark drawing.

**Why a mode of no pair this format reads fails.** This format holds a value axis's modes in one file, and that file can hold only the modes its pairs reach. What becomes of any other mode is the format's own (DEC-006 point 7). A piece that names such a mode asks for what the format cannot do, so it fails at once. A renamed mode in a later major then stops no figure in silence. A loss would not fit: the renderer drew each mode whole, so nothing was lost. The cost is a second piece for high contrast, and no case asks for that yet. A size axis's modes are scenes of their own, so they take files as before.

**Why a drawing with no ground is a finding.** It is what the scene sets, so nothing was lost, and a person may mean it. So it asks for attention and never fails. A released component with no ground leaves it repeating, and that is the cost.

**Why an export compares the files.** The floor rests on it. Previews, the viewing step and a reviewer all see the one-key drawing, so nobody sees the file a page shows before a reader does. The comparison needs no browser, so it costs an export little. A stop with no way past would trap a published piece. Only an export mends a stale copy, and only a release of the capability mends the renderer. So a person may go past it, as DEC-016's Rationale says of an overflow.

**Why the record goes on.** The issue stops the record where no form that fits follows the reader's switch. Here each half is a judgement. The form fits by a reading (point 6). It followed in Chrome and Firefox as far as the test reached, and in part in WebKit. So neither half is plainly met or plainly failed. The record states both, and acceptance settles them.
- **What it buys.** In Chrome and Firefox the figure takes the reader's mode, with no page text for it.
- **What that rests on.** Following the system rests on what browsers ship. In the test, following a site's switch rested on a draft of CSS, and on a detail of GitHub's stylesheets that GitHub does not document. If either moves, a figure follows only the system, and nothing says so.
- **What it costs in WebKit.** In the test, a figure in the other mode on many loads, readable where it paints a ground. The mode can change from one load to the next, and a single image never varies so.
- **What it costs on a site that sets no single `color-scheme`.** A dark figure on a light page, where a single light image would match.
- **What might reach WebKit.** The fragment and `<picture>` did in the test, and each writes HTML or a host's word in a page, which reopens the documentation's rule. The cause of WebKit's result is unknown, and the web view may be part of it.

**Why that reading of the rule on styling.** The rule keeps a theme out of content, so a change of theme changes no content and flags no page. This form keeps that. The page's text names no mode, and a change of look touches only the file. The rule also counts an image file as content, and content sets no colour or theme. Read word for word, no vector image could be content, since each names its colours. So the reading takes the bullet beside it, on what a renderer's settings reach. The founding record reads it so for libraries and a lock (DEC-001 point 10).

This is the reading's hardest case. The rule names light and dark as presentation. A file painted in one theme only shows a theme, and this file picks between two as it is read. So the reading asks more here than it has before.

**Why the reading stays in this record.** The issue asked for a form that fits that rule as it stands, and a form that needs a sentence to fit does not. The founding record reads the same rule from here (DEC-001 point 10). Living-docs reads no image, so no check of its own meets the file. The cost is that a person who reads that rule alone does not meet the reading.

**Why the rule on freshness lands in living-docs, and names no record here.** It binds any producer, a project's own build among them, over which this capability has no standing. Living-docs stands without this capability, so its record takes words that fit any producer, with its own reason. It stays within that point's diagrams. A screenshot or a recording keeps true through its own script, as that record's point 5 says.

### Alternatives considered

- **One image on its own ground, with the promise narrowed to a fixed mode.** Rejected. It costs no format, and every dark page shows a light figure. Following in Chrome and Firefox is worth one format. Against that, this form is worse in two places. Its mode varied by load in WebKit. And a light site that sets no single `color-scheme` can show a dark figure.
- **One image now, and this format once Safari is known.** Left out as a decision, and open to any piece. A piece that names the SVG format today keeps its default file's name when it moves to this one (point 2).
- **A file for each mode, in a `<picture>`.** Rejected. It is no `![alt](path)`, and its `media` attribute themes an image ([living-docs:DEC-002-visual-elements] points 1 and 5). Each page would name a path for each mode.
- **A file for each mode, with GitHub's fragment.** Rejected. It puts one host's word into content, as living-docs refuses for a callout. Any other renderer shows both images. It is the one form seen following both signals in WebKit, which is what this rejection gives up.
- **An inline `<svg>` in the page.** Rejected. It is HTML, and GitHub removes it.
- **The SVG format holding the modes itself.** Rejected, for the reasons above.
- **A renderer of its own for the format.** Rejected, for the reasons above.
- **Only the copy taking the form.** Rejected, for the reasons above.
- **CSS's `light-dark()` in place of a rule.** Left out. In WebKit it varied as the rule did, and runs that swing so widely cannot rank them. The file's plain drawing already serves a tool that reads neither.
- **A name with no key.** Rejected. It adds a second shape of name, and moving from the SVG format breaks a page's link.
- **A key that leaves out the modes of the pairs this format reads.** Rejected. `default` would then name a dark drawing, and a key would gain a meaning of its own.
- **A mark in the name, so both formats can stand.** Left out. No case asks for it, and a later change may add one.
- **A file for each mode of no pair this format reads, reported as a loss.** Rejected, for the reasons above.
- **A pair in the foundations, a brand or a piece.** Rejected, for the reasons above.
- **Reading the contrast's pair.** Left out until a test shows it reaching an image.
- **A sentence in the rule on styling that says what point 6 reads.** Left out, for the reason above. Accepting this record settles that the reading is no change to the rule, so a later sentence saying it would only clarify.
- **A check in living-docs that an image is fresh.** Rejected. Only what wrote a file knows what it was made from.

## Implications

- **Edits to accepted records,** each made once this record is accepted. Each cites this record, but for those in living-docs. Accepting this record accepts them (COR-066 point 5).
  - **The founding record, point 10, "A figure in a documentation page".** The piece's libraries, its lock, its format and the modes it names are that renderer's settings.
  - **The record of the engine and its plugins, point 9, "Each declares what it supports".** The bullet already has a renderer name each format that holds modes, with the signal pairs it reads (DEC-023). A sentence ends it: for the SVG renderer's format that holds several modes in one file, the pairs it reads also limit what that format takes from a piece.
  - **The record of work outside the engine and outputs, point 7.** A bullet follows "No number or date that overflows". An export stops where a switching file the SVG renderer draws paints a combination it holds otherwise than that renderer's file of that combination. It names the element, and the person who runs it may name that element to let it through.
  - **Its point 7, "What it only records".** It also names each element of a switching file the version let through.
  - **Its point 7, after "The export's gate".** A bullet of its own follows. Every export refuses a piece that fails validation on naming both formats, or on a mode of no pair its format reads.
  - **Its point 7, "A published piece's current copy".** A sentence follows the first. Its files hold the bytes of the version that wrote them, each under that file's name with the number left out.
  - **Its point 8, "They fail validation".** It adds a piece that names both the SVG format and the SVG renderer's format of a switching file. It adds a piece in that format whose combinations differ in a value axis's mode of no pair its format reads.
  - **Its point 8, "They ask for attention".** It adds a file of that format with no ground of its own in a mode it holds, until a ground is there. It adds a current copy made with an element of a switching file let through, and names the capability as the fault's owner.
  - **The record of final and published states, point 1, "A number or a date let through".** An element of a switching file let through is named the same way, and stops nothing.
  - **The record of final and published states, Implications, "The changes that write and hold a current copy".** Its last sentence reads: [visual-communication:DEC-018-copy-follows-reader-mode] point 3 says what the hash is taken of.
  - **Living-docs' record of visual elements, point 2, "Another diagram language".** Its last sentence becomes two. "What renders such an image answers for whether it is fresh, and this capability reads no image. A shared way to configure renderers waits for a project that runs two (COR-007)."
  - **Its Rationale.** A paragraph joins it. "**Why what renders an image answers for its freshness.** Only what wrote a file knows what it was made from. A check here would have to read each producer's record, and a project's own build keeps none it could read. The page's anchor already carries a change of the source."
- **These need no edit:**
  - Living-docs' record of visual elements, point 1, as point 6 reads it, and its points 4 and 5.
  - The record of the viewing step, point 1, since the step goes on drawing one key at a time.
  - The record of brands and notations, point 3, which has a file that holds several combinations take its key as a picture's variant does. That covers a switching file (DEC-023).
  - The record of brands and notations, point 2, and the record of the engine's point 6. Each already gives a scene every combination's values.
  - The record of work outside the engine's point 7, "What a run makes". It leaves to each format a mode of no pair that format reads, and this format refuses a piece whose combinations differ in one (point 4).
  - The record of work outside the engine's point 3, whose variants travel with the file.
  - The record of what an export reads, point 1. A piece's formats stay an input, so moving to this format reads as a change, and one export mends it.
  - The record of final and published states, points 2 and 7, since a version's files and a copy's entries keep their shape.
- **Project-kit's use case of putting a figure in a page, and its glossary, narrow** in the change that makes these edits. That covers UC-094's goal, step 5 and postconditions. In the glossary it covers the copies of that goal, "A reader's mode" and the example in the term for a mode. They say the figure takes the mode the reader's browser tells an image, and follows a switch that reaches it. Accepting this record accepts that.
- **Revisit this record,** which reopens the rule on `![alt](path)` as living-docs' own question:
  - if a reader's own setting on a site does not reach the file in a browser the test saw follow it;
  - if an engine the test saw vary does worse than a figure in the other mode, readable where it paints a ground;
  - if a browser or a host drops what following a site's switch rests on, which nothing watches, so a reader's report raises it.
- **What anchors the edited points** may owe answers once the edits land. The change check names them.
- **The change that builds the format** carries out points 1, 2, 4 and 5's finding.
  - It names the format's word, which a piece may name as an addition the format allows (DEC-003 point 3). Its file's extension stays `svg`, so the word and the extension part.
  - It fixes how a rule reaches an element, an opacity and a paint left out among them. A test in a browser holds that each way repaints, which the export's comparison cannot show. It draws an arrowhead for each paint a rule can change, since one arrowhead now serves one colour.
  - It hands the renderer the keys that share a file in one call, with each key's values, as DEC-023 point 2 decides for any format that holds modes. Where the seam does not carry that yet, its version rises with that change (DEC-005 point 8).
  - It gives the check the viewing step's test of a page's ground (DEC-015).
  - It writes the reach, with its date, into the reference page on outputs.
- **The changes that write and hold a current copy** carry out point 3.
- **The first change that publishes a figure this way** shows it on its real page. What a person finds there answers to the revisit above.
- **A documentation site's switch** reaches such a file only where the site sets a single CSS `color-scheme`. Whether a site's criteria ask for that is living-docs' to weigh ([living-docs:DEC-002-visual-elements] point 9).
