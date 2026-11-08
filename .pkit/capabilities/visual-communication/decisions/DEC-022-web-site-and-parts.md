---
id: DEC-022
title: A web page is a page of a site, as wide as its size and as tall as its content
status: accepted
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person designs a web page, or a portal of several, as one piece whose top is `site`, a top of the foundations. Its pages share one header and one footer. Each page is as wide as the size it is drawn at, and as tall as its content. A single web page is a site of one page, so a page joins a portal by being added to it. The parts made for a web page, such as a header or a form, join the starter, and each fits every size at the widths a brand gives it. A form is drawn, never sent. A part may show a state by its colour, such as a field in error, but shows no hover or focus. The viewing step cuts a page too tall for one image into strips, whichever renderer drew it.

## Context

Version 1 of the capability designs a web page or a portal, under a brand ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)). A design is drawn, not a working page. One design is laid out at each size the piece names, and nothing reflows live in a browser, as the founding record keeps live views outside ([visual-communication:DEC-001-visual-communication-discipline] point 9). The record of sizes decides how a size reaches a component: the foundations declare the sizes `desktop`, `tablet` and `phone`, a brand gives each its widths, and a component changes its shape by a switch on the size ([visual-communication:DEC-021-size-and-shape] points 1 to 3). This record decides what a web page is.

Four things stand in the way:
- **No top fits.** The foundations hold the top components ([visual-communication:DEC-007-starter-library] point 1). The figure is a *page alone*, a top with no slot of pages, and its height reads its lowest part. A deck's pages each take one of its layouts, and each takes the deck's size, so its text may run past a page's foot unreported. The word `page` already names a page of any piece, a page alone, and the command that lists a piece's pages.
- **The foundations build on no library.** So a top of theirs cannot draw another library's component, and a `repeat` part needs a component to draw.
- **No top draws a portal.** As several pieces under one brand, a portal's header and footer are typed again in each piece and language, and each page has its own lock and export number. No review reads across its pages. A top whose layouts are its pages' forms already hands its other fields to each page ([visual-communication:DEC-010-list-item-fields] point 5), so a shared header could be one field. What stops it is that such a page takes the top's size.
- **A phone's page is tall.** A page alone holding a column of twenty sections measured 2,096 px tall at 1,200 px wide, and 5,232 px tall at 390 px. Each image the viewing step draws is large enough that a page's smallest text reads ([visual-communication:DEC-015-viewing-step-and-reviewer] point 5). One image of that phone page passes the long edge of 1,568 px that one harness keeps, so the harness shrinks it past reading.

Four terms:
- A *site* is the top this record adds. A *web page* is one of its pages, a page designed for a browser. The records also call the medium the HTML renderer writes a web page ([visual-communication:DEC-020-html-page-drawing] point 5). A site's page is drawn in that medium, and in the others.
- A *web part* is a component made for a web page, such as a header, a form or a button.
- A *band* is a strip of a page's height that the viewing step draws as one image, at the page's whole width.
- A *size* is a mode of a size axis a piece can name, as the record of sizes has it.

## Decision

**The foundations ship a top, `site`, whose pages are web pages, each as wide as its size and as tall as its content. The parts of a web page join the starter. The viewing step draws a tall page in bands.**

### 1. The foundations ship a top, `site`, whose pages are web pages

- **The top.** `site`, a top of the foundations (DEC-007 point 1). Its layouts are its pages' forms, as a deck's are (DEC-010 point 5).
- **One page or many.** A single web page is a site of one page, and a portal is a site of several. So a page joins a portal by being added to the site's pages, and nothing in it is rewritten.
- **The name.** `site` names the whole, as `deck` does. It is not `page`, which already means three things.
- **A drawn design.** Nothing in it reflows in a browser, nothing is sent, and no link joins one page to another.
- **Never inside another page.** A site's pages are pages, so a site placed in a slide's slot is a page inside a page, which fails ([visual-communication:DEC-005-engine-and-plugins] point 5).

