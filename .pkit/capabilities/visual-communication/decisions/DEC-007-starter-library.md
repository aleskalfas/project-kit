---
id: DEC-007
title: The starter library covers the jobs a visual does, and leaves its values to the brand
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability ships a component library to start from, the *starter*, planned wide from the start. It holds a pattern for each common job a visual does, such as showing an order, chosen from published classifications. Each component enters as experimental, so its breadth promises nothing yet. The starter holds the generic forms, and a brand gives them its look.

## Context

The founding record of this capability has it ship component libraries: the foundations, which hold the interface every library shares, and others. It leaves to a later record the component library the capability ships to start from. That library, the *starter*, is the first component library a project meets.

The design work found how libraries were used and missed ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)):
- **Small blocks were reused, and arrangements were rebuilt.** A talk took small blocks from an earlier library and drew each arrangement anew. It even remade a step from another block rather than use the library's own.
- **Ready arrangements went unused.** The talk's generator offered that library's arrangements one line of data away, and no slide used them. The likelier causes were that the job never came up, and that the forms did not fit the message.
- **A brand held its own generic forms.** The brand library the talk used held its own tile, stage and arrow. What made them that brand's was mostly values: flat fills, square corners, its fonts and colours.

A first list of patterns drawn from a slide tool's categories mapped the evidence by how it looked. Broken into its parts, the talk showed other jobs. Most slides set a real exhibit, such as a terminal, beside a claim, and tables recurred across sources.

The core supplies the test of what every project needs (COR-014). A library the capability ships serves every adopter, not one project's subject or taste.

## Decision

**The starter is planned wide from the start, and built ahead of need. It holds a pattern for each common job a visual does, chosen from published classifications of visuals, and the blocks those patterns draw their items with. Each component enters as experimental, with no use needed first. The starter holds the generic form, and a brand gives it its values.**

### 1. Planned wide, and built ahead of need

The starter is planned to cover the jobs visuals commonly do, not only those one project has needed so far.
- **What it holds.** Patterns, which arrange items, and *blocks*. A block is a small component, such as a card or a connector, that a pattern draws its items with or that content places alone. The top components, such as a deck, are the foundations'.
- **The order of building.** A job the evidence shows comes first. The other common jobs follow, built ahead of need, so the starter grows wide in steps.
- **Recurrence is a reason, not a condition.** A local component that recurs is a reason to add a component to the starter. Its owner judges, and no count decides.
- **No privilege.** The engine knows none of the starter's components by name, as the founding record says. So a project may ignore the starter, or publish a library of its own beside it.

### 2. Organised by the job a visual does

- **One job per pattern.** Each pattern answers one question a visual answers, such as "in what order does it happen?", "what rests on what?" or "which items belong together?". Two patterns never share a job, and one pattern never does two.
- **The jobs come from published classifications.** Nancy Duarte's forms of abstract ideas, a practitioners' classification, name them. The classification of visual representations by Lohse, Biolsi, Walker and Rueter, and Yuri Engelhardt's principles that join a visual's parts, check them.
- **The starter's README** lists the patterns by job. For each it gives its question, form, source, evidence and options. It also states the boundary with its neighbours, such as "a list has no order, steps follow one another, a timeline says when".
- **Options stay few.** A pattern's options choose only its arrangement, as the founding record says. About four is the guide, not a limit. Past it, a pattern probably does two jobs, and is split.
- **More than a pattern offers** is a local component, built from the starter's blocks and the engine's tools.
- **Only what data can draw.** A job that needs a tool the engine lacks waits for that tool, such as items on a circle or the layout of a graph.

### 3. Each component enters as experimental

A component enters the starter as experimental, the status that the record of change over time defines, with no use needed first. It enters once it has:
- its job, the established form it follows and that form's source
- its fields and its options, each option a word from a declared list
- its reference renders, each value of each option drawn once, with the combinations the evidence uses
- renders in languages that stress text, such as long compound words and diacritics, beyond the languages of its first project
- a review

The starter's owner, whoever maintains the capability, marks a component stable, as the record of change over time lets a library's owner do.

### 4. The form to the starter, the values to the brand

- **A generic form is a starter component,** which a brand styles with its values. A design system's tile, for example, can be the starter's card in that brand's colours, corners and fonts.
- **Close to the established forms.** The starter draws each generic form close to the forms design systems share, so a brand's values can give it that brand's look. A brand reaches a component only through the roles and component tokens it names, as the record of brands and notations decides. So a starter component names a role for each value a brand's look may change, such as its corners.
- **What stays out.** A form that one brand alone uses is that brand's, as the founding record lets a brand hold parts no shared component has. A subject's concepts belong to a notation (COR-014).
- **Where values fall short,** a brand's own part is a different component, with its own name and job, under the founding record's rule. It is never a changed copy of a starter component.

