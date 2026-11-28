---
id: DEC-080
title: A page's first screen shows one of its three, and a page one screen holds is judged whole
status: proposed
date: 2026-11-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a web page is read on a screen, and a reader sees only part of a tall one at once. This record gives such a page a *screen* at each size it is drawn at: as wide as the page, and as tall as a share of that width fixed for the size, landscape at a desktop and a projector, upright at a tablet and a phone. The *first screen* is that screen at the page's top, where every reader starts. Where the page is taller than its screen, the reader scrolls, and `RS-GRAPHIC-001` asks, beside what it asks of the page whole, that the first screen show at least one of the page's head, its focal point and the action it asks. Where one screen holds the page whole, the reader sees it at once, so a page of sections is judged whole there, as a poster is, and its sections may not compete for one eye. `RS-GRAPHIC-007` weighs a page of sections the same way, and weighs no screen apart. The viewing step draws each such page's first screen, and the reviewer reads it.

## Context

[visual-communication:DEC-068-focal-point-in-the-content] point 3 has `RS-GRAPHIC-001` judge a page a reader scrolls through, such as a site's page, as drawn, never by what its first screen shows. It judges such a page of sections section by section, whatever its height. Both rest on one gap: the viewing step cuts a tall page into bands by the size of an image a harness reads whole, never by a screen, so the capability draws no unit of what a reader sees at once ([visual-communication:DEC-022-web-site-and-parts] point 7). DEC-068 names the two holes this leaves, each accepted knowingly until such a unit is drawn:
- **The first screen.** A page whose first screen shows none of its head, its focal point and its action passes, where they lie lower and stand above the rest of the page, or of its section.
- **A short page of sections.** A page of sections a reader scrolls through, short enough to be seen at once, is judged section by section, so two sections' focal points may compete for one eye unseen.

DEC-068's Alternatives leave two choices to revisit once the step draws a reader's screen at each size: each part judged on the first screen, and a page of sections told by its height against its screen. DEC-022 leaves open a page shorter than a screen, and where a screen's first view ends. The review of [project-kit#3396](https://github.com/aleskalfas/project-kit/issues/3396) found the holes, and [project-kit#3413](https://github.com/aleskalfas/project-kit/issues/3413) is the follow-up.

The words it uses:
- **The three** are a page's head, its focal point and the action it asks of its reader, as `RS-GRAPHIC-001` names them (DEC-068 point 1). On a page with no head they are two.
- **A size** is a mode of the size axis `device` that a piece is drawn at ([visual-communication:DEC-021-size-and-shape] point 1).
- **A band** is a strip of a page's height that the viewing step draws as one image, at the page's whole width (DEC-022, Context).
- **A page of sections** is a page whose content gives its sections as a list, met one after another (DEC-068 point 3).
- A page's **screen** and its **first screen** are what point 1 says.

## Decision

**A page as tall as its content that a browser shows at its own width has a screen at each size, as wide as the page and as tall as a share of that width the rule fixes for the size. Where the page is taller than its screen, a reader scrolls through it, and its first screen shows at least one of the three. Where its screen holds it whole, a reader sees it at once, and a page of sections is judged whole there. The viewing step draws each such page's first screen, and the reviewer reads it.**

### 1. A page's screen is as wide as the page, and as tall as a share of its width fixed for each size

- **Which pages have one.** A page as tall as its content that a browser shows at its own width: a page of a top that asks for no height, such as a site's, which DEC-022 point 3 makes as wide as its size and as tall as its lowest part. A page seen at once by its kind, such as a slide, a poster or a figure, has none (DEC-068 point 3).
- **Its width** is the page's, at the size drawn. The brand's width at a size is the one statement the files make of the window a page is shown in ([visual-communication:DEC-055-smallest-text-size], Rationale, "Why the brand's width stands for the width a page is shown in").
- **Its height** is a share of that width, one for each size: nine sixteenths at `desktop` and at `projector`, five quarters at `tablet`, and sixteen ninths at `phone`. A page drawn at no size takes `desktop`'s, the axis's default (DEC-021 point 3). A mode the foundations add takes its share in the change that adds it.
- **Its first screen** is its screen at the page's top.
- **Scrolled, or seen at once.** At a size where the page is taller than its screen, a reader scrolls through it. At a size where its screen holds it whole, a reader sees it at once. The line is the screen's height, with no margin.
- **The shares are the rule's words.** `RS-GRAPHIC-001` gives them, so that what the rule judges stays within its set and its pin, as the page's frame does in `RS-GRAPHIC-003` (DEC-068 point 4). The viewing step holds the same shares, and a change to one changes the other in the same change.