### 2. Its pages share a header and a footer, and each fills its main part

- **Its pages** lie in the top's field `pages`, and each names its layout (DEC-010 point 5).
- **Two more fields of the top.** `header` and `footer`, each optional, and each the component the content places there. Every page's drawing takes them (DEC-010 point 5). So each is written once in each language, under one lock.
- **Its first layout,** `standard`, has one slot, `main`, which every page fills with the component the content places.
- **Fields and a slot, not parts of its own.** Each takes any component: the starter's, a brand's own part or a local one. So the top needs no library beneath it.
- **A page drawn by its own component** takes none of the top's fields (DEC-010 point 5), so it draws no shared header or footer.
- **Edge to edge.** The drawing places the header, the main part and the footer one under another, each the page's whole width, on the page's background. Each part sets its own inset, so its colour can reach the page's edge and its content keeps from it. A component that sets no inset touches the edge.
- **More layouts later.** A layout the top adds later, such as a page with no header, breaks nothing ([visual-communication:DEC-009-layout-defaults] point 7).

### 3. A page gets its width from its size, and may ask for its own height

- **The site's width.** The site asks for the width of a shared role, `size.site`, the width of a site's pages. A brand gives it at each size it gives ([visual-communication:DEC-021-size-and-shape] point 2), so a page's width follows the size.
- **A default for the role.** It aliases `size.slide`, as a shared role the foundations add after their first version does ([visual-communication:DEC-004-brands-and-notations] point 7). So no released brand owes it a value, and a brand with no size draws a page as wide as its slide.
- **A width that does not follow.** Where a piece is drawn at a size other than the axis's default, and its top's width there is its width at the default, the check asks for attention (point 8). Otherwise the shape would follow the size, and the width would not.
- **A page's height.** A layout may say the height of its page, under `preferred`, by a formula on its drawing's parts. It says no width, since a page always gets the top's. A page drawn by its own component asks what that component asks.
- **What a page gets.** In a top whose layouts are its pages' forms, a page gets the top's width. It gets the top's height where the top asks for one, and else the height it asks for (DEC-005 point 3). A page that asks for more than the top's height gets less than it asks, and is reported as any such element is (DEC-005 point 14).
- **The site asks for its width alone.** So each of its pages is as tall as its lowest part, as the figure is. A layout of a top that asks for no height says its page's height, or fails.
- **The top's own frame.** A top that asks for no height is as wide as the width it asks for, and as tall as its tallest page. Its component sets both, as a component sets the size it asks for. Nothing reads that frame, since the top draws nothing and is no page.
- **From the top down.** A page that takes its own height places nothing from that height, since the height reads its parts. A part placed from the page's foot makes a loop, which is refused (DEC-005 point 3).
- **The shape is the parts'.** The top does not change with the size. A part changes its shape by the size ([visual-communication:DEC-021-size-and-shape] point 3).

### 4. The web parts join the starter, their jobs taken from design systems

- **Generic forms.** A web part is a generic form, which a brand styles with its values (DEC-007 point 4). So it is a starter component, and no library of web parts ships.
- **Their jobs.** A web part's job is its job on a page, not a question a visual answers, such as saying whose site a page belongs to, or taking a reader's answer. Its job and its form come from the components public design systems share, since the classifications of visuals sort pictures, not the parts of a page. Each web part cites the design systems its job and its form come from. Each does one job, and no two share one (DEC-007 point 2).
- **What lays sections down a page** is a web part with that job alone. It is never an option of a pattern that does another job.
- **The bar for entry.** Each meets the starter's bar: its job, its form and source, its fields and options, its reference renders, renders in languages that stress text, and a review (DEC-007 point 3).
- **The list.** The starter's README holds the web parts apart from its other patterns and blocks, each by its job on a page, with its fields, options and states (DEC-007, Implications).

### 5. A web part fits each size, at the widths a brand gives it

