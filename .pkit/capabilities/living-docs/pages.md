---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/schemas/page.schema.json
        - .pkit/capabilities/living-docs/schemas/page-kinds.yaml
        - .pkit/capabilities/living-docs/schemas/page-kinds.schema.json
        - .pkit/capabilities/living-docs/schemas/source.schema.json
        - .pkit/capabilities/living-docs/templates/reference.md
        - .pkit/capabilities/living-docs/templates/signpost.md
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
        - .pkit/capabilities/living-docs/scripts/_lib/formats.py
        - .pkit/capabilities/living-docs/scripts/_lib/sources.py
        - .pkit/capabilities/living-docs/scripts/_lib/source_layout.py
        - .pkit/capabilities/living-docs/scripts/_lib/declarations.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/new.py
      record: ["living-docs:DEC-001", "living-docs:DEC-002", "doc-examples:DEC-001", COR-050, COR-051, COR-056]
      artefact:
        - RS-LDOC-001
        - RS-LDOC-002
        - RS-LDOC-004
        - RS-LDOC-007
        - RS-LDOC-008
        - .pkit/schemas/README.md#the-friction-block
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/cli/README.md#friction-artefacts---at-rev---json
        - RS-LDOC-003
        - RS-LDOC-005
---

# Pages

What makes a document a page of living-docs, and what a page holds ([living-docs:DEC-001-living-docs-discipline] point 4).

## Contents