### 2. The first screen shows at least one of the three

- **The test.** At a size where a reader scrolls through a page, its first screen shows at least one of the three: of the page, or, on a page of sections, of a section that lies in that screen. It shows it whole, or so far that a reader takes it for what it is.
- **Beside the page whole.** `RS-GRAPHIC-001` still judges the page whole, or each of its sections, as DEC-068 decides. The first screen adds a test of its own: that a reader meets one of the three where every reader starts.
- **Which of the three is the design's,** as the order among them is (DEC-068 point 1). A page may open on its head, on the picture that bears its point out, or on its call to act.
- **The page's frame,** as `RS-GRAPHIC-003` defines it, counts as it does on the page whole: a part of it shows one of the three only where it holds one.
- **The first screen alone.** No screen below it is judged.
- **`RS-GRAPHIC-007` weighs no screen apart.** It weighs the strongest difference across the page, or within each section where `RS-GRAPHIC-001` judges the page by its sections (point 3). Whether a reader meets one of the three on the first screen is `RS-GRAPHIC-001`'s alone.

### 3. A page its screen holds whole is seen at once, and judged whole

- **Judged whole.** At a size where a page's screen holds it whole, `RS-GRAPHIC-001` judges it whole there, sections and all, with one focal point, as it judges a page seen at once by its kind (DEC-068 point 3). At a size where the page is taller than its screen, it judges a page of sections section by section, as DEC-068 point 3 decides.
- **Each size apart.** So one page may be judged whole at `desktop` and by its sections at `phone`.
- **`RS-GRAPHIC-007` reads it alike.** It weighs the strongest difference across the page where `RS-GRAPHIC-001` judges it whole, and within each section where that rule judges it by its sections, so the two rules never read one page's sections apart (DEC-068 point 5).

### 4. The viewing step draws each such page's first screen, and the reviewer reads it

- **Which pages.** Each page that has a screen (point 1), at each key drawn, through either renderer.
- **What it draws.** Where the page is taller than its screen at the key's size, an image of its first screen: the strip from the page's top, as wide as the page and as tall as its screen. It is drawn at the scale of the page's own images, so its smallest text reads as theirs does, and under no forced palette. Beside it lie the frames of each element it shows, in part or whole, as beside a band (DEC-022 point 7), and it takes its page's findings, as a band does ([visual-communication:DEC-062-checks-beside-the-frames] point 1).
- **Its foot is no edge of the page.** A part the first screen cuts there shows whole in the page's bands, and is no fault.
- **A page its screen holds whole** takes no image apart: the page's own image shows its first screen.
- **The report** gives each such page, at each key, its screen's height, in the page's px, and says whether its screen holds it whole.
- **The reviewer** reads each first screen beside the page's bands, and judges point 2's test on it. It reads from the report whether a page's screen holds it whole, and judges a page of sections whole or by its sections by that, as point 3 says. Its report names each first screen it read, and each it did not.

## Rationale

**Why judge the first screen.** Readers spend most of their time on a page's first screen, and less on each screen below it, as the Nielsen Norman Group's eye-tracking studies found (Jakob Nielsen, "Scrolling and Attention", 2010; Kara Pernice, "Scrolling and Attention", 2018). What that screen shows tells a reader whether to scroll on (Amy Schade, "The Fold Manifesto: Why the Page Fold Still Matters", 2015). A page whose first screen shows none of the three gives its reader nothing of its point where most reading happens, and no reason to look for it lower.

**Why one of the three, and any one.** DEC-068 point 1 leaves their order to the design: a reader may enter through a dominant picture, and a page may draw its call to act loudest. So the first screen asks for one of them, and leaves which to the design. Asked for all three, a phone's page whose head and picture fill its first screen would fail for an action just below it.

**Why a page its screen holds whole is judged whole.** Its reader takes in its sections together, so they compete for one eye, as on any page seen at once (DEC-068 point 3). DEC-068 told such a page by its kind alone only because no unit of a screen was drawn.

**Why the first screen alone.** Every reader starts at the page's top, so its first screen is the same for each. A later screen falls where a reader stops scrolling, so no two runs would cut it alike.

**Why the page's width, and a share of it.** The brand's width at a size is the files' one statement of a window's width (DEC-055). No file states a window's height, and a share of the width scales with whatever width the brand gives. The shares are the shape of the window a browser leaves on the commonest screen of each kind, rounded to a plain proportion. A laptop's or a monitor's screen, less the browser's bars, comes near nine sixteenths. A tablet held upright, less its bars, comes near five quarters. A phone's tall screen held upright, less the browser's bars and the system's, comes near sixteen ninths. A room's screen shows a window whole, as it shows a slide, at nine sixteenths. A reader's own window may differ, but each size has one number, so two runs judge alike, which DEC-068's Alternatives found missing.