- **Its widths.** They come from the width it gets, from shares, and from what its text measures. A role may set a gap, an inset or a stroke, and may cap a width, such as the length of a line of text. A role never sets the width a part needs in order to fit.
- **Its rows and columns** share the width they get, or take a width they are given. So a part that asks for more than it gets is reported.
- **Too little room.** Where a size leaves a part too little room, the part changes its shape by the size ([visual-communication:DEC-021-size-and-shape] point 3). It never runs past its frame.
- **Drawn at each size.** A web part's reference renders draw it at each size the brand of the tests gives. Its test holds each of its frames inside the page at each size, under that brand and under the neutral brand. No check finds every part that runs past a page's edge, such as a column, so the test is the guard. It is a test of the capability's own, and adds no check to validation.
- **What that proves.** A web part is proved at the widths those two brands give. Under another brand's widths, the reviewer reads what the step draws.

### 6. A form a reader fills is drawn, and a part's states say what it is

- **Never sent.** A form holds no action, and a field shows the text its content gives it.
- **States as colours.** A state's look is a colour family, as the format declares it. So a web part takes the states a family can show, such as a field in error or a button that cannot be pressed (DEC-001 point 6). They need no engine work. Each part's file declares its states.
- **No state of a moment of use,** such as hover, focus or pressed. A design shows a page at rest.

### 7. The viewing step draws a tall page in bands

- **When.** Where one image of the whole page, large enough that its smallest text reads, would pass the long edge the command allows for an image a harness reads whole. That number stays the command's (DEC-015 point 5).
- **Whole width, one scale.** Each band is as wide as the page. A page's bands share one device scale, so its smallest text reads in each.
- **Where it cuts.** Each band overlaps the next by at least the page's tallest line, so every line lies whole in one band. Where a gap between elements lies inside that overlap, the cut falls in it.
- **Cut once.** The step computes the bands once, from the scene's frames. Each tool's module then draws the regions it is handed, so the two routes cut alike (DEC-015 point 2).
- **Frames.** Beside each band lie the frames of the elements it shows, in its own pixels. An element a cut crosses is framed in each band it shows in.
- **Text drawn to nothing** is checked on the whole page once, never band by band (DEC-015 point 3). So a text in an overlap, or across a cut, is reported once.
- **On either route.** The step cuts what either tool draws: the tool that draws the SVG renderer's pages, and the browser that draws the HTML renderer's ([visual-communication:DEC-020-html-page-drawing] point 5).
- **Read whole.** The report lists each page's bands in order. The reviewer reads every band of a page before it reports on that page, and its report names the bands it read.
- **Height alone.** Bands cut a page's height. A page too wide for one image whose smallest text reads is drawn as wide as the command allows, and the report says that its smallest text may not read.
- **Which sizes.** The step draws the combination DEC-015 point 5 sets by default, so a session names the other sizes. The reviewer's agent file, and the skill that guides building a piece, have a session name each size the piece names, a phone's among them.
- **No limit on height.** Neither a skill nor a check limits how tall a page may be. A page past the largest page a format holds, such as a PDF page, is that renderer's to draw otherwise or refuse, and it reports the loss (DEC-001 point 2).

### 8. What breaks, and what the checks report

The record of change over time already counts a removed or renamed layout or slot as a breaking change ([visual-communication:DEC-003-change-over-time] point 6). Beyond it:
- **Not breaking, for a top's library:** a new layout, or a layout's height said, changed or dropped where its top asks for a height. A piece meets each only when a person moves its lock (DEC-001 point 7).
- **Breaking, for a top:** starting or ceasing to ask for a height, since every page's size changes with it. A drawing written for a top that asks for a height then no longer fits, and the reverse.
- **Fails validation,** as the record of files and validation decides ([visual-communication:DEC-002-files-and-validation] point 7):
  - a layout of a top whose layouts are its pages' forms, where the top asks for no height and the layout says none
  - a layout that says a width
  - a site placed inside another page
