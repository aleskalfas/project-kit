---
id: DEC-072
title: The shared roles gain a lead type, for running text set larger than the body, and the other roles the rebuilds lacked wait for a need
status: proposed
date: 2026-11-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the foundations' shared roles gain one type, `type.lead`, for running text set larger than the body so that it is read first, such as a page's opening paragraph or the line under a slide's title. Every brand may give it a value, and a piece's own components can name it. It names a size of running text, not a page's lead, which may be set in it or not. Its default is the body, so no brand owes it a value and none breaks. The deck's line under a slide's title, and its cover's subtitle, come to follow it unless a brand sets them otherwise. The shared roles gain no display type, no emphasis type and no second accent now. Each waits until the person calls a rebuild's stand-in for it short of shipping, or a project asks for it. A shared role is cheap to add and costly to remove, and of what the rebuilds lacked, only this size held a page back. The evidence is two rebuilt presentations and one person.

## Context

The foundations, a component library the capability ships, declare the *shared roles*: the named purposes that every library names and every brand gives a value ([visual-communication:DEC-001-visual-communication-discipline] point 5). Among them are the *typography roles*, each of which gives a text its font, size, weight and line height ([visual-communication:DEC-012-text-runs], Context). A component names a typography role for each text it draws, and a brand gives the role its value. The shared ones set a page's title, a heading, the body, a span set apart at the body's size in a heavier weight, and code, as the capability's page on files lists them. None sets running text larger than the body, none sets text above a page's title, and none sets a span stressed rather than made heavier.

A *local component*, made inside one piece for that piece alone, names roles as any component does (DEC-001 point 4). Under every brand it can count only on the shared roles. It declares no component token, and reads none, since a component token is read only by the component that declares it ([visual-communication:DEC-035-component-tokens] points 3 and 5).

