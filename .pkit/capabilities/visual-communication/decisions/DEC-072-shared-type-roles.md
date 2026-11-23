---
id: DEC-072
title: The shared roles gain a display type, a lead type and an emphasis type, each with a default, and no second accent
status: proposed
date: 2026-11-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the foundations' shared roles gain three types, which every brand may give and a piece's own components can name. `type.display` is for a few words set larger than a page's title, such as a cover's title or a poster's headline. `type.lead` is for running text set between the body and a page's title, such as a slide's lead. `type.emphasis` is for a span stressed within running text, which a brand sets in italic, or however its scripts mark stress. Each has a default that aliases an older type: the display takes a page's title, the lead the body, and the emphasis the strong type. So no brand owes them a value, none breaks, and a brand that gives none draws them as types it already gives. The shared roles gain no second accent. No older colour could stand in for it without merging the two things it sets apart, and the differences it would carry have a place already: a kind in a concept's colour family, beside its sign, and a rank in an order's steps. The evidence is two rebuilt presentations and one person.

## Context

The foundations, a component library the capability ships, declare the *shared roles*: the named purposes that every library names and every brand gives a value ([visual-communication:DEC-001-visual-communication-discipline] point 5). Among them are the *typography roles*, each of which gives a text its font, size, weight and line height ([visual-communication:DEC-012-text-runs], Context). A component names a typography role for each text it draws, and a brand gives the role its value. The shared ones set a page's title, a heading, the body, a span set apart at the body's size in a heavier weight, and code, as the capability's page on files lists them. None sets text above a page's title, none sets running text between the body and a page's title, and none sets a span stressed rather than made heavier.

A *local component*, made inside one piece for that piece alone, names roles as any component does (DEC-001 point 4). Under every brand it can count only on the shared roles. It declares no component token, and reads none, since a component token is read only by the component that declares it ([visual-communication:DEC-035-component-tokens] points 3 and 5).