<!-- pkit:contents -->
- [A page's fields](#a-pages-fields)
- [Anchoring one part](#anchoring-one-part)
- [A kind's format](#a-kinds-format)
- [Types](#types)
- [Sources](#sources)
- [Visual elements](#visual-elements)
<!-- /pkit:contents -->

## A page's fields

A document is a **page** when it is of this capability's page type, `living-docs:page` ("Types" below). Mostly, that means two things. It lies in a documentation root or in a project place that holds pages, and it declares its page kind in `kind`. A page's front matter carries two fields of its own, beside the core's friction block in the `pkit:` container:

```yaml
---
reader: user          # who the page is for: an id of the readers point (user, maintainer, …)
kind: signpost        # the page's kind: the template it follows
pkit:
  friction:
    anchors: { path: [src/cli/**], record: [ADR-006] }
---
```

- **Their shape.** `reader` and `kind` are each a word (`[a-z][a-z0-9-]*`). Their shape is `schemas/page.schema.json`, which validation applies to `kind` on every page, and to `reader` where `RS-LDOC-003` binds.
- **The friction block** is the core's, and `pkit validate` checks it under `friction`.
- **An unclassified document** lies in a space's places, and no other owner claims it. It is no page, no decision record and no rule-set file. It is counted for onboarding to classify, never failed. A document that names a reader but declares no kind is one.

## Anchoring one part

A page that rests on one part of a record or of another document may anchor that part. A change to another point or section of it then asks the page nothing ([the CLI reference, "friction check"](../../cli/README.md#friction-check---base-ref---head-rev---json)).

- **How an anchor names a part** is in [the schemas reference, "The friction block"](../../schemas/README.md#the-friction-block). A record's point is `COR-050#2`, a document's section is its heading's slug, as `docs/cli.md#output`, and its lead is `docs/cli.md#`.
- **What names no part:** a path and a `source`.
- **What it grounds.** An anchor on one part grounds only what that part stands on (`RS-LDOC-001`). A summary of a fact whose home is another page anchors the home's section (`RS-LDOC-002`).

## A kind's format

Pages of a kind follow one format (`RS-LDOC-004`). A kind's template is the starting shape a page of the kind is filled in from. The part of the format validation checks is the kind's *structure*: the sections every page of the kind carries, in order where order matters.

- **Where a structure is declared.** Each kind this capability ships declares its structure once, in `schemas/page-kinds.yaml`. That file is where to read what a kind's pages must carry.
- **What a structure holds.** Each section is a heading level and, where the kind fixes the wording, its text. The sections come in the order listed, unless the kind sets `ordered: false`.
- **What it leaves out.** A structure names only what every page of the kind must carry, so a template may show more, and a page may carry other sections.
- **A kind with no structure,** such as a kind the project adds. Where `RS-LDOC-004` binds on a page of such a kind, the page is reported with its kind and never failed.

A section is a heading written with one to six `#` at the start of a line. These are not read as one:

- a `#` line that is indented, such as under a list item, or that lies inside a block quote, fenced code or an HTML comment
- an underlined (setext) heading
- an HTML heading, such as `<h1>`

A section the kind leaves to its writer needs words of its own, so an empty `#` and a template's unfilled `<placeholder>` do not count. Fixed text is compared ignoring case, runs of white space and trailing punctuation.

### The kinds' templates

`templates/` holds each shipped kind's template:

- **`signpost.md`**, for an index-like file that says what a folder holds and where to go (`RS-LDOC-005`).
- **`reference.md`**, for the page that describes one surface to the reader who uses it, such as an area, a capability or an adapter. The page anchors the code and decisions it describes.

A page of a kind the project adds is written by hand from that kind's own template. A template copied into the definitions location takes the template type there, so it is never a page ("Types" below).

## Types

The capability declares two types in its package metadata, under `friction.types` (DEC-001 points 2 and 4, COR-056). The backbone gives each document its type from the places that match it, and validation reads that answer. A rule set's scope can select pages by their type, `types: [living-docs:page]`.

| Type | What it is | Kind field | On the project's own places |
|---|---|---|---|
| `living-docs:page` | a page of a documentation space | `kind` | admitted |
| `living-docs:template` | a writer's tool in the definitions location, never a page | none | not admitted |

- **The roots give the page type.** Each documentation root is a place of the capability's that gives `living-docs:page`. A document there takes the type only when it declares its page kind in `kind`, present and not empty. One that declares none takes no type and is no page.
- **The definitions location gives the template type.** It ranks ahead of the internal root, so a page template copied there is a template, never a page, though it carries `reader` and `kind`. The definitions there are rule sets, and every rule takes the backbone's type for rules.
- **A project place outside the roots.** It takes the page type when written as `{path: CONTRIBUTING.md, type: living-docs:page}` in `friction.places`. A place left untyped holds the pages that declare their kind there, unless it is an unassigned place of rule sets. They have no type, so a scope that selects by type misses them. So type such a place before a space's definition selects pages by type (DEC-001 point 1).
- **A type of the project's own.** A place inside a root that gives a type of the project's own, such as `{path: docs/changes, type: change-note}`, ranks ahead of the root. Its documents are the project's, and their `kind` is never read as a page kind.
- **Another owner's documents.** A document of another component's type is that component's. So is one it holds in a folder it declares, and one of no type in a place it declares. Validation never reads their `reader` or `kind`.
- **A place another component declares without a type** shadows no other place (COR-056 point 3). So a document there that declares a page kind takes the page type from the root around it, and is a page. `pkit validate` reports, under `packages`, that the root typed the component's file. The component keeps such documents by typing its place.
- **A decision record that would otherwise be a page** fails validation. That is one of the page type, or one of no type that declares its page kind in an untyped project place outside the roots. A decision record is never a page, and validation reads a document's `id` only to tell a decision record.
- **A tie.** Where two typed places rank equal and give different types, the document counts as each (COR-056 point 3). One that counts as the page type is a page until the tie is mended, whatever other type it counts as.
- **Where to read it.** `pkit friction artefacts --json` gives each document its `type`, the place that gave it, and its matching places in the backbone's order ([the CLI reference, "friction artefacts"](../../cli/README.md#friction-artefacts---at-rev---json)).

## Sources

A page that rests on a text outside the repository anchors it with the `source` kind, by the source's name. Such a text is a standard, a specification or another project's documentation:

```yaml
pkit:
  friction:
    anchors:
      path: [src/release/**]
      source: [keep-a-changelog]
```

**Each source is captured once.** The friction checks read the repository alone and never reach the network. So each source is captured in a file of its own, `.pkit/capabilities/living-docs/project/sources/<name>.yaml`:

```yaml
# yaml-language-server: $schema=../../schemas/source.schema.json
title: Keep a Changelog
url: https://keepachangelog.com/en/1.1.0/
version: "1.1.0"
```

- `title`: what the source is called. Required.
- `url`: where it is found. Optional, since a printed standard has none.
- `version`: which text of the source the pages were last checked against, as the source labels that text, such as its version, edition or revision. Required.
  - For Keep a Changelog, it is the document's `1.1.0`, not the release its own changelog has reached.
  - For a source that labels no text, it names the exact text another way, such as a commit of the repository it is published from.
  - Only where nothing names it, it is the date the source was read, `YYYY-MM-DD`. That records when, not what, so a later reader has nothing to compare it with.
  - It is quoted, since YAML reads `1.1` as a number and `2026-10-03` as a date, and the shape wants text.

**The file holds nothing else.** It is bound to its shape, `schemas/source.schema.json`, by its path, so it needs no `pkit_schema`. A `schema_version` would make any later version of the shape rewrite every captured source. The editor directive comment is optional, written when the file is created. Who captured a source, and when each version was recorded, is git's to say.

**The name** is lower-case words of letters and digits joined by single hyphens, such as `rfc-9110`, `iso-8601` or `owasp-top-10`. It starts with a letter, and holds at most 64 characters, so one name is one file on any disk.

- **No digit first,** so `twelve-factor-app` stands for the twelve-factor app.
- **No dot,** since a version belongs in the file, not the name.

**What counts as the source changing: any change to its file, nothing else.** That is why the file holds only these fields. What the source says, and why a page relies on it, are written on the page.

- **The edits it has reason to see:** recording a new version, and correcting the title or the address. Each asks every page anchored to the source for its answer: updated, unchanged with its reason, or deferred.
- **Other edits ask them too:** a comment added later, a reformat, or `1.1` rewritten as `1.1.0`. A repository-wide YAML formatter, or a change of line endings, asks every page anchored to a source at once.
- **A new version asks every page resting on any part of the source.** To narrow that, capture the parts relied on separately, such as `owasp-top-10-a01`, knowing that nothing keeps their versions in step.

**Recording a new version.** On reading a new version of a source, edit `version`, and `url` if the address moved, in a pull request. The change check asks every page anchored to the source to answer in the same pull request. A change to the source that nobody records is not seen, since nothing fetches it.

**Dead, or no answer.** A name no file captures is a dead anchor. The change check fails it where the pull request adds it, and the whole-repository check reports it.

- **Commit a source's file** with the page that first anchors it. A file only the working tree holds is no answer to a check that reads HEAD.
- **Where sources are kept cannot be read,** through a permission or disk error: the resolver gives no answer. The page is not judged, and the documentation check reports itself unresolved until a run succeeds (DEC-001 point 7).

**Rule-set origins** may cite a captured source as where a rule's words were said: `origin: {…, source: {kind: source, value: keep-a-changelog}}` (COR-051 point 5).

**Uninstalling living-docs** removes its project tier, captured sources with it, which stay in git history. It leaves every `source` anchor with no resolver. Whoever uninstalls it removes those anchors in the same change. Where friction is enforced, the change check fails a pull request that keeps them while it takes their resolver away.

`pkit living-docs resolve-source <name>` prints the file a name resolves to. It is the resolver the friction checks run, and `--json` prints `{"paths": [...]}`.

## Visual elements

A page may show diagrams, images, console output and callouts. Each is neutral content: the page holds no styling, and the presentation decides how it looks. On a repository host, such as GitHub, that is the host's own look, and on a site it is the site's theme ([living-docs:DEC-002-visual-elements]).

- **No styling.** Nothing in a page sets a colour, a font, a theme, a class or a style. That rules out these:
  - Mermaid's `%%{init}%%` directive, and a `config` block in a diagram's front matter
  - `classDef`, `class`, `:::`, `style` and `linkStyle` lines
  - HTML attributes that size, align or theme an image
- **Diagrams.** A diagram is a `mermaid` fence in the page, with an `accTitle` and an `accDescr`. A repository host such as GitHub draws it with no setup, and it reads as text where nothing draws it. Another diagram language is used only where it is rendered to an image, shown as an image.
- **What a diagram shows.** A diagram is never a fact's home. Each fact it shows has its home elsewhere: a decision record the page anchors, or prose on a page.
  - Once `RS-LDOC-007` binds, the home may also be anything else the page anchors that decides or states the fact.
  - The page anchors the home of each fact the diagram draws. A diagram of its own page's prose is a view of that prose. One of another page's fact is a summary, with the link and the anchor a summary takes.
  - For a wide diagram, the page anchors the records that decide its parts and how they relate, never most of the repository.
- **Images.** An image is shown with `![alt](path)`, beside the page that shows it. An image that pages of both spaces show lies beside a user page, never under the internal root. For an image made by hand, a screenshot included, the page anchors what it shows. It anchors the image file too where replacing the image should ask whether the text still agrees.
- **Screenshots from a script.** They are taken with a capture script the project keeps, with its window size, scale and theme in settings of their own. The page anchors the script and what the screenshot shows, never the screenshot, since each new capture would flag the page for nothing. When the script's anchor flags the page, the capture runs again before the answer. The same holds for a recording, an animated image included.
- **Console output.** A command and what it prints go in a shell-session fence, such as `console` for a POSIX shell. Each command follows its prompt, `$ `, with its output below.
  - **Who runs the fences:** the run the doc-examples capability ships, or a runner of the project's own. living-docs never runs the product, and how output that varies is matched is the runner's.
  - **A command that cannot run as a test** goes in a fence of its shell's language, with no output.
  - **The anchor:** the page anchors the code whose output the fence shows.
- **Callouts.** A callout is a block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`. Where nothing draws it, it reads as a block quote.
- **Text alternatives.** A diagram, an image or a recording that carries meaning has a text alternative, and a decorative image an empty one, `![](path)`. Where `RS-LDOC-008` binds, validation checks each `mermaid` fence's (DEC-002 point 8).
- **A documentation site** is optional, and the repository host's own view is the default. A site reads the content as written, and takes its theme for diagrams and callouts from one place. It serves one space: its pages and the images they show, wherever they lie. A technical page's link to a user page reaches the user space's site.

**The two proposed rules.** `RS-LDOC-007` widens a fact's home, for every statement a page makes, to what the page anchors that decides or states the fact. It says a diagram or a page is never such a home. `RS-LDOC-008` is the rule on text alternatives.

- **When they bind:** from the major of `LDOC` that accepts them (DEC-002 point 10).
- **Until then,** a fact's home is a decision record the page anchors, or a page (`RS-LDOC-002`).
