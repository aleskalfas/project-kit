---
id: DEC-028
title: Two rule sets hold the principles of visual communication, each rule taken from its field's canon
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability ships its view of good visual communication as two rule sets. `COMM` asks whether a piece says the right thing, and `GRAPHIC` whether it looks right. Each rule is taken from the established principles of its field, and this record names its source, so no project writes them again. A project adds its own rules on top. `COMM` judges only a piece that explains, and `GRAPHIC` every piece. Each rule says apart what can be judged from the content's text and what only the drawn page shows. The rules bind on a piece only once its content is something rules bind on. Until then they guide whoever designs or judges a piece. One rule, on how a page's differences show, narrows a reason the founding record gives for colour.

## Context

The record that founds the capability leaves the rules of good visual communication, with their reasons, to a record of their own ([visual-communication:DEC-001-visual-communication-discipline] point 1). The capability's reviewer reads a piece's drawn pages for faults, and judges no such rule ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).

One talk shows the need, as the capability's planning found ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)). An agent drew and wrote its slides. The talk's author set its rules one at a time while reading them: keep the flow, use plain words, show the big picture first, say why. The agent checked its own slides against them, and the author still caught misses. In the same planning, on 31 October 2026, the capability's maintainer agreed eleven such rules, each taken from the canon with its source. This record words them anew for every kind of piece, and adds a twelfth.

The core layer supplies what rules need. A rule set gives each rule a permanent id, an origin and a status ([COR-051](../../../decisions/core/COR-051-rule-sets.md) points 3 to 5). An origin may cite a record, for a reason longer than a line. The rule-set reviewer takes its rules only from rule sets (COR-057 point 7). A capability may also ship one loaded set, which binds on a session's work rather than on artefacts (COR-070 point 1). This capability's is `VIS`.

A piece's content is a plain data file, and rules bind only on artefacts. Making such a file an artefact is a change of the core ([project-kit#2416](https://github.com/aleskalfas/project-kit/issues/2416)).

## Decision

**The capability ships the principles of visual communication as two method rule sets. `COMM` judges whether a piece says the right thing, and `GRAPHIC` whether it looks right. Each rule is taken from the established canon of its field, and this record names its source. `COMM` judges only a piece that explains, and `GRAPHIC` every piece. Each rule says apart what the content's text shows and what only the drawn page shows. The sets bind on nothing until a piece's content is an artefact.**

### 1. The rules are the canon's, and a project adds its own

The shipped rules are known principles of good design, which no project wants the opposite of. Each is taken from a source this record names. A talk or a project that shows a rule at work confirms it, and is never its source. A project adds its own rules on top, in a set of its own that inherits these (COR-051 point 7).

What the sets leave to others:
- **The look** is the libraries': a brand's values, a component's form and a notation's concepts.
- **What needs no judgement** is a check's, run on every render whether a rule binds or not. Examples are a text that spills out of its box, too little contrast, and a text smaller than its medium allows.
- **A project's taste** is the project's own set, such as a limit on the words in a lead.
- **One piece's goals** are that piece's, so no rule outlives the piece it was written for.
- **A rule about a library,** such as which icons a notation gives, is that library's validation.

### 2. Two sets, by the kind of failure

- **`COMM`:** does the piece say the right thing?
- **`GRAPHIC`:** does the piece look right?

A finding then names its kind of failure, such as "no point" against "no focal point". So its reader knows whether to mend what a page says, or how it shows it.

`GRAPHIC` is named apart from `VIS`, the capability's loaded set. A rule id is permanent (COR-051 point 3), so a finding that cites one set is never read as citing the other.

### 3. Which pieces each set judges

- **`COMM` judges a piece that explains** or argues, such as a talk, a handout, a figure in a documentation page or a poster with one message. It does not judge a piece with no single point, such as a map of a system, a board people fill in, or a mock-up of a screen.
- **A piece says whether it explains,** in a field of its own ([visual-communication:DEC-001-visual-communication-discipline] point 3). Each `COMM` rule names that field, and a reviewer reads it.
- **`GRAPHIC` judges every piece,** whatever its purpose.

The line is data visualisation's own, between explanatory and exploratory work (Cole Nussbaumer Knaflic, *Storytelling with Data*).

### 4. Each rule says apart what the text shows and what the drawing shows

Each rule names two parts:
- **From the text:** what can be judged from the content's text alone, such as whether a lead answers its title.
- **On the drawn page:** what only the page as drawn shows, such as whether the eye finds the point first.