The test of [project-kit#3470](https://github.com/aleskalfas/project-kit/issues/3470) had the capability's designer rebuild two free drafts as pieces, with one brand and the project's libraries. Its results are in the scratchpad note `design-review-ship-call` of the repository the capability is authored in, under "What the test found", question 4, and [visual-communication:DEC-071-sketch-and-rebuild] reads them in its Context. Of the brand, the rebuilds lacked these:
- **type above a page's title** on a projector;
- **a size of running text larger than the body** that a piece's own components could reach;
- **an italic, and more than two weights;**
- **colours** light or strong enough for what they had to carry;
- **a second accent.**

One of these lacks held a piece back. After one round on the person's notes, the person called the second rebuild shippable save one page, whose running text needed the larger size, which the brand gave a piece's own components no way to reach. The person called every other page shippable, though some were drawn without a role the brand lacked. A top may already draw such a size, as the deck draws the line under a slide's title. That size is the top's component token, which no other component reads.

**Why now.** DEC-071 makes every new presentation a rebuild of a sketch. For each of the sketch's choices of type, colour and space, the rebuild takes the brand's role that does that choice's job (DEC-071 point 4). Where no role does, it draws a *stand-in*, the nearest that keeps the part's meaning, and the lack goes to its owner as a *request* (DEC-071 point 5). The shared roles are the foundations', whose owner is whoever maintains the capability. A new shared role waits for its record ([visual-communication:DEC-030-design-agents] point 4). This record decides which of the four roles the rebuilds lacked the shared roles gain now.

**What lies outside it.** The weights and the colours the rebuilds lacked are values, not roles. A brand gives the weights it ships, and gives its colours to the roles it has, among them the families and an order's ends. Such a lack goes to the brand's owner as a request (DEC-071 point 5). Whether a brand may give one font family a file for each weight is decided apart ([project-kit#3276](https://github.com/aleskalfas/project-kit/issues/3276)).

**How far it goes.** Two presentations, drawn with one brand and judged by one person, and one page that the lack of one role held back. The role this record adds rests also on a job that web toolkits in wide use give a type of its own (Rationale, "Why `lead`, named by its job").

The words it uses:
- **A default** is an alias to another role, which a role takes wherever no brand gives it a value ([visual-communication:DEC-008-library-role-defaults] point 1).
- **Running text** is text read as sentences, rather than a head or a label.
- **A page's title** is the text that names a whole page, which the shared type `type.title` sets.
- **A page's lead** is the text a page's content gives to state the page's point, such as a slide's lead under its title ([visual-communication:DEC-029-piece-brief] point 2). The role `type.lead` is no page's lead (point 2).
- **A display type** would set a few words larger than a page's title, read at a glance, such as a cover's title or a poster's headline.
- **An emphasis type** would set a span stressed within running text, as a voice stresses a word, such as a run its component marks as emphasis ([visual-communication:DEC-033-structure-for-readers] point 2).
- **A second accent** would be a colour role that sets a second thing apart from the rest of a page, beside the accent, which sets one thing apart.
- **The rebuild, a stand-in and a request** are DEC-071's.

## Decision

**The shared roles gain `type.lead`, a typography role for running text set larger than the body, with the default `{type.body}`, and the deck's lead token comes to default to it. A display type, an emphasis type and a second accent are not added now: each waits until the person calls a rebuild's stand-in for it short of shipping, or a project asks for it.**

### 1. `type.lead`, running text set larger than the body

- **Its job.** Running text set larger than the body, so that it stands out from the body and is read before it: the job a lead paragraph has in web toolkits such as Bootstrap. Examples are a page's opening paragraph, the line under a slide's title, and a statement or a quotation set apart. It is set as running text, not as a head.
- **Named by its job, not its rank.** How large it stands beside a heading or a page's title is the brand's design (point 5).
- **Within reach of a piece's own components.** A shared role, it is named by any component, a local one included, under every brand (DEC-001 point 4).
- **Its default, `{type.body}`.** A brand that gives it no value sets it as the body, so it still reads as running text, at the body's size. The body is a shared role of the foundations' first version, with no default of its own, so every brand draws the lead ([visual-communication:DEC-004-brands-and-notations] point 7).

### 2. It names a size of running text, not a page's lead

- **Not DEC-029's lead.** A page's lead is the text a page's content gives to state its point (DEC-029 point 2). `type.lead` names how a text is set, not what it says, and says nothing of a page's point.
- **A page's lead may use it or not.** A component chooses the typography role each text it draws is set in. A page's lead may be set in `type.lead`, in the body or in another role, and a text set in `type.lead` need not be any page's lead. Whether a page has a lead is still read from its content (DEC-029 point 2).
- **Nor the deck's field.** A deck's slide has a field named `lead`, which its content fills. The field stays the deck's, and its token follows the role by default (point 3).

### 3. The deck's lead token comes to follow it

- **Its default, `{type.lead}`.** The deck's component token for the line under a title comes to default to `type.lead`, in place of `type.body`.
- **Two texts read it:** a slide's lead and the cover's subtitle. Under a brand that gives `type.lead` and not the token, both are set in `type.lead`, as a piece's own running text at that size is.
- **A brand may point it elsewhere.** A brand that gives the token a value of its own, a role it aliases or a value, sets both texts by that value, apart from `type.lead` (DEC-035 point 4).
- **Nothing changes where neither is given.** Under a brand that gives neither the token nor `type.lead`, the token resolves to the body, as before. A default pointed at another role is neither a break nor an addition (DEC-035 point 6).

### 4. A display type, an emphasis type and a second accent wait for a need

- **Not added now.** This record adds none of them to the shared roles.
- **The trigger, for each.** The first rebuild whose stand-in for it the person calls short of shipping (DEC-071 point 5), or a request from a project. Either reaches the foundations' owner, and the role then waits for a record of its own (DEC-030 point 4).
- **Meanwhile, a stand-in.** A rebuild that needs one of them draws the nearest the shared roles allow that keeps the part's meaning, and the lack reaches the foundations' owner as a request (DEC-071 point 5).
- **A second accent's jobs have a place.** A difference of kind is a concept's, which a notation maps to a colour family and draws with its sign beside it (DEC-004 point 10). A difference of rank along a sequence is an order's, whose steps run between two ends a brand gives ([visual-communication:DEC-032-ordered-colour-steps] point 1). So a second thing set apart by its kind or its rank takes a concept's family or an order's step, and a rebuild draws a stand-in for a second accent only where neither keeps the difference.

### 5. What the role adds, and what it asks of no one

- **An addition.** A new shared role with a default, in the group `type`, which holds the shared types already. So it adds no top group, and breaks no brand or library (DEC-004 point 5). It goes into the foundations' version being built, whose release needs at least a minor.
- **No brand owes a value.** Every brand draws it, at the value it gives or at the body. A brand exports it as it exports every shared role (DEC-004 point 5).
- **No change of format.** A library's roles take a typography role with a default already, and a brand's typography takes the members it took. Every file the capability accepted reads and draws as before ([visual-communication:DEC-003-change-over-time] point 3).
- **No pair, and no order of sizes checked.** A typography role is in no contrast pair, and each text a scene draws is still measured at its own size and weight (DEC-004 point 8). No check compares its size with another type's. The order of a brand's sizes is its design, which its owner judges, as the owner of a library judges a default's fit (DEC-008 point 2).
- **A piece meets it when its lock moves** to a version of the foundations that declares it (DEC-003 point 8).

## Rationale

**Why the lead now, and the rest on need.** A shared role is cheap to add and costly to remove. Added with a default, it asks no brand for a value and breaks nothing (DEC-004 point 5). Released, it is a name every brand exports, which code outside the capability reads with no lock to protect it, and removing it breaks the foundations and every brand (DEC-003 point 6; DEC-004 point 5). So a shared role is added where a piece needs it, not where one might. Of the four roles the rebuilds lacked, only the larger running text held a page back. The person called every other page shippable, though some were drawn without a role the brand lacked. Every new presentation is a rebuild (DEC-071 points 1 and 4), so the lead's lack would hold back each page that meets it until a request is met. The others wait for the same evidence: a stand-in the person calls short of shipping, or a project that asks.

**Why `lead`, named by its job.** Web toolkits in wide use give this job a type of its own: Bootstrap's lead paragraph is running text set larger than the body to make it stand out. The name tells a designer the job at once. It meets the word's two other uses in the capability, a page's lead and the deck's field and token, so point 2 sets them apart. A role is a named purpose (DEC-001 point 5). Named by its rank, between the body and a page's title, it would be a step of a scale under another name, and would tell a brand nothing of what text a component means by it.

**Why a shared role, and not a top's token or a library's role.** A piece's own components draw what no library's component draws, and under every brand they can count only on the shared roles (DEC-035 points 3 and 5). A top's component token, such as the deck's lead, is the narrowest role, one component's. Read by another component, a brand's value meant for the top would restyle something out of its author's sight (DEC-035, Alternatives considered). A library's own role reaches a brand only where the brand names that library (DEC-008 point 4). A type serves every library, and a meaning that recurs across libraries belongs to the foundations (DEC-008 point 2).

**Why the body as its default.** A default is the fairest stand-in under a brand that never gave the role a value, and for a size or a font a nearby role usually serves (DEC-008 point 2). The body keeps the text running text, though no larger than the body. A heading would set it in a head's weight, and it would read as a head.

**Why the deck's lead follows it.** The deck's token sets the line under a slide's title, the job this role names. Pointed at `type.lead`, its default keeps a slide's lead and a piece's own running text at that size alike under a brand that gives the role and not the token. A brand that gives the token a value in every combination, as the neutral brand does, sees no change from the default alone. So the neutral brand points its token at the role (Implications), and under it the two cannot drift apart. The cover's subtitle reads the same token, so it follows too. A brand that would set either apart from the role gives the token a value of its own, which sets both.

**Why no display type or emphasis type now.** Neither held a page back: the pages drawn without them were called shippable. What each would take is open besides. A display's fair default is weighed in the alternatives below, and so is whether emphasis is a typography role or a font family that keeps its text's size. A record made when a stand-in falls short, or a project asks, weighs them on what that need shows.

**Why no second accent now.** What a second accent would carry has a place already. A difference of kind is a concept's, drawn with its sign, within the bound on how many concepts one piece tells apart by colour (DEC-004 point 10). A difference of rank is an order's (DEC-032 point 1). A default would not stand in the way. A shared role added after the foundations' first version may default to a role of another meaning until a brand gives it a value (DEC-008 point 2), and an order's ends default to the neutral family's fill, which marks no kind by a hue (DEC-032 point 1). Nor would a second accent go unguarded: every difference of colour is told another way too, a second accent's as any other (RS-GRAPHIC-006). So the bar is that its jobs have a place. A second accent would be a third way to tell things apart by colour, beside two that each carry checks of their own, a concept's sign and an order's ends. The cost: a brand whose identity holds two colours shows the second only in its own form and in the values it gives its roles, and a piece's own component cannot paint with it under every brand.

### Alternatives considered

- **The four roles now, each with a default.** Not taken: a shared role is cheap to add and costly to remove, and only the larger running text held a page back.
- **No new role: each rebuild draws a stand-in, and the roles wait for more evidence.** Not taken: the stand-in for the larger running text held a page back, and every new presentation is a rebuild (DEC-071 points 1 and 4).
- **A numbered scale of sizes, such as `type.1` to `type.9`.** Rejected: a role is a named purpose (DEC-001 point 5). A number names a rank, and a brand could not know what text a component meant by it, so switching brands would restyle by rank rather than by job.
- **Another name, such as `type.intro` or `type.large`.** Not taken: the first names a place in a page, where the role serves a statement set apart too, and the second names a rank. `lead` names the job as web toolkits name it, and point 2 sets it apart from the word's other uses.
- **A piece's own component that reads a top's token, such as the deck's lead.** Rejected, for DEC-035 point 3's reasons.
- **A size that a piece's own component computes from the body's.** Rejected: only a brand holds a raw value (DEC-001 point 5), and a brand gives a typography role whole.
- **The role as the starter's own.** Rejected: a brand reaches it only by naming the starter (DEC-008 point 4), and a type serves every library (DEC-008 point 2).
- **The lead defaulting to a heading.** Rejected, for the reason under "Why the body as its default".
- **The deck's lead token left at the body.** Rejected: under a brand that gives `type.lead` and not the token, a slide's lead and a piece's own running text at that size would part.
- **A display type defaulting to a page's title.** Not taken now, with point 4's trigger. Under a brand that gives no display, it would stand as large as a page's title. But `type.title` has a default of its own, and the check of the foundations' roles asks a shared role's default to alias a role with none. While `type.title` lies in no released version, it is no older role either (DEC-004 point 7).
- **A display type defaulting to a heading.** Not taken now, with point 4's trigger. The check takes it, and the heading is a role of the foundations' first version. Under a brand that gives no display, though, it would draw below a page's title wherever a brand sets that title above its heads, the job `type.title` has. A size a little off looks off at worst (DEC-008, Rationale), so the record that adds a display weighs the two.
- **An emphasis type defaulting to the strong type.** Not taken now, with point 4's trigger. A typography role sets a span at one size, so it would serve the body alone, and emphasis within a lead or a heading would need roles of its own. Under a brand that gives none, a span stressed and a span set apart for its importance would look alike.
- **Emphasis as a font family that keeps its text's size,** such as `font.emphasis`, which a stressed span takes in whatever text it lies in. Not taken now, with point 4's trigger. It would serve emphasis at every size, which a typography role cannot. But a run style chooses a whole typography role (DEC-012 point 2), so a run that took a family alone and kept its text's size would change how a run is set, beyond adding a role. The record that adds emphasis weighs the two.
- **`type.italic`, or any name of a look.** Rejected: emphasis names a job, and not every script has an italic. Chinese and Japanese mark stress otherwise, such as with dots beside the characters.
- **A second accent defaulting to a neutral role,** as an order's ends default to the neutral family's fill (DEC-032 point 1). Not taken, with point 4's trigger: the default would serve, but the jobs it would do have a place (Rationale, "Why no second accent now").
- **A second accent defaulting to the accent.** Rejected: under a brand that gives it no value, the two things it was added to tell apart would take one colour.
- **A second accent with no default, in a major release of the foundations.** Rejected: every brand and every library would move to a new major, for a colour whose jobs have a place already.

## Implications

- **No edit to an accepted record.** The role is an addition that DEC-004 points 5 and 7 and DEC-008 point 2 allow, and that DEC-030 point 4 asks a record for. Its default aliases a shared role with no default, as the check of the foundations' roles asks, so the check stays as it is. Its one change to the deck is a token's default, which DEC-035 point 6 counts as neither a break nor an addition.
- **Read against this record, and left as they stand:**
  - DEC-001 points 4 and 5, since a local component names roles as any component does, a role is a named purpose, and only a brand holds a value;
  - DEC-003 point 6 and DEC-004 point 5, since a new shared role with a default breaks nothing, and removing one would break the foundations and every brand;
  - DEC-004 point 7, since `type.lead`'s default aliases a role of the foundations' first version;
  - DEC-004 point 8, since each text a scene draws is measured at its own size and weight;
  - DEC-004 point 10, DEC-032 point 1 and RS-GRAPHIC-006, since kinds and ranks are told apart by colour as they decide, and every difference of colour is told another way too;
  - DEC-008 point 2, since the body is the fair stand-in it asks for;
  - DEC-012 point 2, since a run style chooses a typography role, `type.lead` among them;
  - DEC-029 point 2, since a page's lead stays the text its content gives to state its point, set in whatever role its component chooses;
  - DEC-035 points 3 to 6, since no local component reads or declares a token, the deck's token keeps a default that aliases a role, and pointing it at another breaks nothing;
  - DEC-071 point 5, since a rebuild draws a stand-in for a display, an emphasis or a second accent, and the lack reaches the foundations' owner as a request.
- **Which brand gives it values.** The neutral brand gives `type.lead` a value in every combination it gives, as it gives every shared role (DEC-008, Implications), and its owner chooses the values in the slice. On a projector the value is the size the neutral brand's deck lead takes there, so a slide's lead keeps its size. It points its deck lead token at `{type.lead}` in every combination, in place of the values it gives the token now, so a slide's lead and a piece's own running text at that size cannot drift apart under it, and its cover's subtitle follows (point 3). A brand built on the neutral brand gives the role a value only where the neutral brand opens it (DEC-004 point 6). The neutral brand opens no role, and what it opens is decided apart ([project-kit#3169](https://github.com/aleskalfas/project-kit/issues/3169)). A brand with no base gives it a value, or draws it at the body.
- **Left to a slice under [project-kit#3149](https://github.com/aleskalfas/project-kit/issues/3149),** filed once this record is accepted:
  - the foundations' version being built declares `type.lead` with its default, and the deck's lead token defaults to it (points 1 and 3);
  - the neutral brand's version being built gives `type.lead` its values, and points its deck lead token at it;
  - the capability's page on files, where it lists the shared types, and the tests.
- **Its changeset.** This change declares that it moves no surface of the capability. It owes no migration (COR-010).
- **Left open,** each with point 4's trigger:
  - a display type, and its default;
  - an emphasis type, and whether it is a typography role or a font family that keeps its text's size;
  - a second accent.