- **Reported as an element that gets less than it asks** (DEC-005 point 14): a page that asks for more than the top's height.
- **Asks for attention:** a piece drawn at a size other than the axis's default, whose top's width there is its width at the default. It lies at the piece, and names the brand, so it names no component.
- **Reported once.** A finding in what a field of the top draws, read the same on several pages, is reported once, naming its pages.

## Rationale

**Why one top for a page and a portal.** A portal's cost as several pieces is in what they cannot share: the header, the lock, the export number and a review across them. A top whose layouts are its pages' forms shares each of them already, and only a page's size stood in the way. A single page as a site of one costs one list in its content, and later joins a portal with nothing rewritten.

**What one piece costs.** Its pages share what one piece has:
- one lock, so a move is judged on every page
- one state, so no page is published while another is a draft
- one record of findings, so an edit to one page computes every page again
- one content file in each language, which two people editing two pages share
- one HTML file in each language and size, holding every page (DEC-020 point 4)

A page alone, such as the figure, can be placed in a slide, and a site cannot. So a deck that presents a web design shows it only as a picture. A portal that outgrows one piece is split into several sites, each a piece of its own, at the cost of a header typed in each.

**Why `site`.** `page` already names a page of any piece, a page alone and a command, so a top called `page` or `web-page` would add a fourth meaning. A top named for one kind of site, such as `portal`, would misname a single page.

**Why these names.** Content writes each name of the top's interface, so renaming one after a release breaks every site (DEC-010 point 7). The names are chosen once, here. `header`, `main` and `footer` are the names HTML gives those parts of a page. `pages` holds a site's pages, as `slides` holds a deck's. `standard` names the plain form of a page, and gives `page` no fourth meaning.

**Why a page's height, and only where its top asks none.** A web page is as long as what it holds, and a page that takes the top's height hides text past its foot. A deck's pages share one size by design, and keep it. A page asks for a height and gets one, as every element does (DEC-005 point 3), so a missing height on the top means what it means elsewhere. A layout that says its height under a top that asks one has its overflow reported. So a deck's layouts may come to report the overflow Context names. The height lies beside each layout's drawing, since only that drawing knows its lowest part. Nothing format 1 accepted declares a layout's height, and a top whose layouts are its pages' forms with no height was refused, so nothing format 1 accepted is refused ([visual-communication:DEC-003-change-over-time] point 3).

**Why a role, with a default and a finding.** A width is a brand's value ([visual-communication:DEC-021-size-and-shape] point 1), so the top reads a role. A desktop page fills a screen, as a slide does, so `size.slide` is the fairest stand-in. A role with no default would break every brand once the foundations are released (DEC-004 point 5). A brand may still give the sizes and forget the widths, so its phone's shape would draw at a desktop's width. The finding reads the outcome, a top's width that does not change with the size, so it names no component, as the engine names none (DEC-001 point 4). It asks rather than fails, since a piece may mean one width at every size.

**Why slots edge to edge.** A header's colour, or a section's, often runs to the page's edge. A margin in the top would cut it, and a part that wants a margin sets its own.

**Why the starter.** The records hold a generic form in the starter, styled by a brand's values (DEC-007 point 4), and both reject libraries split by kind of work (DEC-001 and DEC-007, Alternatives considered). That split costs most in the parts a page and a slide both draw, such as a card, a button or a table. A header, a navigation or a form serves a web page first. Even so, a fix to it reaches every brand only from the one library, and the starter's bar suits it. A long German word breaks a button as it breaks a card.

**Why jobs from design systems.** The classifications the starter takes its jobs from sort pictures by what they show. A header answers no question a picture answers, so they hold none of a page's parts. Design systems name those parts, and draw them in forms close to each other. The starter draws its forms close to theirs (DEC-007 point 4). One job to a part keeps the rule that two components never compete for one job. A page's sections come in an order, and differ in kind. So laying them down is a job of its own, and no pattern takes it as a second job.

**Why widths from the width a part gets.** A part sized by a number fits one size, and a page is drawn at three. A row that shares its width, or is given one, is reported when its items ask for more. A column or a part placed past the edge is not, so the test of each part's frames is the guard. A cap leaves a part that fits, and a reader needs one, since a line of body text across a desktop page runs past what reads well.