A part may be empty, where the rule needs only the text or only the drawing. A reviewer that reads only the text then knows which part it can judge, and which needs the drawn pages. How a review at the merge treats the part only the drawing shows is that review's question ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)).

### 5. Where the rules bind, and how they guide meanwhile

- **Method sets, with no scope.** Both are method rule sets of the capability, which take no scope (COR-051 point 2). Their rules bind only on an artefact, and only through a set of the project's own that inherits them.
- **Not before a piece's content is an artefact.** Until then, an accepted rule of these sets binds on no piece.
- **Read from the sets.** Whoever designs or judges a piece by these rules reads them from the sets, never from a copy in an agent's instructions. While they bind nothing, they guide, and bind no one. Which agents take them up is the record of the capability's agents' ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)).
- **A break informs.** While a rule binds nothing, a break of it that an agent reports is a finding that informs, which holds nothing. The rule-set reviewer treats a break of a rule that binds nothing the same way (COR-057 point 1, "Rules that bind nothing").
- **Not a loaded set.** The capability's one loaded set is `VIS` (COR-070 point 1). A loaded set binds on a session's work, with no opt-out, and no reviewer of a change reads it.

### 6. A page makes one point, and the pages tell the story in order

These rules judge what a piece says, page by page and across its pages.
- **`RS-COMM-001`, a page makes one point, and shows it.** Sources: Michael Alley's assertion-evidence approach (*The Craft of Scientific Presentations*); Barbara Minto's vertical logic, each part supporting the one above it (*The Pyramid Principle*).
- **`RS-COMM-002`, the big picture comes first.** Sources: Barbara Minto's pyramid principle, the answer before its arguments and their detail; Ben Shneiderman's "overview first, zoom and filter, then details on demand". For something new to the audience: David Ausubel's advance organisers, "the most important single factor influencing learning is what the learner already knows"; Dedre Gentner's structure-mapping theory of analogy (1983).
- **`RS-COMM-003`, the pages tell the story in order.** Source: Barbara Minto's horizontal logic, where the headings alone, in order, carry the argument.

### 7. The words fit the audience, and each fact names its source

These rules judge how a piece says it.
- **`RS-COMM-004`, the words fit the audience.** Sources: audience analysis, the first rule of rhetoric and of technical writing; ISO 24495-1 (2023), plain language. A concrete limit, such as the words in a sentence, is a project's taste (point 1).
- **`RS-COMM-005`, each fact names its source.** Sources: Edward Tufte's principles of analytical design, "thoroughly describe the evidence" (*Beautiful Evidence*); attribution in journalism.

### 8. The eye finds the point first, and sees what belongs together

These rules judge what a reader sees first, and what as one.
- **`RS-GRAPHIC-001`, one focal point.** Sources: visual hierarchy, and the designer's squint test. `COMM` asks whether a page says its point, and this rule whether the eye finds it first.
- **`RS-GRAPHIC-002`, what belongs together is grouped and lined up.** Sources: the Gestalt principles of proximity and connection; Robin Williams' proximity and alignment (*The Non-Designer's Design Book*). Lining parts up to a page's grid is mostly the layouts' work, so the rule's judgement is mostly which parts belong together.

### 9. Nothing extra, and one meaning one look

These rules judge what a page holds.
- **`RS-GRAPHIC-003`, nothing extra.** Sources: Edward Tufte's chartjunk; Richard Mayer's coherence principle. The rule speaks of a page's job, not its message, so it fits a piece that does not explain too, such as a board's empty areas.
- **`RS-GRAPHIC-004`, the same meaning looks the same.** Sources: Robin Williams' repetition; Jakob Nielsen's "consistency and standards"; design systems. The rule leaves a new message free of the picture of the one before, so consistency never costs a page its own message.

### 10. Everyone can read it, where it is shown

These rules judge who can read a page.
- **`RS-GRAPHIC-005`, readable where it is shown.** Sources: Nancy Duarte's glance test (*slide:ology*); legibility minimums for each medium, such as the display image size standard ANSI/INFOCOMM V202.01 (AVIXA's DISCAS). A smallest text size for a medium is a check's, run always (point 1), and the glance test is the rule's.
- **`RS-GRAPHIC-006`, colour is never the only signal.** About one man in twelve cannot tell some colours apart, a projector washes colours out, and a print may be grey. Source: WCAG 1.4.1, use of colour. Contrast (WCAG 1.4.3) is a check's, run always.