**Why the shares are the rule's words.** A share decides what the rule passes. Held by the viewing step alone, it would move with the capability's code, outside the set's pin, as DEC-068 rejects for the page's frame ("The frame defined in this record").

**Why `RS-GRAPHIC-007` weighs no screen apart.** It already weighs where the strongest difference goes across the page, or within each section. The first screen asks only whether a reader meets one of the three there, which is a question of rank, `RS-GRAPHIC-001`'s.

**Why an image of the first screen.** The reviewer judges what a reader sees at once, as the squint test asks of a page (DEC-028 point 8). A line across the bands would have it piece that screen together from strips cut by another measure.

### Alternatives considered

- **All three on the first screen.** Rejected, for the reason above.
- **The head on the first screen.** Rejected: a page that opens on the picture that bears its point out, with its head below, is drawn so on purpose, and DEC-068 point 1 leaves the order to the design.
- **The first screen judged whole, as a page seen at once.** Rejected: a page of sections whose first screen shows its hero and, at its foot, the next section's head drawn as large would fail, though a page's head need not stand above another section's (DEC-068 point 3).
- **Every screen judged, cut down the page at the screen's height.** Rejected: a reader's later screens fall where they stop scrolling, so the cuts would be the step's, not a reader's.
- **The screen's height as a brand's role.** Rejected. A shared role the foundations add after their first version takes a default that aliases an older role ([visual-communication:DEC-004-brands-and-notations] point 7), and no older role gives a height near a screen's at each size. And a brand that gave a tall screen would pass every first screen.
- **The screen declared by the top, as its smallest text is (DEC-055).** Rejected. A screen's shape follows the device a size names, not the kind of page, and a project's own top could declare one that holds every page.
- **The screen named by the piece.** Rejected: a size would have two owners (DEC-021 point 1).
- **The shares left to the viewing step.** Rejected, for the reason above.
- **A margin at the screen's height,** so that a page a little taller is still seen at once. Rejected: its reader does scroll, and the margin would be a second number with no source.

### What it costs

- **A share is not a reader's window.** A page judged on its first screen may show a reader with a shorter window less, and one with a taller window more.
- **One more image** of each page a reader scrolls through, at each key drawn, for the reviewer to read.
- **A new major of `GRAPHIC`,** which each project that inherits it reads, and moves its pin to (Implications).

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it (COR-066 point 5). Accepting this record accepts them.
  - **DEC-068's top line** comes to read: "**Partially superseded by [visual-communication:DEC-070-ship-call-and-one-round] and [visual-communication:DEC-080-readers-first-screen].** Overturned by DEC-070:", followed by its present text from "what this record decides or says that rests on the review's grades" through the sentence that ends "cites each ([visual-communication:DEC-030-design-agents] point 6).", then: "Overturned by DEC-080: in point 3, the bullet "A page a reader scrolls through" whole, the sentence of "Its sections, each a page" that begins "The clause turns on how the page is read", and "Two holes" whole; the Alternatives "Each part judged on the first screen" and "A page of sections a reader scrolls through told by its height against its screen", so far as each is not taken; and, Left open, "A unit of a reader's screen". A page as tall as its content that a browser shows at its own width has a screen at each size, whose first screen shows one of the three where a reader scrolls through the page, and a page its screen holds whole is seen at once there, and judged whole (DEC-080 points 1 to 3). The rest stands, and those passages stay as they stood."
  - **DEC-022 point 7** comes to add, after its bullet "Read whole", a bullet: "**The first screen** (refinement per [visual-communication:DEC-080-readers-first-screen] point 4). A page that has a screen is drawn too as its first screen, a strip from its top as tall as its screen at the size drawn, as that record says."
  - **DEC-022's Implications,** under "Left open", drop the item "A page shorter than a screen, and where a screen's first view ends.", which this record's points 1 and 3 settle.
  - **DEC-028 point 8,** its bullet on `RS-GRAPHIC-001`. After "(*Refactoring UI*)" it comes to add "; the Nielsen Norman Group's eye-tracking studies of scrolling ("Scrolling and Attention")". After its last sentence it comes to add: "[visual-communication:DEC-080-readers-first-screen] gives the reasons for what the rule asks of a page's first screen, and of a page its screen holds whole, and for the source it adds (refinement per that record, points 1 to 3)."
