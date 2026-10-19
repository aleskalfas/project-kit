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
- **Only a Markdown file is a document,** so an image is never a page (DEC-001 point 4).
- **The capability never runs the product.** Executed checks belong to another component, and their results arrive as reading evidence (DEC-001 points 6 and 7).

The maintainer set three constraints on 18 October, on [project-kit#1770](https://github.com/aleskalfas/project-kit/issues/1770):
- **The direction:** pages support at least images and diagrams, and other media where needed. Rendering is configurable, and screenshots, console output and callouts are wanted.
- **A diagram is a view of truth held elsewhere:** in decisions, requirements, use cases or code. It states nothing that has no other home, and it anchors what it shows.
- **Content and presentation stay apart:** content is neutral and true, and carries no styling. Presentation is a layer each project configures, and a sensible default needs no setup and reads right on GitHub.

A design note weighed the options against established practice: docs-as-code, diagram-as-code tools, documentation sites and WCAG's text alternatives. The maintainer took its recommendations on 19 October, on the same issue. This record holds living-docs' share of them. A diagram inside another component's artefact is that component's to decide.

## Decision

**A page shows a diagram, an image, console output or a callout as neutral content, and each project's presentation layer decides how it looks. A diagram is Mermaid text in the page by default, and never a fact's home. What a page shows is anchored at its source and its home, never at a file a tool produced.**

### 1. Content and presentation stay apart

What a page holds is content: true, neutral, and the same wherever it is read. How it looks is presentation, which each project configures.
- **Content:** a diagram's Mermaid text, an image file and its alt text, a capture script and what it writes, a `console` fence, and a callout in the standard syntax.
- **Presentation:** colours, fonts, light and dark, how a diagram or a callout is drawn, how a screenshot is framed, and a documentation site.
- **No styling in content.** A Mermaid fence holds no `%%{init}%%` directive, no `classDef` and no `style` line. A change of theme is then never a change of content.
- **A theme reaches a visual element only through presentation:**
  - on GitHub, through GitHub's own look, which needs no setup
  - on a documentation site, through the site's settings
  - in an image a renderer writes, through the renderer's settings
  - in a screenshot, through the capture script's settings

One theme file that the site and the renderer both read waits for a project that runs both (COR-007).

### 2. A diagram is a Mermaid fence by default

A diagram is written as Mermaid text in a fenced block of the page, whose info string is `mermaid`. It carries no styling (point 1).
- **Drawn with no setup.** GitHub draws the fence, and a site draws it in the project's theme. Where nothing draws it, it reads as text.
- **Its syntax is not validated.** A check whose answer depends on whether a Mermaid parser is installed gives different answers in different places (COR-050 point 2). A project may run such a check in its own continuous integration.
- **Another diagram language** is used only where the project renders it to an image. How the methodology configures a renderer, and checks that an image is fresh, is decided with the first page that needs such a language.

### 3. Each fact has one home, and a diagram is never it

A diagram states only what has a home elsewhere. The homes are widened for every statement, prose or diagram, so that a page may rest on what holds the truth. The rule that states this binds at `LDOC`'s next major (point 10).
- **What may be a fact's home.** Anything the page anchors that states or decides the fact: a record, a rule, an analysis artefact or a section of one, a captured source, or code. The anchor may name the whole, or the part the fact stands on (COR-050 point 2).
- **The page may state such a fact.** It needs no link to another page that states it, and no anchor on one, as DEC-001 point 3 says of a decision record.
- **A user page and the internal root.** A page of the user space anchors a home that lies under the internal root, and links nothing there. User navigation never leads into technical material (DEC-001 point 1).
- **Every other fact** has its home among the pages, as DEC-001 point 3 says.
- **A diagram is never a fact's home.** Each fact a diagram shows has its home in what the page anchors, or in prose on a page. A fact that only a diagram states has no home, and breaks the rule.
- **A diagram anchors what it shows** through its page. The page anchors the home of each fact the diagram draws.
- **A wide diagram,** such as one of a system's parts, anchors the records that decide its parts, or one entry file for each part. An anchor on most of the repository would flag the page on every change (COR-050 point 7).

### 4. A produced file is anchored at its source

A file a tool produces is never anchored. The page anchors what the tool produced it from, and the homes of what it shows.
- **What a produced file is:** an image a renderer writes from a diagram's source, a screenshot a capture script takes, or a recording.
- **No exclusion from friction.** Only a Markdown file is an artefact (DEC-001 point 4). So a produced image flags nothing unless something anchors it.
- **An exclusion from the measures,** where the project's declared surface covers produced files. Nothing anchors them, so they would count as uncovered surface. The project excludes them (COR-050 points 8 and 14).
- **A `console` fence is no produced file.** It is content of its page (point 6).

### 5. Images and screenshots

An image is an image file the page shows with `![alt](path)`.
- **A hand-made image:** the page anchors what the image shows, such as the code of the screen it pictures. It may also anchor the image file, so that replacing the image asks whether the text still agrees.
- **A screenshot:** a capture script the project keeps writes it, marks and arrows included. The page anchors the script and what the screenshot shows, never the screenshot (point 4). A screenshot marked by hand counts as hand-made.
- **A recording** follows the same rule. The page anchors the script or storyboard that produced it.
- **Where an image lies:**
  - beside the page that shows it, in that page's space, with produced images apart from hand-made ones
  - in the user space, when pages of both spaces show it, since a technical page may lead into user material and a user page never leads into technical material (DEC-001 point 1)
  - at its own address, when it is external, such as a badge

The capture tool is the project's, such as a browser driver for web pages or a terminal recorder for a command line.

### 6. Console output

A page shows a command and what it prints in a `console` fence. Each command opens with `$ `, and its output follows it.
- **Produced by a run, never typed.** A runner runs each command and compares its output with the fence, and can write the new output into it. Output that varies from run to run, such as a time or a path, is written as a placeholder the runner matches, such as `<path>`.
- **Kept true:** the page anchors the code whose output it shows. A change to that code flags the page, and the runner shows whether the output moved.
- **The runner is not living-docs'.** Running the product is a test, which this capability never performs (DEC-001 point 6). A project runs its fences with a runner of its own, or one a capability provides.
- **Where its results go:** a failing run fails as a test. Its results reach the reading-evidence point once a record says where kept results live (DEC-001 point 7).

### 7. Callouts

A callout is a block quote whose first line is `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`. It is the one form a callout takes in content.
- **Its look is presentation:** GitHub's own by default, the site's theme on a site.
- **Kept true** as prose is, through the page's anchors.
- **No check.** An unknown type reads as a plain block quote, which costs little.

### 8. A text alternative for each element that carries meaning

A diagram, an image or a recording that carries meaning has a text alternative. A decorative image has an empty one, so that a screen reader passes over it.
- **A diagram's alternative** is its `accTitle` and its `accDescr`, inside the fence. They travel with the diagram into every renderer.
- **An image's alternative** is its alt text. A recording needs one of its own, such as a transcript or its storyboard.
- **The checkable part:** each `mermaid` fence carries an `accTitle` and an `accDescr`. The capability's validation enforces it where the rule binds (DEC-001 point 6).
- **Images are left to reader-review.** No check tells a decorative image from one that carries meaning, so none fails an image.

### 9. A documentation site meets three criteria

GitHub, with no site, stays the default. A project that publishes a site chooses a generator that meets three criteria:
- **It reads content as written:** the page's front matter, Mermaid fences and the standard callout syntax.
- **A theme reaches diagrams and callouts from one place,** in light and in dark.
- **One site serves one space.** It gathers the space's pages and the images they show, wherever they lie, and never includes the internal root in the user space's site (DEC-001 point 1).

Which generator a project uses is its own choice.

### 10. The rules bind at LDOC's next major

`LDOC` gains two rules, proposed:
- **A successor of the rule on one home,** under a new id, stating point 3.
- **The rule on text alternatives,** stating point 8, with its checkable part.

`LDOC`'s next major accepts both, and supersedes the rule on one home. Until then they bind nothing, and the rule on one home binds as it stands (COR-051 point 4).

## Rationale

**Why content stays neutral.** A theme change that touches content flags every page that shows a diagram, though nothing the page says changed. Keeping styling out makes a theme a project setting, which changes no page. The cost is that a project cannot theme what GitHub draws.

**Why Mermaid in the page.**
- **It works on day one.** GitHub draws it with no build step, and it reads as text where nothing draws it.
- **Agents and reviewers handle text.** An agent writes it, and a reviewer reads its diff. Nobody can read a changed image.
- **Friction's cascade reaches through it.** The fence is content, so changing it flags whatever anchors that part of the page. A separate source would stop the cascade at the page (COR-050 point 6).

**Why a diagram is never a fact's home.** A diagram shows relations at a glance, and states none of them in words a check or a reviewer can hold one by one. A fact only a diagram states could drift with no text to compare. With its home elsewhere, a change to the home flags the page through its anchor.

**Why the homes widen for every statement.** The maintainer placed a diagram's truth in decisions, requirements, use cases or code. A decision record a page anchors is already a home, since a change to it flags every page that anchors it. A requirement, a rule, a captured source or code flags the page the same way. So each gives the same guarantee, for prose as for a diagram. Homes for diagrams alone would give one fact two homes, on a page that states it and draws it too.

**Why a produced file is never anchored.** Each render or capture rewrites the file's bytes. An anchor on it would flag the page for nothing, and people would learn to answer blindly, which COR-050 point 7 warns of. The source changes only when what it produces should change.

**Why console output lives in a fence that a runner checks.** The page shows what the reader types and sees, and the same fence is the test. Running it is testing the product, which DEC-001 keeps out of this capability.

**Why one callout syntax.** It reads as a block quote wherever nothing draws it, so it suits every adopter (COR-014). A dialect of one site generator would put that host's syntax into content.

**Why the check covers only Mermaid fences.** WCAG asks a text alternative of every image that carries meaning, and an empty one of a decorative image (success criterion 1.1.1). A check can see whether a fence names its title and description. It cannot tell a decorative image from one that carries meaning, so a check on images would fail correct pages.

**Why criteria, not a generator.** One toolchain does not suit every adopter (COR-014). The criteria keep content as written and the spaces apart, which any generator can be held to.

**Why the rules wait for a major.** A new accepted rule, and a superseded one, each need a new major of `LDOC`. Each major makes every project's pin fall behind until it reviews the set (COR-051 point 7). Landing both rules proposed lets a reviewer preview them, and one major later costs each adopter one review.

### Alternatives considered

- **No default diagram language, each space's definition naming its own.** Rejected. A project would have nothing that works on day one.
- **Mermaid also rendered to a committed image for every diagram.** Rejected. It commits an image per diagram, and puts every diagram behind a renderer.
- **Styling directives in each fence,** so that GitHub shows the project's theme. Rejected. It puts styling into content, and a theme change would flag every page with a diagram.
- **Today's homes kept, each fact a diagram shows also stated in prose.** Rejected. It costs a sentence for each arrow a diagram draws, and leaves the truth the maintainer named outside the homes.
- **The wider homes for diagrams only.** Rejected. One fact would have two homes on a page that states it in prose and draws it.
- **Anchoring a produced file.** Rejected. See Rationale.
- **A runner of `console` fences shipped by this capability.** Rejected. Running the product is testing, which DEC-001 keeps out of this capability. A capability of executed documentation checks may come once a second project wants one (COR-007).
- **A runner as a plugin of a terminal-recording capability.** Not taken. Its input is a scripted storyboard, which a page is not.
- **Each space's definition naming its callout dialect.** Rejected. It puts one host's syntax into content.
- **A check that each callout's type is one of the five.** Not taken. It guards a cosmetic failure (COR-007).
- **The rule on text alternatives as guidance only.** Rejected. The gap grows with every diagram.
- **One rule on text alternatives in a method set of the backbone,** inherited by every component's set. Not taken. It needs a core record and the backbone's first method set, for one rule (COR-007).
- **A ready configuration for one site generator.** Rejected. It binds every adopter to one toolchain (COR-014).
- **Accepting the new rules now, in a major of their own.** Rejected. It costs adopters a major for these rules and another for the next.

## Implications

- **`LDOC`** holds the two proposed rules of point 10, and declares the checkable part of point 8 for the capability's validator. The rule set's version is unchanged until its next major.
- **The validator** reports a `mermaid` fence that lacks an `accTitle` or an `accDescr`, on each page where the rule on text alternatives binds. While that rule is proposed, it binds on no page, and the validator's summary says so.
- **DEC-001** points 1, 3, 6 and 7 name what this record adds to them.
- **The authoring skill** gives writers the forms of points 2 and 5 to 9, and worked examples of a site.
- **Projects** keep their capture scripts and console runners, and choose a site generator if they want one. A project that adopts the rules at `LDOC`'s next major reviews its pages' diagrams for their text alternatives.