### 11. The form says what the content says

**`RS-GRAPHIC-007`** judges a page's differences against its content's: a difference added, or one dropped. A picture fails that adds a difference the content lacks, such as five unrelated hues on one chain. So does one that drops a difference the content has, such as equal bars for a narrowing.

Sources: Jock Mackinlay's expressiveness and effectiveness (*Automating the Design of Graphical Presentations of Relational Information*, 1986); Jacques Bertin's visual variables (*Sémiologie graphique*, 1967). Expressiveness asks that a picture show all the facts and no others. Effectiveness gives the most important fact the variable the eye reads best. Bertin's hue is selective, never ordered: the eye splits items of five hues into five groups.

**What it narrows.** The founding record says that a colour says what a thing is, not where it sits (DEC-001, "Why options are declared, and colour follows meaning"). On a page whose point is an order, the order is what the page says. There the parts of the items that show the order do not take each concept's hue: they share one colour, or step in one shade. Each concept keeps its colour on a mark of its own, such as its icon.

**What it leaves as it is.** How an item takes its colour stays as the founding record decides it (DEC-001 point 6), and that point's words stay true. An item's colour still comes from the concept it names. Content points the parts that show the order at another role, as that point allows, and an icon takes its concept's colour family ([visual-communication:DEC-004-brands-and-notations] point 10). So a piece meets the rule with what the model holds. Colour roles that step in an order are a later refinement of the record of brands and notations.

## Rationale

**Why the canon, and not a project's taste.** No project wants a page without a point, or a colour only some readers can tell apart. A principle that holds for every audience is know-how the capability carries, as its founding record says (DEC-001 point 1). A project's taste, such as a word limit, holds for its own audience alone, so it stays the project's (COR-014).

**Why the reasons live in a record.** Each rule rests on a source and a judgement longer than a line, and a record holds such a reason (COR-051 point 5). An origin in the decider's own words would read, to an adopter, as one person's say. The canon behind it would then have no home. A point per group of rules lets each rule anchor to its reason, so a change to the reason flags the rule. The record gives each rule's id, title, sources and reason, and the rule's statement is its set's.

**Why two sets.** A finding that names its kind of failure tells its reader what to mend. One set would mix "the lead does not answer the title" with "the title is too small to read".

**Why `COMM` judges only a piece that explains.** A map of a system has no single point, and a board people fill in has no lead to answer a title. A rule that judged them would fail every such piece, or be waived each time. A scope selects by path and by type, never by what a piece says it does. So the rule says in its wording which pieces it judges (DEC-001, "Why a piece declares what it is selected by").

**Why each rule says apart what the text and the drawing show.** A reviewer of a change may read a piece's content as text, without the pages drawn. A finding it made on what only the drawing shows would be a guess. A rule that says which part needs the drawn pages lets such a reviewer judge the rest. Whether a change may pass at the merge with that part unjudged is the merge review's question.

**Why accept the sets before they bind.** Whoever designs or judges a piece needs rules to read, with ids a finding cites. A rule that binds nothing still has its id, its origin and its review (COR-051 points 3 to 5). The core's writers and reviewers follow only rules that bind (COR-051, Implications), so these guide and bind no one, and a break of one only informs. Once they bind, none is written again.

**Why not a loaded set.** A loaded set binds a session's work, wherever the capability is installed, and a project cannot opt out (COR-070 point 3). These rules judge pieces, which a project chooses to bind. A loaded set also binds no artefact, so no reviewer of a change could judge a piece against it (COR-051 point 7).

**Why the name `GRAPHIC`.** The set judges a piece's graphic design, and the name means nothing else in the capability. A name close to `VIS` would make findings of the two sets read alike.

**Why the form rule has a point of its own.** It overlaps others: one focal point already fails five equal bars, and colour never alone already asks for a second sign of a kind. Its test of a difference added or dropped is its own, and no other rule asks it. A point of its own lets a change to that test flag this rule alone.

**Why the form rule's wording.**
- **What a reader takes for meaning,** not every difference: a page's grid and its type sizes differ everywhere, and mean nothing.
- **Emphasis where the page's point needs it,** or its job on a page with no single point.
- **Kinds never by hue alone,** as `RS-GRAPHIC-006` asks, and by a line style too, as that rule allows.
- **An order by more than shade,** since steps of one shade collapse under high contrast and forced colours. Position, size, numbering and arrows carry an order too.
- **A quantity by the most exact variable the page allows:** position or length first, angle or area where neither serves, as Mackinlay ranks them.
- **The concept's colour kept on a mark,** so an item still says what it is (`RS-GRAPHIC-004`), while the parts that show the order show it.
- **The frame left out,** since a title bar and a footer are the same on every page. A picture made elsewhere, such as a screenshot, holds differences the piece cannot change.