**Why colours that say what a part is.** A state's look is a colour family as the format stands, and the engine already draws it. So a field in error costs a line of its file and a render. A design shows a page at rest. A hover is a shade of the part at rest, which no family holds. A focus ring drawn outside a part is a part drawn in one state alone, and nothing a component chooses with reads a state. A later change can add either.

**Why bands.** A phone's page of real length is the main thing version 1 draws, and a reviewer must read all of it. A shrunk image hides the small text DEC-015 point 5 guards. A limit on a page's height would refuse the pages this version is for. Bands keep each image readable, and the page whole.

**Why on both routes.** A piece that declares `html` is read through a browser, since that shows what a reader gets (DEC-020 point 5). Bands on the SVG renderer's route alone would send each tall web page to another renderer to be read.

### Alternatives considered

- **A web page as a page alone, `web-page`, and a portal as several pieces.** Rejected. A portal would keep the costs in Context.
- **Two tops: a page alone and a site.** Rejected. Two tops would do one job, and a page moving into a site would be rewritten.
- **Several pieces reading one header as shared content** (DEC-001 point 3). Put off. No record gives shared content a format, and the locks, the export numbers and the reviews would stay apart.
- **A marker on the field that holds the pages, saying they take their own height.** Rejected. A missing height already says it, as for any element.
- **One height for all of a top's pages, on the top.** Rejected. Only a layout's drawing knows its lowest part.
- **A main part that is a list the top's own drawing lays down.** Rejected. A `repeat` part needs a component to draw, and the foundations build on no library. A part that lays sections down a page does it as well.
- **A library of web parts of its own,** released apart as each shipped library is ([visual-communication:DEC-013-shipped-library-releases] point 1). Rejected, for the reasons above. It would set generic forms apart, against DEC-007 point 4.
- **A web part's job from the classifications of visuals.** Rejected. They hold no part of a page.
- **Sections laid down a page by an option of the starter's list.** Rejected. The list would do two jobs.
- **A margin in the top.** Rejected. It would cut a colour that runs to the page's edge.
- **A hover painted by another family.** Rejected. A hover changes a shade, not a hue.
- **A finding for every frame past its page's edge.** Put off. It would cover a brand's and a local part too, and no need has shown yet.
- **A limit on a page's height, named in a skill.** Rejected. It refuses the pages version 1 is for.
- **Bands on the SVG renderer's route alone.** Rejected, for the reason above.
- **Bands cut only between elements.** Rejected. An element taller than a band has no such cut, so the overlap stays, and a gap is taken where the overlap holds one.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-007's summary and Decision sentence** come to add that the starter also holds the parts of a web page, whose jobs and forms come from the components design systems share.
  - **DEC-007 point 2, its heading and its body,** come to say that the starter is organised by the job a visual, or a part of a page, does. A web part's job is its job on a page, not a question a visual answers. Its job and its form come from the components public design systems share, and it cites the design systems they come from. Each does one job, and the README holds the web parts apart, by their jobs on a page.
  - **DEC-007 point 3** comes to add, to a web part's reference renders, its drawing at each size the brand of the tests gives. It adds a test that holds its frames inside the page at each size, under that brand and the neutral brand. Each mode of a size axis a component names, which the record of sizes added there, stays.
  - **DEC-015's Decision sentence** comes to say that the step draws a renderer's output as images by page, band, language and key.
  - **DEC-015 point 1, "What it is"** comes to say that the step draws what a renderer drew for one page, or one band of a page.
  - **DEC-015 point 2, "Behind one module of its own"** comes to say that the module takes what the renderer drew, a page or a page file, with the regions of it to draw.
  - **DEC-015 point 5** comes to add that a page too tall for one image is drawn in bands, as this record's point 7 says.
  - **DEC-015 point 7, "Nothing unseen reads as clean"** comes to say that the reviewer's report names the bands of each page it read.
