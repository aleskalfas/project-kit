---
id: PRJ-012
title: project-kit's own deck shows how it uses visual-communication, its notation stays its own, and the capability's cost is measured on its pieces
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** project-kit presents itself with a deck it draws with the visual-communication capability, as any project draws. The deck lives on the default branch, with no prototype or planning note beside it. It shows a reader how a project uses the capability, and grows a Feature at a time until it holds the whole talk.

The deck's items take their colour from a notation of project-kit's own concepts, which project-kit keeps and never ships. project-kit also takes the two measures of cost that the capability's founding record asks for, on its own pieces. It posts each result on the EPIC that builds the capability.

## Context

**The talk.** project-kit gave a talk about itself on 30 October, in English and in Czech. Its 24 slides were drawn on a whiteboard service by a generator script ([visual-communication:DEC-001-visual-communication-discipline], Context). Planning the visual-communication capability started from that talk (#2423). The planning note, a working prototype, the generator and the talk's text lie on a branch of their own, `docs/talk-notes`, which never merges.

**The capability, installed here.** project-kit ships the capability and registers it in its own manifest, so it draws pieces as any project does. A project's pieces, libraries and notations are its own files, never the capability's ([visual-communication:DEC-001-visual-communication-discipline] point 11).

**What the maintainer asked.** The EPIC that builds the capability ends with project-kit's own deck on the default branch, as the showcase of how project-kit uses the capability (#2423). The maintainer wants no prototype or scratchpad there at the end, but "the clean functionality with the presentation deck as showcase". A part that describes project-kit's capabilities is to follow.

**What no record says yet.** The founding record asks whoever maintains the capability to measure what a one-off costs ([visual-communication:DEC-001-visual-communication-discipline], Implications). No record says what the deck is for, whose notation colours it, or where those measures are taken and reported. This record does (#2502).

## Decision

**project-kit's presentation of itself is a deck, drawn with the visual-communication capability as any project draws, and kept on the default branch as the showcase of how project-kit uses it. Its items take their colour from a notation of project-kit's own concepts, which project-kit does not ship. project-kit takes the capability's two measures of cost on its own pieces, and posts each result on EPIC #2423.**

### 1. The showcase is project-kit's own deck, on the default branch

- **What it is:** a piece, a deck, that holds project-kit's presentation of itself. It is project-kit's work, in project-kit's location for visual work, never in the capability's folder ([visual-communication:DEC-001-visual-communication-discipline] point 11).
- **What it shows:** how a project uses the capability, from a piece that works. A reader finds its content, the libraries it names and its notation, and draws its pages with the capability's commands.
- **It grows a Feature at a time.** A page joins once the capability draws it from the deck's content, its libraries and its local components. No picture of an old slide stands in for a page not yet drawn. The deck holds the talk once its last page joins. A part added later, such as one that describes project-kit's capabilities, joins it the same way.
- **No prototype and no planning note beside it.** They stay on their branch. The capability's records replace the note, and the capability's code replaces the prototype.
- **No fixture, and no example the capability ships.** The capability's tests keep fixtures of their own, and no release of the methodology carries the deck.

### 2. project-kit's pieces use only what every project gets

- **The same commands and files.** The deck, and every other piece project-kit draws, is drawn, checked and exported by the capability's commands, from files in its format. A shipped library reaches them as it reaches any project, through the capability's command ([visual-communication:DEC-003-change-over-time] point 5).
- **Nothing made for them alone.** The capability holds no code, option or file made for project-kit's pieces alone. Their needs are met as any project's are. A need that recurs gets a general tool or a library component. A need of one piece gets a local component or a helper ([visual-communication:DEC-001-visual-communication-discipline] points 4 and 8).

### 3. project-kit's own libraries, its notation first, are never shipped

- **Its notation:** project-kit owns a notation of the concepts its pieces tell apart by meaning, such as project-kit's own files and a project's. Each concept maps to a colour family, and perhaps to an icon or a shape ([visual-communication:DEC-004-brands-and-notations] point 10).
- **Kept, not shipped.** The notation lies in project-kit's library folder. No release of the methodology carries it, and no project receives it. The same holds for any other library project-kit writes for its pieces, such as a brand of its own.

### 4. The two measures are taken on project-kit's pieces

project-kit maintains the capability, so it takes the founding record's two measures on its own pieces ([visual-communication:DEC-001-visual-communication-discipline], Implications). The first is what content costs per page once its components exist, against the code that drew the same page. The second is the tries an agent needs to write a one-off of a kind it has not seen. The tries run until the one-off renders right in every language and set of fonts.
- **When:** each Feature that brings pages of the talk into project-kit's pieces takes the first measure on those pages. Each Feature that writes a one-off of a kind none of project-kit's pieces had before takes the second.
- **Against what:** the generator's function that drew the same page, with the helpers it calls. A page the generator never drew, such as one of the part on capabilities, has no baseline, so only the second measure applies to it.
- **How lines are counted:** as the prototype's comparison counted them, which the founding record's Rationale quotes. Blank lines, comments, docstrings and a component's descriptions are left out. A page's cost is given twice: its content alone, and its content with the components it uses, its local components and helpers included. A component that several measured pages share counts once.
- **Named commits:** each result names the commits it counted, of the pieces and of the generator, so any result can be counted again.

### 5. Each result is posted on EPIC #2423

- **One comment for each result,** on EPIC #2423, the EPIC that builds the capability. Whoever plans the capability's Features reads it there, beside the work that took the measure.
- **If the EPIC closes first:** where measures are still taken after #2423 closes, its last result links the issue where the series goes on.
- **Not kept in the repository.** A result is a measure at one commit, so no page or data file keeps the results. A record that rests on a result cites it as its evidence.
- **A result over the line is an issue too.** The founding record revisits the rule that components are data in either of two cases. Content stops costing less than the code, or an agent needs more than a few tries. A result that shows either says so, and an issue is filed for the revisit and linked from the comment.

## Rationale

**Why the deck is the showcase.** A piece that works shows what the capability does, and project-kit's own check reads it as it reads any piece. A description shows less. A prototype is a second implementation of the capability, which drifts from the first. A planning note is exploration that its records have replaced.

**Why only what every project gets.** A showcase that leans on something made for project-kit shows a project what it will not get. Code made for the deck inside the capability would also count in neither measure, where a helper counts as its page's cost. The old talk needed scripts of its own, to cut a board's export into pages and to draw each terminal as a picture. A showcase that hid such scripts inside the capability would report a lower cost than a project pays.

**Why a page joins only once it is drawn.** A picture of an old slide shows nothing of the capability, and holds no content to measure. Brought in a Feature at a time, every page on the default branch is drawn by the capability. Each Feature's measure then covers what it brought.

**Why project-kit's own notation.** Colour says what a thing is ([visual-communication:DEC-001-visual-communication-discipline] point 6). The talk coloured each item by a concept of project-kit's, such as a layer of its pyramid. A notation shipped with the capability would carry one project's subject into every project ([COR-014](../core/COR-014-universal-applicability.md)). The founding record leaves a project's notations to the project ([visual-communication:DEC-001-visual-communication-discipline] point 9).

**Why the measures are taken here, and counted one way.** project-kit holds the code that drew the talk's pages, so it has a baseline for the first measure. Its pieces are also where the capability's maintainers and their agents write one-offs, which the second measure counts. The count decides whether a rule of the capability is revisited, so it is fixed here rather than left to each result. It continues the comparison the founding record rests on, so the first result on the default branch reads beside it.

**Why on the EPIC, and not in the repository.** The measures decide a rule of the capability, and whoever plans its Features reads the EPIC that holds them. A comment is dated, and stays beside the work that took it. A result kept in the repository would be true at one commit, among files that must stay true. A page about it would go stale with the deck's next change.

### Alternatives considered

- **The prototype, or a scratchpad note, as the showcase.** Rejected. A prototype is a second implementation that drifts, and a planning note is replaced by the records it led to.
- **The deck as a fixture of the capability's tests, or as an example the capability ships.** Rejected. A fixture ties the talk's text to the tests, so a reworded slide changes a test. A shipped example carries project-kit's subject into every project.
- **The whole talk at once, with pictures for the pages not yet drawn.** Rejected. A picture shows nothing of the capability, and has no content to measure.
- **Colour by place, with no notation.** Rejected. One concept would look different on two pages, where the talk coloured each item by what it stood for.
- **project-kit's notation shipped with the capability.** Rejected, for the reasons above.
- **Each result on the EPIC of the Feature that took it.** Rejected. A piece of project-kit's drawn under another EPIC would post where the capability's planners do not read, and the series would have no known start.
- **The results in a committed page or data file.** Rejected. A result is true at one commit, and a page about it would go stale with the deck's next change.

## Implications

- **The deck's state.** While the libraries it locks are unreleased, the deck can only be a draft ([visual-communication:DEC-003-change-over-time] point 8). So its pages are drawn by a render, and no drawing of them is committed ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 7). Whether it later becomes a published piece, whose current copy is committed, is left to a later change.
- **A shipped library changes the deck only when copied in again.** The deck draws with the copies in project-kit's library folder, as any project's piece does. A change made to a shipped library in the capability's folder reaches it only through the capability's command (point 2).
- **The branch that keeps the generator** stays until the last page the generator drew has joined the deck and been measured. Deleting it sooner takes the baseline away.
- **Facts that have a home elsewhere stay there.** The location is in the capability's configuration, each piece's languages and brand in its `piece.yaml`, and its library versions in its lock. A brand project-kit writes for its pieces commits only fonts whose licence lets a public repository hold them ([visual-communication:DEC-004-brands-and-notations] point 9).
- **No page points at the deck yet.** A page that shows readers where it is waits for a later change.
