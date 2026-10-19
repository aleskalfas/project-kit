---
id: DEC-002
title: Pages show diagrams, images, console output and callouts as neutral content
status: proposed
date: 2026-10-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A page often explains best with more than prose. It draws a diagram, shows a screenshot, quotes a command with its output, or marks a warning. Each of these can drift from the software as prose can, and each can carry styling that belongs to one host or one theme.

[living-docs:DEC-001-living-docs-discipline] keeps each page true through its anchors, and gives each fact one home. It says nothing yet about visual elements:
- **A fact's home** is a decision record the page anchors, or a page (DEC-001 point 3). Any other home waits for a page that needs it.
- **An image is never an artefact,** since it has no front matter (COR-050 point 1). So it is never a page either (DEC-001 point 4).
- **The capability never runs the product.** Executed checks belong to another component, and their results arrive as reading evidence (DEC-001 points 6 and 7).

The maintainer set three constraints on 18 October, on [project-kit#1770](https://github.com/aleskalfas/project-kit/issues/1770):
- **The direction:** pages support at least images and diagrams, and other media where needed. Rendering is configurable, and screenshots, console output and callouts are wanted.
- **A diagram is a view of truth held elsewhere:** in decisions, requirements, use cases or code. It states nothing that has no other home, and it anchors what it shows.
- **Content and presentation stay apart:** content is neutral and true, and carries no styling. Presentation is a layer each project configures, and a sensible default needs no setup and reads right on GitHub.

A design note weighed the options against established practice: docs-as-code, diagram-as-code tools, documentation sites and WCAG's text alternatives. The maintainer took its recommendations on 19 October, on the same issue. This record holds living-docs' share of them. A diagram inside another component's artefact is that component's to decide.

## Decision

**A page shows a diagram, an image, console output or a callout as neutral content, and each project's presentation layer decides how it looks. A diagram is Mermaid text in the page by default, and never a fact's home. A page anchors the source of an image or a recording it shows, never the file a tool produced.**

### 1. Content and presentation stay apart

What a page holds is content: true, neutral, and the same wherever it is read. How it looks is presentation, which each project configures.
- **Content:** a diagram's Mermaid text, an image file and its alt text, a capture script and what it writes, a shell-session fence, and a callout in the standard syntax.
- **Presentation:** colours, fonts, light and dark, how a diagram or a callout is drawn, how an image is sized and framed, and a documentation site.
- **No styling in content.** Content holds nothing that sets a colour, a font, a theme, a class or a style. Examples are Mermaid's `%%{init}%%` directive, a `config` block in a diagram's front matter, and `classDef`, `class`, `:::`, `style` and `linkStyle` lines. So are HTML attributes that size, align or theme an image.
- **A theme reaches a visual element only through presentation:**
  - on GitHub, through GitHub's own look, which needs no setup
  - on a documentation site, through the site's settings
  - in an image a renderer writes, through the renderer's settings
  - in a screenshot, through the capture's settings, kept apart from the capture script (point 5)

So a change of theme changes no content, and flags no page. One theme file that the site and the renderer both read waits for a project that runs both (COR-007).

### 2. A diagram is a Mermaid fence by default

A diagram is written as Mermaid text in a fenced block of the page, whose info string opens with `mermaid`. It carries no styling (point 1).
- **Drawn with no setup.** GitHub draws the fence, and a site draws it in the project's theme. Where nothing draws it, it reads as text.
- **Its syntax is not validated.** A check would need a Mermaid parser installed, and no parser the capability could pin draws as each host draws. A project may run such a check in its own continuous integration.
- **Another diagram language** is used only where the project renders it to an image, which the page shows as an image (point 5). How the methodology configures a renderer, and checks that an image is fresh, is decided with the first page that needs such a language.
- **Text laid out as a picture,** such as a folder tree in a code block, is a code block, not a diagram.

### 3. Each fact has one home, and a diagram is never it

A page may rest on what holds the truth about the software, beyond decision records and pages. The rule that states this binds at `LDOC`'s next major (point 10).
- **The homes beyond the pages.** A fact's home may be something the page anchors that decides or states the fact:
  - an accepted decision record or an accepted rule
  - an analysis artefact in force, or a section of one
  - a captured source, for what the source it captures says
  - code
- **One home among them.** Where the page anchors more than one of them for a fact, the first in that list is the fact's home. So what decides a fact comes before what states it.
- **The anchor** may be on the whole home, or on the part of it that decides or states the fact (COR-050 point 2).
- **The page may state such a fact.** It needs no link to another page that states it, and no anchor on one, as DEC-001 point 3 says of a decision record.
- **A user page and the internal root.** A page of the user space may rest on a home under the internal root. It anchors that home, and links nothing under the internal root (DEC-001 point 1).
- **Never a home of this kind:** a page, which is a home only among the pages (DEC-001 point 3), and a diagram in any form, such as a fence, a diagram's source file or an image.
- **Every other fact** has its home among the pages, as DEC-001 point 3 says. A page is a fact's home only where it states the fact in prose.
- **A diagram shows only facts with a home elsewhere.** Each fact it shows has its home in what the page anchors, or in prose on a page. A fact that only a diagram states has no home, and breaks the rule.
- **A diagram anchors what it shows** through its page. The page anchors the home of each fact the diagram draws.
- **A wide diagram,** such as one of a system's parts, anchors the records that decide its parts and how they relate. An anchor on most of the repository would flag the page on every change (COR-050 point 7).

### 4. A produced image or recording is anchored at its source

An image a renderer writes, a screenshot or a recording is never anchored. The page anchors what produced it, and the homes of what it shows.
- **What produced it:** a diagram's source file, a capture script, or a recording's script or storyboard.
- **No exclusion from friction.** Such a file is no artefact (COR-050 point 1). So it flags nothing unless something anchors it.
- **An exclusion from the measures,** where the project's declared surface covers such files. Nothing anchors them, so they would count as uncovered surface. The project excludes them (COR-050 points 8 and 14).
- **A shell-session fence is not produced in this sense.** It is content of its page (point 6).

### 5. Images and screenshots

An image is an image file the page shows with `![alt](path)`.
- **A hand-made image,** a screenshot taken by hand included: the page anchors what the image shows, such as the code of the screen it pictures. It may also anchor the image file, so that replacing the image asks whether the text still agrees.
- **A screenshot from a script:** a capture script the project keeps takes it, marks and arrows included. The page anchors the script and what the screenshot shows, never the screenshot (point 4). The capture's window size, scale and theme are settings apart from the script, which the page does not anchor.
- **Answering a flag:** a page flagged through its capture script is answered after the capture runs again, and the new screenshot is part of the answer.
- **A recording,** an animated image included, follows the same rule. The page anchors the script or storyboard that produced it.
- **Where an image lies:**
  - beside the page that shows it, with produced images apart from hand-made ones
  - beside a page of the user space, when pages of both spaces show it, since a technical page may lead into user material and a user page never leads into technical material (DEC-001 point 1)
  - at its own address, when it is external, such as a badge

The capture tool is the project's, such as a browser driver for web pages or a terminal recorder for a command line.

### 6. Console output

A page shows a command and what it prints in a fence for a shell session, such as `console` for a POSIX shell. Each command follows the shell's prompt, such as `$ `, and its output follows it.
- **Produced by a run, never typed.** A runner runs each command and compares its output with the fence. How it matches output that varies from run to run, such as a time or a path, is the runner's.
- **A command that cannot run as a test,** such as one that needs the network or waits for input, goes in a fence of its shell's language, with no output. No runner reads it.
- **New output is a reviewed change.** A runner that writes new output into a fence changes the page, and a person reviews that change as any other (DEC-001 point 5).
- **Kept true:** the page anchors the code whose output it shows. A change to that code flags the page, and the runner shows whether the output moved.
- **The runner is not living-docs'.** Running the product is a test, which this capability never performs (DEC-001 point 6). A project runs its fences with a runner of its own, or one a capability provides.
- **The fixer of pages runs nothing.** A stale page whose output only a new run can tell is held with one question (DEC-001 point 5).
- **Where its results go:** a failing run fails as a test. Its results reach the reading-evidence point once a record says where kept results live (DEC-001 point 7).

### 7. Callouts

A callout is a block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`. It is the one form a callout takes in content.
- **Its look is presentation:** GitHub's own by default, the site's theme on a site.
- **Kept true** as prose is, through the page's anchors.
- **No check.** An unknown type reads as a plain block quote, which costs little.

### 8. A text alternative for each element that carries meaning

A diagram, an image or a recording that carries meaning has a text alternative. A decorative image has an empty one, so that a screen reader passes over it.
- **A Mermaid diagram's alternative** is its `accTitle` and its `accDescr`, inside the fence. They travel with the diagram into every renderer.
- **An image's alternative** is its alt text. A diagram in another language is shown as an image, and takes an image's alternative.
- **A recording** needs an alternative of its own, such as a transcript or its storyboard.
- **The checkable part:** each `mermaid` fence carries an `accTitle` and an `accDescr`, each followed by text that is not blank. The capability's validation fails a fence without them, where the rule binds (DEC-001 point 6).
- **Images are left to reader-review.** In Markdown, no check tells a decorative image from one that carries meaning, so none fails an image.

### 9. A documentation site meets three criteria

GitHub, with no site, stays the default. A project that publishes a site chooses a generator that meets three criteria:
- **It reads content as written:** the page's front matter, Mermaid fences and the standard callout syntax.
- **A theme reaches diagrams and callouts from one place,** in light and in dark.
- **One site serves one space.** It gathers the space's pages and the images they show, wherever they lie. The user space's site never includes the internal root (DEC-001 point 1). A technical page's link to a user page reaches the user space's site.

Which generator a project uses is its own choice.

### 10. The rules bind at LDOC's next major

`LDOC` gains two rules, proposed:
- **A successor of the rule on one home,** under a new id, stating point 3.
- **The rule on text alternatives,** stating point 8, with its checkable part.

Until a major accepts them, they bind nothing, and the rule on one home binds as it stands (COR-051 point 4). Accepting them is a reviewed change a person makes, which raises `LDOC`'s major and supersedes the rule on one home (COR-051 points 4 and 7). That change also rewrites what names the rule on one home: `LDOC`'s rule on grounding, and DEC-001 point 3's passage on a fact's home.

## Rationale

**Why content stays neutral.** A theme change that touches content flags every page that shows a diagram, though nothing the page says changed. Keeping styling out makes a theme a project setting, which changes no page. The cost is that a project cannot theme what GitHub draws.

**Why Mermaid in the page.**
- **It works on day one.** GitHub draws it with no build step, and it reads as text where nothing draws it.
- **Agents and reviewers handle text.** An agent writes it, and a reviewer reads its diff. Nobody can read a changed image.
- **Friction's cascade reaches through it.** The fence is content, so changing it flags whatever anchors that part of the page. A separate source would stop the cascade at the page (COR-050 point 6).

**Why a diagram is never a fact's home.** A home is where a change to the fact is made. An arrow does not say which relation it shows, and a layout can change with no fact changing. So a diagram cannot state a fact precisely enough to be that place.

**Why the homes widen for every statement.**
- **The truth lies there.** Facts about the software are decided in records and rules, stated in its analysis and its sources, and carried out in its code.
- **The same guarantee.** A change to any of them flags each page that anchors it, as a change to a decision record does.
- **One home whatever the form.** Homes for diagrams alone would give one fact two homes, on a page that states it and draws it too.
- **The order picks one.** What decides a fact is where a change to it is made, before what states or carries it out.

**Why this refines DEC-001 rather than overturning it.** DEC-001 left other homes "not taken yet", waiting for a page that needs them. This record takes them, and keeps every home DEC-001 gives.

**Why a produced image or recording is never anchored.** The anchor on what produced it already carries every change that matters. A render or a capture may write new bytes with nothing changed in what it shows. An anchor on it would then flag the page for nothing, and people would learn to answer blindly, which COR-050 point 7 warns of.

**Why console output lives in a fence that a runner checks.** The page shows what the reader types and sees, and the same fence is the test. Running it is testing the product, which DEC-001 keeps out of this capability.

**Why one callout syntax.** It reads as a block quote wherever nothing draws it, so it suits every adopter (COR-014). A dialect of one site generator would put that host's syntax into content.

**Why the check covers only Mermaid fences.** WCAG asks a text alternative of every image that carries meaning, and an empty one of a decorative image (success criterion 1.1.1). A check can see whether a fence names its title and description. A Markdown image always has an alt text, empty where it is decorative, and no check can tell which an image should be.

**Why criteria, not a generator.** One toolchain does not suit every adopter (COR-014). The criteria keep content as written and the spaces apart, which any generator can be held to.

**Why the rules wait for a major.** A new accepted rule, and a superseded one, each need a new major of `LDOC`. Each major makes every project's pin fall behind until it reviews the set (COR-051 point 7). Landing both rules proposed lets a reviewer preview them, and lets them share one major with whatever `LDOC` accepts next.

### Alternatives considered

- **No default diagram language, each space's definition naming its own.** Rejected. A project would have nothing that works on day one.
- **Mermaid also rendered to a committed image for every diagram.** Rejected. It commits an image per diagram, and puts every diagram behind a renderer.
- **Styling directives in each fence,** so that GitHub shows the project's theme. Rejected. It puts styling into content, and a theme change would flag every page with a diagram.
- **A rule against styling in content,** with a check of Mermaid's directives. Not taken yet. The authoring skill and review carry point 1, and a rule comes if styling slips past them (COR-007).
- **Today's homes kept, each fact a diagram shows also stated in prose.** Rejected. It costs a sentence for each arrow a diagram draws, and leaves a fact's home away from where it is decided or stated.
- **The wider homes for diagrams only.** Rejected. One fact would have two homes on a page that states it in prose and draws it.
- **Anchored artefacts as grounds that need no home, with a home kept to a record or a page.** Not taken. A home is where a change to a fact is made, and for a fact the analysis or the code holds, that place is the analysis or the code.
- **Anchoring a produced image or recording.** Rejected. See Rationale.
- **A runner of shell-session fences shipped by this capability.** Rejected. Running the product is testing, which DEC-001 keeps out of this capability. A capability of executed documentation checks may come once a second project wants one (COR-007).
- **A runner as a plugin of a terminal-recording capability.** Not taken. Its input is a scripted storyboard, which a page is not.
- **Each space's definition naming its callout dialect.** Rejected. It puts one host's syntax into content.
- **A check that each callout's type is one of the five.** Not taken. It guards a cosmetic failure (COR-007).
- **The rule on text alternatives as guidance only.** Rejected. The gap grows with every diagram.
- **A check that fails an HTML image with no `alt` attribute.** Not taken yet. It comes with the first page that shows images in HTML (COR-007).
- **One rule on text alternatives in a method set of the backbone,** inherited by every component's set. Not taken. It needs a core record and the backbone's first method set, for one rule (COR-007).
- **A ready configuration for one site generator.** Rejected. It binds every adopter to one toolchain (COR-014).
- **Accepting the new rules now, in a major of their own.** Rejected. Each major is a review for every adopter, and staging lets these rules share one with whatever `LDOC` accepts next.

## Implications

- **`LDOC`** holds the two proposed rules of point 10, and declares the checkable part of point 8 for the capability's validator. The rule set's version is unchanged until its next major.
- **The validator** fails a `mermaid` fence that lacks an `accTitle` or an `accDescr`, on each page where the rule on text alternatives binds. While that rule is proposed, it binds on no page, and the validator's summary says so.
- **DEC-001** points 1, 3, 6 and 7 name what this record adds to them.
- **The authoring skill** gives writers the forms of points 1, 2 and 5 to 9, and worked examples of a site.
- **Projects** keep their capture scripts and console runners, and choose a site generator if they want one. A project that adopts the rules at `LDOC`'s next major reviews its pages' diagrams for their text alternatives.