**Why the form rule narrows a reason, and leaves the model.** The model already lets content point a part at another role, so a piece can meet the rule today. A change to how the engine resolves colour would rest on a judgement the engine cannot make: what a page's point is. So the rule narrows the principle behind the model, and the model stays.

### Alternatives considered

- **Inline origins in the decider's words.** Rejected: an adopter would read a rule shipped to it as one person's say, and the canon behind it would have no home.
- **One set.** Rejected: a finding would not say which kind of failure it is.
- **The rules in the reviewer's instructions.** Rejected: a copy has no id, no status and no review, and drifts from its source (COR-057, "Why one reviewer that reads the rules").
- **The rules in the capability's loaded set.** Rejected, as "Why not a loaded set" says.
- **Waiting until a piece's content is an artefact.** Rejected: there would be no rule to read meanwhile, and the rules would be written later anyway.
- **A scope on the sets.** Rejected: a method set takes no scope (COR-051 point 2). A set of the project's own says where they bind.
- **The name `VISUAL`.** Rejected: `RS-VISUAL-001` would stand beside `RS-VIS-001`, and neither id can change.
- **The name `LOOK`.** Rejected: in this capability, the look is what libraries give a piece, and a look is a run of the viewing step.
- **The names `DESIGN` and `FORM`.** Rejected: the first reads as a software design's review, and the second is what a brand draws its layouts with (DEC-001 point 5).
- **A concept's colour over the order, always.** Rejected for a page whose point is an order: five hues on one chain read as five unrelated kinds.
- **The order's colour in the engine's model.** Rejected: the engine cannot tell a page's point, and content can already point the parts at a role.
- **A third set inheriting both, for an install to inherit.** Not taken now: it would bind nothing and serve no reader until an install declares a set. Every new major of either set would also force one of it.

## Implications

- **The capability ships two method rule sets** in its rule-sets folder, `COMM` and `GRAPHIC`. Each rule cites this record as its origin, and anchors to the points it rests on. The rules are accepted with this record. In a project that installs the capability, both names join the names of its rule sets, which are unique (COR-051 point 3).
- **Edits to accepted records,** made once this record is accepted, in the change that proposes it (COR-066 point 5):
  - **The founding record's Rationale,** "Why options are declared, and colour follows meaning." Its sentence that a colour says what a thing is, not where it sits, gains its limit: on a page whose point is an order, the parts that show the order show the order, and each concept keeps its colour on a mark of its own (refinement per this record, point 11).
  - **The founding record's Implications.** Its list of what is left to later records no longer names the rules of good visual communication with their reasons (refinement per this record).
  - **The viewing step's record, point 7.** Its bullet "Left to others" says that the rules of visual communication are this record's, and leaves which agent judges a piece against them to the record of the capability's agents (refinement per this record).
- **The capability's README** lists the two sets among what the capability ships.
- **Before the rules bind,** three things are decided elsewhere:
  - a piece's content as an artefact, with the fields that mark a page's title and lead, which the part judged from the text needs ([project-kit#2416](https://github.com/aleskalfas/project-kit/issues/2416));
  - the review at the merge, and how it treats the part only a drawing shows ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)). A reviewer cannot approve a change while a fact a rule names cannot be found (COR-057 point 3), and the drawn pages are not committed;
  - which change owns the breaks a piece's content holds when its piece file starts to say it explains, or names another audience or medium. That file stays plain data, so such a change alters no artefact.
- **A set an install declares.** A capability's install may create one project rule set, which inherits one of its method sets and selects by the capability's own types (COR-017). Binding both sets through one needs a third set that inherits both, or a refinement of the core. That is decided with the steps after a piece's content becomes an artefact.
- **Left to other records:** the agents that design and review a piece by these rules, and which finding the reviewer makes where a rule and its list of faults name one defect ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)); the colour roles that step in an order, and the principles a shipped brand follows, both refining the record of brands and notations ([visual-communication:DEC-004-brands-and-notations]).
- **No migration.** The sets are an addition, and change nothing a project holds (COR-010).