## Rationale

**Why wide, ahead of need.** A library that lacks a job sends each page to a local component, and an arrangement drawn locally is drawn again on the next page. The talk shows it: it reused small blocks and rebuilt every arrangement. A starter grown from one project's needs alone would carry that project's jobs. The jobs every project meets are known from practitioners' catalogues and from research, so they can be built before any project asks.
- **Against building on recurrence.** The core builds tooling once a pattern recurs (COR-007). Here the recurrence is already seen across the field, in the published classifications, rather than within one project. Entry as experimental hedges a wrong guess.

**Why by job, from a cited classification.** A pattern chosen by its look competes with another that does the same job, and an author cannot tell which to take. A job is the question the visual answers, which the author knows before choosing. A slide tool's categories lean to slides, and sort a visual by how it looks.
- **The jobs:** Nancy Duarte's forms of abstract ideas, flow, structure, cluster and radiate (*slide:ology*, chapter 3), fitted the jobs the talk's slides show.
- **The scope:** the classification by Lohse, Biolsi, Walker and Rueter tells a pattern from a chart, a map or a picture. People sorting graphics found it ("A classification of visual representations", *Communications of the ACM*, 1994).
- **The grammar:** Yuri Engelhardt's principles, such as lining up, linking by a connector, containment and clustering, check that the patterns join their parts in every common way.

**Why one job per pattern, and few options.** A pattern with many options grows into a small language, and each option multiplies the renders that test it. A pattern past a few options usually does two jobs, which two patterns do more plainly. A hard limit would refuse a fifth option that is right, so the owner judges, and a reviewer flags a pattern past the guide.

**Why experimental, with no use first.** A starter built ahead of need cannot wait for uses, or nothing ahead of need would enter. A component that bound its owner from its first day could change only in a breaking release, so each such pattern would be a promise. Experimental lets it change while it is tried. Design systems such as GOV.UK's and IBM's Carbon admit components this way, and their owners decide when one is ready.

**Why languages that stress text.** The starter ships to every adopter, and their languages are not its first project's. A long compound word, or a letter with diacritics, breaks a box that English fits.

**Why the form to the starter, and the values to the brand.** A brand that kept its own tile beside the starter's card would have its pieces use the tile. The starter would go untested by those who use it, and a fix to the card would reach no brand's copy. What makes a design system's tile its own is mostly values, so the starter's card in that brand's values gives the same look. Shipped in the starter, one brand's anatomy would reach every adopter (COR-014).

### Alternatives considered

- **A small starter, with a pattern added once a local component recurs about three times, as COR-007 builds tooling.** Rejected. Recurrence in one project would shape a library for every project, and arrangements rebuilt each time show their recurrence late.
- **Patterns chosen by their look, or split by kind of work.** Rejected. Two patterns would serve one job, and the founding record already rejects libraries split by kind of work.
- **A slide tool's categories as the classification.** Rejected. They lean to slides, and sorted the evidence by how it looks.
- **Unproven components in a library of their own.** Rejected. A piece would lock two libraries for one job, and a component moving between them would change its name.
- **A hard limit on options, enforced by a check.** Rejected. It would refuse a fifth option that is right.
- **A starter of few generic forms, each brand keeping its own.** Rejected. The starter would go untested, and a fix to a form would reach no copy.
- **Every form in the starter, a brand's own anatomy included.** Rejected. One brand's form would ship to every adopter.

## Implications

- **The starter's README** holds the list of patterns and blocks by job, the boundaries between them, and what is left out and why. A change of the list is a change of the README and of the starter, not of this record.
- **The starter is built in steps.** What the first pieces need comes first, as experimental components, then the other jobs the evidence shows, then those built ahead of need. A pattern that needs a tool the engine lacks waits for the tool.
- **The reference renders need a brand.** They draw with the brand the capability keeps for its tests, as the record of brands and notations has it. That record leaves open whether a brand ships that projects may lock.
- **This record adds no check to validation.** Its bar for entry is judged in review by the starter's owner. The note a piece gets when it uses an experimental component is the record of change over time's.
- **A project's own component library** may follow these principles. They bind only the starter.
- **Left to the starter's README and later changes:** the blocks that a legend and icons need, so colour is never the only sign.
- **Left open:** whether a notation for software work ships, and as which kind of library, with the diagrams of software work, such as states, classes and sequences.