- **Read against this answer, and left as they stand:**
  - DEC-001 point 1, and DEC-020 point 5, since they call the HTML renderer's medium a web page, in which a site's pages are drawn too.
  - DEC-001 point 4, since the finding of a width that does not follow names no component.
  - DEC-001 point 6, since a state's look through a family is one of the ways it allows.
  - DEC-001 point 9, since a site is a drawn design.
  - DEC-001's and DEC-007's rejection of libraries split by kind of work, since the web parts join the starter.
  - DEC-007's title, since the starter still covers the jobs a visual does.
  - DEC-007 point 1, since the top is the foundations', and a web part is a pattern or a block.
  - DEC-007 point 4, since a web part is a generic form.
  - DEC-007's Implications, "This record adds no check to validation", since the test of frames is a test of the capability's own.
  - DEC-004 point 7, since the new role carries a default.
  - DEC-005 point 3, since a page asks for a height and gets one, and the top's frame is its component's.
  - DEC-005 point 5, since a site's pages are pages.
  - DEC-005 point 14, since a page that gets less than it asks is judged as any element is.
  - DEC-008 point 2, since a role that caps a line ends at a shared role, or a new shared role takes a default.
  - DEC-009 points 1, 6 and 7, since an instance of a site's layout is one page, and a new layout breaks nothing.
  - DEC-009's Implications, its open question of a drawing's physical size, since a height in the scene's px is no physical size.
  - DEC-010 points 5 and 7, since a site's pages name their layout, and the site is a new top.
  - DEC-011 point 4, since a field of the top is drawn once on each page, so an end inside it is found once on the tie's page.
  - DEC-015 point 3, since text drawn to nothing is checked on the whole page.
  - DEC-020 point 4, since a file holds pages of any height, a whole portal in one file.
- **The Task of the web page** adds the top, its first layout, the role with its default, and a layout's height with what a page gets and the top's frame. It gives `size.site` a value at each size in the brand of the tests and the neutral brand. It adds point 8's findings, and builds bands in the viewing step on both routes. It changes the reviewer's agent file and the skill that guides building a piece to name each size, and the release's comparison to read whether a top asks for a height (DEC-003 point 7). It changes the capability's pages, the layouts of `components.md` among them. It gives the analysis's glossary the terms site and web page.
- **The Task of the web parts** adds them to the starter, with the README's section, their jobs and sources, their states, and their renders and tests at each size. The README says which parts set their own inset. It names any shared role a cap on a line needs.
- **The Feature of the web page,** [project-kit#2791](https://github.com/aleskalfas/project-kit/issues/2791), comes to say that a portal is a site of several pages, and that a site is the kind of piece.
- **Left open:**
  - **A deck's layouts saying their heights,** so its text past a page's foot is reported. That is a change of the foundations' deck of its own.
  - **A page's own mark in the shared navigation,** such as the link to the page a reader is on. A family can paint it, but a page would have to give the shared header a word naming its link, and nothing passes a page's word to a field of the top.
  - **A site shown inside a slide,** which point 1 refuses. A slide shows a picture of the page instead, given as a picture file, which does not follow the site ([visual-communication:DEC-025-picture-files], Implications).
  - **A brand's drawing of a site's layout** says its page's height in its own file. How waits for the change that lets a brand declare its drawings (DEC-009 point 8).
  - **A logo in a header that follows the brand** is the brand's value of the picture role `picture.logo`, which the shared header shows ([visual-communication:DEC-025-picture-files] point 4).
  - **A page shorter than a screen,** and where a screen's first view ends.
  - **A brand's or a local part past a page's edge,** which only the reviewer sees until a finding covers it.
  - **The starter's older patterns, which follow no size,** and squash in a phone's main part. Each follows a size in a change of its own.
  - **A portal larger than one piece holds well,** such as a site whose pages lie in files of their own.
  - **A hover, a focus or a pressed state,** and a link between pages, wait for a need.