The test of [project-kit#3470](https://github.com/aleskalfas/project-kit/issues/3470) had the capability's designer rebuild two free drafts as pieces, with one brand and the project's libraries. Its results are in the scratchpad note `design-review-ship-call` of the repository the capability is authored in, under "What the test found", question 4, and [visual-communication:DEC-071-sketch-and-rebuild] reads them in its Context. Of the brand, the rebuilds lacked these:
- **type above a page's title** on a projector;
- **a size between the body and a page's title** that a piece's own components could reach;
- **an italic, and more than two weights;**
- **colours** light or strong enough for what they had to carry;
- **a second accent.**

One of these lacks held a piece back. After one round on the person's notes, the person called the second rebuild shippable save one page, whose running text needed the size between, which the brand gave a piece's own components no way to reach. A top may already draw such a size, as the deck draws the line under a slide's title. That size is the top's component token, which no other component reads.

**Why now.** DEC-071 makes every new presentation a rebuild of a sketch. For each of the sketch's choices of type, colour and space, the rebuild takes the brand's role that does that choice's job (DEC-071 point 4). Where no role does, it draws a *stand-in*, the nearest that keeps the part's meaning, and the lack goes to its owner as a *request* (DEC-071 point 5). The shared roles are the foundations', whose owner is whoever maintains the capability. A new shared role waits for its record ([visual-communication:DEC-030-design-agents] point 4). This is that record, for the four roles the rebuilds lacked.

**What lies outside it.** The weights and the colours the rebuilds lacked are values, not roles. A brand gives the weights it ships, and gives its colours to the roles it has, among them the families and an order's ends. Such a lack goes to the brand's owner as a request (DEC-071 point 5). Whether a brand may give one font family a file for each weight is decided apart ([project-kit#3276](https://github.com/aleskalfas/project-kit/issues/3276)).

**How far it goes.** Two presentations, drawn with one brand and judged by one person, and one page that the lack of one role held back. The roles this record adds rest also on the levels that type scales in wide use hold (Rationale, "Why add type roles on one test").

The words it uses:
- **A default** is an alias to another role, which a role takes wherever no brand gives it a value. A *chain of defaults* follows the defaults from role to role ([visual-communication:DEC-008-library-role-defaults] point 1).
- **Running text** is text read as sentences, rather than a head or a label.
- **A page's title** is the text that names a whole page, which the shared type `type.title` sets.
- **A lead** is the text a page's content gives to state the page's point, such as a slide's lead under its title ([visual-communication:DEC-029-piece-brief] point 2).
- **The rebuild, a stand-in and a request** are DEC-071's.

## Decision

**The shared roles gain `type.display`, `type.lead` and `type.emphasis`, three typography roles, each with a default that aliases an older type, so no brand owes them a value. They gain no second accent.**

### 1. `type.display`, above a page's title

- **Its job.** A few words set larger than a page's title and read at a glance, such as a cover's title, a poster's headline, or a number that is a page's whole point. It is the largest type a brand gives, at each size it gives.
- **Its default, `{type.title}`.** A brand that gives no display sets it as a page's title, the largest type it gives already.
- **A chain that ends where every brand gives a value.** `type.title` has a default of its own, `{type.heading}`. A shared role's default may alias a shared role that has a default, where the chain ends at a shared role without one. Every brand gives that role a value, so every brand draws the display, as [visual-communication:DEC-004-brands-and-notations] point 7 asks of each role added after the foundations' first version. The check of the foundations' roles, which asks a shared role's default to alias a role with no default, comes to take such a chain. It still fails a default of another type, one that leads nowhere, and a loop.

### 2. `type.lead`, between the body and a page's title

- **Its job.** Running text set larger than the body and smaller than a page's title. A page's lead is one such text. Other running text that a page sets above its body is another, such as a statement or a quotation set apart. It is set as running text, not as a head, so where its size stands against a heading's is the brand's to choose.
- **Within reach of a piece's own components.** A shared role, it is named by any component, a local one included, under every brand (DEC-001 point 4).
- **Its default, `{type.body}`.** A brand that gives none sets it as the body, so it still reads as running text.
- **The deck's lead follows it.** The deck's component token for the line under a title comes to default to `type.lead`, in place of `type.body`. Under a brand that gives neither, it draws as before. Under a brand that gives `type.lead` and not the token, a slide's lead and a piece's own running text at that size look alike. A default pointed at another role breaks nothing (DEC-035 point 6).

### 3. `type.emphasis`, for stress within running text

- **Its job.** A span stressed within running text, at the body's size, as `type.strong` sets a span apart for its importance at that size. A component names it as it names any typography role, for a part or for a run style (DEC-012 point 2).
- **Its manner is the brand's.** The role names the job, not a look. A brand sets it in italic where its scripts have one, and otherwise as they mark stress.
- **An italic is a face of its own.** A brand's typography holds no style, so a brand gives an italic as a font family of its own, with its own committed file, as it gives a weight a family of its own (DEC-012 point 4; DEC-004 point 9). No renderer slants an upright face. Whether one family may name a file for each weight, and for each style, is decided with [project-kit#3276](https://github.com/aleskalfas/project-kit/issues/3276).
- **Its default, `{type.strong}`.** A brand that gives none sets a stressed span in the strong type, so the span stays apart from its neighbours, set apart by weight rather than slant.
- **At the body's size alone.** Emphasis within a lead, a heading or a title is left open.

### 4. No second accent

- **Not added.** The shared roles keep one accent, the colour that sets one thing apart from the rest of a page.
- **No fair stand-in.** A shared role added after the foundations' first version needs a default that aliases an older role (DEC-004 point 7), or a major release of the foundations, since a new shared role with no default breaks every brand (DEC-004 point 5). A second accent would set a second thing apart, and apart from the first. Only a role of that meaning would serve as its default (DEC-008 point 2), and no role carries it. The accent would merge the two things, unseen, under every brand that gives the second accent no value, and any other colour carries a meaning of its own.
- **What it would carry has a place.** A difference of kind is a concept's, which a notation maps to a colour family and draws with its sign beside it (DEC-004 point 10). A difference of rank along a sequence is an order's, whose steps run between two ends a brand gives ([visual-communication:DEC-032-ordered-colour-steps] point 1). A second accent would tell two things apart by colour alone, with no sign, and outside the bound on how many concepts one piece tells apart by colour.
- **A colour of one brand's identity** lies in that brand's own form, its drawings and its own components, and in the values it gives the roles it has (DEC-001 point 5). One project's identity goes into its own libraries (DEC-030 point 4).
- **In a rebuild.** Where a sketch sets a second thing apart, the rebuild takes the role that does that difference's job: a concept's family, an order's step, or a type. Where none keeps the difference, it draws a stand-in, and the lack reaches the foundations' owner as a request (DEC-071 point 5).

### 5. What the roles add, and what they ask of no one

- **Additions.** Each is a new shared role with a default, in the group `type`, which holds the shared types already. So none adds a top group, and none breaks a brand or a library (DEC-004 point 5). They go into the foundations' version being built, whose release needs at least a minor.
- **No brand owes a value.** Every brand draws each of them, at the value it gives or at the default. A brand exports them as it exports every shared role (DEC-004 point 5).
- **No change of format.** A library's roles take a typography role with a default, and a brand's typography takes the members it took. Every file the capability accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3).
- **No pair, and no order of sizes checked.** A typography role is in no contrast pair, and each text a scene draws is still measured at its own size and weight (DEC-004 point 8). No check compares the roles' sizes. Their order is a brand's design, which its owner judges, as the owner of a library judges a default's fit (DEC-008 point 2).
- **A piece meets them when its lock moves** to a version of the foundations that declares them (DEC-003 point 8).

## Rationale

**Why add type roles on one test.** Only one of the lacks held a page back, but a shared role with a default costs little. It asks no brand for a value, breaks nothing, and changes how nothing draws until a brand gives it one (DEC-004 point 5). Each of the three serves every kind of work the capability draws. A display serves a poster, a cover and a figure's one number, a lead a site's opening paragraph and a slide read across a room, and emphasis any running text. Type scales in wide use hold the same levels. Material Design's scale runs from display through headline, title and body to label. Bootstrap offers display headings and a lead paragraph. HTML tells `em`, stress, from `strong`, importance. And every new presentation is a rebuild, which looks for the role that does each of a sketch's choices' job (DEC-071 points 1 and 4). Each type the shared roles lack becomes a stand-in in every rebuild that meets it, until a request is met.

**Why shared roles, and not a top's tokens or a library's roles.** A piece's own components draw what no library's component draws, and under every brand they can count only on the shared roles (DEC-035 points 3 and 5). A top's component token, such as the deck's lead, is the narrowest role, one component's. Read by another component, a brand's value meant for the top would restyle something out of its author's sight (DEC-035, Alternatives considered). A library's own role reaches a brand only where the brand names that library (DEC-008 point 4). A type serves every library, and a meaning that recurs across libraries belongs to the foundations (DEC-008 point 2).

**Why each default.** A default is the fairest stand-in under a brand that never gave the role a value, and for a size or a font a nearby role usually serves (DEC-008 point 2).
- *The display takes a page's title,* the largest type a brand gives. Each type the check's narrower rule allows, a heading among them, is smaller than a page's title in many brands, and would draw a display below the title it should stand above.
- *The lead takes the body,* so the text stays running text. A heading would set it in a head's weight, and it would read as a head.
- *The emphasis takes the strong type,* so a stressed span stays apart from its neighbours. The body would drop the stress, unseen. The cost: under a brand that gives no emphasis, a span stressed and a span set apart for its importance look alike.

**Why a chain of two, for the display.** What DEC-004 point 7 guards is that every brand released before a role still draws it. A chain that ends at a shared role with no default keeps that at any length, since every brand gives such a role a value. The check's narrower rule kept chains short where nothing needed a longer one. The display needs a page's title, which has a default of its own.

**Why the emphasis names a job, not italic.** A role is a named purpose (DEC-001 point 5). Not every script has an italic: Chinese and Japanese mark stress otherwise, such as with dots beside the characters. A brand that serves them sets emphasis their way under the same role, and a component that names emphasis means the same under every brand.

**Why an italic is a face of its own, and a typography gains no style.** DTCG's typography holds a font family, a size, a weight, a letter spacing and a line height, and no style, so a brand's files stay valid DTCG (DEC-004 point 1). A renderer that slanted an upright face would draw what the engine did not measure, which DEC-004 point 9 refuses. A face given its own file is measured and drawn from that file, as a weight given a family of its own is (DEC-012 point 4).

**Why no second accent.** For a colour that marks a meaning, only a role of that meaning is a fair stand-in, and a role with none is left with no default rather than a misleading one (DEC-008 point 2). A shared role added after the foundations' first version cannot go without a default short of a major release that breaks every brand (DEC-004 points 5 and 7). So a second accent would take the accent as its default, and under every brand that gives it no value it would merge the two things it was added to tell apart. The capability tells things apart by colour in two ways: by concepts, with a sign beside each and a bound on how many, and by an order's steps. A second accent would be a third way, with neither guard. The cost: a brand whose identity holds two colours shows the second only in its own form and in the values it gives its roles, and a piece's own component cannot paint with it under every brand.

**Why the deck's lead follows the lead.** The deck's token sets the line under a slide's title, a lead's job. Its default pointed at `type.lead` keeps a slide's lead and a piece's own running text at that size alike, under a brand that gives the role and not the token. Under a brand that gives neither, or that gives the token, nothing changes.

### Alternatives considered

- **No new role: each rebuild draws a stand-in, and the roles wait for more evidence.** Not taken: the stand-in for the size between held a page back, every new presentation is a rebuild (DEC-071 points 1 and 4), and a role with a default costs no brand anything.
- **A numbered scale of sizes, such as `type.1` to `type.9`.** Rejected: a role is a named purpose (DEC-001 point 5). A number names a rank, and a brand could not know what text a component meant by it, so switching brands would restyle by rank rather than by job.
- **A piece's own component that reads a top's token, such as the deck's lead.** Rejected, for DEC-035 point 3's reasons.
- **A size that a piece's own component computes from the body's.** Rejected: only a brand holds a raw value (DEC-001 point 5), and a brand gives a typography role whole.
- **The roles as the starter's own.** Rejected: a brand reaches them only by naming the starter (DEC-008 point 4), and a type serves every library (DEC-008 point 2).
- **The display defaulting to a type with no default of its own, such as a heading,** as the check's narrower rule asks. Rejected, for the reason under "Why each default".
- **The lead defaulting to a heading.** Rejected, for the reason under "Why each default".
- **The emphasis defaulting to the body.** Rejected: the stress would vanish, unseen.
- **`type.italic`.** Rejected: it names a look that some scripts lack, not a job.
- **A style in a brand's typography, as CSS's `font-style`.** Rejected: DTCG's typography holds none, and a renderer would slant an upright face, drawing what the engine did not measure (DEC-004 point 9).
- **Emphasis at every size, such as a lead's or a heading's.** Not taken: no need has shown, and a role for it with a default is an addition later (DEC-004 point 5). Its trigger to revisit: a rebuild's stand-in for emphasis within a lead, a heading or a title, reaching the foundations' owner as a request.
- **A second accent defaulting to the accent.** Rejected, for the reasons under "Why no second accent".
- **A second accent with no default, in a major release of the foundations.** Rejected: every brand and every library would move to a new major, for a colour whose jobs have a place already. Its trigger to revisit, with the one above: requests from rebuilds in which a second thing set apart carried neither a kind nor a rank, so that no family and no order kept the difference, or a committed test that finds so.

## Implications

- **No edit to an accepted record.** Each role is an addition that DEC-004 points 5 and 7 and DEC-008 point 2 allow, and that DEC-030 point 4 asks a record for. The check's narrower rule on a shared role's default, and the page that states it, are no record.
- **Read against this record, and left as they stand:**
  - DEC-001 points 4 and 5, since a local component names roles as any component does, a role is a named purpose, and only a brand holds a value;
  - DEC-004 point 5, since a new shared role with a default, in a group that holds shared roles, breaks nothing;
  - DEC-004 point 7, since each role added after the foundations' first version has a default whose chain ends at a role every brand gives a value (point 1);
  - DEC-004 points 8 and 9, since each text a scene draws is measured at its own size and weight, and an italic is a committed file, whose lack refuses the render;
  - DEC-004 point 10, DEC-032 point 1 and [visual-communication:DEC-036-concept-signs], since kinds and ranks are told apart by colour as they decide;
  - DEC-008 point 2, since each default is the fair stand-in it asks for;
  - DEC-012 points 2 and 4, since a run style chooses a typography role, and a face given a family of its own is drawn from its own file;
  - DEC-035 points 3, 5 and 6, since no local component reads or declares a token, and a token's default pointed at another role is neither a break nor an addition;
  - DEC-071 points 4 and 5, since a rebuild takes these roles where they do a choice's job, and a lack still reaches its owner.
- **Which brand gives them values.** The neutral brand gives each a value in every combination it gives, as it gives every shared role (DEC-008, Implications). Its owner chooses the values in the slice. A brand built on the neutral brand gives them values only where the neutral brand opens them (DEC-004 point 6). The neutral brand opens no role, and what it opens is decided apart ([project-kit#3169](https://github.com/aleskalfas/project-kit/issues/3169)). A brand with no base gives them values, or draws them at their defaults.
- **Left to a slice under [project-kit#3149](https://github.com/aleskalfas/project-kit/issues/3149),** filed once this record is accepted:
  - the foundations' version being built declares the three roles with their defaults, and the deck's lead token defaults to `type.lead` (points 1 to 3);
  - the check of the foundations' roles takes a shared role's default whose chain ends at a shared role with none (point 1);
  - the neutral brand's version being built gives the three roles their values;
  - the capability's page on files, where it lists the shared types and says what a shared role's default may alias, and the tests.
- **Its changeset.** This change declares that it moves no surface of the capability. It owes no migration (COR-010).
- **Left open,** with the triggers their alternatives give:
  - emphasis at sizes other than the body's (point 3);
  - a second accent (point 4).
