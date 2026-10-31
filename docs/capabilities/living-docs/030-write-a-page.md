---
reader: act-developer
kind: guide
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
        - .pkit/capabilities/living-docs/schemas/page-kinds.yaml
        - .pkit/capabilities/living-docs/templates/reference.md
        - .pkit/capabilities/living-docs/templates/signpost.md
        - .pkit/capabilities/living-docs/skills/docs-author/docs-author.md
        - .pkit/capabilities/living-docs/skills/docs-author/page.md
      record: ["living-docs:DEC-001#3", "living-docs:DEC-001#4", "living-docs:DEC-001#6", "COR-050#5", "COR-050#6", "COR-050#7"]
      artefact:
        - UC-044
        - ACT-developer
        - RS-LDOC-001
        - RS-LDOC-002
        - .pkit/capabilities/living-docs/pages.md#a-pages-fields
        - .pkit/capabilities/living-docs/pages.md#a-kinds-format
        - .pkit/capabilities/living-docs/pages.md#sources
        - .pkit/capabilities/living-docs/pages.md#visual-elements
        - .pkit/capabilities/living-docs/README.md#authoring-the-docs-author-skill
        - .pkit/capabilities/living-docs/validation.md#what-fails
        - .pkit/capabilities/living-docs/validation.md#what-a-page-mentions-and-does-not-anchor
        - .pkit/cli/README.md#sync
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#declare-your-readers
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#declare-the-pages-outside-the-documentation-roots
---

# Write a page