- **The rules' words,** in `GRAPHIC`, made in this change once this record is accepted:
  - **`RS-GRAPHIC-001`** gains, before its bullet "A page of sections", the bullet: "**Its screen.** A page as tall as its content that a browser shows at its own width, such as a site's page, has a *screen* at each size it is drawn at: what a reader sees of it at once. Its screen is as wide as the page, and as tall as nine sixteenths of that width at `desktop` and at `projector`, five quarters at `tablet`, and sixteen ninths at `phone`, and as at `desktop` where the page is drawn at no size. Its *first screen* is its screen at its top. At a size where the page is taller than its screen, a reader scrolls through it, and its first screen shows at least one of the three, of the page or of a section that lies in that screen, whole or so far that a reader takes it for what it is. At a size where its screen holds it whole, a reader sees it at once."
  - **`RS-GRAPHIC-001`,** its bullet "A page of sections". Its first sentence's "Where a reader scrolls through a page, such as a site's page, and its content gives its sections as a list, met one after another, each section is judged as a page of its own" comes to read "Where a reader scrolls through a page, at a size where it is taller than its screen, and its content gives its sections as a list, met one after another, each section is judged there as a page of its own". Its last sentence comes to read: "A page seen at once, such as a slide, a poster, a figure, or, at a size, a page its screen holds whole, is judged whole there, sections and all, and has one focal point."
  - **`RS-GRAPHIC-007`,** its bullet "A page of sections". Its first sentence comes to read: "**A page of sections,** as `RS-GRAPHIC-001` names it, has each section weighed as a page of its own at a size where that rule judges it by its sections, with its heading, and the lead under it where it has one, as its head, and is weighed whole at a size where that rule judges it whole. No screen is weighed apart from the page." Its last sentence stands.
  - **Their origins stand.** `RS-GRAPHIC-001` and `RS-GRAPHIC-007` keep DEC-068 as their origin, which gives the reasons for the rest of their words. `RS-GRAPHIC-001` comes to anchor this record's points 1 to 3, and `RS-GRAPHIC-007` its points 2 and 3, so that a change to a reason flags the rule (DEC-068 point 8).
  - **The set's next major.** A change to an accepted rule that fails a page it passed asks a new major ([COR-051](../../../decisions/core/COR-051-rule-sets.md) point 7). So `GRAPHIC` takes the next after the one the default branch holds when this change lands, as [visual-communication:DEC-069-leaders-and-layers] point 7 has it for a new rule, and the set's example of `inherits` names it.
- **Read against this record, and left as they stand:**
  - [visual-communication:DEC-015-viewing-step-and-reviewer] point 1, "one page or one band of a page", point 5, "A tall page in bands", and point 7, "names the bands of each page it read", since a first screen is a strip of a page's height drawn as one image at the page's whole width, which DEC-022 calls a band;
  - DEC-021 point 1, "A width is a brand's value", since a screen's height is no width, and the brand's width sets it through the share;
  - DEC-055, since the first screen is drawn at the scale of the page's own images, and changes no text's size;
  - DEC-068 points 1, 4, 5 and 10, since the three, the frame, the form rule's page of sections and a page of sections' title and lead read as they do, with "scrolls through" in point 1's sense;
  - [visual-communication:DEC-030-design-agents] point 8, since the design knowledge comes to teach the studies the rule's reasons cite, by the build below.
- **The work that builds it,** under [project-kit#3413](https://github.com/aleskalfas/project-kit/issues/3413), in this change, which lands only once this record is accepted:
  - **The viewing step** draws each first screen as point 4 says, through either renderer, with its frames, and its report gives each page that has a screen its screen's height and whether its screen holds it whole. The report's schema names both. Tests draw a page taller than its screen and one its screen holds whole, at each size, through each renderer, and check the image, its frames and the report.
  - **The capability's page on outputs** names the first screen in the viewing step's bullets, in what a run writes and in what the report says. **The capability's README** names it where it says what `pkit visual look` draws.
  - **The reviewer's body** reads each first screen and judges point 2's test on it, reads whether a page's screen holds it whole to judge a page of sections as point 3 says, and names the first screens it read in its report, and those it did not under what it did not look at.
  - **The design knowledge's topic on where reading starts** teaches the Nielsen Norman Group's studies of scrolling.
  - **Its changeset** declares that the viewing step draws a page's first screen, and that `GRAPHIC` takes a new major in which `RS-GRAPHIC-001` judges a page's first screen and a page its screen holds whole, and `RS-GRAPHIC-007` weighs such a page whole. It tells a project to read the two rules and move its pin. No migration moves a pin, since the project's own reading is what it waits for (COR-051 point 7). The step's images and report are no installed state, so they owe none either.