A page is written for one reader of one space, follows its kind's format, and anchors what each of its statements rests on. Here you stamp a page, fill it in and check it. A page's fields, its kinds and the sources it may anchor are in [the reference on pages](../../../.pkit/capabilities/living-docs/pages.md#a-pages-fields).

## Contents

<!-- pkit:contents -->
- [Why a page names its reader and its anchors](#why-a-page-names-its-reader-and-its-anchors)
- [Stamp the page](#stamp-the-page)
- [Fill it in](#fill-it-in)
- [Check it](#check-it)
- [Anchor a source outside the repository](#anchor-a-source-outside-the-repository)
<!-- /pkit:contents -->

## Why a page names its reader and its anchors

A page with no reader says everything to everyone, and its reader has to find their part. A statement with no anchor is never asked about again when its ground changes. So each page says whom it is for, and what each of its statements rests on.

Here is a page about the script `src/greet.py`, for the user space's readers. Its anchor names the script, so a change to the script flags the page:

```markdown
---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/greet.py
---

# Greeting

`src/greet.py` prints a greeting and exits.
```

## Stamp the page

The stamp writes the page from its kind's template, with its reader and its anchors in its front matter. Your agent's `docs-author` skill walks it through these choices ([the reference, "Authoring"](../../../.pkit/capabilities/living-docs/README.md#authoring-the-docs-author-skill)):

- **The space.** The user space serves the people who use your system, and the technical space those who build it.
- **The kind,** the page's format ([the reference, "A kind's format"](../../../.pkit/capabilities/living-docs/pages.md#a-kinds-format)). `reference` describes one thing to the reader who uses it, such as a command or a part of the system. `signpost` points into a folder, and only says what the folder holds.
- **The reader.** `user`, `maintainer`, or a reader your project declares ([Set up your spaces, "Declare your readers"](010-set-up-your-spaces.md#declare-your-readers)).
- **The file.** It goes under the space's documentation root, or into a place you declared for the space ([Set up your spaces](010-set-up-your-spaces.md#declare-the-pages-outside-the-documentation-roots)).
- **The anchors.** Name the code it describes with `--path`, the decisions it applies with `--record`, and rules or another page's section with `--artefact`.

Each fence on this page starts from a fresh project, so it first installs living-docs and creates the user space, their output dropped:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p src && echo 'print("Hello")' > src/greet.py
$ pkit living-docs new page docs/greet.md --space user --kind reference --reader user --title "Greeting" --path src/greet.py
stamped docs/greet.md: a reference page of space 'user', for reader 'user'.
These lines still hold the template's placeholders: write in each what it asks for.
  docs/greet.md:13: <One paragraph: what this surface is for, for this reader, and the decision it rests on.>
  docs/greet.md:15: ## <A part of the surface, or a task the reader does with it>
  docs/greet.md:17: <What the reader does and what holds, each rule citing the decision it comes from.>
Anchor each statement on what makes it true (RS-LDOC-001), then run `pkit living-docs validate`, `pkit validate` and `pkit friction check`.
```

`--dry-run` shows the page the stamp would write, and writes nothing. The stamp refuses these, and writes nothing:

- a file that exists
- a reader your project does not declare, once the space has its definition
- a file that would not be a page of the space you named

## Fill it in

Write in each placeholder's place what the page's reader needs, and nothing else. Two rules decide most of what you write:

- **Each statement rests on an anchor.** A statement whose ground the page does not anchor gets its anchor, or goes. Add an anchor under the friction block's `path`, `record` or `artefact` list.
- **Each fact has one home.** A fact a decision record decides has the record as its home, where the page anchors the record. Any other fact has one page as its home. Another page states it only as a summary that links to that page, and anchors the section it links to.

For instance, a guide that summarises what `pkit sync` writes links to the section of the command reference that says so in full. It lists that section among its `artefact` anchors, as `<page>#<section>`. A change to that section then flags the guide.

A page may show a diagram, an image, console output or a callout, with no styling of its own ([the reference, "Visual elements"](../../../.pkit/capabilities/living-docs/pages.md#visual-elements)).

## Check it

Run `pkit living-docs validate` until it reports no error, then commit the page. A page new in its change owes no answer to the friction checks. Below, the page names a second script it does not anchor:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p src && echo 'print("Hello")' > src/greet.py && echo 'print("Bye")' > src/farewell.py
$ pkit living-docs new page docs/greet.md --space user --kind reference --reader user --title "Greeting" --path src/greet.py >/dev/null
$ echo 'Run `src/greet.py` to be greeted, and `src/farewell.py` to be sent off.' >> docs/greet.md
$ pkit living-docs validate | tail -3
mention(s) a page's anchors do not cover, each with an anchor that would cover it (1):
  docs/greet.md
    18: path `src/farewell.py` → path: [src/farewell.py]
```

- **What fails.** A reader your project does not declare, and a page whose sections do not follow its kind's format, are errors ([the reference, "What fails"](../../../.pkit/capabilities/living-docs/validation.md#what-fails)).
- **What is reported.** Validation reports each file path, record, rule or `pkit` command the page names but does not anchor. It gives the anchor that would cover each. Above, `src/greet.py` is covered, and `src/farewell.py` is not.
- **A name that states nothing.** A passage may only name a thing, and say none of its facts. A mark right after the mention then passes it over ([the reference](../../../.pkit/capabilities/living-docs/validation.md#what-a-page-mentions-and-does-not-anchor)):

  ```markdown
  Run `src/farewell.py` <!-- unanchored: named as the next step, not described --> to be sent off.
  ```

- **Who writes a mark.** A person decides each mark, as they decide each answer. An agent may propose one, and writes it only once you accept its words.

## Anchor a source outside the repository

A page that rests on a standard, a specification or another project's documentation anchors it as a captured source. The checks never reach the network, so you record which text of the source your page was checked against ([the reference, "Sources"](../../../.pkit/capabilities/living-docs/pages.md#sources)). Below, the source's file is written, `resolve-source` shows that its name finds the file, and the page anchors it:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p .pkit/capabilities/living-docs/project/sources
$ printf 'title: Keep a Changelog\nurl: https://keepachangelog.com/en/1.1.0/\nversion: "1.1.0"\n' > .pkit/capabilities/living-docs/project/sources/keep-a-changelog.yaml
$ pkit living-docs resolve-source keep-a-changelog
.pkit/capabilities/living-docs/project/sources/keep-a-changelog.yaml
$ pkit living-docs new page docs/changes.md --space user --kind reference --reader user --title "The changelog" --source keep-a-changelog | head -1
stamped docs/changes.md: a reference page of space 'user', for reader 'user'.
```

- **The file** holds `title`, `url` where the source has one, and `version`, and nothing else. Its name is the source's name, and a name no file captures is a dead anchor, which the checks fail where a change adds it. Commit the file with the page that first anchors it, since the checks read what is committed.
- **A new version.** When you read a newer text of the source, edit `version` in a pull request. Every page that anchors the source is then flagged, so you judge what the new text changes for it.
